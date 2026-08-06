+++
title = "Oracle-Gated Agent Loops: Certifying-Algorithm Discipline for AI-Assisted Development of Safety-Critical Software"
description = "Treat the AI agent as an untrusted producer whose every output is admitted only by an independent, deterministic checker — so a change lands not when a model judges it 'looks done,' but when a mechanical oracle goes red→green. Where that sits in the literature (certifying algorithms, Certifiable ML, Forge), and the one thing that is genuinely ours: the combination."
date = 2026-07-16
draft = false
template = "paper.html"
aliases = ["/preprints/oracle-gated-agent-loops/"]
[taxonomies]
tags = ["verification", "ai-agents", "how-it-works"]
authors = ["Ralf Anton Beier"]
+++

*Preprint · open for review — a working draft published to invite review and correction,
not peer-reviewed and not final. Claims are scoped proven / tested-not-proven / planned
(§5) and were checked cold by decorrelated agents against the source; nothing here asserts
production readiness. Found an error or an overclaim? That is exactly the review we are
asking for — see the provenance note below.*

## Abstract

An AI coding agent should be gated like an untrusted producer behind a trusted checker: a
change lands, and an autonomous loop stops, only on a deterministic verdict — never on the
model's own sense of *done*. This is *certifying algorithms* applied to agentic development.
Our contribution is the *combination* — one WebAssembly component gated at build time by
four independent oracles (capability-typed composition, MC/DC coverage, a V-model
traceability gate, and attestation) — together with an honest account of where those gates
are still vacuous against the executing program.

**Keywords:** certifying algorithms; verifier-gated agent loops; WebAssembly Component
Model; MC/DC; DO-178C / DO-333; formal verification; LLM agents.

## 1. Introduction

Autonomous "agent loops" have become a common way to drive AI coding tools: a loop restarts
the agent until a goal is met. The load-bearing question is *how the loop decides the goal
is met.* In much current practice the decision is delegated to a model — the agent's own
self-assessment, or a small auxiliary model reading the transcript [<a href="#ref-10">10</a>, <a href="#ref-11">11</a>]. For
safety-critical software this termination criterion is the wrong one: a plausible-looking
result is not a correct one.

We adopt the opposite rule. The agent is an untrusted producer; a change is admitted only
when an independent, deterministic checker accepts it; the loop is merely the search that
feeds that checker. We call the per-change instance *oracle-gating*. This paper makes three
claims:

1. Oracle-gating is a grounded, named idea — the agentic instance of certifying algorithms
   [<a href="#ref-1">1</a>] and Certifiable ML [<a href="#ref-2">2</a>] — not an ad-hoc practice (§2, §3).
2. Its distinctive value in our setting is a *combination* not, to our knowledge, assembled
   elsewhere: Wasm Component Model + MC/DC + a traceability release gate + attestation (§4).
3. Honesty about the gate's *coverage of execution semantics* is itself part of the method;
   we report where our own gates fall short (§5).

## 2. Background: certifying algorithms and Certifiable ML

A certifying algorithm [<a href="#ref-1">1</a>] returns, with each output, a witness that an independent checker
verifies, so that one "can be sure of the correctness of the output without having to trust
the algorithm." The recent articulation for AI, Certifiable Machine Learning [<a href="#ref-2">2</a>], makes the
asymmetry explicit: an untrusted *learner* does as much work as possible and a trusted
*verifier* only as much as necessary; "as long as the verifier is sound … the generated
result is guaranteed to satisfy its specification." Oracle-gating instantiates this pattern
with an LLM agent as the learner and formal or otherwise mechanical checkers as the
verifier. The lineage also includes proof-carrying code [<a href="#ref-12">12</a>] and translation validation
[<a href="#ref-13">13</a>], both of which pair an untrusted producer with an independent check.

## 3. Related work

**Formal-verifier-gated proof loops.** Baldur [<a href="#ref-4">4</a>], AlphaProof [<a href="#ref-5">5</a>], Aristotle [<a href="#ref-6">6</a>],
APOLLO [<a href="#ref-7">7</a>], and AutoRocq [<a href="#ref-8">8</a>] generate candidate proofs and accept only on a proof kernel's
verdict (Isabelle, Lean, or Rocq). We share their termination criterion; our domain is
systems code and its certification evidence rather than mathematics.

**Sound checkers over LLM output.** Amazon's Automated Reasoning checks [<a href="#ref-9">9</a>] return a
deterministic Valid/Invalid over LLM output via a symbolic engine — the closest commercial
analog to a certificate-checked decision procedure.

**Formal-method-guided code generation.** Nearest to our setting, *Forge* [<a href="#ref-3">3</a>] generates
safety-critical code targeting DO-178C, IEC 61508, and ISO 26262 and terminates its LLM
loop on three verifiers (Dafny, FDR4, Isabelle); its ablation reports that convergence
collapses when verifier feedback is removed.

**The contrast class.** Reflexion [<a href="#ref-10">10</a>] makes the deterministic oracle *optional*, allowing
termination on verbal self-reflection; some deployed loop mechanisms decide completion with
a model judge [<a href="#ref-11">11</a>]. These are precisely the termination criteria oracle-gating rejects.
Notably the discourse is split even among practitioners: OpenAI's Codex `/goal`
documentation argues the evidence-based side ("a Goal should not be marked complete because
the model believes it is probably done") [<a href="#ref-11">11</a>].

## 4. Approach: oracle-gating over a WebAssembly verification toolchain

We do not claim novelty on the gate itself; we claim it on the *combination*. To our
knowledge no other effort applies a certifying-checker-gated agent loop across all four of a
capability-typed substrate, structural-coverage evidence, a traceability gate, and
attestation together.

### 4.1 One iteration

A single oracle-gated step has the shape *produce → check → decide*. The agent — the
untrusted producer — proposes a change: a component, a lowering, an optimization, a proof
obligation. A checker specific to that change then runs and returns a deterministic verdict:
a proof kernel accepts or rejects, a coverage checker names the uncovered condition, a
differential run reports the diverging output, a signature verifies or does not. If the
verdict is red the change is not admitted, and the checker's own output — the failing goal,
the missed trap, the uncovered branch — becomes the next prompt. The loop terminates only
when the relevant oracle is green. Nothing about *the agent believing it is done* enters the
decision: the agent is the search that drives the oracle from failing to passing, and the
certificate the checker consumes (a proof, an LRAT derivation, a coverage report, a
differential trace) is what an outside party can re-check without trusting the agent.

### 4.2 Four oracles, one artifact

The combination is that a single WebAssembly component clears, at build time, four
*independent* checks, each a distinct mechanical oracle:

1. **Substrate — the WebAssembly Component Model.** Components have typed interfaces and
   explicit capability boundaries and fuse to native code; the surface a component may touch
   is the one its interface names, which turns "what could this reach" into a checkable
   question rather than an assumption.
2. **Coverage — MC/DC on WebAssembly.** Structural-coverage evidence in the DO-178C / DO-333
   shape, measured on the *lowered* Wasm the runtime actually executes — so the coverage
   claim is about the shipped artifact, not the source it came from.
3. **Traceability — a V-model gate.** Every requirement, design, and verification artifact
   is a typed, linked object, and a mechanical check reports any requirement whose
   verification is not closed; readiness is a query over that graph rather than a date.
   (Making that check a uniformly merge-blocking gate across every repository is in progress.)
4. **Attestation — signing, and (planned) reject-at-load.** The artifact is signed; the
   intended end state is on-device verification that refuses to execute an image whose
   signature or resource bounds do not match, with the bounds computed off-target by a sound
   analysis.

Beneath these, the concrete oracles are a traceability validator, an MC/DC coverage checker,
a sound abstract interpreter, a certificate-checked SMT decision procedure (QF_BV → LRAT → an
independently checked certificate), a signature verifier, and Verus / Rocq / Lean proofs of
specific properties. None of them consults the producer's opinion.

### 4.3 A worked instance: the gate refuses a plausible rewrite

The discipline earns its keep when a change *looks* correct and is not. Our optimizer
rewrites WebAssembly and validates each rewrite by translation validation — an SMT check
that the rewritten code computes the same *values* as the original. Consider folding a
multiplication by constant zero, `x * 0 → 0`, or dropping the dead result of a division:
both are value-equivalent, and the SMT check accepts them. But if `x` was an expression that
*traps* — an out-of-bounds load, or `INT_MIN / -1` — the original program would have trapped
and the rewrite does not. The value-only oracle is *vacuous* on exactly the behaviour that
matters: it does not model traps, so it certifies a rewrite that silently deletes a mandatory
one. (This is not hypothetical; it was a class of shipped miscompiles.)

Under oracle-gating this is a red gate, not a bug that ships. A trap-freedom check refuses to
fold across a possibly-trapping operand, names the discarded trap, and the rewrite is not
admitted — the loop does not terminate on that step until a trap-preserving version passes.
(Making this one certificate-checked trap-equivalence oracle, proven once rather than
enforced rule-by-rule, is the systemic backing §5 describes; it is built but not yet wired
into the live passes.) The general lesson, developed in §5, is that a gate is worth only what
its checker covers of the executing semantics — and that four independent oracles are harder
to render simultaneously vacuous than one.

## 5. Limitations and honest scoping

We name techniques precisely rather than flattening them to "formally verified," and — less
usually — we name where our *own* verification does not yet cover what it claims. We run
adversarial "challenger" agents against the toolchain using native execution and
computed-operand probing; they consistently out-find the tools' own test suites, for a
single recurring reason:

**Defects cluster where a stated guarantee is not enforced on the path that executes** — a
proof that models an operation abstractly but is vacuous against silicon; a
translation-validation encoding that does not model traps, so an identity rewrite may delete
a mandatory one; a fusion handler that recognizes a relocation type it does not rewrite; a
sandbox check absent from the live dispatch path. This is one class of fault —
*verification that does not cover the execution semantics it asserts* — and recognizing it
is why native differential execution, not the unit suite, is our real gate.

The toolchain is therefore maturing unevenly, predictably by problem shape. Ordered by
maturity of the *soundness* story rather than feature completeness:

- **Proof layer (Verus / Rocq / Lean).** The strongest, scoped claims — e.g. an ARMv7-M
  memory-protection region *validation model* whose arithmetic (power-of-two size,
  alignment, single-pair non-overlap, and base+size overflow-safety) is machine-checked in
  Verus under CI, with an independent Lean model maintained by hand (not yet CI-gated);
  set-level non-overlap is presently a trusted obligation, not machine-checked. The region
  *arithmetic* is proven; programming the MPU on silicon and trapping a faulting tenant is
  *planned*, not built.
- **Optimizer.** Furthest along on soundness-as-a-property: a whole class of
  trap-preservation defects (the translation-validation encoding did not model traps) was
  fixed at the root with a recursive trap-freedom guard. A *systemic* trap-gate — an
  independent, certificate-checked trap-equivalence check so the property holds once rather
  than rule-by-rule — has since been built and merged, but is not yet wired into the live
  optimization passes (the per-pass guard still enforces the property meanwhile); it is the
  template we intend the other tools to follow.
- **Transcoder.** Fast, with a valuable discipline of loudly *declining* an unsupported
  operation rather than emitting silently-wrong code; correctness nonetheless trails feature
  velocity by up to a release — and occasionally a defect is still open at the current tip —
  because new-backend operations can cross from *declined* to *implemented* without a
  native-execution test. New-backend codegen is thus
  *tested-where-executed*, not yet gated by a pre-release differential-execution check. The
  whole-program differential check — identical observable results across interpreter,
  emulator, and real silicon — is a strong equivalence *test*, not a proof of translation.
- **Fusion.** Whole-module invariants (memory isolation under shared-memory fusion;
  relocation and debug-info fidelity) are harder than single-operation lowering. The known
  fault classes here have been closed case by case, each with a regression oracle, but a
  *general* whole-module equivalence invariant is not yet established, and shared-memory
  soundness currently holds under the relocatable-output contract rather than universally.
  We do not claim sound fusion as settled.
- **Runtime.** Sandboxing and filesystem containment are the least-mature surface and an
  area of active hardening; we would not want them relied upon yet.

The methodology itself is enforced, not aspirational: every change is oracle-gated,
load-bearing claims are re-verified cold by a decorrelated reviewer, challenger agents probe
execution semantics adversarially, and public claims are bound to re-derivable evidence —
the discipline used to produce this document.

## 6. Discussion and open questions

We would welcome discussion with three communities. With verifier-gated code-generation
teams [<a href="#ref-3">3</a>]: whether the four-way combination of §4 occupies genuinely unoccupied space, and
where the approaches compose. With the Certifiable ML authors [<a href="#ref-2">2</a>]: whether oracle-gating
over agentic development, with a certification release gate, is a faithful instance of the
learner–verifier paradigm, and whether the vocabulary bridge is worth making explicit. With
the aviation and automotive formal-methods community: how a certifying-checker-gated
*authoring* loop relates to existing learning-assurance processes, which today target
trained models rather than agent-authored code.

## 7. Conclusion

The principle is not ours: correctness conferred by an independent checker rather than by
trust in the producer is the certifying-algorithm idea [<a href="#ref-1">1</a>], restated for AI as the
learner–verifier split [<a href="#ref-2">2</a>]. What we contribute is one specific assembly of it — a
certifying-checker-gated agent loop applied, on a single WebAssembly component and at build
time, across a capability-typed substrate, MC/DC coverage evidence, a V-model traceability
gate, and attestation. We have not found that four-oracle combination elsewhere; the nearest
published system [<a href="#ref-3">3</a>] gates code generation on formal verifiers, but for one language and
without the coverage or traceability legs.

The honest position matters as much as the claim. Our own gates are, in places, vacuous
against the semantics they assert (§5) — a value-only equivalence check that does not model
traps is the clearest case — and we report it because a gate is worth exactly what its
checker covers of the executing program. The same discipline that gates the code was turned
on this note: its claims were checked by independent agents against the sources, and the
corrections applied. We would rather ship a scoped, checkable claim than a flat one, and we
would welcome the verifier-gated and certifiable-ML communities [<a href="#ref-2">2</a>, <a href="#ref-3">3</a>] testing whether the
combination is as unoccupied as it appears.

## Provenance and AI-use disclosure

In keeping with the subject of this note, we disclose its own construction. The text was
drafted by an AI coding agent (Anthropic's Claude, via the Claude Code harness) and then
revised through the discipline the note describes. Concretely: the load-bearing per-tool
claims of §5 were checked by independent, cold-context verification agents against the
current source and issue trackers of each repository; the external works cited in §2–§3
were each checked against the cited source; and corrections from those passes were applied
to this draft — for example, tightening the proof-layer scope, and correcting a claim that
had *understated* the optimizer's progress. The literature positioning and the claim
taxonomy were produced with AI assistance and human-reviewed.

No AI system is an author: an author must be able to take responsibility for the content,
which a program cannot ([arXiv's generative-AI policy](https://blog.arxiv.org/2023/01/31/arxiv-announces-new-policy-on-chatgpt-and-similar-tools/)). The named author is responsible
for everything here, including any error, misattribution, or overclaim the verification
passes did not catch. Two caveats a reader should weigh: the verification above was
performed by *our own* decorrelated agents, not reproduced by an independent third party;
and AI-assisted references may still contain a mistake the checks missed — the citations
should be read at their sources, not taken on this note's authority.

## References

1. <a id="ref-1"></a>R. M. McConnell, K. Mehlhorn, S. Näher, P. Schweitzer. "Certifying algorithms."
   *Computer Science Review* 5(2):119–161, 2011.
   [doi:10.1016/j.cosrev.2010.09.009](https://doi.org/10.1016/j.cosrev.2010.09.009)
2. <a id="ref-2"></a>C. Barrett, T. A. Henzinger, S. A. Seshia. "Certificates in AI: Learn but Verify."
   *Communications of the ACM* 69(1), 2026.
   [cacm.acm.org](https://cacm.acm.org/research/certificates-in-ai-learn-but-verify/)
3. <a id="ref-3"></a>R. Wei, J. Woodcock, S. Foster, et al. "Formal-Method-Guided Vibe Coding: Closing the
   Verification Loop on AI-Generated Safety-Critical Software."
   [arXiv:2606.22413](https://arxiv.org/abs/2606.22413), 2026.
4. <a id="ref-4"></a>E. First, M. N. Rabe, T. Ringer, Y. Brun. "Baldur: Whole-Proof Generation and Repair
   with Large Language Models." *ESEC/FSE*, 2023.
   [PDF](https://people.cs.umass.edu/~brun/pubs/pubs/First23fse.pdf)
5. <a id="ref-5"></a>Google DeepMind. "AI solves International Mathematical Olympiad problems at silver-medal
   level" (AlphaProof), 2024
   ([blog](https://deepmind.google/blog/ai-solves-imo-problems-at-silver-medal-level/));
   see also *Nature*, 2025
   ([s41586-025-09833-y](https://www.nature.com/articles/s41586-025-09833-y)).
6. <a id="ref-6"></a>Harmonic. "Aristotle." [arXiv:2510.01346](https://arxiv.org/abs/2510.01346), 2025.
7. <a id="ref-7"></a>A. Ospanov, F. Farnia, et al. "APOLLO."
   [arXiv:2505.05758](https://arxiv.org/abs/2505.05758), *NeurIPS*, 2025.
8. <a id="ref-8"></a>H. Tu, et al. (incl. A. Roychoudhury). "Agentic Verification of Software Systems"
   (AutoRocq). [arXiv:2511.17330](https://arxiv.org/abs/2511.17330), 2026.
9. <a id="ref-9"></a>Amazon Web Services. "Automated Reasoning checks (Amazon Bedrock Guardrails)."
   [Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-automated-reasoning-checks.html), 2025.
10. <a id="ref-10"></a>N. Shinn, et al. "Reflexion: Language Agents with Verbal Reinforcement Learning."
    *NeurIPS*, 2023. [arXiv:2303.11366](https://arxiv.org/abs/2303.11366)
11. <a id="ref-11"></a>OpenAI. "Using Goals in Codex."
    [Developer documentation](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex), 2026.
12. <a id="ref-12"></a>G. C. Necula. "Proof-Carrying Code." *POPL*, 1997.
    [doi:10.1145/263699.263712](https://doi.org/10.1145/263699.263712)
13. <a id="ref-13"></a>A. Pnueli, M. Siegel, E. Singerman. "Translation Validation." *TACAS*, 1998.
    [doi:10.1007/BFb0054170](https://doi.org/10.1007/BFb0054170)
