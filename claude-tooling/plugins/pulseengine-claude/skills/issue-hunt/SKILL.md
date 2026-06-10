---
name: issue-hunt
description: This skill should be used to run an incremental bug/feature hunt over a repo's issue tracker — pick up everything NEW since the last pass (new issues and new comments), digest and triage it, work the actionable items through the verification chain, and accumulate toward a feature release. Use it when the user says "hunt the issues", "do a bug/feature hunt", "look into the issues and work them", "loop through the issues", "digest the new issues and comments since last time", or wants a standing loop (via /loop or a scheduled agent) that drives the tracker toward releases. One invocation is one pass; the "since last time" watermark is what makes it a loop rather than a full re-scan. Composes with release-planning (land + ship), the feature loop, and the operating contract.
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# Issue hunt — the incremental bug/feature delivery loop

A standing loop you run repeatedly: each pass picks up everything new on the
issue tracker **since the last pass** — new issues and new comments — digests
it, works the actionable items through the chain, and accumulates toward a
**feature release**. The "since last time" watermark is what makes this a loop
and not a re-scan from zero every run. It is the tracker-facing front of
[`release-planning`]'s issue-driven delivery loop.

## State — the watermark (what makes it incremental)

Keep a per-repo watermark in **`.claude/pulseengine/issue-hunt-state.json`**
(git-excluded, same convention as the working-context checkpoint): the timestamp
the last successful hunt finished, per repo. Read it at the start of a pass;
write the pass's start time at the end — **only after the pass succeeded** — so
nothing is missed or double-processed.

First run (no watermark): bound the window explicitly — the last N days, or
"since the last release tag" — and **say which window you chose**. Don't silently
digest the entire backlog.

## Each pass

1. **Pull what's new since the watermark.**
   - New / updated open issues:
     `gh issue list --repo <R> --state open --search "updated:>=<WATERMARK>" --json number,title,updatedAt,labels,author`
     (a new comment bumps an issue's `updatedAt`, so this catches comment
     activity too, not just new issues).
   - New comments on each touched issue:
     `gh issue view <N> --repo <R> --json comments --jq '.comments[] | select(.createdAt > "<WATERMARK>")'`.
   - **State the count up front.** If it's large, process in priority order and
     say what you deferred — never silently truncate.
2. **Digest & triage each item** (the [`release-planning`] evaluate step — measure,
   don't guess):
   - classify: actionable **bug** / **feature request** / **optimization** /
     needs-info / duplicate / out-of-scope noise.
   - bug → reproduce and quantify before deciding; feature/optimization → what
     requirement or decision does it become, what's the measured benefit and the
     constraint it must not break.
   - a comment that changes an **in-flight** item's scope re-opens *that* item;
     it doesn't spawn a new one.
3. **Land actionable items in rivet, assigned to a release** — [`release-planning`]
   Part A: a requirement / decision / test, `release: vX.Y`, status, linked into
   the trace so a regression re-opens the right requirement. needs-info → ask on
   the issue and move on; duplicate → link and close; noise → leave it.
4. **Work them through the chain** — [`pulseengine-feature-loop`] /
   [`oracle-gate-a-change`] / [`proof-synthesis`], closing the V
   ([`traceability-audit`]). Ground every "fixed / done / passing" claim in the
   tool result; **never merge around a red or absent gate** (see
   [`pulseengine-operating-contract`]).
5. **Advance the watermark** to this pass's start time.

## The exit condition is a release, not an empty tracker

When the target release's rivet scope is all `verified` and the V is closed, cut
it via [`release-execution`] — then keep hunting for the next one. Given the
cadence, a single high-value fix can be its own release; a feature can accumulate
across several passes until its scope is complete. "Work on issues forever" has
no exit — the loop delivers *releases*, not activity.

## Running it as a loop

This skill is **one pass**. Invoke it repeatedly — e.g. `/loop <interval>
issue-hunt <repo>` for a cadence, or a scheduled agent for unattended runs. Each
pass is bounded (digest the new, work what's ready, advance the watermark); it
does not block forever. For unattended loops, follow the autonomous-run rules in
[`pulseengine-operating-contract`]: finish the work you start (don't end on a
promise), ground claims in tool results, and don't pause to ask permission
mid-loop for reversible, in-scope actions.

## Disposition (hybrid)

The **digest / triage** half is explorer work — judgment about what an issue
really is; give it scope and a capable model. The **deliver / release** half
routes through the driver skills — obedient, gated. Apply each disposition to its
half (see [`pulseengine-operating-contract`]).

## Anti-patterns

- **Re-scanning the whole backlog every pass** instead of using the watermark —
  wasteful, and it re-litigates settled issues.
- **Advancing the watermark before the work is done** — a crashed pass then skips
  items forever. Advance only on success.
- **Triaging without measuring** — a "bug" with no repro, or a "perf win" with no
  before/after number, isn't ready to work.
- **Acting on an issue without landing it in rivet** — untracked work is invisible
  to the release plan and resurfaces as a gate surprise.
- **Looping with no release target** — the loop's product is releases; an
  open-ended "keep working issues" never converges.
