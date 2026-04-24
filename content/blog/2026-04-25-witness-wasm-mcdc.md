+++
title = "witness — MC/DC for the WebAssembly component model"
description = "The variant-pruning post argued that MC/DC on AI-authored Rust is tractable at Wasm level. This post is the tool: witness instruments a Wasm module, runs a test harness, emits a branch-coverage report, and composes with rivet and sigil for the full evidence chain. v0.1 today, Check-It-pattern qualification on the roadmap."
date = 2026-04-25
draft = true
[taxonomies]
tags = ["verification", "wasm", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
The variant-pruning post argued that MC/DC-for-Rust becomes tractable when you measure at the WebAssembly level rather than the source level — the pattern-matching problem dissolves once code is lowered to `br_if` and `br_table`, the instruction set is small and formally specified, and coverage describes what actually ships. *witness* is the instrument that makes the argument empirical. It instruments a Wasm module, runs the test harness you already have, and emits a branch-coverage report that rivet can read as requirement-to-test evidence and sigil can carry in its attestation bundle. When Rust-level MC/DC lands via the Ferrous / DLR work, witness composes with it rather than competing: two measurement levels, two sets of blind spots, one additive argument.
{% end %}

<!--
TODO (Ralf): before shipping, update the insight + roadmap sections to reflect
what actually lands in v0.1. The skeleton below is written to read correctly
whether the tool is just-shipped or about-to-ship; when v0.1 is in-hand, prune
the "target state" hedging and name the concrete repo + install story.
-->

## Why another coverage tool

I argued the case across the prior two posts:

- [Spec-driven development is half the loop](/blog/spec-driven-development-is-half-the-loop/) framed the pattern — oracle-gated agents downstream of the spec, mechanical instruments at every layer, MBSE driving the build.
- [MC/DC for AI-authored Rust is tractable — the variant-pruning argument](/blog/variant-pruning-rust-mcdc/) argued that five layers of variant pruning (requirements → cargo features → cfg → type system → match arms) collapse the MC/DC coverage burden to what a single shipped variant actually exposes, and that at the Wasm level the hardest part of the Ferrous/DLR mapping problem (Rust pattern matching → MC/DC decisions) has already resolved before measurement begins.

Both posts asked a question the blog cannot answer: is there a tool? Until now, no. This post is the tool.

## What witness does

Point it at a Wasm module and a test-runner command:

```sh
witness instrument app.wasm -o app.instrumented.wasm
witness run --harness "cargo test --target wasm32-wasi" --module app.instrumented.wasm
witness report
```

The instrumentation step rewrites the Wasm to emit a counter at every `br_if`, `br_table`, and `if` instruction. The run step executes the test harness against the instrumented module and collects the counter values. The report step produces a branch-coverage summary keyed to (module, function, offset), with source-level mapping when DWARF-in-Wasm or the name section is present.

That is v0.1. It is not MC/DC in the strict condition-by-condition sense yet. It is branch coverage with an MC/DC-shaped roadmap.

## v0.1 — v1.0

Honest incremental scope:

| Version | What it does | Status |
|---|---|---|
| v0.1 | Branch coverage on Wasm at the decision level. Strict per-`br_if` / per-`br_table` counting. | *TODO: fill in actual status — shipping / in PR / planned* |
| v0.2 | MC/DC condition decomposition when DWARF is present. Groups related `br_if` sequences back into source-level decisions. | Planned |
| v0.3 | rivet integration. Coverage report emits as an in-toto predicate that rivet can link to requirements and sigil can carry. | Planned |
| v0.4 | Variant-aware scope. Post-cfg, post-meld, post-loom measurement points — each one a selectable instrumentation target. | Planned |
| v1.0 | Check-It qualification artifact. Coverage attestation that a small trusted checker can validate, collapsing DO-330 qualification from *"qualify witness"* to *"qualify the checker."* | Planned |

Each step fills a specific gap, and each step can ship independently. Don't wait for v1.0 to get value — v0.1 already produces the branch-coverage evidence the variant-pruning argument depends on.

## The hard problem — decision granularity at Wasm level

Short-circuit evaluation at Rust source (`a && b && c`) compiles to three `br_if` instructions in the emitted Wasm. MC/DC says *"each condition independently affects the decision outcome."* Two honest interpretations:

- **Strict**: each `br_if` is its own decision. Easy to measure, easy to qualify; loses the source-level condition grouping.
- **Reconstructed**: group the sequence of related `br_if`s back into the source-level decision and measure MC/DC over the reconstruction. Harder; needs DWARF-in-Wasm or explicit compiler hints.

v0.1 reports strict coverage only. v0.2 adds DWARF-informed reconstruction with strict as the fallback when DWARF is absent. The definition — exactly how the reconstructed groups are formed, and what invariants the grouping preserves — is worth a short paper. The tool implementation forces you to pick; the paper explains why this pick is the right one.

## Why this does not make Rust-level MC/DC obsolete

Resistance is futile — we adopt both. The overdo principle from [Overdoing the verification chain](/blog/overdoing-the-verification-chain/) applies here at the coverage layer:

- **Rust-level MC/DC** (Ferrous / DLR, when it ships under the 2026 Rust Project Goal) measures decisions at the *source*. Its blind spot is compiler rearrangement — what the compiler emits might have different branches than what the source expresses.
- **witness** measures decisions at the *post-compile Wasm*. Its blind spot is the source-level intent — a condition that expresses a requirement clearly at source might be split into multiple Wasm-level branches with no obvious unit.
- **Translation validation** (loom's Z3 TV on Wasm-IR transformations) bridges the two levels. A proof at the source holds at the Wasm if TV discharges the transformation, so coverage at either level stands in for the other when needed.

Two measurement levels, two blind spots, one additive evidence chain. The same dossier discipline DO-178C has accepted since 1992 — source-level coverage *and* object-code coverage — applies directly. Wasm is the new post-preprocessor level; rustc → Wasm is the compilation step; post-synth machine code is the object code. Witness fills the middle.

## How it composes with the rest of the stack

- **rivet** reads witness reports as test-to-requirement coverage evidence. `rivet validate` can now report *"requirement REQ-N has no test exercising decision D at offset O"* — a new failure class that names uncovered branches specifically.
- **sigil** carries witness reports as in-toto coverage predicates in the attestation bundle (once sigil composes upstream predicates; see the SDD post's note on sigil's transformation-attestation types).
- **loom** emits the post-optimization Wasm that witness measures; loom's translation validation is what makes "coverage on optimized Wasm" a valid stand-in for "coverage on pre-optimization Wasm."
- **meld** fuses components; witness can measure coverage on the fused module or on individual components before fusion.
- **kiln** (or any other Wasm runtime) executes the instrumented module during the test run.
- **spar** — architecture-level. Not directly involved in coverage measurement, but the variant selected at the spar / rivet layer determines which Wasm is produced, which determines what witness measures.

Coverage for AI-authored code is not a one-tool problem. It is a pipeline problem. Each tool owns a narrow mechanical check; the composition is what the audit trail holds.

## Open questions

- **DWARF-in-Wasm maturity.** The spec exists; tooling is uneven across compilers. rustc emits usable DWARF for Wasm targets; Go does partial; AssemblyScript does not. v0.2's reconstruction quality depends on how good the DWARF is.
- **Loom-TV interaction.** When loom optimizes the Wasm, the CFG rearranges. Coverage at pre-loom and post-loom Wasm may disagree. That's arguably correct — you want coverage on what ships — but it needs a careful story for the audit.
- **Decision-granularity formal definition.** Named above; the paper I owe.
- **Component model semantics.** Multi-component Wasm has cross-component calls (`call_indirect`, imports / exports). Whether coverage across components counts as a single argument or separate arguments-per-component is an audit question, not just a technical one.

Honest v0.1 does not solve these. Honest v1.0 does.

## What this unlocks

With witness running against the PulseEngine codebase, the variant-pruning argument stops being prose and becomes a report. The claim *"MC/DC-for-Rust becomes tractable under multi-layer variant management"* becomes a concrete measurement: here is the `f_1 · f_2 · f_3 · f_4 · N_max` scope for variant V, here is the coverage report for V, here is the delta when V changes. The audit dossier has numbers, not just argument.

That is the point of shipping the tool. Arguments without measurements age poorly in safety-critical contexts. Measurements outlive the argument that motivated them.

---

## Sources

<!-- Footnote placeholders - fill in as content matures before shipping -->

---

*This post is part of [PulseEngine](/) — a formally verified WebAssembly Component Model engine for safety-critical systems. Prior posts in the arc: [Formal verification just became practical](/blog/formal-verification-ai-agents/), [What comes after test suites](/blog/what-comes-after-test-suites/), [Spec-driven development is half the loop](/blog/spec-driven-development-is-half-the-loop/), [MC/DC for AI-authored Rust is tractable — the variant-pruning argument](/blog/variant-pruning-rust-mcdc/).*
