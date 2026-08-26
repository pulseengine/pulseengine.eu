---
name: verify-your-own-claims
description: This skill should be used before reporting findings to a user, writing a PR body or issue comment, posting an audit result, or making any assertion about a codebase, a toolchain, or a system's state — especially a claim that GENERALIZES ("only X and Y do Z", "all of them pass"), asserts a CAUSE ("it fails because…"), asserts a NEGATIVE ("there is no…"), or reports a measurement as clean ("0 found", "all green"). ALWAYS use it when a claim rests on a grep, a search, a script you just wrote, or an API listing. It is the counterpart to [`claim-verification`], which gates a repo's documents with CI; this one covers the assertions you emit into a conversation, a PR body or an issue, where there is no build to fail — so the check has to be a procedure you run, not a gate that runs for you.
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# Verify your own claims

The operating contract already says: ground every progress claim in a tool
result. That rule catches the model that reports work it never did.

**It does not catch this.** Every failure below *had* a tool result behind it.
The claim was grounded — and still wrong, because the claim reached further
than the instrument could see.

> **The one principle.** A tool result behind a claim is **necessary, not
> sufficient.** The claim must not exceed what the instrument can measure. So
> before asserting, name the instrument, and name what it is blind to.

This is [`oracle-gate-a-change`]'s red-first discipline turned on your own
sentences, and it is [`gate-potency`]'s question — *can this check fail?* —
asked about the check you just ran on yourself.

## Why this is a real class, not a hypothetical

Five instances, one session, same author, all with evidence in hand:

| the instrument | the claim | what it could not see |
|---|---|---|
| `grep 'z3::\|use z3\|Z3_\|z3_sys'` over `.rs` + Cargo deps | *"Only loom and synth link Z3."* | Z3 as a **subprocess** and as a **Bazel toolchain** — so gale, relay and rules_verus, the largest un-certificate-checked Z3 surface in the org, were invisible |
| a link checker matching `href="([^"]+)"` | *"0 dead links."* | **Zero links.** The output is minified and emits unquoted `href=/docs/`. Six were dead, four on a nav-linked page |
| `gh run list` conclusions | *"cancelled by dependabot storms + cancel-in-progress."* | The **cause**. The concurrency group was per-branch; the durations sitting in the same output showed a 30-minute timeout |
| *(no probe ran)* | *"gale: cross-check none."* | Everything. An asserted **negative** with no instrument behind it at all |
| `--version` / exit-code conformance | *"these tools are fine"* (so they went unexercised) | **Behaviour.** The two most severe defects of the survey were in tools that passed every convention cleanly |

Note what is *not* in that table: a single instance of reporting work that was
never done. The contract's rule was satisfied every time.

## The four checks

Run these against the claim you are about to make. Each one is named after the
instance it would have caught.

### 1. Does the instrument have a zero-case that looks like success?

A checker that matched nothing prints the same triumphant `0 problems` as a
checker that matched everything and found nothing wrong. **Print the
denominator, and fail on zero.**

```
75 pages, 94 internal links checked, 0 dead     <- evidence
0 dead links                                    <- not evidence
```

If a count of *things examined* cannot be produced, the result is not a
measurement. This is [`gate-potency`]'s vacuity check applied to a one-off
script.

### 2. What shape of the thing would this probe be blind to?

Before generalizing from a search, enumerate the forms the target can take, and
confirm the pattern covers each. A dependency can arrive as a linked crate, a
spawned binary, a build-system toolchain, a vendored source tree, a container
image. One grep sees one form.

State the scope you actually searched — *"no crate links Z3"* is defensible;
*"nothing uses Z3"* is not, from the same grep.

### 3. Is this a cause, or a correlation the data also permits?

Reporting *what happened* needs the observation. Reporting **why** needs the
alternatives ruled out. Before writing "because", ask what else predicts the
same data, and check whether the answer is already in the output you have —
it usually is.

### 4. Did I probe every member of the population I am generalizing over?

A table with a row per repo asserts a result per repo. If one row was never
probed, it does not get a value — it gets **"unprobed"**. An absent instrument
never produces a negative finding; it produces no finding.

The tell: you are about to write a confident cell for something you have not
run a command against.

## Then: separate what you measured from what you concluded

In the report itself, keep them visibly apart. The measurement is durable and
someone else can re-run it; the conclusion is yours and may be wrong.

```
Measured:   57 cancelled, 3 failure, 0 success across 60 runs (2026-07-15 → 08-25);
            durations 30.4–102.5 min against timeout-minutes: 30
Concluded:  the job cannot finish inside its budget
```

Anyone can falsify the second line without re-deriving the first. That is the
property worth having, and it is the same reason a rivet artifact separates the
requirement from its verifying evidence.

## Anti-patterns

- **Treating "I ran a tool" as the end of the check.** It is the beginning. The
  contract's rule is the floor, not the ceiling — this skill exists because five
  claims cleared that floor and were still wrong.
- **Conformance as a proxy for correctness.** Passing a convention audit says a
  tool meets the convention. It says nothing about whether the tool works. Both
  of the worst defects in one survey were in tools with impeccable `--version`.
- **A confident cell for an unprobed row.** Fill it with *unprobed*, or delete
  the row. Do not let table symmetry manufacture a finding.
- **Rewriting the claim smaller after being challenged, without saying so.**
  If the scope was wrong, correct it plainly once and move on — see the
  operating contract on corrections.
- **Running this on trivia.** It is for load-bearing claims: ones that route
  work, close an issue, or land in a PR body someone will act on. Not for "the
  file is at `src/main.rs`."

## Where this composes

- [`claim-verification`] — the same species, other target: a repo's *documents*,
  where a `claims.yaml` sidecar and a CI gate can make drift fail the build.
  A sentence in a PR body has no build, which is why this one is a procedure.
- [`gate-potency`] — check 1 is its vacuity audit, scoped to a script you wrote
  five minutes ago rather than a standing CI gate.
- [`clean-room-verification`] — when a claim survives these four checks and is
  still consequential, hand it cold to a fresh-context agent. This skill is the
  cheap pass; that one is the expensive pass.
- [`report-tool-friction`] — an instrument that cannot see a whole shape of the
  thing it searches is often a *tool* gap worth filing, not just a personal
  slip.
- [`pulseengine-operating-contract`] — *"Ground every progress claim in a tool
  result"* is the always-on floor this skill builds on.
