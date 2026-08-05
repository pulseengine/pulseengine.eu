---
name: gate-potency
description: This skill should be used to audit whether a repo's EXISTING required CI checks can still fail — the vacuous-gate class, where a check runs, reports green, and cannot go red. Use it when the user says "audit our gates", "can our CI actually fail", "is this check real", "why did that slip through a green board", when inheriting or taking over a repo, at the campaign self-verify interval, and before a release whose evidence rests on CI being green. Presence is not potency — a non-empty required-checks list proves a gate exists, never that it bites. The method is negative control (inject a violation, confirm red) plus six mechanical audits for the ways a gate goes inert. Composes with oracle-gate-a-change (which covers wiring an oracle you are authoring), release-execution (fire before tagging) and repo-hygiene (same cadence).
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# Gate potency — can this check still go red?

[`oracle-gate-a-change`] covers the oracle you are *authoring*: write it, wire it, watch it flip
red→green. This skill covers the gate you **inherited** — green since before you arrived, trusted
forever, never re-proved.

> **The one principle.** A green dashboard over a non-empty required-checks list is not evidence.
> **Presence is not potency.** The question is never "does a required check exist" — it is
> "**can this listed, running, currently-green check still go red today?**"

Nothing re-validates a standing gate on its own. The failure modes are mundane, invisible to
reading, and produce *confident, documented, auditable green over unverified code* — the
highest-severity failure a verification methodology can have.

## Why this is a real class, not a hypothetical

Two sibling repos sharing no code independently grew the same four bugs. Field-observed in one
sweep: a mutation gate reading a path the tool never writes (**4 months of vacuous green; 210
survivors reported as 0**) — and the same bug again in a second repo on a **hard** gate, whose own
artifact recorded 5 survivors while CI printed 0; a format check covering 1 of 4 workspaces; a
changed-paths classifier failing open two ways, skipping 11 of 18 required contexts; a "fail on
sorry" gate where all 12 `sorry`s carried the self-exempting comment; 7 verification artifacts
citing tests that never existed; a crashed tool run scored as a good one.

Once the artifact under test is well covered, the residual defects **migrate into the instruments**,
where they are structurally hard to see — the instrument's entire job is to report "fine".

## The audit

Run over **every required status check** on the protected branch. For each one:

### 1. Negative control — the only real proof
Inject a deliberate violation and confirm the check goes **red**: an unformatted file, a surviving
mutant, a broken trace link, a `sorry` without the exemption, a deleted assertion. Restore
afterwards. Everything below is a cheap proxy; this is the actual evidence. Do it on a scratch
branch and record the run URL — that link *is* the potency evidence.

### 2. Reads what it writes
Assert the gate parses a path the tool actually produces. Compare the parsed path against the real
output/artifact layout, not against the docs. Version bumps silently relocate results files.

### 3. Scope covers the repo
Derive the target set mechanically — every `[workspace]` manifest, every `include_str!` input, every
crate — rather than trusting a hand-typed glob or a list that was correct when written.

### 4. Defined ⇒ enforced
A check that exists in the tool but appears in no workflow is not a gate. Grep the workflows for an
actual invocation. Registry entries, scripts and harnesses are inert until something runs them.

### 5. `skipped` ≠ `passed`
On GitHub a **skipped** required context satisfies the merge button. Therefore **any paths-filter is
a gate-disabler**, and its permissive branch is usually its *error* path (an errored `git diff`
skipping the matrix). Classifier error paths must fail **closed**. Treat every skipped required
context as unverified.

### 6. Missing evidence ⇒ red
An absent results file must fail the gate, never default to a clean count (`MISSED=0`). Likewise a
crashed or timed-out tool run is **not** a pass — check the exit code, not just the summary line.

## Output

A per-check verdict: **potent** (negative control went red — with the run link), **inert** (proved
it cannot fail — file it), or **unproven** (not yet negative-controlled). Report the counts up
front. `unproven` is an honest state; `potent` without a negative control is not.

For every inert gate, file the defect in the repo it belongs to, and record whether any released
claim rested on it — a vacuous gate usually means published evidence needs re-checking, not just a
CI fix.

## Cadence

Fire at the **self-verify interval** the feature loop already mandates, when **inheriting a repo**,
and **before a release** whose evidence rests on green CI. Pairs naturally with [`repo-hygiene`]
as a release-tail sweep. Negative controls are cheap enough for that cadence; if a repo's checks are
numerous, rotate — audit the checks guarding this release's claims first.

## Anti-patterns

- **Trusting a non-empty `required_status_checks.contexts`.** It proves a list exists. Three of its
  contexts can be vacuous and the invariant still passes.
- **Reading the workflow instead of breaking it.** Vacuous gates look correct in review — that is
  precisely why they survive. Only the negative control settles it.
- **Auditing the check you just wrote and calling the standing ones fine.** The inherited gates are
  the risk; they have had longer to rot and nobody has ever seen them red.
- **Accepting a green summary line.** Check the exit code and the artifact; a crashed run prints a
  clean-looking tail.
- **Fixing the gate and closing the issue.** If the gate was inert, ask what shipped behind it.

## Where this composes

- [`oracle-gate-a-change`] — authoring-time twin: wire the oracle and prove it fails *in CI*. This
  skill is the standing-gate counterpart.
- [`claim-verification`] — a claim bound to a vacuous gate is an unbacked claim; potency is what
  makes the evidence real.
- [`release-execution`] — run before tagging; a release whose gate was inert needs its claims
  re-checked, not just its CI repaired.
- [`report-tool-friction`] — an inert gate in a PulseEngine tool is friction; file it in that tool's
  own repo.
