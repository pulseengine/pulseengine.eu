# Exploratory arm: refactor-decision skill in relay

Pre-registered 2026-10-29, before the `refactor-decision` skill ships in the
pulseengine-claude plugin. This is an **exploratory** arm next to the
pre-registered hotspot experiment
([2026-10-hotspot-trigger.md](2026-10-hotspot-trigger.md)). It is not part of
that experiment's criteria, and nothing in it changes them. Its result is
reported as exploratory, never as confirmation.

## Why an extra arm

The plugin's `refactor-decision` skill applies in every repository except
rivet and spar, which stay as the hotspot experiment's treatment and control
until 2027-02-01. relay is the one repository with a measured baseline for
the skill's subject. Measuring it in the same window costs little and tells us
whether the skill changes anything there.

## The change in relay

- The `refactor-decision` skill, which covers preparatory refactoring for
  features, a second copy or path of a rule, recorded decisions on re-fix
  chains, and litter-pickup.
- relay's own local refactor trigger (rules C, A and D from #294, recorded
  in a git-ignored state file), already running before the window.

The two cannot be separated in relay. The arm measures their combination.

## Window

2026-11-01 to 2027-01-31, the same window as the hotspot experiment.

## Baseline

**The metric is the frozen tool's automated count, not a curated count.**

The instrument is relay's fix-of-a-fix detector, ported to Rust
(`tools/refactor-metrics/` in relay, its own workspace). It is frozen before
2026-11-01, once it reproduces the existing Python detector's output pair for
pair on the same 500 merges. It is identified by a content hash of its
sources, which stays stable through relay's squash merges, and by relay's
`main` commit once merged. Both are recorded here when available.

| measure | baseline | status |
|---|---|---|
| **fix-of-a-fix pairs, automated count of the frozen tool, per 100 first-parent merges** (the metric) | the Python detector reports **24 raw pairs** in 500 first-parent merges (2026-04-12 to 2026-10-28), i.e. 4.8 per 100 | to be restated from the frozen Rust tool on the same 500 merges before 2026-11-01. That restated value is the baseline. |
| fix share of merges | 78 of 500 (15.6%) overall; 23 to 51% per release since v1.130 | `fix`/`revert` subjects; the 3 hand-added fixes are excluded from the metric |

The figure published in pulseengine.eu#294, 16 re-fixing commits, is **context
only**. It came from manual curation: 3 fix commits added by hand that the
subject rule misses, 16 of the 24 pairs read at line level, 4 rejected as false
positives, and 8 not sampled. The window is measured only by the frozen tool,
without curation, so the two counts are comparable.

## Measures in the window

1. Fix-of-a-fix pairs per 100 first-parent merges: **the frozen tool's
   automated count**, with no manual curation. Any change to the tool during
   the window is reported, not absorbed. A curated count may be reported
   alongside as context only.
2. Fix share of first-parent merges, using the same subject rule.
3. Recorded refactor decisions (none / small / large), counted by trigger and
   outcome.
4. Rule C firings, each with whether the copy was removed or given a single
   owner.

## Expected direction, stated in advance

- **Measure 1:** below the baseline that the frozen tool restates for the same 500 merges.
- **Measure 4:** most rule C firings end with one owner.
- **No expectation is stated for the fix share.** Part of its earlier rise was
  a change in labelling style.

A result in the opposite direction is reported as such.

## Limits

- One repository, no control, and no randomisation.
- The detector has measured precision of about 75% and poor recall. Using the
  same tool on both sides keeps baseline and window comparable, not exact.
- relay's development phase may differ between the baseline period and the
  window.

This arm can show a direction worth testing properly. It cannot show that the
skill caused it.
