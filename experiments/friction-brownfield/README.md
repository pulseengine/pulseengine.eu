# friction × model v2 (brownfield): task material checks

Pre-registration: [`docs/experiments/2026-11-friction-brownfield.md`](../../docs/experiments/2026-11-friction-brownfield.md).

- `cost.py`: the notional cost table of the pre-registration. Calls no API.
- `check_task.py`: the acceptance checks for one task, run on the bench
  machine against the private task material (see below).
- `tasks.sha256`: the sha256 of the task archive (first line: an
  uncompressed USTAR archive of the sorted files, mtime 0, uid and gid 0,
  mode 0644) and of every file in it, as it was when the acceptance checks
  ran. **An authoring snapshot, not a calibration freeze**: the
  pre-registration commits a separate freeze before each calibration round.
- `authoring/<task>.json`: how the task's code bases were written (Mistral
  Vibe version, model, auto-approve setting, prompt hashes, rounds, cost).

The task material itself (code bases, change request, hidden suites,
generator, prompts) is not in this repository. It stays private until the
full run is reported, so that it cannot reach a model's training data before
the run.

## check_task.py

```sh
python3 check_task.py self-test                    # no toolchain; also run in CI
python3 check_task.py all    TASK_DIR c rust       # the 10 checks, each its own process
python3 check_task.py check  TASK_DIR c 7          # one check; exit 0 pass, 1 fail, 2 could not run
python3 check_task.py negctl TASK_DIR c 7          # break check 7 in place, expect 1, restore, expect 0
```

The 10 checks and the pre-registration's potency bullets they implement
("The success oracle, independent of friction"):

| check | what | doc |
|---|---|---|
| 1 | baseline builds without warnings, passes the visible tests and the regression suite | bullet 1 |
| 2 | baseline fails the new-behaviour suite, and still fails it with the new names supplied (so the failure is behaviour, not only a missing name) | bullet 2 |
| 3 | reference builds, passes visible and both hidden suites, adds no new finding at the top analyser level, (Rust) passes every Kani harness | bullet 3 |
| 4 | invariant mutant passes the new-behaviour suite and fails the regression suite | bullet 4 |
| 5 | visible-pass mutant passes the visible tests and fails a hidden suite | bullet 5 |
| 6 | a probe on the reference gives a new finding from each real tool: B1 and B2 (C), B1, B2 and B3 (Rust) | bullet 6 |
| 7 | visible and hidden suites share no case; an independent sanity check of the vectors; every stored vector file is what the generator writes | bullet 7 |
| 8 | every name the hidden suites and Kani harnesses use that the baseline lacks is in the change request (found by compiling them against the baseline) | bullet 8 |
| 9 | the baseline prompt is under the 90K-token cap, by a pessimistic bound of 2 bytes per token plus 8K | bullet 9 |
| 10 | the feature-ablation split re-derives (strip of the authored tree equals the baseline; baseline plus reference equals the complete system), and the baseline's analyser noise is inside the task's noise budget | "Review is mechanical" |

Two parts of check 7 are stricter than the doc's wording and are stated here
so they can be argued with: disjointness is per case (a case is its sequence
of request frames; a follow-up read shared by two cases is not a shared
case), and the sanity check recomputes the expected 0x17 responses from the
spec's initial register values, so a generator that never exercises the
feature's ordering cannot pass.

**Negative controls.** `negctl` applies one in-place edit from the task's
private `negctl.json` (one per check), requires exit 1, reverses the same
edit, requires the file to be byte-identical to before and the check to
exit 0 again. Nothing is restored from version control.

**Finding fingerprint.** (tool, rule, file, flagged line text with whitespace
collapsed), compared as multisets. The doc's fingerprint also has the
enclosing function; check_task.py leaves it out.

Build directories go under `FXM_BUILD_DIR` (internal disk; see v1's
harness for why) and are removed after each check.
