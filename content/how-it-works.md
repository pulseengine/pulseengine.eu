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

Read the **thick arrows** as the component flowing through the pipeline, and the
**dashed arrows** as proofs, evidence, and coordination flowing *between* stages —
the edges that turned the line into a graph.

{% mermaid() %}
flowchart TB
  spar["spar<br/>architecture"]
  code["components<br/>Rust → wasm"]
  meld["meld<br/>fuse"]
  loom["loom<br/>optimize"]
  synth["synth<br/>compile → native"]
  kiln["kiln<br/>interpret (host)"]
  gale["gale → gust<br/>verified OS · on real silicon"]
  apps["relay · wohl · jess"]
  verify{{"Verify gate<br/>Verus · Rocq · Lean<br/>scry · witness · ordeal"}}
  sigil["sigil<br/>sign · attest"]
  rivet[("rivet<br/>traceability spine")]

  spar ==>|WIT + skeletons| code ==> meld ==> loom
  loom ==>|compile| synth ==> gale
  loom -.->|interpret · on-target planned| kiln
  gale ==> apps

  loom -.->|proofs · wsc.facts| synth
  verify -.->|gates every stage| loom
  loom -.-> sigil
  synth -.-> sigil
  sigil -.->|signed evidence| rivet
  verify -.->|evidence| rivet
  spar -.->|typed artifacts| rivet

  classDef ours fill:#242836,stroke:#6c8cff,color:#e1e4ed;
  classDef gate fill:#161922,stroke:#4ade80,color:#e1e4ed;
  classDef spine fill:#242836,stroke:#fbbf24,color:#e1e4ed;
  classDef agent fill:#242836,stroke:#c084fc,color:#e1e4ed;
  class spar,code,meld,loom,synth,kiln,gale,apps,sigil ours
  class verify gate
  class rivet spine
{% end %}

Reading it:

- **The component pipeline (thick):** components fuse (meld), optimize (loom), then
  reach real silicon by being *compiled to native* by synth — that's gale's `gust`,
  bit-identical on three chips today. kiln *interprets* the same component (on the
  host now; an on-target `no_std` interpreter is the dashed, in-progress path).
- **The graph edges (dashed) are the news.** loom now hands synth the invariants it
  *proved* (`wsc.facts`); the **Verify gate** (green) blocks the build when the
  evidence isn't there; and every stage's evidence lands in **rivet** (amber), the
  traceability spine. The agents' own coordination lands there too, through
  GitHub issues and releases. These edges span *repositories*; no single repo's CI owns them.
- **Blue is ours; the external engines we build on** — Verus, Z3, Rocq, Lean,
  Sigstore, Aeneas — live inside the Verify and Attest steps, not as separate nodes.

## Following the flow

### 1 · Design — spar

[spar](https://github.com/pulseengine/spar) ingests AADL v2.3, SysML v2, and
CAN/DBC into one semantic model, runs safety analysis and TSN timing bounds, and
then *generates* what everything downstream starts from: WIT interfaces, Rust
skeletons, Lean 4 proof-obligation skeletons (theorem statements to discharge
downstream), and rivet artifacts. The design is checked before any code exists.
(spar's scheduling proofs are fully discharged; its TSN timing bounds are
cross-validated against a reference tool, not yet machine-proven.)

### 2 · Trace — rivet (the spine)

[rivet](https://github.com/pulseengine/rivet) is a schema-driven SDLC artifact
manager: requirement → architecture → design → code → test, with built-in schemas
for ISO 26262, DO-178C, IEC 61508, EN 50128, IEC 62304, the EU AI Act, and STPA /
STPA-Sec / STPA-AI. It imports spar's models and CI's test results, validates the
traceability integrity of the whole V on every commit, and generates compliance
reports each release. It's the thread every other tool hangs its evidence on.

### 3 · Build — meld → loom → synth

Component code compiles to wasm; [meld](https://github.com/pulseengine/meld)
fuses multiple components into one module;
[loom](https://github.com/pulseengine/loom) optimizes it and is
**translation-validated** — each optimization is *checked* per run (Z3 where the
function is in scope, a structural + differential backstop otherwise), not trusted;
[synth](https://github.com/pulseengine/synth) transcodes wasm toward native **ARM —
Cortex-M, Cortex-R5, and AArch64 (ARMv8) — and RISC-V**, and it's exercised on **real
silicon**: bare-metal and cycle-gated on Cortex-M3, Cortex-M4, and RISC-V (ESP32-C3),
and host-native on **Apple Silicon** (AArch64/ARMv8-A, differential-tested against
wasmtime). Still early: integer only (scalar float is rejected, not miscompiled), no
fused multi-memory yet.

{{ pipeline() }}

**The two bands read in opposite directions.**
[sigil](https://github.com/pulseengine/sigil) spans *above* the line because it
acts on what flows through it — attesting the artifacts the pipeline produces.
[varve](https://github.com/pulseengine/varve) spans *below* because it delivers
the boxes themselves: the exact meld, loom, synth and kiln binaries a build ran,
as one signed, dated, digest-pinned layer. sigil answers *"is this component what
it claims to be?"* — varve answers *"is the toolchain that produced it the one you
think, on every machine and every runner?"* A packaging line, not another station
on the assembly line.

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
root stays valid until every consumer edits their own config. And the published
layer carries the tools that *check* our work, not the upstream Bytecode Alliance
tools that *build* it — layer composition across two trust roots ships in the
tool, but what is published today is one realm.

### 4 · Verify — the gate

Not one technique but several, deliberately independent, so no single blind spot
is shared across them:

- **Verus · Rocq · Lean 4** — deductive proof (SMT/Z3, theorem proving, scheduling
  theory). Some legs prove the Rust source directly; others prove a hand-transcribed
  model, and where they do, that model↔code link is itself named as trusted base
  (see [the maturity series](/tags/how-it-works/)).
- **[scry](https://github.com/pulseengine/scry)** — sound abstract interpretation
  over the fused *wasm* (the third DO-333 leg). Soundness is machine-checked over
  scry's integer model; the proof against canonical Wasm semantics is still in
  progress.
- **[witness](https://github.com/pulseengine/witness)** — MC/DC-style structural
  coverage on the *compiled* wasm: it measures the bytecode that actually ships
  (source-level mapping rests on a stated DWARF-correctness assumption).
- **[ordeal](https://github.com/pulseengine/ordeal)** underwrites the deductive
  layer itself — a certificate-checked SMT solver whose untrusted core is paired
  with an LRAT (RUP) checker whose soundness (*accept ⇒ UNSAT*) is machine-checked
  in Lean 4 over an Aeneas-generated model of the Rust (Charon/Aeneas trusted). Even
  its UNSAT answers carry evidence a checker can re-verify — a rare, strong core.

Proof and abstract interpretation cover all inputs *in principle*; witness
measures the bytecode that actually ships. No single technique spans both — which
is the point. (For an honest look at the limits, see
[this eval](@/blog/2026-07-09-honest-failure-by-construction.md).)

### 5 · Attest — sigil

[sigil](https://github.com/pulseengine/sigil) can sign artifacts and
transformations — embedded signatures, Sigstore keyless, SLSA provenance — so what
Verify establishes stays bound to exactly the bytes that run. sigil's
embedded-signature lineage traces to Frank Denis's
[wasmsign2](https://github.com/jedisct1/wasmsign2) (MIT): we took it over and
diverged substantially — roughly 18× the code and the signing engine rewritten — but
the original DNA is his.

### 6 · Run — kiln · gale

[kiln](https://github.com/pulseengine/kiln) is an interpreter and runtime for
Component-Model wasm (partial WASI 0.2, early development). The interpreter runs on
std; getting to bare metal is synth's native path, not the interpreter on-target.
[gale](https://github.com/pulseengine/gale)'s North Star is **gust** — a general,
multi-tenant *verified OS*, where mutually-distrusting components are MPU-isolated
over one tiny (~4-item) Rust trusted base, composed entirely from verified parts. It
reached toward that from the other end: gale began as a formally-verified Rust
replacement for **Zephyr** RTOS kernel primitives (39 modules across the Zephyr
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

### 7 · Integrate — relay · wohl · jess

Applications exercise the chain end-to-end.
[relay](https://github.com/pulseengine/relay) is flight software — a formally
*verifiable* control cascade: its geometric SE(3) attitude loop carries a
Lean-proven Lyapunov argument, while the IEKF estimator is property-tested with a
proof still to land. [wohl](https://github.com/pulseengine/wohl) is home
supervision. [jess](https://github.com/pulseengine/jess) is where software meets
metal: an evidence-as-code hub for taking the falcon stack from simulation, through
hardware-in-the-loop, *toward* a real drone. It hasn't flown on hardware — that's
the Phase-2 arc (its name is the falconry tether, on purpose).

### Across all of it — the agent loop

Today PulseEngine's agents coordinate the plain way — they synchronize through
**GitHub issues and releases**, running in loops to hunt issues, implement features,
and check whether a new release actually works. That is a deliberate choice rather
than a gap: issues and releases are already durable, signed and auditable, with no new
infrastructure to trust. Around that, [rivet](https://github.com/pulseengine/rivet)'s
MCP tools expose validate / add / link / coverage to agents, and
[temper](https://github.com/pulseengine/temper) (a GitHub App) holds every repo to
the same standards. The [mcp](https://github.com/pulseengine/mcp) framework was our
early Rust MCP bet — its future is now unclear, since the official MCP Rust SDK went
its own way and mcp was stripped back.

And the methodology those agents follow is itself packaged as tooling — the
[**pulseengine-claude**](https://github.com/pulseengine/pulseengine.eu/tree/main/claude-tooling/plugins/pulseengine-claude)
skills (proof-synthesis, oracle-gating, clean-room verification, release-execution,
and more), which live in this very site's repo. "Write the code and close the V" is
an installable practice here, not tribal knowledge.

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

## See also

- [Projects](@/projects/_index.md) — the parts, by role, as an interactive map.
- [Timeline](@/timeline.md) — the month-by-month story of how all of this got built,
  from kiln onward.
- [Reports](@/reports/_index.md) — live compliance and coverage output from rivet
  and witness.
- [The honest maturity map](/tags/how-it-works/) — a growing series of deep dives
  into where the seams still show, tagged `how-it-works`.
- [GitHub](https://github.com/pulseengine) — every repository named above.
