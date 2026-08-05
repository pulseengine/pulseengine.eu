+++
title = "Speaker notes — every number in the deck"
description = "What each figure in the Wasm Research Day 2026 talk measures, what it does not mean, and where it came from."
date = 2026-08-06
template = "page.html"
+++

The title slide promises *every number on these slides says where it came from*.
This is that promise, written down. Open it on a second screen during Q&A.

Each entry is: **what the slide says** → what it actually measures → **what it
does not mean** → where it comes from.

---

## 43 of 45 — slides 19 and 32

**Slide 19** ("Is this the Component Model, or our dialect?") — *43 / 45
canonical-ABI fixtures pass at runtime.*
**Slide 32** (takeaway) — *fuse the graph into one core module and the boundary is
gone; 43 of 45 canonical-ABI fixtures then behave identically.*

**What it measures.** 45 wit-bindgen test fixtures. Each one is a *component
graph* exercising a canonical-ABI feature — strings, lists, records, variants,
options, results, resources, multi-return, flags, enums, type aliases — across
**both directions** of cross-component calls. For each: compose the graph, fuse it
into a single core module, **run it**, and compare the observed behaviour against
the unfused original. 43 behave identically.

This is a **differential execution oracle**, not a validation check. That
distinction matters and is worth saying: a fused module can type-check, pass
`wasm-tools validate`, and still be wrong. Only running it catches that class.

**What it does not mean.**
- Not 43/45 of the Component Model *specification* — it is a fixture pass rate.
- Not "lowered to native and still correct". This is the **fusion** step, run
  under a host. The lowering to a native object is a separate stage.
- Not a claim about async, which is rejected rather than tested.

**The two failures.** Three-component resource forwarding chains where the
*intermediate* component re-exports a resource it does not itself define. A known
hard corner of the canonical ABI, not a general weakness.

**Source.** meld's RFC-46 response, and its fixture suite.

---

## The composition figures — slide 6

*5 components → 1 component, 20 741 B → meld fuse → 1 core module, 9 874 B (−52.4%)
→ gustos.o, 4 812 B text, .bss 0 → 3 native functions.*

**What it measures.** The five `gust:os` provider components, composed with `wac`,
fused with `meld fuse --memory shared`, optimized with `loom optimize --passes
inline`, lowered with `synth compile --target cortex-m3 --all-exports
--relocatable`. Sizes by `wc -c` and `arm-zephyr-eabi-size`. The three undefined
symbols are `poll-task`, `read32`, `write32`, by `nm -u`.

**What it does not mean.**
- `.bss 0` is **zero static RAM in the object** — not "this OS needs no RAM".
  Stacks and any linear-memory arena are provided by the embedder.
- "3 native functions" is the **seam**, not the trusted base. See slide 20.
- The 52.4% includes deleted component metadata, not only memory merging.

**Correction on the record.** An earlier version of the flow slide said *11 linear
memories*. The composed component has **5**. The 11 came from a grep that also
matched five `(export "memory")` lines and a `canon lift`; meld's own stdout says
"Fusing 11 components", which made the wrong number look right.

---

## 8 bytes of SRAM — slide 9

*A whole flashed image: 6 028 B flash of 131 072 (4.6%), 8 B SRAM of 8 192 (0.1%),
8 184 free.*

**What it measures.** `gust_wdg_silicon` — the firmware actually flashed for the
Cortex-M3 leg — by `arm-zephyr-eabi-size`.

**What it does not mean.** This is the **watchdog silicon test image**: one
dissolved driver plus the minimum to boot and report. It is a **floor, not a
system footprint** — no scheduler, no task set, no application. Say this before
someone asks; the slide says it too.

---

## 2 048 of 8 192 — slide 33 (gaps)

*An OS node reserves 2 048 bytes for its shadow stack, and the budget is asserted
rather than proven.*

**Why it is in the deck.** gale's OS-node builds pass `synth --shadow-stack-size
2048`, and synth's own flag contract says: *"The footprint is ASSERTED (the budget
is trusted), not proven — synth does not yet prove the program's max shadow-stack
depth fits the budget."* scry computes the depth; wiring it is the named next
step. If asked "do you have a stack bound" the answer is **no, and here is exactly
what would give us one**.

---

## The driver seams — slides 17 and 18

*USART: 254 B · 0 SRAM · 3 relocations. DMA: 220 B · 0 SRAM · 6 Kani proofs.*

**What it measures.** `arm-zephyr-eabi-size` on the committed dissolved objects;
`nm -u` for the relocation count; `kani::proof` harness count for the DMA
ownership FSM.

**Correction on the record.** The USART figure was **326 B** in an earlier draft.
That number comes from a results file attributed to a two-year-old toolchain and
no current build reproduces it; the committed object measures 254. The DMA object
is **220 B**, not the 218 that had been circulating.

---

## Three dies — slide 14

*Cortex-M4 and Cortex-M3: IWDG reset CONFIRMED, `RCC_CSR 0x14000000 → 0x34000000`,
`IWDGRSTF=1`. RISC-V: native 271 vs dissolved 499 milliticks/call, 1.839× slower,
correctness IDENTICAL over [0,2047], mismatch 0.*

**What it does not mean.** The two watchdog legs are **one happy path on two
dies**. They do not evidence the cannot-un-start property — the firmware never
attempts an un-start. That property is a source-level Kani proof and stays one.

The ESP32-C3 figure **reproduces** a July measurement using the committed synth
0.40 object; the current toolchain pin is newer, so it is not a measurement of
what we ship today. The re-dissolve is blocked because the `gust_mix` wasm input
is not in the repository.

---

## The fact channel — slides 21 to 23

*Nine bytes: `01 01 01 03 07 03 00 ff 0f`. A guarded memory access: 232 → 104 B.*

**What it measures.** The nine bytes are computed from loom's own emitter
(`build_wsc_facts_payload`): schema version, fact count, kind, function index,
value id, body length, then `lo`/`hi` as signed LEB128. One value-range fact,
function 3, value 7, range [0, 2047].

**What it does not mean.** The 232 → 104 figure is **what the channel does when it
carries a fact** — not evidence that we produce many. The emitter, schema and wire
format are done and byte-verified against the consumer; the *source* that would
populate it at volume is not wired. loom emits **no** `wsc.facts` section by
default.

---

## The clamp — slides 26 to 28

*native LLVM 0.50 ticks/call · dissolved today 0.70 (1.4× slower) · with the proof
0.23 (2.2× faster). And `assert_unchecked` → stock LLVM 30 B → 12 B.*

**What it measures.** `gust_floor_bench`, same harness for all three. The
`assert_unchecked` comparison is rustc → thumbv7m, `opt-level="s"`, lto,
panic=abort.

**The honest headline, volunteered before anyone asks.** The shipping
configuration is **1.4×–1.84× slower than native LLVM**. The 0.23 row is the
proof-carrying path, and it depends on a fact channel whose producer is not wired.

**Correction on the record.** The deck used to claim *"a compiler with no verifier
cannot reach it"*. That is **false** — told the same premise, stock LLVM folds the
clamp identically. What is ours is the *provenance* of the premise:
`assert_unchecked` is unchecked, so a wrong range is undefined behaviour with no
diagnostic. Both emit the same instruction; only one of them checked.

---

## Componentization cost — slides 30 and 31

*gpio 502 → 1196 · timer 204 → 828 · spi 454 → 1450 · wdg 638 → 1718 B. And
1746 → 1428 B, −318, with a bounded arena.*

**What it does not mean.** The **1746** control is a *rebuild* against the
wit-bindgen fork with the feature off — not the shipped 1718 object. The −318 is
attributable to the feature alone; the version bump between them costs +20 B on
its own. Measuring against the shipped object would have credited the feature with
−298 and been wrong.

**Correction on the record.** The spi figure was **1244** in an earlier draft.
That number appears nowhere in the repository or its history; the measured and
recorded figure is 1450.

---

## What synth actually eats — slide 21 (synth tab)

**Correction on the record.** The synth tab's `in` row used to read *WIT / ABI —
lift · lower*, and did not name the actual input at all. On gale's path synth is
handed **one core module** — `loom.wasm`, `fused.stripped.wasm`, or a `.wat`; every
`build-*.sh` in `benches/gust/` calls `synth compile <core-module>`. It is never
handed a WIT file or a component, and its CLI has no `--wit` flag.

synth *does* carry a WIT parser (`synth-wit`) and a canonical-ABI lift/lower
implementation (`synth-abi`) — but on this pipeline they are not on the path,
because **meld already did the lifting and lowering upstream and erased the
boundary**. Claiming them as synth inputs credited synth with meld's work.

If asked "so what does synth do with WIT?" — on this pipeline, nothing. It is a
core-module compiler here. The Component Model work happens one stage earlier.

---

## 50 rules · 50 Rocq Qed — slide 20 (synth tab)

Say the denominator if asked: 50 *selection* rules proved, against synth's own ISA
model. It is not 50 of all rules in all backends, and the model is ours rather than
an external mechanization.

---

## Things to say before being asked

- **Proofs are gated on pull requests, path-filtered** — Verus, Rocq and Kani run
  on push and PR to main for proof-relevant paths. A commit outside those paths
  triggers nothing. **Lean runs in no workflow at all.**
- **We have not been audited** by any certification authority. The project says so
  in its own posture statement.
- **Bounded model checking is bounded.** If asked for the bound on a specific
  property, say you will follow up rather than guess.
