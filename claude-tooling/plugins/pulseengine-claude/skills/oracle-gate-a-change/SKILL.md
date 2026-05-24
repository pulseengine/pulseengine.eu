---
name: oracle-gate-a-change
description: This skill should be used whenever proposing, designing, landing, or evaluating a consequential change on a PulseEngine project (rivet, spar, witness, sigil, meld, loom, synth, wohl) — including "propose a change", "add a feature", "fix a bug", "is this safe to land", "what verifies this", "what's the gate", "how do we know this is correct", "before merging this", or whenever a code change needs a mechanical check to back it. ALWAYS use this skill before claiming a property holds and before recommending a change be merged.
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# Oracle-gate a change

## When this fires

Before any consequential change lands on a PulseEngine project. The gate is **mechanical** — a check that fires or doesn't, not an LLM reading the spec back. The skill picks the right oracle for the kind of claim, writes it first if it doesn't exist, and refuses to call the change "done" until red flips to green.

This is distinct from [`clean-room-verification`], which validates *findings* before reporting. Oracle-gating runs at the *system* layer: it's how an agent's "I changed X" earns the right to be merged.

## Procedure

### 1. Name the kind of claim the change makes

Before anything else: what is this change asserting? Pick the right oracle for the claim type:

| Claim type | Mechanical oracle (PulseEngine toolchain) |
|---|---|
| Type / schema / traceability claim | `rivet validate`, `rivet check`, `rivet coverage` |
| Architecture / scheduling / WIT generation claim | spar analysis pass (one of 27+: EMV2 fault trees, ARINC 653 partitioning, ASIL decomposition, modal-filtered scheduling, piecewise-affine TSN arrival curves) |
| Branch / decision / MC/DC coverage on a Wasm artifact | `witness` truth-table gap report — **the gap view, not a coverage percentage**. The percentage is the wrong artifact. |
| Build-stage integrity / attestation | `sigil` verification chain |
| Memory-safety / UB / overflow / dedup-logic | Kani BMC (used in wohl + synth), Verus (used in wohl/AlertDispatcher) |
| Property-based / state-explosion search | fuzz harness (cargo-fuzz / synth's gale fuzzer), z3-backed verifier in synth-verify |
| Symbol-elimination claim (e.g. cross-language LTO) | `nm <artifact.elf> | grep <symbol>` returning zero. From the gale → zephyr LTO work. |
| Coverage gap | `rivet coverage` against the schema-defined trace topology |

If the claim doesn't fit any of these, the change is making a fuzzy claim that can't be mechanically backed. **Sharpen the claim or escalate** — fuzzy claims should not gate merges.

### 2. If no oracle exists for the claim, write the oracle first

This is the most-skipped step and the highest leverage one. If the change claims a new property and no test / `rivet check` / proof obligation / fuzz harness / `nm` invocation currently fires red-or-green for that property:

- **Write the oracle first.** Add the test that would currently fail. Add the `rivet check` rule. Write the Kani harness. Add the fuzz target.
- **Land the oracle separately if possible** so its red state is visible before the change that's supposed to flip it green. This makes the gate's behavior observable.

If you cannot write the oracle (the property isn't checkable with current tooling), **surface the gap clearly** in the PR description. Do not paper over it with prose review. Either the property is checkable or the change can't claim it.

### 3. Attach a kill-criterion to the claim

Per PulseEngine methodology, every claim should carry a falsifiable kill-criterion: "this claim would be wrong if X is observed." This is required for the philosophy to compose — without kill-criteria the falsification stance is empty.

Examples:
- "AlertDispatcher dedup is correct" → kill-criterion: "if Verus flags a duplicate-acceptance path."
- "Cross-language LTO eliminated gale symbols" → kill-criterion: "if `nm zephyr.elf | grep gale_` returns non-zero."
- "PR doesn't drop trace coverage" → kill-criterion: "if `rivet coverage` reports a new uncovered predicate."

### 4. Gate the diff

Only the diff that flips the oracle from red to green counts. Specifically:
- If the oracle was already green before the change: the change must add a new oracle that goes red→green on this diff, or this change isn't actually verified.
- If the oracle was red: the change should flip it green. If green wasn't reached, the change isn't ready.
- If the oracle's behavior was unchanged: the change is doing something the oracle doesn't measure. Either expand the oracle or shrink the claim.

### 5. Verify before reporting "done"

Apply [`clean-room-verification`] to the claim "this change passed its oracle." An agent saying "I ran the test and it passed" is itself an unverified claim — actually re-run the oracle in a clean environment and read the output.

## The rules baked in

- **A "done" without a flipped mechanical oracle is unverified.** No exceptions for "small" changes.
- **Soft oracles (LLM reading the spec back) don't count.** They cannot find what the spec didn't anticipate. From the `mythos-slop-hunt` and `spec-driven-development-is-half-the-loop` blog posts.
- **Write the oracle first if it's missing.** If the property is worth claiming it's worth checking.
- **Specification completeness is the bottleneck.** Per `formal-verification-ai-agents`, agent-written proofs are cheap now — the limiting factor is whether the spec covers what the change is actually doing.
- **Kill-criteria are mandatory.** A claim without a falsifier is not a claim, it's a hope.

## Anti-patterns

- "Review looks good" as the gate. Review is input; oracle is the gate.
- "Tests pass" without saying *which* test exercises the new property. If you can't name it, it doesn't exist.
- Skipping the oracle write because "we already have lots of tests." The relevant question is whether *this property* is checked, not whether *anything* is.
- Treating `rivet validate` green as proof the change is correct. `rivet validate` is one oracle of many; pick the one matching the claim type.

## Where this composes

`pulseengine-feature-loop` runs this skill per change inside the feature loop. `release-execution` expects every PR in the queue to have passed through this gate before merge. Verification of the oracle-passed claim flows to [`clean-room-verification`].
