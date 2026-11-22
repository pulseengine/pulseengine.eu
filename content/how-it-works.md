+++
title = "How it works"
description = "One path from a system-architecture model to signed code running on hardware — the PulseEngine tools that compose along it, stage by stage, and the projects built on top."
template = "how-it-works.html"
aliases = ["/projects/"]
+++

PulseEngine is not a single program. It's a set of small, independent tools —
each doing one job in the life of a safety-critical WebAssembly component, and
each independently verifiable. This page shows the **flow**: how one thing
travels from a system-architecture model, through build and verification, to
signed artifacts running on a real target — and, stage by stage, which tools do
the work and how far along each one is.

{% <note kind="tip"> %}
Everything here is **work in progress**, at varying maturity. The tools compose
in principle and in the worked examples below — this is not a one-button
production pipeline, and *"verified"* always means **specific properties,
machine-checked**, never a blanket guarantee. Where a seam is still manual or a
stage is early, we say so.
{% </note> %}

## Three views of one factory

The same four tools, looked at from three angles. Switch between them; the boxes
do not move, only what is said about them.

<!-- factory-views-component -->

There is no reading key, and that is deliberate. The previous version of this
picture encoded the component's path as thick arrows and everything else as
dashed ones, which is what let a single diagram carry three unrelated questions
and then need three sentences explaining how to look at it. Inside each view
above, every edge means one thing.

What is *not* in any of them: relay, wohl and jess. They are products built with
this toolchain rather than a stage of it, so putting them at the end of a flow
would repeat the error the arrows made. They have their own section below.

## Following the flow

<nav class="stage-key" aria-label="Stages">
<a href="#design">Design</a><a href="#trace">Trace</a><a href="#build">Build</a><a href="#verify">Verify</a><a href="#ship">Ship</a><a href="#gate">Gate</a><a href="#run">Run</a>
</nav>

### 1 · Design — spar {#design}

[spar](https://github.com/pulseengine/spar) is a compiler for system-architecture
models. It ingests AADL v2.3, SysML v2, and CAN/DBC into one semantic model, runs
pluggable analysis passes — safety analysis, ARINC 653 partitioning, and TSN
timing bounds — plus a deployment solver, and then *generates* what everything
downstream starts from: WIT interfaces, Rust skeletons, Lean 4 proof-obligation
skeletons (theorem statements to discharge downstream), and rivet artifacts. It
also renders SVG, ships an LSP server and a
[VS Code extension](https://marketplace.visualstudio.com/items?itemName=pulseengine.spar-aadl),
and compiles to a single WebAssembly component. The design is checked before any
code exists.

<div class="tools tools--design">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/spar" rel="noopener">spar</a><p class="tool__does">Architecture models (AADL, SysML v2, CAN/DBC) in; analyses, WIT, Rust and Lean 4 skeletons and rivet artifacts out.</p><p class="tool__maturity">Scheduling proofs fully discharged; TSN timing bounds cross-validated against a reference tool, not yet machine-proven. Among the most exercised tools.</p></div>
</div>

### 2 · Trace — rivet (the spine) {#trace}

[rivet](https://github.com/pulseengine/rivet) is a schema-driven SDLC artifact
manager: requirement → architecture → design → code → test, with built-in schemas
for ISO 26262, ISO/PAS 8800, ASPICE, DO-178C, IEC 61508, EN 50128, IEC 62304,
SOTIF, the EU AI Act, STPA / STPA-Sec / STPA-AI and GSN safety cases, plus
cross-domain bridge schemas. It imports spar's models and CI's test results,
validates the traceability integrity of the whole V on every commit — broken
links fail the build — and generates compliance reports each release
([Reports](@/reports/_index.md)). It's the thread every other tool hangs its
evidence on.

<div class="tools tools--trace">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/rivet" rel="noopener">rivet</a><p class="tool__does">Typed, schema-checked traceability across the V; validates on every commit and generates compliance reports per release.</p><p class="tool__maturity">Among the most exercised tools.</p></div>
</div>

### 3 · Build — meld → loom → synth {#build}

Component code compiles to wasm; [meld](https://github.com/pulseengine/meld)
fuses multiple components into one module;
[loom](https://github.com/pulseengine/loom) optimizes it (multi-pass, via
Cranelift ISLE) and is **translation-validated** — each optimization is *checked*
per run (Z3 where the function is in scope, a structural + differential backstop
otherwise), not trusted; [synth](https://github.com/pulseengine/synth) transcodes
wasm toward native **ARM — Cortex-M, Cortex-R5, and AArch64 (ARMv8) — and
RISC-V**, and it's exercised on **real silicon**: bare-metal and cycle-gated on
Cortex-M3, Cortex-M4, and RISC-V (ESP32-C3), and host-native on **Apple Silicon**
(AArch64/ARMv8-A, differential-tested against wasmtime). Three separate tools, one
flow; every stage is independently verifiable.

<div class="tools tools--build">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/meld" rel="noopener">meld</a><p class="tool__does">Fuses multiple WebAssembly components into a single module.</p><p class="tool__maturity">Work in progress.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/loom" rel="noopener">loom</a><p class="tool__does">Multi-pass optimizer for the fused module.</p><p class="tool__maturity">Translation-validated per run: Z3 where the function is in scope, a structural + differential backstop otherwise.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/synth" rel="noopener">synth</a><p class="tool__does">Transcodes wasm toward native ARM (Cortex-M, Cortex-R5, AArch64) and RISC-V.</p><p class="tool__maturity">Still early: integer only (scalar float is rejected, not miscompiled), no fused multi-memory yet.</p></div>
</div>

### 4 · Verify — the gate on the code {#verify}

Not one technique but several, deliberately independent, so no single blind spot
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
- **[scry](https://github.com/pulseengine/scry)** — sound abstract interpretation
  over the fused *wasm* (the third DO-333 leg), computing invariants that hold for
  all executions and feeding them downstream to loom. Soundness is machine-checked
  over scry's integer model; the proof against canonical Wasm semantics is still
  in progress.
- **[witness](https://github.com/pulseengine/witness)** — MC/DC-style structural
  coverage on the *compiled* wasm: it measures the bytecode that actually ships
  (source-level mapping rests on a stated DWARF-correctness assumption).
- **[ordeal](https://github.com/pulseengine/ordeal)** underwrites the deductive
  layer itself — a pure-Rust, wasm-native QF_BV SMT solver whose untrusted core is
  paired with an LRAT (RUP) checker whose soundness (*accept ⇒ UNSAT*) is
  machine-checked in Lean 4 over an Aeneas-generated model of the Rust
  (Charon/Aeneas trusted). Even its UNSAT answers carry evidence a checker can
  re-verify — a rare, strong core.

Proof and abstract interpretation cover all inputs *in principle*; witness
measures the bytecode that actually ships. No single technique spans both — which
is the point. How far each technique reaches differs by project: gale and relay
run Verus, Kani, Rocq and Lean in CI on specific properties, and their docs say
what is proven, what is bounded and what is only tested. A green proof job is not
the same as everything proven: Rocq accepts `Admitted`, and Verus trusts
`external_body`. (For an honest look at the limits, see
[this eval](@/blog/2026-07-09-honest-failure-by-construction.md).)

<div class="tools tools--verify">
<div class="tool"><span class="tool__name">Verus · Rocq · Lean 4</span><p class="tool__does">Deductive proof, wired into Bazel by <a href="https://github.com/pulseengine/rules_verus" rel="noopener">rules_verus</a>, <a href="https://github.com/pulseengine/rules_rocq_rust" rel="noopener">rules_rocq_rust</a> and <a href="https://github.com/pulseengine/rules_lean" rel="noopener">rules_lean</a>.</p><p class="tool__maturity">Specific properties per project. Verus trusts <code>external_body</code>; Rocq accepts <code>Admitted</code>; some legs prove models, not the Rust.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/scry" rel="noopener">scry</a><p class="tool__does">Sound abstract interpretation over the fused wasm.</p><p class="tool__maturity">Soundness machine-checked over scry's integer model; the proof against canonical Wasm semantics is still in progress.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/witness" rel="noopener">witness</a><p class="tool__does">MC/DC-style structural coverage on the compiled wasm.</p><p class="tool__maturity">Source-level mapping rests on a stated DWARF-correctness assumption. Among the most exercised tools.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/ordeal" rel="noopener">ordeal</a><p class="tool__does">Certificate-checked SMT solver: untrusted core, checked LRAT certificates.</p><p class="tool__maturity">Checker soundness machine-checked in Lean 4 over an Aeneas-generated model; Charon/Aeneas trusted.</p></div>
</div>

### 5 · Ship — sigil · varve {#ship}

[sigil](https://github.com/pulseengine/sigil) can sign artifacts and
transformations — embedded signatures, Sigstore keyless or Ed25519, SLSA
provenance — so what Verify establishes stays bound to exactly the bytes that run.
sigil's embedded-signature lineage traces to Frank Denis's
[wasmsign2](https://github.com/jedisct1/wasmsign2) (MIT): we took it over and
diverged substantially — roughly 18× the code and the signing engine rewritten — but
the original DNA is his.

**The two bands read in opposite directions.**
sigil spans *above* the line in the factory views because it acts on what flows
through it — attesting the artifacts the pipeline produces.
[varve](https://github.com/pulseengine/varve) spans *below* because it delivers
the boxes themselves: the exact meld, loom, synth and kiln binaries a build ran,
as one signed, dated, digest-pinned layer. sigil answers *"is this component what
it claims to be?"* — varve answers *"is the toolchain that produced it the one you
think, on every machine and every runner?"* A packaging line, not another station
on the assembly line: it is what makes "which pipeline" answerable.

A per-project `varve.toml` names a realm and a layer; the realm supplies both the
registry and the trust root, so no environment variable is involved. Outside a
pinned project a shim **refuses** — `error: no varve.toml found walking up from …`,
exit 1 — rather than silently running whatever is on PATH. Anti-rollback is
offline: an older layer is rejected with no network and no clock.

The limits are varve's own, and belong here rather than in a footnote. The
**rolling channel is provisional and makes no qualification promise** — its root
rotates at a v1.0 ceremony that has not happened, and the qualified channel is not
open. There is **no key rotation, revocation, expiry, threshold or transparency
log**, so a consumer pins the root by hand from a published asset and a leaked
root stays valid until every consumer edits their own config. Three realms are published, and one
composes the other two: `pulseengine` carries the tools that *check* our work,
`pulseengine-wasm` carries the upstream component-model tools that *build* it, and
`covalent` holds no tools at all. It exists only to assert that those two belong
together. Each included layer is verified against its own realm's root, so a
composing realm asserts a pairing and cannot widen trust.

<div class="tools tools--ship">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/sigil" rel="noopener">sigil</a><p class="tool__does">Signs and attests artifacts and transformations: embedded signatures, Sigstore keyless or Ed25519, SLSA provenance.</p><p class="tool__maturity">Among the most exercised tools.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/varve" rel="noopener">varve</a><p class="tool__does">Delivers the pinned, signed toolchain layer: the exact binaries a build ran, signed, dated and digest-pinned.</p><p class="tool__maturity">Rolling channel provisional, no qualification promise; no key rotation, revocation, expiry, threshold or transparency log yet.</p></div>
</div>

### 6 · Gate — jig · plant · sieve {#gate}

Every stage above reports through CI, so the CI checks are evidence too. A green
CI check means "nothing I looked at was wrong". It does not say whether the check
looked. This stage is about proving the checks themselves can fail.
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
apart. All three are work in progress.

<div class="tools tools--gate">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/plant" rel="noopener">plant</a><p class="tool__does">Runs each CI check against a planted bad input and fails when the check stays green.</p><p class="tool__maturity">Work in progress, pre-1.0.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/jig" rel="noopener">jig</a><p class="tool__does">Shared CI baseline: reusable workflows pinned by SHA, plus fork guard, lockfile audit, action pins and a required verdict.</p><p class="tool__maturity">Work in progress, prereleases only. A first shadow pilot, beside a repository's own required checks, is open.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/sieve" rel="noopener">sieve</a><p class="tool__does">Shared CI path classifier: picks which heavy jobs a pull request touches; unsure means everything runs.</p><p class="tool__maturity">Work in progress.</p></div>
</div>

### 7 · Run — kiln · gale {#run}

[kiln](https://github.com/pulseengine/kiln) is an interpreter and runtime for
Component-Model wasm (partial WASI 0.2, early development). The interpreter runs on
std; getting to bare metal is synth's native path, not the interpreter on-target.
[gale](https://github.com/pulseengine/gale)'s North Star is **gust** — a general,
multi-tenant *verified OS*, where mutually-distrusting components are MPU-isolated
over one tiny (~4-item) Rust trusted base, composed entirely from verified parts. It
reached toward that from the other end: gale began as a Rust replacement, with Verus
contracts on the source, for **Zephyr** RTOS kernel primitives (39 modules across the Zephyr
kernel surface), and still provides those verified primitives — sem, mutex, msgq,
timers — as the *supply chain* the OS composes from. Proofs run across three provers
(Verus, Rocq, Lean), ASIL-D-targeted, and honest work-in-progress: some primitives
are proven, others (parts of the scheduler) are still admitted stubs, the Rocq/Lean
proofs are over abstract models, and multi-tenant isolation is still on the roadmap.
What boots today dissolves app + runtime + primitives into a single native object
that runs on **real silicon across three chips and two architectures** — Cortex-M4
(STM32 G474RE), Cortex-M3 (STM32F100), and RISC-V (ESP32-C3) — each dissolved from the
same components and bit-identical to native, with no runtime underneath; the same
components also [run live in a browser](https://pulseengine.github.io/gale/).

<div class="tools tools--run">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/kiln" rel="noopener">kiln</a><p class="tool__does">Interpreter and runtime for Component-Model wasm.</p><p class="tool__maturity">Early development, partial WASI 0.2. The interpreter runs on std; bare metal is synth's native path.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/gale" rel="noopener">gale</a><p class="tool__does">Rust replacements for Zephyr kernel primitives, with Verus contracts on the source; its North Star is gust, a multi-tenant verified OS.</p><p class="tool__maturity">Some primitives proven, parts of the scheduler still admitted stubs; Rocq/Lean proofs over abstract models; multi-tenant isolation on the roadmap.</p></div>
</div>

## Built on the base — relay · wohl · jess {#built}

These are not another stage of the pipeline — they are products built *with*
it. Each one drives the same loop end to end, and each is where the methodology
has to survive contact with a real domain.

<div class="tools tools--built">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/relay" rel="noopener">relay</a><p class="tool__domain">flight software</p><p class="tool__does">Flight-software components for WebAssembly, inspired by NASA's cFS and reimagined as generic components, with formal proofs of specific safety properties: Verus contracts on the mission-layer crates, Kani bounded model checking, Lean for the controller's Lyapunov algebra.</p><p class="tool__maturity">The geometric SE(3) attitude loop carries a Lean-proven Lyapunov argument; the IEKF estimator is property-tested, with a proof still to land.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/wohl" rel="noopener">wohl</a><p class="tool__domain">home supervision</p><p class="tool__does">A wireless field-sensor product on STM32G0 — CCSDS payloads over a sub-GHz radio, bridged at the hub. The small-target end of the range, where footprint decides what is possible.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/jess" rel="noopener">jess</a><p class="tool__domain">hardware integration</p><p class="tool__does">Where software meets metal: an evidence-as-code hub for taking relay's falcon flight stack from simulation, through hardware-in-the-loop, toward a real drone, tracked in rivet the whole way.</p><p class="tool__maturity">It hasn't flown on hardware — that's the Phase-2 arc (its name is the falconry tether, on purpose).</p></div>
</div>

## A worked example

Two real repositories show the chain on real inputs today — and are honest about
which layers are live and which are still skeletons.

**Build + verify + trace — [example-kvs](https://github.com/pulseengine/example-kvs).**
It takes a real third-party specification — Eclipse S-CORE's persistency
key-value store — and expresses it through the whole stack: rivet typed artifacts
(which validate today), plus a spar AADL model, a WIT contract, a witness MC/DC
harness, a sigil release manifest, and a verification gate — the last of these still
*skeletons that show the shape*, with the gate running as a stub. It's an honest map
of how the pieces interlock on something we didn't invent; the
[maturity series](/tags/how-it-works/) walks which layers are
live. (And
[playground-eclipse-score](https://github.com/pulseengine/playground-eclipse-score)
converts **2,985** Eclipse **safety artifacts** — requirements, architecture, FMEA,
and more — into rivet's typed YAML, testing schema coverage at real scale.)

**Run + hardware — falcon → jess.** relay's falcon flight stack — an Invariant-EKF
estimator, geometric SE(3) attitude control, an ADRC inner loop — flies in Gazebo
SITL and runs on an **emulated** Cortex-M7. gale's gust composition, meanwhile,
already runs on **real silicon** — Cortex-M4 (G474RE), Cortex-M3 (F100), and RISC-V
(ESP32-C3) — and in the browser. So silicon itself is reached;
[jess](https://github.com/pulseengine/jess) — the
evidence-as-code hub — is about taking the *flight* stack from simulation toward
hardware-in-the-loop and, eventually, a drone. The tether is still on.

## Where the seams still show

Being honest about maturity is part of the method:

- The stages are **independent tools at different maturity** — rivet, spar,
  witness, and sigil are the most exercised; kiln and synth are earlier.
- **"Composes"** means *demonstrated in the worked examples and in CI*, not a
  single turnkey command.
- Every **"verified"** claim is a specific, machine-checked property — proven,
  measured, or still manual. We keep a running honest account of which is which;
  each repo's README and the [blog](@/blog/_index.md) track it.

## Supporting projects {#supporting}

PulseEngine projects that support the core toolchain — Bazel rules, layers,
examples, and integration tooling.

<div class="tools tools--support">
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/temper" rel="noopener">temper</a><p class="tool__domain">repo hardening</p><p class="tool__does">GitHub App that hardens repositories to organizational standards.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/rules_wasm_component" rel="noopener">rules_wasm_component</a><p class="tool__domain">Bazel rules</p><p class="tool__does">Bazel rules for WebAssembly Component Model development with multi-profile builds.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/bazel-file-ops-component" rel="noopener">bazel-file-ops-component</a><p class="tool__domain">Bazel + WASM</p><p class="tool__does">Universal file operations for Bazel build systems via WebAssembly components.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/covalent-layers" rel="noopener">covalent-layers</a><p class="tool__domain">layer composition</p><p class="tool__does">A layer that composes the pulseengine and pulseengine-wasm toolchains.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/example-kvs" rel="noopener">example-kvs</a><p class="tool__domain">example</p><p class="tool__does">Eclipse S-CORE persistency through the full PulseEngine stack — rivet, spar, WIT, witness, sigil.</p></div>
<div class="tool"><a class="tool__name" href="https://github.com/pulseengine/playground-eclipse-score" rel="noopener">playground-eclipse-score</a><p class="tool__domain">playground</p><p class="tool__does">Eclipse S-CORE typed-traceability playground — sphinx-needs artifacts converted to rivet.</p></div>
</div>

Also: [rules_verus](https://github.com/pulseengine/rules_verus),
[rules_rocq_rust](https://github.com/pulseengine/rules_rocq_rust),
[rules_lean](https://github.com/pulseengine/rules_lean),
[rules_ordeal](https://github.com/pulseengine/rules_ordeal),
[pulseengine-layers](https://github.com/pulseengine/pulseengine-layers),
[wasm-layers](https://github.com/pulseengine/wasm-layers),
[wasm-component-examples](https://github.com/pulseengine/wasm-component-examples).

## Forks & dependencies {#forks}

The PulseEngine GitHub organisation also hosts forks and vendored copies of
third-party projects. These are **not** PulseEngine projects — they exist for
build reproducibility, patching, or experimentation. We do not design, build, or
maintain them.

| Repository | What it is | Why it's here |
|---|---|---|
| [z3](https://github.com/pulseengine/z3) | Z3 Theorem Prover | Vendored for ordeal's build; we replaced it with our own solver |
| [z3.rs](https://github.com/pulseengine/z3.rs) | Rust bindings for Z3 | Same — vendored for build reproducibility |
| [wasmtime](https://github.com/pulseengine/wasmtime) | WebAssembly runtime | Forked for experimentation; kiln is our interpreter and runtime |
| [wit-bindgen](https://github.com/pulseengine/wit-bindgen) | WIT binding generator | Vendored for rules_wasm_component builds |
| [walrus](https://github.com/pulseengine/walrus) | WASM transformation library | Forked for loom's optimization passes |
| [wasm-tools](https://github.com/pulseengine/wasm-tools) | WASM CLI and libraries | Vendored for component-model tooling |
| [zephyr](https://github.com/pulseengine/zephyr) | Zephyr RTOS | Forked as reference for gale's kernel primitives |
| [picolibc](https://github.com/pulseengine/picolibc) | C library for embedded systems | Vendored for cross-compilation targets |
| [rowan](https://github.com/pulseengine/rowan) | Rust parser library | Vendored for spar's model parsing |
| [renode-bazel-rules](https://github.com/pulseengine/renode-bazel-rules) | Bazel rules for Renode | Forked for simulation-in-CI integration |
| [bazel-central-registry](https://github.com/pulseengine/bazel-central-registry) | Bazel module registry | Forked for private module publishing |

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
