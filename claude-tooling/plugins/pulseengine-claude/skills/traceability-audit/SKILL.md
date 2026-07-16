---
name: traceability-audit
description: This skill should be used to ensure the rivet traceability graph is COMPLETE and bidirectional across the whole V — requirement → architecture → design → code, and back up through unit, integration, and system/requirements-qualification tests — for ANY safety standard the project targets (DO-178C aerospace, ISO 26262 automotive, EN 50128 rail, IEC 61508 functional-safety, IEC 62304 medical, ASPICE, SOTIF, EU AI Act), including components certified to several at once. Use it both while authoring (research/exploration phase — add findings and wire their linkages as you go) and as the blocking check before a release. Use it whenever the question is "are all the rivet artifacts in and properly linked", "is every requirement designed/implemented/tested at each level", "did we capture this finding into rivet", or before tagging when the V-model gate must hold. It defines the closure rules the release V-model gate enforces; pair with oracle-gate-a-change (rivet check is the oracle) and proof-synthesis (proofs are right-side evidence alongside tests).
metadata:
  author: pulseengine.eu
  version: "0.1.0"
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

## Closure rules — the audit (mechanical; `rivet check` is the oracle)

Run `rivet validate && rivet check && rivet coverage` for each declared schema.
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
