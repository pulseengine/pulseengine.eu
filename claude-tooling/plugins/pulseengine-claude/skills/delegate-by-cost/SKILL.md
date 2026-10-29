---
name: delegate-by-cost
description: "Use this skill BEFORE EVERY Agent (Task) call, to choose `model:`, and whenever a delegated tier has failed the same check twice and the question is retry, escalate or stop. From an opus or fable parent, mechanical work with an exact check (grep, census, count, extract, file:line list, build-and-test against a red/green test) goes to `model: haiku`; `sonnet` only where the subtask needs judgment that is not top-tier; a subagent with no `model:` runs at the parent's price by default. Delegated work is mostly cache reads, and haiku's cache read costs a twentieth of opus's (a quarter past 100K-token prompts) while sonnet's costs half. Escalate one rung at a time only on a mechanical failure, and at the top rung stop and ask the user. No cheap check, no delegation. Also fires on \"use a cheaper model\", \"try haiku first\", \"escalate it\". Composes with oracle-gate-a-change, verify-your-own-claims and proof-synthesis."
metadata:
  author: pulseengine.eu
  version: "0.2.0"
---

# Delegate by cost — choose `model:` before every Agent call

**Every Agent call gets an explicit `model:`.** A call without one runs on the parent's model and
the parent's price (unless a default subagent model is configured); that is the default you are
overriding, not a neutral choice.

## The rule

From an `opus` or `fable` parent:

- **Mechanical work with an exact check → `haiku`.** Grep, census, count, extract, "read these N
  files and list which declare X", a build-and-test loop against a test that goes red. The check
  is a count, a `file:line` list you can spot-check, a test run, `rivet check`, a schema
  validation. For read-only locate work, `subagent_type: "Explore"` with `model: haiku`: Explore's
  built-in default resolved to an older haiku on 2026-10-29, at ten times the current haiku's
  input and cache-read rates.
- **Judgment that is not top-tier → `sonnet`.** Multi-file reading where the answer is not a
  closed list, a routine edit under a test, a first-pass review whose findings you will grade.
- **Real design, ambiguity, cross-cutting judgment → stay on the parent tier**, or do it yourself.
- **No cheap check → no delegation.** If grading the answer means re-deriving it, do the work at
  the tier you are on.

Never use `subagent_type: "fork"` for a tier change: a fork inherits the parent's model and
ignores `model:`.

## Why haiku, not "one rung down"

Delegated work is dominated by **cache reads**: the subagent re-reads its growing context every
turn. Measured over this repo's own down-routed subagent traffic (2026-10-29 transcript study):
613M cache-read tokens against 3.5M output tokens. So the cache-read rate is the price that
matters, and on it the tiers are not evenly spaced.

Rates per MTok as published on 2026-10-29 (platform.claude.com pricing page):

| rung | input | cache read | output |
|---|---|---|---|
| `haiku` (prompt ≤ 100K) | $0.10 | $0.01 | $0.50 |
| `haiku` (prompt > 100K) | $0.50 | $0.05 | $2.50 |
| `sonnet` | $2 | $0.10 | $10 |
| `opus` | $4 | $0.20 | $20 |
| `fable` | $10 | $0.25 | $50 |

On cache reads, `sonnet` is half of `opus` and `haiku` is a twentieth; `opus` is only a fifth
below `fable`. A sonnet hop halves the bill; a haiku hop removes about 95% of it, or 75% once
the worker's prompt passes 100K tokens. Rates move:
re-read them from the `claude-api` skill or the pricing page before quoting a figure.

## Is it worth delegating at all

Normalize the parent tier's cost to `1`. Let `r` be the worker's cost as a fraction of it, `p`
the chance its answer passes your check, `v` the cost of the check. Delegating pays when
**`r + (1-p)·(1 + v) < 1`**. With a near-free mechanical check (`v ≈ 0`) that is `p > r`: at
`r ≈ 0.05` the worker need be right one time in twenty. When the check costs what producing
costs (`v ≈ 1`), the bar rises past one in two and the ladder is a cost trap.

## The procedure

1. **Name the oracle before dispatching.** An oracle written after you have seen a plausible
   answer gets shaped to fit it.
2. **Skip delegation for a handful of tool calls.** The handoff costs more than the work.
3. **Dispatch at the lowest plausible tier, `model:` explicit.** State the deliverable in a closed
   format, require every claim to rest on something read, and keep the expected answer out of the
   brief.
4. **Grade against the oracle, not the worker's summary** ([`verify-your-own-claims`]).
5. **On a pass, stop.** Do not re-verify on a higher tier.
6. **On a failure, tell the kinds apart.** A *mechanical* failure (wrong count, bad `file:line`,
   red test, invalid schema) → retry, then escalate. A worker that *disagrees with your judgment*
   and cites evidence → re-derive from its evidence first; the parent is not the oracle.
7. **Retry once within the tier, carrying the oracle's failure output** (the diff, the failing
   assertion, the wrong count), never the same brief again ([`proof-synthesis`]).
8. **Escalate one rung at a time** (`haiku` → `sonnet` → `opus` → `fable`), same oracle. Raising
   `effort` on the same tier is a cheaper step than a tier jump; try it first.
9. **At the top rung, one attempt, then stop and ask the user** with `AskUserQuestion` and concrete
   options. Two rungs failing the same oracle is evidence about the task, not only the models.
10. **Record the class.** "X fails below sonnet" is reusable; a class that failed the ladder once
    starts at the rung that worked ([`capture-session-learnings`]).

Workers do not re-delegate: one driver, one ladder, one oracle. When delegating writes, use
`isolation: "worktree"` and a build or test as the oracle.

## The reminder hook

The plugin's PreToolUse hook on the Agent tool adds a one-line reminder to the session when an
Agent call has no `model:` and its `subagent_type` is absent, `general-purpose` or `claude`. It
never denies or alters the call. The reminder arrives with that call's result, so it shapes the
*next* call, not the one that triggered it. It is throttled per session: the first such call,
then every 10th consecutive one; a call that sets `model:` resets the count.

## What this is based on

- **The `model:` override routes** (2026-10-14): counted from the workers' own request records, not
  asked of them. One read-only census brief run at three tiers returned identical, correct answers;
  the parent had it wrong. That is why step 6 exists.
- **The first version of this skill did not change behaviour** (2026-10-29 transcript study,
  1,531 sessions): it was invoked 0 times; only its description steered. Explicit `model:` rose from
  19% to 54% of Agent calls, mostly where the user spelled out the ladder, and was decaying (41 of
  177 down-routed in the latest week). 187 Agent calls without `model:` ran on opus, and Explore
  use fell from 143 to 3. Most down-routing went opus → sonnet, the smaller saving. Hence the
  description now names the trigger moment, the rule now says haiku, and the hook reminds.
- **Not exercised: escalation.** One case in the study. Steps 7–9 are reasoned design, not
  measurement.
