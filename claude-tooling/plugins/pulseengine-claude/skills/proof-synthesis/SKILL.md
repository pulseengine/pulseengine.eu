---
name: proof-synthesis
description: This skill should be used when writing, repairing, or strengthening a machine-checked proof, spec, contract, or invariant in ANY PulseEngine verification backend — Verus (SMT/Z3), Rocq/Coq, Lean 4, Dafny, Kani (bounded model checking), or scry (sound abstract interpretation) — and whenever a proof obligation, assertion, or verification job is failing and needs an iterative generate→verify→refine loop. Backend-agnostic by design: the verifier's own output is the oracle, never an LLM's opinion. Fires across gale, scry, the rules_* proof toolchains, and any repo that carries proofs. Use it for the production of proofs; pair it with oracle-gate-a-change (the verifier is the gate) and stpa-audit/feature-loop (which say *what* must be proven).
metadata:
  author: pulseengine.eu
  version: "0.4.0"
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

## Driving the loop with an AI prover — the acceptance gate

When the *generator* in step 2 is a capable theorem-proving model (a
Leanstral-class Lean agent, or the Verus/Rocq equivalents), the loop is
unchanged — the verifier is still the oracle — but four disciplines are
load-bearing, and each is **checkable**. Grounded in PulseEngine's own graded
trials of a benchmark-topping Lean model against real ordeal and gale
obligations:

- **Clean-room the model, not just the review.** A proving agent with filesystem
  access will `grep` the real proof (or its compiled `.olean`) and copy it — *a
  proof it copies is not a proof it found.* Run every attempt in a sandbox
  containing only the target statement (its proof replaced by `sorry`) and its
  dependencies. **Check:** scan the agent transcript for reads of the
  source/`.olean`, and **diff the produced statement byte-for-byte** against the
  real one to confirm it proved *your* theorem, not a lookalike — spec-equivalence
  (step 1) is still the wall even when the proof passes.
- **Accept on `#print axioms` + a leak scan, never on "it passed."** A green build
  is necessary, not sufficient. Gate every AI-authored proof on: exit 0, no
  `sorry`, `#print axioms` reporting only the expected core
  (`propext`/`Classical.choice`/`Quot.sound` — **no `sorryAx`/`native_decide`**),
  and a clean transcript leak scan. Then **re-verify under the project's pinned
  toolchain** — an AI run on a newer Lean/Mathlib (or unpinned Verus/Z3) that
  passes is a *candidate*, not evidence, until the pinned build re-checks it. The
  generator is never the oracle, even when it succeeds.
- **Measure on your surface, not the benchmark.** Capability is jagged and
  domain-specific: the same model that saturates miniF2F (100%) converged cleanly
  on Mathlib-flavoured scheduling lemmas here yet could **not** close the
  Aeneas-simulation idiom that dominates a systems proof — same model, same week,
  same harness. Don't read a benchmark score as reliability on your workload; run a
  few graded trials on *your* obligations and record where it converges and where
  it doesn't, so adoption is domain-scoped.
- **Wire the language-server MCP.** Live goal state (`lean-lsp-mcp` for Lean; the
  equivalent for other backends) was the difference between *zero* proof attempts
  and genuine engagement — without it the agent can't see what it's proving.

Why this is safe: across every trial the model never produced a wrong proof the
kernel accepted — failures were honest `sorry`/errors only. That is the
certifying-algorithm / untrusted-producer property (see Independence) applied to
the *prover itself*: a jagged generator cannot corrupt the record when a trusted,
separately-checked oracle has the final say — whether it fails *or* succeeds.

## Independence — and the new AI common mode

Producing one proof correctly (the loop above) is necessary but not sufficient.
Multiple verification legs only shrink the trusted base if their **trusted bases
differ and no single author sits on both sides.** One agent (or one context)
authoring the spec, the proof, the model, *and* the test silently re-correlates
legs that look independent — the diversity becomes theatre. Humans decorrelate by
default; one AI *re-correlates* by default. Grounded in what the PulseEngine repos
actually do — and where they have already been bitten:

- **Prove against the code, or an *external* model — not a hand-mirror you also
  wrote.** Most proofs here verify a hand-transcribed model, not the shipped code:
  `coq_of_rust` of the *same* Verus source (gale), γ-mirrors of the Rust crate
  (scry), a Rocq model "not yet refined to the Rust" (relay), a selector model that
  "diverges from the shipped selector in 5 ways" (synth). A model that drifts from
  the code fools *every* backend identically. The one leg that catches this is a
  **differential against an external artifact the author didn't write** — wasmtime
  execution, an independent optimizer (`wasm-opt`), a POSIX/FreeRTOS reference,
  WasmCert-Coq — or a structural-coverage measurement of the *compiled* artifact
  (witness MC/DC on the shipped wasm, which honestly measures rather than claims to
  prove). Weight those; they attack model-vs-reality, which no same-authored proof
  can. The *strongest* form of "external model" is proving **published theory you
  didn't invent**: spar proves Liu & Layland / Joseph & Pandya / Dertouzos scheduling
  bounds in Lean, so the spec has peer-reviewed ground truth, not a self-authored
  mirror. But then the **theory↔code link becomes the trusted-base item** — spar
  labels its Lean→Rust step a "manual extraction, checked via property tests"; name
  that link and back it (property tests, or a refinement proof), or the honest
  external theory silently reconnects to unverified code.
- **Keep the same agent/context off both sides of a check.** Spec vs its proof,
  artifact vs its oracle, model vs its implementation — different lineage. Route the
  *spec* review through a cold [`clean-room-verification`] subagent (relay's 11/0
  then 10/1 confirm/refute is the model). This is the direct antidote to the AI
  common mode — load-bearing now, not nice-to-have.
- **Prefer the certifying-algorithm pattern — it defeats the common mode by
  construction.** An untrusted producer emits a *checkable certificate*; a small,
  separately-authored, verified checker validates it (ordeal: LRAT certificate +
  independent `ordeal-lrat` checker; synth: untrusted selector + trusted per-op
  validator; ordeal-vs-Z3 where a verdict disagreement is a hard error). The checker
  provably is *not* the checked thing, so a producer's blind spots — including an
  AI's — can never make a wrong answer accepted. Reach for this over "trust the
  prover" whenever the property admits a certificate.
- **Mutation / vacuity is a *required* meta-oracle, not nightly.** It is the one
  check that catches a proof that passes because the spec is *vacuous* — exactly the
  AI-authored failure. In this org it is nightly-only (gale) or absent (scry)
  precisely where it's needed most. Gate it per-change on any AI-authored proof.
- **Don't let two "independent" legs share a backend.** Verus + Kani over the same
  Verus-stripped *mirror* (relay), two provers both bottoming in Z3, one γ-style
  across backends (scry). If they share a solver or a model, name it as trusted base
  — the redundancy is only real *above* the shared layer.

**Vacuity has already shipped green here — learn the smells.** A match catch-all
`| _ => Some s` made *all* i64 proofs vacuously true (synth `WasmSemantics.v`, since
fixed). An `Axiom foo := True` stood in for a master lemma (loom `Correctness.v`). A
"proof" was a false structural-equality masked by a broken toolchain (scry join).
**When a hard obligation goes green fast, suspect vacuity:** confirm the spec isn't
trivially satisfiable, the model isn't a no-op fall-through, and no `Axiom`/`admit`
is quietly doing the work. This is the spec-side twin of "the verifier is the oracle."

### Make the common mode structurally unlikely (the approach)

The rules above are *defensive* — they catch re-correlation. Three moves make it
structurally unlikely, and they are where the strongest verification work heads:

- **Generation over checking.** A drift gate — a freshness check, `claim-check`, a
  sorry-budget — *catches* divergence; **generation** makes it unrepresentable by
  emitting the dependent artifacts from one source, so there is nothing to diverge.
  ordeal's `regen.sh` regenerates the Lean model from the Rust; the limit is a single
  definition that *emits* the spec, the code, the proof-model, the prose, and the
  tests together (how a formal language standard is generated from one source rather
  than kept in sync). Generation is checking taken to its limit. **When you find
  yourself writing a gate to keep two artifacts in sync, ask whether one can be
  generated from the other instead** — a hand-mirror that could drift is a generation
  opportunity, not a thing to police.
- **Independence as a bug-finder, not just a comfort.** Two independent mechanisations
  of the *same* obligation are a tool: **run both and mine the disagreements** — a
  divergence localizes a spec ambiguity or a translation gap exactly where the trusted
  base bites. Don't shelve the second checker as a "fallback" (a `bv_decide`-style
  Lean checker beside an Aeneas-translated one; hand-written abstract proofs beside
  `coq_of_rust`-translated ones) — a benched second mechanisation is a bug-finder
  you're not running.
- **Invest a reference oracle.** The highest-value use of a verified/executable
  artifact is often not "it's proven" but "it's the thing everything else is
  *differential-tested against*" — an interpreter you didn't write (an external
  verified reference), an independent optimizer, a coverage oracle on the shipped
  artifact. Pick one artifact per layer, make it the oracle, and differential the rest
  against it — the value is the independent witness, not the proof badge.

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
- **One agent on both sides of the check.** The spec and its proof, or the model
  and the code, authored by the same context — the AI becomes the shared blind spot
  and your "independent" legs re-correlate. Split the authorship; review the spec
  cold (see Independence, above).
- **Proving a hand-mirror model that can silently drift from the shipped code.** A
  green prover on a model you also wrote is not a correct binary. Pair it with a
  differential against an external artifact, or refine the proof to the actual code.

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
