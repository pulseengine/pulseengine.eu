+++
title = "Overdoing the verification chain — and mapping it to six safety domains"
description = "The prior posts argued for proofs and for traceability. This one shows the full chain, why I chose to overdo rather than undercommit, and where the stack earns credit across six safety domains — with an honest read on what still does not clear the bar."
date = 2026-04-29
draft = true
[taxonomies]
tags = ["verification", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
Proofs cover all inputs. Tests cover realistic inputs. Concurrency checkers cover every interleaving. Mutation testing covers the test suite itself. Sanitizers catch what unsafe code actually does at runtime. Each technique answers a different question. When you do not yet know which question the next assessor cares about — and you will not, because you work across six standards written by six different committees — overdoing is the only honest default.
{% end %}

## The arc so far

[Formal verification just became practical](/blog/formal-verification-ai-agents/) made the case that AI agents collapse the cost of writing proof annotations. [What comes after test suites](/blog/what-comes-after-test-suites/) argued that proofs layer — Verus for functional contracts, Rocq for abstract models, Lean for scheduling theory, Kani for bounded state exploration, tests and sanitizers for everything else — and that rivet[^rivet-184] holds the traceability together.

This post zooms out. What does the whole chain look like, why is overdoing the right default, and where does the same stack earn credit across more than avionics?

## Why overdo is the default

Regulated domains reward defense in depth, not minimum-viable verification. Each technique has a blind spot. Proofs miss the cases where your specification is wrong. Tests miss the inputs you did not think to try. Model checkers miss states beyond their bound. Sanitizers only see what ran. Human review misses what scrolled past.

Combinations shrink the blind spot faster than any single technique improves. Adding a second, independent tool at the same layer is often cheaper than tightening the first one beyond diminishing returns.

And AI-velocity code grows the verification surface. If an agent can implement a feature in minutes, the proof annotations, tests, benches, and traceability artifacts have to keep pace on the same clock. A pipeline that runs proofs, tests, sanitizers, and mutation testing on every push scales to meet that. One that runs fewer does not.

The cost of overdoing is CI budget. The cost of undercommitting is a certification campaign that stalls because one technique the assessor expected is missing. I know which I would rather pay.

## The chain, layer by layer

Ten layers, each answering a different question. No project names in this table — this is the technique picture, not the adoption picture.

{% mermaid() %}
flowchart TB
    subgraph allIn["proves for all inputs"]
        direction TB
        lean[Lean · Rocq]
        verus[Verus · Rocq-of-Rust]
        kani["Kani (bounded)"]
        ztv[Z3 translation validation]
    end
    subgraph manyIn["covers many realistic inputs"]
        direction TB
        prop[proptest]
        loom["tokio-rs/loom<br/>every interleaving"]
        mut["cargo-mutants<br/>tests the tests"]
        crit["criterion<br/>perf regression"]
    end
    subgraph runtimeObs["observes what actually runs"]
        direction TB
        miri[Miri]
        san[ASAN · TSAN · LSAN · UBSAN]
    end
    rivet["rivet — traceability<br/>across all three"]

    allIn -.-> rivet
    manyIn -.-> rivet
    runtimeObs -.-> rivet

    classDef grp fill:#13161f,stroke:#3d4258,color:#8b90a0;
    classDef tool fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef trace fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
    class allIn,manyIn,runtimeObs grp;
    class lean,verus,kani,ztv,prop,loom,mut,crit,miri,san tool;
    class rivet trace;
{% end %}

| Layer | Answers | Techniques |
|---|---|---|
| Pure mathematical logic | Is the theory sound? | Lean 4 + Mathlib, Rocq |
| Functional contracts on Rust | Does the code satisfy its spec for all inputs? | Verus (SMT/Z3), Rocq-of-Rust, Aeneas (planned refinement into Lean) |
| Bounded state-space exhaustion | Does it hold up to a realistic bound? | Kani (CBMC) |
| IR-to-IR translation | Does the pipeline preserve what was proved at the source? | Bespoke Z3 translation validation on the WASM optimizer |
| Property-based sampling | Does it hold on randomised realistic distributions? | proptest |
| Concurrency exhaustion | Does it hold under every thread interleaving? | tokio-rs/loom |
| Runtime observation of unsafe code | Do the unsafe regions actually behave? | Miri, ASAN, TSAN, LSAN, UBSAN |
| Test-suite adequacy | Would my tests detect a real bug? | cargo-mutants |
| Performance regression | Did the latency budget hold? | criterion — before any hardware test |
| Traceability | Which requirement does each of the above satisfy? | rivet |

Operationally, those layers run through **four gates** on every push:

{% mermaid() %}
flowchart LR
    push([developer push])
    pc["pre-commit<br/>rivet 21-hook template"]
    bz["bazel test //...<br/>hermetic"]
    gh["GitHub Actions<br/>miri · sanitizers · proptest<br/>fuzz · differential · mutation"]
    kv["cargo-kiln verify-matrix<br/>ASIL profile"]
    hw([hardware])

    push --> pc --> bz --> gh --> kv --> hw

    classDef endpoint fill:#13161f,stroke:#4a5068,color:#e1e4ed;
    classDef gate fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    class push,hw endpoint;
    class pc,bz,gh,kv gate;
{% end %}

1. **Pre-commit** — shift-left. rivet's 21-hook template is the reference: formatting, clippy, cargo-test, cargo-audit, cargo-deny, cargo-bench-check, cargo-mutants, rivet-validate.
2. **Bazel `test //...`** — the hermetic gate. Compiles and runs verus_test, kani_test, rocq_proof_test, lean_proof_test alongside rust_test.
3. **GitHub Actions** — the matrix gate. Miri, sanitizers, proptest, fuzz smoke, differential, mutation, integration.
4. **ASIL-profile verify** — the pre-release gate. ASIL-D config exercises the strictest path in CI before anything reaches a board.

Hardware comes after criterion benchmarks have cleared their regression budget. Silent performance drift is just as disqualifying as a failed proof, and it is cheaper to catch it in minutes on a laptop than in hours on a bring-up rig.

## Where we stand — honest assessment

Traffic-light at the chain-layer level, not the project level. The project-level matrix lives in the tracking issue[^rivet-184].

| Layer | Status |
|---|---|
| Mathematical logic (Lean, Rocq) | ✅ shipping |
| Functional SMT contracts (Verus) | ✅ shipping at scale; Z3 proof certificates not yet independently checkable |
| Refinement from Rust to Lean (Aeneas) | ◐ scaffolded; hermetic Charon pending[^rules-lean-1] |
| Bounded model checking (Kani) | ✅ shipping |
| Translation validation (Z3 on WASM IR) | ✅ shipping, bespoke |
| Abstract interpretation | ❌ not yet — the one missing third DO-333 technique class |
| proptest / tokio-rs/loom / sanitizer | ✅ present but unevenly adopted across the estate |
| Mutation testing | ◐ shipping at pre-commit in one repo; generalizing via a canonical template |
| Traceability (rivet) | ✅ shipping, living artifact |

## Six standards, one chain

Most safety-critical standards are published behind per-copy paywalls. I cannot quote them verbatim. What follows is grounded in open-access primary sources where available (NASA-STD-8719.13[^nasa-std-8719], ECSS-Q-ST-80C Rev.2[^ecss-80c], NASA Langley's DO-333 case study materials[^nasa-langley-do333][^nasa-cr-2014], peer-reviewed papers[^mdpi-do333]) and in named secondary interpretations from qualified vendors and consultants where not[^ldra-do332][^ldra-26262][^ldra-61508][^adacore-en50128][^afuzion-do332][^afuzion-do330][^visure-do333][^tuv-61508][^milemb-do332][^rapita-do332]. Every claim below cites at least one source; paywall caveats are consolidated in the Sources section.

| Standard | Domain | FM posture | Our fit | Biggest gap |
|---|---|---|---|---|
| DO-178C + DO-333 | Avionics (DAL A–C) | DO-333 permits formal analysis in place of testing under soundness + completeness conditions[^mdpi-do333][^visure-do333] | Two of three DO-333 technique classes; WASM-IR translation validation is a §FM.6.7(f)-style asset[^nasa-cr-2014] | DO-330 qualification dossier[^afuzion-do330] for Verus / Kani / Z3 TV |
| ISO 26262 (Part 6) | Automotive (ASIL A–D) | Formal verification "highly recommended" at ASIL D as summarised in vendor compliance guides[^ldra-26262][^parasoft-26262] | Strong fit; ASIL-profile gate already in the CLI | Tool Confidence Level qualification[^ldra-26262] |
| IEC 61508-3 | General FS (SIL 1–4) | Formal methods "highly recommended" at SIL 3/4; Annexes A/B list techniques including theorem proving[^ldra-61508][^tuv-61508] | Strong fit; HOL lineage welcomed | Proven-in-use or §7.4.4 qualification argument[^ldra-61508] |
| EN 50128 | Railway (SIL 0–4) | Formal proof explicitly "highly recommended" at SIL 3/4[^adacore-en50128][^en50128-academia] | Best cultural fit — theorem proving is the railway norm (B-method heritage) | Lean lacks certification precedent vs. B / Coq[^en50128-academia] |
| IEC 62304 + FDA CSA | Medical (Class A/B/C) | Silent on specific tools; accepts technique plus traceability | Traceability via rivet is the usable artifact | Mapping proofs into DHF + ISO 14971 risk controls |
| ECSS-Q-ST-80C Rev.2 | Space (Cat A/B) | Recommended; no rigid qualification regime[^ecss-80c] | Fits; artifacts are assessor-checkable | No established credit template for newer provers |

Nuclear (IEC 60880) sits outside this table deliberately. Regulator acceptance of SMT-backed arguments is harder to establish than the other six domains, and the pedigree preference for tabular methods means an SMT-first stack walks in with a disadvantage.

A one-line gloss for each technique in the matrix below — skip if these read like home:

- **Theorem proving** — machine-checked mathematical proofs (Lean, Rocq) that a specification holds for all inputs. The proof term is independently re-checkable by a small kernel.
- **SMT contracts** — `requires` and `ensures` annotations on Rust functions, discharged automatically by an SMT solver (Z3, behind Verus). Fast in CI; limited to decidable theories.
- **Bounded MC** — *bounded model checking*: exhaustive exploration of every execution up to a finite bound on loop iterations and state depth. Kani for Rust.
- **Translation validation** — a per-pass proof that a compiler transformation preserves semantics, run on the actual input. Lets a source-level proof extend to the executable. Our WASM optimizer uses bespoke Z3 encoding here.
- **Abstract interpretation** — execute the program over mathematical sets (`non-negative integer`, `[0, 255]`) instead of concrete values, to compute a sound over-approximation of all possible behaviours without running it on concrete inputs. Astrée is the canonical industrial tool.
- **proptest** — property-based testing with random input generation and failure shrinking.
- **tokio-rs/loom** — permutation-checks every possible thread interleaving in a bounded concurrent program.
- **Sanitizer · Miri** — runtime instrumentation that detects undefined behaviour, memory errors, and data races (ASAN, TSAN, LSAN, UBSAN, Miri).
- **Mutation testing** — inject small plausible bugs into the source and check whether the test suite catches them; empirical test-suite adequacy.
- **Traceability** — requirement ↔ design ↔ code ↔ test ↔ proof chain, validated on every commit (rivet).

At a glance, all seven domains against the core chain techniques:

<div class="credit-matrix-wrap">
<table class="credit-matrix">
  <thead>
    <tr>
      <th></th>
      <th title="Lean · Rocq · proof terms independently checkable by kernel">Theorem<br>proving</th>
      <th title="Verus via Z3 — needs tool-qualification argument">SMT<br>contracts</th>
      <th title="Kani — bounded state-space exhaustion">Bounded<br>MC</th>
      <th title="Z3 on WASM IR — source→object preservation">Translation<br>validation</th>
      <th title="Not yet in our stack — the third DO-333 technique class">Abstract<br>interp.</th>
      <th title="Property-based testing — random robustness">proptest</th>
      <th title="tokio-rs/loom — every thread interleaving">tokio-rs<br>loom</th>
      <th title="Miri + ASAN/TSAN/LSAN/UBSAN — runtime anomaly detection">Sanitizer<br>&nbsp;· Miri</th>
      <th title="cargo-mutants — test-suite adequacy">Mutation<br>testing</th>
      <th title="rivet — requirements-to-evidence linking">Trace-<br>ability</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>DO-178C + DO-333 (avionics)</th>
      <td class="fit-strong" title="strong — DO-333 theorem-proving class">●</td>
      <td class="fit-partial" title="partial — needs DO-330 TQL qualification">◐</td>
      <td class="fit-strong" title="strong — DO-333 model-checking class">●</td>
      <td class="fit-strong" title="strong — matches FM.6.7(f) source-to-object rule">●</td>
      <td class="fit-gap" title="gap — the third DO-333 technique not yet in our stack">○</td>
      <td class="fit-strong" title="strong — DO-178C §6.4.2.2 recognises random testing">●</td>
      <td class="fit-strong" title="strong — bounded model checking for concurrency (DO-333)">●</td>
      <td class="fit-strong" title="strong — runtime robustness evidence">●</td>
      <td class="fit-strong" title="strong — test-suite adequacy addresses the MC/DC-for-Rust gap">●</td>
      <td class="fit-strong" title="strong — rivet artefacts support the full trace chain">●</td>
    </tr>
    <tr>
      <th>ISO 26262 ASIL D (automotive)</th>
      <td class="fit-strong" title="HR at ASIL D (per vendor compliance guides)">●</td>
      <td class="fit-partial" title="partial — Tool Confidence Level argument required">◐</td>
      <td class="fit-strong">●</td>
      <td class="fit-partial">◐</td>
      <td class="fit-gap">○</td>
      <td class="fit-strong" title="Part 6 Table 9 interface/robustness testing">●</td>
      <td class="fit-partial" title="partial — Table 10 integration context">◐</td>
      <td class="fit-strong" title="Table 7 analysis techniques">●</td>
      <td class="fit-partial" title="Table 13 referenced as test-quality metric">◐</td>
      <td class="fit-strong">●</td>
    </tr>
    <tr>
      <th>IEC 61508 SIL 4 (general FS)</th>
      <td class="fit-strong" title="HR in Annex A technique tables">●</td>
      <td class="fit-partial">◐</td>
      <td class="fit-strong" title="model checking in Annex B">●</td>
      <td class="fit-partial">◐</td>
      <td class="fit-partial" title="abstract interpretation recognised in Annex B">◐</td>
      <td class="fit-strong" title="Annex B.5.3 boundary / equivalence class testing">●</td>
      <td class="fit-strong" title="Annex B concurrency model checking">●</td>
      <td class="fit-strong" title="Annex B defensive programming / dynamic analysis">●</td>
      <td class="fit-strong" title="Annex C.5.12 mutation testing — explicit">●</td>
      <td class="fit-strong">●</td>
    </tr>
    <tr>
      <th>EN 50128 SIL 4 (railway)</th>
      <td class="fit-strong" title="HR — Table A.3 Formal Proof">●</td>
      <td class="fit-partial">◐</td>
      <td class="fit-strong" title="Table A.17 model checking">●</td>
      <td class="fit-partial">◐</td>
      <td class="fit-gap">○</td>
      <td class="fit-strong" title="Table A.14 random testing">●</td>
      <td class="fit-strong" title="Table A.17 model checking for concurrency">●</td>
      <td class="fit-strong" title="Table A.5 defensive programming">●</td>
      <td class="fit-strong" title="Table A.17 test coverage adequacy">●</td>
      <td class="fit-strong">●</td>
    </tr>
    <tr>
      <th>IEC 62304 Class C (medical)</th>
      <td class="fit-partial" title="accepted; standard silent on specific tool">◐</td>
      <td class="fit-partial">◐</td>
      <td class="fit-partial">◐</td>
      <td class="fit-partial">◐</td>
      <td class="fit-na" title="standard silent">—</td>
      <td class="fit-strong" title="§5.5.5 unit acceptance criteria allow property-based">●</td>
      <td class="fit-partial" title="concurrency testing accepted">◐</td>
      <td class="fit-strong" title="UB detection valued for unsafe code">●</td>
      <td class="fit-strong" title="FDA CSA accepts mutation as adequacy evidence">●</td>
      <td class="fit-strong" title="§9 + FDA DHF requires full traceability">●</td>
    </tr>
    <tr>
      <th>ECSS-Q-ST-80C Cat A (space)</th>
      <td class="fit-partial">◐</td>
      <td class="fit-partial">◐</td>
      <td class="fit-partial">◐</td>
      <td class="fit-partial">◐</td>
      <td class="fit-na">—</td>
      <td class="fit-strong">●</td>
      <td class="fit-partial">◐</td>
      <td class="fit-strong">●</td>
      <td class="fit-partial" title="accepted but no established template">◐</td>
      <td class="fit-partial">◐</td>
    </tr>
    <tr>
      <th>IEC 60880 Cat A (nuclear)</th>
      <td class="fit-partial" title="theorem proving has strongest nuclear-regulator acceptance">◐</td>
      <td class="fit-gap" title="regulators distrust SMT-only arguments">○</td>
      <td class="fit-partial">◐</td>
      <td class="fit-partial">◐</td>
      <td class="fit-gap">○</td>
      <td class="fit-partial">◐</td>
      <td class="fit-partial">◐</td>
      <td class="fit-partial">◐</td>
      <td class="fit-partial">◐</td>
      <td class="fit-partial">◐</td>
    </tr>
  </tbody>
</table>
</div>

<div class="credit-matrix-legend">
  <span class="fit-strong">strong fit</span>
  <span class="fit-partial">partial — needs qualification or conditions</span>
  <span class="fit-gap">gap today</span>
  <span class="fit-na">standard silent</span>
</div>

## What becomes useful per domain

Concrete reads on where the same chain would actually cash in.

- **Automotive (ASIL D).** Kani with ASIL profiles plus rivet traceability plus cargo-mutants answers exactly what Part 6 unit-verification tables and Part 8 tool-confidence guidance expect to see[^ldra-26262]. Fits without rework.
- **Avionics (DAL A–C).** The WASM-IR translation validation is the under-valued asset; it is the kind of translation-preservation argument DO-333's source-to-object rules were written for[^nasa-cr-2014][^mdpi-do333]. Qualification under DO-330 is the work.
- **Railway (SIL 4).** The cultural fit is strong; the specific move is to port critical Lean theorems to Rocq for dossier gravitas — Coq has industrial precedent[^en50128-academia] that Lean does not yet — and to show a worked Aeneas refinement to bridge Rust implementation to the proof[^aeneas-paper].
- **Medical (Class C + FDA CSA).** Primarily a traceability and risk-control mapping play. rivet is the usable artifact. Proofs are a bonus the standard does not strictly require.
- **Space (Category A).** Assessor-checkable artifacts (proof terms, SMT certificates) are where realistic credit lives[^ecss-80c]. Dual-formalization of critical modules in Rocq strengthens this.
- **General functional safety (SIL 4).** The baseline. If this works, the four above largely follow[^ldra-61508][^tuv-61508].
- **Nuclear (Category A).** Hardest. Defer unless mission-critical. If pursued, pair SMT with tabular specifications in the dossier; do not rely on SMT alone.

## Where we go from here

Three pieces visibly missing.

**Abstract interpretation — the third DO-333 technique class.** This is the single layer of the chain we do not yet run. Abstract interpretation executes a program in a mathematical universe where concrete values (`42`) are replaced by sets (`non-negative integer`, `[0, 255]`, `may-alias set`) and computes a *sound over-approximation* of every possible behaviour without running the program on concrete inputs. It is particularly strong at integer overflow, division-by-zero, out-of-bounds accesses, and numerical precision loss — exactly the classes of runtime failure that SMT is awkward with and bounded model checking cannot guarantee outside its bound.

Three candidate paths, in rough order of "credibility already established" vs "fits our toolchain":

- **[Astrée](https://www.absint.com/astree/)** (AbsInt, commercial). The canonical AI tool. Airbus A380 and A350 used it for DO-178B/C DAL A credit, and that precedent is exactly what a certification authority wants to see. Supports C and Ada — not Rust. For PulseEngine it would only fit the C-shim boundary (WASI host intrinsics, FFI shims), and it drags in a separate toolchain we would otherwise avoid. Licence cost is in the tens of thousands of EUR per year.
- **[MIRAI](https://github.com/facebookexperimental/MIRAI)** (Meta, research-grade). An abstract interpreter for Rust MIR, designed for the language. Covers integer overflow, panics, and some memory properties out of the box. Recent activity is low (steady since 2022), but the code is open source and the property classes it targets are the ones that matter for ASIL-D and DAL-A credit stories. Fastest way to see whether AI adds signal on our codebase — weekend-scale prototype.
- **Charon-based value analysis.** The strategic fit. Our pending Aeneas integration[^rules-lean-1] exposes Rust MIR as LLBC through Charon. A modest abstract interpreter built directly on LLBC — interval, sign, and may-alias lattices to start — keeps a single Rust-MIR toolchain, reuses the Nix-hermetic build, and produces analysis artefacts that live alongside the Lean and Rocq proofs. Rough effort: 2–4 months of focused work to a first useful pass.

The plan: prototype with MIRAI this quarter to confirm which property classes actually pay off on our code; plan Charon-based value analysis as the longer-term investment once Aeneas is running end-to-end. Astrée stays on the shelf for the C-shim boundary if and when a specific certification programme asks for it.

**The Check-It pattern.** NASA's own tool-qualification research[^nasa-cr-2017] describes the shape: untrusted prover emits a checkable proof certificate, tiny trusted checker validates it, only the checker is qualified under DO-330. Rocq and Lean work this way by construction. Verus, Kani, and the WASM-IR translation validator do not yet. Building certificate emitters and independent checkers collapses the DO-330 problem from "qualify Z3" (infeasible) to "qualify a small checker" (tractable). This is likely the next post's topic.

{% mermaid() %}
flowchart LR
    untrusted["untrusted prover<br/>Verus · Kani · Z3"]
    cert["proof certificate<br/>SMT unsat core<br/>CBMC trace<br/>checkable artifact"]
    checker["trusted checker<br/>small · auditable<br/>qualified under DO-330"]
    ok([qualified verification])

    untrusted -->|emits| cert
    cert -->|validated by| checker
    checker --> ok

    classDef risky fill:#13161f,stroke:#f87171,color:#e1e4ed;
    classDef transit fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef trusted fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
    classDef endpoint fill:#13161f,stroke:#4ade80,color:#e1e4ed;
    class untrusted risky;
    class cert transit;
    class checker trusted;
    class ok endpoint;
{% end %}

**Aeneas end-to-end.** The rules_lean Bazel wiring is scaffolded but not yet running; hermetic Charon is the missing piece. Tracked at rules_lean#1[^rules-lean-1]. The rules_verus sysroot-handling pattern transfers almost directly.

Twenty-five coordinated issues in the tracker[^rivet-184] raise the floor across the estate — not to reach "done," but to raise the worst cell in the matrix until every project runs every technique its surface supports. Overdoing, applied.

---

## Sources and caveats

Most safety-critical software standards — DO-178C and its supplements, ISO 26262, IEC 61508, IEC 62304, IEC 60880, EN 50128 — are published by standards bodies (RTCA, EUROCAE, ISO, IEC, CENELEC) behind per-copy paywalls. I cannot quote them verbatim. Claims about those standards above are backed either by freely available primary sources (NASA standards, ECSS PDFs, NASA Langley materials, peer-reviewed papers) or by named secondary interpretations from qualified vendors and consultants (LDRA, AdaCore, AFuzion, Parasoft, TÜV SÜD, Visure, Rapita, Military Embedded Systems). Each footnote below flags its tier inline.

[^rivet-184]: pulseengine/rivet issue #184 — *Tracking: pulseengine-wide V&V coverage initiative*. [github.com/pulseengine/rivet/issues/184](https://github.com/pulseengine/rivet/issues/184). Live roadmap for the 25 coordinated adoption issues.

[^rules-lean-1]: pulseengine/rules_lean issue #1 — *Finish Aeneas end-to-end pipeline*. [github.com/pulseengine/rules_lean/issues/1](https://github.com/pulseengine/rules_lean/issues/1). Tracking issue for hermetic Charon wiring.

[^nasa-std-8719]: NASA — *NASA-STD-8719.13 Software Safety Standard*. [standards.nasa.gov](https://standards.nasa.gov/standard/NASA/NASA-STD-871913). Primary (open access — "cleared for public accessibility on the internet").

[^ecss-80c]: European Cooperation for Space Standardization — *ECSS-Q-ST-80C Rev.2 Software Product Assurance*, 30 April 2025. [Direct PDF](https://ecss.nl/wp-content/uploads/2025/05/ECSS-Q-ST-80C-Rev.2(30April2025).pdf). Primary (open access; ECSS license-agreement registration required but free).

[^nasa-langley-do333]: NASA Langley Research Center — *DO-333 Case Studies* overview page. [shemesh.larc.nasa.gov/fm/DO-333-case-studies.html](https://shemesh.larc.nasa.gov/fm/DO-333-case-studies.html). Primary (open access). NASA interpretation of DO-333, not DO-333 itself.

[^nasa-cr-2014]: Darren Cofer and Steven Miller — *Formal Methods Case Studies for DO-333*. NASA/CR-2014-218244, April 2014. [NTRS](https://ntrs.nasa.gov/citations/20140004055). Primary (open access). The reference case-study report for DO-333 practice.

[^mdpi-do333]: Yang et al. — *Formal Analysis and Verification of Airborne Software Based on DO-333*. MDPI Electronics 9(2):327, 2020. Peer-reviewed. [Open access](https://www.mdpi.com/2079-9292/9/2/327).

[^ldra-do332]: LDRA — *DO-332 Supplement guide*. [ldra.com/do-332](https://ldra.com/do-332/). Secondary (interpretation of paywalled RTCA DO-332).

[^ldra-26262]: LDRA — *ISO 26262 guide*. [ldra.com/iso-26262](https://ldra.com/iso-26262/). Secondary (interpretation of paywalled ISO 26262).

[^ldra-61508]: LDRA — *IEC 61508 guide*. [ldra.com/iec-61508](https://ldra.com/iec-61508/). Secondary (interpretation of paywalled IEC 61508).

[^adacore-en50128]: AdaCore — *EN 50128 compliance*. [adacore.com/industries/rail/en50128](https://www.adacore.com/industries/rail/en50128). Secondary (interpretation of paywalled CENELEC EN 50128).

[^afuzion-do332]: AFuzion — *DO-332 Introduction*. [afuzion.com/do-332-introduction-object-oriented-technology](https://afuzion.com/do-332-introduction-object-oriented-technology/). Secondary.

[^afuzion-do330]: AFuzion — *DO-330 Introduction — Tool Qualification*. [afuzion.com/do-330-introduction-tool-qualification](https://afuzion.com/do-330-introduction-tool-qualification/). Secondary.

[^visure-do333]: Visure Solutions — *DO-333 guide*. [visuresolutions.com/aerospace-and-defense/do-333](https://visuresolutions.com/aerospace-and-defense/do-333/). Secondary.

[^tuv-61508]: TÜV SÜD — *IEC 61508 Functional Safety*. [tuvsud.com/en-us/services/functional-safety/iec-61508](https://www.tuvsud.com/en-us/services/functional-safety/iec-61508). Secondary.

[^milemb-do332]: Military Embedded Systems — *DO-332, the Liskov Substitution Principle, and local type consistency ramp up DO-178 certification*. [militaryembedded.com](https://militaryembedded.com/avionics/safety-certification/do-332-liskov-consistency-ramp-do-178-certification). Secondary.

[^rapita-do332]: Rapita Systems — *DO-332 overview*. [rapitasystems.com/do-332](https://www.rapitasystems.com/do-332). Secondary.

[^parasoft-26262]: Parasoft — *ISO 26262 and ASIL requirements*. [parasoft.com/learning-center/iso-26262](https://www.parasoft.com/learning-center/iso-26262/what-is/). Secondary.

[^en50128-academia]: *The new CENELEC EN 50128 and the use of formal method* (academia.edu preprint). [Open access](https://www.academia.edu/143234284/The_new_CENELEC_EN_50128_and_the_usedof_formal_method). Peer-community preprint; supports the claim that EN 50128:2011 treats formal proof as highly recommended at SIL 3/4.

[^nasa-cr-2017]: NASA — *Formal Methods Tool Qualification*. NASA/CR-2017-219371. [Open PDF](https://shemesh.larc.nasa.gov/fm/FMinCert/NASA-CR-2017-219371.pdf). Primary (open access). Source of the Check-It / Kind 2 pattern referenced in this post.

[^aeneas-paper]: Son Ho and Jonathan Protzenko — *Aeneas: Rust Verification by Functional Translation*. ICFP 2022. [arXiv 2206.07185](https://arxiv.org/abs/2206.07185). Primary (open access).
