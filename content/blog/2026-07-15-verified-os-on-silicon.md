+++
title = "A verified OS, composed to 3.5 KB on real silicon"
description = "gust is a small RTOS — a cooperative scheduler, the classic primitives (semaphore, mutex, message queue, event), and device drivers — built entirely from verified WebAssembly components. They don't run on a runtime; they compose at build time into one native image of about 3.5 KB, bit-identical on three real chips, over a trusted base of ~77 lines. Here's how it fits together."
date = 2026-07-15
draft = true
[taxonomies]
tags = ["wasm", "embedded", "verification", "how-it-works"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
`gust` is a small operating system — a cooperative scheduler, the classic RTOS
primitives (semaphore, mutex, message queue, event), and device drivers — and every
part of it is a **verified WebAssembly component**. Those components don't run *on* a
wasm runtime. They **compose at build time into a single native image of about
3.5 KB**, running bit-identical on a Cortex-M3, a Cortex-M4, and a RISC-V chip. The
only thing you have to *trust* underneath is a **~77-line native shim**. Here's how it
fits together.
{% end %}

## The stack

Everything above the line is verified wasm, composed by [meld](https://github.com/pulseengine/meld)
into one core module; below it is the trusted native base — a thin capability seam and
a tiny shim, and nothing else.

{% mermaid() %}
flowchart TB
  subgraph verified["verified wasm — meld-composed into one core module"]
    direction TB
    app["app component<br/>imports gale:kernel"]
    os["gale-kiln · the OS<br/>exports gale:kernel — scheduler + sem·msgq·mutex·event"]
    drv["7 thin-seam drivers<br/>uart · dma · gpio · timer · spi · i2c · adc"]
    app --- os --- drv
  end
  drv ==>|"gust:hal/mmio — read32 · write32"| tcb
  subgraph trusted["trusted native base"]
    direction TB
    tcb["~77-line TCB shim · 5 atoms<br/>vector table · SysTick · mmio / irq / dma"]
    hw["Cortex-M · RISC-V silicon"]
    tcb ==> hw
  end

  classDef ours fill:#242836,stroke:#6c8cff,color:#e1e4ed;
  classDef trust fill:#161922,stroke:#4ade80,color:#e1e4ed;
  class app,os,drv ours
  class tcb,hw trust
{% end %}

An **app** component imports the `gale:kernel` interface. A **gale-kiln** component
*exports* it — that's the OS itself: [kiln](https://github.com/pulseengine/kiln)'s
cooperative scheduler over [gale](https://github.com/pulseengine/gale)'s verified
kernel primitives. The **drivers** import only the thin `gust:hal/mmio` capability.
Each piece is built and verified on its own, with real sizes and real proofs:

| component | flash | imports / exports | proven (Kani unless noted) |
|---|---|---|---|
| `gale-app-demo` | ~0.6 KB | imports `gale:kernel` | the app's own logic |
| `gale-kiln` (scheduler + primitives) | ~1.2 KB | **exports** `gale:kernel` | semaphore shipped (Verus + Rocq); rest in progress |
| `uart-thin` | 254 B | `gust:hal/mmio` + `irq` | RX-decision FSM over all 2³² status words |
| `dma-own` | 218 B | + `dma` resource | ownership FSM, 6/6 (access-iff-owned, barrier-pairing, …) |
| `gpio-thin` | 490 B | `gust:hal/mmio` | 4/4 (bounded, injective, mode-safe) |
| `timer-thin` | 212 B | `gust:hal/mmio` | 3/3 (wrap-safe deadline across u32 wrap) |
| `spi-thin` | 494 B | `gust:hal/mmio` | 6/6 (exclusive-bus, no-lost-byte, …) |
| `i2c-thin` | 992 B | `gust:hal/mmio` | 7/7 (ACK-all-but-last, phase-gating, …) |
| `adc-thin` | 754 B | `gust:hal/mmio` | 7/7 (channel-bounds, read-after-EOC, …) |

## Drivers over a two-function seam

The design idea is the driver row. Each driver is *verified wasm* that imports
**only** `gust:hal/mmio` — two functions, `read32` and `write32`. A GPIO driver is
490 bytes of Kani-proven logic sitting over **two** trusted primitives, not 490 bytes
you have to trust. Adding a driver adds **zero new trusted atoms**: it rides the same
two-function seam.

So the whole trusted native base is small and fixed. It's a **~77-line Rust shim** —
the vector table and reset handler, a one-line SysTick tick, and **five MMIO "atoms"**:
`mmio_read32`, `mmio_write32`, `irq_poll`, and `dma_program` / `dma_barrier` for DMA.
That is the entire thing you extend trust to. Everything else — scheduler, IPC, every
driver — is verified wasm above the line.

## How it composes

Composition is a build-time operation, and the exact chain is worth seeing, because
"fuse → optimize → compile" hides what actually happens:

```text
gale-app-demo.wasm   (~0.6 KB, imports gale:kernel, memory.grow = 0)
gale-kiln.wasm       (~1.2 KB, exports gale:kernel, memory.grow = 0)

meld  fuse --memory shared --address-rebase   →  fused.wasm   # imports resolved against
                                                              # exports, ONE shared memory
loom  optimize --passes inline                →  whole-program inline
      strip exports  (keep {memory, run-demo}) →  240 B wasm
synth compile --target cortex-m3 --relocatable →  fused.o      # 668 B .text, 0 undefined symbols
link  fused.o + ~77-line native TCB shim       →  3.5 KB image, 8 B bss   # fits F100's 8 KB SRAM
```

Upstream of `meld` it's separate components with typed WIT worlds. The instant `meld`
resolves the app's `import gale:kernel` against gale-kiln's `export`, the component
boundaries are gone — [loom](https://github.com/pulseengine/loom) and
[synth](https://github.com/pulseengine/synth) see one flat core module, and the
shipped artifact has **no runtime underneath it at all**. The kernel dissolves to a
668-byte `.text`; the whole image, TCB included, is about 3.5 KB and fits the 8 KB of
SRAM on an STM32F100.

## Does the native code still do what the wasm did?

The demo answers in one number. `run-demo()` runs a fixed sequence of semaphore
operations and returns a bitfield; the correct answer is **53** (`0b110101` —
would-block, increment, full). It returns **53** three ways: under `wasmtime` (the
component composition, interpreted), on **qemu Cortex-M3**, and on a **real STM32F100**
read out with the hardware cycle counter. The kill-criterion is blunt: *either side
≠ 53 falsifies the dissolve.*

Two honest notes on that. First, this is a **differential equivalence check against a
reference semantics — not a proof of translation.** The component *logic* is verified
(Verus/Rocq/Kani); that the dissolved native code matches the wasm is *tested*, bit for
bit, not yet proven. Second, it's measured on real hardware and it's fast: bit-identical
against native LLVM, the dissolved code runs at **1.73×** on the Cortex-M3 (STM32F100),
**1.45×** on the Cortex-M4 (Nucleo G474RE), and **1.84×** on RISC-V (ESP32-C3).

## What it buys, and where it is

The point of composing an OS this way is the shape of the trust: **verified logic all
the way up, a tiny fixed native base at the bottom, and no runtime in between.** A new
peripheral is a new verified-wasm driver over the same two-function seam — it doesn't
grow the thing you trust. And because the components dissolve to native, you pay
nothing at runtime for the abstraction: one small image, on the metal.

Honest about where it stands: the **semaphore is fully shipped** (Verus + Rocq + Kani +
on-hardware tests); the other primitives and the drivers are Kani-proven with some
Renode content-gates still landing; the wasm→native dissolve is differentially tested,
not yet proven-equivalent; and multi-tenant isolation (MPU) is still on the roadmap.
It's work in progress. But the composition is real, and it runs — a verified operating
system that dissolves to 3.5 KB of native code, on three real chips.

---

*Where this sits in the wider toolchain: [how it works](@/how-it-works.md).*
