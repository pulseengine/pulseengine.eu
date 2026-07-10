+++
title = "Where the seams still show"
description = "\"Works together\" is not a yes-or-no. A toolchain is a set of connections, each at some level of maturity, and the honest thing is to map them — wired-in-CI, demonstrated-once, still-manual — rather than let the clean diagram imply they're all the same. Here is that map for PulseEngine, seams included."
date = 2026-07-16
draft = true
[taxonomies]
tags = ["verification", "process", "traceability", "how-it-works"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
A pipeline diagram draws every connection the same weight. Reality doesn't work
that way: some seams are gated in CI on every commit, some have been demonstrated
once, some are still stitched by hand. We'd rather map our own seams than have
someone find them — so here's the honest version of *how it all fits together*,
with the maturity written on each joint.
{% end %}

We publish a clean [how-it-works](@/how-it-works.md) page, and it's true — but a
diagram flattens something important. Every arrow on it looks equally solid. In a
real, work-in-progress toolchain, they aren't. So this is the companion the
reference page can't be: the same chain, annotated by **how load-bearing each
connection actually is** today.

Three honest states:

{% note(kind="tip") %}
**Wired** — gated in CI; a break fails the build. **Demonstrated** — shown to work
end-to-end at least once, not yet a standing gate. **Manual** — real, but a human
still carries the artifact across the seam.
{% end %}

## The chain, joint by joint

**spar → rivet artifacts.** *Demonstrated.* spar generates typed artifacts and
interfaces from an architecture model; the shapes line up, and it's been exercised,
but the generate-and-ingest loop isn't yet a per-commit gate on every project.

**rivet across the V.** *Wired.* This is the most exercised seam we have.
`rivet validate` runs in CI; a broken requirement → architecture → design → code →
test link fails the build. It's the connection we trust most because it's the one
the machine checks most often.

**component code → meld → loom → synth.** *Mixed.* meld (fuse) and loom (optimize)
are the more travelled part of the build tail, and loom is **translation-validated**
— each optimization is checked rather than trusted, with Z3 where the function is in
scope (straight-line integer/bitvector code) and a structural + differential backstop
for the rest, not SMT everywhere. synth (wasm → native ARM/RISC-V) is earlier — no
float or fused multi-memory yet; treat native transcode as demonstrated, not routine.

**the Verify gate.** *Wired, with an honest asterisk.* Verus, Rocq, Lean, scry,
witness, and ordeal run in CI. The asterisk: several deductive proofs verify a
**hand-transcribed model** of the code, not the shipped code itself — gale's Rocq
proofs, for instance, run over abstract models, and some of its modules (parts of
the scheduler) are still admitted stubs. Where that's true, the model ↔ code link is
a *trusted-base item* — and we name it as one rather than let the green check imply
more. (scry's soundness is likewise machine-checked over its integer model, with the
proof against canonical Wasm semantics still to come.) witness is the leg that
resists this: it measures MC/DC on the **compiled wasm that actually ships**, so it
can't drift from the *bytecode* — though its source-level mapping still rests on a
stated DWARF-correctness assumption. (We wrote about a concrete limit of the proof
side [here](@/blog/2026-07-09-honest-failure-by-construction.md).)

**sigil attest.** *Demonstrated.* Embedded signing, Sigstore keyless, and SLSA
provenance work; binding them as a mandatory release gate across every repo is not
uniform yet.

**kiln / gale run.** *Mixed.* gale carries machine-checked proofs across three
provers (Verus, Rocq, Lean) — some primitives proven, others still admitted stubs —
and the same components run in a browser and dissolve to a bare-metal (emulated)
Cortex-M3, which is demonstrated and genuinely fun to watch. kiln, the interpreter
and runtime, is earlier — a std interpreter today, not yet running on-target.

**relay / wohl / jess.** *Demonstrated → in progress.* relay's falcon flight stack
flies in Gazebo SITL and runs on an emulated Cortex-M7; its SE(3) attitude loop is
Lean-proven while the estimator is property-tested (proof next). jess — the
hardware-integration hub — is, by its own name, *the falconry tether that holds the
bird during training before free flight.* Real hardware (HIL → drone → flight) is
the Phase-2 arc, not a shipped fact.

## The principle under the map

Two rules keep this honest rather than aspirational:

1. **"Verified" means a specific, machine-checked property** — never a blanket
   guarantee over a tool or a repo. If we can't name the property and the checker,
   we don't call it verified.
2. **Every hand-written bridge is named as trusted base.** A proof of a model you
   also wrote is only as good as the model-to-code link. Naming that link — and
   saying whether it's backed by tests, a refinement proof, or nothing yet — is the
   difference between honesty and theatre.

None of this makes the [how-it-works](@/how-it-works.md) diagram wrong. It makes it
*legible*: the arrows are real, and now you know which ones the machine holds up and
which ones we still do by hand. Closing a seam means moving a joint from *manual* to
*demonstrated* to *wired* — and we'd rather you watch that happen than pretend it
already has.
