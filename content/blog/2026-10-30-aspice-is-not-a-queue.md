+++
title = "Read ASPICE as a pattern: 302 of gale's 329 software requirements have a check linked, none has a result"
description = "Read as a pattern, ASPICE's engineering processes ask that every requirement be traceable to a verification measure that can fail, and to a recorded result. Measured in gale on 26 October 2026: 302 of 329 software requirements have a verification measure linked, none has a recorded result, and 25 requirements marked verified without results sit in releases rivet reports as cuttable."
date = 2026-10-30
draft = true
[taxonomies]
tags = ["aspice", "verification", "traceability", "process", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**In gale, 302 of 329 software requirements have a verification measure
linked, and none of them has a recorded result.** gale's CI imports no test
results into rivet, so the trace stops at the link.

We read ASPICE's engineering processes as a design pattern: a requirement is
real when a test, proof, simulation, hardware run or review can fail against
it, and the trace runs from the requirement to that check and on to its
result. Measured that way, gale's links are in place and its evidence is
not.
{% </insight> %}

The earlier posts in this series argued that the bottleneck in an agent
factory is verification and decisions ([SAFe was built for slow
humans](/blog/safe-was-built-for-slow-humans/)) and estimated delivery from
gates ([Can we deliver X by January?](/blog/can-we-deliver-x-by-january/)).
Both assume the thing being verified is worth verifying. This post looks at
the requirements themselves: what the Automotive SPICE process assessment
model (PAM)[^aspice-pam] asks of them, and how far our own repositories are
from that.

## What the PAM asks of a requirement

Section 3.3.4 of PAM 4.1 rejects the process-blueprint reading in its
title: "Why a PRM and PAM are not a lifecycle model or development process
blueprint". It calls each process a "distinct conceptual silo" and states
that a PRM/PAM "neither predefines, nor discourages, any order in which PRM
processes or Base Practices are to be performed. Ultimately, in Automotive
SPICE® consistency must be fulfilled as required by the
traceability/consistency Base Practices in MAN.3 or SYS.x, SWE.x, and
HWE.x". In MAN.3 that consistency is consistency of the project plan
(MAN.3.BP9); in the SYS, SWE and HWE processes it is consistency between
requirements, architecture, verification measures and results, which is
the part this post is about. The same section adds that "it is the
assessor's responsibility to map the elements in such a HOW level to the
Assessment Indicators", which is the direction this post argues for: map
the work you do onto the model.

The PAM names no lifecycle model. MAN.3.BP2 asks for one "appropriate to
the scope, context, and complexity of the project", so in our reading an
iterative or flow-based lifecycle can qualify, as long as the project
defines it. Four passages from the engineering processes carry the rest
of the argument:

- **Verifiability.** SWE.1.BP1 Note 2 (the same text as SYS.2.BP1 Note 2)
  gives, as an informative example of the requirement characteristics an
  organisation defines, "verifiability (i.e., verification criteria being
  inherent in the requirements text)". Note 1 names ISO/IEC/IEEE
  29148[^iso-29148], ISO 26262-8 and the INCOSE guide as places where such
  characteristics are defined.
- **Pass/fail criteria.** SWE.6.BP1 asks that verification measures for the
  software be specified against the software requirements, including
  "pass/fail criteria for the verification measures".
- **Recorded results.** SWE.6 outcome 3 requires that verification results
  are recorded, and outcome 5 that they are traceable to the verification
  measures.
- **Links are not consistency.** SWE.6.BP4 Note 4 says "Traceability alone,
  e.g., the existence of links, does not necessarily mean that the
  information is consistent." The sentence recurs in the other traceability
  base practices.

Together these describe a pattern: a requirement states how it can be
checked, a verification measure with pass/fail criteria is traced to it, the
measure runs, and its result is recorded and traced back. A requirement
that nothing can fail against fits none of that, however many approvals it
carries.

## What the pattern does not cover

This reading is narrower than ASPICE. What it describes is the engineering
processes performed at capability level 1, process attribute PA 1.1. OEMs
contract for capability level 2 or 3. That brings PA 2.1 and PA 2.2:
planned and monitored performance, review and approval criteria for work
products, work-product review and baselines. SUP.1 asks for independent
quality assurance and SUP.8 for configuration management. The pattern
replaces none of these obligations. Consistency is semantic, and in
practice it is shown by review, so review is the consistency oracle the
PAM relies on. A two-person team with rivet and a CI gate can hold the
pattern, but would still need PA 2.x evidence to be rated above CL1.

The pattern also says little about how organisations get assessed. A
capability rating can rise while the requirements stay unverifiable only in
a poorly run assessment, or in a self-assessment against a mapping of
phases to processes. A competent assessor rating SWE.1.BP1 against the
organisation's defined characteristics should catch it. CMMI ratings,
which grew out of the earlier CMM, carry the same limit.

## Oracles, and what each can catch

An oracle is a mechanical or human check that can confirm or deny that an
artifact meets a requirement. The PAM's Table 1 lists the kinds of
verification measure without ranking them: test cases, measurements,
calculations, simulations, reviews and analyses. The ranking below is ours.

| Oracle | What it challenges | Strength and limit |
|---|---|---|
| **Human review** | "Does this look right?" | Required for intent, hazards, adequacy and semantic consistency. Weak as a repeated check of routine correctness |
| **Static analysis** | "Does this code have undefined behavior?" | Catches whole bug classes, within the analyzer's model |
| **Automated test** | "Does this code pass these cases?" | Catches regressions, only for the cases written |
| **Formal proof** | "Does this property hold for all inputs?" | Proves the stated property for all inputs, relative to the spec and the trusted base |
| **Simulation** | "Does the system behave in a modelled environment?" | As good as the model's fidelity |
| **Hardware** | "Does the real silicon behave?" | Most reality-grounded and least exhaustive: no model gap, few inputs, limited observability |

Table 1 also notes that "software units generally cannot be verified by
means of calculations or analyses". The same PAM lists static analysis
among unit verification measures (SWE.4.BP1 Note 1), so we read the note as
excluding hand calculation, not tool-based code analysis; whether a Verus
proof over a unit counts as an "analysis" in the note's sense is an
assessor's call. Here is where each oracle meets a requirement in our
repositories.

**Architecture.** In gale every software requirement derives from a system
requirement, and every architecture component is allocated from a software
requirement: 329/329 and 52/52 in `rivet coverage`. The links are
hand-written YAML, and `rivet validate` fails when one points at an
artifact that does not exist. rivet can also import AADL models through
spar's parser and analysis crates; gale does not use that path.

**Formal proof.** gale's semaphore, a Rust port of Zephyr's `k_sem`, has
ten software requirements, `SWREQ-SEM-P01` to `SWREQ-SEM-P10`. Most are
stated as Verus `ensures` and invariant clauses in `src/sem.rs`. For P4 and
P6 to P8 the clauses pin count and queue length, but not which thread
wakes or which error code returns. Separately, `proofs/sem_proofs.v` is a
Rocq development that proves count invariants over an abstract model; its
theorems carry no P-labels. rivet records no evidence for any of the ten:
all are `approved`, and `rivet release status v0.1.0` reports the release
not cuttable for that reason.

**Simulation and hardware.** gale has a Renode emulation workflow
(`.github/workflows/renode-tests.yml`). jess is the hub meant to carry
relay's flight stack onto a Pixhawk 6X-RT board; today it runs that stack
under Renode, and its README states there is no hardware in that loop yet.
20 of the requirements jess's marker scan lists are `REQ-PIX-*` hardware
requirements, which jess#298 tracks. No hardware result is recorded.

## What we measured in gale

rivet[^rivet] is our artifact store: a git-native, schema-typed graph of
requirements, design and verification artifacts, with releases as scoped
sets of artifacts. Measured on gale at `463b3a3`, 26 October 2026, each row
below counts something narrower than "verified":

| Number | What it counts | Source |
|---|---|---|
| 491 | Requirements: 111 stakeholder, 51 system, 329 software | `rivet stats` |
| 302 of 329 | Software requirements with an incoming `verifies` link (rivet's rule `swe1-has-verification`; the PAM practice is SWE.6.BP4) | `rivet coverage` |
| 47 of 51 | System requirements with one (rivet's `sys2-has-verification`; PAM SYS.5.BP4) | `rivet coverage` |
| 0 | Software requirements with a recorded result | `rivet trace-results`; gale has no `results/` directory |
| 27 of 329 | Software requirements with no `verifies` link | `rivet list --format json --full` |
| 53 of 329 | Software requirements with no `verification-criteria` field | same |
| 27 of 329 | Software requirements with status `verified`, all of them among the 53 | same |
| 252 | Verification artifacts (of 276 in total) that declare a method: 135 automated test, 73 formal verification, 42 static analysis, 2 review | same |
| 0 of 485 | Requirements and design artifacts with a source test marker | `rivet coverage --tests` |

**Linked, with no results.** We call the 302 *unverified artifacts*:
something can fail against each of them, and nothing has been recorded
doing so. `rivet import-results --format junit`
records results and `rivet trace-results` reads them, but `rivet verify`
accepts a link as evidence and `rivet release status` keys on status, so
neither requires a recorded pass yet. That half is rivet's gap; rivet#1129
proposes closing it. A declared method is a statement of intent in the same
way: 73 artifacts say "formal verification", and none has a result.

**Wishes.** The 27 requirements with no linked measure are the ones nothing
currently challenges. They come in two kinds. 11 have no criteria field
either; all are `proposed`, 9 are scheduled for v0.11.0 to v1.0.0, and
several are concrete enough to test as written. `REQ-OS-MPU-001` requires
that an out-of-bounds access by one tenant "faults rather than silently
corrupting a sibling". These are deferred intentions. The other 16 state
criteria and have no measure; all are `draft` or `proposed` with no
release. These are unimplemented obligations, and each needs a gate.

**The missing field is a proxy.** Of the 53 without a `verification-criteria`
field, 42 have a measure linked, and some state criteria in the description.
`REQ-DRV-BREADTH-001` requires that a four-driver image "SHALL fit the F100
8 KiB SRAM budget" and add no trusted-native atoms "beyond the existing
four", which a build can check.

**The marker scan measures the instrument.** `rivet coverage --tests` scans
`src/` and `tests/` by default for markers such as `// rivet: verifies ...`.
gale has none and records verification as separate artifacts, so all 485
system requirements, software requirements and detailed-design artifacts
the scan checks come back uncovered. relay (0 of 340) and jess (0 of 24)
look the same. In relay#605 a maintainer re-measured with the link census
and put relay's gap at 15. `rivet coverage` agrees: 12 of 279 software
requirements, 2 of 38 system requirements and 1 of 23 detailed designs
are unlinked.

## What we get wrong

**`verified` without results, in releases reported as cuttable.** All 27
software requirements marked `verified` were set by hand in YAML, and none
has a recorded result. 25 of them sit in eight releases (v0.3.0, v0.4.0,
v0.5.0, v0.6.0, v0.7.0, v0.8.0, v0.9.0, v0.10.0) that `rivet release
status` reports as cuttable. An assessor would likely record that as a
status-model inconsistency, with SWE.6 outcomes 3 and 5 not achieved for
those releases.

**The release gate does not see missing criteria.** It keys on status. 47 of
the 57 software requirements with a `release:` have no criteria field, and
the 25 above are among them. v0.1.0, which is not cuttable, contains none
of the 47; it is blocked because its ten semaphore requirements and their
system requirement are `approved` and not `verified`. The 9 scheduled
requirements with neither criteria nor a measure sit in releases that are
not cuttable, blocked by their `proposed` status. rivet#1127 proposes a
detector that would report requirements without criteria at the gate.

**Commit history is outside the trace.** rivet supports configurable commit
trailers such as `Implements:`, `Fixes:`, `Verifies:`, `Satisfies:` and
`Refs:`, analysed by `rivet commits`. gale's `rivet.yaml` has no `commits:`
section.

**Our issues outran our measurements.** gale#461 and relay#605 were opened
against the marker-scan counts; relay#605 has since been re-scoped to the
15. relay#606 and spar#523, which asked to add `rivet validate` to CI, were
closed because `rivet validate` already runs inside a required CI check in
both.

## Counterarguments we take seriously

**"A requirement may be verified by analysis or review without an automated
test."** Yes. The PAM lists both, and review remains the oracle for intent,
hazard analysis, verification adequacy and semantic consistency. It scales
poorly as a repeated check of routine correctness, which is where the
mechanical oracles earn their place.

**"Your system may optimise for links instead of verification."** This is
the real risk, and our numbers show its first form: 302 links, no results.
An agent can also write a test that links to a requirement and checks
almost nothing. The defence is gate potency, showing that a gate goes red
when the artifact is wrong; our `gate-potency` skill audits that by
injecting a violation. The human reviews the gates, not every diff.

**"What stops an agent weakening a requirement to make a gate pass?"**
Nothing mechanical. Requirement text lives in git, so a weakened
requirement is a reviewable diff, and that review stays with a human.

**"What if every gate passes and the result is still unsafe?"** Then the
specification was wrong. The oracles check behaviour against it; whether it
is right remains a human judgement and the place escalation goes.

## What to take from this

For each requirement, name the check that can fail against it and the place
its result is recorded. If there is no check, add a gate or retire the
requirement. If there is a check and no result, the trace is not closed.

Count with an instrument that matches how verification is recorded. In
gale the missing-field count gives 53, the marker scan 485, and the link
census 27. Only the link census counts requirements that nothing currently
challenges.

## Limits and how we measured

This is one organisation's reading of ASPICE, applied to gale, relay, jess
and rivet, all of which are work in progress. None of it has been assessed;
we claim no compliance and no capability level. An assessor might read the
PAM differently.

Measurements used rivet 0.39.0 (the version this site's CI pins; gale,
relay and jess CI pin other versions), on gale at `463b3a3` (26 October
2026), relay at `21c9472` and jess at `1f93f98`. Commands: `rivet stats`,
`rivet coverage`, `rivet coverage --tests`, `rivet release status
<version>` for every release a gale software requirement names, `rivet
trace-results SWREQ-SEM-P01`, and `rivet list --type <type> --format json
--full` for `sw-req` and the four verification types. Criteria, status,
release and method counts come from the JSON fields; `verifies` links are
counted as incoming links from verification artifacts.

[^aspice-pam]: VDA QMC, *Automotive SPICE® Process Assessment / Reference
Model*, version 4.1, dated 24 August 2026, available only by download from
the [VDA QMC Automotive SPICE page](https://vda-qmc.de/en/automotive-spice/).
Automotive SPICE defines its own measurement framework, an adaption of
ISO/IEC 33020:2019. This post quotes short passages from §3.3.4 (including
its title), MAN.3.BP2, SYS.2.BP1, SWE.1.BP1, SWE.4.BP1, SWE.6.BP1,
SWE.6.BP4 and Table 1 as short quotations for commentary (quotation
right); the copyright remains with VDA QMC. Locations are listed in
[`docs/research/aspice-pam-4.1-quotes.md`](https://github.com/pulseengine/pulseengine.eu/blob/main/docs/research/aspice-pam-4.1-quotes.md).

[^iso-29148]: ISO/IEC/IEEE 29148:2018, *Systems and software engineering:
Life cycle processes: Requirements engineering*. Named in SWE.1.BP1 Note 1
of PAM 4.1 as one example, alongside ISO 26262-8 and the INCOSE Guide for
Writing Requirements.

[^rivet]: PulseEngine, *rivet*,
[github.com/pulseengine/rivet](https://github.com/pulseengine/rivet).

---

*This post is part of [PulseEngine](/), a WebAssembly Component Model engine
for safety-critical systems, with machine-checked proofs for parts of it
(work in progress). Recent posts:
[The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/),
[Agents don't tidy up](/blog/agents-dont-tidy-up/),
[SAFe was built for slow humans](/blog/safe-was-built-for-slow-humans/),
[Can we deliver X by January?](/blog/can-we-deliver-x-by-january/).*
