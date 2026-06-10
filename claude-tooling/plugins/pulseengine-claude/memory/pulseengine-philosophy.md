---
name: pulseengine-philosophy
description: "Pulseengine.eu engineering philosophy — verification + traceability + attestation methodology applied across every project"
metadata:
  node_type: memory
  type: reference
  scope: plugin-bundled
---

PulseEngine (https://pulseengine.eu) — verification + traceability + attestation tooling for safety-critical software, automotive background. The philosophy below is durable methodology, not branding. See [[pulseengine-toolchain]] for the tool landscape.

**Core mission**: *"AI writes the code. Who proves it's safe?"*

**Three pillars**: verification, traceability, attestation.

## Methodology

**Falsification, not prediction.** From `2026-05-01-cross-language-lto-three-quiet-barriers`:
- Predict specifically — claims must be falsifiable, not vague.
- Measure on production geometry, not synthetic benchmarks.
- Publish the falsification when you were wrong — *"wrong-prediction data is more informative than the predicted number would have been if it landed."*
- Reframe around what the data supports, not what you set out to prove.
- Binary evidence directly supports claims (e.g. `nm zephyr.elf | grep gale_` and read zero).

**Defense-in-depth, not minimum-viable verification.** From `2026-04-22-overdoing-the-verification-chain`:
- In regulated domains, combining techniques (proofs + tests + model checkers + sanitizers + mutation testing + fuzzing) shrinks blind spots faster than tightening any single technique.
- When you don't know which question an assessor will ask, overdoing is the only honest default.
- AI-velocity authorship *grows* the verification surface, doesn't shrink it.

**MBSE is mandatory infrastructure for AI-authored safety code.** From `2026-04-23-spec-driven-development-is-half-the-loop`:
- Model-based systems engineering (AADL via spar, requirements via rivet) used to feel heavyweight; AI-velocity untraceable code inverts that — the model must *drive* the build, not sit alongside.
- Cost dropped from "half a day per requirement" to "agent-minutes plus human review."

**Variant pruning collapses MC/DC scope.** From `2026-04-24-variant-pruning-rust-mcdc`:
- MC/DC burden on the shipped artifact is proportional to a single variant, not the combinatorial product of feature flags.
- Five pruning layers: requirements variants → cargo features → cfg → type system → match arms.
- Counter to the naive "Rust pattern matching makes MC/DC harder" reading.

**Formal verification cost collapsed under AI.** From `2026-03-15-formal-verification-ai-agents`:
- The seL4-era cost ("PhD students writing 200k lines of proof for 10k lines of code") is no longer the regime.
- Agent-written annotations checked by SMT solvers in seconds — AutoVerus 91.3%, AlphaVerus 85%, Lean Copilot 74.2%.
- *Specification completeness* is now the bottleneck, not proof-writing.

**The synthesis (three patterns colliding).** From `2026-04-25-three-patterns-colliding`:
- Karpathy-style LLM wiki (compounding knowledge across sessions) + oracle-gated agents (mechanical verification gate) + typed compliance (rivet, auditable result).
- Each alone fails — wiki drifts into fiction, oracle has no memory, typed traceability is labor-intensive. Together they cancel each other's failure modes.

## How to apply (framing only — the procedures live in skills)

When advising on any PulseEngine project (or movement-tracker, which uses the same methodology):
- Frame work in PulseEngine vocabulary — *falsification, traceability, attestation, kill criteria*.
- Every claim needs a kill-criterion. The per-change ritual for this lives in the `oracle-gate-a-change` skill.
- Every release needs a falsification statement. The per-release ritual lives in the `release-execution` skill.
- Don't propose techniques without a measurable adoption gate.
- Don't propose minimum-viable verification when defense-in-depth is on the table.

The procedural how — feature-loop composition, oracle selection per change, release tail, clean-room verification of findings — lives in the procedural skills shipped with this plugin, not in this memory file. This memory is the always-on framing; the skills load on trigger.

See also: [[pulseengine-toolchain]], the `oracle-gate-a-change` skill, the `pulseengine-feature-loop` skill.
