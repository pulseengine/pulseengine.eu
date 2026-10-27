+++
title = "gale"
description = "Drop-in Rust replacement for Zephyr RTOS kernel primitives, with Verus contracts on the source and Rocq proofs over models"
template = "docs-section.html"
sort_by = "weight"
weight = 40
+++

## What it does

gale replaces Zephyr RTOS kernel C source files with Rust equivalents. Verus checks the Rust source against its contracts, Rocq proves invariants of abstract models of some primitives, and Lean proves scheduling theory. Your Zephyr application code does not change. The C API stays the same: gale provides the implementation behind it through an FFI layer that Kani bounded-checks and differential tests compare against the Rust model. The FFI shims Verus does not look inside are reviewed by eye against the C they replace.

**Input:** a Zephyr project using standard kernel APIs (semaphores, mutexes, message queues, etc.).
**Output:** the same Zephyr application, running on gale's Rust kernel primitives instead of the original C.

## When to use it

Use gale when you are working toward safety-critical certification on a Zephyr-based RTOS and want kernel primitives that carry machine-checked evidence. gale targets ASIL-D; it is not certified, and what its proofs cover is listed in [Verification Status](/docs/gale/verification/). Your application code, drivers, and Zephyr subsystems remain unchanged. Only the kernel primitives are replaced.

## Getting started

```sh
git clone https://github.com/pulseengine/gale
cd gale

# Run the test suite
cargo test

# Run Zephyr integration tests (requires Zephyr SDK + west)
west build -b qemu_cortex_m3 zephyr/gale_sem.c
west build -b qemu_cortex_m3 zephyr/gale_mutex.c
```

Enable gale in your Zephyr project by adding the overlay:

```
CONFIG_GALE_KERNEL_SEM=y
CONFIG_GALE_KERNEL_MUTEX=y
# ... per-primitive CONFIG flags
```

Each primitive has its own CONFIG guard — adopt incrementally.

## How it connects

- **spar:** models the kernel architecture in AADL; scheduling analysis validates timing before implementation
- **Verus:** SMT checks of requires/ensures contracts on all 39 modules, with a declared trusted base of `external_body` functions
- **Rocq:** theorem proving over hand-written models, fully proven for 10 modules; `poll`, `sched` and `thread_lifecycle` are `Admitted` stubs
- **Lean:** scheduling theory (RMA bound, priority ceiling, priority-queue ordering), not implementation proofs
- **Kani:** bounded model checking; the kernel harnesses hold within stated bounds such as `count <= 20`
- **rivet:** tracks every requirement, design decision, and verification result; STPA safety analysis managed as rivet artifacts
- **kiln:** gale and kiln together provide the runtime platform for relay and wohl

## Limitations

- Verus, Kani, Rocq and Lean run in gale's Formal Verification workflow on pull requests that touch proof-relevant paths, on pushes, and weekly. A green run is not "all proven": Rocq accepts `Admitted`, and Verus runs without `--no-cheating`, so its declared trusted base is accepted
- The proofs are about the Rust source and abstract models. The native code the meld, loom and synth pipeline produces from it is differentially tested against a reference semantics, not proven equivalent
- Functional tests (cargo test, Zephyr integration, Renode) run on every commit
- The [verification honesty assessment](/docs/gale/verification/) documents exactly what is proven vs what is tested

## Reference

- [Getting Started (full)](/docs/gale/getting-started/)
- [Verification Status](/docs/gale/verification/) — what is proven, what is not
- [Kernel Coverage](/docs/gale/coverage/) — which primitives are replaced, which are excluded and why
- [Safety Analysis](/docs/gale/safety/) — STPA analysis
