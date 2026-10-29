# friction × model: pilot harness

The harness for the experiment pre-registered in
[`docs/experiments/2026-10-friction-x-model.md`](../../docs/experiments/2026-10-friction-x-model.md).
Read that document first. It fixes the levels, the models, N = 10, the three
repetitions, the lint set, the hypotheses and the decision rules. This
directory implements them; it does not change them.

Status: pilot only. `fxm.py matrix` refuses to run without `--pilot`.

## Layout

```
fxm.py                       the runner: loop, friction tools, oracle, report, self-test
frozen.sha256                every fixed task file; a run stops if one differs
misra-rules-2.22.0.txt       the MISRA C:2012 rules cppcheck 2.22.0's add-on has a checker for
tasks/<id>/
  spec.md                    behaviour spec, numbered sentences (shown to the model)
  c/<header>.h, c/stub.c     fixed C header and stub (shown)
  rust/stub.rs               Rust stub (shown)
  kani/proofs.rs             fixed Kani harnesses (shown at F4 only, never editable)
  hidden/                    the oracle; never shown, every file carries a canary
    gen_vectors.py           one Python reference model -> vectors.h + vectors.rs
    test_main.c, hidden.rs   C and Rust drivers over the same vectors
  reference/                 a correct solution: must pass, with zero findings everywhere
  mutant/                    a wrong solution: must fail the hidden suite
```

Pilot tasks: `t01-ring-buffer` (bounded byte FIFO) and `t02-q15-saturating`
(saturating Q15 arithmetic).

The harness is Python stdlib only. It runs offline, except for the
`claude` CLI calls.

## Commands

```sh
cd experiments/friction-x-model

python3 fxm.py self-test               # stub model, stub tools: no API, no toolchain (runs in CI)
python3 fxm.py self-test --with-tools  # also the real oracle on reference and mutant (needs cc, cargo)
python3 fxm.py check-tools             # each pinned tool and its version; SKIPPED/MISMATCH exits 3
python3 fxm.py check-tasks             # oracle and friction potency; 0 failed AND 0 skipped required

# one run
python3 fxm.py run --task t01-ring-buffer --level F3 --model claude-haiku-5-5 --rep 1

# the pilot: 2 tasks x 5 levels x 4 models x 3 reps = 120 runs; resumable
python3 fxm.py matrix --pilot
python3 fxm.py report

python3 fxm.py gen-vectors             # only when a reference model changes: rewrites vectors + frozen.sha256
```

Exit codes: 0 ok · 1 a check failed · 2 could not run · 3 incomplete (a tool
was missing). A skipped check is never green.

Each run writes `results/<task>/<level>/<model>/rep<k>.json`, with every
iteration's findings, token usage and notional cost. The record also holds
the final code, the hidden-suite result, residual findings, the toolchain
versions and the hash of `frozen.sha256`. `matrix` skips a run that is
already `ok` and re-runs one that is `could-not-run`. It stops cleanly at a
usage limit, so running the same command again resumes. Scratch builds go
to `work/`, which git ignores.

Environment overrides, for tool paths only: `FXM_CLAUDE`, `FXM_CC`,
`FXM_CPPCHECK`, `FXM_RUST_TOOLCHAIN`, `FXM_MIRI_TOOLCHAIN`. `check-tools`
still checks the pinned versions. Every subprocess runs with
`RUSTUP_AUTO_INSTALL=0`, so a missing toolchain is reported as missing and
never downloaded.

## Pins

| tool | pin | checked by |
|---|---|---|
| Claude Code CLI | 2.1.312 | `claude --version` |
| cppcheck | 2.22.0, `addons/misra.py` sha256 `2955eca9db4b4e863977a6b075ba0361a9d433ba30f0a80ee6ddc5bd1599893d` | version string and file hash |
| Rust (F2, F3, hidden tests) | 1.96.1 with clippy 0.1.96 | `rustc +1.96.1 --version` |
| Kani (F4) | cargo-kani 0.67.0 | `cargo kani --version` |
| Miri (residual) | rustup `nightly-2026-09-23`, which reports `rustc 1.100.0-nightly (6bb1652a0 2026-09-22)` | the version string, not the name |
| C compiler | the system `cc` (Apple clang on the bench machine), with ASan, UBSan and `--analyze` | recorded per run |

## Setting up the bench machine

The pilot runs on the bench machine, not in CI and not on a laptop. Keep at
least 20 GB free on its disk (`df -h`) before and after installing.

```sh
# 0. work directory and checkout, at the PR's head commit
mkdir -p "$WORK" && cd "$WORK"
git clone https://github.com/pulseengine/pulseengine.eu.git && cd pulseengine.eu
git checkout <commit>
cd experiments/friction-x-model

# 1. C toolchain: Apple clang with sanitizers and the static analyzer
xcode-select -p || xcode-select --install

# 2. cppcheck 2.22.0 from the tag (a package manager may ship another version)
cmake --version                 # needed for the build; install it first if missing
git clone --depth 1 --branch 2.22.0 https://github.com/danmar/cppcheck.git "$WORK/cppcheck-src"
cmake -S "$WORK/cppcheck-src" -B "$WORK/cppcheck-src/build" -DCMAKE_BUILD_TYPE=Release \
      -DFILESDIR="$WORK/cppcheck/share/cppcheck"
cmake --build "$WORK/cppcheck-src/build" -j
cmake --install "$WORK/cppcheck-src/build" --prefix "$WORK/cppcheck"
export PATH="$WORK/cppcheck/bin:$PATH"
shasum -a 256 "$WORK/cppcheck/share/cppcheck/addons/misra.py"   # must be 2955eca9...893d
rm -rf "$WORK/cppcheck-src"

# 3. Rust 1.96.1 + clippy, and the Miri nightly
rustup toolchain install 1.96.1 --profile minimal --component clippy
rustup toolchain install nightly-2026-09-23 --profile minimal --component miri
cargo +nightly-2026-09-23 miri setup

# 4. Kani 0.67.0
cargo +1.96.1 install --locked kani-verifier --version 0.67.0
cargo kani setup

# 5. Claude Code CLI 2.1.312, logged in to the owner's subscription
npm install --prefix "$WORK/claude-code" --no-fund --no-audit @anthropic-ai/claude-code@2.1.312
export PATH="$WORK/claude-code/node_modules/.bin:$PATH"
claude --version            # 2.1.312 (Claude Code)
# authenticate with the owner's subscription (CLAUDE_CODE_OAUTH_TOKEN from `claude setup-token`)

# 6. gates, in this order; each must pass before the next
python3 fxm.py check-tools            # every line "ok", exit 0
python3 fxm.py self-test --with-tools # all checks passed
python3 fxm.py check-tasks            # "0 failed, 0 skipped", exit 0

# 7. the pilot
python3 fxm.py matrix --pilot
python3 fxm.py report
```

If `check-tasks` reports a finding on a reference solution, fix the reference
in a reviewed PR before the pilot. The F1 references are the likely ones,
since cppcheck was not available where the harness was written. Fix it by
changing the reference, never the lint set. `frozen.sha256` changes with it.

## What the self-test covers

Without a model or a toolchain, the self-test checks:

- F0 is one call, and the loop stops at zero findings or at N = 10;
- findings and the previous code reach the next prompt;
- the argv: model id, effort, `--tools ""`, the schema, no bare mode,
  no ambient settings, and the prompt on stdin;
- no hidden file reaches any argv or stdin, at any level, for both tasks;
- a model swap, a usage limit or a CLI failure is could-not-run, and a
  transient failure is retried;
- the suppression scan;
- an edited Kani harness stops the run;
- the committed vectors equal a fresh generation;
- the Wilson intervals, the decision rule and the thesis verdict, on known
  values.

`--with-tools` adds the real oracle on the reference and the mutant through
the stub model in both languages. It also runs a violating-then-fixed answer
pair through the loop to a clean stop.
