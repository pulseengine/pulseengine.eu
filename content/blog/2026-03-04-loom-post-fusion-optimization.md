+++
title = "loom: why optimizing after fusion is not the same as wasm-opt"
description = "After meld fuses components into a flat module, loom optimizes across boundaries that no longer exist. A fused optimizer that understands what meld produces, with optional Z3 translation validation to verify the result."
date = 2026-03-09
draft = true
[taxonomies]
tags = ["deep-dive", "loom", "series"]
authors = ["Ralf Anton Beier"]
+++

*This is part 4 of a series on building a verified WebAssembly pipeline for safety-critical embedded systems. [Part 1](/blog/zero-cost-component-model/) introduces the approach. [Part 3](/blog/meld-component-fusion/) covers where meld is heading with cross-component fusion.*

## What loom does

After meld fuses a WebAssembly component into a flat core module, the result is structurally simple but not yet optimized. The adapter trampolines are gone, the indirect dispatch tables are collapsed, the import chains are resolved — but the code still carries artifacts of its multi-module origin. Dead functions from adapter generation, redundant memory operations from same-memory copies, trivial forwarding calls that used to cross component boundaries.

loom is an optimization pipeline designed specifically for this fused output.

## The fused optimizer

This is what makes loom different from a general-purpose Wasm optimizer. The fused optimizer understands the patterns that meld produces:

**Adapter devirtualization.** When meld fuses components, it generates adapter functions — thin wrappers that forward calls between what used to be separate modules. loom detects these trivial forwarders and rewrites callers to call the target directly. The adapter becomes dead code and gets eliminated.

**Same-memory adapter collapse.** In the Component Model, cross-component calls copy data between linear memories. After meld fuses components that share the same memory (which is common — the adapter and main module typically share memory), the copy becomes a same-address copy. loom detects this pattern and eliminates the redundant allocation and memcpy entirely.

**Canonical ABI cleanup.** meld resolves `canon lift` / `canon lower` pairs into concrete function calls, but the resulting code may still contain patterns like trivial `cabi_post_return` functions (empty cleanup stubs) or duplicate type definitions from the original multi-module structure. The fused optimizer cleans these up.

These are patterns that [wasm-opt](https://github.com/WebAssembly/binaryen) — the standard Wasm optimizer — has no concept of. wasm-opt does not understand the Canonical ABI, does not know what a meld adapter looks like, and [does not support Component Model input at all](https://github.com/WebAssembly/binaryen/issues/6728).

## What wasm-opt does well

This is not a competition. wasm-opt is production-grade, battle-tested across Emscripten, Rust, and LLVM, with 10 years of development and over 150 optimization passes. For standard Wasm optimization — constant folding, dead code elimination, inlining, loop-invariant code motion, register allocation, GC type optimization, SIMD — wasm-opt is the ecosystem standard and categorically more comprehensive than loom's general-purpose passes.

After meld fuses and loom applies its fused optimizer, running wasm-opt on the result is a reasonable and complementary step. loom handles the fusion-specific patterns; wasm-opt handles the deep general-purpose optimization. They work on different layers of the problem.

## Where loom goes further: Z3 translation validation

For safety-critical systems, "the optimizer probably didn't break anything" is not sufficient. loom includes optional translation validation via Z3 SMT solving: after optimizing a function, loom can encode both the original and optimized versions as logical formulas and ask Z3 to prove they are semantically equivalent.

This is not full formal verification of the optimizer itself — it is a per-function post-hoc check that the specific optimization applied to the specific function preserved semantics. If Z3 finds a counterexample, the optimization is rejected for that function.

{% note(kind="warning") %}
Translation validation is implemented but has limitations. It currently works on functions with straightforward control flow. Complex branching patterns, indirect calls, and memory aliasing require further work. This is an active area of development, not a production capability.
{% end %}

The direction is clear: every optimization loom applies should be verifiable. Not just tested — proven, function by function, transformation by transformation. This connects to the broader verification story across the pipeline, covered in [part 5](/blog/proving-the-pipeline/).

## The optimization pipeline

Beyond the fused optimizer, loom runs a multi-phase pipeline on the fused module:

1. **Fused optimizer** — adapter devirtualization, same-memory collapse, Canonical ABI cleanup
2. **Constant propagation** — replace immutable globals with their values
3. **Constant folding** — fold arithmetic on known values, algebraic identities, strength reduction
4. **Common subexpression elimination** — deduplicate repeated computations
5. **Function inlining** — inline small functions exposed by fusion
6. **Post-inline constant folding** — second pass to exploit inlining results
7. **Loop-invariant code motion** — hoist loop-invariant expressions
8. **Branch simplification and dead code elimination** — clean up control flow
9. **Block merging and local simplification** — final cleanup

The first phase is what makes loom unique. Phases 2-9 are standard compiler optimizations — loom implements them, wasm-opt implements them better. The value of having them in loom is pipeline integration and the ability to validate each transformation with Z3.

## What's next for loom

- Expanding Z3 validation coverage to handle more control flow patterns.
- Validating the fused optimizer against meld's evolving output as meld gains cross-component fusion.
- Exploring whether loom's fused optimization passes could be contributed upstream as Binaryen passes for the broader ecosystem.
- ISLE rule compilation — loom uses Cranelift's ISLE pattern-matching infrastructure for its type representation, with the goal of expressing optimization rules declaratively. This is infrastructure that is set up but not yet active.

*Next in the series: [part 5 — synth + kiln: from Wasm to firmware](/blog/synth-kiln-wasm-to-firmware/).*
