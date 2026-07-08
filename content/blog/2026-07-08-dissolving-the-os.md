+++
title = "Dissolving the OS: a WebAssembly Component-Model kernel with no runtime"
description = "We wrote OS kernel primitives, a cooperative async scheduler, and a device driver as WebAssembly Component Model components, then dissolved the whole thing to native code with no runtime left at the end. It boots on a Cortex-M3, the verified driver logic carries Kani proofs, and on real STM32F100 silicon the dissolved hot path runs at 1.73× native (a 73% slowdown — the honest cost of the maximal-wasm choice). This is the journey: how a loop of AI agents got us here, the barriers nobody documents, the fixes we filed and watched ship across five tool repos, what a proof-carrying lowering could reach — and what's still open."
date = 2026-07-08
draft = false
[taxonomies]
tags = ["wasm", "component-model", "verification", "process", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
The PulseEngine thesis everywhere else in the stack is *compile everything to
WebAssembly and run it through meld → loom → synth; only the bare-minimum hardware
is native.* This post applies that to the operating system itself.

**[gust](https://github.com/pulseengine/gale/tree/main/benches/gust)** is a
maximal-wasm mini-kernel: the verified [gale](https://github.com/pulseengine/gale)
kernel primitives plus the [kiln](https://github.com/pulseengine/kiln) *cooperative*
async scheduler (no preemption, priorities, or WCET bound yet — those are open;
see *What's still open*), authored as Component Model components, **fused by
[meld](https://github.com/pulseengine/meld), optimised by
[loom](https://github.com/pulseengine/loom), and compiled to a native relocatable
object by [synth](https://github.com/pulseengine/synth)** — so the OS rides the
same wasm→ARM toolchain as the application and there is *no resident runtime* on
the device.

It works. The composed `run-demo` component boots bare-metal on a Cortex-M3 and
returns the same `53` it returns on wasmtime. A driver added through the new
`gust:hal` seam keeps its whole protocol in verified wasm with only a ~10-line
register-poke as trusted code. And on a real STM32F100 (the gale#65 px4io
failsafe class) the dissolved hot path measures **1.73× native LLVM** with
**bit-identical output** — the *output* matches across qemu, a real Cortex-M4, and a
RISC-V ESP32-C3; the *overhead* itself ranges 1.73×–2.21× by target (table below).
(Convention throughout: native LLVM = 1.00×, lower is closer to native — so 1.73× is
a 73% slowdown, the honest cost of the maximal-wasm choice against the project's
10–20% goal.)

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
poses is: *how do you add a driver — a UART, an engine-control loop, whatever jess
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

**A green light that meant nothing (rivet).** This one is a barrier of a different
kind — not a tool that failed, a tool that *passed too easily*. We had asked rivet
for a first-class way to scope a release and query its readiness; the rivet agent
shipped it (a `release: vX.Y` field and a `rivet release status` gate that exits
non-zero when the release isn't cuttable). We pointed it at gale's first release —
the semaphore primitive — and it reported **✓ cuttable**. It should not have. The
requirements were `approved`, not verified; we *knew* the verification links were
incomplete. A gate that greens a release you know isn't ready is worse than no gate.

Chasing it produced a small trilogy of our own. First we assumed the gate was wrong
and tried to "fix" it by wiring the unit and integration test artifacts directly to
the requirements — and rivet's schema *rejected that*, correctly: in an ASPICE
V-model a unit test verifies a design element, an integration test verifies an
architecture component, and only a formal/analysis verification may verify a
requirement directly. The schema was right; our fix was wrong. Then, tracing the V
properly, we found the gate wasn't lying either: the semaphore's requirements *were*
verified — formally, by the Verus/Rocq/Kani proofs, which is the correct primary
evidence for an invariant like "count never exceeds limit." The real bug was a third
thing: a coverage *rule* that advertised unit and integration verifications as
acceptable direct verifiers of a requirement — which the link schema forbids — so it
emitted a permanent, un-actionable "missing verification" warning on every
requirement in the project. One-line fix to the rule; the false warning vanished; the
release is now, honestly, cuttable.

The lesson is the one the whole stack is built on and still easy to forget: **a
green oracle is only as trustworthy as the thing it actually measures.** We very
nearly "fixed" the tool, then very nearly trusted the green — and the discipline that
saved us both times was refusing to believe either the pass or the fail until we
could point at the mechanism. That is oracle-gating turned on itself.

## The loop is agents talking to agents

Here is the part that is genuinely new, and the reason this post exists as a seed
rather than a finished artifact.

Little of the *perf grind* above was a human reading a stack trace — though humans
ranked the asks, authored the architecture and the proofs, and authorised every
release. The gale work was driven by an agent running a long, oracle-gated loop:
check for new tool releases, dissolve the body, measure, find where the cost is, file
the finding in the owning tool's tracker with a falsifiable claim, and — when the
tool ships the fix — re-measure and verify. synth#428, #472, #474 were filed that way. synth shipped the levers and the
#474 fix; we verified each on the next release. The tools — synth, meld, loom,
wit-bindgen — each have their own agents. **The perf loop is those agents handing
each other evidence through issues.**

That is exactly the methodology PulseEngine argues for everywhere: agent-authored
work is only trustworthy when every claim is bound to a mechanical oracle —
`rivet validate`, a Kani harness, a Renode cycle count, `nm | grep`, a bit-identical
correctness gate. The agent doesn't get to *say* the dissolve is correct; it has to
flip a red oracle green. This whole journey is that contract applied to building an
OS.

### A trilogy of error, told from three trackers

The clearest way to describe how the tool agents work is the old *Simpsons*
"Trilogy of Error" episode: one day, three characters, three storylines that each
look complete on their own but only make sense once you see where they intersect.
Our version has more than three threads — synth on codegen, loom and meld on
composition, rivet on traceability, wit-bindgen on the bindings — and each runs its
own agent, its own tracker, its own release cadence. gale is the consumer that sees
all of them collide in one place: the dissolve pipeline and the moment a byte comes
back wrong.

The intersections are the interesting part, because none of the agents can see them
alone. The synth agent optimising a leaf prologue cannot know that gale's *driver*
code is dominated by exactly that residual and its *arithmetic* code isn't — only
the consumer, disassembling both, knows which lever matters where. The loom agent
inlining an export wrapper cannot know that doing so is what let synth's next lever
find the clamp to fuse. The rivet agent shipping a configurable release gate cannot
know that gale's coverage rule was quietly mis-modelled so the gate would green on
the wrong evidence. Each finding is a message from the one node that could see the
collision, filed into the tracker of the node that can fix it.

Watching one lever travel that loop, release by release, is the whole thesis in
miniature. We filed the driver-class prologue/spill residual as a ranked ask. It
came back first as an opt-in *spike* (`SYNTH_SPILL_REALLOC`, flag-off) — we measured
it: −20 bytes on the scheduler hot path, exactly where the disassembly said the cost
lived. The next release matured it with a Belady spill-plan re-choice — we
re-measured: −24 bytes. The release after that flipped it **default-on** — "the
allocator release" — and we re-measured the shipped default: **−26 bytes on
`gust_poll`, no flag, bit-identical output.** Four synth releases, one lever, each
step measured on the same body on the same qemu cycle counter. The agent never *said*
the lever helped; it flipped a byte count and posted the number.

{% note(kind="tip") %}
That is what "agents talking to agents" actually buys you, and why it is not just
distributed bug-filing: the loop *converges*. A human maintainer would have taken the
prologue ask, guessed at scope, and shipped once. The loop shipped a spike, got a
real number back from a real consumer, matured it, got a better number, and only then
made it default — with a regression gate (`gust_codegen_bench` stays 1.81×,
correctness identical) standing the whole time. The consumer's measurement is the
tool's acceptance test.
{% end %}

This still isn't the whole record — the synth, meld, loom, wit-bindgen, and rivet
agents each saw a different half of every collision, and their accounts belong here
too. But it is no longer a stub. It is the loop, caught in the act, from the one seat
that watches all the threads meet.

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
modelled. To be precise about what "on silicon" means here: these are **halt-and-read
cycle counts of the hot path** (DWT CYCCNT on the ARM parts, systimer on RISC-V), not
an end-to-end run — confirming the driver's literal bytes on the wire is still open
(*What's still open*, below).

## The floor below native

Everything above is a story about *catching up* to native LLVM — closing a 2.81×
gap to 1.81× and, lever by lever, toward parity. Parity is a fine goal. It is also
the wrong ceiling.

Here is the claim the whole verified-substrate bet ultimately points at: **verified
code *could* be faster than the native build, precisely because it is verified** —
not as rhetoric, but as a number we can already hand-lower and measure, even though
the pipeline cannot emit it yet.

The mechanism is that the proof is an optimisation input the native compiler never
had. Take gale's failsafe mixer: `clamp(1500 + (ch − 1024), 1000, 2000)`. LLVM
compiles the clamp because it must — it cannot know the caller's range. But in a
*composed* system, the caller often can prove it. When a composition establishes
that the channel value stays in `[524, 1524]` — a range gale's primitives already
carry as a Verus/Rocq/Kani invariant — then `1500 + (ch − 1024)` is provably already
inside `[1000, 2000]`, **both clamp branches are dead**, and the whole function
collapses to a single `add` — one LLVM won't emit here, because it never had the
bound. (LLVM elides clamps all the time when the range is locally visible; the point
is that this range lives across a component boundary it can't see.)

We built a bench for exactly this — three lowerings of the same mixer, timed over
the same proven-range inputs on the same cycle counter, with a soundness gate that
refuses to run unless the specialised form is bit-identical to the full clamp over
the proven range:

| lowering | cycles/call | vs native |
|---|---|---|
| native (LLVM, full clamp) | 0.50 | 1.00× |
| dissolved today (synth) | 0.83 | 1.65× |
| **proof-carrying floor** (`add`, clamp elided — *hand-lowered, not yet pipeline-emitted*) | **0.23** | **0.45×** |

{% insight() %}
**0.45× native — a hand-lowered lower bound, not a pipeline output.** synth cannot
emit this yet ([synth#494](https://github.com/pulseengine/synth/issues/494) +
[loom#240](https://github.com/pulseengine/loom/issues/240) are open); this is the
`add` an ideal proof-carrying lowering *would* produce — hand-written, and
soundness-gated to be bit-identical to the full clamp over the proven range, on the
same qemu `-icount` bench as every other number here. It runs at less than half the
cost of the native build.

The reason LLVM doesn't reach it isn't incapacity — LLVM elides clamps routinely when
the bound is locally visible. It's *information*: the range that kills the clamp
crosses a component boundary an external verifier supplies, which a standalone
compiler never sees. A stack that owns the whole chain — Verus proof → wasm → loom →
synth — can flow that proof in as an IR premise. That is the leapfrog thesis, and it
is still ahead of us, not shipped.
{% end %}

The honest caveat is the whole reason this is a "floor" and not a shipped result:
the number is what synth *could* emit with the proof in hand, and synth does not yet
consume proofs as premises. That is the one lever, of all the ones in this post,
still entirely ahead of us — [synth#494](https://github.com/pulseengine/synth/issues/494)
(proof-carrying specialisation) paired with
[loom#240](https://github.com/pulseengine/loom/issues/240) (carry the Verus range
through the fuse as an IR premise). The spill lever and the arithmetic levers took us
from 2.81× to 1.81× — real parity progress. The floor at 0.45× is the leapfrog, and
the day it ships, the same loop that adopted the spill lever will adopt it, and this
table's middle row will move toward its bottom row on real silicon.

## DMA, as an ownership handoff you can prove

The thin-seam UART showed a driver can be verified wasm with a three-register
trusted surface. DMA is the case that looks like it *can't* — because DMA is the one
place where an agent outside the sandbox writes into memory the wasm engine believes
is private. Model it naively and you either drag the buffer out into trusted native
code, or you silently break synth's assumption that linear memory is the module's
alone.

The Component Model already has the discipline this needs: **`own<T>`**. An owned
handle can be *moved*, and the type system proves the previous holder can no longer
touch it. So we model a DMA transfer as an ownership round-trip — the wasm component
holds `own<buffer>`, *transfers* it to the DMA engine, and gets it back on the
completion interrupt as a `future<own<buffer>>` the kiln scheduler awaits. Because
meld has already fused the component memories into one shared region, the handle
carries only the *permission*, not the bytes: zero-copy DMA with statically-checked
exclusive ownership. The wasm side is *provably* hands-off for the exact window the
engine is writing.

The part that decides *who may touch the buffer* — the ownership state machine, the
barrier pairing, the streaming ring for circular transfers — is verified wasm,
dissolved to **218 bytes** of native with a three-atom trusted surface (program the
descriptor, emit the cache barrier, poll the IRQ). Six Kani proofs hold it up: access
is possible **iff** the buffer is wasm-owned; the cache/invalidate barrier is emitted
*by construction* at every handoff, so it is structurally impossible to forget; an
aborted transfer never leaves the buffer ownerless; and in the streaming case each
chunk is owned by exactly one side at a time.

This is also the first place the DMA-region marking bites: synth grew a
`--volatile-segment` flag ([synth#543](https://github.com/pulseengine/synth/issues/543),
now real) that tells codegen *this range is externally mutable during the transfer
window* — so the ownership handle is not only a safety mechanism, it is the signal
that lets the compiler stay aggressive everywhere except the handoff. It is, at the
same time, the embedded instance of a
[Bytecode Alliance shared-memory proposal](https://github.com/cpetig/wasm-shm-test/blob/main/DESIGN.md)
for the Component Model — where "the host may answer zero to the allocation request
and use a fixed valid address, because an embedded CPU has only an MPU, not an MMU"
is precisely gale's world. The general form is being designed upstream; the verified
embedded reference implementation is running here.

## What's still open

This is a seed, and an honest one. The thesis is proven end-to-end, but the gap to
the project's 10–20%-overhead goal is real and the work is visible:

- **The proof-carrying floor is the one lever still entirely ahead.** Parity is in
  reach; *beating* native is the open frontier — synth#494 + loom#240, the 0.45×
  measured above. Everything else in this list is engineering; that one is the thesis.
- **RISC-V caught up between drafts.** When the first draft went up, the RV32
  dissolved code was byte-identical release over release because the levers lived only
  in the ARM backend. Then [synth#472](https://github.com/pulseengine/synth/issues/472)
  **closed** — four arithmetic levers ported to RV32 (cmp→select, immediate-shift-fold,
  i32 local-promotion, const-address-fold). We re-measured on the ESP32-C3 lane: with
  the levers enabled, `gust_mix` shrinks **132 → 116 bytes (−12%)**, all of it from
  cmp→select and shift-fold (the other two don't apply to this function, and we didn't
  invent a win for them). They ship flag-off for now, so the 2.12× silicon number above
  is unchanged until they default-on — but the lagging architecture is no longer
  standing still. (This is the loop's own tail: our published number goes stale the
  moment the tool ships, which is a good problem, and the same loop that measured the
  ARM levers just measured these.)
- **Driver-class codegen — the residual shipped.** When we filed the leaf-prologue
  and stack-spill residual (synth#428) it was the thing standing between driver code
  and parity. It is no longer open: synth's verified allocator work (the epic behind
  the spill lever) matured through a spike and Belady spill-planning to **default-on**,
  and gale adopted it — the scheduler hot path lost 26 bytes with no flag. What remains
  is the arithmetic side of driver code, and the floor above.
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
