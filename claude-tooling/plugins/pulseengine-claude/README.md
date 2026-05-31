# pulseengine-claude

PulseEngine engineering methodology as installable Claude Code tooling.

## What's inside

- **Reference memory** (`memory/`) — auto-injected at session start via the plugin's SessionStart hook:
  - `pulseengine-philosophy.md` — verification + traceability + attestation, falsification methodology, defense-in-depth, MBSE-mandatory, variant pruning, the three-patterns synthesis.
  - `pulseengine-toolchain.md` — directory of the tools (rivet, spar, witness, sigil, meld, loom, synth, smithy, wohl) and what each is for.

- **Skills** (`skills/`) — loaded on trigger only:
  - `clean-room-verification/` — the smithy ritual: findings → falsifiable claims → cold subagent → confirm/refute/cannot-verify → reconcile.
  - `release-execution/` — end-to-end release machinery: PRs → reviewers → fixes → merge → CI → **V-model traceability completeness gate** → tag → GitHub Release + crates.io verify. The gate blocks the tag until every `approved`/`implemented` artifact has a closed V (req → arch → impl) and green right-side evidence (tests, witness MC/DC, attestation). Includes the per-release falsification statement.
  - `oracle-gate-a-change/` — per-change procedure: name the mechanical oracle (rivet check / spar pass / witness gap / sigil verify / Kani / Verus / fuzz / nm symbol check), write it first if it doesn't exist, only the diff that flips it counts.
  - `pulseengine-feature-loop/` — end-to-end compose loop: spar (AADL) → WIT → rivet typed artifacts → code (oracle-gated) → witness MC/DC → sigil attestation → clean-room verify.
  - `release-artifact-pipeline/` — the standardized release.yml: signed `SHA256SUMS.txt`, CycloneDX SBOM, SLSA attestation, cosign keyless OIDC. Canonical implementation in `pulseengine/synth/.github/workflows/release.yml`.
  - `report-tool-friction/` — standing dogfooding practice: when a tool errors, misbehaves, or forces a workaround during real work, file it as a `tool-friction` issue in the tool's own repo — automatically, as you hit it. Referenced by the feature loop and release execution.

## Install

The marketplace manifest sits at the **repo root** of pulseengine.eu (under `.claude-plugin/marketplace.json`) so the install flow mirrors `anthropics/skills` exactly:

```
/plugin marketplace add pulseengine-eu github.com/pulseengine/pulseengine.eu
/plugin install pulseengine-claude@pulseengine-eu
```

(Run the first command inside Claude Code, or `claude plugin marketplace add ...` from the shell. Adjust GitHub coordinates to wherever you actually publish the repo.)

## Design

Partition rule: **belief / disposition / vocabulary stays in memory; multi-step procedure becomes a skill**. The memory files describe always-on framing for every session. The skills load only when their trigger fires — proposing a change, cutting a release, auditing findings, doing a feature end-to-end.

The skills compose: `pulseengine-feature-loop` orchestrates a feature; `oracle-gate-a-change` runs per change inside the loop; `clean-room-verification` is the verify step both feature-loop and oracle-gate point at; `release-execution` ships the result and gates the tag on V-model completeness; `report-tool-friction` runs as a standing practice across all of them, turning every workaround into a tracked issue.
