---
name: bootstrap-verification
description: This skill should be used to stand up the PulseEngine verification scaffolding for a NEW or not-yet-built piece — a greenfield repo, a fresh component, or work that doesn't exist yet — so it is traceable and verifiable from commit one rather than retrofitted later. Use it when starting something from scratch, when a repo/component has no rivet project yet, or when the user says "bootstrap this", "set this up properly from the start", "I want to use this on a piece I haven't done yet", or "get the verification scaffolding in". It picks the target standard(s), runs rivet init, scaffolds STPA/STPA-Sec + the traceability skeleton, seeds the top of the V, and wires the piece into the feature loop, release gate, and compliance/MC-DC reporting — the greenfield counterpart to pulseengine-feature-loop (which assumes an existing project).
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# Bootstrap verification

The cheapest verifiable system is one that was traceable from its first commit;
the most expensive is one where the analysis is reconstructed at the end. This
skill is the **greenfield on-ramp**: given a piece that may not exist yet, it
stands up the rivet scaffolding, seeds the top of the V (losses → requirements),
and wires the piece into the loop so that *every subsequent change lands already
traced*. It is PulseEngine's MBSE stance made operational — the analysis and
requirements lead, the code follows, and `rivet check` is meaningful before
there's a line of implementation.

> Use this **before** `pulseengine-feature-loop`, not instead of it. Bootstrap
> creates the structure and the trace roots; the feature loop grows the piece
> against them.

## Steps — from nothing to a verifiable piece

### 1. Decide what "verifiable" means here
- **Target standard(s)** — DO-178C / ISO 26262 / EN 50128 / IEC 61508 /
  IEC 62304 / ASPICE / SOTIF / EU AI Act (a piece may carry several). This
  picks which rivet schemas to enable.
- **Integrity level** — DAL / ASIL / SIL / safety class — set it now; it
  propagates down the chain (see [`traceability-audit`]).
- **Category** — is this a tool or a consumer/application? (see
  [`pulseengine-repo-taxonomy`] memory) — it sets which lens dominates.

### 2. Scaffold the rivet project
- Run **`rivet init`** to create the rivet project + `rivet.yaml`; declare the
  chosen schema(s) in it.
- Create the artifact tree: `safety/stpa/`, `safety/stpa-sec/`,
  `requirements/`, `decisions/`, `tests/` with `_index` stubs.
- Confirm `rivet validate` is green on the empty skeleton.

### 3. Seed the top of the V (this is the "bootstrap" — it works with zero code)
- **Losses & hazards** via [`stpa-audit`] — even for an unbuilt piece you can
  state the stakeholder losses and system-level hazards; that's the whole point
  of doing it first. Add the STPA-Sec security pass alongside (shared control
  structure).
- **Top-level requirements / safety goals** as the trace roots, linked from the
  hazards/constraints. Mark them `draft` until reviewed.
- These seeds are placeholders the real analysis fills — but they make the trace
  graph *exist*, so it can only ever grow closed.

### 4. Wire the piece into the loop
- **`pulseengine-feature-loop`** drives each feature from here: architecture
  (spar) → design → code → tests, every artifact linked.
- **`traceability-audit`** defines what "closed at every level" means as the
  piece grows; run `rivet check` from commit one so gaps surface immediately,
  never accrue.
- **`proof-synthesis`** if the piece carries proofs (Verus/Rocq/Lean/Kani/scry).

### 5. Wire the release + evidence plumbing
- Add the standardized release pipeline ([`release-artifact-pipeline`]) and, if
  the piece produces a rivet compliance report or witness MC/DC, the
  `compliance.yml` / witness-evidence publishing so it surfaces on
  pulseengine.eu (mirror the rollout used for loom/synth/wohl/meld).
- The release V-model gate ([`release-execution`]) now has a real chain to gate
  on — from the very first release.

## Why bootstrap-first matters
- **You can use the methodology on work you haven't done yet.** Losses,
  hazards, and requirements are authored against the *intended* system; the
  implementation is then built to satisfy a trace that already exists.
- **No retrofit scramble.** A piece bootstrapped this way never faces a
  release-time traceability gap because the graph was closed incrementally.
- **Consumers get parity with tools.** Application repos (wohl, relay, new
  pieces) that today author no STPA can be stood up the same way the toolchain
  repos are.

## Where this composes
- [`pulseengine-repo-taxonomy`] — pick the lens for the new piece.
- [`stpa-audit`] — seeds the hazard analysis at the top of the V.
- [`traceability-audit`] — the chain the bootstrapped piece grows into, closed
  at every level for whichever standard(s) it targets.
- [`pulseengine-feature-loop`] — takes over once the scaffold + roots exist.
- [`release-artifact-pipeline`] / [`release-execution`] — the evidence plumbing
  and the gate the piece ships through.
- [`report-tool-friction`] — if `rivet init` or the scaffolding has gaps.

## Anti-patterns
- **Writing code first, analysis later.** Bootstrap exists precisely to prevent
  this; the requirements/hazards lead.
- **Bootstrapping structure but leaving the trace roots empty** — a scaffold
  with no seeded losses/requirements is just empty folders; seed the top so the
  graph is real.
- **Skipping the standard/integrity-level decision** — retrofitting ASIL/DAL/SIL
  down a half-built chain is exactly the cost this skill avoids.
- **Hard-coding one standard** — choose per piece; some carry several.
