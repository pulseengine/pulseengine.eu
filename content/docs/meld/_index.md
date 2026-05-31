+++
title = "meld"
description = "Fuse multiple WebAssembly components into a single module"
template = "docs-section.html"
sort_by = "weight"
weight = 30
+++

## What it does

meld takes multiple WebAssembly components and fuses them into a single core module. Imports match exports, dependency order is resolved, index spaces are remapped, and cross-component calls get adapter trampolines. The output is one deployable `.wasm` binary with no runtime linking.

**Input:** two or more `.wasm` component files.
**Output:** a single fused `.wasm` core module.

## When to use it

Use meld when you have composed WebAssembly components (built with rules_wasm_component or wasm-tools) and need a single binary for deployment — especially in embedded or safety-critical environments where runtime component linking is unacceptable.

## Getting started

```sh
# Build from source
git clone https://github.com/pulseengine/meld
cd meld && cargo install --path meld-cli

# Fuse two components
meld fuse component_a.wasm component_b.wasm -o fused.wasm

# With shared memory (default is multi-memory)
meld fuse --memory shared a.wasm b.wasm -o fused.wasm
```

## How it connects

- **rules_wasm_component:** builds the components that meld fuses
- **spar:** generates the WIT interfaces that define the component boundaries
- **loom:** optimizes the fused output
- **sigil:** signs the fused binary
- **rivet:** tracks STPA safety analysis for the fusion pipeline

## Limitations

- Not published to crates.io — build from source
- Parser and attestation stages have placeholder proofs only
- Instruction rewriting has spec-level support but no implementation proof yet
- The `rocq-of-rust` translation covers offset computation and memory layout; larger functions are not yet translated

## Reference

- [Architecture](/docs/meld/architecture/) — the five-stage fusion pipeline
- [Proof Status](/docs/meld/proof-status/) — what is proved, what has placeholders, known gaps
- [Proof Guide](/docs/meld/proof-guide/) — how to read and extend the Rocq proofs
- [Proof Decisions](/docs/meld/proof-decisions/) — key design choices in the proof architecture
