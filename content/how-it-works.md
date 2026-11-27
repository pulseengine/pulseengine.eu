+++
title = "How it works"
description = "One path from a system-architecture model to signed code running on hardware — the PulseEngine tools that compose along it, stage by stage, and the projects built on top."
template = "how-it-works.html"
aliases = ["/projects/"]
+++

PulseEngine is a set of small, independent tools. Each does one job in the life
of a safety-critical WebAssembly component and is independently usable and
checkable. This
page follows one artifact from a system-architecture model through build and
verification to signed code on a real target, and lists for each stage its tools.

{% <note kind="tip"> %}
Everything here is **work in progress**. The tools compose in the worked
examples below and in CI, not as a one-button production pipeline. Every
*"verified"* claim names a specific property; it is never a blanket guarantee.
Each repo's README and the [blog](@/blog/_index.md) keep a running account of
which claims are machine-proven, bounded, tested or still manual.
{% </note> %}

## Three views of one factory

The same four tools, looked at from three angles. Switch between them; the boxes
do not move, only what is said about them.

<!-- factory-views-component -->

Inside each view, every edge means one thing. relay, wohl and jess are not in the
views: they are products built with PulseEngine, and they have their own section
below.

## Following the flow

<nav class="stage-key" aria-label="Stages">
<a href="#design">Design</a><a href="#trace">Trace</a><a href="#build">Build</a><a href="#verify">Verify</a><a href="#ship">Ship</a><a href="#gate">Gate</a><a href="#run">Run</a>
</nav>

### 1 · Design — spar {#design}

[spar](https://github.com/pulseengine/spar) is a compiler for system-architecture
models. It ingests AADL v2.3, SysML v2 (partial), and CAN/DBC into one semantic
model, runs pluggable analysis passes (safety analysis, ARINC 653 partitioning,
and TSN timing bounds) plus a deployment solver, and then *generates* what
everything downstream starts from: WIT interfaces, Rust skeletons, Lean 4
proof-obligation skeletons (theorem statements to discharge downstream), and
rivet artifacts. It also renders SVG, ships an LSP server and a
[VS Code extension](https://marketplace.visualstudio.com/items?itemName=pulseengine.spar-aadl),
and compiles to a single WebAssembly component. The design is checked before any
code exists.

<div class="tools tools--design">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/spar" rel="noopener">spar</a><p class="tool__does">Architecture models (AADL, SysML v2 partial, CAN/DBC) in; analyses, WIT, Rust and Lean 4 skeletons and rivet artifacts out.</p><p class="tool__maturity"><a href="https://github.com/pulseengine/spar#readme" rel="noopener">Status: see README</a></p></div>
</div>

### 2 · Trace — rivet (the spine) {#trace}

[rivet](https://github.com/pulseengine/rivet) is a schema-driven SDLC artifact
manager: requirement → architecture → design → code → test, with built-in schemas
(schemas, not certification) for ISO 26262, ISO/PAS 8800, ASPICE, DO-178C,
IEC 61508, EN 50128, IEC 62304, SOTIF, the EU AI Act, STPA / STPA-Sec / STPA-AI
and GSN safety cases, plus cross-domain bridge schemas. It imports spar's models
and CI's test results, validates the traceability integrity of the whole V on
every commit (broken links fail the build), and generates compliance reports
each release ([Reports](@/reports/_index.md)).

<div class="tools tools--trace">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/rivet" rel="noopener">rivet</a><p class="tool__does">Typed, schema-checked traceability across the V; validates on every commit and generates compliance reports per release.</p><p class="tool__maturity"><a href="https://github.com/pulseengine/rivet#readme" rel="noopener">Status: see README</a></p></div>
</div>

### 3 · Build — meld → loom → synth {#build}

Component code compiles to wasm. [meld](https://github.com/pulseengine/meld)
fuses multiple components into one module,
[loom](https://github.com/pulseengine/loom) optimizes it (multi-pass, via
Cranelift ISLE), and [synth](https://github.com/pulseengine/synth) transcodes it
toward native ARM and RISC-V; it refuses constructs it has no lowering for.

In loom, translation validation is on by default: after each pass, a changed
function is reverted unless Z3 (or ordeal) proves it equivalent within loom's model, or it is listed
in loom's trust ledger. A function outside the model is left unchanged, and the
transforms kept without a proof are listed by reason in that ledger.

<div class="tools tools--build">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/meld" rel="noopener">meld</a><p class="tool__does">Fuses multiple WebAssembly components into a single module.</p><p class="tool__maturity"><a href="https://github.com/pulseengine/meld#readme" rel="noopener">Status: see README</a></p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/loom" rel="noopener">loom</a><p class="tool__does">Multi-pass optimizer for the fused module.</p><p class="tool__maturity"><a href="https://github.com/pulseengine/loom#readme" rel="noopener">Status: see README</a></p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/synth" rel="noopener">synth</a><p class="tool__does">Transcodes wasm toward native ARM and RISC-V.</p><p class="tool__maturity"><a href="https://github.com/pulseengine/synth#readme" rel="noopener">Status: see README</a></p></div>
</div>

### 4 · Verify — the gate on the code {#verify}

Verification uses several deliberately independent techniques, so a blind spot
in one is less likely to be shared by the others:

- **Verus · Rocq · Lean 4** — deductive proof. **Verus** checks requires/ensures
  contracts on Rust source via SMT/Z3; functions marked `external_body` are
  trusted, not checked. **Rocq** machine-checks invariants. **Lean 4**
  proves results about models of the domain. Some
  legs prove the Rust source directly; others prove a hand-transcribed model, and
  where they do, that model-to-code link is a trusted, human-checked step (see
  [the maturity series](/tags/how-it-works/)).
- **[scry](https://github.com/pulseengine/scry)**: abstract interpretation
  designed to be sound, over the fused *wasm* (the abstract-interpretation leg of DO-333), computing
  invariants intended to hold for all executions. It is designed to feed loom.
- **[witness](https://github.com/pulseengine/witness)** — MC/DC-style structural
  coverage on the *compiled* wasm: it measures the bytecode that actually ships
  (source-level mapping rests on a stated DWARF-correctness assumption).
- **[ordeal](https://github.com/pulseengine/ordeal)** re-checks part of the
  deductive layer (the bit-vector obligations Verus emits) and is synth's
  translation-validation engine. It is a pure-Rust, wasm-native QF_BV SMT solver
  whose untrusted core is paired with an LRAT (RUP) checker. Each UNSAT answer
  carries an LRAT certificate that the checker re-verifies.

Proof and abstract interpretation cover all inputs *in principle*; witness
measures the bytecode that actually ships. No single technique spans both. How
far each technique reaches differs by project; each project's docs say what is
proven, what is bounded and what is only tested. (For an honest look at the limits, see
[this eval](@/blog/2026-07-09-honest-failure-by-construction.md).)

<div class="tools tools--verify">
<div class="tool"><span class="tool__name">Verus · Rocq · Lean 4</span><p class="tool__does">Deductive proof, wired into Bazel by <a href="https://github.com/pulseengine/rules_verus" rel="noopener">rules_verus</a>, <a href="https://github.com/pulseengine/rules_rocq_rust" rel="noopener">rules_rocq_rust</a> and <a href="https://github.com/pulseengine/rules_lean" rel="noopener">rules_lean</a>.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/scry" rel="noopener">scry</a><p class="tool__does">Abstract interpretation, designed to be sound, over the fused wasm; designed to feed loom.</p><p class="tool__maturity"><a href="https://github.com/pulseengine/scry#readme" rel="noopener">Status: see README</a></p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/witness" rel="noopener">witness</a><p class="tool__does">MC/DC-style structural coverage on the compiled wasm.</p><p class="tool__maturity"><a href="https://github.com/pulseengine/witness#readme" rel="noopener">Status: see README</a></p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/ordeal" rel="noopener">ordeal</a><p class="tool__does">Certificate-checked SMT solver: untrusted core, checked LRAT certificates.</p><p class="tool__maturity"><a href="https://github.com/pulseengine/ordeal#readme" rel="noopener">Status: see README</a></p></div>
</div>

### 5 · Ship — sigil · varve {#ship}

[sigil](https://github.com/pulseengine/sigil) can sign artifacts and
transformations (embedded signatures, Sigstore keyless or Ed25519, SLSA
provenance), so each stage's output, and the attestations about it, are bound to
exact bytes by signature. sigil's embedded-signature lineage traces to Frank
Denis's [wasmsign2](https://github.com/wasm-signatures/wasmsign2) (MIT): we
started from it and have diverged since, but the original DNA is his.

**The two bands read in opposite directions.**
In the Build, verify, release view, sigil's band runs *below* the boxes because
it acts on what flows through it, attesting the artifacts the pipeline produces.
In the Use it view, [varve](https://github.com/pulseengine/varve)'s band runs
*above* them because it delivers the boxes themselves: the exact meld, loom, synth and kiln binaries a build ran,
as one signed, dated, digest-pinned layer. sigil answers *"is this component what
it claims to be?"*, and varve answers *"are the tools that produced it the ones
you think, on every machine and every runner?"* varve is a packaging line outside
the assembly line; it makes "which pipeline ran" answerable.

A per-project `varve.toml` names a realm and a layer; the realm supplies both the
registry and the trust root, so no environment variable is involved. Outside a
pinned project a shim **refuses**, naming the missing `varve.toml` (exit 1),
rather than silently running whatever is on PATH. Anti-rollback is
offline after the first install (a fresh consumer has no high-water mark yet): an
older layer is rejected by a check that needs no network and no clock.

Realms compose:
`pulseengine` carries PulseEngine's own tools, `pulseengine-wasm` carries the
upstream component-model tools, and `covalent` holds no tools and only asserts
the two belong together. Each included layer is verified against its own realm's
root, so a composing realm asserts a pairing and cannot widen trust.

<div class="tools tools--ship">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/sigil" rel="noopener">sigil</a><p class="tool__does">Signs and attests artifacts and transformations: embedded signatures, Sigstore keyless or Ed25519, SLSA provenance.</p><p class="tool__maturity"><a href="https://github.com/pulseengine/sigil#readme" rel="noopener">Status: see README</a></p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/varve" rel="noopener">varve</a><p class="tool__does">Delivers the pinned, signed layer of tools: the exact binaries a build ran, signed, dated and digest-pinned.</p><p class="tool__maturity"><a href="https://github.com/pulseengine/varve#readme" rel="noopener">Status: see README</a></p></div>
</div>

### 6 · Gate — jig · plant · sieve {#gate}

Every stage above reports through CI, so the CI checks are evidence too. This
stage checks that those checks can fail.
[plant](https://github.com/pulseengine/plant) runs each check against an input it
must reject, a planted bad input, and fails when the check stays green.
[jig](https://github.com/pulseengine/jig) is the shared CI baseline for
pulseengine repositories: reusable GitHub Actions workflows, pinned by commit
SHA, and the Rust checker they run — a fail-closed fork guard, a lockfile and
audit check, an action-pin check, and a required verdict that is red on any
failure, cancellation or unselected skip. jig runs its own plant controls.
[sieve](https://github.com/pulseengine/sieve) decides per pull request which heavy
CI jobs a change touches; when it is unsure, everything runs. The false-skip
controls against sieve live in plant, by design: the decider and its check live
apart.

<div class="tools tools--gate">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/plant" rel="noopener">plant</a><p class="tool__does">Runs each CI check against a planted bad input and fails when the check stays green.</p><p class="tool__maturity"><a href="https://github.com/pulseengine/plant#readme" rel="noopener">Status: see README</a></p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/jig" rel="noopener">jig</a><p class="tool__does">Shared CI baseline: reusable workflows pinned by SHA, plus fork guard, lockfile audit, action pins and a required verdict.</p><p class="tool__maturity"><a href="https://github.com/pulseengine/jig#readme" rel="noopener">Status: see README</a></p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/sieve" rel="noopener">sieve</a><p class="tool__does">Shared CI path classifier: picks which heavy jobs a pull request touches; unsure means everything runs.</p><p class="tool__maturity"><a href="https://github.com/pulseengine/sieve#readme" rel="noopener">Status: see README</a></p></div>
</div>

### 7 · Run — kiln · gale {#run}

[kiln](https://github.com/pulseengine/kiln) is an interpreter and runtime for
Component-Model wasm.

[gale](https://github.com/pulseengine/gale)'s North Star is **gust**, which its
roadmap calls "a general multi-tenant verified OS": the goal is mutually-distrusting
components, MPU-isolated over one Rust trusted base. gale provides Rust
replacements, with Verus contracts on the source, for **Zephyr** RTOS kernel
primitives, as the *supply chain* the OS composes from.

<div class="tools tools--run">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/kiln" rel="noopener">kiln</a><p class="tool__does">Interpreter and runtime for Component-Model wasm.</p><p class="tool__maturity"><a href="https://github.com/pulseengine/kiln#readme" rel="noopener">Status: see README</a></p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/gale" rel="noopener">gale</a><p class="tool__does">Rust replacements for Zephyr kernel primitives, with Verus contracts on the source; its North Star is gust, which its roadmap calls "a general multi-tenant verified OS".</p><p class="tool__maturity"><a href="https://github.com/pulseengine/gale#readme" rel="noopener">Status: see README</a></p></div>
</div>

## Built on the base — relay · wohl · jess {#built}

These are products built with PulseEngine, outside the pipeline. Each is where
the methodology meets a real domain; each card links its README for status.

<div class="tools tools--built">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/relay" rel="noopener">relay</a><p class="tool__domain">flight software</p><p class="tool__does">Flight-software components for WebAssembly, inspired by NASA's cFS and reimagined as generic components, with formal proofs of specific safety properties.</p><p class="tool__maturity"><a href="https://github.com/pulseengine/relay#readme" rel="noopener">Status: see README</a></p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/wohl" rel="noopener">wohl</a><p class="tool__domain">home supervision</p><p class="tool__does">Home supervision: sensor nodes send CCSDS packets to a hub that runs Kani-checked monitor components.</p><p class="tool__maturity"><a href="https://github.com/pulseengine/wohl#readme" rel="noopener">Status: see README</a></p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/jess" rel="noopener">jess</a><p class="tool__domain">hardware integration</p><p class="tool__does">Where software meets metal: an evidence-as-code hub for taking relay's falcon flight stack from simulation, through hardware-in-the-loop, toward a real drone, tracked in rivet the whole way.</p><p class="tool__maturity"><a href="https://github.com/pulseengine/jess#readme" rel="noopener">Status: see README</a></p></div>
</div>

## Worked examples

These repositories show the chain on real inputs; each README says which layers
are live.

**Build + verify + trace — [example-kvs](https://github.com/pulseengine/example-kvs).**
It takes a real third-party specification, Eclipse S-CORE's persistency
key-value store, and expresses it through the stack, layer by layer: rivet typed
artifacts, a spar AADL model, a WIT contract that builds against the upstream
code, and a verification gate (`tools/verify.py`) that runs Bazel tests per
artifact. The [maturity series](/tags/how-it-works/) walks which layers are live. (And
[playground-eclipse-score](https://github.com/pulseengine/playground-eclipse-score)
converts Eclipse **safety artifacts** (requirements, architecture, FMEA, and
more) into rivet's typed YAML, testing schema coverage at real scale.)

**Run + hardware — falcon → jess.** relay's falcon flight stack (an Invariant-EKF
estimator, geometric SE(3) attitude control, an ADRC inner loop) flies in Gazebo
SITL; jess takes it from simulation, through hardware-in-the-loop, toward a real
drone. gale's dissolved code also
[runs in a browser](https://pulseengine.github.io/gale/).

## Supporting projects {#supporting}

PulseEngine projects that support the PulseEngine tools: Bazel rules, layers,
examples, and integration tooling.

<div class="tools tools--support">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/temper" rel="noopener">temper</a><p class="tool__domain">repo hardening</p><p class="tool__does">GitHub App that hardens repositories to organizational standards.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/rules_wasm_component" rel="noopener">rules_wasm_component</a><p class="tool__domain">Bazel rules</p><p class="tool__does">Bazel rules for WebAssembly Component Model development with multi-profile builds.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/kapsel" rel="noopener">kapsel</a><p class="tool__domain">Bazel + WASM</p><p class="tool__does">File operations for Bazel builds as a WebAssembly component, growing into a capability shell for AI agents.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/covalent-layers" rel="noopener">covalent-layers</a><p class="tool__domain">layer composition</p><p class="tool__does">A layer that composes the pulseengine and pulseengine-wasm realms.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/example-kvs" rel="noopener">example-kvs</a><p class="tool__domain">example</p><p class="tool__does">Eclipse S-CORE persistency through the PulseEngine stack.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/playground-eclipse-score" rel="noopener">playground-eclipse-score</a><p class="tool__domain">playground</p><p class="tool__does">Eclipse S-CORE typed-traceability playground: sphinx-needs artifacts converted to rivet.</p></div>
</div>

Also: [rules_verus](https://github.com/pulseengine/rules_verus),
[rules_rocq_rust](https://github.com/pulseengine/rules_rocq_rust),
[rules_lean](https://github.com/pulseengine/rules_lean),
[rules_ordeal](https://github.com/pulseengine/rules_ordeal),
[pulseengine-layers](https://github.com/pulseengine/pulseengine-layers),
[wasm-layers](https://github.com/pulseengine/wasm-layers),
[wasm-component-examples](https://github.com/pulseengine/wasm-component-examples).

## Forks & dependencies {#forks}

The PulseEngine GitHub organisation also hosts forks of third-party projects.
These are **not** PulseEngine projects. We do not design, build, or maintain
them.

| Repository | What it is | Upstream |
|---|---|---|
| [z3](https://github.com/pulseengine/z3) | Z3 Theorem Prover | Fork of [Z3Prover/z3](https://github.com/Z3Prover/z3) |
| [z3.rs](https://github.com/pulseengine/z3.rs) | Rust bindings for Z3 | Fork of [prove-rs/z3.rs](https://github.com/prove-rs/z3.rs) |
| [wasmtime](https://github.com/pulseengine/wasmtime) | WebAssembly runtime | Fork of [bytecodealliance/wasmtime](https://github.com/bytecodealliance/wasmtime) |
| [wit-bindgen](https://github.com/pulseengine/wit-bindgen) | WIT binding generator | Fork of [bytecodealliance/wit-bindgen](https://github.com/bytecodealliance/wit-bindgen) |
| [walrus](https://github.com/pulseengine/walrus) | WASM transformation library | Fork of [wasm-bindgen/walrus](https://github.com/wasm-bindgen/walrus) |
| [wasm-tools](https://github.com/pulseengine/wasm-tools) | WASM CLI and libraries | Fork of [bytecodealliance/wasm-tools](https://github.com/bytecodealliance/wasm-tools) |
| [zephyr](https://github.com/pulseengine/zephyr) | Zephyr RTOS | Fork of [zephyrproject-rtos/zephyr](https://github.com/zephyrproject-rtos/zephyr) |
| [picolibc](https://github.com/pulseengine/picolibc) | C library for embedded systems | Fork of [zephyrproject-rtos/picolibc](https://github.com/zephyrproject-rtos/picolibc) |
| [rowan](https://github.com/pulseengine/rowan) | Lossless syntax-tree library | Fork of [rust-analyzer/rowan](https://github.com/rust-analyzer/rowan) |
| [renode-bazel-rules](https://github.com/pulseengine/renode-bazel-rules) | Bazel rules for Renode | Fork of [antmicro/renode-bazel-rules](https://github.com/antmicro/renode-bazel-rules) |
| [bazel-central-registry](https://github.com/pulseengine/bazel-central-registry) | Bazel module registry | Fork of [bazelbuild/bazel-central-registry](https://github.com/bazelbuild/bazel-central-registry) |

## Archived {#archived}

No longer actively maintained; the code remains available:
[agora](https://github.com/pulseengine/agora) (agent coordination),
[glsp-mcp](https://github.com/pulseengine/glsp-mcp) (graphical modeling),
[thrum](https://github.com/pulseengine/thrum) (pipeline orchestrator),
[studio-mcp](https://github.com/pulseengine/studio-mcp) (WindRiver Studio MCP),
[timedate-mcp](https://github.com/pulseengine/timedate-mcp) (time/date MCP),
[wasi-mcp](https://github.com/pulseengine/wasi-mcp) (WASI MCP proposal),
[rules_moonbit](https://github.com/pulseengine/rules_moonbit) (Bazel rules for MoonBit),
[moonbit_checksum_updater](https://github.com/pulseengine/moonbit_checksum_updater).

## See also

- [Timeline](@/timeline.md) — the month-by-month story of how all of this got built,
  from kiln onward.
- [Reports](@/reports/_index.md) — live compliance and coverage output from rivet
  and witness.
- [The honest maturity map](/tags/how-it-works/) — a series of deep dives, tagged
  `how-it-works`.
- [GitHub](https://github.com/pulseengine) — every repository named above.
