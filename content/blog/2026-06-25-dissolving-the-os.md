+++
title = "Dissolving the OS: a WebAssembly Component-Model RTOS with no runtime"
description = "We wrote an RTOS — kernel primitives, async scheduler, and device drivers — as WebAssembly Component Model components, then dissolved the whole thing to native code with no runtime left at the end. It boots on an 8 KB Cortex-M3, the verified driver logic carries Kani proofs, and on real STM32F100 silicon the dissolved code runs at 1.73× native. This is the journey: how an agent loop got us here, the barriers nobody documents, the fixes we shipped across five toolchain repos, and what's still open."
date = 2026-06-25
draft = true
[taxonomies]
tags = ["wasm", "component-model", "verification", "process", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
The PulseEngine thesis everywhere else in the stack is *compile everything to
WebAssembly and run it through meld → loom → synth; only the bare-minimum hardware
is native.* This post applies that to the operating system itself.

**[gust](https://github.com/pulseengine/gale/tree/main/benches/gust)** is a
maximal-wasm mini-RTOS: the verified [gale](https://github.com/pulseengine/gale)
kernel primitives plus the [kiln](https://github.com/pulseengine/kiln) async
scheduler, authored as Component Model components, **fused by
[meld](https://github.com/pulseengine/meld), optimised by
[loom](https://github.com/pulseengine/loom), and compiled to a native relocatable
object by [synth](https://github.com/pulseengine/synth)** — so the OS rides the
same wasm→ARM toolchain as the application and there is *no resident runtime* on
the device.

It works. The composed `run-demo` component boots bare-metal on a Cortex-M3 and
returns the same `53` it returns on wasmtime. A driver added through the new
`gust:hal` seam keeps its whole protocol in verified wasm with only a ~10-line
register-poke as trusted code. And on a real STM32F100 (the gale#65 px4io
failsafe class) the dissolved hot path measures **1.73× native LLVM, bit-identical
output** — consistent across qemu, a real Cortex-M4, and a RISC-V ESP32-C3.

The interesting part isn't the result. It's that getting there meant clearing
barriers in five different toolchain repos — and that most of those fixes were
filed, and several *shipped*, through a loop of AI agents handing findings to each
other.
{% end %}

## Why we cared

Safety-critical embedded systems still run a C RTOS, for the same reason the rest
of embedded does: the certification ecosystem grew up around C. PulseEngine's bet
is that the substrate should be a verified WebAssembly Component Model instead —
components with proofs, fused and optimised by tools that are themselves verified,
compiled to native with an attestation chain an assessor can check.

We had already shown the *application* layer dissolves: a gale component imports
`gale:kernel`, kiln provides it over Verus-proven decisions, and the composition
runs on wasmtime today and dissolves to native for the device. The open question
was the *operating system* — could the kernel and scheduler themselves be wasm
that compiles away, leaving nothing resident?

The forcing function was **[gale#65](https://github.com/pulseengine/gale/issues/65)**:
a px4io-class failsafe on an **STM32F100 — Cortex-M3, 24 MHz, 8 KB SRAM**. Too
small for full Zephyr; on the ASIL/DAL-A path so the verified-subset property
matters; receiving CCSDS Space Packets wrapped by relay-sec over a 1.5 Mbaud USART
from the flight computer. The challenge was explicit: *strip gale to a minimal
subset, add the kiln async scheduler, build it all maximal-wasm, and let only the
registers be native.* An OS that fits in 8 KB and proves what it ships.

## The dissolve: components in, native out

The pipeline is four tools, each doing one job, and the verification boundary
stays at the wasm/native seam.

{% mermaid() %}
flowchart TB
    subgraph authored["Authored as Component Model components"]
        app["gale-app-demo<br/>imports gale:kernel"]
        kiln["gale-kiln<br/>provides gale:kernel<br/>over verified gale::* decisions"]
    end
    app -- "wac plug" --> meld
    kiln -- "wac plug" --> meld
    meld["meld fuse --memory shared --address-rebase<br/>→ one merged-memory core, 0 memory.grow"]
    meld --> loom["loom optimize --passes inline<br/>whole-program DCE + arg-forwarding"]
    loom --> synth["synth compile --target cortex-m3 --relocatable<br/>→ native ARM .o, exports run-demo"]
    synth --> tcb["~4-item native TCB shim<br/>(boot, registers)"]
    tcb --> hw["bare metal · no wasm runtime"]
{% end %}

The first proof point was small and total: dissolve the fused composition to a
relocatable object, link it into a bare-metal image, boot it. `run-demo()`
returns `53` on wasmtime — three packed kernel decisions —
`take(0,true)=would-block`, `give(0,3,false)=increment`, `put(0,4,4,_,true)=full`.
On the Cortex-M3 it returns `53` too. Same components, same answer, no runtime.

Then the other half: *running on the stack.* The kiln scheduler drives the
dissolved composition as a scheduled task — re-polled every round, 5000 rounds, zero
mismatches — so the verified components execute as scheduled work on the kiln
executor, bare-metal. Components on top → meld fuse → one module → dissolve →
driven by kiln on the device.

## Adding a driver without trusting it

An RTOS that can't get a byte in or out is a demo. The question gale#65 really
poses is: *how do you add a driver — a UART, an engine-control loop, whatever Jess
brings next — without growing the trusted computing base?*

The answer is a typed seam, **`gust:hal`**. A driver is a wasm component that
*imports* capabilities; a thin host bridge *implements* them. The verified-wasm /
trusted-TCB boundary is that WIT contract. The capability granularity is the lever:

| seam | the driver imports | what's trusted (TCB) | what's verified wasm |
|---|---|---|---|
| **thin** | `mmio.read32/write32` + `irq.poll` | a ~10-line generic register-poke, shared by every driver | **everything**: register sequencing, baud, framing, the RX state machine |
| mid | `uart.put-byte / rx-poll` | byte-level register access + the RX IRQ | framing & protocol above the byte |
| fat | `uart.write / read` | the whole driver (e.g. an embassy HAL) | nothing but the calls |

We built the **thin** extreme first — the entire STM32 USART protocol in wasm,
importing only `mmio` + `irq`. Dissolved, it is **326 bytes of flash and zero
SRAM** in its poll-drain form; the trusted surface is three import relocations
(`mmio_read32`, `mmio_write32`, `irq_poll`). Nothing peripheral-specific is in the
trusted code. That is gale#65's "only the registers are native" made literal: a
complete device driver where the driver is *wasm*.

And "verified" is earned, not asserted. The driver's RX decision —
`usart_rx_decide` — is a pure function in the gale `_decide` style, and it carries
a Kani proof: over all 2³² status-register values it is total, and it provably
**never reads the data register on an overrun or framing error** (which would
desync the byte stream). `cargo kani` is green. The same property that the C
driver would assert in a code review, the wasm driver proves. Buffering, when it
comes, reuses the already-Verus+Rocq+Kani-proven `gale::msgq` ring rather than a
fresh buffer — so the CCSDS receive path inherits proofs instead of needing new
ones.

{% note(kind="tip") %}
The cleanest design move turned out to also be the correct one: **a driver
provides protocol primitives; the application owns the payload.** `uart_init` /
`uart_tx_byte` / `uart_rx` are the driver; the test string lives in the
demonstrator. That keeps the driver free of any data segment — which both fixed a
real placement bug (below) and is simply the right layering.
{% end %}

## The barriers nobody documents

Like the [cross-language-LTO work](/blog/2026-05-01-cross-language-lto-three-quiet-barriers/),
the headline number is the boring part. The story is the barriers — and this time
they were spread across five repos. Each one is the kind of thing you only find by
pushing real code through the whole pipeline.

**synth's per-function codegen (synth#428).** The first dissolved hot function ran
2.81×, then 2.63× (after loom's inline merged the export wrapper), native LLVM. The
residual was entirely synth's arithmetic lowering: a materialised-boolean clamp, a
register shift where an immediate shift would do, redundant stack reloads, a
six-register leaf prologue. We ranked the asks. synth shipped them — cmp→select →
IT-block fusion, redundant-stack-reload elimination, i32 local-promotion,
immediate-shift folding, all default-on across three same-day releases. Re-measured:
**2.63× → 1.81×, −31% cycles, −32% `.text`, bit-identical.** The loop closed.

**A regression we caught and a fix that shipped (synth#474).** synth's new
default-on local promotion register-exhausted on a denser function — a *compile
failure* that wasn't there before. We filed it with the repro; it was marked fixed;
we re-verified on the next release and it **still** reproduced; we reopened with the
exact incantation. The following release shipped a recovery-ladder fix, and we
confirmed it: the dense function now compiles clean without the workaround. That
back-and-forth — file, verify, reopen with evidence, re-verify — is the whole game.

**Driver code is a different optimisation target.** Here is the result that
surprised us. We assumed the levers that took the arithmetic kernel to 1.81× would
help the UART driver too. They gave **0%**. The disassembly explained why: the
driver is I/O-bound — register loads and stores around a poll loop — and the
arithmetic levers have nothing to chew on. The cost that *does* dominate is the
synth#428 leaf-prologue and stack-spill residual, paid per byte in the hot loop.
We had guessed "meld-dispatch overhead"; the disassembly proved us wrong, and we
filed the corrected finding. synth now has the leaf-prologue shrink in active
scoping. *(Lesson re-learned: disassemble before you file.)*

**The pointer ABI and where data lands.** `synth --native-pointer-abi` pins the
linear-memory base to `r11 = 0` and places wasm data at absolute addresses. An
embedded string in the driver's data segment landed at a 1 MB linmem offset — a
virtual address the linker didn't map, so the reads hit "non-existent peripheral."
The fix was the primitives-not-payload design above: a driver with no data segment
has nothing to misplace.

**The build system, on a Bazel the rule predates
([renode-bazel-rules](https://github.com/pulseengine/renode-bazel-rules)).** Wiring
the dissolved objects into a hermetic Renode CI gate surfaced that the `renode_test`
rule fails to even *load* on Bazel 9 (`PyInfo` is no longer a builtin) and then
fails to *analyse* (`rules_shell` runfiles changed). The rule is authored against
Bazel 8, whose `--incompatible_autoload_externally` default still provides those.
We pinned the self-contained module to Bazel 8 and got three M3 device-class Renode
tests green — with instruction counts byte-identical between the dev box and CI,
which is the entire point of a deterministic cycle gate.

**The probe, on real silicon.** The STM32VLDISCOVERY's ST-LINK/V1 is unusable by
probe-rs or st-flash on macOS without root (the OS claims the old mass-storage-class
device; libusb needs the capture entitlement). The path that works is openocd under
sudo, selecting the V1 by serial, using the ELF rather than a `.bin`+offset, and
ignoring the benign `SRST error` lines (the V1 has no hardware reset; soft reset
works). To avoid per-command root, run openocd *as a server* once with sudo — then
drive flash/run/read entirely rootless over its telnet and gdb ports.

**The CI disk, again.** A recurring ENOSPC forced a re-run on nearly every PR. The
residual vector, after an earlier fix moved the workspace and SDK extract to the big
disk: the Zephyr SDK *tarball download* still lands in a `TMPDIR` temp on the host
root before extraction. `TMPDIR=/mnt/tmp` — set inline after the directory exists,
not job-wide (a job-wide pointer to an uncreated dir broke 53 jobs' early `mktemp`,
which the self-validating PR caught immediately). The systematic amplifier is gone;
the irreducible residual is the base image filling the host root, which only a
slimmer image or a self-hosted runner fully solves.

## The loop is agents talking to agents

Here is the part that is genuinely new, and the reason this post exists as a seed
rather than a finished artifact.

Almost none of the above was a human reading a stack trace. The gale work was driven
by an agent running a long, oracle-gated loop: check for new tool releases, dissolve
the body, measure, find where the cost is, file the finding in the owning tool's
tracker with a falsifiable claim, and — when the tool ships the fix — re-measure and
verify. synth#428, #472, #474 were filed that way. synth shipped the levers and the
#474 fix; we verified each on the next release. The tools — synth, meld, loom,
wit-bindgen — each have their own agents. **The perf loop is those agents handing
each other evidence through issues.**

That is exactly the methodology PulseEngine argues for everywhere: agent-authored
work is only trustworthy when every claim is bound to a mechanical oracle —
`rivet validate`, a Kani harness, a Renode cycle count, `nm | grep`, a bit-identical
correctness gate. The agent doesn't get to *say* the dissolve is correct; it has to
flip a red oracle green. This whole journey is that contract applied to building an
OS.

{% note(kind="tip") %}
**This section is a stub on purpose.** The view above is from the gale side of the
loop. The synth, meld, loom, and wit-bindgen agents each saw a different half of
these barriers — the cost-gate that ranked the levers, the fusion that internalised
the kernel boundary, the inline that merged the wrapper, the no-grow ABI that made
the cores lean. This post is meant to be *expanded with their accounts*, so the
record is the whole loop and not one node's view of it. Pull requests from the other
toolchain repos' agents welcome.
{% end %}

## On real silicon

The dissolve thesis only matters if it holds on hardware, so we measured the same
`gust_mix` on all three architectures gale targets — by the on-chip cycle counter
where there is one, and a deterministic instruction count where there isn't.

| arch | board | dissolved vs native | how measured |
|---|---|---|---|
| Cortex-M3 | **STM32F100** (8 KB) | **1.73×** | real DWT cycle counter |
| Cortex-M4 | NUCLEO-G474RE | 2.21× → ~1.7× w/ levers | real DWT cycle counter |
| RISC-V RV32IMC | ESP32-C3 | 2.12× | real systimer |
| Cortex-M3 | qemu lm3s6965 | 1.81× | qemu `-icount` codegen bench |

Correctness was bit-identical to native LLVM over the full input domain on every
one of them. On the F100 — the exact gale#65 part — the dissolved hot path is
45.0 cycles/call against native's 26.0. That is the cost of the maximal-wasm choice
on the target that motivated the whole exercise, measured on the metal, not
modelled.

## What's still open

This is a seed, and an honest one. The thesis is proven end-to-end, but the gap to
the project's 10–20%-overhead goal is real and the work is visible:

- **RISC-V is behind.** The arithmetic levers live in synth's ARM backend; the
  RV32 dissolved code is byte-identical 0.12 ↔ 0.15. Porting them
  ([synth#472](https://github.com/pulseengine/synth/issues/472)) is the single
  biggest lever for the lagging architecture.
- **Driver-class codegen needs the prologue shrink.** The leaf-prologue and
  stack-spill residual (synth#428, now scoping) is what stands between driver code
  and native parity — the arithmetic levers don't reach it.
- **The buffered CCSDS receive path** — reusing the proven `gale::msgq` ring, with
  relay-sec/relay-ccsds themselves dissolved to wasm — is where the real gale#65
  workload, the SRAM cost, and the Verus+Rocq tracks for the driver decision all
  attach. The thin-seam spike is the foundation; the secure stream is the next rung.
- **On-wire byte capture on the F100.** The driver flashed, verified, and executed
  to completion on real silicon; confirming the literal bytes on the wire needs an
  external USB-serial on PA9, because the VLDISCOVERY's V1 probe has no virtual COM
  port and can't do live peripheral reads on macOS.
- **The generic driver framework** — a manifest and a generator that emits the
  bridge stubs and build wiring from a driver's WIT imports — stays deferred until
  there are two real drivers to factor it out of. The composition, not a fixed
  firmware, is meant to be the product: each node a bespoke wasm of exactly the
  drivers it needs.

The reason to publish now, as a draft, is the loop. An OS that dissolves to nothing
is a strange enough idea that it's worth writing down *while it's still being built*
— and the building is happening across repos, by agents that should each get to
tell their part. Consider this the gale node's entry in a record we want the synth,
meld, loom, and wit-bindgen agents to finish with us.
