+++
title = "Guide"
description = "How PulseEngine's tools work together — from architecture to compliance"
template = "docs-section.html"
sort_by = "weight"
weight = 1
+++

PulseEngine is not one tool. It is a set of tools that solve different parts of the same problem: building safety-critical software where every decision is traceable, every transformation is verified, and the compliance evidence generates itself.

This guide walks through the ecosystem using real examples — how we use these tools to build [relay](https://github.com/pulseengine/relay) (flight software) and [gale](https://github.com/pulseengine/gale) (verified RTOS kernel). Not hypothetical. What we actually do.

## The problem

You are building software that goes into a car, an aircraft, a medical device. Standards require you to show that requirements trace to architecture, architecture traces to design, design traces to tests, and tests trace to evidence. When something changes, the chain must update. When an auditor asks, the evidence must be there.

Today most teams maintain this chain manually — spreadsheets, ALM databases, documents that drift from the code. AI agents are now producing code faster than anyone can update the tracking. The gap between velocity and traceability is growing.

## How the ecosystem closes it

**1. Model the architecture** — [spar](/docs/spar/) parses your system architecture in AADL or SysML v2. Before you write code, it validates scheduling feasibility, resource budgets, latency bounds, connectivity. It generates WIT interfaces and Rust code skeletons from the model. If the architecture is unsound, you know before the first line of implementation.

**2. Build the components** — [rules_wasm_component](https://github.com/pulseengine/rules_wasm_component) builds the WebAssembly components from the generated code via Bazel — hermetic, reproducible, multi-language.

Then [meld](https://github.com/pulseengine/meld) fuses multiple components into a single core module. This is not simple concatenation — it is a five-stage compiler pipeline (parse, resolve, merge, adapt, encode) with its own formal verification:

- **Rocq proofs** — 13,330 lines of Coq across 28 files. 357 closed proofs, zero admitted. The spec layer defines a forward simulation between composed and fused execution. The merge proofs establish that index remapping is injective, complete, and bounded across all six Wasm index spaces. Memory layout is proved sequential and disjoint. The adapter spec proves lift/lower roundtrip for all primitive value types.
- **STPA safety analysis** — losses, hazards, unsafe control actions, controller constraints, and loss scenarios managed as rivet artifacts. The control structure covers the full pipeline: parser, resolver, merger, adapter generator, and encoder.
- **Verus pilot** — SMT verification beginning with the merger's core index operations.

The proof-to-code ratio is 1.62× — more lines of proof than implementation. The [proof status](/docs/meld/proof-status/) documents exactly what is proved, what has placeholder proofs, and what the known model gaps are.

[loom](https://github.com/pulseengine/loom) then optimizes the fused module, [synth](https://github.com/pulseengine/synth) transcodes to native ARM if needed. [sigil](https://github.com/pulseengine/sigil) signs every transformation.

**3. Verify everything** — Not just formal proofs. A verification pyramid with independent layers that reinforce each other. This is how [gale](/docs/gale/) verifies every kernel primitive:

- **Verus** — SMT/Z3 contracts on every public function. Preconditions, postconditions, invariants. All inputs, not a sample.
- **Rocq** — machine-checked proofs of abstract invariants that hold regardless of implementation.
- **Lean 4** — mathematical proofs for scheduling theory, priority ceiling, ring buffer correctness.
- **Kani** — bounded model checking that exhaustively explores reachable state spaces.
- **Differential testing** — the C FFI shims produce identical results to the Verus-verified Rust model. Every module.
- **Property-based testing** — proptest generates random operation sequences and verifies invariants hold.
- **Fuzzing** — adversarial inputs thrown at every kernel primitive.
- **Zephyr upstream suites** — the actual Zephyr test suites pass with gale replacing the original C code.
- **Multi-architecture emulation** — Renode runs tests on Cortex-M4F, M33, and Cortex-R5 hardware models.
- **FFI model equivalence** — proves the boundary between verified Rust and the C interface preserves correctness.

Each layer catches different classes of bugs. Formal proofs catch logical errors. Differential testing catches implementation drift. Fuzzing catches edge cases. Upstream suites catch compatibility regressions. Together they form a verification surface that no single technique achieves alone.

**4. Trace to evidence** — [rivet](/docs/rivet/) manages the traceability chain as YAML files in git. Requirements link to architecture decisions, which link to design, which link to tests, which link to commits. `rivet validate` checks the graph on every commit. A broken link fails the build. No spreadsheets.

**5. Ship compliance** — `rivet export` generates the compliance report as a build artifact. Every release publishes its own evidence. See them live at [/reports/](/reports/). The auditor gets a URL, not a binder.

## How gale uses this

[gale](https://github.com/pulseengine/gale) is the first project built entirely within this ecosystem. It replaces the C kernel primitives of Zephyr RTOS with formally verified Rust — semaphores, mutexes, scheduler, message queues, memory slabs, pipes, condition variables, event flags, polling, timeslicing, and more.

The Zephyr kernel has 51 source files. Gale replaces 19 of them completely, provides verified decision helpers for 4 more, and documents why the remaining 28 are excluded (boot glue, debug infrastructure, hardware drivers — no kernel state mutation, no safety impact).

**How it verifies:**

Each replaced kernel file goes through the full pyramid. Take the semaphore:

- Verus contracts prove give/take preserve count invariants for all inputs
- Rocq proves abstract semaphore properties independent of implementation
- Lean proves priority inheritance correctness mathematically
- Kani exhaustively checks all states for counts up to 20
- Differential tests verify the C FFI shim matches the Rust model exactly
- Proptest generates thousands of random give/take/reset sequences
- Fuzzing throws adversarial inputs at the API
- Zephyr's own `tests/kernel/semaphore` passes with gale replacing the C code
- Renode runs the semaphore test on Cortex-M4F, M33, and Cortex-R5 emulated hardware

This is not "we ran the proofs once." This is layered verification where each technique catches what the others miss.

**How it traces:**

rivet tracks every requirement, design decision, and verification result. The STPA safety analysis — losses, hazards, unsafe control actions, controller constraints, loss scenarios — is managed as rivet artifacts. Every kernel primitive traces from its Zephyr requirement through architecture and design to test evidence.

**The honest status:**

The formal verification tools (Verus, Rocq, Lean, Kani, Miri) do not yet run in CI — they require Bazel + Nix toolchains. The functional tests (cargo test, Zephyr integration, Renode) run on every commit. The [verification honesty assessment](/docs/gale/verification/) documents exactly what is proven, what is tested, and where the gaps are. This is closer to seL4's approach — build the proofs, then build the CI to enforce them — than to claiming everything is continuously verified when it is not.

gale is targeting ASIL-D. The verification infrastructure exists because it has to.

## How relay uses this

[relay](https://github.com/pulseengine/relay) is formally verified flight software inspired by NASA's cFS, reimagined as generic WebAssembly components. It uses the same ecosystem:

- spar models the flight software architecture
- The pipeline builds and signs the components
- Verification runs on every commit
- rivet traces requirements to implementation

relay proves the ecosystem works beyond automotive — the same tools, the same traceability, applied to aerospace.

## Next steps

To understand individual tools in depth:

- **[rivet reference](/docs/rivet/)** — schemas, CLI, architecture, how traceability validation works
- **[spar reference](/docs/spar/)** — AADL compliance, analysis passes, VS Code integration
- **[gale reference](/docs/gale/)** — kernel coverage, verification status, safety analysis

To see it in action:

- **[Blog](/blog/)** — deep dives into verification, traceability, and design decisions
- **[Compliance reports](/reports/)** — live evidence generated by rivet on every release
- **[GitHub](https://github.com/pulseengine)** — all source code
