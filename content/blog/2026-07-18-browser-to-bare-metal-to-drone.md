+++
title = "From a browser tab to a real drone"
description = "The same component set runs four ways: live in a browser tab, fused as one WebAssembly module, transcoded toward native ARM, and — the arc we're on now — onto a drone's flight controller. Portability isn't the headline. The honest one is what each boundary between them does, and doesn't yet, verify."
date = 2026-07-18
draft = true
[taxonomies]
tags = ["wasm", "embedded", "verification", "how-it-works"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
One component set; four places it runs — a **browser tab**, a **fused wasm
module**, **native ARM**, and, the arc we're climbing now, a **drone's flight
controller**. The interesting part isn't portability for its own sake. It's being
honest about the *boundaries*: which crossing is backed by a proof, which by
differential testing, and which is still ahead of us.
{% end %}

Most software is written for one substrate and stuck there. A kernel primitive is
kernel code; a browser demo is browser code; flight software is flight software. The
Component Model lets us treat all of those as the *same artifact* pointed at
different backends. What *doesn't* come for free is the verification: each boundary
the artifact crosses has its own honest status, and this post is mostly about naming
them.

Here's the same journey, four stops.

## 1 · A browser tab

[gale](https://github.com/pulseengine/gale) is reaching for **gust** — a
multi-tenant verified OS built from verified parts — and it got there from verified
**Zephyr** kernel primitives, which it still provides (sem, mutex, msgq, timers). The
proofs run across three provers (Verus, Rocq, Lean), and it's honest work-in-progress:
some primitives are proven, others — including parts of the scheduler — are still
admitted stubs, and gale's README keeps a running ledger of exactly which is which.
The components
[run live in a browser](https://pulseengine.github.io/gale/) — the same `gale::*`
decisions the proofs are about, executing in a tab. It's the most approachable way
to meet the RTOS: no board, no flash, just a URL.

## 2 · One fused module

The build tail fuses and shrinks the composition: **meld** fuses multiple
components into a single WebAssembly module, and **loom** optimizes the fused whole
(translation-validated — the optimization is checked, not trusted). We wrote about
taking this to its conclusion in [Dissolving the
OS](@/blog/2026-07-08-dissolving-the-os.md): fuse the app and the kernel into one
merged-memory core with no runtime `memory.grow` between them.

## 3 · Native ARM, bare metal

[synth](https://github.com/pulseengine/synth) transcodes wasm toward native ARM
Cortex-M and RISC-V. synth targets Cortex-M4 today and doesn't yet lower
floating-point or meld-fused multi-memory components. And this is the stop that
reached **real silicon**: gale's `gust` composition — app + kiln-async scheduler +
dissolved primitives — runs on a physical **Nucleo G474RE (Cortex-M4)**, flashed via
probe-rs, correctness-matched to wasmtime, with no wasm runtime left at the bottom.
gale's integer kernel also dissolves to an *emulated* Cortex-M3 (the *dissolving the
OS* demo above; the M3 board is pending). Separately, the
[relay](https://github.com/pulseengine/relay) flight stack — falcon's control cascade
(an Invariant-EKF estimator, geometric SE(3) attitude control, an ADRC inner loop) —
still flies only in Gazebo SITL and on an **emulated** Cortex-M7. So: gale/gust has
reached real M4 silicon; the *flight* stack has not.

## 4 · Onto the drone — the tether is still on

[jess](https://github.com/pulseengine/jess) is where the software meets hardware.
Its name is deliberate: *a jess is the falconry tether that holds the bird during
training before free flight.* That's exactly the honest status — jess is the
hardware-integration and release-watch hub, and real flight is the arc it's on, not
a thing already done.

The Phase-2 target is a distributed flight controller on a Pixhawk 6X-RT: an NXP
i.MX RT1176 running the falcon cascade on its Cortex-M7 and the IEKF estimator on
its Cortex-M4 (each a fused wasm component, talking over shared memory with
CCSDS + relay-sec framing), an STM32F100 I/O MCU for failsafe and PWM mixing, and
DroneCAN / MAVLink out to ESCs, GPS, and a ground station. jess itself is
**evidence-as-code**: the substance lives in [rivet](https://github.com/pulseengine/rivet)
artifacts and a [spar](https://github.com/pulseengine/spar) AADL hardware model,
exercised by that Bazel chain — so the road from sim to HIL to drone is tracked, not
improvised.

## Why the four stops matter

A demo that only runs in a browser proves it runs in a browser. A proof over a
hand-written model proves something about the model. Making one artifact travel all
four substrates is worth it *not* because verification comes free across them — it
doesn't — but because it lets us name each boundary honestly:

- **wasm → fused wasm** (meld + loom): loom checks each optimization per run
  (translation-validated) and reverts on a counterexample.
- **wasm → native ARM** (synth): this crossing is *differentially tested* against a
  reference wasm semantics — **not** proven equivalent. gale's own
  verification-honesty ledger insists on exactly this distinction, and so do we.
  It's the boundary where there is still something to verify.
- **native → real silicon:** gale's `gust` already boots on a physical Cortex-M4
  (Nucleo G474RE), correctness-matched to wasmtime. Reached.
- **silicon → a flying drone** (jess): this is what's still ahead — getting the
  *flight* stack onto real hardware. The tether is on.

witness measures MC/DC on the *wasm* that ships; it does not instrument the native
ARM synth emits, so even the coverage claim stops at the wasm boundary. One artifact
the whole way down means one thing to point at each step — and an honest label on
every crossing, including the ones that aren't proofs yet.

---

*See [how it all fits together](@/how-it-works.md) for the full pipeline ·
[gale demo](https://pulseengine.github.io/gale/) ·
[relay](https://github.com/pulseengine/relay) ·
[jess](https://github.com/pulseengine/jess).*
