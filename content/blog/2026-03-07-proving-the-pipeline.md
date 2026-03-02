+++
title = "Proving the pipeline: verification from component to binary"
description = "Each transformation in the pipeline — fusion, optimization, transcoding — should be provably correct. This is what formal verification of a WebAssembly toolchain looks like, and what it takes to qualify for ISO 26262 and DO-178C."
date = 2026-03-15
draft = true
[taxonomies]
tags = ["deep-dive", "verification", "series"]
authors = ["Ralf Anton Beier"]
+++

*This is part 6 of a series on building a verified WebAssembly pipeline for safety-critical embedded systems. [Part 1](/blog/zero-cost-component-model/) introduces the approach. [Part 5](/blog/synth-kiln-wasm-to-firmware/) covers native transcoding and the runtime layer.*

## Why proof matters

For most software, testing is sufficient. You run your test suite, you fuzz, you deploy. If something breaks, you patch and redeploy.

Safety-critical systems do not work this way. In automotive (ISO 26262), aerospace (DO-178C), and medical devices (IEC 62304), you must demonstrate that your toolchain does not introduce errors — or that you have mitigated the risk of tool errors through additional verification. This is called tool qualification.

A compiler that has been formally verified to preserve semantics — like [CompCert](https://compcert.org/) for C — changes the qualification equation. Airbus uses CompCert precisely because its verified compilation eliminates a layer of object-code verification that would otherwise be required. The tool is qualified once; every project that uses it benefits.

The PulseEngine pipeline has the same aspiration: prove that each transformation preserves semantics, so the pipeline itself can be qualified as a tool, not re-verified per project.

## What needs to be proven

The pipeline has three transformations, each requiring its own correctness argument:

### meld: fusion preserves semantics

meld takes a Component Model component (a tree of core modules, canonical ABI operations, and instantiation chains) and produces a flat core module. The proof obligation: the fused module, when executed with the same host imports, produces the same observable behavior as the original component.

This is structurally similar to a linking correctness proof. The challenges are specific to the Component Model:

- **Index space merging** — functions, memories, tables, and globals from multiple modules are renumbered into a single space. Every reference must be correctly rewritten.
- **Canonical ABI resolution** — `canon lift` / `canon lower` pairs are replaced by direct calls with appropriate type conversions. The conversion must be semantically equivalent to what a compliant runtime would produce.
- **Import resolution** — internal imports (module A importing from module B) become direct references. Only host imports remain.

The formal framework: [Iris-Wasm](https://dl.acm.org/doi/abs/10.1145/3591265) provides mechanized separation logic for Wasm 1.0 in Rocq. A [mechanized formalization of the Wasm spec](https://www.semanticscholar.org/paper/A-Mechanized-Formalization-of-the-WebAssembly-in-Huang/2fde569f52c37fe8e45ebf05268e1b4341b58cbf) proves type safety and memory safety. These provide the foundation, but a fusion-specific proof is new work.

### loom: optimization preserves semantics

loom applies optimization passes to the fused module. Each pass must preserve semantics: the optimized function produces the same outputs for the same inputs.

loom takes two approaches:

**Translation validation via [Z3](https://github.com/Z3Prover/z3).** After optimizing a function, loom encodes both the original and optimized versions as SMT formulas and asks Z3 to prove equivalence. This is not a proof that the optimizer is correct in general — it is a per-function, per-optimization check that this specific transformation preserved semantics. If Z3 finds a counterexample, the optimization is rejected for that function.

**Declarative rules via ISLE.** Cranelift's [ISLE](https://github.com/bytecodealliance/wasmtime/tree/main/cranelift/isle) pattern-matching framework allows optimization rules to be expressed declaratively. [Crocus/VeriISLE](https://dl.acm.org/doi/10.1145/3617232.3624862) has demonstrated that ISLE instruction-lowering rules can be verified — they reproduced known bugs and found new ones in Cranelift. The same verification approach could apply to loom's optimization rules once they are expressed in ISLE.

### synth: transcoding preserves semantics

synth transcodes Wasm to native code. The proof obligation: the native output, when executed on the target architecture, produces the same behavior as the Wasm input when executed by a compliant interpreter.

This is the hardest proof in the pipeline. It spans two instruction set architectures (Wasm and the target ISA) and must account for the differences in memory models, calling conventions, and instruction semantics.

Precedent exists. [VeriWasm](https://github.com/PLSysSec/veriwasm) verifies that native x86-64 output from Wasm compilation preserves software fault isolation properties, with Rocq proofs for the verifier. CompCert proves that compilation from C to multiple target architectures preserves semantics. A synth-specific proof would draw on both approaches.

The wasm2c path offers an alternative verification strategy: transpile Wasm to C, then rely on a qualified C compiler ([IAR](https://www.iar.com/), [Green Hills](https://www.ghs.com/), [Wind River Diab](https://www.windriver.com/products/diab-compiler)) for the last step. The qualification burden shifts to the C compiler, which may already be qualified for the target domain.

## The verification tools

- **[Verus](https://github.com/verus-lang/verus)** — SMT-based formal verification for Rust. Proofs are expressed in Rust syntax, alongside the implementation code. For verifying kiln's interpreter, meld's fusion logic, and loom's optimization passes.
- **[Rocq](https://rocq-prover.org/)** (formerly Coq) — the proof assistant for the mathematical foundations. The semantic model of Wasm, the correctness theorems for each transformation, the proofs that tie everything together. Iris-Wasm and the mechanized Wasm spec are both built in Rocq.
- **[Z3](https://github.com/Z3Prover/z3)** — the SMT solver behind loom's translation validation and Verus's proof obligations. Z3 checks satisfiability of logical formulas — when loom asks "are these two functions equivalent?", Z3 provides the answer.

## What this means for qualification

In ISO 26262, a software tool used in the development of safety-related systems must be qualified according to its Tool Confidence Level (TCL). A tool that could introduce errors without detection requires higher qualification effort.

A formally verified pipeline reduces the TCL requirement: if the tool is proven correct, the confidence in its output is higher, and the qualification effort per project is lower. The tool is qualified once. Each project that uses it inherits that qualification — subject to impact analysis and integration testing, but without re-verifying the tool's internal correctness.

In DO-178C, the DO-330 supplement provides a framework for tool qualification. A verified compiler (like CompCert) satisfies the highest qualification criteria (TQL-1) because it can be shown to not introduce errors. A verified build pipeline — meld + loom + synth, each proven correct — would target the same classification.

{% note(kind="warning") %}
None of this exists today in qualified form. No Wasm runtime or toolchain has undergone ISO 26262 or DO-178C qualification. CompCert took years of research and engineering to reach production qualification. We are at the beginning of this path — the tools exist, the verification approaches are being developed, and the goal is clear. Claiming otherwise would be dishonest.
{% end %}

## The long game

Qualifying a toolchain for safety-critical use is measured in years, not months. The path:

1. **Build the tools** — meld, loom, synth, kiln, sigil. Ship working software that people can use. *(In progress.)*
2. **Add verification** — Z3 translation validation in loom, Verus proofs for critical algorithms, Rocq formalization of the semantic model. *(Starting.)*
3. **Demonstrate the pipeline** — end-to-end, from Component Model source to verified firmware, on a real embedded target. *(Future.)*
4. **Pursue qualification** — work with a certification authority to qualify the pipeline for a specific standard and domain. *(Long-term.)*

Each step builds on the previous one. The tools have to work before they can be verified. The verification has to exist before it can be qualified.

*Next in the series: [part 7 — the toolchain: hermetic builds and supply chain attestation](/blog/hermetic-toolchain/).*

If you are working on formal verification of WebAssembly or tool qualification for safety-critical systems — we would like to hear from you. Everything is at [github.com/pulseengine](https://github.com/pulseengine).
