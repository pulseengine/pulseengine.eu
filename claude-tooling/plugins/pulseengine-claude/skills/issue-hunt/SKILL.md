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

Keep a per-repo watermark in **`.claude/pulseengine/issue-hunt-state.json`**: the
timestamp the last successful hunt finished, per repo. Read it at the start of a
pass; write the pass's start time at the end — **only after the pass succeeded** —
so nothing is missed or double-processed.

**Verify the state file is actually git-excluded — don't assume `.claude/` is.**
Before the first write, confirm the path is ignored: `git check-ignore
.claude/pulseengine/issue-hunt-state.json` must print the path (exit 0). It has
been committed by accident once when only part of `.claude/` was excluded. If it
isn't ignored, add the rule (and `git rm --cached` any already-tracked copy)
before writing — a tracked state file leaks the loop's bookkeeping into every PR.

**Re-pull with a small overlap, then dedup — exact-boundary misses.** GitHub's
`updatedAt`/`createdAt` and your local clock can skew by seconds, and `>=` on an
exact watermark can drop an item that landed in the same second. Query from
**watermark minus ~60s** and dedup against what the last pass already processed
(by issue number + last-seen comment id, below) rather than trusting the boundary
to be tight. Cheap re-reads are fine; a silently skipped comment is not.

The state is more than one timestamp — keep, per repo:
- `watermark` — pass-start time of the last successful pass.
- `last_seen_comment_id` per touched issue — the highest comment id already
  digested, so a re-pull (or a self-echo, below) is recognized and skipped
  without re-triaging.
- **`pending_gates`** — open PRs this loop is waiting on, each as
  `{ pr, repo, watcher_run_id?, action_on_green }` (e.g. "merge", "tag vX.Y",
  "close #N"). A pass that opens a PR but can't land it yet (CI still running, a
  fork it must pause at) records the gate here instead of dropping it; the **next
  pass checks `pending_gates` first** and acts on any that went green — that's how
  a deferred merge gets owned across passes instead of forgotten.

First run (no watermark): bound the window explicitly — the last N days, or
"since the last release tag" — and **say which window you chose**. Don't silently
digest the entire backlog.

## Each pass

0. **Resolve `pending_gates` first.** Before pulling new work, check the gates the
   last pass left open: for each, look at the PR's current check status and act on
   `action_on_green` if it went green (merge / tag / close), or leave it and
   re-record if still pending. This is what makes a deferred merge get *owned*
   across passes instead of silently dropped.

1. **Pull what's new since the watermark** (from watermark − ~60s; see State).
   - New / updated open issues:
     `gh issue list --repo <R> --state open --search "updated:>=<WATERMARK>" --json number,title,updatedAt,labels,author`
     (a new comment bumps an issue's `updatedAt`, so this catches comment
     activity too, not just new issues).
   - New comments on each touched issue:
     `gh issue view <N> --repo <R> --json comments --jq '.comments[] | select(.createdAt > "<WATERMARK>")'`.
   - **Filter your own echoes.** This loop comments on issues (triage notes,
     "landed in rivet", "fixed in #NN") — and every such comment bumps `updatedAt`,
     so the next pass re-pulls the issue and sees *its own* comment as "new". Drop
     any item whose **only** post-watermark activity is a comment by the operating
     account, and skip any comment at or below `last_seen_comment_id`. Without this
     the loop chases its own tail and re-triages settled issues every pass. (Be
     careful at the boundary: with the −60s overlap, a real human comment can share
     the window with your echo — filter by *author + comment id*, not by time.)
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
   [`pulseengine-operating-contract`]). If you open a PR but can't land it this
   pass (CI still running, a release fork you must pause at), **record it in
   `pending_gates`** with its `action_on_green` — don't end the pass on the
   promise of a merge you didn't make.
5. **Advance the watermark** to this pass's start time, **and** update
   `last_seen_comment_id` for every issue you touched (so your own echoes and
   re-pulls are recognized next pass). Both only on a successful pass.

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
- **Re-digesting your own comments** — the loop's triage/status comments bump
  `updatedAt`; without the self-echo filter (step 1) it re-pulls and re-triages
  issues it just touched, chasing its own tail forever.
- **Dropping a deferred merge on the floor** — opening a PR you can't land this
  pass and not recording it in `pending_gates` means the next pass never checks
  it; the "fix" sits green-and-unmerged indefinitely.
