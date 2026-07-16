---
name: release-planning
description: This skill should be used to plan releases in rivet — assign which requirements/artifacts belong to which release and drive development from that plan — and to run the issue-driven delivery loop — an error, regression, or optimization comes in, gets evaluated, flows through the full verification chain, and ships in a planned release. Use it when scoping a release ("what goes in v0.X"), triaging an incoming issue/bug/optimization toward a release, asking "is v0.X ready to cut", or driving a roadmap. Builds on rivet's existing `release:` field + status lifecycle (draft→proposed→approved→implemented→verified→accepted); composes with the feature loop (build each item), traceability-audit (a release is ready when its items' V is closed), and release-execution (cut it).
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# Release planning & the delivery loop

Two halves of one working model: **plan** which requirements land in which
release (in rivet, so the V-model artifacts drive the roadmap — not a separate
spreadsheet or only GitHub milestones), and **deliver** against that plan via an
issue-driven loop (error/optimization in → evaluate → full chain → ship). This
matches how the toolchain repos already work — synth plans by phase milestones
and ships eval-first fixes ("mla fusion regresses flat_flight 255→257 on
Cortex-M4 — gate it?"); loom plans by version milestones (v0.4/v0.5/v1.0) — but
makes the plan live in rivet and the loop explicit.

## Part A — Release planning *in rivet*

rivet artifacts already carry a **`release:`** field and a status lifecycle
(`draft → proposed → approved → implemented → verified → accepted`). Use them as
the plan, not GitHub milestones alone:

- **Scope a release** = the set of requirements/decisions tagged `release: vX.Y`.
  Assign each requirement to the release it's targeted for; an unassigned
  requirement is backlog, not a commitment.
- **Readiness is a query, not an opinion** — for `release: vX.Y`, how many of its
  artifacts are `verified`/`accepted` vs still `approved`/`implemented`? `rivet`
  (filter by release + status) + `rivet coverage` give the live burn-down. The
  release is cuttable when **every** artifact in its scope is `verified` and the
  V is closed (see [`traceability-audit`]).
- **Drive from it** — "what must we implement for v0.X" is exactly the
  `release: v0.X` + status≠verified set. Pull work from there.
- **Mirror to GitHub milestones** for visibility (synth phases, loom versions),
  but rivet's `release:` field is the source of truth — the milestone is a view.
- **Move scope deliberately** — deferring a requirement to a later release is a
  scope decision (bump its `release:`), surfaced and logged, not silent.

## Part B — The issue-driven delivery loop

An error, regression, or optimization arrives (a GitHub issue, a failing run, a
benchmark delta). Run it as a loop, not an ad-hoc fix:

1. **Evaluate — measure, don't guess.** Reproduce and quantify. The synth
   pattern is the bar: a regression is a *number* (255→257 cycles), an
   optimization is a measured delta, a bug is a failing run. Root-cause it.
2. **Classify against the plan.** Is it a *new requirement* (capability gap), a
   *regression* against an existing verified requirement (the trace says what
   broke), or an *optimization* (a decision with a measured benefit + a
   constraint it must not violate)? Each maps to a rivet artifact.
3. **Land it in rivet, assigned to a release.** Create/extend the
   requirement/decision/test, set `release:` (this release if urgent, a planned
   one if not) and `status`. Link it into the trace (what it satisfies/affects)
   so a regression re-opens the right requirement's verification.
4. **Run the full chain.** [`pulseengine-feature-loop`] + [`oracle-gate-a-change`]
   — fix/implement, re-establish the oracle (tests, witness MC/DC, proofs via
   [`proof-synthesis`]); a perf optimization must keep the *correctness* oracle
   green while improving the measured number.
5. **Close the V.** [`traceability-audit`] — the artifact is `verified` only with
   passing tests at the right levels; the regression's original requirement is
   re-verified.
6. **Ship in its release.** When the release's scope is all `verified`,
   [`release-execution`] cuts it (V-model gate + falsification statement). Given
   the frequent cadence here, a single high-value fix can be its own release.

## Worked shapes (from the repos)
- **Optimization (synth/loom):** measured regression/gain → a `decision` artifact
  with the benchmark + the invariant it must preserve → implement → witness/proof
  oracle stays green AND the number improves → `verified` → release.
- **Bug (kiln):** failing run → the requirement it violates is found via the
  trace → fix + a regression test that `verifies` it → `verified` → patch release.
- **Capability gap (loom "consume scry invariants"):** new requirement →
  `release: vX.Y` → feature loop → verified → planned release.

## Where this composes
- [`bootstrap-verification`] — a new piece gets its first release plan here.
- [`pulseengine-feature-loop`] / [`oracle-gate-a-change`] — execute each item.
- [`proof-synthesis`] — discharge proof obligations an item carries.
- [`traceability-audit`] — release readiness = the scope's V closed at all levels.
- [`release-execution`] — cut the release once readiness holds.
- [`report-tool-friction`] — if rivet can't express a planning query you need.

## Anti-patterns
- **Planning only in GitHub milestones**, divorced from the rivet trace — the
  roadmap then can't be driven by, or gated on, verification state.
- **Fixing without a measurement** — an "optimization" with no before/after
  number, or a "bug fix" with no failing-then-passing test, isn't a closed loop.
- **Optimizing the number while letting the correctness oracle slip** — perf work
  must keep proofs/tests/MC-DC green; a faster wrong answer is a regression.
- **Cutting a release before its scope is `verified`** — readiness is the query,
  not the calendar; move scope out explicitly rather than shipping it unverified.
- **Untriaged issues** — an issue with no rivet artifact and no release is
  invisible to the plan and resurfaces as a release-time surprise.
