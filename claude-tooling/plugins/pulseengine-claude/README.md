# pulseengine-claude

PulseEngine engineering methodology as installable Claude Code tooling.

## What's inside

- **Reference memory** (`memory/`) — auto-injected at session start via the plugin's SessionStart hook:
  - `pulseengine-philosophy.md` — verification + traceability + attestation, falsification methodology, defense-in-depth, MBSE-mandatory, variant pruning, the three-patterns synthesis.
  - `pulseengine-toolchain.md` — directory of the tools (rivet, spar, witness, sigil, meld, loom, synth, smithy, wohl) and what each is for.
  - `pulseengine-repo-taxonomy.md` — the two kinds of PulseEngine repo and which lens to use: **toolchain development** (the tool builds itself — inward; oracle-gate the tool, dogfood the chain) vs **toolchain consumer/application** (compose the full feature loop outward). Picks the right methodology per repo.

- **Memory-persistence hooks** (`hooks/`) — keep work from starting cold:
  - **SessionStart** injects the methodology memory *and* situational awareness (git branch / status / recent commits, a best-effort repo-category guess, and the working-context resumed from last time).
  - **PreCompact + SessionEnd** save a `.claude/pulseengine/working-context.md` checkpoint (git state + an agent-maintained notes section, kept out of git via `.git/info/exclude`) so context survives compaction and carries to the next session.

- **Skills** (`skills/`) — loaded on trigger only:
  - `clean-room-verification/` — the smithy ritual: findings → falsifiable claims → cold subagent → confirm/refute/cannot-verify → reconcile.
  - `release-execution/` — end-to-end release machinery: PRs → reviewers → fixes → merge → CI → **V-model traceability completeness gate** → tag → GitHub Release + crates.io verify. The gate blocks the tag until every `approved`/`implemented` artifact has a closed V (req → arch → impl) and green right-side evidence (tests, witness MC/DC, attestation). Includes the per-release falsification statement.
  - `oracle-gate-a-change/` — per-change procedure: name the mechanical oracle (rivet check / spar pass / witness gap / sigil verify / Kani / Verus / fuzz / nm symbol check), write it first if it doesn't exist, only the diff that flips it counts.
  - `pulseengine-feature-loop/` — end-to-end compose loop: spar (AADL) → WIT → rivet typed artifacts → code (oracle-gated) → witness MC/DC → sigil attestation → clean-room verify.
  - `release-artifact-pipeline/` — the standardized release.yml: signed `SHA256SUMS.txt`, CycloneDX SBOM, SLSA attestation, cosign keyless OIDC. Canonical implementation in `pulseengine/synth/.github/workflows/release.yml`.
  - `report-tool-friction/` — standing dogfooding practice: when a tool errors, misbehaves, or forces a workaround during real work, file it as a `tool-friction` issue in the tool's own repo — automatically, as you hit it. Referenced by the feature loop and release execution.
  - `capture-session-learnings/` — continuous learning: distill a session's resume-state into the working-context checkpoint, and promote durable patterns/decisions into memory or a new skill. The agent-authored counterpart to the memory-persistence hooks; where recurring `report-tool-friction` workarounds get promoted so they stop recurring.
  - `stpa-audit/` — conduct or **audit** an STPA / STPA-Sec hazard analysis on rivet's typed artifacts: completeness as a mechanical oracle (`rivet check` over the loss→hazard→constraint→UCA→scenario closure rules + STPA-Sec CIA/adversarial-causation/attacker-type) plus soundness as a clean-room reasoning review. The safety-case front-end of the feature loop; feeds the release V-model gate.
  - `proof-synthesis/` — **backend-agnostic** generate→verify→refine loop for machine-checked proofs across Verus, Rocq/Coq, Lean 4, Dafny, Kani, and scry's abstract interpretation. The verifier's own output is the oracle (never an LLM judge); grounded in AutoVerus/AutoRocq research. The proof-side counterpart of `stpa-audit`; the per-change loop behind the feature loop's Verify step.
  - `traceability-audit/` — ensure the rivet trace is **complete and bidirectional across the whole V** for **any standard** (DO-178C, ISO 26262, EN 50128, IEC 61508, IEC 62304): requirement → architecture → design → code, and back up through **unit / integration / requirements-qualification** tests + witness MC/DC + sigil, via `rivet check` closure rules. Covers the *research/exploration phase* too. The detailed closure-rule definition behind release-execution's V-model gate.
  - `bootstrap-verification/` — **greenfield on-ramp**: stand up the verification scaffolding for a new or not-yet-built piece — pick the standard(s)/integrity level, `rivet init`, scaffold STPA + the traceability skeleton, seed the top of the V (losses → requirements) and wire the piece into the feature loop, release gate, and compliance/MC-DC reporting — so it's traceable from commit one. Use it *before* the feature loop, including for work that doesn't exist yet.
  - `release-planning/` — plan releases **in rivet** (assign requirements to releases via the `release:` field + status lifecycle; readiness is a query, not a calendar) and run the **issue-driven delivery loop**: an error/regression/optimization comes in → evaluate (measure, don't guess) → land it as a rivet artifact assigned to a release → run the full chain → ship. Grounded in how synth/loom/kiln actually work; composes with the feature loop, traceability-audit, and release-execution.

## Install

The marketplace manifest lives at `.claude-plugin/marketplace.json` in the repo root of pulseengine.eu.

`/plugin marketplace add` takes **one source argument** — a full git URL or the `owner/repo` shorthand. It does **not** take a separate name argument (the marketplace name, `pulseengine-eu`, is read from `marketplace.json`). Run these inside Claude Code:

```
# Add the marketplace — full HTTPS URL (most reliable):
/plugin marketplace add https://github.com/pulseengine/pulseengine.eu
#   …or SSH:        /plugin marketplace add git@github.com:pulseengine/pulseengine.eu.git
#   …or shorthand:  /plugin marketplace add pulseengine/pulseengine.eu

# Install the plugin — <plugin-name>@<marketplace-name>, both from marketplace.json:
/plugin install pulseengine-claude@pulseengine-eu
```

Equivalent from the shell: `claude plugin marketplace add https://github.com/pulseengine/pulseengine.eu`. A bare `github.com/owner/repo` (no scheme) and the old two-argument `<name> <coords>` form are **not** accepted by current Claude Code.

## Design

Partition rule: **belief / disposition / vocabulary stays in memory; multi-step procedure becomes a skill**. The memory files describe always-on framing for every session. The skills load only when their trigger fires — proposing a change, cutting a release, auditing findings, doing a feature end-to-end.

The skills compose: `pulseengine-feature-loop` orchestrates a feature; `oracle-gate-a-change` runs per change inside the loop; `clean-room-verification` is the verify step both feature-loop and oracle-gate point at; `release-execution` ships the result and gates the tag on V-model completeness; `report-tool-friction` runs as a standing practice across all of them, turning every workaround into a tracked issue.

The hooks and `capture-session-learnings` close the loop *across* sessions: the memory-persistence hooks save/restore the mechanical checkpoint, and the skill writes the narrative half they can't — promoting recurring patterns (including friction workarounds) into durable memory or new skills. The `pulseengine-repo-taxonomy` memory ensures each session applies the right lens for the repo it's in (tool-development vs consumer/application).
