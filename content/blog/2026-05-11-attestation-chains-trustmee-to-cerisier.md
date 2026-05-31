+++
title = "Reasoning about attestation chains: from TrustMee to Cerisier"
description = "Two academic papers — TrustMee verifies single attestations in Wasm, Cerisier reasons about their composition in a capability machine — and what is still missing to close sigil's PQ-migration trust story. An internal milestone, not a finished result."
date = 2026-05-11
draft = true
[taxonomies]
tags = ["verification", "attestation", "sigil", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
Sigil's chain of build-time attestations — meld, loom, synth, kiln — verifies link-by-link today. Every consumer question reduces to "did each link verify, yes or no". That is fine until the chain spans a post-quantum signature migration, at which point a flat verifier has no vocabulary for "this link was Ed25519 before key rotation, the next is SLH-DSA after". Two recent papers stake out the two halves of the right answer. TrustMee (Aalto, Feb 2026) gives an engineering pattern for shipping the verifier itself as a signed Wasm component. Cerisier (Aarhus, April 2026) gives a program logic in Iris and Rocq for *reasoning* about chains of attestation — but only inside one capability machine. Neither alone closes sigil's problem. The mapping doc that identifies the gap is in draft. The sister logic that fills it is not.
{% end %}

## Why bother reasoning about chains

[What comes after test suites](/blog/what-comes-after-test-suites/) argued that the verification surface grows with AI-velocity code, not shrinks. The follow-up — [overdoing the verification chain](/blog/overdoing-the-verification-chain/) — laid out the ten-layer stack of proofs, tests, sanitizers, and traceability that closes the gap inside one repository. Both posts treated *signed attestation chains* the way most of the industry does today: as a transport problem. You sign each artefact, you walk the chain at verification time, you accept it if every link's signature is valid.

That works as long as nothing changes underneath the chain. The moment something does — a key rotates, a signature scheme migrates, an upstream stage's proof admits a lemma it did not last week — a flat link-by-link verifier has nothing to say about how trust evolved. It can tell you each link is valid. It cannot tell you the *composition* of the links still means anything.

Sigil emits these chains today. The [Sigstore-keyless + Fulcio + Rekor + SLSA L4](/blog/what-comes-after-test-suites/) pipeline is shipping. Post-quantum signature support (SLH-DSA / FIPS 205) is in progress. The interesting part of that PQ migration is not the cryptography. It is what the verifier should *say* about an artefact whose stages span both sides of the switch.

This post is the internal milestone on that question: two papers I have been reading, the gap between them, and the draft documents in sigil's repo that name the gap. Both paper reads are first-pass — search-only, not full PDF — and both notes files carry that caveat. The predoc in sigil's repo carries the same. I am preserving it here.

## Two papers, two halves of an answer

**TrustMee** ([arXiv 2602.13148](https://arxiv.org/abs/2602.13148), Aalto / Ericsson, Feb 2026) is a systems paper. The idea is engineering, not formal: each remote-attestation bundle ships its own *signed WebAssembly Component Model module* that implements the per-platform verification logic. A generic "Trustee" driver verifies that Wasm component's signature against a trusted PKI, runs it in Wasmtime with WASI-HTTP enabled (so the component can fetch CRLs and TCB collateral) and a scoped filesystem (for caching), and emits a signed EAT Attestation Result. Reported overhead is approximately 2.7% on SEV-SNP and 17.2% on TDX, with TDX dominated by collateral fetch rather than CPU. The trick is that the verifier-diversity problem — every TEE needs its own logic — collapses into a code-signing problem on a single PKI for Wasm verification components.

What TrustMee proves about the verifier is roughly nothing in the formal sense. There is no Coq, Iris, Rocq, Lean, or Verus artefact. The TCB is *enumerated* (Trustee core, Wasmtime, the platform-specific attestation infrastructure, the PKI) rather than *bounded by proof*. That is fine — TrustMee is solving the engineering problem of how to deliver a verifier, not the logical problem of what the verifier means.

**Cerisier** ([arXiv 2604.13638](https://arxiv.org/abs/2604.13638), Aarhus and Leuven, April 2026) is the formal-methods complement. It is the first program logic for *modular reasoning* about trusted, attested, and untrusted code running together on a CHERI-TrEE capability machine. Built in Iris on top of Rocq, fully mechanised. It extends Cerise — the existing program-logic base for capability machines — with the enclave primitives that CHERI-TrEE adds: register-enclave-code, init-enclave-data, deinit (backed by a memory-sweep revocation), and a hashed enclave-identity primitive.

The two papers do not cite each other; TrustMee predates Cerisier by about two months. They are complementary, not competing. TrustMee gives you the *per-link verified verifier* as an engineering artefact. Cerisier gives you the *logic of how attested values compose* — inside one capability machine.

## The vocabulary that Cerisier adds

Two terms do most of the work in Cerisier; both deserve a one-line English gloss before the symbol shows up.

A **sealing predicate** is the user's pre-commitment to what an enclave's identity *means*. Before any execution happens, the verifier registers, for each enclave identity `i` they intend to interact with, a logical predicate `P_i` that captures the semantic invariant that enclave preserves — for example, "any value this enclave seals is a positive integer less than 1000". The runtime later delivers a sealed value; the logic discharges the proof obligation that the underlying value satisfies `P_i`.

The **universal contract** — written `V(w)` in the paper — is the worst-case obligation the logic retains about any value `w` whose origin you cannot inspect. For values from open-world adversary code, `V(w)` is the weakest safe-to-share predicate. For values sealed under a registered identity `i`, the universal contract reduces to "the underlying value satisfies `P_i` instead". The universal contract is what lets you reason about code whose internals you do not have, without abandoning the proof structure.

Composition then follows the standard Iris pattern. Iris is a separation logic: its **frame rule** is the modular-composition primitive that lets a local proof about a region of state extend cleanly into a larger context, without having to re-prove anything about the parts of state the local proof did not touch. Sealed values are framable. Once you know `P_i` of a sealed value, you continue to know `P_i` until you explicitly forget it — which happens, in Cerisier, when the enclave terminates and the memory-sweep revocation invalidates prior capabilities. That is the *safe-to-deinit* discharge lemma: the runtime backs the logic.

In English: Cerisier lets you say *"the verifier pre-commits to what each enclave identity means; the runtime delivers seals; the logic composes the resulting trust claims modularly"*. The static-time-only, single-machine-only scope is not a bug. It is the explicit domain.

## What neither paper covers, and where sigil sits

Sigil's chain spans dimensions neither paper formalises:

- **Build stages**, not enclaves. `meld → loom → synth → kiln` is a producer pipeline; each stage emits an artefact and walks away. There is no shared runtime that mediates "the verifier sees the seal and the predicate in the same memory at the same time" — the Cerisier scenario.
- **Multiple signature schemes**. Ed25519 today, SLH-DSA / FIPS 205 tomorrow, both during a transition window. Cerisier's sealing relation is abstract; the underlying machine primitive is the capability plus a hashed identity, not a digital signature. There is no vocabulary for "this seal was produced under signature scheme A; that one under scheme B".
- **Key rotation and time**. Cerisier is static-in-time. There is no `▷` (later) modality wired into trust evolution, no "trust state at moment t1 differs from trust state at t2", no revocation list, no age-of-attestation predicate.
- **Content-addressed artefact store**. Sigil's "memory" is a SHA-256 content-addressed global store across time and machines. Cerisier's memory is mutable, hardware-checked, single-machine.
- **Detachment**. Cerisier's verifier reasons about seals in its own memory. Sigil's verifier reasons about DSSE envelopes that were produced months ago on another machine, possibly across an air gap.

The mapping doc in sigil's repo — [`docs/security/attestation-trust-formalization.md`](https://github.com/pulseengine/sigil/blob/main/docs/security/attestation-trust-formalization.md), tracked as CG-14 / CR-25 / CD-28 — walks each of these in order. The conclusion it lands on is not "we adopt Cerisier". It is:

> Cerisier is a strong **template** — its sealing-predicate-with-identity primitive, its universal-contract-for-untrusted-code pattern, its frame-rule-based modular reasoning — for what a sister logic over **content-addressed artefact stores with time-indexed trust predicates** would look like. That sister logic does not exist. Building it is a real research contribution, not an engineering port.

That is the news. The mapping is in draft. The trust-evolution-scenarios doc is also in draft. The sister logic, the one that would actually answer sigil's questions, is not.

## The PQ migration as the worked example

The cleanest forcing-function example is the post-quantum signature migration sigil is currently rolling out. NIST has finalised SLH-DSA (FIPS 205). Sigil's pipeline will, during a transition window, produce chains where stage `N` is signed under Ed25519 — produced before key rotation — and stage `N+1` is signed under SLH-DSA, produced after. Both stages reference the same upstream artefact. A flat verifier checks: stage `N` signature valid (yes), stage `N+1` signature valid (yes), accept.

What that flat answer hides:

- The Ed25519 key that signed stage `N` may have been rotated *between* stage `N` and stage `N+1`. The verifier has no way to express "this seal is from before the rotation, that one is from after".
- If a future cryptographically relevant quantum computer breaks Ed25519, every chain whose pre-rotation links are *only* Ed25519-attested becomes retroactively weaker. The verifier needs vocabulary for "the residual claim about stage `N` is now bounded by the strength of Ed25519, not the strength of the proof inside stage `N`".
- The trust state of the *composition* — what the artefact at the end of the chain still means — depends on which links were produced under which scheme at which time.

A Cerisier-style judgement, sketched against the sister logic the predoc proposes, makes the cross-scheme transition first-class. One pre-condition, one transition, one residual obligation. Roughly:

```text
{ Sealed_at(t₀, K_ed25519, P_N)(stage_N)
∗ KeyRotation(K_ed25519 ↦ K_slhdsa, at t₁, t₀ < t₁)
∗ Sealed_at(t₂, K_slhdsa, P_{N+1})(stage_{N+1}), t₁ < t₂ }
  verify_chain(stage_N, stage_{N+1})
{ ResidualTrust(P_N ⊓ Strength(K_ed25519, t_now))
∗ ResidualTrust(P_{N+1} ⊓ Strength(K_slhdsa, t_now)) }
```

Read in English: at verification time, *given* that stage `N` was sealed at time t₀ under an Ed25519 key with predicate `P_N`, *and* that key was rotated to an SLH-DSA key between t₀ and the production of stage `N+1` at time t₂, *and* stage `N+1` was sealed under the new key with predicate `P_{N+1}` — then the residual trust about stage `N` is the conjunction of its original predicate with the *current* strength of the Ed25519 key (a time-dependent quantity), and likewise for stage `N+1` under SLH-DSA. The judgement makes the cross-scheme transition observable rather than hiding it inside a yes/no chain walk.

This is one judgement, not a logic. The trust-evolution-scenarios doc in sigil's repo carries several more — Scenario 1 is the PQ case sketched above; subsequent scenarios cover Verus admits crossing stages, OIDC identity rotations, and Rekor-log freshness. None of them are mechanised. All of them are in draft. The point is to demonstrate that the questions are *expressible* in a sister-logic vocabulary, not that the logic exists yet.

## What the composition would look like

The honest division of labour, if both papers' patterns matured:

- **Per-link verifier — TrustMee shape.** Sigil could emit, alongside each signed artefact, a signed Wasm verification component that knows how to verify *that artefact's specific attestation envelope*. A generic driver verifies the component's signature against sigil's PKI, runs it in Wasmtime, and gets back a signed EAR (EAT Attestation Result) describing what the link established. TrustMee's pattern transfers directly; the schemas (DSSE envelopes, in-toto statements, SBOMs, module-signature sections) are different from TEE quotes, but the driver/PKI/Wasm-component shape is identical. Tracking issue [pulseengine/sigil#79](https://github.com/pulseengine/sigil/issues/79) already gestures at this for the cFS context.
- **Chain logic — extended Cerisier shape.** A sister logic — time-indexed, content-addressed, signature-scheme-aware — would compose the per-link EARs into a *chain-level* statement: "the residual trust about the final artefact, given the chain of EARs and the time-indexed key state, is `R`". That logic does not exist. It is the publication-target work the predoc points at.

Sigil sits at the intersection. It produces the chains today. It could consume verifier-pattern-shaped components tomorrow. The chain logic is the longer thread — research, not engineering.

## Honest framing

A few caveats I want to keep visible.

Both paper reads are first-pass and search-only. Neither was read end-to-end against the PDF — both notes files carry the same caveat, and so does the sigil predoc. Specific theorem statements, frame-rule notation, exact Rocq mechanisation breakdowns are all marked "needs PDF re-verification" in the source notes. The structural claims — Cerisier formalises local attestation in a capability machine, explicitly does not formalise remote attestation, has no time index or key rotation; TrustMee is engineering without formal soundness — are reliable. The literal-quote claims are not.

The sister logic is not a side project I can spin up next quarter. It is the kind of thing that lands at PLDI, OOPSLA, or CCS 2027 if it lands at all, and only after `scripts/mythos/` — the [oracle-gated bug-hunt pipeline](/blog/mythos-slop-hunt/) — has run against sigil's actual codebase and produced empirical material on the bugs the current flat-chain verifier would have missed. That empirical pairing is the realistic theoretical-meets-practical story. This post is the theory side; the Mythos run is the empirics side; the worked PQ example is the forcing function that connects them.

No assessor has evaluated any of this in a certification audit. The existing [credit matrix across six safety standards](/blog/overdoing-the-verification-chain/) covers proofs of *functional* correctness; trust-evolution logic over signed artefact chains is not yet in that table at all. Adding it is future work for the next mapping pass.

## The internal milestone

Concretely, what this post records:

- The mapping document — Cerisier primitives ↔ sigil primitives — is in draft in the sigil repo. It identifies a real gap, not a port opportunity.
- The trust-evolution-scenarios document — PQ migration as Scenario 1, plus several more — is in draft. It expresses the questions a sister logic would answer.
- The sister logic itself does not exist. Building it is a 2027-cycle publication target, gated on the `scripts/mythos/` empirical pass against sigil.
- TrustMee's Wasm-verifier-as-signed-component pattern is the design template for any per-link verifier sigil ships; sigil issue [#79](https://github.com/pulseengine/sigil/issues/79) is the engineering hook.

This is low-cost. Two papers read, two drafts written, one publishable note for context. The high-cost work — the sister logic, the mechanisation, the credit-template against safety standards — is deferred until the empirical material is there to argue from.

That is the discipline I keep trying to hold. Read the right papers early, write the gap down honestly, defer the expensive work until the cheap work has produced enough evidence to justify it. The point of a research thread is not to publish on the first pass. It is to know what you are publishing *about* by the time you commit to the writing.

---

## References

- arXiv [2602.13148](https://arxiv.org/abs/2602.13148) — *TrustMee: Self-Verifying Remote Attestation Evidence*. Sadri Sinaki, Ahmad, Xie, Sebrechts, Kjällman, Gunn (Aalto / Ericsson Research, Feb 2026).
- arXiv [2604.13638](https://arxiv.org/abs/2604.13638) — *Cerisier: A Program Logic for Attestation in a Capability Machine*. Rousseau, Carnier, Van Strydonck, Keuchel, Devriese, Birkedal (Aarhus / Leuven, April 2026).
- [Cerise (JACM 2023)](https://iris-project.org/pdfs/2023-jacm-cerise.pdf) — the program-logic base Cerisier extends.
- [CHERI-TrEE (EuroS&P 2023)](https://pure-oai.bham.ac.uk/ws/portalfiles/portal/192263870/eurosp2023_final72.pdf) — the capability-machine model Cerisier targets.
- Sigil predoc — *Attestation-Trust Formalisation* — at [`docs/security/attestation-trust-formalization.md`](https://github.com/pulseengine/sigil/blob/main/docs/security/attestation-trust-formalization.md). Tracked as CG-14 / CR-25 / CD-28.
- Prior PulseEngine posts: [*What comes after test suites*](/blog/what-comes-after-test-suites/) (Apr 7), [*Overdoing the verification chain*](/blog/overdoing-the-verification-chain/) (Apr 22), [*Mythos slop-hunt*](/blog/mythos-slop-hunt/) (Apr 25).

*[PulseEngine](/) is a formally verified WebAssembly Component Model engine for safety-critical systems. Code at [github.com/pulseengine](https://github.com/pulseengine). All tools are open source under Apache-2.0 or MIT.*
