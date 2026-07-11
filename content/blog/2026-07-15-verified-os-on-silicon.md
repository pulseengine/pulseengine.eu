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

The design idea is the driver row. Each driver is *verified wasm* that imports **only**
`gust:hal/mmio` — two functions, `read32` and `write32`. A GPIO driver is 490 bytes of
Kani-proven logic over **two** trusted primitives, not 490 bytes you trust; adding a
driver adds **zero new trusted atoms**.

So the trusted native base stays small and fixed — a **~77-line Rust shim**: the vector
table and reset, a one-line SysTick, and **five MMIO atoms** (`mmio_read32`,
`mmio_write32`, `irq_poll`, plus `dma_program` / `dma_barrier`). That's the whole thing
you trust. Everything else — scheduler, IPC, every driver — is verified wasm above the
line.

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
resolves the app's `import gale:kernel` against gale-kiln's `export`, the boundaries are
gone — [loom](https://github.com/pulseengine/loom) and
[synth](https://github.com/pulseengine/synth) see one flat core module, and the shipped
artifact has **no runtime underneath it at all**: a 668-byte kernel in a ~3.5 KB image,
on the metal.

## Does the native code still do what the wasm did?

The demo answers in one number. `run-demo()` runs a fixed sequence of semaphore
operations and returns a bitfield; the correct answer is **53** (`0b110101` —
would-block, increment, full). It returns **53** three ways: under `wasmtime` (the
component composition, interpreted), on **qemu Cortex-M3**, and on a **real STM32F100**
read out with the hardware cycle counter. The kill-criterion is blunt: *either side
≠ 53 falsifies the dissolve.*

Two honest notes. This is a **differential equivalence check against a reference
semantics — not a proof of translation**: the component *logic* is verified
(Verus/Rocq/Kani), but that the native code matches the wasm is *tested* bit-for-bit,
not proven. And it's fast — bit-identical against native LLVM at **1.73×** (Cortex-M3,
STM32F100), **1.45×** (Cortex-M4, Nucleo G474RE), **1.84×** (RISC-V, ESP32-C3).

## What it buys

The point of composing an OS this way is the shape of the trust: **verified logic all
the way up, a tiny fixed native base at the bottom, and no runtime in between.** A new
peripheral is a new verified-wasm driver over the same two-function seam — it doesn't
grow the thing you trust. And because the components dissolve to native, you pay
nothing at runtime for the abstraction: one small image, on the metal.

## The architecture, and where it's headed

v0.2 is a deliberate rung, not the destination. The **North Star is a general
multi-tenant verified OS**: mutually-distrusting components on one chip, each in its own
MPU region, each holding only the capabilities it's granted — all over the same thin
TCB. Here is that v1.0 target, and how far it is today:

{% mermaid() %}
flowchart TB
  t["tenants · mutually-distrusting, MPU-isolated"]
  seam["gust:os · one typed syscall seam<br/>time · log · spawn · channel · io"]
  os["kiln scheduler + gale primitives<br/>semaphore closed · rest in progress"]
  drv["drivers over gust:hal/mmio<br/>uart · dma today · + gpio timer spi i2c adc"]
  tcb["~77-line native TCB · 5 atoms<br/>+ MPU regions"]
  hw["Cortex-M3 / M4 silicon"]
  t -.-> seam
  seam -.-> os
  os ==> drv
  drv ==>|"read32 · write32"| tcb
  tcb ==> hw

  classDef shipped fill:#242836,stroke:#4ade80,color:#e1e4ed;
  classDef planned fill:#161922,stroke:#8b90a0,stroke-dasharray:5 3,color:#b6bac8;
  class os,drv,tcb,hw shipped
  class t,seam planned
{% end %}

*Green runs today (v0.2 — the composition, uart + dma, the semaphore, on silicon).
Dashed is planned: the `gust:os` syscall seam (v0.4) and mutually-distrusting tenants
under MPU (v0.5). The trusted base and its two-function seam never change as the stack
grows.*

The path there is a ladder, honest about where each rung stands:

- **v0.1 — a primitive, fully closed** *(shipped).* The semaphore, proven end-to-end
  (Verus + Rocq + Kani) and tested on hardware.
- **v0.2 — the composition, on silicon** *(shipped — everything above).* App +
  scheduler + primitives + drivers, dissolved to one native image on three chips.
- **v0.3 — driver breadth** *(next).* Prove the thin-seam model generalizes — GPIO,
  timer, SPI as verified-wasm drivers over the same two-function seam, **zero new
  trusted atoms**, fused into one node that still fits the F100's 8 KB.
- **v0.4 — the `gust:os` seam.** Replace ad-hoc imports with one typed syscall world:
  `time`, `log`, `spawn`, `channel`, `io`. The I/O is an **io_uring-shaped
  submit/completion queue** — *composed, not invented*, from parts already proven
  (`gale::msgq` for the rings, kiln for the executor, the driver seam for the device,
  `dma-own`'s `own<buffer>` for registered buffers), with the "valid until complete"
  buffer lifecycle enforced by the Component-Model type system instead of tracked at
  runtime.
- **v0.5 — isolation.** Two mutually-distrusting components in one image, each in its
  own MPU region; a faulting tenant can't corrupt a sibling or the TCB — hardware
  enforcement, not a trusted check. (Blocked on synth growing multi-memory lowering.)
- **v1.0 — the OS, cut.** The whole composition, signed, booting the *same* components
  on Cortex-M3 and Cortex-M4.

The invariant that makes the ladder tractable is the one from the driver row: **it
grows without growing the trusted base.** Every new capability is verified wasm over
the same two-function seam; MPU isolation is hardware, not new trusted code. The
kill-criterion is literally an `nm` atom-count check — the day a fourth native bridge
atom appears, the milestone fails.

Even *loading* an image is meant to be verified rather than trusted:
[scry](https://github.com/pulseengine/scry) computes the memory and stack bounds
host-side, [sigil](https://github.com/pulseengine/sigil) signs them into the module,
and kiln checks that signature before it believes the bounds — reject-at-load, on a
device that can't recompute them itself.

None of v0.3–v1.0 is built; the roadmap is typed requirements in rivet, where readiness
is a query over closed verification, not a calendar. But the shape is fixed and v0.2
runs — a verified OS that dissolves to 3.5 KB on three real chips, with a path to a
multi-tenant one that never grows what you trust.

---

*Where this sits in the wider toolchain: [how it works](@/how-it-works.md).*
