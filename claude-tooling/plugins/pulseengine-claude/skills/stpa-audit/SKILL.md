---
name: stpa-audit
description: This skill should be used when conducting or AUDITING an STPA (System-Theoretic Process Analysis) or STPA-Sec (its security extension) hazard analysis on a PulseEngine project — including "do an STPA", "audit the hazard analysis", "are our losses/hazards/UCAs complete", "STPA-Sec review", "security hazard analysis", "check the safety/ artifacts", or before a release whose V-model gate depends on the hazard analysis being sound. Fires whenever the front-end of the safety case (losses → hazards → constraints → UCAs → loss scenarios) needs to be built or verified. rivet already provides the typed schema, link semantics, and `rivet check` topology validation — this skill operationalizes the method and the audit on top of it.
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# STPA / STPA-Sec audit

STPA is the hazard-analysis front-end of the V-model: it derives, top-down,
*what must never happen* (losses), *the system states that lead there*
(hazards), *the constraints that prevent them*, and *how control actions go
wrong* (UCAs → loss scenarios). STPA-Sec is the same machinery turned on an
adversary: security losses, security hazards, and unsafe control actions an
attacker can *cause*. In PulseEngine this is not prose — it is a **typed graph
in rivet**, which makes completeness a *mechanical oracle* and soundness a
*reasoning* review. This skill covers both building it and, especially,
auditing it.

## The rivet vocabulary (ground truth)

STPA artifacts: `loss`, `hazard` (and `sub-hazard`), `system-constraint`,
`controller` / `controlled-process` (the control structure),
`controller-constraint`, `uca`, `loss-scenario`.

STPA-Sec artifacts (the security inversion): `sec-loss` (with `cia-impact`,
`stakeholders`), `sec-hazard` (`cia-impact`, `severity`,
`leads-to-sec-loss`), `sec-constraint` (`prevents-sec-hazard`), `sec-uca`
(`uca-type`, `context`, **`adversarial-causation`** — inject / spoof / tamper
/ intercept — and `attacker-type`), `sec-scenario` (`attack-vector`,
`attacker-type`).

The schema lives in rivet (`schemas/stpa-sec.yaml`); rivet itself dogfoods it
under `safety/stpa/` and `safety/stpa-sec/`. **Read those as the worked
example** before auditing another project's analysis.

## The audit — two halves, both required

### Half 1 — Completeness (mechanical; this is the oracle)
Run rivet and treat a failing link-topology as a hard finding, per
[`oracle-gate-a-change`]:
```
rivet validate          # schema + types well-formed
rivet check             # link topology — the STPA closure rules below
rivet coverage          # is the hazard analysis traced into the rest of the V?
```
The closure rules `rivet check` should enforce (flag any gap as a blocker):
- every `loss` is led to by ≥1 `hazard`; no orphan losses, no hazard without a loss;
- every `hazard` is prevented by ≥1 `system-constraint` / `controller-constraint`;
- the control structure is complete — every `controller` has its
  `controlled-process` and the relevant control/feedback actions;
- every `uca` traces to a `hazard` **and** has ≥1 `loss-scenario` explaining
  its causation;
- **STPA-Sec:** every `sec-hazard` has a `sec-constraint`; every `sec-uca`
  has non-empty `adversarial-causation` **and** `attacker-type`; every
  `sec-scenario` names an `attack-vector`; `cia-impact` is set on sec-losses
  and sec-hazards and the triad (C, I, A) is consciously covered, not partial.

If `rivet check` can't express one of these rules, that's a tooling gap →
[`report-tool-friction`] against rivet, then audit it by hand for now.

### Half 2 — Soundness (reasoning; clean-room)
A green `rivet check` proves the *graph is closed*, not that the *analysis is
right*. Per [`clean-room-verification`], spawn a cold reviewer and have them
re-derive a sample, not infer from the existing labels:
- Are the losses the *actual* stakeholder losses, or a convenient subset?
- Is each hazard a genuine worst-case **system state**, not a failure mode or
  a cause? (STPA hazards are states, not events.)
- Is each UCA genuinely unsafe **in its context** (provided/not-provided/
  wrong-timing/wrong-duration)? Context is where bogus UCAs hide.
- Do loss scenarios give a *plausible causal chain*, or just restate the UCA?
- **STPA-Sec:** is the attacker model explicit and adequate (capability,
  position, goal)? Does `adversarial-causation` answer *how* (inject/spoof/
  tamper/intercept), not just *that*? Is security co-developed with safety, or
  bolted on after (a smell — STPA and STPA-Sec share the control structure)?

## Conducting it (when there's no analysis yet)
Work the four STPA steps top-down, writing rivet artifacts at each:
1. **Losses & hazards** — stakeholder losses; system-level hazards that lead
   to them (+ `cia-impact` for the STPA-Sec pass).
2. **Control structure** — controllers, controlled processes, control +
   feedback actions.
3. **UCAs** — for each control action, the four ways it's unsafe in context.
4. **Loss scenarios** — causal chains that produce each UCA; for STPA-Sec, the
   adversarial scenarios (attack-vector, attacker-type).
Each artifact links via rivet's typed predicates so `rivet check` can later
audit closure. Then run the audit above on your own output.

## Where this composes
- [`pulseengine-feature-loop`] — STPA/STPA-Sec is the loop's true front-end:
  losses/hazards/constraints precede the AADL architecture in spar and the
  typed requirements in rivet. A feature that changes hazardous behavior
  re-opens the analysis.
- [`oracle-gate-a-change`] — `rivet check` over the STPA closure rules is the
  mechanical oracle; the diff that closes a gap is the one that counts.
- [`clean-room-verification`] — Half 2; audit the reasoning cold.
- [`release-execution`] — the STPA/STPA-Sec analysis being complete *and*
  sound is a precondition of the V-model traceability gate: every safety/
  security constraint must trace forward to a requirement, architecture,
  implementation, and verification evidence.

## Anti-patterns
- **Treating STPA as a document** instead of rivet's typed graph — you lose
  the mechanical completeness oracle and traceability into the V.
- **Auditing completeness without soundness** — `rivet check` green is
  necessary, not sufficient; a closed graph of wrong hazards still passes.
- **Security as an afterthought** — STPA-Sec shares the control structure with
  STPA; co-develop them. A sec-analysis with empty `adversarial-causation` or
  no explicit attacker model is theatre.
- **Hazards written as events or causes** rather than states; **UCAs without
  context**; **loss scenarios that restate the UCA** instead of explaining it.
- **Partial CIA coverage** in STPA-Sec passed off as complete.
