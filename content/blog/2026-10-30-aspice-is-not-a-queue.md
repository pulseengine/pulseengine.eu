+++
title = "ASPICE is not a queue of approvals. A requirement is only real if something can challenge it."
description = "Read ASPICE as a design pattern for tracing intent to verified behavior, and a requirement matters only if a test, proof, simulation or hardware run can fail against it. Measured in gale on 26 October 2026: 53 of 329 software requirements lack a verification-criteria field, 11 have neither criteria nor a verification link, and no test results are recorded yet."
date = 2026-10-30
draft = true
[taxonomies]
tags = ["aspice", "verification", "traceability", "process", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**Read ASPICE as a design pattern for tracing intent to verified behavior,
and a requirement is real only when something can challenge it.**

Architecture, code, tests, proofs, simulations or hardware have to be able
to fail against a requirement. A requirement nothing can fail against is a
wish, however many approvals it carries.

We measured our own repositories against that bar. gale has 491
requirements, 329 of them software requirements. 53 of the 329 have no
`verification-criteria` field. Most of those still have a verification
measure linked, but 11 have neither criteria nor a link. Of 276
verification artifacts, 252 declare a method and only 2 of those declare
human review. None of them has a recorded result in rivet yet.
{% </insight> %}

[The first post](/blog/safe-was-built-for-slow-humans/) argued that the
bottleneck in an agent factory is verification and decisions, and
[the second](/blog/can-we-deliver-x-by-january/) estimated delivery from
gates and flow history. Both assume that the thing being verified is worth
verifying. This post is about the artifacts themselves: what makes a
requirement real, what the Automotive SPICE process assessment model
(PAM)[^aspice-pam] says about it, and how far our own repositories are from
the bar we set.

## What makes a requirement real

A wish is a statement that nothing can challenge. "The software shall be
maintainable" and "the kernel shall support priority inheritance" have IDs,
owners and approvals, and no test, proof or simulation can fail against
either of them as written. Wishes are expensive because they look like
requirements. An assessor reads them, the traceability matrix lists them,
and they count toward coverage while constraining nothing.

Three nearby states are often lumped in with wishes, and each needs a
different triage. A **deferred intention** is scoped for later and marked
`proposed` or `draft`. An **unimplemented obligation** states its criteria
but has no verification measure yet, so it needs a gate. An **unverified
artifact** has a measure linked but no result recorded against it: it can
be challenged and has not been yet, so its test needs to run and report.
Below, "wish" means the strict case, a requirement with neither criteria nor
a linked measure.

A wish also cannot be estimated. The [estimation
post](/blog/can-we-deliver-x-by-january/) counts gates passed per week, and a
requirement without a gate passes none. It is invisible to the forecast.

## What the PAM says

ASPICE is usually taught as a process: the V-model, the process areas SYS.1
to SYS.5 and SWE.1 to SWE.6, capability levels 0 to 5, and a sequence of
reviews and sign-offs. That reading is understandable. Automotive SPICE
descends from SPICE (ISO/IEC 15504), a process assessment framework that
drew on the earlier CMM. PAM 4.1 is developed in accordance with ISO/IEC
33004 and reproduces its capability measurement framework from ISO/IEC
33020. Assessors rate process performance, and the word "process" is in
the name.

The model itself is more careful. Section 3.3.4 of PAM 4.1 is titled "Why a
PRM and PAM are not a lifecycle model or development process blueprint". It
calls each process a "distinct conceptual silo", a grouping of related
characteristics of one technical topic, and continues:

> "In this respect, a PRM/PAM neither predefines, nor discourages, any order
> in which PRM processes or Base Practices are to be performed. Ultimately,
> in Automotive SPICE® consistency must be fulfilled as required by the
> traceability/consistency Base Practices [...]"
> (PAM 4.1, §3.3.4)

The same section notes that MAN.3 BP2 still requires a project to "Define
the project lifecycle", so order is not irrelevant. The PAM leaves the
choice of lifecycle to the project and asks that it be defined, and it
judges the result by consistency. As far as the PAM is concerned, Kanban,
a V-model and a spiral are all acceptable lifecycles, as long as the
project defines the one it uses.

None of this is new in 4.1. The 4.0 release of October 2023 was the
complete revision: it replaced "work products" with "information items",
already merged traceability and consistency into a single base practice
("Ensure consistency and establish bidirectional traceability"), and
already contained §3.3.4. PAM 4.1, released on 24 August 2026, describes
itself in its own document history as the removal of MLE.2 BP5 plus
editorial changes.

Three further passages carry the argument. The traceability base practices
say that links do not prove consistency:

> "Traceability alone, e.g., the existence of links, does not necessarily
> mean that the information is consistent."
> (PAM 4.1, SYS.2.BP5 Note 7; the sentence recurs in the later traceability
> base practices, e.g. SYS.3.BP4 Note 7)

SYS.2.BP1 Note 2 gives verifiability as an example characteristic of a
requirement: "verification criteria being inherent in the requirements
text". Note 1 of the same practice names ISO/IEC/IEEE 29148[^iso-29148], ISO
26262-8 and the INCOSE guide as examples of where such characteristics are
defined. SWE.4.BP1 asks that unit verification measures specify
"pass/fail criteria for verification measures".

Table 1 of the PAM lists what a verification measure can be: test cases,
measurements, calculations, simulations, reviews and analyses. It adds that
not every measure fits every domain, and that "software units generally
cannot be verified by means of calculations or analyses". The list is
flat.

Taken together, these passages describe a pattern with four parts. **Intent**
is a requirement whose text carries its verification criteria.
**Traceability** is a bidirectional link from intent to architecture, code
and verification measures. **Verification** is a measure with pass/fail
criteria that can fail against the intent. **Consistency** means the linked
information agrees, which is more than a link being present. The process
(reviews, approvals, assessments) is how an organisation shows an assessor
that the pattern holds. A project can run the process without the pattern,
and a two-person team with a CI gate can hold the pattern with very little
process.

## Map your work, not your process

The common adoption path takes an existing process, waterfall or V-model or
SAFe, and maps ASPICE onto it. SYS.2 becomes the "requirements phase", SWE.4
the "unit test phase", and a compliance matrix shows that phase X satisfies
process Y. The capability rating can rise while the requirements stay
wishes, because nothing in the mapping asks whether a test can fail against
them. This is the same trap [the SAFe post](/blog/safe-was-built-for-slow-humans/)
described: the existing process with new labels.

The other direction maps the work into what the PAM describes:

| Instead of... | Do this... |
|---|---|
| "Our requirements phase satisfies SYS.2" | "Our requirements carry verification criteria in their text" |
| "Our architecture phase satisfies SYS.3" | "Our architecture allocates requirements to components, and the allocation is a checked link" |
| "Our unit test phase satisfies SWE.4" | "Our tests have pass/fail criteria and can fail against the requirements they verify" |
| "We have a traceability matrix" | "Our links are validated, and the linked information is consistent" |

CMMI has the same gap one level up. It grew out of the CMM, and its level 5
rates how well-defined, measured and improving an organisation's processes
are. A level-5 requirements process can still document, review and trace
requirements that no test can fail against. Both models rate process
capability, and neither rates whether a given requirement can be
challenged. The question we ask of each artifact is narrower: can something
fail against it?

## The oracle axis for requirements

An oracle is a mechanical or human check that can confirm or deny that an
artifact meets a requirement. Oracles differ in what they can catch.

| Oracle | What it challenges | Strength and limit |
|---|---|---|
| **Human review** | "Does this look right?" | Needed for intent, hazards and adequacy. Weak as a repeated check of routine correctness |
| **Static analysis** | "Does this code have undefined behavior?" | Catches whole bug classes, within the analyzer's model |
| **Automated test** | "Does this code pass these cases?" | Catches regressions, only for the cases written |
| **Formal proof** | "Does this property hold for all inputs?" | Proves the stated property for all inputs, relative to the spec and the trusted base |
| **Simulation** | "Does the system behave in a modelled environment?" | As good as the model's fidelity |
| **Hardware** | "Does the real silicon behave?" | Most reality-grounded and least exhaustive: no model gap, few inputs, limited observability |

The ordering is our judgement; the PAM does not rank these, and hardware
does not sit at the top. A passing hardware run shows the requirement held
for the cases exercised on that board, with only the outputs visible.
Proofs, simulation and unit tests are cheaper and cover more of the input
space, so hardware is best used once they have narrowed the risk to what
only silicon can answer.

### Where each oracle meets a requirement in our repositories

**Architecture.** In gale, every software requirement is derived from a
system requirement and every architecture component is allocated from a
software requirement; `rivet coverage` reports 329/329 and 52/52 for those
rules. `rivet validate` fails when a link points at an artifact that does
not exist. These links are hand-written YAML in gale. rivet can also
import AADL architecture models through spar's parser and analysis crates,
but gale does not use that path today.

**Code.** gale's semaphore is a Rust port of Zephyr's `k_sem`. The
provenance artifact `PROV-SEM-001` records the upstream file
(`kernel/sem.c`) and its SHA-256, so a change upstream is detectable
against the port.

**Formal proof.** The semaphore has ten software requirements,
`SWREQ-SEM-P01` to `SWREQ-SEM-P10`, from "0 ≤ count ≤ limit" to wait-queue
ordering. They are stated as Verus `ensures` and invariant clauses in
`src/sem.rs`. Separately, `proofs/sem_proofs.v` is a Rocq development that
proves count invariants over an abstract model and structural facts about
the rocq-of-rust translation of the code; its theorems are not labelled
with the P-numbers. rivet records no evidence for any of the ten yet: all
are `approved`, none `verified`, and `rivet release status v0.1.0` reports
the release as not cuttable for exactly that reason.

**Simulation.** gale runs Renode emulation tests in CI
(`.github/workflows/renode-tests.yml`). jess is the hub meant to carry
relay's flight stack onto real hardware. Today it runs that stack under
Renode emulation, and its README states there is no hardware in that loop
yet.

**Hardware.** jess plans the path from hardware-in-the-loop against
simulation to a Pixhawk 6X-RT board. 20 of the 24 requirements jess's
`rivet coverage --tests` lists are `REQ-PIX-*` hardware requirements, and
jess#298 tracks hardware verification markers for them. No hardware result
is recorded yet.

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

    subgraph right["Right side of V (verification gates)"]
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
{% </mermaid> %}

A V-model with links shows which test relates to which requirement. A
V-model with gates shows which test can fail against it. Every arrow on the
right side above should be the second kind.

## What we measured in gale

rivet[^rivet] is our artifact store: a git-native, schema-typed graph of
requirements, architecture, design and verification artifacts, with
releases as scoped sets of artifacts. Here is gale measured with it on
26 October 2026.

| Number | What it counts | Command |
|---|---|---|
| 491 | Requirements: 111 stakeholder, 51 system, 329 software | `rivet stats` |
| 276 | Verification artifacts: 141 software, 58 unit, 37 integration, 40 system | `rivet stats` |
| 276 of 329 | Software requirements with a `verification-criteria` field | `rivet list --type sw-req --format json --full` |
| 53 of 329 | Software requirements without that field | same |
| 42 of 53 | ...of which have an incoming `verifies` link | same, plus the four verification types |
| 27 of 53 | ...of which have status `verified` | same |
| 11 of 329 | Software requirements with neither criteria nor a `verifies` link, all `proposed` | same |
| 302 of 329 | Software requirements with a `verifies` link (91.8%) | `rivet coverage`, rule `swe1-has-verification` |
| 47 of 51 | System requirements with a `verifies` link (92.2%) | `rivet coverage`, rule `sys2-has-verification` |
| 252 of 276 | Verification artifacts that declare a `method` | `rivet list ... --format json --full` |
| 135 / 73 / 42 / 2 | ...declaring automated-test / formal-verification / static-analysis / review | same |
| 0 of 485 | Artifacts with a source test marker | `rivet coverage --tests` |

Calling all 53 wishes would overstate the problem. The metric is a
missing field, and a missing field is a proxy. 42 of the 53 have a
verification measure linked, 27 have status `verified`, and some state
their criteria in the description instead of the field. `REQ-DRV-BREADTH-001`, for example, requires that a four-driver
image "SHALL fit the F100 8 KiB SRAM budget" and add no trusted native
atoms, which a build can check. The requirements that meet the definition
of a wish are the 11 with neither criteria nor a link. All 11 are
`proposed`; 9 are scoped to releases v0.11.0 to v1.0.0 and 2 to no release.

The `0 of 485` line measures the instrument. `rivet coverage --tests`
counts source markers such as `// rivet: verifies ...` in source and test
files. gale records verification as separate artifacts with `verifies`
links, so the scanner finds nothing and reports every requirement and
design element as uncovered. relay (0 of 340) and jess (0 of 24) show the
same. In relay#605 a maintainer re-measured with the link-based census and
put relay's real gap at 15 artifacts rather than the 207 the issue was
opened with; `rivet coverage` on relay gives 267 of 279 software
requirements linked.

The stages a requirement passes through, and where gale stands at each:

| Stage | What it means | gale on 26 October 2026 |
|---|---|---|
| Criteria stated | The requirement is verifiable | 276 of 329 by field, more in description text |
| Measure linked | A verification artifact claims to verify it | 302 of 329 (`rivet coverage`) |
| Result recorded | A pass/fail result is attached in rivet | 0: `rivet trace-results SWREQ-SEM-P01` reports "no test evidence" |
| Status verified | The artifact's `status` field says `verified` | 27 of 329, set in YAML; none rests on a result recorded in rivet |

rivet can already record results. It ships `rivet import-results --format
junit` and `rivet verify`, which advances a requirement to `verified` when
it has verifying test evidence. gale has not wired its CI to either, and
its `results/` directory does not exist yet.

## What we get wrong

**The release gate does not catch missing criteria today.** `rivet release
status` keys on artifact status, not on whether criteria exist. 47 of the
57 software requirements with a `release:` have no `verification-criteria`
field. 25 of those 47 sit in eight releases (v0.3.0, v0.4.0, v0.5.0,
v0.6.0, v0.7.0, v0.8.0, v0.9.0, v0.10.0) that `rivet release status`
reports as "Cuttable". v0.1.0, which is not cuttable, contains none of the
47; it is blocked because the ten semaphore requirements and their system
requirement are `approved` and not yet `verified`. The 9 of the 11 wishes
that carry a release sit in not-cuttable releases, and they are blocked by
their `proposed` status, not by the missing criteria.
rivet#1127 proposes a wish detector that would report requirements without
criteria, so the gap is visible at the gate.

**The links exist, the evidence does not.** 302 software requirements have
a verification measure linked, and none has a recorded result. 91.8% linked
is not 91.8% verified. rivet#1129 tracks connecting recorded results to
`trace-results` and the release gate; the import path itself already
exists.

**A method field is a declaration.** 252 verification artifacts say how
they verify, and 73 say formal verification. That is a statement about
intent until a result is recorded.

**Our marker scanner reports zero where the link-based gap is small.** It
reports 0% for all three repositories, while `rivet coverage` leaves 27 of
329 software requirements unlinked in gale and 12 of 279 in relay. rivet#1128
proposes hardware verification markers, and gale#461 and relay#605 track
the triage of the uncovered lists. relay#606 and spar#523, which asked to
add `rivet validate` to CI, were closed because validate is already a
required check in both.

**rivet's commit trailers are not configured in gale.** rivet supports
`Implements:`, `Fixes:`, `Verifies:`, `Satisfies:` and `Refs:` trailers and
can analyse them with `rivet commits`. gale's `rivet.yaml` has no
`commits:` section, so its history is not yet part of the trace.

## Counterarguments we take seriously

**"A requirement may be verified by analysis or review without an automated
test."** Yes. The PAM lists both as verification measures, and review is
essential for intent, hazard analysis and verification adequacy. As a
repeated check of routine correctness it scales poorly. In gale, 2 of 252
measures that declare a method declare review.

**"Coverage is not correctness, and a marker is not a result."** Agreed,
and our own numbers show it: 91.8% linked, zero results recorded, and a
marker scanner that reports zero for a different reason. Each of these
measures something narrower than "verified".

**"Your system may optimise for links and markers instead of verification."**
This is the real risk. An agent can write a test that technically links to
a requirement and checks almost nothing. The defence is gate potency: a
gate has to be shown to fail when the artifact is wrong, and our
`gate-potency` skill audits that by injecting a violation and checking that
CI goes red. The human reviews the gates, not every diff.

**"What stops an agent weakening a requirement to make a gate pass?"**
Nothing mechanical. Requirement text lives in git, so a weakened
requirement is a reviewable diff, and the review of requirement changes
stays with a human.

**"What if every gate passes and the result is still unsafe?"** Then the
specification was wrong. The oracles check behaviour against the
specification; whether the specification is right remains a human judgement
and the place where escalation goes.

## What to take from this

A requirement is real when something can fail against it. For each one,
ask which oracle challenges it: a test, a proof, a simulation, a hardware
run or a review. If the answer is none, add a gate or retire the
requirement.

Measure your wishes with an instrument that matches how you record
verification. In gale, the missing-field count gives 53, the marker scanner
gives 485, and the strict definition (no criteria and no linked measure)
gives 11. The 11 are the wishes; the other two numbers describe the
instruments.

Treat links as the start of the trace. The trace closes when a result is
recorded against the requirement and the release gate reads it.

## Limits and how we measured

This is one organisation's reading of ASPICE, applied to gale, relay, jess
and rivet. None of it has been assessed by an ASPICE assessor, and we do
not claim compliance. All of it is work in progress.

Measurements used rivet 0.39.0 (the version our CI pins), on gale at
`463b3a3` (26 October 2026), relay at `21c9472` and jess at `1f93f98`. The
commands were `rivet stats`, `rivet coverage`, `rivet coverage --tests`,
`rivet release status <version>` for every release in gale, `rivet
trace-results SWREQ-SEM-P01`, and `rivet list --type <type> --format json
--full` for `sw-req` and the four verification types. Criteria, status,
release and method counts come from the JSON fields; `verifies` links are
counted as incoming links from verification artifacts.

The ASPICE interpretation is the author's. An assessor might read the PAM
differently.

[^aspice-pam]: VDA QMC, *Automotive SPICE® Process Assessment / Reference
Model*, version 4.1, 24 August 2026. Available only by download from the
[VDA QMC Automotive SPICE page](https://vda-qmc.de/en/automotive-spice/).
This post quotes short passages from §3.3.4, SYS.2.BP1, SYS.2.BP5, SWE.4.BP1
and Table 1 for the purpose of commentary; the copyright remains with VDA
QMC. The quoted passages are collected in
[`docs/research/aspice-pam-4.1-quotes.md`](https://github.com/pulseengine/pulseengine.eu/blob/main/docs/research/aspice-pam-4.1-quotes.md).

[^iso-29148]: ISO/IEC/IEEE 29148:2018, *Systems and software engineering:
Life cycle processes: Requirements engineering*. Named in SYS.2.BP1 Note 1
of PAM 4.1 as one example, alongside ISO 26262-8 and the INCOSE Guide for
Writing Requirements, of where requirement characteristics are defined.

[^rivet]: PulseEngine, *rivet*,
[github.com/pulseengine/rivet](https://github.com/pulseengine/rivet).

---

*This post is part of [PulseEngine](/), a WebAssembly Component Model engine
for safety-critical systems, with formally verified components (work in
progress). Prior posts in the arc:
[SAFe was built for slow humans](/blog/safe-was-built-for-slow-humans/),
[Can we deliver X by January?](/blog/can-we-deliver-x-by-january/),
[The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/).*
