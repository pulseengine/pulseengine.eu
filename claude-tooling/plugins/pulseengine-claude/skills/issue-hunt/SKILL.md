---
name: issue-hunt
description: This skill should be used to run an incremental bug/feature hunt over a repo's issue tracker — pick up everything NEW since the last pass (new issues and new comments), digest and triage it, work the actionable items through the verification chain, and accumulate toward a feature release. Use it when the user says "hunt the issues", "do a bug/feature hunt", "look into the issues and work them", "loop through the issues", "digest the new issues and comments since last time", or wants a standing loop (via /loop or a scheduled agent) that drives the tracker toward releases. One invocation is one pass; the "since last time" watermark is what makes it a loop rather than a full re-scan. Composes with release-planning (land + ship), the feature loop, and the operating contract.
metadata:
  author: pulseengine.eu
  version: "0.2.0"
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
- **`queues`** per repo — `{ agent_closable, needs_decision, floor, brake,
  demoted_this_pass }`, refreshed from `check-issue-classes.py --format json` at
  pass start. `brake` is `open` or `close-only`; the pass reports it before
  doing anything else.
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

## The backlog brake — split the queue, throttle only the undecided half

Audits find faster than the loop closes. Measured 2026-10-21: rivet 33 open,
spar 37 open; spar went from 1 to 37 in seven months. The exit condition below is
right — a release, not an empty tracker — but nothing limited intake.

**Do not throttle discovery.** Self-inspection produces the most valuable finds
(the silently-wrong class: spar #482, #481, #478; rivet #1037). Throttling the
hunt to protect a number would suppress exactly the findings worth having.

So the brake splits the queue on the only axis that decides whether an agent can
finish an item alone — **not** on who filed it:

| class | meaning | under the brake? |
|---|---|---|
| **`agent-closable`** | a named reproducer exists **and currently fails on `main`** | **no — uncapped** |
| **`needs-decision`** | scope, architecture, priority, or no oracle yet | **yes** |

Provenance is deliberately not the axis. It also isn't available: every non-bot
issue in both repos is authored by the same account, so "agent-filed" cannot be
recovered from tracker metadata, and the title-length proxy agrees with the
Claude Code body marker only 20% (rivet, on the 259 non-bot issues) and 35%
(spar) of the time. The oracle axis needs none of that.

**`agent-closable` carries a reproducer, and the gate checks less than that
sentence suggests.** If a label alone released an issue from the brake, an agent
would write both the fix and the exemption that released it — spar #385's bug
class, which ran green over 12 of 12 unproven obligations. So:

- The issue body carries a fenced ` ```repro ` block holding one command.
- **Before working an `agent-closable` item, run that command.** It must fail. An
  exit 0 means the issue is already fixed (close it) or misclassified (demote it)
  — never "proceed".
- Promoting `needs-decision` → `agent-closable` *is* authoring that reproducer.

**The proof is by reference, not by command.** `agent-closable` requires a
`repro-run:` link to a **GitHub Actions run in the issue's own repository**, and
the gate asserts over the API that the run exists, that its `conclusion` is
`failure`, and that its head commit **touches a test path**. Only reviewed
repository code ever executes, in that repo's own CI where it already runs, and
the token needs read scopes alone.

That closes the hole an earlier revision had: checking only that a ` ```repro `
block parsed, which ` ```repro `/`true` satisfies. Executing the block here was
refused and stays refused — issue bodies are editable after labelling, including
by external filers, and the job holds a cross-repo token, so running strings from
an issue body would be command injection with a secret in the environment. A
`true` reproducer cannot produce a red run that adds a test, so it now fails by
construction.

**Entering class (a) therefore costs a failing test**, which is the work the
amendment calls an (a)-class task. Expect few or no items to qualify on the first
pass; that is the mechanism working, not a misconfiguration. Keep the ` ```repro `
block as local documentation if you like — it is no longer what is checked.

**The threshold is a ratchet, not a number.** The floor is whatever
`needs-decision` measured at the first fully classified pass, recorded in
`scripts/issue-class-floors.json` in the pulseengine.eu repo — **committed**,
because the state file below is git-excluded and a per-machine threshold cannot
be audited. The ratchet is two-sided: above the floor the pass
runs **close-only**, and *below* it the floor itself is a finding, because a floor
left above the real count is headroom new undecided work slips into. Above the
floor, or growing across two consecutive passes, the pass runs **close-only**: work the oldest actionable items, close obsolete ones with a
rationale ([`repo-hygiene`]), file nothing new.

**Staleness demotes, timed from the label.** The incentive runs toward class (a),
so an `agent-closable` item still open **21 days after it was labelled** (not
filed — most of this backlog predates the brake) demotes to `needs-decision`
and comes under the brake. It was not oracle-closable in practice. Nobody judges
motives, and the demotion rate measures classification honesty directly.

**Bulk filers check the brake first.** [`gate-potency`], [`traceability-audit`]
and internal evaluations check it before filing; over the floor they write **one
umbrella issue** instead of N.

**Report both queue sizes, the floor and the brake state at the top of every
pass.** `scripts/check-issue-classes.py` is the oracle — exactly one class per
open issue, a parseable reproducer on every `agent-closable`, and the ratchet. It
ships a `--self-test` decision table (22 cases, both directions, 11 of 11
source mutations caught). Its live half is `workflow_dispatch` only until the
cross-repo token and the first classified pass exist — arming a schedule that is
red on day one for a known reason trains everyone to ignore red. See
`.github/workflows/issue-classes.yml`.

Autonomy here means opening PRs that CI gates, under the standing merge-when-green
rule. It does not mean pushing to a protected branch.

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

On an **idle tick** — a pass where nothing is new since the watermark — fire
[`repo-hygiene`] instead of spinning: the issue board is the same surface this
loop watermarks, so hygiene closes what shipped (and sweeps worktree/branch/cache
residue the loop accreted) while the next pass triages what's new.

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
