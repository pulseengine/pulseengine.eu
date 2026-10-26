+++
title = "ASPICE is not a queue of approvals. A requirement is only real if something can challenge it."
description = "ASPICE is usually read as a process — a V-model, a checklist, a queue of human sign-offs. But the standard's core idea is simpler and sharper: traceability from intent to verified behavior. A requirement matters only if architecture, code, tests, simulation, or hardware can rub against it. If nothing can challenge it, it is not an artifact — it is a wish."
date = 2026-10-30
draft = true
ready = true
[taxonomies]
tags = ["aspice", "verification", "traceability", "process", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**ASPICE is not a queue of human approvals. It is a design pattern for making
intent traceable to verified behavior.**

A requirement matters only if architecture, code, tests, simulation, or
hardware can rub against it. If nothing can challenge it, it is not an
artifact — it is a wish.

We measured this in our own repositories. gale has 288 requirements. 485
design elements and requirements have no test markers — nothing challenges
them. They are wishes. The ones with verification measures are real: tests,
proofs, static analysis. Only 2 are human reviews.
{% </insight> %}

[The first post](/blog/safe-was-built-for-slow-humans/) argued that the
bottleneck in an agent factory is not generation — it is verification and
decisions. [The second post](/blog/can-we-deliver-x-by-january/) showed how
to estimate from gates and flow history. [The third post](/blog/the-orchestrator-who-does-what/)
showed who does what. This post is about the artifacts themselves: what makes
a requirement real.

## The wish problem

Every safety-critical project has a requirements document. Most of it is
wishes.

A wish is a statement that nothing can challenge. "The system shall be
safe." "The software shall be maintainable." "The kernel shall support
priority inheritance." These are not requirements — they are hopes. No test
can fail against them. No proof can refute them. No simulation can falsify
them. They sit in the document, approved, signed off, and forgotten.

The problem is not that wishes are bad. The problem is that wishes look like
requirements. They have IDs. They have traceability links. They have
approvals. An assessor reads them and nods. But nothing in the system can
rub against them. They are dead weight — worse than dead weight, because
they create the illusion of coverage.

We measured this in our own work. gale has 288 requirements across the
stakeholder → system → software hierarchy. Running `rivet coverage --tests`
shows 485 design elements and requirements with **no test markers found**.
Nothing challenges them. They are wishes.

## ASPICE reframed

ASPICE (Automotive SPICE, ISO 29110) is usually read as a process. The
V-model. The process areas (SYS.1 through SYS.5, SWE.1 through SWE.6). The
capability levels. The assessments. The queue of approvals: requirements
review, architecture review, code review, test review, sign-off, sign-off,
sign-off.

But read the standard carefully and the core idea is different. ASPICE is
about **bidirectional traceability**: every requirement must be traceable to
architecture, to code, to tests — and back again. The traceability is not
bureaucracy. It is the mechanism that makes intent verifiable.

The standard says: "test cases shall be derived from and traceable to
requirements" (SWE.4.BP2, SWE.6.BP2). "Verification measures" — not just
tests, but reviews, static analysis, formal verification, simulation. The
point is not that a human approved something. The point is that **something
can fail against the requirement**.

This is the oracle axis from [the first post](/blog/safe-was-built-for-slow-humans/),
applied to requirements. A requirement is real if an oracle can challenge it.
An oracle is a mechanical check that can confirm or deny correctness — a test
that fails when the code is wrong, a proof that fails when the property
doesn't hold, a simulation that fails when the model diverges from reality,
hardware that fails when the silicon doesn't behave.

## The oracle axis for requirements

Not all verification is equal. Some oracles are stronger than others.

| Oracle | What it challenges | Strength |
|---|---|---|
| **Human review** | "Does this look right?" | Weak — humans miss things, get tired, rubber-stamp |
| **Static analysis** | "Does this code have undefined behavior?" | Medium — catches bugs, but limited by the analyzer's model |
| **Automated test** | "Does this code pass these cases?" | Medium — catches regressions, but only for cases you thought of |
| **Formal proof** | "Does this property hold for all inputs?" | Strong — mathematically guarantees correctness (if the proof is sound) |
| **Simulation** | "Does this model match reality?" | Strong — but only as strong as the model's fidelity |
| **Hardware** | "Does this silicon actually work?" | Strongest — the real thing, no model gap |

In gale, the verification methods break down as: 126 automated tests, 64
formal verifications (Verus, Rocq, Kani), 42 static analyses (Miri), and **2
reviews**. Two. Out of 234 verification measures, two are human approvals.
The rest are mechanical oracles that can fail.

This is not an accident. It is the design. The human reviews the diff in the
pull request. The oracles do the verification. The human is the orchestrator
([the third post](/blog/the-orchestrator-who-does-what/)); the oracles are
the gates.

## What "rubbing against" looks like

A requirement is challenged when an artifact rubs against it. The artifact
tries to satisfy the requirement. The oracle checks whether it succeeded.
If the oracle can fail, the requirement is real.

Here is what that looks like in practice, across the V-model:

### Architecture rubs against requirements

The architecture allocates each requirement to a component. If the component
cannot satisfy the requirement — if the allocation is wrong, if the
component's interface doesn't support it — the architecture review fails.

In our work: spar (the architecture compiler) ingests AADL models and emits
rivet artifacts. Each system requirement is allocated to an architecture
component. The allocation is a rivet link. If the component changes and the
allocation breaks, `rivet validate` fails. The architecture rubs against the
requirement.

### Code rubs against requirements

The code implements the requirement. If the code is wrong — if it doesn't
match the specification, if it has a bug — the tests fail.

In our work: gale's semaphore implementation is Rust code that must match
Zephyr's `k_sem` API semantics. The provenance artifact (`PROV-SEM-001`)
records the exact upstream file and SHA256. The code is traced to the
requirement via rivet links. If the code diverges from the upstream
semantics, the tests fail. The code rubs against the requirement.

### Tests rub against requirements

The tests verify the requirement. If the test is wrong — if it doesn't
actually test the requirement, if it passes vacuously — the test is a wish,
not an oracle.

In our work: gale's verification.yaml maps every test to the design elements
and requirements it verifies. `rivet coverage --tests` shows which
requirements have no test markers. Those are wishes. The ones with test
markers are real — the tests can fail. The tests rub against the
requirements.

### Formal proofs rub against requirements

The proof verifies the requirement. If the proof is wrong — if the
specification is weaker than the requirement, if the proof has a gap — the
proof checker fails.

In our work: gale's semaphore has 10 properties (P1-P10) verified by Verus
SMT proofs and Rocq theorem proofs. Each property maps to a software
requirement. The verification-criteria field in the requirement artifact
records which proofs verify it. If a proof fails, the requirement is not
verified. The proofs rub against the requirements.

### Simulation rubs against requirements

The simulation models the requirement's domain. If the simulation is wrong —
if the model doesn't match reality — the simulation results are meaningless.

In our work: relay's flight stack is verified in Renode simulation before it
touches hardware. The simulation models the sensors, the actuators, the
control loop. If the simulation diverges from reality, the HITL (hardware-in-the-loop)
test fails. The simulation rubs against the requirements.

### Hardware rubs against requirements

The hardware is the real thing. If the hardware fails — if the silicon doesn't
behave, if the board doesn't boot — the requirement is not verified.

In our work: jess carries relay's flight stack from simulation to hardware.
The ladder (sim → HITL → silicon) is the path from model to reality. Each
rung is a gate. If the hardware fails, the requirement is not verified. The
hardware rubs against the requirements.

## The V-model with gates

The V-model is usually drawn as two lines: the left side descends from
requirements to code, the right side ascends from tests to system
verification. The lines meet at the bottom (implementation).

But the V-model is about **linking**, not **challenging**. A link says "this
test is related to this requirement." A gate says "this test can fail against
this requirement." The difference is everything.

A V-model with links is a wish factory. A V-model with gates is a
verification system.

```
Stakeholder req ──derives-from──→ System req ──derives-from──→ SW req
     │                                │                           │
     │         ┌── gate ──┐          │         ┌── gate ──┐        │
     │         │ architecture│        │         │    code     │       │
     │         └─────┬─────┘          │         └─────┬─────┘       │
     │               │                  │               │             │
     │         ┌─────┴─────┐    ┌─────┴─────┐   ┌─────┴─────┐       │
     └────────→│   test    │←───│   proof   │←──│   sim     │←──────┘
               │  (can fail)│    │ (can fail)│   │ (can fail)│
               └───────────┘    └───────────┘   └───────────┘
```

Every link in the V must be a gate. If a link is just a link — if nothing
can fail — it is a wish.

## rivet's implementation

rivet is our implementation of this idea. It is a git-native, schema-driven
artifact store. Every artifact is typed (requirement, architecture, code,
test, proof, simulation result, hardware result). Every artifact has links
to other artifacts. Every link is bidirectional.

The key command is `rivet coverage --tests`. It scans the codebase for test
markers and reports which artifacts have no test coverage. In gale, it
reports 485 uncovered artifacts. Those are wishes. The orchestrator's job is
to either add a gate (a test, a proof, a simulation) or remove the wish.

The other key command is `rivet validate`. It checks that all links resolve,
that all artifacts are well-formed, that the traceability graph is complete.
If a link is broken, validation fails. If an artifact is orphaned,
validation warns. The traceability is not a spreadsheet — it is a graph that
can be queried, validated, and gated.

rivet also enforces commit trailers. Every commit must carry a typed trailer
that ties it back to an artifact (`rivet-artifact: REQ-001`). This makes the
traceability git-native — the history is the audit trail.

## The orchestrator's job

The orchestrator's job is to ensure every requirement has a gate. A
requirement without a gate is a wish. Wishes go to the decision queue —
the orchestrator decides: add a gate, or remove the wish.

This is the blue hat from [the third post](/blog/the-orchestrator-who-does-what/):
factory operations. The factory's output is not code — it is verified
behavior. A requirement without a gate is not verified behavior. It is a
wish.

The orchestrator does not write the tests or the proofs. The agents do. The
orchestrator ensures that every requirement has something that can challenge
it. The agents produce the artifacts. The oracles check them. The
orchestrator reviews the diff and decides what's next.

## What we would tell you to take from this

**A requirement is only real if something can challenge it.** If nothing can
fail against it, it is a wish — no matter how many approvals it has.

**ASPICE is not a queue of approvals.** It is a design pattern for making
intent traceable to verified behavior. The traceability is the mechanism.
The gates are the proof.

**Measure your wishes.** Run coverage. Count the requirements with no test
markers. In our work, it's 485 out of 288+ requirements. Those are wishes.
Either add a gate or remove the wish.

**Prefer mechanical oracles over human reviews.** In our work, 2 out of 234
verification measures are human reviews. The rest are tests, proofs, static
analysis — oracles that can fail. Humans are orchestrators, not oracles.

**The V-model needs gates, not just links.** A link says "related." A gate
says "can fail." Build gates.

## Limits

This is one project's implementation: gale, relay, jess, and the rivet
toolchain. It has not been assessed by an external ASPICE assessor. The claim
is not "we are ASPICE-compliant" but "we read ASPICE as a design pattern, and
this is what we built."

The 485 uncovered artifacts in gale are not all wishes — some are design
elements that will get tests later, some are roadmap items not yet
implemented. The point is not that they are bad. The point is that they are
**not yet real** — nothing challenges them yet.

The comparison to human reviews (2 out of 234) is from gale's
verification.yaml. Other projects may have different ratios. The principle
holds: mechanical oracles are stronger than human approvals.

## Sources and caveats

The data is from our own repositories: gale (288 requirements, 58
verification measures, 485 uncovered), relay (91 requirement files, 115
verification files, 207 uncovered), jess (24 uncovered requirements). Measured
on 30 October 2026 with `rivet coverage --tests` and `rivet validate`.

The ASPICE interpretation is the author's. The standard (ISO 29110 / VDA
PAM 4.0) requires bidirectional traceability; the reframe from "process" to
"design pattern" is ours. An assessor might read it differently.

[^aspice-pam]: VDA Automotive SPICE PAM 4.0. Primary (standard). The process
assessment model: SYS.1-SYS.5, SWE.1-SWE.6, MAN.3, and supporting processes.

[^iso-29110]: ISO/IEC 29110 — Software engineering — Lifecycle profiles for
Very Small Entities (VSEs). Related but not identical to ASPICE; ASPICE is
the automotive adaptation.

[^rivet]: PulseEngine, *rivet* — typed knowledge graph + oracle-gated agents.
[github.com/pulseengine/rivet](https://github.com/pulseengine/rivet). Primary
(tool documentation).

---

*This post is part of [PulseEngine](/) — a formally verified WebAssembly
Component Model engine for safety-critical systems. Prior posts in the arc:
[SAFe was built for slow humans](/blog/safe-was-built-for-slow-humans/),
[Can we deliver X by January?](/blog/can-we-deliver-x-by-january/),
[The orchestrator: who does what](/blog/the-orchestrator-who-does-what/),
[The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/).*
