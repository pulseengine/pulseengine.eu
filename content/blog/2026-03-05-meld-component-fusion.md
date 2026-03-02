+++
title = "meld: from intra-component fusion to cross-component composition"
description = "meld v0.1.0 fuses the internal structure of a single component. The next step is fusing multiple components that talk to each other — resolving cross-component calls, shared types, and resource lifecycles at build time."
date = 2026-03-06
draft = true
[taxonomies]
tags = ["deep-dive", "meld", "series"]
authors = ["Ralf Anton Beier"]
+++

*This is part 3 of a series on building a verified WebAssembly pipeline for safety-critical embedded systems. [Part 1](/blog/zero-cost-component-model/) introduces the approach. [Part 2](/blog/meld-v0-1-0/) is a technical walkthrough of meld v0.1.0 — what `wit-component` produces and what meld does to it.*

## What meld does today

meld v0.1.0 handles intra-component fusion. A single WebAssembly component — the tree of core modules, shim modules, fixup modules, and canonical ABI operations that `wit-component` produces — gets flattened into one core module. The [v0.1.0 walkthrough](/blog/meld-v0-1-0/) shows this in detail: 4 core modules, 23 instances, and 23 canonical ABI operations become 1 module with 54 functions and direct calls.

This already solves a real problem. Every embedded Wasm runtime consumes core modules, not components. meld bridges that gap at build time — you develop with the Component Model, deploy as a core module.

## Where meld is heading

Intra-component fusion is the foundation. The harder and more valuable problem is cross-component fusion: taking multiple components that communicate through WIT interfaces and fusing them into a single artifact.

### Cross-component calls

When component A calls component B through a WIT interface, the Canonical ABI inserts a `canon lower` on the caller side and a `canon lift` on the callee side. These operations handle type conversion, memory allocation in the callee's linear memory, and potentially string transcoding.

After cross-component fusion, these become direct function calls within a single module. If both components share the same string encoding and the same memory (after fusion, they do), the entire lift/lower sequence reduces to a plain call with no marshalling overhead.

### Shared types and deduplication

Composed components often import the same WIT types and the same WASI interfaces. After fusion, these redundant definitions collapse. Duplicate type definitions, duplicate import declarations, duplicate resource handle tables — all resolved to single definitions.

### Resource lifecycle

Component Model `resource` types have handle tables that track ownership across component boundaries. When two components are fused, resources that were passed across the boundary become internal. The handle table management for those resources can be eliminated — the resource is now a direct reference within a single module.

Resources that cross the boundary to the *host* still need handle tables. But component-to-component resource passing becomes zero-cost after fusion.

### What this means for the pipeline

Cross-component fusion is where meld's output becomes significantly more valuable for loom. After intra-component fusion, loom already sees across what were module boundaries. After cross-component fusion, loom sees across what were *component* boundaries — enabling optimization across the entire composed application.

This is where the "zero-cost abstraction" claim gets its strongest support. The full Component Model — typed composition, isolation, versioned interfaces — is available during development. After meld, all of it is gone. What remains is a flat module that looks like it was written as a single program.

{% note(kind="warning") %}
Cross-component fusion is not implemented yet. meld v0.1.0 handles intra-component fusion only. The design for cross-component fusion is in progress — the challenges around resource lifecycle, string transcoding across different encodings, and memory layout merging are real engineering problems, not just implementation work.
{% end %}

## The role of meld in the pipeline

meld is the first transformation in the pipeline, and it sets up everything that follows:

- **For loom:** meld produces a flat module where former component boundaries are erased. loom's fused optimizer understands the specific patterns meld generates — adapter trampolines, same-memory copies, redundant imports — and eliminates them. The cleaner meld's output, the more loom can optimize.

- **For synth:** meld reduces the number of modules from many to one. synth transcodes one module to native code, not a graph of interconnected modules. This simplifies the transcoding problem significantly.

- **For kiln:** The host and builtin component implementations that kiln provides become the only remaining imports after meld has resolved everything internal. kiln's interface with the fused module is clean and minimal.

- **For sigil:** meld is the first transformation that sigil attests. The proof that fusion preserves semantics — that the fused module behaves identically to the composed component — is the foundation of the entire attestation chain.

## Who else works on composition

The Bytecode Alliance's [WAC](https://github.com/bytecodealliance/wac) (WebAssembly Composition) is the standard tool for composing components. WAC resolves imports against exports and produces a composed component — but the output is still a Component Model component with multiple core modules and instantiation chains. WAC composes; meld fuses.

[wasm-merge](https://github.com/WebAssembly/binaryen) (Binaryen) merges core modules by connecting imports to exports. It operates at the core module level, not the Component Model level — it has no concept of canonical ABI operations, WIT interfaces, or resource types.

meld operates at the Component Model level and produces core module output. It understands what `wit-component`, WAC, and the Canonical ABI generate, and resolves that structure into something any core Wasm runtime can consume.

*Next in the series: [part 4 — loom: post-fusion optimization](/blog/loom-post-fusion-optimization/).*
