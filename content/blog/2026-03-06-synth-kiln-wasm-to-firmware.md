+++
title = "synth + kiln: from Wasm to firmware"
description = "synth transcodes optimized Wasm to native code. kiln provides the runtime layer — host and builtin component implementations that the native code links against. Together, they produce a firmware image with no Wasm runtime on the device."
date = 2026-03-12
draft = true
[taxonomies]
tags = ["deep-dive", "synth", "kiln", "series"]
authors = ["Ralf Anton Beier"]
+++

*This is part 5 of a series on building a verified WebAssembly pipeline for safety-critical embedded systems. [Part 1](/blog/zero-cost-component-model/) introduces the approach. [Part 4](/blog/loom-post-fusion-optimization/) covers post-fusion optimization.*

## The last mile

After meld fuses and loom optimizes, the result is a flat, optimized core Wasm module. For cloud and server targets, this is where the pipeline ends — hand the module to wasmtime or another runtime. For embedded targets, there is one more step: the Wasm module must become native code that runs directly on the hardware.

This is what synth and kiln do together.

## synth: Wasm to native

synth transcodes the fused Wasm module to native machine code — an ELF binary or firmware image for the target architecture. ARM Cortex-M is the first backend, with the architecture designed for pluggable backends so that additional targets (TriCore, RISC-V, or others) are separate implementations.

synth aims for provably correct transcoding: a proof that the Wasm input and the native output are semantically equivalent. This is the hardest part of the pipeline to verify, and it is early work.

### The landscape

Wasm-to-native is not a new idea. Several tools exist:

- **[wasm2c](https://github.com/WebAssembly/wabt)** (WABT) transpiles Wasm to C, then compiles with any standard toolchain. This is pragmatically powerful — you get GCC, Clang, or a qualified safety-critical compiler (IAR, Green Hills, Wind River Diab), and for safety-critical work, the qualification burden shifts to the C compiler — which may already be qualified for the target domain. Siemens and Stanford demonstrated a [3 KB ROM Wasm runtime](https://cs.stanford.edu/~keithw/) using this approach.

- **[aWsm](https://github.com/gwsystems/aWsm)** (GW University + ARM Research) compiles Wasm to native via LLVM, targeting x86-64, aarch64, and ARM Cortex-M. Performance within 10% of native on microprocessors, within 40% on Cortex-M. Uses LLVM's full optimization pipeline.

- **[Infineon's TriCore AOT](https://github.com/Infineon/aurix_webassembly_aot)** translates Wasm to native TriCore for AURIX — their ASIL-D automotive MCU. Direct instruction translation for a specific production target.

- **WAMR AOT** (wamrc) compiles Wasm ahead of time, but the output still requires the WAMR runtime on the device for system calls and memory management.

All of these produce native code at build time — not at runtime. DLR's DASC 2025 paper notes that JIT and AOT at *runtime* generate executable object code, "a behavior which is not foreseen by current regulations." Build-time transcoding avoids this entirely, and this applies to all the tools above, not just synth.

### Where synth fits

synth's differentiator is not that it produces native code — others do that. It is:

1. **Pipeline integration.** synth receives meld+loom output, which is already fused and optimized. The other tools take raw Wasm modules. meld+loom as a preprocessing step would benefit any of them.

2. **Proof correctness.** synth aims to prove that its transcoding preserves semantics. This is the same verification goal that runs through the entire pipeline — meld proves fusion correct, loom proves optimization correct, synth proves transcoding correct, sigil attests the chain.

3. **Pluggable backends.** The architecture separates target-specific code generation from the common transcoding framework, so adding a TriCore or RISC-V backend does not require redesigning the pipeline.

{% note(kind="warning") %}
synth is early. The ARM Cortex-M backend is the first target. Proof correctness is the goal, not the current state. The wasm2c path (Wasm to C, then a qualified C compiler) is a pragmatically viable alternative for teams that need a certified toolchain today.
{% end %}

## kiln: the runtime layer

When synth transcodes user component logic to native code, the result is not a standalone binary. The component has imports — WASI calls, host functions, resource lifecycle management. Something must provide those implementations on the target device.

That is kiln.

kiln is the backend for the builtin and host components that synth generates. When the native code calls `get-stdout`, `exit`, or any other WASI function, kiln provides the implementation. When a resource handle needs to be allocated or dropped, kiln manages the table. When the component's memory needs initialization, kiln sets it up.

kiln is not just a WASI shim. It is a `no_std` Component Model runtime in Rust, designed for the same constrained targets that synth produces code for. It provides:

- **WASI 0.2 implementations** for the host interfaces the component imports
- **Resource handle management** for component-level resources
- **Memory and table initialization** for the fused module
- **An interpreter mode** for targets where native transcoding is not needed or not yet available

The firmware image that ships to the device contains synth's native code *and* kiln's runtime layer, linked together. kiln is not an alternative to synth — it is the other half.

### kiln as interpreter

For targets where interpretation is preferred — perhaps for flexibility, for hot-loading Wasm updates without reflashing, or because a synth backend does not exist for the architecture — kiln provides a `no_std` Component Model interpreter. This is the same runtime, the same WASI implementations, the same resource management — but executing Wasm bytecode instead of native transcoded code.

## From component to firmware

The full path:

1. Developer writes components against WIT interfaces, in any language
2. **meld** fuses them into a flat core module
3. **loom** optimizes across the erased boundaries
4. **synth** transcodes to native for the target (or the module runs on kiln's interpreter)
5. **kiln** provides the host/builtin runtime layer
6. **sigil** attests every step
7. The result is a firmware image: native user code + kiln runtime, ready to flash

No Wasm runtime on the device. No Component Model overhead at runtime. The full composition model was available during development and has been erased by the time the code reaches the target.

*Next in the series: [part 6 — proving the pipeline](/blog/proving-the-pipeline/).*
