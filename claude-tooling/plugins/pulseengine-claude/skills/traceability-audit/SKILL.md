---
name: traceability-audit
description: This skill should be used to ensure the rivet traceability graph is COMPLETE and bidirectional across the whole V — requirement → architecture → design → code, and back up through unit, integration, and system/requirements-qualification tests — for ANY safety standard the project targets (DO-178C aerospace, ISO 26262 automotive, EN 50128 rail, IEC 61508 functional-safety, IEC 62304 medical, ASPICE, SOTIF, EU AI Act), including components certified to several at once. Use it both while authoring (research/exploration phase — add findings and wire their linkages as you go) and as the blocking check before a release. Use it whenever the question is "are all the rivet artifacts in and properly linked", "is every requirement designed/implemented/tested at each level", "did we capture this finding into rivet", or before tagging when the V-model gate must hold. It defines the closure rules the release V-model gate enforces; pair with oracle-gate-a-change (rivet check is the oracle) and proof-synthesis (proofs are right-side evidence alongside tests).
metadata:
  author: pulseengine.eu
  version: "0.2.0"
---

# Traceability audit

Certification credit — in *any* domain — comes from a **closed, bidirectional**
trace: every requirement flows down to architecture, design, and code, and back
up through verification evidence at each level, with nothing orphaned in either
direction. The standards differ in vocabulary and integrity levels, not in this
shape. In PulseEngine the graph is rivet's typed artifacts, so completeness is a
**mechanical oracle** (`rivet check`), not a spreadsheet review. This skill owns
the chain definition and the closure rules, standard-agnostically; the release
V-model gate runs it before tagging, and the feature loop authors against it.

## The V — the same shape in every standard

```
 stakeholder need / hazard / safety goal
        │ derives
        ▼
 REQUIREMENT (one or more decomposition levels)        ◄── system / qualification test  (verifies top-level req)
        │ satisfies                                         ▲
        ▼                                                   │
 ARCHITECTURE  (spar / AADL)                           ◄── integration test             (verifies architecture)
        │                                                   ▲
        ▼                                                   │
 DESIGN  (detailed / low-level)                        ◄── unit / module test           (verifies design / LLR)
        │ implements                                        ▲
        ▼                                                   │
 SOURCE CODE  ──────────────────────────────────────────────┘
        + every test level produces a PASSING result; MC/DC (witness) + attestation (sigil) layer on top
```

Generic link verbs rivet uses across schemas: `derives`, `satisfies`,
`implements`, `verifies`, `executes`. Every standard's schema ships completeness
objectives (e.g. "every requirement is verified by a test", "every unit is
covered") that `rivet check` enforces.

## Cross-standard mapping — audit whichever schema(s) the project declares

| Generic level | DO-178C (aero) | ISO 26262 (auto) | EN 50128 (rail) | IEC 61508 (FS) | IEC 62304 (med) |
|---|---|---|---|---|---|
| Goal / hazard | — (system) | safety-goal | — | safety-req | — |
| Requirement(s) | hw-sw-req (HLR) → lw-sw-req (LLR) | functional → technical → software-safety-requirement | sw-safety-integrity-req → sw-req-spec | sw-safety-req | sw-req |
| Architecture | (architecture) | software architecture | sw-design-spec (arch) | (architecture) | (architecture) |
| Design | sw-design / lw-sw-req | software-unit-design | sw-design-spec | sw-design | sw-detailed-design |
| Code | source-code | (unit impl) | (module) | (module) | sw-unit |
| **Unit test** | lw-sw-test-case | unit-test (unit-test-plan) | sw-module-test | (unit verification) | sw-unit-verification |
| **Integration test** | (integration) | software integration test | sw-integration-test | sw-integration-test | sw-integration-test |
| **System / qualification test** | hw-sw-test-case | software qualification test | (overall sw test) | sw-verification | sw-system-test |
| Integrity level | DAL | ASIL | SIL | SIL | safety class |

A component certified to several standards carries several schemas at once;
audit each, and reuse evidence across them where the artifact is the same. If a
target standard isn't listed, the generic chain + closure rules still apply —
map to that schema's type names.

## Step 0 — can the loaded schema even express the right side of the V?

**Do this before auditing anything.** An audit against a schema that has no
verification type is itself vacuous: it runs, reports green, and gates nothing.

```sh
rivet schema list      # do the loaded schemas define a test / verification type?
rivet stats            # which types actually carry artifacts?
```

If the answer is no, **that is the finding** — stop and drive the schema change;
do not report a clean audit. Field cases, both discovered only by running the
tool rather than reading YAML: one repo loaded `common + stpa + dev`, where `dev`
is exactly `requirement, design-decision, feature` — **no test type to point at**,
`verifies` recorded provenance but gated nothing, and the status lifecycle
structurally capped at `implemented` (**zero** artifacts `verified`/`accepted`
project-wide). Another reported `requirement-coverage 0/45 = 0.0%` with its
`verification-method` fields **silently ignored** — "field not defined in schema
for type 'requirement'".

Symptoms that mean you are on this rock, not doing well:
- `rivet validate` is **green with the entire right arm of the V empty**, or
  emits the same warning on every requirement so the team learned to ignore it;
- every requirement tops out at `implemented`;
- verification fields exist in the YAML but no rule reads them.

## Closure rules — the audit (mechanical; `rivet check` is the oracle)

Run `rivet validate && rivet check && rivet coverage` for each declared schema.
Use the mechanisms rivet actually ships for the right side — **name them, don't
re-derive them by eye**:

- `rivet coverage` reports **combined V-closure**; `rivet coverage --tests` maps
  tests to requirements.
- `rivet verify <ID>` advances an artifact on a `verifies` link **or** a
  `// rivet: verifies <ID>` source marker — the cheap path when hand-authoring
  one artifact per test is the reason it never happens.
- the `requirement-verification` rule surfaces requirements with **no incoming
  `verifies`**. Treat its output as the burn-down list, not as noise.

**Warnings are not a pass.** A release bar of "0 errors" tolerates exactly the
debt this audit exists to find — one repo shipped on `FAIL (0 errors, 87
warnings, 33 broken cross-refs)` where the warnings *were* the unmapped
verification.
Treat any open edge as a finding. For **every `approved`/`implemented`
artifact**, both directions must close:

Forward (nothing under-specified):
- every requirement `satisfies`-links to architecture **and** decomposes to
  design / lower-level requirements; no requirement without design; no design
  without code (`implements`).

Backward (nothing unverified) — the part a coarse "has a `verifies` link" check
misses:
- every **design / low-level requirement** has ≥1 **unit/module test** that
  `verifies` it, **with a passing executed result**;
- every **architecture / integration boundary** has ≥1 **integration test**;
- every **top-level / safety requirement** has ≥1 **system / qualification
  test** with a passing result;
- every new decision/branch has a **witness MC/DC** truth-table with zero gap
  rows at the integrity level required; every shipped artifact is **sigil**-
  attested;
- the declared **integrity level** (DAL/ASIL/SIL/class) is set and consistent
  down the chain;
- no orphan tests (a test with no requirement it verifies); no requirement whose
  only verification lacks an executed, passing result.

Green `rivet check` = the graph is closed; passing test **results** = the right
side is real. Both are required. If `rivet check` can't express a rule, that's a
tooling gap → [`report-tool-friction`], then audit it by hand.

## Research / exploration phase — wire it as you go, don't retrofit

The cheapest time to keep the trace closed is while the work is fresh; the most
expensive is reconstructing it at release.
- **Capture each finding as a rivet artifact immediately** — a requirement,
  design decision, hazard, constraint, or risk goes in as typed YAML the moment
  it's understood, not "later".
- **Wire its linkages at creation** — link up (what it derives from / affects)
  and down (what it constrains / will be satisfied by), so the graph never
  accrues orphans.
- **New findings re-open the trace** — a finding that changes behavior links to
  the requirements/decisions it invalidates or extends; run `rivet check` so the
  impact surfaces now, not at the gate.
- Keep `rivet coverage` trending toward full as work proceeds.

This is where [`capture-session-learnings`] hands off: a durable finding becomes
a traced rivet artifact, not just a memory note.

## Where this composes
- [`release-execution`] — its step-4 V-model gate **is** this audit run before
  tagging; this skill is the detailed, standard-agnostic closure-rule definition.
- [`pulseengine-feature-loop`] — step 3 authors these artifacts; this skill says
  what "complete and linked" means at every level for whichever standard applies.
- [`stpa-audit`] — losses/hazards/constraints are the top of this chain.
- [`proof-synthesis`] — machine-checked proofs are right-side verification
  evidence alongside the test levels (`verifies` them too).
- [`oracle-gate-a-change`] — `rivet check` over these rules is the oracle.

## Anti-patterns
- **Hard-coding one standard.** The chain is universal; a component may be
  ISO 26262 *and* IEC 61508 at once. Audit every declared schema.
- **Retrofitting traceability at release** instead of wiring it during research.
- **Coarse "tested = has a `verifies` link"** without the level distinction — a
  requirement verified only by a unit test has no qualification evidence; a
  design with only a system test has no unit coverage.
- **A `verifies` link with no executed, passing result** — a planned test isn't
  verification.
- **One-directional checking** — forward-only misses unverified requirements;
  backward-only misses unimplemented ones.
- **Findings left in prose/chat** instead of captured as linked rivet artifacts.
