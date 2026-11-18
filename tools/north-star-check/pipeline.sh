#!/usr/bin/env bash
# rivet: verifies REQ-NORTH-STAR-COMPONENT
# Build the North Star check as a component and run it through our own chain:
#
#   cargo (wasm32-wasip2) -> component
#   loom optimize         -> optimised component
#   wsc sign / verify     -> signed component; a flipped byte must fail verify
#   meld fuse             -> core module, which is what kiln runs
#   cases.py              -> Python script, component (wasmtime), optimised
#                            and signed component (wasmtime) and kiln agree on
#                            the committed data, the 15 planted violations and
#                            FUZZ seeded random cases
#
# The tools come from the varve layer pinned in varve.toml (scripts/install-varve.sh
# puts its shims on PATH); this script only checks they are there.
#
#   tools/north-star-check/pipeline.sh OUT_DIR
#
# Env: FUZZ (default 200) · KILN_GAP=1 tolerates kiln failing to start (a
# recorded gap: kiln 0.7.2/0.7.3 lack three wasi:filesystem imports and
# wasi:cli/exit exit-with-code); the
# harness fails if kiln starts running, so the switch gets removed.
# Exit: 0 all steps hold · 1 a step failed · 2 could not run.
set -euo pipefail

OUT="${1:?usage: pipeline.sh OUT_DIR}"
FUZZ="${FUZZ:-200}"
HERE="$(cd "$(dirname "$0")" && pwd)"
for t in cargo wasmtime loom wsc meld kiln python3; do
  command -v "$t" >/dev/null || { echo "pipeline: $t not on PATH" >&2; exit 2; }
done
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"

echo "== tool versions"
for t in wasmtime loom wsc meld kiln; do printf '%s: ' "$t"; "$t" --version 2>&1 | head -1; done

echo "== build"
cargo build --manifest-path "$HERE/Cargo.toml" --release --target wasm32-wasip2 --locked
cp "$HERE/target/wasm32-wasip2/release/north-star-check.wasm" "$OUT/north-star-check.wasm"

echo "== loom optimize"
loom optimize "$OUT/north-star-check.wasm" -o "$OUT/north-star-check.opt.wasm"

echo "== wsc sign + verify (one-off key for this run)"
wsc keygen -k "$OUT/sign.key" -K "$OUT/sign.pub"
wsc sign -k "$OUT/sign.key" -i "$OUT/north-star-check.opt.wasm" -o "$OUT/north-star-check.signed.wasm"
wsc verify -K "$OUT/sign.pub" -i "$OUT/north-star-check.signed.wasm"
# Negative control: one flipped byte in the middle of the module.
python3 - "$OUT/north-star-check.signed.wasm" "$OUT/tampered.wasm" <<'EOF'
import sys
b = bytearray(open(sys.argv[1], "rb").read())
b[len(b) // 2] ^= 0x01
open(sys.argv[2], "wb").write(b)
EOF
if wsc verify -K "$OUT/sign.pub" -i "$OUT/tampered.wasm"; then
  echo "pipeline: a flipped byte still verifies" >&2
  exit 1
fi
echo "flipped byte: verification refused, as it must be"
rm -f "$OUT/sign.key"

echo "== meld fuse (kiln runs core modules)"
meld fuse --memory multi "$OUT/north-star-check.wasm" -o "$OUT/north-star-check.core.wasm"

echo "== negative control: a mutant that drops rule 3's kind check must fail the comparison"
rm -rf "$OUT/mutant" && mkdir -p "$OUT/mutant"
cp -R "$HERE/Cargo.toml" "$HERE/Cargo.lock" "$HERE/src" "$OUT/mutant/"
python3 - "$OUT/mutant/src/check.rs" <<'EOF'
import sys
p = sys.argv[1]
s = open(p).read()
old = "if !in_set(&kind, &kinds)? {"
if s.count(old) != 1:
    sys.exit("pipeline: mutation site not found once in check.rs")
open(p, "w").write(s.replace(old, "if false && !in_set(&kind, &kinds)? {"))
EOF
cargo build --manifest-path "$OUT/mutant/Cargo.toml" --release --target wasm32-wasip2 --locked --quiet
wasmtime compile -S cli-exit-with-code=y \
  "$OUT/mutant/target/wasm32-wasip2/release/north-star-check.wasm" -o "$OUT/mutant.cwasm"
if python3 "$HERE/cases.py" --wasm "$OUT/mutant.cwasm" --runner python \
  --runner "mutant=wasmtime run --allow-precompiled -S cli-exit-with-code=y --dir {dir}::/case {wasm} --root /case"; then
  echo "pipeline: the mutant passed the comparison; the harness cannot fail" >&2
  exit 1
fi
echo "mutant: the comparison failed, as it must"

echo "== differential"
# wasmtime compiles each artifact once up front instead of once per case.
# -S cli-exit-with-code=y: exit code 2 needs the unstable exit-with-code.
WT=(wasmtime run --allow-precompiled -S cli-exit-with-code=y)
for a in north-star-check north-star-check.opt north-star-check.signed; do
  wasmtime compile -S cli-exit-with-code=y "$OUT/$a.wasm" -o "$OUT/$a.cwasm"
done
GAP=()
if [ "${KILN_GAP:-0}" = 1 ]; then GAP=(--expect-cannot-run kiln); fi
python3 "$HERE/cases.py" --fuzz "$FUZZ" --wasm "$OUT/north-star-check.cwasm" \
  --runner python \
  --runner "wasmtime=${WT[*]} --dir {dir}::/case {wasm} --root /case" \
  --runner "loom=${WT[*]} --dir {dir}::/case $OUT/north-star-check.opt.cwasm --root /case" \
  --runner "signed=${WT[*]} --dir {dir}::/case $OUT/north-star-check.signed.cwasm --root /case" \
  --runner "kiln=kiln --wasi --dir {dir} --wasi-arg --root --wasi-arg {dir} $OUT/north-star-check.core.wasm" \
  ${GAP[@]+"${GAP[@]}"}
