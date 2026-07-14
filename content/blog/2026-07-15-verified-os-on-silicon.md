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

Every part of `gust` is a verified wasm component, composed by
[meld](https://github.com/pulseengine/meld) and lowered to a single native image over
one trusted native base — a thin capability seam and a ~77-line shim, and nothing else.

An **app** component imports the `gale:kernel` interfaces (`sem`, `msgq`, `mutex`,
`event`). A **gale-kiln** component *exports* them — that's the OS itself:
[kiln](https://github.com/pulseengine/kiln)'s cooperative scheduler over
[gale](https://github.com/pulseengine/gale)'s verified kernel primitives. The
**drivers** import only the thin `gust:hal/mmio` capability — the hardware-abstraction
seam, two functions wide. Each piece is built and verified on its own, with real sizes
and real proofs (Kani is a bounded model checker for Rust; Verus/Rocq where noted):

| component | flash | imports / exports | proven (Kani unless noted) |
|---|---|---|---|
| `gale-app-demo` | ~0.6 KB | imports `gale:kernel/*` | the app's own logic |
| `gale-kiln` (scheduler + primitives) | ~1.2 KB | **exports** `gale:kernel/*` | semaphore shipped (Verus + Rocq); rest in progress |
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

So the trusted native base stays small and fixed — a **~77-line Rust shim** with a
**four-atom trusted base**: MMIO read, MMIO write, IRQ poll, and DMA transfer
(`dma_program` + `dma_barrier`, the one atom that hands off a buffer). That's the whole
thing you trust; the uart-only breadth node needs only three. Everything else —
scheduler, IPC, every driver — is verified wasm above the line.

## How it composes

Composition happens at build time — two typed components in, one native image out:

{% mermaid() %}
flowchart TB
  app["gale-app-demo · ~0.6 KB<br/>imports gale:kernel/*"]
  kiln["gale-kiln · ~1.2 KB<br/>exports gale:kernel/*"]
  fused["meld fuse → one component<br/>single shared memory"]
  opt["loom · inline across seam + strip<br/>→ 240 B core module"]
  obj["synth compile → cortex-m3<br/>→ 668 B .text"]
  img["link + ~77-line native TCB<br/>~3.5 KB image · fits F100's 8 KB SRAM"]

  app ==> fused
  kiln ==> fused
  fused ==> opt ==> obj ==> img

  classDef ours fill:#242836,stroke:#6c8cff,color:#e1e4ed;
  classDef base fill:#161922,stroke:#4ade80,color:#e1e4ed;
  class app,kiln,fused,opt ours
  class obj,img base
{% end %}

Upstream of `meld` it's separate components with typed WIT worlds. `meld` resolves the
app's imports of the `gale:kernel` interfaces against gale-kiln's exports into **one
self-contained component** with a single shared linear memory;
[loom](https://github.com/pulseengine/loom) then inlines across that now-internal seam,
so [synth](https://github.com/pulseengine/synth) compiles what is effectively **one flat
core module**. That last step is where the Component Model earns its keep: once the seam
is internal, the canonical-ABI adapters and now-unreachable code strip away — the
interface boundary costs *nothing* in the shipped image (it's how ~1.8 KB of input
components fall to a 240-byte core). The result has **no runtime underneath it at all**:
a 668-byte kernel in a ~3.5 KB image, on the metal.

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

The shape of the trust: **verified logic all the way up, a tiny fixed native base at the
bottom, no runtime in between.** A new peripheral is a new verified-wasm driver over the
same two-function seam — it doesn't grow what you trust, and because the components
dissolve to native, it costs nothing at runtime.

## The architecture, and where it's headed

v0.2 is a deliberate rung, not the destination. The **North Star is a general
multi-tenant verified OS**: mutually-distrusting components on one chip, each fenced into
its own MPU region (Memory Protection Unit — the hardware that traps out-of-bounds
access), each holding only the capabilities it's granted — all over the same thin TCB.
Here is that v1.0 target, and how far it is today:

{% mermaid() %}
flowchart TB
  t["tenants · mutually-distrusting, MPU-isolated"]
  seam["gust:os · one typed syscall seam<br/>time · log · spawn · channel · io"]
  os["kiln scheduler + gale primitives<br/>semaphore closed · rest in progress"]
  drv["drivers over gust:hal/mmio<br/>uart · dma today · gpio timer spi proven"]
  tcb["~77-line native TCB · 4 atoms<br/>+ MPU regions (v0.5)"]
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
- **v0.3 — driver breadth** *(drivers proven; fusing).* GPIO, timer, SPI as
  verified-wasm drivers over the same seam (Kani 4/4, 3/3, 6/6); four of them fuse into
  one ~2.4 KB node at **three** trusted atoms and 0 SRAM — the thin-seam model
  generalizing past uart + dma.
- **v0.4 — the `gust:os` seam.** Replace ad-hoc imports with one typed syscall world:
  `time`, `log`, `spawn`, `channel`, `io`. The I/O is an **io_uring-shaped
  submit/completion queue** — *composed, not invented*, from parts already proven
  (`gale:kernel/msgq` for the rings, kiln for the executor, the driver seam for the
  device, `dma-own`'s `own<buffer>` — an ownership-typed buffer handle — for registered
  buffers), with the "valid until complete"
  buffer lifecycle enforced by the Component-Model type system instead of tracked at
  runtime.
- **v0.5 — isolation.** Two mutually-distrusting components in one image, each in its
  own MPU region; a faulting tenant faults instead of corrupting a sibling — hardware
  enforcement, not a trusted check. The region *arithmetic* is already proven (below);
  the on-silicon programming is blocked on [synth carrying multiple memories to distinct
  native bases](https://github.com/pulseengine/synth/issues/404).
- **v1.0 — the OS, cut.** The whole composition, signed, booting the *same* components
  on Cortex-M3 and Cortex-M4.

The invariant that makes the ladder tractable is the one from the driver row: **it
grows without growing the trusted base.** Every new capability is verified wasm over
the same two-function seam; MPU isolation is hardware, not new trusted code. The
kill-criterion is literally an `nm` atom-count check — the day a *new* native bridge
atom appears, the milestone fails.

### Isolation, honestly

The v0.5 rung is where "verified OS" has to be most careful about proven versus planned.
Today gale ships a **formally verified ARMv7-M MPU region model** (`src/mpu.rs`, proven
in Verus *and* Lean): power-of-two sizing, a 32-byte minimum, base-alignment, and — the
subtle one, from a hazard analysis finding — that `base + size` can't wrap the address
space and silently defeat isolation:

```rust
pub fn validate_region(base: u32, size: u32) -> (result: bool)
    ensures result ==> base as int + size as int <= u32::MAX as int,
{
    if size == 0 { return false; }
    let power_of_two = (size & (size - 1)) == 0;
    let min_size     = size >= MIN_REGION_SIZE;          // 32 bytes on ARMv7-M
    let aligned      = (base & (size - 1)) == 0;
    let no_overflow  = base.checked_add(size).is_some(); // UCA U-6: base+size must not wrap
    power_of_two && min_size && aligned && no_overflow
}
```

That mirrors Zephyr's `mpu_partition_is_valid()` line for line — but read it honestly:
it's a proven model of the region *arithmetic*. It does not yet *program* an MPU
register or *trap* a faulting tenant on silicon. That step — one MPU region per component
memory, reprogrammed on context switch — is the v0.5 TCB work, and it's blocked on synth
lowering multiple linear memories to distinct native bases. So: the region math is
proven; the on-silicon enforcement is designed and unbuilt, with the kill-criterion
already written down — *a crafted tenant writes outside its region without a fault.*

### Two ways to run it: dissolve, or interpret

Today there's one path, and it's the one this whole post described: **synth dissolves the
composition to native** and it boots on the metal — no compiler, no interpreter, nothing
dynamic on the device. That's the certified hot path.

A second is planned, and — this is worth getting right — it is **not** "keep the compiler
out of the certification base." The dissolve already keeps *both* the compiler and the
interpreter off the device; synth runs at build time and ships a pure native image. The
second path is about **tenants that move.** A dissolved native image can't checkpoint and
migrate a *running* instance; an interpreter can. So
[kiln](https://github.com/pulseengine/kiln) is set to grow a **`no_std` on-target
interpreter** ([kiln#415](https://github.com/pulseengine/kiln/issues/415)) that runs the
*same* verified components on the device — for the dynamically-loaded, migratable tenants
the multi-tenant North Star needs, while the hot path stays dissolved. Two poles of one
artifact, behind one WIT contract.

Interpreting on-device is exactly what makes **load-time trust** matter — and it's where
[sigil](https://github.com/pulseengine/sigil) comes in.
[scry](https://github.com/pulseengine/scry) computes the hard bounds — shadow-stack
depth, longest execution path — **host-side**, because the target can't recompute them.
Those bounds ride in kiln's `kiln.resource_limits` section; sigil signs the whole module
so the bounds are *covered* by the signature; and kiln's loader runs a **`no_std`,
offline, key-based verify as one inseparable admission step** —
[**reject-at-load**](https://github.com/pulseengine/kiln/issues/421) if the signature is
invalid, the bounds section is missing, or the signed bounds exceed the device's
RAM/stack budget ([sigil#187](https://github.com/pulseengine/sigil/issues/187)). The
payoff is unglamorous and exactly right: a fixed-RAM overrun becomes an **integration
failure on the bench, not a trap mid-mission.**

{% mermaid() %}
flowchart TB
  wasm["one verified-wasm OS<br/>meld-fused · loom-optimized"]
  synth["synth dissolves → native<br/>boots on the metal · today"]
  bounds["scry bounds, sigil-signed<br/>in kiln.resource_limits · planned"]
  gate["kiln loader verifies<br/>reject-at-load · planned"]
  kiln["kiln interprets on-target<br/>migratable tenants · planned"]

  wasm ==>|dissolve| synth
  wasm -.->|load| gate
  bounds -.-> gate
  gate -.->|admit| kiln

  classDef shipped fill:#242836,stroke:#4ade80,color:#e1e4ed;
  classDef planned fill:#161922,stroke:#8b90a0,stroke-dasharray:5 3,color:#b6bac8;
  class wasm,synth shipped
  class bounds,gate,kiln planned
{% end %}

v0.2 runs and v0.3's drivers are proven; v0.4 and up are typed requirements in
[rivet](https://github.com/pulseengine/rivet), where readiness is a query over closed
verification (`rivet release status` goes non-zero until each V closes), not a calendar.
The shape is fixed and v0.2 runs — a verified OS that dissolves to 3.5 KB on three real
chips, with a path to a multi-tenant one that never grows what you trust.

---

*Where this sits in the wider toolchain: [how it works](@/how-it-works.md).*
