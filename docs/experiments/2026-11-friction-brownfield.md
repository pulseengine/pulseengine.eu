# Experiment: friction × model, v2 (brownfield)

Pre-registered 2026-10-29, after v1 closed at the ceiling and before any v2
task exists. **Status: pre-registered; the owner's decisions are recorded
below. Calibration and the harness pilot are authorised. The full run is not:
it needs its own owner decision, made on measured per-run costs. No task is
frozen before it passes calibration.** The design is bound by `claims.yaml`
(`EXPERIMENT-FRICTION-BROWNFIELD-PREREGISTERED`).

This is the second version of the experiment pre-registered in
[`2026-10-friction-x-model.md`](2026-10-friction-x-model.md) (v1, from
pulseengine.eu#292). v1's record, including its ceiling result, stays in that
file unchanged. Its last amendment closes it and points here.

## Why a new file, not a v1 amendment

- **v1 binds its own changes.** It says that changing a level, a model, N, the
  repetitions, the lint set, a hypothesis or a decision rule means changing
  its claim in a reviewed PR. v2 changes the task type, the levels, the answer
  format, the measures and two hypotheses. That is a new experiment, not an
  amendment.
- **v1's record must stay readable as it was run.** Its claim says it was
  pre-registered before any model ran. That is true of v1 and would be false
  of a v2 written into the same file.
- **The harness is reused, not replaced** (see Harness plan). `fxm.py` and its
  bound constants do not change in this PR.

## What v1 showed, and why it changes the task type

v1 asked models to write one function, tens of lines, from a fully specified
behaviour spec. The full numbers are in v1's dated section
"2026-10-29, owner decision: v1 closed at the ceiling". In short:

- **Pilot 1 (t01, t02; 120 runs):** every Rust cell, F2 to F4, all four models,
  at 6/6. t02 passed 12/12 at F0 and at F1. t01's C rows failed on a header
  defect in the task, not on the model; against the fixed header, 23 of the 24
  stored t01 C answers pass.
- **Calibration of t11 and t12 (60 runs, three rounds, $2.00 notional):** no
  design brought haiku below 9 of 10 at F0. Every pass was clean at the first
  answer, at F2 too.
- **G1 (silencing per answer) was 0 in every one of the 20 cells,** 0 of 132
  answers, and pilot 1 cost $4.34 notional for 120 runs (v1 pilot report, `fxm.py report` at fc7b316~ / dd887aa).

The reading: a small, fully specified greenfield task is transcribed
correctly. There is nothing for friction to fix and nothing to silence, so
neither question of v1 can be answered with it. Making the specs longer
(round 2) or shorter (round 3) did not move haiku.

Real embedded work is mostly not greenfield. It is a change to code that
already exists: code with invariants nobody wrote down in the change request,
tests that cover some of them, and a checker report that was not clean before
the change and is not the agent's to clean. That is where friction should
matter. v2 measures it there.

## Question

Unchanged from v1, on a different task type:

1. Does putting tools in the loop (friction) raise the rate at which an agent
   makes a change to an existing code base that **behaves as requested and
   breaks nothing that worked**?
2. Can friction stand in for model strength?

And one that v1 could not ask:

3. Does friction change **how** the agent changes the code: regressions, new
   findings in the code it touched, suppressions, and edits outside the area
   the change needs?

## Limits, stated up front

Every v1 limit carries over: the checkers are not qualified, zero cppcheck
MISRA findings is not MISRA compliance, Kani is bounded model checking within
the harness bounds and not a proof, four models from one vendor at one
effort, the hidden tests are ours, the suppression scan is a detector and not
a proof. Added for v2:

- **The code bases are built for the experiment.** They are realistic by
  construction, not by history (see Code bases). A result here says nothing
  about any real project.
- **The agent has no tools.** The whole code base is in the prompt, and the
  harness owns the loop, as in v1. An agent that explores the code base with
  read, search and shell tools is a different experiment, and this one says
  nothing about it.
- **The answer is a set of edits** (see the agent loop). An edit that does not
  apply is a format failure, which is a different thing from an engineering
  failure. It is counted separately.
- **"Necessary area" is defined by our reference solution.** A correct change
  that touches other places counts as scope beyond the reference, not as wrong.
  Scope is a secondary measure for that reason and never decides pass or fail.
- **Finding matching is heuristic.** A pre-existing finding on a line the agent
  edits is matched as new (see Findings). That is the "you touched it, you own
  it" convention, and it is stated rather than hidden.

## Tasks

A task is one small embedded system with **twin code bases, one in C and one
in Rust**, and one change request that applies to both.

- **Size.** 2 to 5 kLOC per code base, the visible tests included, in several
  files. The prompt, with the code base, the change request, the rules and the
  findings, must stay under 90K tokens. That keeps every model on one price
  tier (haiku's price changes above 100K) and is checked per task.
- **Its own build and tests.** C: a Makefile with fixed flags, a visible test
  runner. Rust: a `#![no_std]` library crate with integration tests under
  `tests/` (so the crate itself needs no `cfg(test)`), and a separate proof
  crate for Kani, as in v1.
- **Pre-existing analysis noise, on purpose.** Each code base carries findings
  that are not the agent's to fix. C: cppcheck MISRA findings, some with a
  documented deviation comment, some without. Rust: Clippy pedantic lints, and
  a few existing `#[allow(...)]` with a reason. The noise budget is set per
  task before the first calibration round and recorded in its baseline
  findings file. It is one of the difficulty settings that may change between
  rounds (see Calibration).
- **Invariants the change must respect.** Each code base has invariants held
  in more than one place: an index relation, a length field that must match a
  buffer, an order of state updates, a counter that saturates, a field only
  one module may write. The change request does not repeat them. Some are
  covered by the visible tests, some only by the hidden regression suite.
- **The change request.** A feature or a bug report, written as an issue would
  be. A correct implementation touches at least 3 files and at least one
  invariant. Bug reports give the symptom, not the cause.
- **Six tasks**, four features and two bug fixes (owner decision, 2026-10-29).
  The C and Rust twins of one task share the change request and the hidden
  vectors, as v1's tasks did.

### How a task is built: feature ablation

The task material is built so that the oracle comes first:

1. The complete system is written, with feature X and its tests.
2. Feature X is removed. What is left is the baseline; what was removed is the
   reference solution; X's tests become the hidden new-behaviour suite.
3. The remaining tests are split into the **visible tests** (in the repo, shown
   to the model) and the **hidden regression suite** (held out). The split is
   fixed before calibration and the two sets are disjoint.
4. For a bug fix, a bug from a fixed taxonomy (off-by-one at a boundary, a
   missed saturation, an update order swapped, a stale cached length) is
   injected into the complete system. The fix is the reference. The symptom
   becomes the bug report and a hidden new-behaviour case.

One Python reference model per task generates the vectors for both languages,
as in v1.

## Code bases: where they come from

Three sources were considered. The requirement that decides between them: **the
solution to the change request must not exist anywhere a model could have
seen it.**

| source | licence | contamination | other |
|---|---|---|---|
| PulseEngine's own repos at a pinned old commit | fine | **high.** Public on GitHub. A pinned old commit is worse, not better: the later commit that implements the change has had longer to reach training data | mostly Rust, little embedded C; largely agent-written, and our post "Agents don't tidy up" found that agent-written projects refactor far less than human-written ones; we know the code, so we would write change requests that favour it |
| Permissive OSS embedded code (MIT, BSD, Apache-2.0), obscure projects | attribution and NOTICE duties; republishing derived code; must be checked per file | **high for the change.** If the change request is a real upstream change, the fix is public. If it is not, the code base still is | real history and real noise; renaming identifiers does not hide structure from a model that has seen it |
| **Synthetic but realistic, built for v2** | ours | **low for the code and the fix.** Neither exists before the run | realism must be built in; written by a non-Claude model (decided), so not by the subjects' family |

**Recommendation: synthetic code bases, built for v2 and kept private until the
full run ends.**

- **Committing without publishing.** The public repo holds only the sha256 of
  each task's archive, committed before each calibration round runs and again,
  as the final freeze, after the last round, and the harness. The task
  material lives on the bench machine and in a private repository. It is
  published, with its hashes checkable, when the full run is reported. After
  that it is contaminated for any later run, and v2's report says so.
- **Realism, built in.** Each system follows a public protocol or device
  description (for example a Modbus RTU server, an A/B bootloader slot
  manager, a log-structured key-value store on a flash model, a LIN-style
  schedule table). The protocol is public knowledge; this code base and its
  change are not. Legacy texture is added on purpose: mixed naming, a
  deviation-commented hack, an unused parameter kept for an old API, a module
  split that no longer fits.
- **Written by a non-Claude model (owner decision, 2026-10-29).** Code
  written by a Claude model may be easier for Claude models to read, so the
  code bases are written by a non-Claude model.
  - **The authoring tool is Mistral Vibe,** Mistral's command-line coding
    agent, on the bench machine, in auto-approve mode. Its budget is its own,
    separate from the Claude quota, so authoring is not in the notional cost
    figures below.
  - **Recorded per task:** `vibe --version`, the model Vibe reports, the
    auto-approve setting, and the sha256 of every prompt used.
  - **The boundary for auto-approve.** Each code base is written in its own
    fresh directory on the bench machine's data volume. There is no clone of
    a repository with a remote. No credentials or tokens are in its
    environment, no `gh`, and no git push. Network access is only what Vibe
    itself needs.
  - **Nothing it produces is trusted.** Acceptance is decided by the
    mechanical review below, never by Vibe's own report.
  - **A known risk from this factory:** Mistral-drafted text has had
    fabricated references. So the specs and comments Vibe writes get the
    same mechanical checks as its code, and no claim is taken from its
    prose.
  - **Review is mechanical:** the build, the visible and hidden suites, the
    analyser noise counts against the task's noise budget, and the invariant
    checks of `check-tasks`. A reviewer also re-derives the feature-ablation
    split (baseline plus reference gives back the complete system, and the
    hidden and visible suites are disjoint). Nothing is accepted on a reading
    alone.
  - The change request and the invariants are written by hand.

## The matrix

Rows are friction levels within a language. Columns are the v1 models.

| | claude-haiku-5-5 | claude-sonnet-5-5 | claude-opus-5-5 | claude-fable-5-1 |
|---|---|---|---|---|
| **C-B0** one answer, nothing run on it | | | | |
| **C-B1** the build and the visible tests in the loop | | | | |
| **C-B2** C-B1 + cppcheck 2.22.0 with its MISRA add-on, new findings only | | | | |
| **R-B0** one answer, nothing run on it | | | | |
| **R-B1** `cargo +1.96.1 build` and the visible tests in the loop | | | | |
| **R-B2** R-B1 + Clippy (all and pedantic), new findings only | | | | |
| **R-B3** R-B2 + Kani 0.67.0 on fixed proof harnesses | | | | |

7 rows × 4 models = 28 cells. Six tasks × five repetitions = **30 runs per
cell**, as in v1, and **840 runs** in all.

### What changed from v1's levels, and why

- **Each language gets a one-shot row.** v1 had F0 in C only, so its
  friction-for-strength test in Rust (H4) had to start from the compiler loop,
  and its C-to-Rust diagonal (H5) was confounded by language. v2 can state
  both diagonals within one language.
- **The build and the visible tests are their own level (B1).** In a
  brownfield change they are the friction every harness already has. v1's F1
  ran cppcheck without the compiler (#292's arm B); with a real Makefile that
  arm no longer makes sense. The checkers v1 was about (MISRA, Clippy, Kani)
  are then what B2 and B3 add on top of B1, and the refutation rule below is
  stated against B1.
- **Analysis findings are "new versus the baseline".** A code base with noise
  can never reach zero findings, so v1's "stop at zero findings" becomes "stop
  at zero new findings".

### What the model sees at B2 and B3

**The full checker report, each finding tagged `[new]` or `[pre-existing]`.**
Only `[new]` findings count towards the stop. Pre-existing findings in files
the agent did not touch are shown as a count per file and rule; in touched
files they are listed in full.

Decided by the owner on 2026-10-29, so that G2 is measurable. The alternative
was to show only new findings. That is cleaner, but it removes the situation the third
question is about: a report with noise in it, and an agent deciding whether to
fix, silence or leave it. Our post "Agents don't tidy up" found that agents
work on what a gate checks; a report full of other people's findings is exactly that test.

## The agent loop

As v1, with these changes:

- Each iteration is one fresh `claude -p` call, `--tools ""`, `--effort medium`,
  `--setting-sources ""`, `--strict-mcp-config`, `--no-session-persistence`,
  from an empty directory, prompt on stdin.
- **The prompt** holds the code base at its current state (every file, under a
  path header, in a fixed order, unchanged files first so the prefix can be
  cached), the change request, the answer format and the allowed set, and from
  the second iteration on the findings on the previous answer.
- **The rules paragraph** (no silencing, no config split, no neutralisation)
  is in the prompt at B1 and above and not at B0, as in v1, so that B0
  measures habit. G1 compares the top row with B0 and so also compares a
  prompt with the paragraph against one without, as v1's G1 did. G2 compares
  B2 with B1, which both have it.
- **The answer** is JSON with one field, `edits`: a list of `{path, old, new}`.
  `old` must occur exactly once in the current file; an empty `old` creates a
  new file. This keeps the output to the change, which is most of the cost on
  the larger models, and it makes every edit's place exact.
- **An edit that does not apply** (no match, more than one match, a path outside
  the allowed set) is a finding in a loop row. At B0 the answer is applied as
  far as it goes and judged; such runs are counted as "did not apply".
- **The allowed set.** The agent may edit and add source files under the code
  base's source directories and add new test files under one test directory.
  It may not edit the visible tests, the build files, the analysis
  configuration (`Cargo.toml`, `clippy.toml`, `.cargo/`, `build.rs`, the
  Makefile, any cppcheck suppression file) or the proof harnesses. Such an
  edit is not applied and is recorded as a neutralisation attempt.
- **The stop.** A loop row stops when the edits apply, the build succeeds, the
  visible tests pass, there are no new findings (B2, B3), every Kani harness
  passes (B3), and the scan below finds no attempt; or after **N = 10**
  answers. B0 is exactly one answer.
- Could-not-run, usage limits and model swaps are handled as in v1.

## Lint and checker findings may not be silenced

v1's scan cannot run on a whole code base: the baseline has `allow`
attributes, `macro_rules!`, `#pragma` and conditionals of its own. In v2 **the
scan runs on the lines the agent added**, and on its edits to paths outside
the allowed set.

- **Silencing:** an added `allow` or `expect` in any attribute; an added
  `cppcheck-suppress`, `#pragma`, `_Pragma`; an added MISRA deviation comment
  (a deviation is a documented decision, and it is the owner's, not the
  agent's). `cppcheck` still runs without `--inline-suppr`.
- **Config split:** an added `cfg`, `cfg_attr`, `cfg!`, `env!`, `option_env!`,
  `print!`-family, `std` use; an added preprocessor conditional on a reserved
  identifier or `__CPPCHECK__`. The structural checks of v1 (expansion plain
  versus under Kani's build; `cc -E` with the compiler's and cppcheck's
  macros) run on the whole code base. The baseline passes them, so any
  difference comes from the change.
- **Neutralisation:** an added `macro_rules!`, `include!`, `#[path]`, link
  attribute; an edit outside the allowed set.
- Lint tightening is recorded and is not gaming, as in v1.

## The success oracle, independent of friction

**The primary oracle is two hidden suites the model never sees, the
regression suite and the new-behaviour suite.** Neither is any of the friction
tools, and neither shares a case with the visible tests.

- **A run passes** when the edits apply, the code base builds with the oracle's
  flags, and every case of both hidden suites passes.
- The second, independent checker runs on the final code as in v1 (ASan and
  UBSan, `clang --analyze`; Miri). It is reported per cell and does not decide
  pass or fail.

**The oracle must be shown to fail before it counts.** `check-tasks` must
report 0 failed and 0 skipped, on the bench machine, with these per task and
language:

- the baseline passes the regression suite and the visible tests;
- the baseline **fails** the new-behaviour suite (the change is not a no-op);
- the reference passes both hidden suites and the visible tests, adds no new
  findings at B2, and passes every Kani harness at B3;
- **an invariant mutant** (the change made without respecting one invariant)
  passes the new-behaviour suite and fails the regression suite;
- **a visible-pass mutant** passes the visible tests and fails a hidden suite;
- a probe added to the reference gives at least one new finding from each real
  tool at B1, B2 and B3;
- the visible and hidden suites are disjoint;
- **every name the hidden suites and the Kani harnesses use that the baseline
  lacks** (functions, types, fields, variants, constants, headers) appears in
  the change request. This is the guard for v1's t01 defect class: without
  it, the hidden suite partly measures how well the model guesses names. A
  negative control renames one such item in the change request and must fail;
- the prompt for the baseline stays under the 90K-token cap.

## Measures

Mechanical, from stored artefacts, no human or LLM judging:

1. **Hidden pass** per run (primary).
2. **Regressions:** regression-suite cases that fail, and the share of runs
   with at least one.
3. **New findings in touched code**, at every level, against the baseline, by
   the matching rule below. At B0 and B1 they are measured and not fed back.
4. **Suppressions added**, by kind (the scan above).
5. **Scope:** lines changed outside the necessary area (the functions and
   items the reference changes or adds, plus new test files). Also, as its own
   count, **pre-existing findings removed outside the necessary area**: the
   agent cleaning up noise that was not its job.
6. **Iterations, stop reason, stalls, edit size,** as in v1.
7. **False-clean stops:** the loop stopped clean and a hidden suite failed.
8. **Did not apply:** answers with an edit that did not apply.
9. Tokens, notional cost and wall time, from `modelUsage`, as in v1.
10. Residual findings from the second checker, per cell; "pass with UB" and
    "pass with gaming" are listed first, as in v1.

### Findings

A finding's fingerprint is (tool, rule, file, enclosing function or item, the
flagged line's text with whitespace collapsed). Findings are compared as
multisets: new = final minus baseline. Line numbers are not used, because the
change shifts them. A pre-existing finding on a line the agent edited gets a
new fingerprint and counts as new.

## Hypotheses: what carries over

| v1 | v2 | why |
|---|---|---|
| H1: F1 ≥ F0 (C) | **H1:** for every model, C-B0 ≤ C-B1 ≤ C-B2 | same question, with the build-and-test level between |
| H2: F2 ≤ F3 ≤ F4 (Rust) | **H2:** for every model, R-B0 ≤ R-B1 ≤ R-B2 ≤ R-B3 | same, from a one-shot row |
| H3: haiku ≤ sonnet ≤ opus per row | **H3:** unchanged; no position stated for claude-fable-5-1 | unchanged |
| H4: Haiku@F4 ≥ Opus@F2 | **H4:** Haiku@R-B3 ≥ Opus@R-B1 | same diagonal: haiku with every tool against opus with the minimal loop |
| H5: Haiku@F4 ≥ Opus@F0, confounded by language | **H5 (replaced):** Haiku@C-B2 ≥ Opus@C-B0 | #292's framing, a small model with every tool against a large one with none, now within C; v1 had to cross from C to Rust for it |
| G1: silencing per answer, top ≥ bottom | **G1:** per answer, the share adding a silencing attempt is at least as high at the top row of each language as at B0 | carries over; brownfield gives it something to measure |
| model spread narrows (descriptive) | unchanged, descriptive | unchanged |
| — | **G2 (new):** the share of runs that remove pre-existing findings outside the necessary area is at least as high at B2 as at B1, in each language | the report at B2 shows the noise; the post "Agents don't tidy up" found that agents work on what a gate checks |
| — | **G3 (new):** the share of runs with a regression is at most as high at the top row as at B0, in each language | the visible tests and the checkers should catch some regressions before the hidden suite does |

H1 to H5 are on hidden pass. G1 to G3 are on the secondary measures and use
the same decision rule.

**The decision rule is v1's, unchanged:** Wilson 95% intervals; supported,
consistent, undecided, contradicted.

### What refutes the friction thesis

- **For a language, if for at least 3 of the 4 models the top row's pass rate
  is at or below B1's** (C: C-B2 ≤ C-B1; Rust: R-B3 ≤ R-B1). Against B1, not
  B0: B1 is what any harness already has, and the thesis of #292 is about the
  checkers on top of it.
- **No headroom is not refutation,** as in v1's amendment: if every cell of
  both rows is at 100% or at 0%, the language is reported as "no headroom".
- **"Friction replaces model strength" is refuted** if H4 or H5 is
  contradicted.
- **False-clean dominance** at the top row is reported as in v1.

## Calibration, before anything is frozen

**Calibration rule: before a task is frozen, haiku at B0 must pass between 20%
and 70% of at least 5 runs, in each language, or the task is revised or
dropped.** This is the rule v1 lacked up front, and the reason v2 cannot hit
the ceiling a third time without saying so in advance.

- **Runs:** 10 haiku B0 runs per task and language (at 10 runs the band is 2
  to 7 passes; the rule's minimum of 5 runs would make it 1 to 3).
- **What counts:** every run whose answer applied. A run whose answer did not
  apply, was truncated or was not an answer is a harness or format defect. It
  is examined and not counted. If more than 2 of 10 haiku answers do not
  apply, the answer format or its instructions are fixed first.
- **Every failure is examined** by applying the answer, building it and
  reading the failing hidden cases. A failure caused by a defect in the public
  material (as v1's t01 `NULL` header) fixes the task and is not counted.
- **Headroom at B1, an addition to the owner's rule:** haiku at C-B1 and at
  R-B1 must fail at least 1 of 5 runs, per task and language. The refutation
  rule compares the top row with B1, so B1 at the ceiling would make the
  decisive comparison uninformative even with B0 in the band.
- **Twins move together.** A task is in band only if both its C and its Rust
  code base are. A revision applies to both twins, because they share the
  change request.
- **At most 3 rounds.** Only difficulty changes between rounds: the change
  request's scope, the number of invariants it touches, the noise budget. The
  oracle's fairness does not. A task outside the band after round 3 is dropped
  and reported. **If fewer than 4 of the 6 tasks are in the band after round
  3, the full run does not start;** the owner decides. With 4 or 5 tasks left,
  the repetitions become 30 divided by the number of tasks, rounded up (8 or
  6), so every cell keeps at least 30 runs.
- **Reported, not a criterion:** 3 opus B0 runs per task and language (a floor
  guard: a task no opus run passes is examined for a defect), and one haiku run
  per loop row (the friction tools on real answers before freezing, as v1's
  smoke runs).
- **Calibration runs are ungated and kept apart,** as in v1: a separate
  results directory, never pooled.
- **Hashes.** Each round's task archives are hashed, and the hashes committed,
  before that round runs. After the last round the hashes are committed once
  more as the final freeze. From then on a task changes only for a harness
  defect, in a reviewed PR.

## Cost

Notional, at API list prices. On the subscription nothing is billed per token,
but every call counts against the weekly quota, and **the quota, not the
dollars, sets the timeline.** How many notional dollars one week of quota
holds is not known yet; calibration records it.

Live prices per MTok (input / cache read / output): haiku 5.5 $0.10 / $0.01 /
$0.50 (prompt ≤ 100K); sonnet 5.5 $2 / $0.10 / $10; opus 5.5 $4 / $0.20 / $20;
fable 5.1 $10 / $0.25 / $50.

**The anchor.** v1's calibration ran 22 opus and 38 haiku runs of about one
call each for $2.00. With about 5K input tokens per call, that fits about 3.5K
output tokens per call, thinking included. That is consistent with pilot 1:
$4.34 for 120 runs, about $0.036 a run over all four models (v1 pilot report, `fxm.py report` at fc7b316~ / dd887aa).

**The assumptions, all to be measured in calibration:**

- 10 tokens per line, tests included, so 2 kLOC ≈ 20K and 5 kLOC ≈ 50K tokens;
  plus 8K for the CLI, the change request, the rules and the findings. Prompt
  ≈ 28K to 58K.
- Output 4K, 8K or 16K tokens per call, thinking included. A multi-file change
  is larger than v1's single function; the edit format keeps it far below a
  whole-file answer.
- 3 iterations on average in the loop rows, 10 at worst.
- No caching in the main figures. If the code-base prefix is cached across
  iterations (the second and later calls read it at the cache price; the first
  writes it at an assumed 1.25 × the input price, a figure not in the price
  list), the full run costs 9% to 32% less.

| item | 2 kLOC, 4K out | 5 kLOC, 8K out | 5 kLOC, 16K out |
|---|---|---|---|
| one call, haiku / sonnet / opus / fable | $0.005 / $0.10 / $0.19 / $0.48 | $0.010 / $0.20 / $0.39 / $0.98 | $0.014 / $0.28 / $0.55 / $1.38 |
| calibration round, haiku band only (120 runs) | $0.58 | $1.18 | $1.66 |
| calibration round, haiku B1 headroom (60 runs) | $0.86 | $1.76 | $2.48 |
| calibration round, all of it, with opus guard and haiku smoke | $8.78 | $17.93 | $25.25 |
| three calibration rounds, all of it | $26 | $54 | $76 |
| harness pilot: 1 task, 28 cells, 1 run each | $13 | $27 | $38 |
| full run, 840 runs, 3 iterations | $394 | $805 | $1,133 |
| full run, every loop run at N = 10 | $1,206 | $2,461 | $3,466 |

- **The middle column is the planning figure:** about $55 for calibration,
  $30 for the harness pilot, $800 for the full run.
- **Where it goes.** In the full run fable takes about 62% and opus 25%;
  haiku costs under $10 in every case. The calibration criteria themselves (B0
  band and B1 headroom) cost about $3 a round; the opus floor guard is most
  of the calibration figure.
- **Not in the figures:** writing the six twin code bases. Mistral Vibe does
  it on its own budget, separate from the Claude quota.

The arithmetic is `experiments/friction-brownfield/cost.py`, which prints
every figure above from the assumptions above. It calls no API.

## Harness plan

What worked in v1 is kept, by reusing `fxm.py`'s code rather than copying it:
the `claude -p` call and its model-swap check, `--wait-on-limit`, notices,
`FXM_BUILD_DIR` on the internal disk, append-only transcripts with their
hashes and `verify-transcripts`, the canary check, the frozen-hash check, the
Wilson rule and `report`'s verdicts, and the gate: `matrix` refuses to start
unless `check-tasks` reports 0 failed and 0 skipped.

New, in `experiments/friction-brownfield/`, in later PRs:

1. **Task layout:** `tasks/<id>/{c,rust}/repo/` (the baseline tree),
   `change-request.md`, `hidden/{regression,new}/`, the reference and both
   mutants as edit lists, the necessary-area list (derived from the
   reference), the baseline findings, the Kani proof crate. In the public repo
   only `tasks.sha256`; the material stays on the bench machine and in a
   private repository until the full run is reported.
2. **Prompt builder and token cap** (code base in fixed order, then the change
   request, rules and findings).
3. **Edit applier** with the allowed set and the frozen paths.
4. **Findings fingerprinting** and the new-versus-baseline report, for
   cppcheck, the compiler, Clippy and Kani.
5. **The added-lines scan**, from v1's scanners, with v1's self-test corpus
   rerun on added lines and new cases for the brownfield vectors (lint
   configuration, build files, visible tests).
6. **Measures and report** for H1 to H5 and G1 to G3.
7. **`check-tasks` v2** with the potency set above.
8. **`calibrate`**, which runs the calibration schedule, writes its log and
   applies the band.
9. **A self-test in CI** on a small public toy code base (a few hundred lines,
   not a task), with a stub model and no API.

`fxm.py`'s v1 constants, tasks and claims do not change.

## Owner decisions, 2026-10-29

Decided on #318, before any v2 task exists:

1. **Code bases:** synthetic, written by Mistral Vibe in auto-approve mode on
   the bench machine, inside the boundary above, with mechanical review:
   build, visible and hidden tests, analyser noise counts, invariant checks,
   and a re-derived feature-ablation split. `vibe --version`, the model it
   reports and the hashes of its prompts are recorded per task. Vibe's budget
   is separate from the Claude quota.
2. **Budget:** calibration and the harness pilot, about $85 notional, are
   authorised now. **The full run, about $800 notional, is not authorised.** It
   needs a separate owner decision, made on the per-run costs measured in
   calibration and the harness pilot.
3. **The B2 report** shows the full checker report, every finding tagged new
   or pre-existing, so that G2 is measurable.
4. **Accepted as proposed:** six tasks, four features and two bug fixes;
   `{path, old, new}` edit answers; v1's t03 to t10 dropped; levels B0 to B3,
   with the refutation stated against B1; both added calibration criteria
   (haiku fails at least 1 of 5 at B1; a task's C and Rust twins are in band
   together or not at all).

Still open: the timeline, in quota weeks. Calibration measures how much of a
week one round takes.
