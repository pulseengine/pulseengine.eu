+++
title = "The architecture no single repo owns"
description = "The toolchain became a graph this month — so let's go under the hood of two of its edges: how a verified OS composes out of a dozen components across five repos into one 3.5 KB native image, and how loom, synth, and ordeal hand each other proofs to compile WebAssembly to ARM that's checked, not trusted. Real components, real sizes, the actual certificate flow."
date = 2026-07-15
draft = true
[taxonomies]
tags = ["verification", "process", "wasm", "how-it-works"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
PulseEngine is a dozen small repositories that turn **WebAssembly components** into
verified native code — or interpret them — for safety-critical embedded targets. For
a long time that toolchain was a **line**. This month it became a **graph**: proofs
flow *between* stages, one solver is shared across repos, and a whole OS composes out
of parts that live in five different repositories. This post goes under the hood of
two of those edges — the composition, and the proof machinery — because the
interesting behaviour is no longer inside any single repo. It's in the wiring
between them, which is precisely what no single repo's CI can see.
{% end %}

## The shape, first

{% mermaid() %}
flowchart TB
  spar["spar<br/>architecture"]
  code["components<br/>(Rust → wasm)"]
  meld["meld<br/>fuse"]
  loom["loom<br/>optimize"]
  synth["synth<br/>compile → native"]
  kiln["kiln<br/>interpret (host)"]
  gale["gale · gust<br/>on real silicon"]
  ordeal["ordeal<br/>shared solver"]
  sigil["sigil<br/>attest"]
  agora["agora<br/>agents"]
  rivet[("rivet<br/>everything reports here")]

  spar ==>|WIT + skeletons| code ==> meld ==> loom
  loom ==>|compile| synth ==> gale
  loom -.->|interpret · on-target planned| kiln

  loom -.->|proofs · wsc.facts| synth
  synth -.->|checks with| ordeal
  loom -.->|slated| ordeal
  loom -.-> sigil
  synth -.-> sigil
  sigil -.->|signed evidence · designed| rivet
  agora -.->|coordination facts| rivet
  spar -.->|typed artifacts| rivet

  classDef ours fill:#242836,stroke:#6c8cff,color:#e1e4ed;
  classDef edge fill:#242836,stroke:#c084fc,color:#e1e4ed;
  classDef spine fill:#242836,stroke:#fbbf24,color:#e1e4ed;
  class spar,code,meld,loom,synth,kiln,gale,ordeal,sigil ours
  class agora edge
  class rivet spine
{% end %}

*Thick = the component moving through the pipeline; dashed = the new cross-repo edges
(proofs, the shared solver, attestation, coordination). Edges marked planned / slated
/ designed aren't live yet — the honest graph, not the flattering one. The rest of
this post zooms into two of these edges.*

## Edge one: a whole OS, composed from parts in five repos

`gust` is gale's verified-OS target, and it does not live in any single repository.
It's a **Component-Model composition**: a set of components with typed WIT interfaces,
each built and verified in its own repo, that `meld` resolves and flattens into one
core module. Here is what actually composes, with real sizes and what each part is
proven for:

| component | flash | imports / exports | proven (Kani unless noted) |
|---|---|---|---|
| `gale-app-demo` | ~0.6 KB | imports `gale:kernel` | the app's own logic |
| `gale-kiln` (scheduler + primitives) | ~1.2 KB | **exports** `gale:kernel` (sem/msgq/mutex/event) | semaphore shipped (Verus+Rocq), rest in progress |
| `uart-thin` | 254 B | imports `gust:hal/mmio` + `irq` | RX-decision FSM over all 2³² status words |
| `dma-own` | 218 B | + `dma` resource | ownership FSM, 6/6 (access-iff-owned, barrier-pairing, …) |
| `gpio-thin` | 490 B | `gust:hal/mmio` | 4/4 (bounded, injective, mode-safe) |
| `timer-thin` | 212 B | `gust:hal/mmio` | 3/3 (wrap-safe deadline across u32 wrap) |
| `spi-thin` | 494 B | `gust:hal/mmio` | 6/6 (exclusive-bus, no-lost-byte, …) |
| `i2c-thin` | 992 B | `gust:hal/mmio` | 7/7 (ACK-all-but-last, phase-gating, …) |
| `adc-thin` | 754 B | `gust:hal/mmio` | 7/7 (channel-bounds, read-after-EOC, …) |

The drivers are the point of the design: each is *verified wasm* importing **only**
the thin `gust:hal/mmio` capability — `read32` / `write32`. The untrusted native
surface stays tiny. The TCB is a **~77-line Rust shim** — a vector table + reset, a
one-line SysTick handler, and **five MMIO "atoms"** (`mmio_read32`, `mmio_write32`,
`irq_poll`, plus `dma_program` / `dma_barrier` for DMA). Every driver above adds
**zero new TCB atoms** — it rides the same `read32`/`write32` seam. A GPIO driver is
490 bytes of *proven* logic over 2 trusted primitives, not 490 bytes you have to
trust.

Composition is a build-time operation, and it's worth seeing the exact chain, because
"fuse → optimize → compile" hides what's really happening:

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

Upstream of `meld` it's separate components with typed worlds; the instant `meld`
resolves `app`'s `import gale:kernel` against `gale-kiln`'s `export`, the component
boundaries are gone — `loom` and `synth` see one flat core module, and the shipped
artifact has **no runtime underneath it at all**.

Does the dissolved native code still do what the wasm did? The demo answers in one
number. `run-demo()` runs a fixed sequence of semaphore operations and returns a
bitfield; the correct answer is **53** (`0b110101` — `would-block`, `increment`,
`full`). It returns **53** three ways: under `wasmtime` (the component composition,
interpreted), on **qemu Cortex-M3**, and on a **real STM32F100** with the hardware
cycle counter. The kill-criterion is blunt: *either side ≠ 53 falsifies the dissolve.*
This is a **differential equivalence check against a reference semantics, not a proof
of translation** — the honest bound, and the same one gale's own ledger insists on.

The payoff is real silicon, measured bit-identical against native LLVM: **1.73×** on
the Cortex-M3 (STM32F100), **1.45×** on the Cortex-M4 (Nucleo G474RE), **1.84×** on
RISC-V (ESP32-C3). Five repositories' outputs — gale, kiln, meld, loom, synth — lining
up on a chip. No single repo could have claimed that; the composition is the claim.

## Edge two: loom, synth, and ordeal pass each other proofs

The build tail used to be three tools in a row. Now they hand each other *evidence*,
and the last one is checked by a fourth. Follow one function from wasm to ARM:

{% mermaid() %}
flowchart TB
  loom["loom<br/>optimize"]
  synth["synth<br/>wasm → ARM"]
  ordeal["ordeal<br/>QF-BV solver"]
  lean["Lean-verified<br/>LRAT checker"]
  arm["native ARM / RISC-V"]

  loom ==>|optimized wasm| synth ==> arm
  loom -.->|wsc.facts: v∈[lo,hi], divisor≠0, shift<32| synth
  synth -.->|"per-rule: WASM ≡ ARM ?"| ordeal
  ordeal -.->|UNSAT + LRAT certificate| lean
  lean -.->|accept ⇒ UNSAT| synth

  classDef ours fill:#242836,stroke:#6c8cff,color:#e1e4ed;
  classDef trust fill:#161922,stroke:#4ade80,color:#e1e4ed;
  class loom,synth,ordeal,arm ours
  class lean trust
{% end %}

**loom proves what it optimizes, then writes the proofs down.** Every optimization
pass is *translation-validated*: loom encodes the function before and after as QF-BV
(bitvector) formulas and asks a solver whether they can differ. UNSAT ⇒ the transform
is sound and is kept; anything else — a counterexample, a timeout, or a check it can't
run — and the function is **reverted** (a fail-safe added in v1.1.18 after a skipped
proof was once mistaken for a passed one). The scope is honest: straight-line integer
and bitvector code is in scope; loops and the memory model are not. Then loom does
something new — it *keeps* the invariants it proved and emits them as a `wsc.facts`
custom section: `this value is in [524, 1524]`, `this divisor is nonzero`, `this shift
is < 32`, keyed to the exact operator in the function body.

**synth reads those facts and deletes code LLVM would be forced to keep.** synth's
instruction selection is a Rocq-verified rule DSL — 40 rules, 40 `Qed` theorems, "ISLE
with a proof-assistant backend," where a missing rule is an *enumerable coverage gap*
that declines loudly, never a silent miscompile. On top of that, it ingests loom's
facts (VCR-PERF-002): if a value's proven range makes both arms of a clamp dead, synth
elides the whole branch (`84 B → 14 B` on one benchmark); if a divisor is proven
nonzero, the div-by-zero trap guard (`CMP / BNE / UDF`) simply isn't emitted. This is
why a dissolved kernel can dip *below* native LLVM's cycle floor — measured **0.45×**
in the proof-carrying bench: LLVM has to keep guards it can't prove unnecessary; synth
has a proof that says it can drop them. (That floor is still flag-gated pending a
silicon re-measure — the shipped default sits around **1.5×**.)

**ordeal checks synth's work, and a Lean-verified checker checks ordeal.** After
codegen, synth asks the honest question — *is this ARM sequence equivalent to the wasm
it came from?* — as a per-rule QF-BV query, and hands it to
[ordeal](https://github.com/pulseengine/ordeal), its default solver since v0.27
(Z3 build pain gone; no C++ toolchain). ordeal is an *untrusted* CDCL SAT core that
bit-blasts the query; when it answers UNSAT it emits an **LRAT certificate**, and a
**Lean-4-verified checker** (translated from the Rust kernel via Aeneas, and
drift-gated so the proof tracks the shipped code) validates that certificate before
the answer is believed. The theorem is `accept ⇒ UNSAT`: a buggy solver can fail to
prove something, but it *cannot* make a wrong answer accepted. Z3 is kept only as a
development-time differential oracle — **141/141 agreement, zero disagreements** — not
in the trusted chain. (Honest edges: Charon/Aeneas are trusted, not themselves
verified end-to-end; 64-bit multiply/divide are Kani-proven only at width 8.)

Read that as a graph and every arrow crosses a repo boundary: loom's proofs land in
synth, synth's queries land in ordeal, ordeal's certificates land in a checker whose
soundness is proven in a fourth. The verification isn't *in* a repo; it's *between*
them.

## No single repo's CI owns the seams

Which is the whole problem. Every one of those repos can be internally green — tests
pass, proofs close — and the property that spans them can still be wrong, because
nothing between two repos is anyone's build gate.

We keep finding exactly this. These look like housekeeping; they are not — each is a
claim one repo makes that only *another* repo, or the shipped artifact, can falsify.
In one sweep this week:

- **[ordeal](https://github.com/pulseengine/ordeal)** — the shipped soundness proof is
  complete and CI-gated, but its `lean/README.md` still says it's open. The repo
  disagrees with itself.
- **[scry](https://github.com/pulseengine/scry)** — the opposite: the engine is real
  and its Rocq proofs admit-free, but the README still reads "v0.1.0, no real logic
  yet." A repo *underselling* its code makes everything that cites it look inflated.
- **[sigil](https://github.com/pulseengine/sigil)** — began as a hard fork of Frank
  Denis's MIT-licensed `wasmsign2`, diverged ~18×, and carried no license or
  attribution. A cross-repo *lineage* fact no per-repo check would flag.

"Does this README match the shipped proof," "does synth's `ordeal = 0.4` match ordeal's
actual API," "is this fork's license retained" — none are statements a single build can
evaluate. They're architecture properties, and the architecture is the thing no single
repo owns.

## Checking it takes a fleet

You cannot verify a graph one node at a time. So the check spans repos too: a fleet of
agents sweeps *every* repo at once, reads each one's real source, and cross-references
the claims — the README against the shipped proof, the website against each repo's
honesty ledger, one repo's "we depend on X" against X's actual API.

That's not hypothetical — it's how this post was built. A fleet mapped what each
component ingests *today* (the sizes, the fact schema, the certificate flow above) and
surfaced the drift as filed issues, the three above among them. And the coordination is
becoming auditable: [agora](https://github.com/pulseengine/agora) mirrors the agents'
own negotiation into rivet as typed facts — so "how the fleet coordinated" is a record,
not folklore. (agora's still a spike; the direction is the point.)

The pipeline was easy to verify because a line has no surprising interactions. A graph
does — a proof handed across a repo boundary, a solver shared by three tools, an OS
that only exists when five repos line up on a chip. Every one of those lives in the
space *between* repositories. So that's where we've pointed the agents. The
architecture is the thing no single repo owns; increasingly, it's the thing the fleet
is there to check.

---

*The reference view of how the pieces fit: [how it works](@/how-it-works.md). The
honest maturity map: the [how-it-works series](/tags/how-it-works/).*
