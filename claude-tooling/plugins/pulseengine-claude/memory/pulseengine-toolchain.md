---
name: pulseengine-toolchain
description: "The single roster of what each pulseengine tool does — rivet, spar, witness, sigil, meld, loom, synth, kiln, gale, scry, smithy, thrum, temper, mcp, wohl. Directory only; the compose-loop procedure lives in the pulseengine-feature-loop skill."
metadata:
  node_type: memory
  type: reference
  scope: plugin-bundled
---

Map of the PulseEngine tools. Each lives in `/Users/r/git/pulseengine/<name>` on Ralf's machine and has its own per-project memory store under `~/.claude/projects/-Users-r-git-pulseengine-<name>/memory/`. Treat this as a directory, not a spec — read the project memory for current state.

## Core stack

**rivet** — typed traceability CLI. YAML artifacts in git, schemas, `rivet validate / check / coverage / impact`, typed link predicates (verifies, implements, traced-by), MCP server so agents maintain traceability as they work. Schema support: STPA, ASPICE, IEC 61508, DO-178C, EN 50128, EU AI Act. Installed at `/Users/r/.cargo/bin/rivet`. From `2026-03-15-rivet-v0.1.0`.

**spar** — AADL v2.3 architecture analysis. 27+ analysis passes including scheduling, latency, ARINC 653 partitioning, EMV2 fault trees, ASIL decomposition solver. Modal filtering on operations modes, piecewise-affine arrival curves for TSN, PMOO/LUDB multiplexing. Feeds rivet's traceability graph. Generates WIT interfaces from AADL (don't hand-write WIT in wohl). MCP server for agent access. From `2026-05-11-spar-v0.9.x-milestone`.

**witness** — Wasm MC/DC coverage. Instruments Wasm, runs tests, emits **truth tables with masking / unique-cause proofs**, not coverage percentages. `witness-viz` shows which condition vectors are missing and suggests test stubs. Philosophy: structured evidence (truth table + gap identification + test suggestion) is the artifact, not a number. From `2026-04-25-witness-wasm-mcdc` + `2026-05-05-witness-the-truth-table-not-the-percentage`.

**sigil** — signed attestation chains. Build-stage pipelines, multi-scheme signatures, key rotation, content-addressed stores, detached verification. Sits at intersection of TrustMee (Aalto, signed Wasm verifier) and Cerisier (Aarhus, Iris-formalized sealing predicates) — but the time-indexed, scheme-aware, detached sister logic to those doesn't yet exist, so sigil contains real open research. From `2026-05-11-attestation-chains-trustmee-to-cerisier`.

**meld** — verification fusion tool. Track-3 passes (consult per-project memory for current scope). v0.1.0 in `2026-03-02-meld-v0.1.0`.

**synth** — WebAssembly Component Model engine that transcodes via program synthesis to ARM/RISC-V with Rocq proofs. Cover targets are i.MX RT1062 / STM32H743 (never name NXP S32G publicly). RV32 parity is a tracked goal. See synth project memory for cadence.

**loom** — companion project with its own Rocq Formal Proofs CI; upstream toolchain breakages occasionally turn that gate red.

**kiln** — interpreter and runtime (not just a runtime, not AOT). Companion to synth.

**smithy** — clean-room verifier *agent* (not a CLI). The pattern: spawn smithy (or equivalent subagent) with only the claims, no prior context, to confirm/refute/cannot-verify findings. The procedure lives in the `clean-room-verification` skill.

**wohl** — application of the stack to a wireless field-sensor product (STM32G0 + door contact, CCSDS payload, sub-GHz radio, Matter Bridge at the hub but never native Matter at sensors).

**gale** — formally verified Zephyr RTOS kernel primitives in Rust, ASIL-D targeted. Triple-track verification: Verus (SMT/Z3) + Rocq (theorem proving) + Lean (scheduler/priority proofs); hundreds of Verus-verified properties. A load-bearing target of the `proof-synthesis` skill.

**scry** — sound **abstract interpretation** for Wasm (Cousot framework) — the third DO-333 formal-methods leg alongside deductive proof (gale) and structural coverage (witness). Computes invariants over the fused Wasm Core module, feeds them to loom and sigil-signed evidence to rivet. A named backend in `proof-synthesis`. Runs witness MC/DC as a live CI gate.

**thrum** — observability / unified dashboard (`thrum-api`) over the toolchain; also the design-system source for the pulseengine.eu site.

**temper** — GitHub App that hardens org repos to standards (dependabot routing, config, auto-merge). Org automation, not a per-project CLI.

**mcp** — Rust framework for building Model Context Protocol servers and clients (the MCP layer rivet/spar expose). Published to crates.io.

**ordeal** — certificate-checked QF_BV SMT. Ships inside the varve layer; a decision procedure whose results carry a checkable certificate rather than being trusted on the solver's word.

**varve** — toolchain **layer manager**, and the reason "which toolchain produced this artifact?" is answerable. Distributes the whole tool set as one signed, dated, digest-pinned OCI layer (`YYYY.MM.P`) on `ghcr.io/pulseengine/varve/layers`; per-project `varve.toml` pin discovered by walking up from cwd; offline verification against a trust root; anti-rollback counters; content-addressed core so layers coexist and switching is `cd`; PATH shims; `self-update` (old-verifies-new); `deposit` / `export-bazel` for CI. Sits **outside** the layer it installs — it must exist before any layer does. Native Rust CLI, so witness MC/DC and scry are N/A to varve itself (they target the Wasm the layers carry).

Two properties of varve are load-bearing for the other skills, both verified by execution (2026-08-08, v0.13.0):

- **No silent fallback.** Outside a pinned project a shim *refuses* — `error: no varve.toml found …`, exit 1 — rather than running whatever is on PATH. Inside one it dispatches and exits 0.
- **Realms beat the ambient environment.** When the pin names a `realm`, a committed `varve-realms.toml` supplies the registry *and* the trust root, and a hostile `VARVE_TRUST_ROOT` cannot substitute a different root. Negative control: the same bogus root makes `varve verify` exit 1 with no realm, and is ignored with one. Prefer the realm path — it needs no environment variable and is the stronger of the two.

## How they compose

The procedure for composing these tools end-to-end (spar → WIT → rivet → code → witness → sigil → smithy) lives in the **`pulseengine-feature-loop` skill** shipped with this plugin, not here. This memory is the directory; the skill is the recipe.

This file is the **single roster** for the tools — other files (skills, hooks)
should reference it, not re-enumerate. See also: [[pulseengine-philosophy]] and the
plugin's procedural skills.
