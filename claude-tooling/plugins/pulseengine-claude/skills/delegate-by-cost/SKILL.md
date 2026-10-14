---
name: delegate-by-cost
description: This skill should be used whenever work is about to run on a more capable (and more expensive) model than it requires — a repo-wide grep, a file census, a mechanical audit, "read these N files and report", a build-and-test loop — and whenever a chosen tier has failed a task two or three times and the question becomes "retry, escalate, or stop". Use it when the user says "this is cost saving", "use a cheaper model", "spawn a subagent to do it", "try haiku/sonnet first", or "escalate it". It routes a subtask DOWN to the cheapest tier that passes a mechanical check, verifies the result, and escalates UP one rung at a time only on mechanical failure, stopping at the top tier to ask the user rather than looping. The precondition is economic: the ladder saves money only when checking an answer is cheaper than producing it, and is a cost TRAP when it is not. Composes with oracle-gate-a-change, verify-your-own-claims (grade the worker, not its summary) and proof-synthesis (the retry loop).
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# Delegate by cost — the cheapest tier that passes the oracle

The capable model you are running on is not the right machine for most of the work it is
asked to do. A repo census, a selector lookup, a "read these twelve files and tell me which
ones declare X" — these are **mechanical** tasks with an exact answer, and the cheap tiers
get them right. Running them at the top of the ladder is not thoroughness, it is waste.

But the ladder is not free, and the direction people get wrong is the obvious one: **a
cascade that usually fails costs MORE than never cascading at all.** You pay the cheap
attempt, you pay the verification, and then you pay the expensive attempt anyway. So this
skill is a precondition and a procedure, in that order.

## Why this is a real class

Normalize the tier you would otherwise have used to `1`. Let `r` be the cheap tier's cost as
a fraction of it, `p` the probability its answer passes your check, `v` the cost of running
that check. You verify either way, so compare:

    ladder:  r + v + (1-p)·(1 + v)        direct:  1 + v

which reduces to **`r + (1-p)·(1 + v) < 1`**. Two readings fall straight out:

- **With a cheap mechanical oracle (`v ≈ 0`) the condition is `p > r`.** When the bottom rung
  costs a fortieth of the top, it only has to be right about one time in forty to break even.
  Delegating down is then close to a free option, and *not* delegating is the expensive choice.
- **When verification costs about what production costs (`v ≈ 1`), the bar jumps past one in
  two.** If checking the answer means re-deriving it on the expensive model, you have already
  paid for the expensive model and the ladder bought nothing.

**So the precondition is: verifying must cost materially less than producing.** It does not
have to be a script. A test suite, a build, an exact count, a `file:line` list the parent can
spot-check, `rivet check`, a schema validation — all qualify. "Re-read everything and form a
second opinion" does not. **No cheap check, no ladder:** do the work at the tier you are on.

This is [`oracle-gate-a-change`] costed. The methodology already says every change should flip
a mechanical oracle; the oracle you built for correctness turns out to be the thing that makes
cheap delegation affordable. The two rules are the same rule seen from different ends.

## The rungs

One table, deliberately the only place tiers are named. The names are the `Agent` tool's
`model` enum values, which float across model generations — unlike version strings, which
[`pulseengine-operating-contract`] bans from routing rules for exactly this reason. **If a new
tier appears, edit this table and nothing else.**

| rung | `model:` | reach for it when |
|---|---|---|
| bottom | `haiku` | grep/census/extract/format, closed answer, oracle is exact |
| lower-middle | `sonnet` | the above plus light judgment, multi-file reading, routine edits under a test |
| upper-middle | `opus` | real judgment, design, ambiguity, anything cross-cutting |
| top | `fable` | long-horizon work, or a task the rung below has mechanically failed |

Read the ladder **relative to the session's own model**, not absolutely: "one rung down" from
`opus` is `sonnet`. Between two model rungs sits a cheaper one — **same model, more effort**
(`effort: "high"`/`"xhigh"`). Try that before paying a higher per-token rate; raising effort
costs more tokens at the same price, while a tier jump raises the price of every token.

## The procedure

**1. Build or name the oracle FIRST, before dispatching anyone.** Not after reading the
worker's answer. An oracle written once you have seen a plausible answer gets shaped to fit it,
and a ladder graded by a flexible oracle is a ladder that always "passes".

**2. Decide whether to delegate at all.** A handful of tool calls is not worth a subagent —
do it yourself. Delegate when the work is a self-contained subtask with a closed deliverable.

**3. Dispatch at the lowest plausible rung.** Pass `model:` explicitly every time — never rely
on the default, and **never use `subagent_type: "fork"` for this**, because a fork inherits the
parent's model and silently ignores `model:`. A fork can never be a tier change.
Brief hygiene: state the deliverable in a closed format, require every claim to rest on
something read, and **keep the expected answer out of the brief** — a brief that contains the
answer tests nothing.

**4. Grade against the oracle, not against the worker's summary.** This is
[`verify-your-own-claims`] pointed at someone else's output.

**5. On a pass, you are done.** Do not "just double-check it" on a higher tier. That spends
the entire saving to buy a second opinion you have no reason to want.

**6. On a failure, distinguish which kind it is — this is the step that goes wrong.**

| the worker... | do this |
|---|---|
| fails the **mechanical** check — wrong count, bad `file:line`, red tests, invalid schema | retry, then escalate |
| **disagrees with your own judgment**, with cited evidence | **re-derive from its evidence first** |

A disagreement is not a failure. Check the worker's citations before you overrule it: if the
evidence holds, the worker was right and escalating would spend money to punish a correct
answer. (This is not hypothetical — see "What this is based on" below.)

**7. Retry within the rung before climbing, and cap it.** Two attempts per rung. A retry must
carry **the oracle's failure output** — the actual diff, the failing assertion, the wrong count
— not a resubmission of the same brief. That is the generate→verify→refine loop from
[`proof-synthesis`], and the verifier's output is the signal; without it a retry is a coin flip.

**8. Climb one rung at a time**, re-running the same oracle. Effort rung before model rung.

**9. At the top rung, one attempt. Then stop and ask.** Do not loop at the top; do not keep
re-briefing. Put it to the user with `AskUserQuestion` and concrete options — the task may be
underspecified, the oracle may be wrong, or the work may need to be cut up differently. Two
rungs failing the same oracle is evidence about the *task*, not just about the models.

**10. Record the class, not just the outcome.** "Cross-repo release-state reconciliation fails
below the upper-middle rung" is reusable; "attempt 3 failed" is not. A class that has failed
the ladder once starts at the rung that worked — re-laddering a known-failing class is paying
the trap fee twice. Durable ones belong in memory via [`capture-session-learnings`].

## The ladder is driven by the top-level session only

Workers do not re-delegate. A worker that spawns its own ladder makes cost unaccountable and
nests failures where the oracle cannot see them. One driver, one ladder, one oracle.

## Anti-patterns

- **Laddering without a cheap oracle.** The headline failure. You will pay every rung and still
  not know whether any answer was right.
- **Grading the summary.** A worker's "all nine verified" is a claim, not a result.
- **Writing the oracle after seeing the answer.** It will fit.
- **Using a fork for a tier change.** It silently stays on the parent's model, so the whole
  "cost saving" is imaginary while looking like it worked. Count the `model` field in the
  worker's transcript if you need proof it routed.
- **Escalating on judgment disagreement.** Re-derive from cited evidence first.
- **Re-verifying a pass on a higher tier.** Spends the saving on reassurance.
- **Resubmitting an identical brief as a "retry".** Carry the failure output or do not retry.
- **Laddering write work with no build or test as the oracle.** A wrong edit that passes no
  check is worse than an expensive correct one. When delegating writes, use
  `isolation: "worktree"` so a bad attempt is discardable.
- **Delegating what you could do in three tool calls.** The handoff costs more than the work.

## What this is based on

Measured in this repo on 2026-10-14, so the honest limits are visible:

- **The `model` override routes.** Verified by counting the model field in each worker's own
  request records rather than asking it what it was: 12 requests on the bottom-rung model, 17
  on lower-middle, 27 on top, in the three respective workers. `effort` is accepted alongside it.
- **The premise holds on mechanical work.** One identical read-only brief — find every
  `backdrop-filter` declaration under `sass/` and `templates/`, name the owning selector,
  classify each as chrome or content — run at three rungs returned **identical, correct**
  answers: 9 declarations, same selectors, same 2-chrome/7-content split. The bottom rung used
  the fewest tool calls; the top rung took about 2.5× the wall-clock for the same answer.
- **The top tier is not the oracle.** The parent session, on the upper-middle rung, had the
  split wrong (1/8) and all three workers had it right. The mechanical selector lookup caught
  the parent, not the workers. This is why step 6 exists.
- **Not exercised: escalation.** No rung failed, so the climb, the retry-with-failure-output
  loop and the stop-and-ask terminus are **procedure, not measurement**. Exercising them needs
  a task the lower rungs genuinely fail against a mechanical oracle. Treat those steps as
  reasoned design until that run exists, and do not cite them as verified.
- **Not exercised: write delegation.** Every probe was read-only. The `isolation: "worktree"`
  guidance above is untested here.
- Cost ratios are a rate card, not a bill, and they move. Get current numbers from the
  `claude-api` skill rather than from any number written into a skill file.

## Where this composes

- [`oracle-gate-a-change`] — the oracle is the precondition; this skill is its cost consequence.
- [`verify-your-own-claims`] — grade the worker against evidence, not against its confidence.
- [`clean-room-verification`] — a cold re-check is itself a cheap-tier job, so the ladder makes
  clean-room review affordable enough to do by default.
- [`proof-synthesis`] — the retry loop, where the verifier's output drives the next attempt.
- [`gate-potency`] — an oracle that cannot fail turns the ladder into unverified cost saving.
- [`pulseengine-operating-contract`] — static disposition→tier routing per skill lives there;
  this skill is the dynamic half, for when the chosen tier does not deliver.
