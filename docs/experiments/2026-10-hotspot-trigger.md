# Experiment: fix-hotspot trigger in rivet, spar as control

Pre-registered 2026-10-22, before the trigger exists. Published with the post
"Agents don't tidy up". The criterion below is bound by `claims.yaml`
(`EXPERIMENT-HOTSPOT-TRIGGER-PREREGISTERED`); changing a threshold means
changing that claim in a reviewed PR, which is the point.

## The change

One change: a fix-hotspot trigger in **rivet only**, as rivet-local
configuration, not in the pulseengine-claude plugin (the plugin also loads in
spar). When a source file collects more than a set number of fixes in a
window, the next fix to it opens a refactoring task instead of another spot
fix. No other process change in rivet or spar during the window.

## Window

The three calendar months after the month in which the trigger ships.

## Baselines, measured 2026-10-22

| measure | rivet | spar | source |
|---|---|---|---|
| `refactor:` share of PR commits, last ~90 merged PRs | 5 of 175 (2.9%) | 2 of 201 (1.0%) | GitHub REST `pulls/N/commits` |
| refactor share judged from diffs, sampled commits | 9% (n=45, 95% CI 4-21) | 3% (n=30) | `judge-batches.py` |
| feature share judged from diffs | 38% | 57% | `judge-batches.py` |
| `fix:` commits on `rivet-cli/src/main.rs`, 2026-08-01 to 2026-10-22 | 35 of 60 (12.8 per month) | n/a | `git log` |

## Criterion: the trigger counts as working only if all hold

1. rivet: `refactor:` share of PR commits in the window is at least 10%, over at least 100 PR commits.
2. rivet: `fix:` commits on `rivet-cli/src/main.rs` average at most 6.4 per month in the window (half the baseline), or the file no longer exists because it was split.
3. rivet: refactor share judged from diffs, on a fresh sample of the window, is at least 15%, and the feature share judged from diffs stays at or above 25%.
4. spar (control): `refactor:` share of PR commits in the window stays at or below 5%.

If 1 to 3 hold and 4 fails, the change was not the trigger. If any of 1 to 3
fails, the trigger did not work as specified, and the report says so.

## Not a criterion

Fix-on-fix. rivet's 5 of 21 has a 95% interval of 11 to 45%, so it cannot
decide anything at this sample size.

## Instrument check

Every monthly run first re-scores the classifier on its frozen references and
withholds the report if fix precision falls below 0.75 or recall below 0.70.
Haiku is the checker; it does not produce training data.
