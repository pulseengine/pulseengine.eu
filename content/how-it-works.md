+++
title = "How it works"
description = "One path from a system-architecture model to signed code running on hardware — and how the PulseEngine tools compose along it. The Projects page shows the parts; this shows the flow."
template = "how-it-works.html"
+++

PulseEngine is not a single program. It's a set of small, independent tools —
each doing one job in the life of a safety-critical WebAssembly component, and
each independently verifiable. The [Projects](@/projects/_index.md) page lays out
the parts by role. This page shows the **flow**: how one thing travels from a
system-architecture model, through build and verification, to signed artifacts
running on a real target.

{% note(kind="tip") %}
Everything here is **work in progress**, at varying maturity. The tools compose
in principle and in the worked examples below — this is not a one-button
production pipeline, and *"verified"* always means **specific properties,
machine-checked**, never a blanket guarantee. Where a seam is still manual or a
stage is early, we say so.
{% end %}

## The pipeline at a glance

{% mermaid() %}
flowchart TB
  spar["spar · design<br/>AADL · SysML · CAN/DBC"]
  code["component code<br/>Rust → wasm"]
  meld["meld · fuse"]
  loom["loom · optimize"]
  synth["synth · transcode → ARM / RISC-V"]
  sigil["sigil · sign · SLSA · SBOM"]
  run["kiln — interpreter &amp; runtime<br/>gale — RTOS primitives"]
  apps["relay · wohl<br/>applications"]
  hw["jess<br/>HIL → real drone → flight"]
  rivet[("rivet · traceability spine")]
  verify{{"Verify gate<br/>Verus · Rocq · Lean · scry · witness · ordeal"}}

  spar -->|WIT · skeletons · proof obligations| code
  code --> meld --> loom --> synth --> sigil --> run --> apps --> hw
  verify -. gates .-> meld
  verify -. gates .-> synth
  spar -. typed artifacts .-> rivet
  verify -. evidence .-> rivet
  apps -. evidence .-> rivet

  classDef spine fill:#242836,stroke:#fbbf24,color:#e1e4ed;
  classDef gate fill:#242836,stroke:#4ade80,color:#e1e4ed;
  class rivet spine
  class verify gate
{% end %}

Two things run *across* the flow rather than sitting in it:

- **rivet** is the traceability spine (amber): every stage's inputs, decisions,
  and evidence are typed artifacts it links into a V-model and re-checks on every
  commit — a broken link fails the build.
- **Verify** is a gate, not a stage (green): several independent techniques run in
  CI and block the build when the evidence isn't there.

## Following the flow

### 1 · Design — spar

[spar](https://github.com/pulseengine/spar) ingests AADL v2.3, SysML v2, and
CAN/DBC into one semantic model, runs safety analysis and TSN timing bounds, and
then *generates* what everything downstream starts from: WIT interfaces, Rust
skeletons, Lean 4 proof obligations, and rivet artifacts. The design is checked
before any code exists.

### 2 · Trace — rivet (the spine)

[rivet](https://github.com/pulseengine/rivet) is a schema-driven SDLC artifact
manager: requirement → architecture → design → code → test, with built-in schemas
for ISO 26262, DO-178C, IEC 61508, EN 50128, IEC 62304, the EU AI Act, and STPA /
STPA-Sec / STPA-AI. It imports spar's models and CI's test results, validates the
whole V on every commit, and generates compliance reports each release. It's the
thread every other tool hangs its evidence on.

### 3 · Build — meld → loom → synth

Component code compiles to wasm; [meld](https://github.com/pulseengine/meld)
fuses multiple components into one module;
[loom](https://github.com/pulseengine/loom) optimizes it and is
**translation-validated** — the optimization is *checked*, not trusted;
[synth](https://github.com/pulseengine/synth) transcodes wasm to native ARM
Cortex-M and RISC-V through program synthesis.

{{ pipeline() }}

### 4 · Verify — the gate

Not one technique but several, deliberately independent, so no single blind spot
is shared across them:

- **Verus · Rocq · Lean 4** — deductive proof on the Rust *source*: SMT/Z3,
  theorem proving, and scheduling theory.
- **[scry](https://github.com/pulseengine/scry)** — sound abstract interpretation
  over the fused *wasm* (the third DO-333 formal-methods leg).
- **[witness](https://github.com/pulseengine/witness)** — MC/DC structural
  coverage on the *compiled* wasm: it measures what actually ships.
- **[ordeal](https://github.com/pulseengine/ordeal)** underwrites the deductive
  layer itself — a certificate-checked SMT solver whose untrusted core is paired
  with a formally-verified LRAT checker (the CompCert pattern), so even the
  solver's answers carry evidence a checker can re-verify.

Proof and abstract interpretation cover all inputs *in principle*; witness
measures the bytecode that actually ships. No single technique spans both — which
is the point. (For an honest look at the limits, see
[this eval](@/blog/2026-07-09-honest-failure-by-construction.md).)

### 5 · Attest — sigil

[sigil](https://github.com/pulseengine/sigil) signs every artifact and
transformation — embedded signatures, Sigstore keyless, SLSA provenance, SBOM —
so what Verify established stays bound to exactly the bytes that run.

### 6 · Run — kiln · gale

[kiln](https://github.com/pulseengine/kiln) is an interpreter and runtime for
Component-Model wasm (WASI 0.2, with a no_std path for embedded targets).
[gale](https://github.com/pulseengine/gale) provides formally-verified Zephyr RTOS
kernel primitives in Rust (Verus + Rocq), targeting ASIL-D. The same verified
components [run live in a browser](https://pulseengine.github.io/gale/) and
dissolve to a bare-metal Cortex-M3.

### 7 · Integrate — relay · wohl · jess

Applications prove the chain end-to-end.
[relay](https://github.com/pulseengine/relay) is flight software — a verified
control cascade — built as WebAssembly components;
[wohl](https://github.com/pulseengine/wohl) is home supervision.
[jess](https://github.com/pulseengine/jess) is where software meets metal: it
brings the falcon flight stack from simulation, through hardware-in-the-loop, onto
a real drone.

### Across all of it — the agent loop

rivet's MCP tools, the [mcp](https://github.com/pulseengine/mcp) framework,
[agora](https://github.com/pulseengine/agora) (real-time agent coordination on a
signed, traceable fact log), and [temper](https://github.com/pulseengine/temper)
(a GitHub App that holds every repo to the same standards) let AI agents write
code *and* keep the traceability and verification current as they go — never as an
afterthought.

## A worked example

Two real repositories carry the whole thing end-to-end today.

**Build + verify + trace — [example-kvs](https://github.com/pulseengine/example-kvs).**
It takes a real third-party specification — Eclipse S-CORE's persistency
key-value store — and runs it through the full stack: rivet typed artifacts, a
spar AADL model, a WIT contract, a witness MC/DC harness, a sigil release
manifest, and an artifact-driven verification gate. It's the shortest way to watch
the pieces interlock on something we didn't invent. (And
[playground-eclipse-score](https://github.com/pulseengine/playground-eclipse-score)
converts **2,985** of that project's requirements into rivet's typed YAML —
traceability at real scale.)

**Run + hardware — falcon → jess.** relay's falcon flight stack — an Invariant-EKF
estimator, geometric SE(3) attitude control, an ADRC inner loop — flies in Gazebo
SITL and runs bare-metal on an emulated Cortex-M. gale runs the same verified
primitives in the browser and dissolves them to a Cortex-M3.
[jess](https://github.com/pulseengine/jess) closes the loop onto real hardware:
HIL, then a real drone, then flight.

## Where the seams still show

Being honest about maturity is part of the method:

- The stages are **independent tools at different maturity** — rivet, spar,
  witness, and sigil are the most exercised; kiln and synth are earlier.
- **"Composes"** means *demonstrated in the worked examples and in CI*, not a
  single turnkey command.
- Every **"verified"** claim is a specific, machine-checked property — proven,
  measured, or still manual. We keep a running honest account of which is which;
  each repo's README and the [blog](@/blog/_index.md) track it.

## See also

- [Projects](@/projects/_index.md) — the parts, by role, as an interactive map.
- [Reports](@/reports/_index.md) — live compliance and coverage output from rivet
  and witness.
- [GitHub](https://github.com/pulseengine) — every repository named above.
