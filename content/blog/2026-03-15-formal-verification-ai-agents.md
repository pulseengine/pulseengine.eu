+++
title = "Formal verification just became practical — AI agents changed the economics"
description = "Formal verification was too expensive for most teams. AI agents collapse the effort. Here is what works, what is still open, and how we verify kernel code with Verus, Rocq, and Lean in CI."
date = 2026-03-15T20:00:00+00:00

[taxonomies]
tags = ["verification", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
Formal verification was a craft practiced at a handful of universities and research labs. The barrier was never the math — it was the effort. AI agents collapse that effort. The same agents that write code can write proof annotations, and the solver checks them in seconds. The question shifts from "can we afford to prove this" to "what remains to be solved."
{% end %}

## The shift

For decades, formal verification was reserved for projects with extraordinary budgets and timelines. [seL4](https://dl.acm.org/doi/10.1145/1629575.1629596) took a decade of PhD students writing ~200,000 lines of Isabelle/HOL proofs for ~10,000 lines of C kernel code (SOSP 2009). CompCert took years. The rest of us tested and hoped.

Two things changed in 2025:

First, [Verus](https://github.com/verus-lang/verus) matured into a practical verification tool for Rust — not a research prototype, a tool that two of three best papers at OSDI 2024 were built on. Microsoft and Amazon use it in production. You write specifications as Rust code (`requires`, `ensures`), and an SMT solver (Z3) checks them exhaustively.

Second, AI agents learned to write these specifications. [AutoVerus](https://github.com/microsoft/verus-proof-synthesis) (Microsoft, ICLR 2025) achieves 91.3% success rate generating Verus proofs automatically. [AlphaVerus](https://github.com/cmu-l3/alphaverus) (CMU, ICML 2025) bootstraps verified code by translating from Dafny to Verus with self-improvement. [Lean Copilot](https://github.com/lean-dojo/LeanCopilot) automates 74.2% of proof steps in Lean. [Strat2Rocq](https://arxiv.org/abs/2510.10131) extracts reusable proof lemmas from LLM reasoning, improving CoqHammer's success rate by 13.4%.

Martin Kleppmann [wrote in December 2025](https://martin.kleppmann.com/2025/12/08/ai-formal-verification.html): "AI will make formal verification go mainstream." The POPL 2026 conference in Rennes dedicated an [entire workshop](https://popl26.sigplan.org/home/dafny-2026) to AI-assisted verification. The academic consensus is forming.

I wanted to see if this holds in practice.

## What I actually do

I use formal verification on [gale](https://github.com/pulseengine/gale), a Rust port of Zephyr RTOS kernel primitives targeting ASIL-D automotive safety. AI agents write the code and the proofs. Multiple verification tools check the results. CI validates everything on every commit.

The verification stack, honestly:

**Three independent proof systems:**
- **Verus** (SMT/Z3) — functional correctness. Every public function has `requires`/`ensures` contracts. The solver checks all inputs exhaustively.
- **Rocq** (theorem prover, formerly Coq) — independent proof of the same properties using a fundamentally different technique. Zero admitted lemmas.
- **Lean** — third proof track. Three proof systems means no single tool's soundness bug can propagate undetected.

**Bounded and runtime checking:**
- **Kani** — bounded model checking. Exhaustive state space exploration within finite bounds.
- **Miri** — undefined behavior detection.
- **Proptest** — property-based testing with random operation sequences.
- **Fuzz testing** — coverage-guided mutation.
- **Mutation testing** — verifies that tests actually catch bugs.
- **Differential specs** — POSIX and FreeRTOS reference models validate specification independence.
- **Sanitizers** — address, thread, and leak sanitizers.

**Integration testing:**
- 36 Zephyr test suites on multiple emulated boards (Cortex-M3, M4F, M33, Cortex-R5).

All of this runs in CI. All of it traces through [rivet](https://github.com/pulseengine/rivet) from requirement to proof to test to evidence.

This is comprehensive. It is also not complete — there are open questions I have not solved yet.

## The Rust subset problem

The hardest part is not writing proofs. It is writing Rust code that all verification tools accept simultaneously.

Verus accepts a subset of Rust — no trait objects, no closures in proof context, overflow checked by default. The `coq_of_rust` translator for Rocq accepts a different subset — no async, simpler pattern matching, explicit types preferred. Kani accepts most Rust but has its own limitations.

The solution: write the source once with Verus annotations, then use `verus-strip` (a tool in gale) to produce plain Rust without verification syntax. The stripped version feeds into cargo test, Kani, Miri, coq_of_rust, and everything else.

```
src/sem.rs            ← Verus-annotated source (single source of truth)
  ├── verus! { }      ← Verus verifies this
  └── verus-strip ──→ plain/src/sem.rs  ← plain Rust
                        ├── cargo test
                        ├── cargo kani
                        ├── cargo miri
                        └── coq_of_rust → proofs/*.v
```

The intersection of what all tools accept is narrower than any single tool, but it covers the patterns you actually need for kernel primitives: structs, enums, match, if/else, Result, Option, checked arithmetic, impl blocks. Getting agents to consistently write to this intersection is an ongoing challenge — they tend to reach for language features that one or another tool rejects.

## What works for proofs

From AutoVerus's research and my experience:

**Start with the invariant.** Every data structure needs an `inv()` spec function that captures what must always be true. Every operation proves it preserves the invariant.

```rust
pub open spec fn inv(&self) -> bool {
    self.limit > 0 && self.count <= self.limit
}
```

**Let Z3 try first.** Most proof obligations are simpler than they look. Write the spec, run Verus, see if it passes without manual proof steps.

**Add assert breadcrumbs when it does not.** Intermediate assertions guide the solver:

```rust
assert(self.count < self.limit);       // establish bound
assert(self.count + 1 <= self.limit);  // then increment is safe
```

**Classify the error, apply the matching fix.** Verus error types have known repair strategies — `PreCondFail` means the caller's context is insufficient, `InvFailEnd` means the loop body breaks the invariant, `ArithmeticFlow` means a bound is missing. Targeted fixes beat random attempts.

For Rocq: `lia` solves most integer goals. `unfold; auto` handles structural proofs. Strat2Rocq found that 42.5% of proof improvements come from lemmas that let CoqHammer skip induction — if you can state a closed-form intermediate lemma, do it.

## Bazel rules for reproducibility

I maintain Bazel rules for each verification tool so that proofs are hermetic and reproducible:

- [rules_verus](https://github.com/pulseengine/rules_verus) — `verus_test` rule, pre-built Verus binaries with SHA-256 verification
- [rules_rocq_rust](https://github.com/pulseengine/rules_rocq_rust) — `rocq_library` + `coq_of_rust` integration via hermetic Nix toolchains
- [rules_lean](https://github.com/pulseengine/rules_lean) — `lean_proof_test` with Mathlib and Aeneas support

A single `bazel test //...` runs all proof tracks. No local tool installation required.

## What is still open

I want to be honest about what this approach does not yet solve.

**MC/DC and structural coverage.** ISO 26262 recommends MC/DC for the highest ASIL levels. MC/DC was designed for C — measure which boolean conditions affect decision outcomes. A [joint paper by the German Aerospace Center and Ferrous Systems](https://arxiv.org/abs/2409.08708) investigated how MC/DC applies to Rust and found that it *is* applicable, but needs modification. Rust's pattern matching compiles to decisions that contain implicit conditions not visible in source code. The `?` operator desugars to hidden match expressions. Refutable patterns need to be treated as decisions with sub-conditions.

The [Safety-Critical Rust Consortium](https://rustfoundation.org/safety-critical-rust-consortium/) — which includes Ferrous Systems, Arm, AdaCore, Toyota, and others — is [working on MC/DC support as a 2026 Rust Project Goal](https://blog.rust-lang.org/2026/01/14/what-does-it-take-to-ship-rust-in-safety-critical/). An earlier compiler implementation was removed due to maintenance concerns. The consortium is approaching it again with shared ownership between industry and the Rust project. This is an active area of work, not a solved problem.

I believe mathematical proofs of functional correctness provide strictly stronger evidence than any coverage metric — a proof covers all inputs, MC/DC covers only tested inputs. But this is a direction I am working toward, not a claim I can make today. The standards community and certification bodies have not yet accepted formal proofs as a replacement for structural coverage. That conversation is starting.

**Tool qualification.** Three independent proof systems (Verus, Rocq, Lean) checking the same properties gives high confidence that no single tool's bug can cause a false positive. This supports a TCL1 (Tool Confidence Level 1) argument — but no assessor has evaluated this specific combination yet. The argument is sound in principle; it has not been tested in a certification audit.

**coq_of_rust maturity.** The Rust → Rocq translation is improving but not complete. Complex Rust patterns sometimes produce Rocq code that is difficult to reason about. The monadic DSL that `coq_of_rust` generates requires proof strategies that are specific to its output format.

**Specification completeness.** Formal proofs are only as good as their specifications. A correct proof of an incomplete spec gives false confidence. Writing complete specifications requires deep domain understanding — AI agents can write *syntactically valid* specs faster than humans, but *semantically complete* specs still need human review.

## The economics, honestly

The old economics: formal verification requires specialized researchers, costs $1M+, takes years. Practical only for projects where failure means loss of life.

The new economics: AI agents write proof annotations. Solvers check them in seconds. CI runs all verification tracks on every commit. The marginal cost of verifying a new function is minutes, not months.

This does not make verification free. Writing good specifications still requires understanding the domain. Getting code into the intersection of all verification tools still takes care. Debugging a failed proof still needs insight. The open questions above are real and require work to resolve.

But the effort dropped by orders of magnitude. The projects that could never afford formal verification — most automotive, most medical devices, most industrial control — now have a practical path. The tools exist. The agents can use them. The open questions are tractable.

The proof is not in a paper. It is in the CI log.

---

*A detailed reference for agents and developers working with these tools is available as the [Verification Guide](/guides/verification-guide/) ([download as Markdown](/guides/VERIFICATION-GUIDE.md)). It covers error tables, proof tactics, the Rust subset intersection, and Bazel rules. We update it as we learn what works — if something is wrong or missing, [open an issue](https://github.com/pulseengine/pulseengine.eu/issues).*

*This post is part of [PulseEngine](/) — a formally verified WebAssembly Component Model engine for safety-critical systems.*
