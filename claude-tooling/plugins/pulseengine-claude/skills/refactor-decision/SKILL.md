---
name: refactor-decision
description: This skill should be used whenever an agent decides whether to stop patching and refactor, or is asked to "refactor X" or "tidy first". It does NOT apply in pulseengine/rivet or pulseengine/spar before 2027-02-01.
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# Refactor decision: when to stop patching, and how to refactor safely

## Scope: check this first

**Does not apply in pulseengine/rivet or pulseengine/spar before 2027-02-01 (pre-registered experiment, [`docs/experiments/2026-10-hotspot-trigger.md`](https://github.com/pulseengine/pulseengine.eu/blob/main/docs/experiments/2026-10-hotspot-trigger.md)). There, record nothing and change nothing under this skill.**
The experiment measures rivet's own fix-hotspot trigger against spar as the
control from 2026-11 to 2027-01 and promises no other process change in either
repository during the window. In those two repositories follow their own
process as if this skill did not exist: no trigger below fires, no decision is
recorded, and no comment cites this skill.

Run both checks before anything else in this skill:

```sh
# 1. Which repository: every remote, SSH and HTTPS, forks included (upstream).
git remote -v | grep -Eiq '[:/]pulseengine/(rivet|spar)(\.git)?/?[[:space:]]' && echo EXCLUDED-REPO
# 2. Which day, in UTC.
[[ "$(date -u +%Y-%m-%d)" < "2027-02-01" ]] && echo BEFORE-2027-02-01
```

If both print, stop here. The grep governs which repositories are excluded:
a remote naming pulseengine/rivet or pulseengine/spar, and nothing else.
Before 2027-02-01 the same holds when the change is a PR into pulseengine/rivet or pulseengine/spar opened from another checkout, and when the checkout has no remote at all. Recording a decision *in*
rivet the tool, from another repository, is fine; the exclusion is about the
two repositories.

## When

Each trigger names what counts as evidence that it fired. A trigger is a reason
to decide, and only (a), (b) and (d) are reasons to act.

### (a) Preparatory refactoring: the feature does not fit

The trigger is a feature whose diff would be tangled because the structure does
not fit it: the same decision edited in several places, a parameter threaded
through layers that do not use it, a branch added to code that should not know
about the feature. Kent Beck's own wording, in ["Tidy First
Example"](https://tidyfirst.substack.com/p/tidy-first-example) (Tidy First?,
2025-01-30): "For each hard change, make the change easy (warning, this
may be hard), then make the easy change." Martin Fowler's ["An example of
preparatory refactoring"](https://martinfowler.com/articles/preparatory-refactoring-example.html)
(2015-01-05) works one through.

**Make the change easy in its own behaviour-preserving step, then make the change.**
The first step is its own commit, or its own PR when the feature PR would
otherwise be hard to review. The tests are unchanged in that commit and green
before and after it. The feature then lands as a separate commit on top. The
evidence is the pair of commits and the two green runs.

### (b) A second copy of a rule, or a second path for one decision

The trigger is a change that would add a second (or third) copy of a rule or a
decision: a native mirror of a component's rule, a sibling component, a split
orchestrator, a legacy path kept next to the new one, a state such as "not
calibrated" encoded in two places. Adam Tornhill, ["Kill the
Clones"](https://adamtornhill.com/articles/aspnetclones/killtheclones.html)
(December 2015), measures this as change coupling: duplication matters when the
copies must change together, because "duplication of knowledge is always an
expensive one". Code that only looks alike and encodes different knowledge is
not this trigger.

**Delete the first copy, or name the one owner the others delegate to.**
The evidence is in the PR: either the old copy or path is deleted, or the other
copies call the named owner as thin adapters and a test exercises the rule
through the owner. In relay (pulseengine.eu#294) this was the strongest of the
backtested rules and cheap to check at review: its first firing would have
prevented 3 review findings and a later fix, and it fired live on 2026-10-28,
when "no calibration" encoded in two places made an uncalibrated vehicle
armable once two individually green PRs were combined in the merge queue.

### (c) A re-fix chain or a review cluster: decide, do not refactor

Two signals, both weaker than (b). **Rule A:** a second confirmed fix-of-a-fix
in one file within 60 merges. Confirmed means you read both fixes and the later
one repairs the earlier one's lines or its defect (blame the lines the fix
edits on its parent). In relay it was noisy: 1 of 6 firings was true. **Rule
D:** 3 or more findings in one file in one review. It is late, because the
defects have already merged, but in relay it was unambiguous.

**A fix-of-a-fix chain or a review cluster triggers a recorded decision, never a refactor.**
The decision is none, small or large, with a one-line reason. Prefer small when
it removes the defect class: delete a legacy path, or move a duplicated rule
into one owned API with the copies as thin adapters (in relay that took the rule
copies from 10 + 10 + 10 to 0, with behaviour byte-identical across 6,250 ticks).
Size alone is not a reason to split a file; in relay splitting the large file
was explicitly not recommended, because size was not the cause. A large
decision goes to the owner (see Recording).

### (d) Litter pickup in code you are already changing

Fowler names it in ["Workflows of
Refactoring"](https://martinfowler.com/articles/workflowsOfRefactoring/)
(2014-01-08). The trigger is a small, local defect of form (a misleading name,
dead code, a duplicated expression) inside a hunk the current change already
edits.

**Pick up litter only inside the code the change already touches.**
Keep it to the functions the diff already edits, in its own commit, with no new
abstraction and no rename that spreads to other files. Anything wider is
uninvited scope under the operating contract's "Do the simplest thing" and
needs the user's grant.

## How

**No refactor lands without evidence that behaviour did not change.**
- The tests that cover the code are unchanged in the refactor commit and green
  before and after it. If nothing covers it, add a characterization test first,
  as its own commit, and watch it pass on the old code.
- For numeric or control code, run old and new over the same inputs and compare
  the outputs exactly. relay's evidence was a differential run byte-identical
  over 6,250 ticks. A summary statistic is not evidence; the diff of outputs is.
- Name the oracle you used in the commit body, as [`oracle-gate-a-change`]
  requires for any change.

**Keep refactoring and behaviour change apart.** A refactor is its own commit
with a `refactor:` prefix, and it changes no test expectation. A commit that
does both cannot show which half broke something.

**Never refactor without a named purpose.** The purpose is one of the triggers
above plus what it enables or removes ("lets the feature touch one place",
"removes the second copy of the arm rule"). When the purpose is met, stop.

**"Refactor X" without a named purpose and a check is clarified, not executed.**
Ask what the refactor should achieve and how you will know behaviour held.
Jiang et al., ["Your Wish Is My Commit: Over-Compliant Refactoring in AI Coding
Agents"](https://arxiv.org/abs/2610.36346) (arXiv 2610.36346, 2026), repeatedly
asked Codex and Claude Code, across five models and over 3,000 turns, to
refactor further. None stopped once the code was clean: "Every model kept
editing, rewriting up to 31x the original codebase before first stopping", and
edits resumed even after a model had declared the task complete. A repeated "refactor further" with no
new purpose gets the same question, not another pass. Horikawa et al., ["Agentic
Refactoring: An Empirical Study of AI Coding Agents"](https://arxiv.org/abs/2511.04824)
(arXiv 2511.04824), found in the AIDev dataset's Java projects that agents'
refactorings lean slightly more than humans' toward low-level edits (27.6% vs
24.4%), led by Rename Variable and Change Variable Type, with limited measured
improvement from those edits, while medium-level refactorings showed "small but
statistically significant improvements in structural metrics". A rename sweep
is not a purpose.

**An agent's refactor PR is reviewed like any other change.** It passes
[`oracle-gate-a-change`] and, before it is reported as behaviour-preserving,
[`clean-room-verification`]. relay found nothing that caught defects arriving in
one large feature PR before a review did, so a large feature PR gets its review
before merge, not after.

## Merge queue: two greens can be red together

**A merge-queue ejection is a possible interaction defect, not a flake.**
Two PRs that are each green can be red together through a semantic conflict
with no textual one. In relay a struct grew a field and a sentinel value
changed meaning, and the "no calibration" state encoded in two places made an
uncalibrated vehicle armable once two such PRs were combined. Before
re-queueing an ejected PR, read what the other PRs in the same queue group
changed and whether they touch the same rule. A shared rule with two copies is
trigger (b). [`ci-status`] points here for queue ejections.

## Recording

No new state file. A decision is recorded where the work already lives:

- **On the issue or PR where the trigger fired**, as one line:
  `refactor-decision: trigger (a|b|c|d), decision none|small|large, reason: <one line>`.
- **In rivet**, where the repository has a rivet project whose schema has a
  `design-decision` type (`rivet schema list`): a small or large decision
  becomes a `design-decision` artifact linked to the requirement it serves.
  Ask rivet for the type and the link; do not hand-guess the store's shape.
- **In the working context**, only a pointer to that record, so the next
  session finds it.
- **A large decision, or any decision that widens scope, goes to the owner.**
  In an unattended session post it as a `needs-decision` through
  [`factory-notice`], with none, small and large as the options, and carry on
  with independent work. Never take it on the recommendation because nobody
  answered.

## Anti-patterns

- Refactoring automatically because a rule fired. Rules A and D ask for a
  decision; only the decision says whether to act.
- Splitting a file because it is long, when the defects come from a duplicated
  rule or a lifecycle bug that the split leaves intact.
- A refactor commit that also changes a test expectation.
- Keeping the legacy path "for now" next to the new one, with no owner named.
- Re-queueing an ejected PR as a flake without reading what it was combined
  with.
- Applying this skill in pulseengine/rivet or pulseengine/spar before
  2027-02-01.
