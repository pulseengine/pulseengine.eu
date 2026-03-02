+++
title = "The toolchain: hermetic builds and supply chain attestation"
description = "A verified pipeline needs a reproducible build system. Bazel provides hermeticity, Nix provides toolchain reproducibility, and sigil attests every transformation. This is how the pieces fit together."
date = 2026-03-18
draft = true
[taxonomies]
tags = ["deep-dive", "sigil", "bazel", "series"]
authors = ["Ralf Anton Beier"]
+++

*This is part 7 of a series on building a verified WebAssembly pipeline for safety-critical embedded systems. [Part 1](/blog/zero-cost-component-model/) introduces the approach. [Part 6](/blog/proving-the-pipeline/) covers formal verification of each transformation.*

{% insight() %}
Any engineer, on any machine, can reproduce the exact build that produced any released artifact. This is not just good engineering practice — it is a regulatory requirement. ISO 26262 demands traceability from requirements to deployed artifact. DO-178C requires configuration management that can reproduce any released build. A hermetic, attested build pipeline satisfies both from a single infrastructure investment.
{% end %}

## Why reproducibility matters

Formal verification proves that a transformation *can* preserve semantics. But if you cannot reproduce the exact build that produced a specific artifact, the proof is disconnected from reality. You need both: correctness (the algorithm is right) and reproducibility (this specific binary was produced by this specific verified pipeline, with these specific inputs).

For safety-critical qualification, this is not optional. ISO 26262 requires traceability from requirements through implementation to the deployed artifact. DO-178C requires configuration management that can reproduce any released build. If your toolchain produces different outputs on different machines or at different times, qualification becomes impractical.

[Ferrocene](https://ferrocene.dev/) — the qualified Rust compiler for safety-critical systems — understood this early. Cargo is included in their distribution but explicitly not qualified — qualifying a tool that touches the internet and executes arbitrary build scripts is prohibitively complex. For safety-critical production builds, Ferrocene's [Safety Manual](https://public-docs.ferrocene.dev/main/safety-manual/rustc/constraints.html) requires invoking `rustc` directly, bypassing cargo entirely, with procedural constraints: clean build environments, build monitoring, controlled environment variables. [CriticalUp](https://github.com/ferrocene/criticalup) manages toolchain distribution with cryptographic signature verification.

The PulseEngine pipeline automates what Ferrocene achieves through procedural controls. Bazel invokes compilers directly (not through cargo), enforces hermeticity through sandboxing, and tracks every input and output in the build graph. Nix provides reproducible toolchain provisioning. sigil attests the chain.

## Bazel: the build system

Every tool in the PulseEngine pipeline builds with [Bazel](https://bazel.build/). Bazel's hermetic build model — where every input is declared, every action is sandboxed, and outputs are cacheable and reproducible — aligns directly with the requirements of a qualified toolchain.

More importantly, Bazel allows the pipeline tools themselves to be composed as build rules. Building a WebAssembly component, fusing it with meld, optimizing with loom, and transcoding with synth are all build actions that Bazel can track, cache, and reproduce.

### rules_wasm_component

[rules_wasm_component](https://github.com/pulseengine/rules_wasm_component) is the foundation — Bazel rules for WebAssembly Component Model development. At v1.0.0 with over 770 commits, it is the most mature piece of the build infrastructure. It supports multi-language component builds (Rust, C, C++, Go, MoonBit), dependency management, multi-profile builds, and integration with the broader Bazel ecosystem through the [Bazel Central Registry](https://registry.bazel.build/).

This is where the Component Model enters the build graph. Components built with these rules flow into the pipeline — meld, loom, synth — as hermetically tracked artifacts.

### rules_rocq_rust

[rules_rocq_rust](https://github.com/pulseengine/rules_rocq_rust) provides Bazel rules for the [Rocq](https://rocq-prover.org/) theorem prover and [rocq-of-rust](https://github.com/formal-land/rocq-of-rust) integration. This is how formal proofs enter the build system: Rocq proofs are compiled alongside the Rust implementation, ensuring that proof artifacts stay in sync with the code they verify.

rules_rocq_rust already uses [Nix](https://nixos.org/) for hermetic toolchain management — Rocq's dependency chain is complex, and Nix provides the reproducibility guarantee that Bazel's sandboxing alone cannot for toolchains with external dependencies.

### rules_verus

[rules_verus](https://github.com/pulseengine/rules_verus) brings [Verus](https://github.com/verus-lang/verus) — SMT-based Rust verification — into Bazel. Verus proofs are expressed in Rust syntax, making them natural to integrate with Rust build rules. This is early work — the rules exist but are not yet production-grade.

### rules_moonbit

[rules_moonbit](https://github.com/pulseengine/rules_moonbit) provides hermetic [MoonBit](https://www.moonbitlang.com/) toolchain support in Bazel. MoonBit compiles to WebAssembly and is one of the languages supported by rules_wasm_component for component development.

## Nix: toolchain reproducibility

Bazel provides hermetic *builds* — every action is sandboxed, inputs are declared, outputs are deterministic. But the *toolchain itself* — the compiler, the linker, the verification tools — must also be reproducible. If two developers have different versions of Rocq or Verus, the proofs may not match.

[Nix](https://nixos.org/) solves this. A Nix flake pins every toolchain dependency to an exact revision, and Nix's content-addressed store ensures that the same inputs always produce the same outputs. Where Bazel sandboxes the build actions, Nix sandboxes the toolchain provisioning.

Today, only rules_rocq_rust uses Nix for toolchain management. Extending Nix flakes across the entire pipeline — meld, loom, synth, kiln, sigil — is an active priority. The goal: any developer, on any machine, can reproduce the exact build environment that produced any released artifact.

## sigil: attesting the chain

Formal verification proves correctness. Reproducibility ensures consistency. [sigil](https://github.com/pulseengine/sigil) proves provenance: this specific artifact was produced by this specific pipeline.

sigil uses [Sigstore](https://www.sigstore.dev/) keyless signing for each pipeline stage. The final artifact carries a chain of attestations — one per transformation — that links it back to the source component and the exact tool versions that produced it.

- **Wasm module signing** — sigil signs Wasm modules using custom sections, following the approach from [wasmsign2](https://github.com/wasm-signatures/wasmsign2).
- **SLSA provenance** — attestations follow the [SLSA](https://slsa.dev/) framework, providing standardized supply chain metadata.
- **In-toto layouts** — pipeline steps are expressed as [in-toto](https://in-toto.io/) layouts, enabling third-party verification of the supply chain.

### The attestation chain

Verification says: "meld's fusion algorithm is correct."
Reproducibility says: "this build environment matches the qualified configuration."
sigil says: "this specific ELF was produced by meld v0.1.0 → loom v0.2.0 → synth v0.1.0, from this specific source component, at this time, with these configuration parameters."

For audit and qualification purposes, this chain is the evidence trail. An assessor can verify not just that the tools are correct, but that the correct tools were actually used to produce the artifact under review.

### Signing native artifacts

Today, sigil signs Wasm modules. After synth transcodes to native, the artifact is an ELF binary, not a Wasm module. Signing native artifacts — ELF sections, MCUboot TLV headers for secure boot — is [in progress](https://github.com/pulseengine/sigil/issues/47) to complete the attestation chain from source to deployed firmware.

{% note(kind="warning") %}
The build infrastructure is real and actively used, but not yet complete. Nix integration is partial — only rules_rocq_rust uses it today. sigil's attestation chain covers Wasm artifacts but not yet native binaries. rules_verus is early. We are building toward full hermetic reproducibility with end-to-end attestation, and we are honest about what is and is not done.
{% end %}

## Tying it together

The qualified pipeline vision:

1. **Bazel** tracks every input, action, and output in the build graph
2. **Nix** ensures the toolchain is identical across all environments
3. **meld + loom + synth** transform components to firmware (each verified — [part 6](/blog/proving-the-pipeline/))
4. **sigil** attests every step with cryptographic evidence
5. The result: a firmware image with a complete, verifiable chain from source to binary

This is not a new idea. It is the combination that matters — hermetic builds, verified transformations, and cryptographic attestation, applied to the specific problem of WebAssembly-based safety-critical systems.

If you are working on reproducible builds for safety-critical toolchains, Bazel for embedded, or supply chain security for WebAssembly — we would like to hear from you. Everything is at [github.com/pulseengine](https://github.com/pulseengine).
