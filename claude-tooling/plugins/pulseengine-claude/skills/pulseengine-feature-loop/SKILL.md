---
name: pulseengine-feature-loop
description: This skill should be used when doing a feature end-to-end on a PulseEngine project (rivet, spar, witness, sigil, meld, loom, synth, wohl, kiln) — including "implement a feature", "add a new requirement", "extend the architecture", "write a new pass", "ship a feature end-to-end", "do this properly with traceability", "model-driven implementation", or any feature work that should pass through the full AADL → WIT → typed traceability → oracle-gated code → MC/DC → attestation → verify loop. ALWAYS use this skill when the user authorizes feature work on a PulseEngine project and the work touches more than a single file.
metadata:
  author: pulseengine.eu
  version: "0.4.0"
---

# PulseEngine feature loop

## When this fires

End-to-end feature work on a PulseEngine project where the methodology actually composes: spar (AADL architecture) → rivet (typed traceability) → code (agent-written, oracle-gated) → witness (MC/DC on Wasm) → sigil (signed attestation) → smithy (clean-room verify). This is the "MBSE is mandatory infrastructure for AI-authored safety code" claim made concrete.

Use this when the feature touches more than one layer of the stack. Single-file refactors don't need the full loop; reach for [`oracle-gate-a-change`] alone.

## Standing practice across every step

Friction is data. At any step below, if a tool errors, produces wrong output, lacks a capability you needed, or forces a workaround, file it via [`report-tool-friction`] in that tool's repo *as you hit it* — then continue. A workaround you don't report is friction the next feature re-hits. This is woven through the whole loop, not a phase of it.

This is a long-running explorer (see [`pulseengine-operating-contract`]): self-verify at a **concrete interval — before every tag, and at least every ~2 features/releases in a round** (not "at some point") — with fresh-context subagents ([`clean-room-verification`]) — re-checking **both** the work (against requirements/architecture) **and** the campaign machinery (is the merge gate actually non-empty? is everything claimed "released" really tagged with a `success` CI run, not `cancelled`? — the campaign invariants in the operating contract). Across a multi-feature round the machinery failures are the ones per-feature review misses.

## The compose loop (ordered steps, each producing a concrete artifact)

### 0. Resolve the loop's tools through varve — pin before you build

Every step below invokes a tool, and by default gets *whatever is on PATH*. That is the
mixed-toolchain hazard: half the pipeline running on one tool version and half on another, producing
an artifact no single toolchain ever built. Pinning a **varve** layer closes it by construction and
makes the outputs traceable to an exact toolchain.

Two committed files — the realm supplies the registry and the trust root, so **no environment
variable is needed**. Take the realm definitions from the published asset rather than pasting a
key; the rolling root is provisional and will rotate at the v1.0 ceremony:

```sh
# the canonical realm definitions ship with every varve release
gh release download --repo pulseengine/varve -p varve-realms.toml
```

```toml
# varve.toml — this project's pin
manifest-version = 1

[toolchain]
realm   = "pulseengine"
channel = "rolling"
layer   = "2026.08.2"
```

```sh
varve install          # fetch + verify + lay down the layer
varve shim install     # shims on PATH; switching projects is `cd`
varve which rivet      # which binary runs here — and which layer it came from
```

- **State the layer when you report results.** `varve which <tool>` prints the layer and manifest
  digest; that identity is what makes "which toolchain produced this?" answerable later. A result
  reported without it is not reproducible evidence.
- **A refusal is the feature.** Outside a pinned project a shim exits 1 rather than falling back to
  an ambient binary. Do not "fix" that by bypassing varve — fix the pin.
- **Prefer the realm over `VARVE_TRUST_ROOT`.** The realm is authoritative and cannot be overridden
  by the ambient environment; the env var can. See the roster entry in
  [`pulseengine-toolchain`] for the negative control establishing this.
- If a repo has no pin yet, say so plainly rather than implying the loop ran pinned. Adding
  `varve.toml` is a reviewable change like any other — and per **varve**'s design, the *only* way a
  project ever changes layers.

**Artifact:** a committed pin, and a layer identity attached to whatever the loop produces.

> The **rolling** channel is provisional and makes no qualification promise; its root rotates at the
> v1.0 ceremony. That is precisely why the realms file is *downloaded*, not pasted. Verified
> empty-handed on varve v0.14.0: published assets only, fresh store, no `VARVE_TRUST_ROOT` —
> `installed layer 2026.08.2 … verified: signature OK, 9 tool(s) match their signed digests`.

### 1. Start in spar — model the architecture

If the feature changes architecture (new component, new mode, new interaction, new resource sharing):
- Edit / create the AADL model in spar's `.aadl` files.
- Run the relevant spar analysis passes:
  - EMV2 fault trees if it touches safety.
  - ARINC 653 partitioning if it's an avionics-style isolation question.
  - ASIL decomposition if it's automotive.
  - Modal-filtered scheduling + piecewise-affine TSN arrival curves if it touches timing.
- Confirm the analysis passes are green for the new model.
- **Artifact:** updated `.aadl` files + spar analysis output.

### 2. Generate WIT from spar

WIT interfaces are *derived from AADL via spar*, never hand-written. From `wohl/spar-generates-wit.md`.
- Run the spar → WIT generator.
- The new WIT lands in the consumers (wohl, witness, etc.).
- **Artifact:** updated `.wit` files. Their diff against main is a function of the AADL change, not a manual edit.

### 3. Write typed requirements / decisions / tests in rivet

For each new property the feature claims:
- Add a requirement / decision / test artifact in the project's rivet directories.
- Use the appropriate schema (STPA, ASPICE, IEC 61508, DO-178C, EN 50128, EU AI Act, or custom).
- Link via rivet's typed predicates: `verifies`, `implements`, `traced-by`.
- Run `rivet validate` and `rivet check` — both must be green.
- **Artifact:** new YAML in `requirements/`, `decisions/`, `tests/`. `rivet coverage` should show the trace topology now covering the new property.

**Close the right side of the V when the test lands — don't defer it.** The
left side grows fast because authoring it is natural; the right side gets
skipped silently, every feature, until the debt is measured in the hundreds
(one repo: **257 of 269 sw-reqs with no verification**; another: 20 artifacts
and *one* `verifies` link). The cheap path is a **source marker**, not a
hand-authored YAML artifact per test:

```rust
// rivet: verifies REQ-001          // also: #[rivet::verifies("REQ-001")]
#[test]                             // Python: # rivet: verifies REQ-001
fn add_does_not_overflow() { ... }  //         @rivet_verifies("REQ-001")
```

Then, the moment the oracle is green:

```sh
rivet coverage --tests    # marker → requirement map; the burn-down list
rivet verify REQ-001      # advances implemented → verified, opt-in and auditable
```

**If a criterion belongs to another project, say so in the requirement and hold
the artifact at `implemented`.** The loop is shaped for one repo; the work often
is not. A criterion only a downstream consumer can run is not missing evidence —
it is evidence that is not yours to produce, and promoting without it asserts
exactly the property you did not check. See [`traceability-audit`] →
*"Verified is not always decidable inside this repo."*

`rivet verify` **refuses without evidence** — *"no verifying evidence. Add an
incoming `verifies` link … or a `// rivet: verifies REQ-001` marker"* — so this
is a mechanical check, not a prose step. Use `partially-verifies` when the test
discharges only part of the requirement. If the loaded schema has no
verification type at all, that is the finding: see [`traceability-audit`] step 0.

### 4. Write the code, oracle-gated per change

Per [`oracle-gate-a-change`]:
- Identify the mechanical oracle for each property the code claims (rivet check / Kani / Verus / fuzz / witness gap / sigil verify / `nm` symbol check).
- Write missing oracles first.
- Land code that flips the oracle from red to green.
- Each PR passes through `oracle-gate-a-change`.
- **Artifact:** code diff + a now-green oracle traceable to the rivet requirement.

### 5. Witness — MC/DC truth table on the Wasm artifact

If the feature lands a new branch / decision / variant:
- Run `witness` on the relevant Wasm component.
- Inspect the **truth table** (not the coverage percentage) — confirm masking / unique-cause vectors exist for each new condition.
- If gaps appear, witness-viz suggests test stubs — add them, rerun.
- **Artifact:** truth table file under `witness-out/` (or similar) showing zero unresolved gap rows.

### 6. Sigil — sign the attestation chain

If the feature lands a new build artifact or a new build-stage:
- Run sigil to sign the relevant outputs.
- Confirm the verification chain end-to-end: detached verifier accepts the signed artifact.
- **Artifact:** signed component manifest, verifiable detached.

> **Recurring N/A is a backlog item, not an exemption.** Steps 5 and 6 are
> conditional ("if the feature lands…"), which makes them easy to wave off. If you
> mark either one N/A for the same reason **three features running**, file it (an
> issue / [`report-tool-friction`]) — that pattern is exactly how a real-flight
> MC/DC gap and a missing attestation chain stayed hidden across ~20 features.

### 7. Clean-room verify the whole loop

Per [`clean-room-verification`]:
- Write the feature's claims as discrete falsifiable claims.
- Spawn smithy (or equivalent subagent) cold — no inherited framing.
- Reconcile.

### 8. Land via release-execution

When the feature is green end-to-end, ship it via [`release-execution`]. Its **traceability completeness gate** is where this loop gets audited at release time: every `approved`/`implemented` artifact must have the full V closed — requirement → architecture → implementation, and up the right side (tests via `verifies`, witness MC/DC with zero gap rows, sigil attestation). If a step here was skipped, that gate is where it surfaces as a blocker. Include the falsification statement for the new behavior in the release notes.

**Own the merge-wait — don't delegate and assume.** The merge must block on the required gate: a PR that landed in seconds didn't wait for CI, and a tag on that commit is not verified. Confirm the merge actually waited (HEAD run `completed`/`success`, not `cancelled` by a merge-train and not skipped on an empty gate) before treating the feature as shipped. This is the same assert release-execution makes — the loop doesn't get to skip it just because it handed the merge off. *(Restated inline for execution-time reachability — the deliberate redundancy exception to single-source; see [`pulseengine-operating-contract`] → "Single-source by default". Keep in sync; don't drift-sweep it away.)*

## What "MBSE is mandatory infrastructure" means here

This loop is not optional ritual. It's the cheap version of safety-critical engineering — agent-minutes replace half-a-day-per-requirement, the model drives the build instead of sitting alongside it, and the alternative (untraceable AI-authored code) is unshippable in regulated domains.

The loop's *cost* is now in tooling, not labor. Skipping a step skips the corresponding evidence; assessor confidence is the metric, not throughput.

## Anti-patterns

- Hand-writing WIT files. Spar generates them; if WIT changes, the AADL changed first.
- Writing code before the rivet typed artifacts exist. The traceability must lead, not follow.
- Trusting `witness` coverage percentages. Read the gap rows in the truth table. From `witness-the-truth-table-not-the-percentage` and `witness-wasm-mcdc`.
- Skipping sigil "because internal." If the artifact ever leaves your machine — including to CI — the attestation chain is the gate that lets others trust what you built.
- Inlining clean-room verification or oracle-gating instead of pointing at those skills. Duplication is the failure mode this whole stack is designed to avoid.
- Working around a tool silently. If you hand-edit generated WIT, `|| true` a failing check, or do a step outside the tool "for now," that's friction — file it via [`report-tool-friction`]. Unreported workarounds are how the tools stop improving.
- Calling the feature "done" before all eight steps have a green artifact.

## Where this composes

Sits at the top of the composition tree. Calls [`oracle-gate-a-change`] per change. Calls [`clean-room-verification`] for the verify step. [`report-tool-friction`] runs as a standing practice across every step. Hands off to [`release-execution`] when green — whose traceability completeness gate audits the artifacts this loop produced.
