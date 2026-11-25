#!/usr/bin/env bash
# rivet: verifies REQ-NORTH-STAR-COMPONENT
# Build the North Star check as a component and run it through our own chain:
#
#   cargo (wasm32-wasip2) -> component
#   loom optimize         -> optimised component
#   wsc sign / verify     -> signed component; a flipped byte must fail verify
#   meld fuse             -> core module, which is what kiln runs
#   harness (Rust)        -> a rule-3 mutant must fail the comparison; then the
#                            Python script, the component, the optimised and
#                            the signed component (wasmtime) and kiln must
#                            agree on the committed data, the 19 planted
#                            violations and FUZZ seeded random cases
#
# The tools come from the varve layer pinned in varve.toml (scripts/install-varve.sh
# puts its shims on PATH); this script only checks they are there.
#
#   tools/north-star-check/pipeline.sh OUT_DIR
#
# OUT_DIR must not contain spaces: the harness splits runner commands on
# whitespace.
# Env: FUZZ (default 200) · KILN_GAP=1 tolerates kiln failing to start. CI
# no longer sets it: since covalent 2026.11.27 (kiln 0.9.0) kiln must run the
# component like the other runners. The harness fails if kiln runs while the
# switch is set, so it cannot linger.
# Exit: 0 all steps hold · 1 a step failed · 2 could not run.
set -euo pipefail

OUT="${1:?usage: pipeline.sh OUT_DIR}"
FUZZ="${FUZZ:-200}"
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
for t in cargo wasmtime loom wsc meld kiln python3 od dd cmp; do
  command -v "$t" >/dev/null || { echo "pipeline: $t not on PATH" >&2; exit 2; }
done
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
case "$OUT" in *" "*) echo "pipeline: OUT_DIR contains a space" >&2; exit 2 ;; esac

echo "== tool versions"
for t in wasmtime loom wsc meld kiln; do printf '%s: ' "$t"; "$t" --version 2>&1 | head -1; done

echo "== build"
cargo build --manifest-path "$HERE/Cargo.toml" --release --target wasm32-wasip2 --locked
cp "$HERE/target/wasm32-wasip2/release/north-star-check.wasm" "$OUT/north-star-check.wasm"
cargo build --manifest-path "$HERE/harness/Cargo.toml" --release --locked
CASES=("$HERE/harness/target/release/north-star-cases" --repo "$REPO")

echo "== loom optimize"
loom optimize "$OUT/north-star-check.wasm" -o "$OUT/north-star-check.opt.wasm"

echo "== wsc sign + verify (one-off key for this run)"
wsc keygen -k "$OUT/sign.key" -K "$OUT/sign.pub"
wsc sign -k "$OUT/sign.key" -i "$OUT/north-star-check.opt.wasm" -o "$OUT/north-star-check.signed.wasm"
wsc verify -K "$OUT/sign.pub" -i "$OUT/north-star-check.signed.wasm"
# Negative control: one flipped bit in the byte in the middle of the module.
cp "$OUT/north-star-check.signed.wasm" "$OUT/tampered.wasm"
size=$(wc -c < "$OUT/tampered.wasm")
off=$((size / 2))
byte=$(od -An -tu1 -j "$off" -N1 "$OUT/tampered.wasm" | tr -d ' ')
oct=$(printf '%03o' $((byte ^ 1)))
# shellcheck disable=SC2059 # the format string is the escaped byte itself
printf "\\$oct" | dd of="$OUT/tampered.wasm" bs=1 seek="$off" conv=notrunc 2>/dev/null
if cmp -s "$OUT/north-star-check.signed.wasm" "$OUT/tampered.wasm"; then
  echo "pipeline: the byte flip changed nothing" >&2
  exit 2
fi
if wsc verify -K "$OUT/sign.pub" -i "$OUT/tampered.wasm"; then
  echo "pipeline: a flipped byte still verifies" >&2
  exit 1
fi
echo "flipped byte at offset $off: verification refused, as it must be"
rm -f "$OUT/sign.key"

echo "== meld fuse (kiln runs core modules)"
meld fuse --memory multi "$OUT/north-star-check.wasm" -o "$OUT/north-star-check.core.wasm"

# wasmtime compiles each artifact once up front instead of once per case.
# -S cli-exit-with-code=y: exit code 2 needs the unstable exit-with-code.
WT=(wasmtime run --allow-precompiled -S cli-exit-with-code=y)

echo "== negative control: a mutant that drops rule 3's kind check must fail the comparison"
rm -rf "$OUT/mutant" && mkdir -p "$OUT/mutant/src"
cp "$HERE/Cargo.toml" "$HERE/Cargo.lock" "$OUT/mutant/"
cp "$HERE"/src/*.rs "$OUT/mutant/src/"
site='if !in_set(&kind, &kinds)? {'
if [ "$(grep -cF "$site" "$HERE/src/check.rs")" != 1 ]; then
  echo "pipeline: mutation site not found once in check.rs" >&2
  exit 2
fi
sed 's/if !in_set(&kind, &kinds)? {/if false \&\& !in_set(\&kind, \&kinds)? {/' \
  "$HERE/src/check.rs" > "$OUT/mutant/src/check.rs"
grep -qF 'if false && !in_set(&kind, &kinds)? {' "$OUT/mutant/src/check.rs" || {
  echo "pipeline: the mutation did not apply" >&2
  exit 2
}
cargo build --manifest-path "$OUT/mutant/Cargo.toml" --release --target wasm32-wasip2 --locked --quiet
wasmtime compile -S cli-exit-with-code=y \
  "$OUT/mutant/target/wasm32-wasip2/release/north-star-check.wasm" -o "$OUT/mutant.cwasm"
if "${CASES[@]}" --wasm "$OUT/mutant.cwasm" --runner python \
  --runner "mutant=${WT[*]} --dir {dir}::/case {wasm} --root /case"; then
  echo "pipeline: the mutant passed the comparison; the harness cannot fail" >&2
  exit 1
fi
echo "mutant: the comparison failed, as it must"

echo "== differential"
for a in north-star-check north-star-check.opt north-star-check.signed; do
  wasmtime compile -S cli-exit-with-code=y "$OUT/$a.wasm" -o "$OUT/$a.cwasm"
done
GAP=()
if [ "${KILN_GAP:-0}" = 1 ]; then GAP=(--expect-cannot-run kiln); fi
"${CASES[@]}" --fuzz "$FUZZ" --wasm "$OUT/north-star-check.cwasm" \
  --runner python \
  --runner "wasmtime=${WT[*]} --dir {dir}::/case {wasm} --root /case" \
  --runner "loom=${WT[*]} --dir {dir}::/case $OUT/north-star-check.opt.cwasm --root /case" \
  --runner "signed=${WT[*]} --dir {dir}::/case $OUT/north-star-check.signed.cwasm --root /case" \
  --runner "kiln=kiln --wasi --dir {dir} --wasi-arg --root --wasi-arg {dir} $OUT/north-star-check.core.wasm" \
  ${GAP[@]+"${GAP[@]}"}
