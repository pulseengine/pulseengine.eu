+++
title = "ASPICE is not a queue of approvals. A requirement is only real if something can challenge it."
description = "ASPICE is usually read as a process — a V-model, a checklist, a queue of human sign-offs. But the standard's core idea is sharper: traceability from intent to verified behavior. A requirement matters only if architecture, code, tests, proofs, simulations, or hardware can rub against it. If nothing can challenge it, it is not an artifact — it is a wish. Measured in our own repos: 53 of 329 software requirements are wishes. 47 of them are scheduled for release."
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

A requirement matters only if architecture, code, tests, proofs, simulations,
or hardware can rub against it. If nothing can challenge it, it is not an
artifact — it is a wish.

We measured this in our own repositories. gale has 491 requirements across
the stakeholder → system → software hierarchy. 53 software requirements (16%)
have no verification criteria in their text — nothing can challenge them.
They are wishes. 47 of the 57 requirements scheduled for a release are
wishes. The release gate catches them: `rivet release status` says NOT
cuttable.

Of 234 verification measures with a recorded method, only 2 are human
reviews. The rest are mechanical oracles: 126 automated tests, 64 formal
verifications, 42 static analyses. The oracles do the verification. The
human orchestrates.
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

We use "wish" as shorthand. A more precise taxonomy: a **deferred intention**
is a requirement for future scope, marked `status: planned`. An
**unimplemented obligation** is a requirement with verification criteria but
no verification measure yet. An **unverified artifact** is a requirement with
a linked measure that has not run or has no recorded evidence. All three
are wishes in the sense that matters here: nothing currently challenges
them. The distinction matters for triage — a deferred intention might
become real next quarter; an unimplemented obligation needs a gate now;
an unverified artifact needs its test to run.

The problem is not that wishes are bad. The problem is that wishes look like
requirements. They have IDs. They have traceability links. They have
approvals. An assessor reads them and nods. But nothing in the system can
rub against them. They are dead weight — worse than dead weight, because
they create the illusion of coverage.

And you cannot estimate a wish. [The second post](/blog/can-we-deliver-x-by-january/)
showed how to estimate from gates and flow history — but a wish has no gate.
There is nothing to measure. The factory's throughput is measured in gates
passed per week. A wish passes no gates. It is invisible to the estimation
model. It is a hole in the corpus.

We measured this in our own work. gale has 491 requirements across the
stakeholder → system → software hierarchy (111 stakeholder, 51 system, 329
software). Running `rivet coverage --tests` shows 485 design elements and
requirements with **no test markers found**. Nothing challenges them. They
are wishes.

## What the numbers mean

The numbers measure different things. Here is the reconciliation:

| Number | What it counts | Source | Denominator |
|---|---|---|---|
| 491 | Total requirements (stakeholder + system + software) | `rivet stats` across all artifact files | — |
| 329 | Software requirements only (`sw-req`) | `rivet stats` | — |
| 276 | SW requirements with `verification-criteria` in text | Manual count of `fields.verification-criteria` | 329 sw-req |
| 53 | SW requirements WITHOUT verification criteria (wishes) | 329 − 276 | 329 sw-req |
| 57 | SW requirements scheduled for a release (`release:` field) | Manual count | 329 sw-req |
| 47 | SW requirements with release but NO criteria (wishes scheduled to ship) | Manual count | 57 with release |
| 276 | Total verification measure artifacts (unit + SW + system + integration) | `rivet stats` | — |
| 234 | Verification measures with a `method:` field | `grep method: verification.yaml` | 276 verification artifacts |
| 126 | Automated tests | `grep method: automated-test` | 234 with method |
| 64 | Formal verifications (Verus, Rocq, Kani) | `grep method: formal-verification` | 234 with method |
| 42 | Static analyses (Miri, etc.) | `grep method: static-analysis` | 234 with method |
| 2 | Human reviews | `grep method: review` | 234 with method |
| 91.8% | SW requirements with a linked verification measure | `rivet coverage` (rule: swe1-has-verification) | 329 sw-req |
| 485 | Artifacts with no test markers (design elements + requirements) | `rivet coverage --tests` | 1067 total artifacts |
| 207 | relay: artifacts with no test markers | `rivet coverage --tests` in relay | relay total artifacts |
| 24 | jess: uncovered requirements (all hardware REQ-PIX-*) | `rivet coverage --tests` in jess | jess total artifacts |

**What the numbers do not prove:**

- 91.8% link coverage does not mean 91.8% verified. The links exist, but
  `rivet trace-results` shows "no test evidence" — the tests have not run
  or their results are not recorded.
- 83% with verification criteria does not mean 83% verified. Criteria in
  text is necessary but not sufficient — the verification measure must
  exist, run, and pass.
- 485 uncovered includes design elements (DD-*), not just requirements.
  Design elements are verified through code tests, not their own tests.
- 2 human reviews out of 234 measures is a snapshot of gale's
  verification.yaml. Other repos may differ.

**The distinction that matters:**

| Stage | What it means | rivet command |
|---|---|---|
| Criteria in text | Requirement is verifiable | `fields.verification-criteria` |
| Measure linked | A verification measure claims to verify it | `rivet coverage` (91.8%) |
| Measure executed | The test/proof/analysis has run | `rivet trace-results` (shows "no test evidence") |
| Evidence recorded | Pass/fail result is in rivet | (not yet implemented — rivet#1129) |
| Release ready | All artifacts in the release are verified | `rivet release status` (NOT cuttable) |

A requirement can be at any stage. Only at the last stage is it real.

## Why people think ASPICE is a process

ASPICE is almost always introduced as a process. The V-model diagram. The
process areas (SYS.1 through SYS.5, SWE.1 through SWE.6). The capability
levels (0 through 5). The assessments. The training courses. The consultants.
The tool vendors selling "ASPICE compliance platforms." The whole industry
is built around the idea that ASPICE is a process you implement.

This is understandable. ASPICE grew out of SPICE (Software Process
Improvement and Capability dEtermination, ISO/IEC 15504), which was
explicitly a **process assessment** framework. The name itself says "process."
The capability levels measure process maturity. The assessors judge process
performance. The training teaches process implementation. The tools manage
process workflows. Everything points to "process."

And the process interpretation is not wrong — it is just incomplete. It
answers "how mature is our process?" but not "is our intent verified?"

A process-mature organization can produce garbage. A process-immature
organization can produce verified behavior. The process is the HOW. The
traceability is the WHAT.

## The standard itself moved away from "process"

Read the PAM 4.1 carefully and the standard has been moving away from the
process interpretation for years.

**3.1 → 4.0 (2023):** "Work products" were renamed "information items."
A work product is an artifact of a process — a document, a file, a
deliverable. An information item is a "separately identifiable body of
information that is produced, stored, and delivered for human use." The
rename is not cosmetic. It shifts the focus from the process output (the
document) to the information itself (the intent). The information item is
what matters. The work product is just one container for it.

**4.0 → 4.1 (2026):** The traceability and consistency base practices were
merged. In 3.1, traceability and consistency were separate BPs. In 4.0/4.1,
they are one BP: "Ensure consistency and establish bidirectional
traceability." The standard now treats them as one thing — you cannot have
consistency without traceability, and traceability without consistency is
just links.

And the standard added a section that most people skip:

> **"Why a PRM and PAM are not a lifecycle model or development process
> blueprint"**
>
> "A PRM/PAM groups a set of coherent and related characteristics of a
> particular technical topic and calls it 'process'. In different terms, a
> process in a PRM represents a 'distinct conceptual silo'. In this respect,
> a PRM/PAM **neither predefines, nor discourages, any order** in which PRM
> processes or Base Practices are to be performed. Ultimately, in Automotive
> SPICE® **consistency must be fulfilled** as required by the
> traceability/consistency Base Practices."
> — ASPICE PAM 4.1, Section 3.3.4

The standard **explicitly says** it is not a process blueprint. A "process"
in ASPICE is not a sequence of steps. It is a "conceptual silo" — a topic
area. The order is up to you. What matters is **consistency** — and
consistency is only demonstrable through traceability.

The standard also says:

> **"Traceability alone, e.g., the existence of links, does not necessarily
> mean that the information is consistent."**
> — ASPICE PAM 4.1, SYS.3.BP4 Note 7

Links are not enough. The information must be consistent. And consistency
is only demonstrable when something can fail.

## The challenge

If ASPICE is not a process, what is it?

It is a **design pattern for making intent traceable to verified behavior**.

The pattern is:

1. **Intent** — a requirement with verification criteria in its text
   (verifiability, SYS.2.BP1 Note 2)
2. **Traceability** — bidirectional links from intent to architecture, code,
   verification measures (SYS.2.BP5, SWE.4.BP4)
3. **Verification** — measures with pass/fail criteria that can challenge the
   intent (SWE.4.BP1, SWE.6.BP1)
4. **Consistency** — the links are not just links; the information is
   consistent (SYS.3.BP4 Note 7)

A requirement that follows this pattern is real. A requirement that doesn't
is a wish.

The process — the V-model, the reviews, the approvals, the assessments — is
the HOW. The pattern is the WHAT. You can have the process without the
pattern (compliance theater). You can have the pattern without the process
(a two-person startup with rivet and a CI gate). The pattern is what makes
the intent verifiable. The process is what makes it auditable.

## The V-model is not the point

The V-model is the most recognizable picture in ASPICE. Left side descends
from requirements to code. Right side ascends from tests to system
verification. The lines meet at the bottom.

Most companies see the V-model and think: "That's our process. We do a
V-model. We just need to add ASPICE labels to the boxes."

This is backwards.

The PAM 4.1 says so explicitly, in a section most people skip:

> **"Why a PRM and PAM are not a lifecycle model or development process
> blueprint"**
>
> "A PRM/PAM groups a set of coherent and related characteristics of a
> particular technical topic and calls it 'process'. In different terms, a
> process in a PRM represents a 'distinct conceptual silo'. In this respect,
> a PRM/PAM **neither predefines, nor discourages, any order** in which PRM
> processes or Base Practices are to be performed."
> — ASPICE PAM 4.1, Section 3.3.4

The V-model is a **visualization**, not a **requirement**. It is one way to
draw the conceptual silos. It is not the only way. And it is not the point.

The point is **consistency through traceability**. The order is up to you.
Kanban, waterfall, V-model, spiral — ASPICE doesn't care. What ASPICE cares
about is that your intent is traceable to verified behavior.

## The SAFe trap, again

This is the same trap as [the first post](/blog/safe-was-built-for-slow-humans/).

In SAFe, the trap is: *"same as our process, but with SAFe ceremonies."* The
team keeps their process, adds standups and retrospectives, and calls it
SAFe. The bottleneck doesn't move.

In ASPICE, the trap is: *"same as our V-model, but with ASPICE labels."* The
team keeps their V-model, adds traceability links between the boxes, and
calls it ASPICE. The wishes don't become real.

Most companies do this. They take their existing process — waterfall,
V-model, SAFe, whatever they have — and try to **map ASPICE onto it**. They
assign SYS.2 to the "requirements phase," SWE.1 to the "software
requirements phase," SWE.4 to the "unit test phase." They produce a
compliance matrix: "our phase X satisfies ASPICE process Y." The assessor
nods. The process maturity level goes up.

And nothing changes. The requirements are still wishes. The tests still
can't fail. The traceability is still just links.

## Map your work, not your process

The right direction is the opposite. Don't map ASPICE onto your process.
Map your **work** into what ASPICE describes.

| Instead of... | Do this... |
|---|---|
| "Our requirements phase satisfies SYS.2" | "Our requirements are information items with verification criteria in the text" |
| "Our architecture phase satisfies SYS.3" | "Our architecture allocates requirements to components, and the allocation is traceable" |
| "Our unit test phase satisfies SWE.4" | "Our tests have pass/fail criteria and can fail against the requirements they verify" |
| "Our review phase satisfies the review BP" | "Our reviews are the weakest oracle; our tests, proofs, and simulations are the strong ones" |
| "We have a traceability matrix" | "We have bidirectional links, and the links are consistent — not just present" |

The question is not "which ASPICE process does our phase satisfy?" The
question is "can something challenge this requirement?"

If the answer is no, it doesn't matter which phase you're in, which process
area you mapped, or what capability level you scored. It is a wish.

## CMMI: the same trap, one level up

The same critique applies to CMMI — and it is sharper there, because CMMI
Level 5 is the highest rating, and companies brag about it.

CMMI (Capability Maturity Model Integration) is the general process
maturity model. ASPICE is the automotive adaptation of SPICE (ISO/IEC
15504), which was itself inspired by CMMI. They measure the same thing:
**process maturity**. How well-defined, managed, measured, and optimized are
your processes?

CMMI Level 5 is "Optimizing" — quantitatively managed, continuously
improving, statistically predictable. It is the top of the pyramid. Companies
spend years and millions to get there. They put the rating on their
website. They win contracts because of it.

And they still produce wishes.

A CMMI Level 5 organization has mature processes for requirements
management. The process says: "requirements shall be documented, reviewed,
and traced." The process is followed. The documentation exists. The
reviews happen. The traceability matrix is maintained.

And the requirements are still wishes. No verification criteria in the
text. No tests that can fail. No proofs. No simulation. The process is
mature. The artifacts are not real.

This is not a bug in CMMI. It is the same design gap as ASPICE. Both
models measure **process maturity** (the HOW). Neither measures **artifact
quality** (the WHAT). A mature process for producing wishes is still a
mature process for producing wishes.

The Stack Overflow question says it plainly: *"The Model is losing its
credibility, first because the companies adopt the model not looking for a
maturer software development model, but to be appraised to a CMMI level."*

The appraisal is the goal. The rating is the product. The actual work —
verified behavior, challenged requirements, passing gates — is incidental.

## The pattern

The pattern is the same across all three:

| Framework | Measures | Can be gamed by | The real question |
|---|---|---|---|
| **SAFe** | Team velocity, sprint throughput | Story points, ceremony theater | Can we deliver verified behavior? |
| **ASPICE** | Process capability, traceability links | V-model with labels, compliance matrix | Can something challenge this requirement? |
| **CMMI** | Process maturity level | Documented processes, appraisal evidence | Is the intent traceable to verified behavior? |

All three are process frameworks. All three can be implemented as
theater. All three answer "how mature is our process?" but not "is our
intent verified?"

The fix is the same for all three: **map your work, not your process.**
Don't ask "which CMMI process area does our phase satisfy?" Ask "can
something challenge this requirement?" Don't ask "what ASPICE level are
we?" Ask "is this artifact real?" Don't ask "what's our sprint velocity?"
Ask "what gates did we pass?"

The maturity level, the capability rating, the velocity — these are
measurements of the process. The verified behavior is the measurement of
the work. Measure the work.

## ASPICE reframed

ASPICE (Automotive SPICE, VDA PAM 4.1) is usually read as a process. The
V-model. The process areas (SYS.1 through SYS.5, SWE.1 through SWE.6). The
capability levels. The assessments. The queue of approvals: requirements
review, architecture review, code review, test review, sign-off, sign-off,
sign-off.

But read the standard carefully and the core idea is different. ASPICE is
about **bidirectional traceability**: every requirement must be traceable to
architecture, to code, to verification measures — and back again. The
traceability is not bureaucracy. It is the mechanism that makes intent
verifiable.

And the standard says something sharper than most people notice:

> **"Traceability alone, e.g., the existence of links, does not necessarily
> mean that the information is consistent."**
> — ASPICE PAM 4.1, SYS.3.BP4 Note 7 (also SYS.4.BP4 Note 5, SWE.4.BP4 Note 4)

Links are not enough. A link says "related." Consistency says "correct."
And consistency is only demonstrable when something can fail.

The standard also says requirements must be **verifiable**:

> **"verifiability (i.e., verification criteria being inherent in the
> requirements text)"**
> — ASPICE PAM 4.1, SYS.2.BP1 Note 2 (also SWE.1.BP1 Note 2)

A requirement without verification criteria in its text is not verifiable.
It is a wish.

And verification measures must have **pass/fail criteria**:

> **"Specify verification measures for each software unit... including
> pass/fail criteria for verification measures"**
> — ASPICE PAM 4.1, SWE.4.BP1

A verification measure without pass/fail criteria cannot fail. It is not a
gate. It is a wish.

The standard lists what a verification measure can be:

> **"Verification measure can be: Test cases, Measurements, Calculations,
> Simulations, Reviews, Analyses"**
> — ASPICE PAM 4.1, Table 1 — Terminology

Reviews are on the list — but they are the weakest oracle. A review can
fail, but humans miss things. The stronger oracles — tests, simulations,
analyses, calculations — are mechanical. They fail when the artifact is
wrong, not when the human is tired.

This is the oracle axis from [the first post](/blog/safe-was-built-for-slow-humans/),
applied to requirements. A requirement is real if an oracle can challenge it.
An oracle is a mechanical check that can confirm or deny correctness — a test
that fails when the code is wrong, a proof that fails when the property
doesn't hold, a simulation that fails when the model diverges from reality,
hardware that fails when the silicon doesn't behave.

**Gate potency** is the property that a gate can still fail. A gate that
always passes is not a gate — it is a wish with a green badge. The
`gate-potency` skill audits whether CI checks can still go red.

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
reviews**. Two. Out of 234 verification measures with a recorded method,
two are human approvals. The rest are mechanical oracles that can fail.

This is not an accident. It is the design. The human reviews the diff in the
pull request. The oracles do the verification. The human is the orchestrator
([the third post](/blog/the-orchestrator-who-does-what/)); the oracles are
the gates.

A note on "weak": human review is not worthless. It is essential for intent,
hazard analysis, safety argumentation, and verification adequacy — the things
mechanical oracles cannot check. But as a **repeated oracle** for routine
correctness, it is weak. Humans miss things, get tired, rubber-stamp. The
mechanical oracles do not.

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

But hardware is not automatically the **strongest** oracle. It is the most
**reality-grounded** oracle — no model gap, no simulation fidelity question.
But it is the least **exhaustive** oracle. You cannot test every input on
silicon. You cannot test every failure mode. Hardware has limited
observability — you see the output, not the internal state. A passing
hardware test does not prove the requirement; it proves the requirement
held for the cases you tested.

Hardware does not replace proofs, tests, or simulation. It is the final
reality check — the last rung on the ladder. The earlier rungs (proof,
simulation, unit test) are cheaper and more exhaustive. Hardware is the
most expensive and least exhaustive. Use it when the earlier rungs have
narrowed the risk to what only silicon can answer.

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

{% <mermaid> %}
flowchart TB
    subgraph left["Left side of V (specification)"]
        direction TB
        stk["Stakeholder req"]
        sys["System req"]
        sw["SW req"]
        arch["Architecture"]
        code["Code"]
        stk -->|"derives-from"| sys
        sys -->|"derives-from"| sw
        sw -->|"allocated-to"| arch
        arch -->|"implements"| code
    end

    subgraph right["Right side of V (verification — gates)"]
        direction TB
        test["Test<br/>(can fail)"]
        proof["Proof<br/>(can fail)"]
        sim["Simulation<br/>(can fail)"]
        hw["Hardware<br/>(can fail)"]
    end

    code -->|"verified by"| test
    code -->|"verified by"| proof
    arch -->|"verified by"| sim
    sys -->|"verified by"| hw

    style stk fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
    style sys fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
    style sw fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
    style arch fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style code fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style test fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style proof fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style sim fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed
    style hw fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed

    classDef spec fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed;
    classDef design fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef gate fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
    classDef verify fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed;
    classDef hw fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
{% </mermaid> %}

Every link in the V must be a gate. If a link is just a link — if nothing
can fail — it is a wish.

## rivet's implementation

rivet is our implementation of this idea. It is a **typed knowledge graph**
with a **release gate**: a git-native, schema-driven artifact store where
every artifact is typed (requirement, architecture, code, test, proof,
simulation result, hardware result), every artifact has bidirectional links
to other artifacts, and every release is a gate that cannot be cut until
its artifacts are verified.

**The release is the gate.** In our work, we plan in rivet releases. Each
release is a bound — a set of artifacts scoped to ship together. `rivet
release status v0.1.0` shows the readiness burn-down: which artifacts are
approved, which are verified, which are blocking. The release cannot be cut
until the artifacts are verified. The release is the gate, not the issue.

```
$ rivet release status v0.1.0
Release v0.1.0 — 11 artifact(s)
  approved     11

✗ NOT cuttable — 11 artifact(s) not yet verified.
```

The key command is `rivet coverage`. It shows rule-based coverage: which
artifacts satisfy which traceability rules. In gale:

```
Rule                           Source Type           Covered    Total        %
swe1-has-verification          sw-req                    302      329    91.8%
sys2-has-verification          system-req                 47       51    92.2%
```

91.8% of software requirements have a verification measure linked. 8.2%
do not. Those 8.2% are wishes — they have no `verifies` link, nothing
challenges them.

But link coverage is not the same as test evidence. `rivet trace-results
SWREQ-SEM-P01` shows the forward trace — the verification measures that
claim to verify it — but reports **"no test evidence"**. The links exist.
The tests have not run. Or their results are not recorded. The requirement
has a gate, but the gate has not been exercised.

This is the gap we are working on. The links are there. The evidence is
not. A link without evidence is still a wish — just a wish with better
paperwork.

`rivet coverage --tests` scans the codebase for test markers and reports
which artifacts have no test coverage. In gale, it reports 485 uncovered
artifacts. Those are wishes. The orchestrator's job is to either add a gate
(a test, a proof, a simulation) or remove the wish.

The other key command is `rivet validate`. It checks that all links resolve,
that all artifacts are well-formed, that the traceability graph is complete.
If a link is broken, validation fails. If an artifact is orphaned,
validation warns. The traceability is not a spreadsheet — it is a graph that
can be queried, validated, and gated.

rivet also enforces commit trailers. Every commit must carry a typed trailer
that ties it back to an artifact (`rivet-artifact: REQ-001`). This makes the
traceability git-native — the history is the audit trail.

## What we get wrong

We are honest about where we fall short.

**Most of our work items are not fully set up as ASPICE.** gale has 329
software requirements. 276 (83%) have verification criteria in their text.
53 (16%) do not. Those 53 are wishes — they have no `verification-criteria`
field, nothing can challenge them. And 47 of the 57 requirements scheduled
for a release have no verification criteria. They are wishes scheduled to
ship. The release gate catches them — `rivet release status` says NOT
cuttable — but they should not be there in the first place.

**The links exist, but the evidence does not.** `rivet trace-results` shows
verification measures linked to requirements, but reports "no test
evidence." The tests exist in the codebase. Their results are not recorded
in rivet. A link without evidence is a wish with better paperwork.

**The release gate works, but it is blocking.** `rivet release status
v0.1.0` shows 11 artifacts approved but not verified. The release cannot be
cut. The gate is doing its job — but the artifacts need test results
recorded.

**Coverage is link coverage, not verification coverage.** `rivet coverage`
shows 91.8% of SW requirements have a linked verification measure. But
`rivet trace-results` shows "no test evidence" for those same requirements.
The links exist. The tests have not run — or their results are not
recorded. 91.8% linked is not 91.8% verified.

These are the gaps we are filing issues for. The wish detector (rivet#1127),
hardware verification markers (rivet#1128), recording test results
(rivet#1129), link statistics (rivet#1130), the triage of uncovered
artifacts (gale#461, relay#605, jess#298), adding verification criteria
(gale#462), adding rivet validate to CI where it is missing (relay#606,
spar#523, meld#528, kiln#600, witness#327), and cross-repo drift
monitoring (warte#20). The pattern is the same: make the wishes visible,
then decide — add a gate, or remove the wish.

## Counterarguments we take seriously

**"A requirement may be verifiable through analysis or review even if it
has no automated test."** Yes. ASPICE PAM 4.1 lists reviews and analyses as
verification measures. A human can challenge a requirement. But the human
is a weak *repeated* oracle — essential for intent and adequacy, weak for
routine correctness. Our data: 2 of 234 measures are reviews. The other
232 are mechanical. That is not because reviews are worthless. It is
because mechanical oracles scale.

**"Coverage is not correctness."** Correct. 91.8% link coverage does not
mean 91.8% verified. The links exist; the evidence does not. This is why
we filed rivet#1129 (record test results) — the gap between linked and
verified is exactly what we are working to close.

**"A test marker is not proof that the requirement is verified."** Correct.
A test marker says a test exists. It does not say the test is valid, does
not say the test covers the requirement, does not say the test passed. This
is why we need rivet#1129 — recording pass/fail evidence, not just markers.

**"Your system may optimize for producing links and markers rather than
meaningful verification."** This is the real risk. An agent could satisfy a
weak oracle — write a test that technically challenges a requirement but
does not meaningfully verify it. The defense is gate potency (Blog 1): the
gates must be proven to fail. A gate that cannot fail is not a gate. The
`gate-potency` skill audits this. And the orchestrator reviews — not every
diff, but the gates themselves.

**"What happens when an agent satisfies a weak oracle?"** The gate passes,
but the requirement is not verified. This is why the orchestrator's job is
not just to add gates, but to add *appropriate* gates. The orchestrator
decides: is this test strong enough? Is this proof sound? Is this
simulation faithful enough? The mechanical oracles do the checking. The
human does the judging.

**"What prevents an agent from deleting or weakening a requirement to make
a gate pass?"** Nothing mechanical. This is why the orchestrator reviews
the diff. The agent can propose; the human disposes. The release gate
(`rivet release status`) shows what changed. The commit trailers tie every
commit to an artifact. The audit trail is the defense.

**"What is the escalation path when all mechanical gates pass but the
result is still unsafe?"** The orchestrator. The human in the loop. The
mechanical oracles check correctness against the specification. The human
checks whether the specification is right. If all gates pass but the result
is unsafe, the specification was wrong — and that is a human decision, not
a mechanical one.

## The orchestrator's job

The orchestrator's job is to ensure every requirement has a gate. A
requirement without a gate is a wish. Wishes go to the decision queue —
the orchestrator decides: add a gate, or remove the wish.

This is the blue hat from [the third post](/blog/the-orchestrator-who-does-what/):
factory operations. The factory's output is not code — it is verified
behavior. A requirement without a gate is not verified behavior. It is a
wish.

In the dark factory — agents running autonomously on cron loops, producing
artifacts, opening PRs — the orchestrator is the one who ensures the gates
exist. The agents produce the artifacts. The oracles check them. The
orchestrator reviews the diff and decides what's next. The agents do not
decide which requirements are real. The orchestrator does.

The orchestrator does not write the tests or the proofs. The agents do. The
orchestrator ensures that every requirement has something that can challenge
it. The agents produce the artifacts. The oracles check them. The
orchestrator reviews the diff and decides what's next.

This is the same pattern as Blog 3's orchestrator: the human enables the
agents, prioritizes across friction/operations/decisions, and verifies the
output. Here, the "output" is not code — it is verified behavior. The
orchestrator's leverage is in designing the gates, not in writing the tests.

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

[^aspice-pam]: VDA QMC, *Automotive SPICE® Process Assessment Model (PAM) 4.1*,
preview release, April 2026. Primary (standard, preview). Downloaded from
[vda-qmc.de](https://vda-qmc.de/wp-content/uploads/2026/04/Automotive-SPICE-PAM-4.1_Preview.pdf).
Quotes from SYS.2.BP1, SYS.3.BP4, SYS.4.BP4, SWE.1.BP1, SWE.4.BP1, SWE.6.BP1,
and Table 1 (Terminology). The final release may differ from the preview.

[^iso-29148]: ISO/IEC/IEEE 29148:2018, *Systems and software engineering —
Lifecycle processes — Requirements engineering*. Referenced by ASPICE PAM 4.1
as the standard for "defined characteristics for requirements" including
verifiability. Primary (standard, paywalled).

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
