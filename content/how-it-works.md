+++
title = "How it works"
description = "One path from a system-architecture model to signed code running on hardware — the PulseEngine tools that compose along it, stage by stage, and the projects built on top."
template = "how-it-works.html"
aliases = ["/projects/"]
+++

PulseEngine is a set of small, independent tools. Each does one job in the life
of a safety-critical WebAssembly component and is independently verifiable. This
page follows one artifact from a system-architecture model through build and
verification to signed code on a real target, and lists for each stage its tools
and how mature each one is.

{% <note kind="tip"> %}
Everything here is **work in progress**, at varying maturity. The tools compose
in the worked examples below and in CI, not as a one-button production
pipeline. Every *"verified"* claim names a specific property and says whether it
is machine-proven, bounded, tested or still manual; it is never a blanket
guarantee. Where a seam is still manual or a stage is early, we say so.
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
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/spar" rel="noopener">spar</a><p class="tool__does">Architecture models (AADL, SysML v2 partial, CAN/DBC) in; analyses, WIT, Rust and Lean 4 skeletons and rivet artifacts out.</p><p class="tool__maturity">Lean proofs of the scheduling and network-calculus theory are fully discharged; they cover the theory, not the Rust code. TSN bounds are also cross-checked against the panco reference.</p></div>
</div>

### 2 · Trace — rivet (the spine) {#trace}

[rivet](https://github.com/pulseengine/rivet) is a schema-driven SDLC artifact
manager: requirement → architecture → design → code → test, with built-in schemas
(schemas, not certification) for ISO 26262, ISO/PAS 8800, ASPICE, DO-178C,
IEC 61508, EN 50128, IEC 62304, SOTIF, the EU AI Act, STPA / STPA-Sec / STPA-AI
and GSN safety cases, plus cross-domain bridge schemas. It imports spar's models
and CI's test results, validates the traceability integrity of the whole V on
every commit (broken links fail the build), and generates compliance reports
each release ([Reports](@/reports/_index.md)). It's the thread every other tool
hangs its evidence on.

<div class="tools tools--trace">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/rivet" rel="noopener">rivet</a><p class="tool__does">Typed, schema-checked traceability across the V; validates on every commit and generates compliance reports per release.</p><p class="tool__maturity">Work in progress.</p></div>
</div>

### 3 · Build — meld → loom → synth {#build}

Component code compiles to wasm. [meld](https://github.com/pulseengine/meld)
fuses multiple components into one module,
[loom](https://github.com/pulseengine/loom) optimizes it (multi-pass, via
Cranelift ISLE), and [synth](https://github.com/pulseengine/synth) transcodes it
toward native ARM (Cortex-M, Cortex-R5 and AArch64/ARMv8) and RISC-V.

In loom, translation validation is on by default: after each pass, a changed
function is reverted unless Z3 (or ordeal) proves it equivalent. A function
outside the model is left unchanged, and the transforms kept without a proof are
listed by reason in loom's trust ledger.

synth's output is checked against native output on real Cortex-M3, Cortex-M4
and ESP32-C3 boards for a benchmark kernel (cycle counts on the Cortex-M parts,
systimer ticks on the ESP32-C3), and executed against wasmtime for AArch64 in CI
on arm64 Linux.

<div class="tools tools--build">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/meld" rel="noopener">meld</a><p class="tool__does">Fuses multiple WebAssembly components into a single module.</p><p class="tool__maturity">Work in progress.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/loom" rel="noopener">loom</a><p class="tool__does">Multi-pass optimizer for the fused module.</p><p class="tool__maturity">Translation validation on by default; functions outside the model are left unchanged, and transforms kept without a proof are listed in its trust ledger.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/synth" rel="noopener">synth</a><p class="tool__does">Transcodes wasm toward native ARM (Cortex-M, Cortex-R5, AArch64) and RISC-V.</p><p class="tool__maturity">Pre-release: integers, and scalar f32/f64 on FPU targets; constructs without a lowering are refused, not miscompiled. Multi-memory phase 1 only.</p></div>
</div>

### 4 · Verify — the gate on the code {#verify}

Verification uses several deliberately independent techniques, so no blind spot
is shared across them:

- **Verus · Rocq · Lean 4** — deductive proof. **Verus** checks requires/ensures
  contracts on Rust source via SMT/Z3; functions marked `external_body` are
  trusted, not checked. **Rocq** machine-checks invariants; in gale and relay
  these are hand-written abstract models, not connected to the Rust. **Lean 4**
  proves results about models of the domain: in gale, rate-monotonic utilization
  bounds, the priority ceiling protocol and ring-buffer index arithmetic. Some
  legs prove the Rust source directly; others prove a hand-transcribed model, and
  where they do, that model↔code link is itself named as trusted base (see
  [the maturity series](/tags/how-it-works/)).
- **[scry](https://github.com/pulseengine/scry)**: sound abstract interpretation
  over the fused *wasm* (the third DO-333 leg), computing invariants that hold for
  all executions. It is designed to feed loom.
- **[witness](https://github.com/pulseengine/witness)** — MC/DC-style structural
  coverage on the *compiled* wasm: it measures the bytecode that actually ships
  (source-level mapping rests on a stated DWARF-correctness assumption).
- **[ordeal](https://github.com/pulseengine/ordeal)** re-checks part of the
  deductive layer (the bit-vector obligations Verus emits) and is synth's
  translation-validation engine. It is a pure-Rust, wasm-native QF_BV SMT solver
  whose untrusted core is paired with an LRAT (RUP) checker whose soundness
  (*accept ⇒ UNSAT*) is machine-checked in Lean 4 over an Aeneas-generated model
  of the Rust (Charon/Aeneas trusted). Each UNSAT answer carries an LRAT
  certificate that the Lean-checked checker re-verifies.

Proof and abstract interpretation cover all inputs *in principle*; witness
measures the bytecode that actually ships. No single technique spans both. How
far each technique reaches differs by project: gale and relay run Verus, Kani,
Rocq and Lean in CI on specific properties, and their docs say what is proven,
what is bounded and what is only tested. (For an honest look at the limits, see
[this eval](@/blog/2026-07-09-honest-failure-by-construction.md).)

<div class="tools tools--verify">
<div class="tool"><span class="tool__name">Verus · Rocq · Lean 4</span><p class="tool__does">Deductive proof, wired into Bazel by <a href="https://github.com/pulseengine/rules_verus" rel="noopener">rules_verus</a>, <a href="https://github.com/pulseengine/rules_rocq_rust" rel="noopener">rules_rocq_rust</a> and <a href="https://github.com/pulseengine/rules_lean" rel="noopener">rules_lean</a>.</p><p class="tool__maturity">Specific properties per project. Verus trusts <code>external_body</code>; Rocq accepts <code>Admitted</code>; some legs prove models, not the Rust.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/scry" rel="noopener">scry</a><p class="tool__does">Sound abstract interpretation over the fused wasm; designed to feed loom.</p><p class="tool__maturity">Core domains and transfers proven in Rocq over scry's integer model; harder transfers tested, not proven; proof against WasmCert-Coq deferred.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/witness" rel="noopener">witness</a><p class="tool__does">MC/DC-style structural coverage on the compiled wasm.</p><p class="tool__maturity">Source-level mapping rests on a stated DWARF-correctness assumption.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/ordeal" rel="noopener">ordeal</a><p class="tool__does">Certificate-checked SMT solver: untrusted core, checked LRAT certificates.</p><p class="tool__maturity">Checker soundness machine-checked in Lean 4 over an Aeneas-generated model; Charon/Aeneas trusted.</p></div>
</div>

### 5 · Ship — sigil · varve {#ship}

[sigil](https://github.com/pulseengine/sigil) can sign artifacts and
transformations (embedded signatures, Sigstore keyless or Ed25519, SLSA
provenance), so each stage's output, and the attestations about it, are bound to
exact bytes by signature. sigil's embedded-signature lineage traces to Frank
Denis's [wasmsign2](https://github.com/wasm-signatures/wasmsign2) (MIT): we
started from it and have diverged since, but the original DNA is his.

**The two bands read in opposite directions.**
sigil spans *above* the line in the factory views because it acts on what flows
through it, attesting the artifacts the pipeline produces.
[varve](https://github.com/pulseengine/varve) spans *below* because it delivers
the boxes themselves: the exact meld, loom, synth and kiln binaries a build ran,
as one signed, dated, digest-pinned layer. sigil answers *"is this component what
it claims to be?"*, and varve answers *"are the tools that produced it the ones
you think, on every machine and every runner?"* A packaging line, not another
station on the assembly line: it is what makes "which pipeline" answerable.

A per-project `varve.toml` names a realm and a layer; the realm supplies both the
registry and the trust root, so no environment variable is involved. Outside a
pinned project a shim **refuses** (`error: no varve.toml found walking up from …`,
exit 1) rather than silently running whatever is on PATH. Anti-rollback is
offline after the first install (a fresh consumer has no high-water mark yet): an
older layer is rejected with no network and no clock.

The limits are varve's own, and belong here rather than in a footnote. The
**rolling channel is provisional and makes no qualification promise**: its root
rotates at a v1.0 ceremony that has not happened, and the qualified channel is not
open. There is **no key rotation, revocation, expiry, threshold or transparency
log**, so a consumer pins the root by hand from a published asset and a leaked
root stays valid until every consumer edits their own config. Realms compose:
`pulseengine` carries PulseEngine's own tools, `pulseengine-wasm` carries the
upstream component-model tools, and `covalent` holds no tools and only asserts
the two belong together. Each included layer is verified against its own realm's
root, so a composing realm asserts a pairing and cannot widen trust.

<div class="tools tools--ship">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/sigil" rel="noopener">sigil</a><p class="tool__does">Signs and attests artifacts and transformations: embedded signatures, Sigstore keyless or Ed25519, SLSA provenance.</p><p class="tool__maturity">Work in progress.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/varve" rel="noopener">varve</a><p class="tool__does">Delivers the pinned, signed toolchain layer: the exact binaries a build ran, signed, dated and digest-pinned.</p><p class="tool__maturity">Rolling channel provisional, no qualification promise; no key rotation, revocation, expiry, threshold or transparency log yet.</p></div>
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
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/plant" rel="noopener">plant</a><p class="tool__does">Runs each CI check against a planted bad input and fails when the check stays green.</p><p class="tool__maturity">Work in progress, pre-1.0.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/jig" rel="noopener">jig</a><p class="tool__does">Shared CI baseline: reusable workflows pinned by SHA, plus fork guard, lockfile audit, action pins and a required verdict.</p><p class="tool__maturity">Work in progress, prereleases only. A first shadow pilot, beside a repository's own required checks, is open.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/sieve" rel="noopener">sieve</a><p class="tool__does">Shared CI path classifier: picks which heavy jobs a pull request touches; unsure means everything runs.</p><p class="tool__maturity">Work in progress.</p></div>
</div>

### 7 · Run — kiln · gale {#run}

[kiln](https://github.com/pulseengine/kiln) is an interpreter and runtime for
Component-Model wasm (partial WASI 0.2, early development). The interpreter runs on
std; getting to bare metal is synth's native path, not the interpreter on-target.

[gale](https://github.com/pulseengine/gale)'s North Star is **gust**: a general,
multi-tenant *verified OS*, where mutually-distrusting components are MPU-isolated
over one small Rust trusted base, composed entirely from verified parts. gale
reached toward that from the other end: it began as a Rust replacement, with Verus
contracts on the source, for **Zephyr** RTOS kernel primitives, and still provides
those verified primitives (sem, mutex, msgq, timers) as the *supply chain* the OS
composes from.

Proofs run in Verus, Rocq and Lean, ASIL-D-targeted; the gale card below says how
far they reach. The full fused composition (app, runtime and primitives dissolved
into one native object) boots on an emulated Cortex-M3 (QEMU lm3s6965evb). On
real boards, the dissolved gust_mix kernel is bit-identical to native on the
STM32 G474RE (Cortex-M4), the STM32F100 (Cortex-M3) and the ESP32-C3 (RISC-V),
and the kiln-async scheduler stack (gust_control) runs on the G474RE. The same
components also [run live in a browser](https://pulseengine.github.io/gale/).

<div class="tools tools--run">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/kiln" rel="noopener">kiln</a><p class="tool__does">Interpreter and runtime for Component-Model wasm.</p><p class="tool__maturity">Early development, partial WASI 0.2. The interpreter runs on std; bare metal is synth's native path.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/gale" rel="noopener">gale</a><p class="tool__does">Rust replacements for Zephyr kernel primitives, with Verus contracts on the source; its North Star is gust, a multi-tenant verified OS.</p><p class="tool__maturity">Some primitives proven, parts of the scheduler still admitted stubs; Rocq/Lean proofs over abstract models; multi-tenant isolation on the roadmap.</p></div>
</div>

## Built on the base — relay · wohl · jess {#built}

These are not another stage of the pipeline: they are products built *with*
it. Each one drives the same loop end to end, and each is where the methodology
has to survive contact with a real domain.

<div class="tools tools--built">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/relay" rel="noopener">relay</a><p class="tool__domain">flight software</p><p class="tool__does">Flight-software components for WebAssembly, inspired by NASA's cFS and reimagined as generic components, with formal proofs of specific safety properties: Verus contracts on the mission-layer crates, Kani bounded model checking, Lean for the controller's Lyapunov algebra.</p><p class="tool__maturity">Lean proves the Lyapunov algebra behind the SE(3) attitude controller (a model, not the Rust); the IEKF estimator is property-tested, with a proof still to land.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/wohl" rel="noopener">wohl</a><p class="tool__domain">home supervision</p><p class="tool__does">Home supervision: sensor nodes send CCSDS packets to a hub that runs six Kani-checked monitor components. Today's sensor is a wired STM32G0 bench node; sub-GHz field nodes are planned.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/jess" rel="noopener">jess</a><p class="tool__domain">hardware integration</p><p class="tool__does">Where software meets metal: an evidence-as-code hub for taking relay's falcon flight stack from simulation, through hardware-in-the-loop, toward a real drone, tracked in rivet the whole way.</p><p class="tool__maturity">It hasn't run on drone hardware yet: Phase 2 is bench and tethered, free flight is Phase 3.</p></div>
</div>

## A worked example

These repositories show the chain on real inputs today, and say which layers are
live and which are still skeletons.

**Build + verify + trace — [example-kvs](https://github.com/pulseengine/example-kvs).**
It takes a real third-party specification, Eclipse S-CORE's persistency
key-value store, and expresses it through the whole stack: rivet typed artifacts
that validate today, a spar AADL model, a WIT contract that builds against the
upstream code in CI, and a verification gate (`tools/verify.py`) that runs real
Bazel tests per artifact. The witness MC/DC harness and the sigil release
manifest are still skeletons that show the shape. The
[maturity series](/tags/how-it-works/) walks which layers are live. (And
[playground-eclipse-score](https://github.com/pulseengine/playground-eclipse-score)
converts Eclipse **safety artifacts** (requirements, architecture, FMEA, and
more) into rivet's typed YAML, testing schema coverage at real scale.)

**Run + hardware — falcon → jess.** relay's falcon flight stack (an Invariant-EKF
estimator, geometric SE(3) attitude control, an ADRC inner loop) flies in Gazebo
SITL and runs on an **emulated** Cortex-M7. gale's gust kernel, meanwhile,
already runs on the real boards listed under [Run](#run), and in the browser.
[jess](https://github.com/pulseengine/jess), the evidence-as-code hub, is about
taking the *flight* stack from simulation toward hardware-in-the-loop and,
eventually, a drone.

## Where the seams still show

Each repo's README and the [blog](@/blog/_index.md) keep a running account of
which claims are machine-proven, bounded, tested or still manual.

## Supporting projects {#supporting}

PulseEngine projects that support the PulseEngine tools: Bazel rules, layers,
examples, and integration tooling.

<div class="tools tools--support">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/temper" rel="noopener">temper</a><p class="tool__domain">repo hardening</p><p class="tool__does">GitHub App that hardens repositories to organizational standards.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/rules_wasm_component" rel="noopener">rules_wasm_component</a><p class="tool__domain">Bazel rules</p><p class="tool__does">Bazel rules for WebAssembly Component Model development with multi-profile builds.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/bazel-file-ops-component" rel="noopener">bazel-file-ops-component</a><p class="tool__domain">Bazel + WASM</p><p class="tool__does">Universal file operations for Bazel build systems via WebAssembly components.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/covalent-layers" rel="noopener">covalent-layers</a><p class="tool__domain">layer composition</p><p class="tool__does">A layer that composes the pulseengine and pulseengine-wasm toolchains.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/example-kvs" rel="noopener">example-kvs</a><p class="tool__domain">example</p><p class="tool__does">Eclipse S-CORE persistency through the full PulseEngine stack: rivet, spar, WIT, witness, sigil.</p></div>
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
| [walrus](https://github.com/pulseengine/walrus) | WASM transformation library | Fork of [wasm-bindgen/walrus](https://github.com/wasm-bindgen/walrus); carried a witness fix until upstream walrus 0.26.3 |
| [wasm-tools](https://github.com/pulseengine/wasm-tools) | WASM CLI and libraries | Fork of [bytecodealliance/wasm-tools](https://github.com/bytecodealliance/wasm-tools) |
| [zephyr](https://github.com/pulseengine/zephyr) | Zephyr RTOS | Fork of [zephyrproject-rtos/zephyr](https://github.com/zephyrproject-rtos/zephyr) |
| [picolibc](https://github.com/pulseengine/picolibc) | C library for embedded systems | Fork of [zephyrproject-rtos/picolibc](https://github.com/zephyrproject-rtos/picolibc) |
| [rowan](https://github.com/pulseengine/rowan) | Rust parser library | Fork of [rust-analyzer/rowan](https://github.com/rust-analyzer/rowan) |
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
- [The honest maturity map](/tags/how-it-works/) — a growing series of deep dives
  into where the seams still show, tagged `how-it-works`.
- [GitHub](https://github.com/pulseengine) — every repository named above.
