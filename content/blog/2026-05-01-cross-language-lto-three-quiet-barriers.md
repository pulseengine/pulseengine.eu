+++
title = "Cross-language LTO on Cortex-M: three barriers and a wrong prediction"
description = "We pushed LLVM cross-language LTO between verified Rust and Zephyr's C kernel. Three barriers nobody documents. Cleared them. Then measured — and the prediction we'd shipped was wrong by a lot. The story of what that taught us, and the framework for picking a regime when the data doesn't dominate."
date = 2026-05-01
draft = true
[taxonomies]
tags = ["verification", "process", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
[gale](https://github.com/pulseengine/gale) is our drop-in formally-verified Rust replacement for the kernel primitives in Zephyr RTOS. We turned on cross-language LTO between rustc and clang on Cortex-M expecting a 10–30% handoff speedup from inlining the Rust into the C call sites. The prediction was wrong — the LTO build came out 1.1 percentage points *slower* per handoff than the GCC + Gale build with the FFI calls intact.

What the measurement actually revealed was that the FFI overhead is a rounding error against the surrounding C kernel cost, and that clang's codegen for that C runs a few cycles per handoff slower than GCC's — enough to outweigh what LTO saved by erasing the FFI. The real value of LTO on this stack lives somewhere else: a binary where every verified-Rust function has been inlined into the call site that uses it, with `nm zephyr.elf | grep gale_` returning zero. That is the configuration where an assessor can verify, with one command, that what was proved is what shipped.

Two configurations now satisfy different constraints — GCC + Gale a touch faster, LLVM + LTO a touch smaller and FFI-shim-free — and the choice between them is a real system-design call.
{% end %}

## Why we cared

[gale](https://github.com/pulseengine/gale) is a drop-in formally-verified Rust replacement for the kernel primitives in Zephyr RTOS — the semaphores, mutexes, message queues, ring buffers, and schedulers everything else in the system leans on. The Verus proofs live next to the Rust source. The Rust compiles to a static archive, the Zephyr public API is unchanged, the C kernel calls into the Rust across an FFI boundary, and the application doesn't notice the substitution.

Why bother? Safety-critical embedded code is mostly C. Not because C is good for safety — the opposite — but because the toolchain and certification ecosystem grew up around C and leaving it has been expensive.

The economics of that decision are starting to shift. The US Office of the National Cyber Director's 2024 report *Back to the Building Blocks*[^oncd] made the case for moving off memory-unsafe languages where it's feasible; DARPA's TRACTOR program[^tractor], announced the same year, is funding the automated-translation side of it — combining static analysis with LLMs to convert legacy C codebases to idiomatic Rust at scale. gale is on the same trajectory from a different angle: not automated translation, but hand-written Rust replacements with Verus proofs for the safety-critical kernel primitives where any translator's output would still need extensive verification work to be trusted in an ASIL- or SIL-rated safety case.

For this to work as a substitution rather than a research demo, three things have to hold:

- **The Rust can't be slower.** Embedded parts run timing budgets where every cycle of ISR latency lands in an assessor's argument. A "verified Rust costs 5% more cycles" headline kills adoption.
- **The binary can't be much bigger.** Cortex-M parts gale targets live in the 32 KB to 1 MB flash range. A few KB of Rust runtime is a real percentage on the smaller end.
- **The assessor has to verify that what was proved is what shipped.** ISO 26262 doesn't accept "trust the toolchain." The safety case argues from the binary that runs on the device. Anything between the proof and the binary that the assessor can't read — opaque optimisations, FFI shims that hide call structure — is a gap that costs extra evidence to close.

Concretely, gale slots in at the layer where Zephyr's `kernel/sem.c` (and friends) used to live. The public API is unchanged, the kernel internals are unchanged, and the middle is rewritten to follow an extract → decide → apply pattern: C reads kernel state and runs side effects (spinlock, wait queue, scheduler), Rust decides the action, C applies the result.

{% mermaid() %}
flowchart TB
    app["Application<br/>(engine bench: crank_isr → k_sem_give,<br/>worker → k_sem_take)"]

    subgraph zapi["Zephyr public API · unchanged"]
        api["&lt;zephyr/kernel.h&gt;<br/>k_sem_give · k_sem_take · ..."]
    end

    subgraph gz["gale Zephyr module · gale/zephyr/"]
        gc["gale_sem.c · gale_pipe.c · ...<br/>z_impl_* live here<br/>extract → decide → apply"]
    end

    subgraph ffi["FFI boundary · gale/ffi/"]
        hdr["gale_sem.h · ...<br/>uint64_t gale_k_sem_give_decide(...)<br/>(packed decision struct)"]
    end

    subgraph rust["Verified Rust core · gale/src/"]
        rs["gale_k_sem_*_decide<br/>gale_sem_count_init · ..."]
        verus["Verus proofs<br/>P1, P2, P3, P5, P6, P9"]
        rs -.checked by.-> verus
    end

    subgraph zint["Zephyr kernel internals · unchanged"]
        sched["z_unpend_first_thread<br/>z_ready_thread · z_pend_curr<br/>k_spin_lock"]
    end

    app --> api --> gc
    gc -->|FFI call| hdr --> rs
    gc -->|side effects| sched

    classDef src fill:#13161f,stroke:#4a5068,color:#8b90a0;
    classDef step fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef ours fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef proved fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
    classDef grp fill:#13161f,stroke:#3d4258,color:#8b90a0;

    class app,api,sched,hdr src;
    class gc,rs ours;
    class verus proved;
    class zapi,gz,ffi,rust,zint grp;
{% end %}

Cross-language LTO is the toolchain machinery all three converge on. It should make the Rust fast (inlining), the binary smaller (no duplicate shim code), and the binary auditable (verified Rust function bodies emitted directly into the C call sites, no FFI hop visible).

{% mermaid() %}
flowchart TB
    subgraph noLto["Without cross-language LTO"]
        direction LR
        rs1["Rust source<br/>gale_*"]
        cl1["C source<br/>Zephyr kernel"]
        rsobj["object<br/>(machine code)"]
        clobj["object<br/>(machine code)"]
        link1["lld"]
        bin1["zephyr.elf<br/>bl gale_* + ret<br/>across FFI boundary"]
        rs1 -->|rustc| rsobj
        cl1 -->|clang| clobj
        rsobj --> link1
        clobj --> link1
        link1 --> bin1
    end

    subgraph yesLto["With cross-language LTO"]
        direction LR
        rs2["Rust source<br/>gale_*"]
        cl2["C source<br/>Zephyr kernel"]
        rsbc["LLVM bitcode"]
        clbc["LLVM bitcode"]
        link2["lld --lto-O3"]
        bin2["zephyr.elf<br/>gale_* bodies inlined<br/>into C call sites"]
        rs2 -->|rustc<br/>-Clinker-plugin-lto| rsbc
        cl2 -->|clang -flto=thin| clbc
        rsbc --> link2
        clbc --> link2
        link2 --> bin2
    end

    classDef src fill:#13161f,stroke:#4a5068,color:#8b90a0;
    classDef step fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef before fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef after fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
    classDef grp fill:#13161f,stroke:#3d4258,color:#8b90a0;

    class rs1,cl1,rs2,cl2 src;
    class rsobj,clobj,rsbc,clbc,link1,link2 step;
    class bin1 before;
    class bin2 after;
    class noLto,yesLto grp;
{% end %}

That was the bet.

## The prediction

[gale](https://github.com/pulseengine/gale) is our formally-verified Rust replacement for Zephyr's kernel primitives. After six weeks of work, the engine-control bench reported a `−3.1%` handoff median against GCC `-Os` on stm32f4_disco — Cortex-M4F at 168 MHz, 7,750 samples, p<1e-100 across 13 RPM steps. Real measurement. The number stands.

The path from there to LTO ran through our internal optimization story, which carried this prediction:

> `-flto` LLVM + Gale: **expected meaningfully faster** — order of 10–30% at handoff mean.

The mechanism was supposed to be obvious. Each handoff goes through a `bl gale_*_decide` and a `ret` — about 3 cycles on Cortex-M4F. Cross-language LTO would inline those away. The verified Verus preconditions would also let the inliner remove defensive C branches like `if (sem->count != sem->limit)` because the precondition makes them provably dead. Compound across every kernel-primitive call site and the win was supposed to compound with it.

It didn't.

## Three barriers

When we first turned the LTO crank, the linked binary had **10 surviving `gale_` symbols**. The flag was on, the linker was right, the build succeeded — and zero inlining was happening.

We spent two days finding three independent reasons. The diagnostic flow for each (the exact `file` / `llvm-dis` / `llvm-objdump` commands, the IR snippets that proved the cause, the experiments we ran and reverted) is in the optimization story[^optimization-story] and issue[^gale-issue-10]. The summaries below are enough to recognise the same problem if you hit it.

{% mermaid() %}
flowchart LR
    s0["LTO flag set<br/>10 surviving<br/>gale_ symbols"]
    b1["Barrier 1<br/>Zephyr's clang<br/>ignores CONFIG_LTO<br/>(no bitcode emitted)"]
    s1["10 surviving<br/>(bitcode now flows,<br/>inliner declines)"]
    b2["Barrier 2<br/>target-cpu / target-feature<br/>mismatch on every fn"]
    s2["5 surviving<br/>(all are sret returns)"]
    b3["Barrier 3<br/>sret type mismatch<br/>(rustc opaque bytes vs<br/>clang named struct)"]
    s3["0 surviving<br/>on hot path"]

    s0 --> b1 --> s1 --> b2 --> s2 --> b3 --> s3

    classDef state fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef wall fill:#1a1d27,stroke:#f87171,color:#e1e4ed;
    classDef done fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;

    class s0,s1,s2 state;
    class b1,b2,b3 wall;
    class s3 done;
{% end %}

**Barrier 1 — Zephyr's clang doesn't honour `CONFIG_LTO`.** The CMake property that turns `CONFIG_LTO=y` into a `-flto` flag is empty for the clang toolchain — only the GCC path sets it. So the build accepts the config, prints no warning, and silently produces ELF objects instead of LLVM bitcode. lld has nothing to inline against. Fix locally by injecting `-flto=thin` from a downstream module; fix upstream by extending Zephyr's clang and lld CMake paths. Filed upstream[^zephyr-issue].

**Barrier 2 — function attributes silently block the inliner.** Once bitcode flows on both sides, LLVM's inliner runs a feature-compatibility check on the `target-cpu` / `target-features` strings that rustc and clang each emit on every function. rustc emits `target-cpu="generic"` and no feature list; clang emits `target-cpu="cortex-m3"` plus ~50 explicit features. The mismatch reduces to "not compatible" and the inliner declines to merge. No warning. No diagnostic. Fix is `RUSTFLAGS=-Ctarget-cpu=cortex-mN -Ctarget-feature=...` matching a strict subset of clang's emission. That dropped surviving symbols from 10 to 5.

**Barrier 3 — `#[repr(C)]` struct returns are an `sret` type mismatch.** The five remaining symbols all returned a struct via `sret` pointer. rustc lowers `#[repr(C)]` struct returns to opaque byte-array `sret`; clang lowers the same struct to a named-type `sret`. The bytes are semantically identical; the IR types disagree; the inliner refuses to merge. Not a flag problem — an FFI-design problem. Pack ≤ 8-byte structs into `uint64_t` so AAPCS[^aapcs] returns them in r0/r1 (both sides emit `i64`, types match, inliner runs). For larger structs, redesign — drop fields the caller can derive, split single-`ERROR` actions into per-error variants. We redesigned three decision structs in gale. Surviving symbol count went from 5 to 0 on the semaphore test, and from 5 to 1 on the engine bench (the survivor is `gale_sem_count_init` — called once at boot, irrelevant to the hot path).

## The result

Two builds, one handoff. Both run the same crank-ISR-signals-worker pattern from the engine bench through the kernel; the difference is whether the gale FFI calls survive the linker.

Without LTO (the GCC + Gale build):

{% mermaid() %}
sequenceDiagram
    participant ISR as crank_isr<br/>(ISR context)
    participant API as Zephyr API
    participant G as gale_sem.c
    participant K as Zephyr internals<br/>(spinlock, wait_q,<br/>scheduler)
    participant R as gale_k_sem_give_decide<br/>(verified Rust,<br/>separate ELF symbol)

    ISR->>API: k_sem_give(&data_ready)
    API->>G: z_impl_k_sem_give(sem)
    G->>K: k_spin_lock + z_unpend_first_thread
    G->>R: bl gale_k_sem_give_decide
    Note over R: Verus-proved:<br/>P3 (count capped),<br/>P9 (no overflow)
    R-->>G: ret (packed decision in r0)
    G->>K: apply (z_ready_thread or sem->count = ...)
{% end %}

With cross-language LTO (the LLVM + Gale + LTO build, after the three barriers were cleared) the verified Rust body is inlined directly into the C call site — the FFI hop disappears from the call trace and the symbol disappears from the ELF:

{% mermaid() %}
sequenceDiagram
    participant ISR as crank_isr<br/>(ISR context)
    participant API as Zephyr API
    participant G as gale_sem.c<br/>(verified Rust inlined)
    participant K as Zephyr internals<br/>(spinlock, wait_q,<br/>scheduler)

    ISR->>API: k_sem_give(&data_ready)
    API->>G: z_impl_k_sem_give(sem)
    G->>K: k_spin_lock + z_unpend_first_thread
    Note over G: Verus-proved decision logic<br/>inlined here — no bl/ret,<br/>no symbol in linked ELF
    G->>K: apply (z_ready_thread or sem->count = ...)
{% end %}

Both builds, run on Renode at 168 MHz, 7,750 samples, all 13 RPM steps with p<1e-100 against baseline[^gale-issue-26]:

| Build | handoff median | handoff max | Δ vs GCC baseline |
|---|---:|---:|---:|
| GCC `-Os` baseline (no Gale) | 354 cyc / 2107 ns | 423 cyc / 2518 ns | — |
| GCC `-Os` + Gale (no LTO) | 343 cyc / 2042 ns | 412 cyc / 2452 ns | **−3.1% / −2.6%** |
| LLVM + Gale + LTO | 347 cyc / 2065 ns | 414 cyc / 2464 ns | **−2.0% / −2.1%** |

LLVM + LTO is **4 cycles per handoff slower** than GCC + Gale, despite LTO provably eliminating the FFI calls.

Flash goes the other way:

| Build | total flash | vs GCC baseline |
|---|---:|---:|
| GCC `-Os` baseline | 37,033 B | — |
| GCC `-Os` + Gale | 38,353 B | +1,320 B (+3.6%) |
| LLVM + Gale + LTO | 37,993 B | **+960 B (+2.6%)** |

LTO trims the Gale memory overhead by about 27% on the engine bench (about 41% on a larger semaphore test we also measured). The inlining we did for cycles doubles as binary-size cleanup — every inlined FFI shim drops out of `.text`.

## Why the prediction was wrong

Two things stack against each other:

The FFI bl/ret pair is real overhead — about 3 cycles per handoff. LTO removes it. That part of the prediction was right.

But clang's codegen at `-Oz` for the surrounding C kernel-primitive code (Zephyr's spinlock, wait queue, scheduler) is a few cycles slower per handoff than GCC's at `-Os`. Net: the toolchain difference washes out the inlining gain and adds 4 cycles back.

We measured the 4-cycle gap. We did *not* run the controlled experiment that would isolate the FFI-savings cycles from the toolchain-codegen cycles — that needs a fourth variant (LLVM-no-LTO + Gale) on the same Renode bench. The contributions are inferred from the three variants we did measure.

The deeper observation: **the handoff path is dominated by C kernel code, not by the FFI**. Ten cycles of FFI overhead is a rounding error against 340 cycles of spinlock and scheduler logic. Eliminate the FFI and you save 0.8% in isolation; toolchain codegen difference for the surrounding 340 cycles can easily wash that out and reverse the sign.

The prediction had the geometry inverted. It treated the FFI overhead as a meaningful fraction of the handoff cost — true on a synthetic round-trip benchmark, false on a real Zephyr handoff where the kernel does the heavy lifting in C.

## How to choose

Two configurations, neither dominates:

| | GCC + Gale (no LTO) | LLVM + LTO |
|---|---|---|
| Median handoff cycles | **−3.1%** vs baseline | −2.0% vs baseline |
| Total flash | +1,320 B over baseline | **+960 B** over baseline |
| Cross-language inlining | no — FFI stays as `bl gale_*` | **yes** — 0 hot-path `gale_` symbols |
| Toolchain artefacts | one (Zephyr SDK GCC) | three (SDK GCC + apt.llvm.org clang + ld.lld matching rustc) |
| Currently at a freeze point | leave it — switching means re-qual | active rework window — choose deliberately |

The choice is a system-design decision typically made once, at the start of a program or during an architectural rework like the one Gale itself represents. Once shipped, switching costs re-qualification of the safety case. So the choice should map to the constraints that dominate the platform — not to whichever number on this page is biggest.

Throughput-budget vs flash-budget is a pre-existing axis on every embedded program. The third row above adds something new: **verifiable proof-to-binary correspondence**. The FFI calls in the GCC build were always there; nobody had measured them. With the LTO build, the assessor can verify the claim with `nm zephyr.elf | grep gale_` and read zero. If the safety case argues from "what was proved is what shipped", that's the only configuration where the argument has direct binary evidence.

For Gale itself, both lanes stay live in CI as regression guards. We don't pick one — we publish both numbers, and let downstream consumers map their constraints to a regime.

## What `nm` returning zero actually buys

In an ISO 26262 argument the safety case runs backward from the binary on the device to the verification evidence at the source. Each link in that chain has to be defensible.

The GCC + Gale chain has three links: the verified Rust function (Verus proof), the C FFI shim that invokes it as a forwarding wrapper, and the compiled machine code for both. The LLVM + LTO chain has two: the verified Rust function and machine code where its body has been inlined directly into the C call site — the shim drops out. That is one fewer hand-written component to defend, traded for one more compiler-transformation step (the cross-language inline) to qualify.

`nm zephyr.elf | grep gale_` returning zero is *symbol-absence* evidence — the gale function no longer exists as a callable entry point. That is direct evidence the inlining happened. The stronger claim, that the call site contains a faithful reproduction of the verified Rust function body, rests on the bitcode-level chain (rustc emits bitcode → lld merges and inlines → no separate symbol survives) rather than on `nm` alone. We're not claiming ISO 26262 *requires* this configuration; the standard does not prescribe a toolchain shape. What it does require is that the safety case be defensible, and "the verified function and the function in the ELF are the same compiled artifact" is qualitatively easier to defend than "the verified function plus a hand-written shim plus their compilations are jointly correct."

## Limits

- Cortex-M3 and Cortex-M4F only. The CMake has branches for RISC-V and AArch64; those are unbuilt.
- One workload — the engine bench, spinlock-dominated handoff with no FPU. Longer Rust hot paths or arithmetic-heavy code may move differently.
- The compilers used here are the Zephyr SDK GCC and apt.llvm.org clang. Neither is itself a safety-qualified product; both can be qualified through process-based arguments, and commercial qualified variants exist that we haven't selected or tested.
- Three measurement points (GCC baseline, GCC + Gale, LLVM + Gale + LTO). A fourth — LLVM + Gale without LTO — would isolate the FFI-savings cycles from the toolchain-codegen cycles. Not run.
- No assessor survey across automotive, medical, industrial, or aerospace. The numbers are technical, not market-research.

## What we shipped upstream

We filed an issue with the Zephyr project[^zephyr-issue] documenting all three barriers, with local workarounds and a proposed shape for the upstream fixes — and offered to send PRs.

## Take-away

Cross-language LTO between rustc and clang on bare-metal ARM works end-to-end today, but only after clearing three barriers that aren't documented anywhere we could find. The `bl`/`ret` you can save by inlining is real but small. On real Zephyr workloads where the kernel-primitive C code dominates, eliminating the FFI is well under 1% of the handoff cost — and clang's codegen difference vs GCC for the surrounding C can wash it out.

The LTO regime delivers what the GCC regime can't: provable absence of FFI shims in the linked binary, and about 360 bytes less flash. Whether that outweighs a 1.1% cycle cost is a system-design question the data alone doesn't decide.

### The method that actually mattered

What we expected to learn was a performance number. What we learned was a method:

- **Predict from the architecture** (we said: 10–30% faster, mechanism = eliminating the per-handoff `bl`/`ret`). Specific enough to be falsifiable.
- **Measure on real hardware** (Zephyr handoff through spinlock + wait queue + scheduler — not a synthetic FFI round-trip where the FFI dominates). The geometry is what the prediction implicitly assumes.
- **Publish the falsification.** Wrong-prediction data is more informative than the predicted number would have been if it landed. "We expected X, we got Y, here is what Y means" is the post worth writing.
- **Reframe around what the data supports.** The FFI savings weren't the win; proof-to-binary correspondence is. Write up what was actually learned, not what you set out to prove.

That sequence is the load-bearing thing — not the cycle count, not even the inlining win.

---

## Sources

[^gale-issue-10]: [`pulseengine/gale#10`](https://github.com/pulseengine/gale/issues/10) — "LLVM LTO: Get true cross-language inlining (zero overhead)". The closing comment carries the full archaeology: each barrier with the commit that fixed it, each measurement with the CI run that produced it, the reverted experiments that ruled out the wrong hypotheses.

[^gale-issue-26]: [`pulseengine/gale#26`](https://github.com/pulseengine/gale/issues/26) — "engine-bench-renode-lto.yml — measure handoff cycle delta under LLVM+LTO". The CI run that produced the cycle numbers in this post and the comment with the result.

[^zephyr-issue]: [`zephyrproject-rtos/zephyr#107948`](https://github.com/zephyrproject-rtos/zephyr/issues/107948) — the upstream-Zephyr issue summarising the three barriers and proposing fixes for the two that are Zephyr-side.

[^optimization-story]: [`docs/research/optimization-story.md`](https://github.com/pulseengine/gale/blob/main/docs/research/optimization-story.md) — the in-repo doc that carries the same data in long form.

[^aapcs]: [ARM AAPCS-32](https://github.com/ARM-software/abi-aa/blob/main/aapcs32/aapcs32.rst) — Procedure Call Standard for the Arm Architecture. The "fundamental data type ≤ 8 bytes returns in r0/r1" rule is what makes the `uint64_t` packing for `sret` elimination work.

[^oncd]: [*Back to the Building Blocks: A Path Toward Secure and Measurable Software*](https://bidenwhitehouse.archives.gov/wp-content/uploads/2024/02/Final-ONCD-Technical-Report.pdf), US Office of the National Cyber Director, February 2024 — the report that put memory-safe languages on the federal cybersecurity agenda.

[^tractor]: [TRACTOR — Translating All C to Rust](https://www.darpa.mil/research/programs/translating-all-c-to-rust), DARPA Information Innovation Office, program manager Dr. Dan Wallach. Announced [July 2024](https://www.darpa.mil/news/2024/memory-safety-vulnerabilities); test & evaluation by [MIT Lincoln Laboratory](https://www.ll.mit.edu/tractor).

---

*This post is part of [PulseEngine](/) — a formally verified WebAssembly Component Model engine for safety-critical systems. Prior posts in the verification arc: [Formal verification just became practical](/blog/formal-verification-ai-agents/), [What comes after test suites](/blog/what-comes-after-test-suites/), [Spec-driven development is half the loop](/blog/spec-driven-development-is-half-the-loop/).*
