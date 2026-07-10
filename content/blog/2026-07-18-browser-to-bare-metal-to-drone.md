+++
title = "From a browser tab to a real drone"
description = "The same verified components run four ways: live in a browser tab, fused as one WebAssembly module, transcoded to native ARM, and — the arc we're on now — onto a drone's flight controller. Portability isn't the headline. The point is that the verification done once travels with the artifact across every substrate."
date = 2026-07-18
draft = true
[taxonomies]
tags = ["wasm", "embedded", "verification"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
One set of verified components; four places it runs. A **browser tab**, a **fused
wasm module**, **native ARM**, and — the arc we're climbing now — a **drone's
flight controller**. The interesting part isn't portability for its own sake. It's
that the verification you did once rides along with the artifact, unchanged, from
the tab to the metal.
{% end %}

Most software is written for one substrate and stuck there. A kernel primitive is
kernel code; a browser demo is browser code; flight software is flight software. The
Component Model lets us treat all of those as the *same artifact* pointed at
different backends — and if that artifact is verified, the verification comes with
it.

Here's the same journey, four stops.

## 1 · A browser tab

[gale](https://github.com/pulseengine/gale) provides formally-verified Zephyr RTOS
kernel primitives in Rust (Verus + Rocq). The verified components
[run live in a browser](https://pulseengine.github.io/gale/) — the exact same
`gale::*` decisions the proofs are about, executing in a tab. It's the most
approachable way to meet a verified RTOS: no board, no flash, just a URL.

## 2 · One fused module

The build tail fuses and shrinks the composition: **meld** fuses multiple
components into a single WebAssembly module, and **loom** optimizes the fused whole
(translation-validated — the optimization is checked, not trusted). We wrote about
taking this to its conclusion in [Dissolving the
OS](@/blog/2026-07-08-dissolving-the-os.md): fuse the app and the kernel into one
merged-memory core with no runtime `memory.grow` between them.

## 3 · Native ARM, bare metal

[synth](https://github.com/pulseengine/synth) transcodes the fused wasm to native
ARM Cortex-M through program synthesis; the same components dissolve to a bare-metal
**Cortex-M3** behind a tiny native shim — no wasm runtime left at the bottom. The
[relay](https://github.com/pulseengine/relay) flight stack — falcon's control
cascade (an Invariant-EKF estimator, geometric SE(3) attitude control, an ADRC inner
loop) — flies in Gazebo SITL and runs bare-metal on an emulated Cortex-M, exercised
through a hermetic Bazel firmware chain and Renode emulation.

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

A demo that only runs in a browser proves it runs in a browser. A proof that only
applies to a hand-written model proves something about the model. The reason to make
one artifact travel all four substrates is that the *verification travels with it*:
the properties gale's proofs establish, and the coverage witness measures on the
shipped wasm, are about the same bytes that get fused, transcoded, and — when the
tether comes off — flown.

That last step isn't finished, and we won't pretend it is. But the path is one
artifact wide the whole way down, which is the point: you verify once, and you don't
re-verify at every substrate boundary because there's nothing new to verify — it's
the same thing, moved.

---

*See [how it all fits together](@/how-it-works.md) for the full pipeline ·
[gale demo](https://pulseengine.github.io/gale/) ·
[relay](https://github.com/pulseengine/relay) ·
[jess](https://github.com/pulseengine/jess).*
