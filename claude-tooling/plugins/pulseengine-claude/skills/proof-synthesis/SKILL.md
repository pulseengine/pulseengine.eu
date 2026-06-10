---
name: proof-synthesis
description: This skill should be used when writing, repairing, or strengthening a machine-checked proof, spec, contract, or invariant in ANY PulseEngine verification backend — Verus (SMT/Z3), Rocq/Coq, Lean 4, Dafny, Kani (bounded model checking), or scry (sound abstract interpretation) — and whenever a proof obligation, assertion, or verification job is failing and needs an iterative generate→verify→refine loop. Backend-agnostic by design: the verifier's own output is the oracle, never an LLM's opinion. Fires across gale, scry, the rules_* proof toolchains, and any repo that carries proofs. Use it for the production of proofs; pair it with oracle-gate-a-change (the verifier is the gate) and stpa-audit/feature-loop (which say *what* must be proven).
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# Proof synthesis

Writing a machine-checked proof is a search, and the verifier is the only
honest judge of progress. This skill is the **backend-agnostic loop** for that
search — generate a candidate, run the real verifier, read its actual error,
refine from that error, repeat — applied uniformly across every formal backend
PulseEngine uses. It is the proof-side analogue of `stpa-audit`: where that
audits the hazard graph, this *produces* the evidence that closes proof
obligations.

> **The one rule that makes this work:** the **verifier's output is the
> oracle**. Never accept "this looks proven" from a model. Published evidence:
> an LLM-as-judge misses **26%** of failures a deterministic/executable checker
> catches ([arXiv 2605.26457](https://arxiv.org/abs/2605.26457)). A proof that
> the prover hasn't accepted is not a proof.

This is a long-running explorer (see [`pulseengine-operating-contract`]): self-verify
at an interval as you build — re-check progress against the spec with fresh-context
subagents ([`clean-room-verification`]), rather than trusting your own running thread.

## The loop (identical across backends)

1. **Specify first.** Write the property/contract/invariant *before* the proof.
   This is the hard part and the usual failure point: on CLEVER (161 Lean
   problems) no SOTA agent end-to-end-verifies more than **1**, with
   *spec-equivalence* the dominant wall ([arXiv 2505.13938](https://arxiv.org/pdf/2505.13938)).
   A proof of the wrong spec is worse than no proof. Have the spec itself
   reviewed cold ([`clean-room-verification`]) — "is this the property we
   actually need?" — before sinking effort into proving it.
2. **Generate** a candidate proof / annotations / lemmas.
3. **Run the verifier** (the oracle — see the per-backend table). Capture the
   *exact* error, counterexample, or remaining goal — not a paraphrase.
4. **Critique from the verifier output.** Read the counterexample / failing
   goal / SMT timeout and localize the real gap. Don't guess; the prover told
   you where it broke.
5. **Refine** with the smallest targeted change (strengthen an invariant, add a
   lemma, supply a witness, split a case, add a `decreases`/termination
   measure). Re-run.
6. **Converge or escalate.** If stuck after a few rounds: decompose into
   lemmas, strengthen the inductive hypothesis, or — if the obligation is
   genuinely too hard — flag it rather than papering over (see anti-patterns).

This three-phase shape (generate → refine-with-tips → debug-from-verifier-errors)
is exactly what reaches **90%+** on a 150-task Verus benchmark in AutoVerus
([arXiv 2409.13082](https://arxiv.org/pdf/2409.13082),
[microsoft/verus-proof-synthesis](https://github.com/microsoft/verus-proof-synthesis)).
It is the concrete instantiation of [`oracle-gate-a-change`] for proofs.

## Per-backend adapter — same loop, different oracle

| Backend | Invoke (the oracle) | What "the error" is | Notes |
|---|---|---|---|
| **Verus** | `cargo verus verify` / `verus` | SMT failure, failing `ensures`/`requires`, timeout | watch quantifier triggers; split lemmas when Z3 times out |
| **Rocq / Coq** | `rocq`/`coqc`, `dune build` | remaining proof goal / tactic failure | decide *when to query the prover vs. predict a tactic*, keep a proof-tree (AutoRocq, [arXiv 2511.17330](https://arxiv.org/pdf/2511.17330)) |
| **Lean 4** | `lake build` / `lean` | unsolved goals, `sorry` left | autoformalize NL→spec as a *biconditional* and prove equivalence ([arXiv 2511.11829](https://arxiv.org/pdf/2511.11829)) |
| **Dafny** | `dafny verify` | failing assertion / postcondition | strong source for cross-language bootstrap (below) |
| **Kani** | `cargo kani` | counterexample trace | bounded — record the bound; absence of CEX ≠ unbounded proof |
| **scry** | the abstract-interpretation run | unproven invariant / lost precision | soundness is the property; widening/narrowing tuning is the "refine" step |

When the verifier can't be invoked or behaves wrongly, that's a tooling gap →
[`report-tool-friction`] against the backend, then continue by hand.

## Advanced patterns (from the research, use when they fit)

- **Cross-language bootstrap** — translate an already-verified artifact from a
  higher-resource language to a lower-resource one using verifier feedback, no
  human in the loop (AlphaVerus, Dafny→Verus,
  [alphaverus.github.io](https://alphaverus.github.io)). Useful for gale, but
  success rates are still modest (~33% HumanEval-Verified) — treat as an
  accelerator, not a guarantee.
- **Spec autoformalization environment** — drive the loop inside an
  agent↔verifier↔filesystem harness (Verus-SpecGym, [arXiv 2605.26457](https://arxiv.org/abs/2605.26457))
  so each refinement is checked, not assumed.
- **Lemma library reuse** — converged sub-proofs become reusable lemmas; the
  next obligation starts from a richer base.

## Anti-patterns

- **Trusting an LLM "looks proven" instead of running the verifier.** The whole
  point; the 26%-miss result is why.
- **Proving the wrong spec.** A green verifier on a spec that doesn't capture the
  requirement is a false sense of safety — spec-equivalence is the real wall.
- **Vacuous / unsound shortcuts** to make it pass: `admit`/`sorry`, `assume`,
  over-strong axioms, `#[verifier::external]` escape hatches, unbounded claims
  from a bounded Kani run, or widening scry to the point of uselessness. These
  flip the oracle green while removing its meaning — strictly worse than an
  honest red.
- **Refining without reading the counterexample.** The prover localized the gap;
  use it instead of guessing.
- **Grinding a genuinely-too-hard obligation forever** instead of decomposing,
  strengthening the invariant, or flagging it as an open lemma.

## Where this composes

- [`oracle-gate-a-change`] — this skill *is* the per-change loop when the
  mechanical oracle is a prover/checker; the diff that flips it green is the one
  that counts.
- [`pulseengine-feature-loop`] — the Verify step (Verus/Rocq/Lean/scry) is
  produced by this loop; the feature isn't done until the obligations are
  discharged by the verifier, not by assertion.
- [`stpa-audit`] / [`pulseengine-feature-loop`] say *what* must hold
  (constraints, requirements); proof-synthesis produces the machine-checked
  evidence that it does.
- [`clean-room-verification`] — review the *spec* cold (is it the right
  property?) before and after proving it.
- [`report-tool-friction`] — verifier/toolchain gaps hit during the loop become
  tracked issues against the backend.
