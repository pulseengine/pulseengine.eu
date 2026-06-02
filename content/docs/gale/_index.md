+++
title = "gale"
description = "Drop-in verified Rust replacement for Zephyr RTOS kernel primitives"
template = "docs-section.html"
sort_by = "weight"
weight = 40
+++

## What it does

gale replaces Zephyr RTOS kernel C source files with formally verified Rust equivalents. Your Zephyr application code does not change. The C API stays the same — gale provides the implementation behind it through an FFI layer that is itself verified to match the Rust model.

**Input:** a Zephyr project using standard kernel APIs (semaphores, mutexes, message queues, etc.).
**Output:** the same Zephyr application, running on verified kernel primitives instead of the original C.

## When to use it

Use gale when you need a Zephyr-based RTOS with verified kernel correctness for safety-critical certification (ASIL-D, SIL 4). Your application code, drivers, and Zephyr subsystems remain unchanged. Only the kernel primitives are replaced.

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
- **Verus/Rocq/Lean:** three independent formal verification paths on every kernel primitive
- **Kani:** bounded model checking exhaustively explores reachable states
- **rivet:** tracks every requirement, design decision, and verification result; STPA safety analysis managed as rivet artifacts
- **kiln:** gale and kiln together provide the runtime platform for relay and wohl

## Limitations

- Formal verification tools (Verus, Rocq, Lean, Kani, Miri) do not yet run in CI — they require Bazel + Nix toolchains
- Functional tests (cargo test, Zephyr integration, Renode) run on every commit
- The [verification honesty assessment](/docs/gale/verification/) documents exactly what is proven vs what is tested

## Reference

- [Getting Started (full)](/docs/gale/getting-started/)
- [Verification Status](/docs/gale/verification/) — what is proven, what is not
- [Kernel Coverage](/docs/gale/coverage/) — which primitives are replaced, which are excluded and why
- [Safety Analysis](/docs/gale/safety/) — STPA analysis
