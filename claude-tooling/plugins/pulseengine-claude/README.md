# pulseengine-claude

PulseEngine engineering methodology as installable Claude Code tooling.

## What's inside

- **Reference memory** (`memory/`) — auto-injected at session start via the plugin's SessionStart hook:
  - `pulseengine-philosophy.md` — verification + traceability + attestation, falsification methodology, defense-in-depth, MBSE-mandatory, variant pruning, the three-patterns synthesis.
  - `pulseengine-toolchain.md` — directory of the tools (rivet, spar, witness, sigil, meld, loom, synth, smithy, wohl) and what each is for.
  - `pulseengine-repo-taxonomy.md` — the two kinds of PulseEngine repo and which lens to use: **toolchain development** (the tool builds itself — inward; oracle-gate the tool, dogfood the chain) vs **toolchain consumer/application** (compose the full feature loop outward). Picks the right methodology per repo.
  - `pulseengine-operating-contract.md` — **how to run the skills on capable, agentic models** (the most capable tier available — the file routes by tier, never by version), grounded in Anthropic's *Prompting Claude Fable 5* guide: ground every progress claim in a tool result; never merge around a red/absent gate; **verify the machinery, not only the artifacts** (campaign invariants: assert the required-checks gate is non-empty; merged ≠ released — claimed-released items must carry a tag + a `success` run; a `cancel-in-progress` merge train leaves the tagged commit's CI unverified); assessment-is-a-deliverable boundaries; finish the turn you promised; minimal scope; don't transcribe reasoning into output (it trips a silent Opus fallback); watch for classifier fallback on crypto work; and the **skill disposition + model routing** — driver / hybrid / explorer / cross-cutting, every skill classified (drivers on a biddable model at low–medium effort; hybrids route their judgment half to a capable model; explorers on the most capable model at higher effort), plus the **always-on direction of travel** — push mechanical subtasks *down* a tier behind a cheap oracle, escalate only on a mechanical failure, and never treat the top tier as the oracle (see `delegate-by-cost`). The prompt-layer twin of oracle-gating.

  - `pulseengine-cli-conventions.md` — the org CLI baseline every tool's command line must meet (`--version` prints `<binary> <semver>` and exits 0, unknown flags exit 2, structured output is `--format json`), with the measured state that produced each rule.
  - `pulseengine-prose-conventions.md` — how agent-written text should read — commit messages, PR bodies, issue text, blog posts — with the tell-frequencies measured across this repo's own output.

- **Memory-persistence hooks** (`hooks/`) — keep work from starting cold:
  - `pulseengine-generated-media.md` — what we may publish as video or animation and what it may never stand for: the EU AI Act Article 50(4) limbs we sit outside and why, and the harder in-house rule that a generated depiction must never substitute for a measured result.
  - **SessionStart** injects the methodology memory *and* situational awareness (git branch / status / recent commits, a best-effort repo-category guess, and the working-context resumed from last time).
  - **SessionStart** also writes one line into `$CLAUDE_ENV_FILE` (`hooks/persist-shell-options.sh`), which Claude Code runs before every Bash command: `if [ -n "$ZSH_VERSION" ]; then setopt no_nomatch no_equals; fi`. Under zsh, an unmatched glob (`--include=*.py`, a `?` in a URL) no longer aborts the command with `no matches found`, and `echo ===` no longer fails with `== not found`; under bash the line does nothing. Appended once however often SessionStart fires, never truncating what other hooks wrote. `pipefail` is deliberately not set.
  - **SessionStart + SessionEnd** also run the factory-notice inbox (`hooks/factory-notice.sh`): at start, list any answers waiting and, only inside the owner's decision windows, this agent's surfaced decisions, consuming nothing; at end, post a minimal automatic session summary if the agent posted none and the session changed something, then hand the outbox to a detached sync so the session never waits on warte. The start hook uses warte only if it answers within 3 seconds; both exit 0 on every path and are silent on failure.
  - **PreToolUse (Agent)** adds a one-line reminder to choose `model:` per `delegate-by-cost` (`hooks/agent-model-reminder.sh`) when an Agent call has no `model:` and its `subagent_type` is absent, `general-purpose` or `claude`. It only adds context: it never denies, approves or rewrites the call, and it exits 0 silently on anything else, a missing or crashing python3 included. Claude Code delivers the context with the call's result, so it shapes the next call, not this one. Throttled per session: it reminds on the first such call and then on every 10th consecutive one, and a call that sets `model:` resets the count. The count lives in one small file per `session_id` under `$CLAUDE_PLUGIN_DATA/agent-model-reminder/` (else `$TMPDIR/pulseengine-claude/agent-model-reminder/`), written atomically and pruned after 7 days; missing or corrupt state fails open to a reminder, never to a blocked call.
  - **PreCompact + SessionEnd** save a `.claude/pulseengine/working-context.md` checkpoint (git state + an agent-maintained notes section, kept out of git via `.git/info/exclude`) so context survives compaction and carries to the next session.

- **Skills** (`skills/`) — loaded on trigger only:
  - `clean-room-verification/` — the smithy ritual: findings → falsifiable claims → cold subagent → confirm/refute/cannot-verify → reconcile.
  - `release-execution/` — end-to-end release machinery: PRs → reviewers → fixes → merge → CI → **V-model traceability completeness gate** → tag → GitHub Release + crates.io verify. The gate blocks the tag until every `approved`/`implemented` artifact has a closed V (req → arch → impl) and green right-side evidence (tests, witness MC/DC, attestation). Includes the per-release falsification statement.
  - `oracle-gate-a-change/` — per-change procedure: name the mechanical oracle (rivet check / spar pass / witness gap / `wsc verify` / Kani / Verus / fuzz / nm symbol check), write it first if it doesn't exist, only the diff that flips it counts.
  - `pulseengine-feature-loop/` — end-to-end compose loop: spar (AADL) → WIT → rivet typed artifacts → code (oracle-gated) → witness MC/DC → sigil attestation → clean-room verify.
  - `release-artifact-pipeline/` — the standardized release across **five tracks**: (A) native binaries — signed `SHA256SUMS.txt`, CycloneDX SBOM, SLSA attestation, cosign keyless OIDC (canonical: `pulseengine/synth`); (B) distribution — crates.io for everything Rust + npm for CLIs; (C) wasm — sigil + cosign signing and **witness MC/DC + scry** verification gates, holding wasm to the same bar as the binary; (D) a Pages verification dashboard (witness-viz/scry-viz); (E) rivet verification extraction (the relay/gale test-level `verifies` pattern). Built from an org-wide release-consistency sweep.
  - `report-tool-friction/` — standing dogfooding practice: when a tool errors, misbehaves, or forces a workaround during real work, file it as a `tool-friction` issue in the tool's own repo — automatically, as you hit it. Referenced by the feature loop and release execution.
  - `capture-session-learnings/` — continuous learning: distill a session's resume-state into the working-context checkpoint, and promote durable patterns/decisions into memory or a new skill. The agent-authored counterpart to the memory-persistence hooks; where recurring `report-tool-friction` workarounds get promoted so they stop recurring.
  - `stpa-audit/` — conduct or **audit** an STPA / STPA-Sec hazard analysis on rivet's typed artifacts: completeness as a mechanical oracle (`rivet check` over the loss→hazard→constraint→UCA→scenario closure rules + STPA-Sec CIA/adversarial-causation/attacker-type) plus soundness as a clean-room reasoning review. The safety-case front-end of the feature loop; feeds the release V-model gate.
  - `proof-synthesis/` — **backend-agnostic** generate→verify→refine loop for machine-checked proofs across Verus, Rocq/Coq, Lean 4, Dafny, Kani, and scry's abstract interpretation. The verifier's own output is the oracle (never an LLM judge); grounded in AutoVerus/AutoRocq research. The proof-side counterpart of `stpa-audit`; the per-change loop behind the feature loop's Verify step.
  - `traceability-audit/` — ensure the rivet trace is **complete and bidirectional across the whole V** for **any standard** (DO-178C, ISO 26262, EN 50128, IEC 61508, IEC 62304): requirement → architecture → design → code, and back up through **unit / integration / requirements-qualification** tests + witness MC/DC + sigil, via `rivet check` closure rules. Covers the *research/exploration phase* too. The detailed closure-rule definition behind release-execution's V-model gate.
  - `bootstrap-verification/` — **greenfield on-ramp**: stand up the verification scaffolding for a new or not-yet-built piece — pick the standard(s)/integrity level, `rivet init`, scaffold STPA + the traceability skeleton, seed the top of the V (losses → requirements) and wire the piece into the feature loop, release gate, and compliance/MC-DC reporting — so it's traceable from commit one. Use it *before* the feature loop, including for work that doesn't exist yet.
  - `release-planning/` — plan releases **in rivet** (assign requirements to releases via the `release:` field + status lifecycle; readiness is a query, not a calendar) and run the **issue-driven delivery loop**: an error/regression/optimization comes in → evaluate (measure, don't guess) → land it as a rivet artifact assigned to a release → run the full chain → ship. Grounded in how synth/loom/kiln actually work; composes with the feature loop, traceability-audit, and release-execution.
  - `issue-hunt/` — the **incremental bug/feature hunt loop**: each pass picks up only what's *new since the last pass* (new issues + new comments, via a git-excluded per-repo watermark — with a self-echo filter so the loop's own triage comments don't re-trigger it, and a `pending_gates` record so a PR it opens but can't land this pass gets owned and merged on a later pass), digests + triages it, works the actionable items through the chain, and accumulates toward a feature release. One invocation = one pass; designed to run on `/loop` or a scheduled agent. The tracker-facing front of `release-planning`.
  - `claim-verification/` — treat a document's **load-bearing claims as gated requirements**: a README badge/tagline/"formally verified"/trusted-base number is a claim that must stay true, so *mark* the assertion, *bind* it to evidence a machine re-derives (proof file exists, `external_body`/`admit`/`sorry` counts recounted from source, badge string == the honest wording), and *gate* it so drift fails the build — truth-over-time as a property of the gate, not the author. Ships a runnable reference `claim-check.py` + `claims.example.yaml` (models the loom/gale/relay drifts). Gate the claims, not the narrative. The doc-facing sibling of `traceability-audit`.
  - `repo-hygiene/` — the **post-release residue sweep**: stale worktrees, dead local/remote branches (including squash-merge artifacts git cannot see as merged), ancient stashes, per-agent build caches, status noise, and the open-issue board. **Quiesce-gated** — the sweep mutates (removes worktrees, deletes branches, `rm -rf`s caches), so it proves the tree is idle before it acts, which makes it safe to run inside a live multi-agent campaign. Closure is evidence-based: an issue closes against a tagged release, or as obsolete/superseded with a rationale, or stays open with an explicit `remaining:` note — never silently.
  - `gate-potency/` — **can this check still go red?** The inherited-gate counterpart to `oracle-gate-a-change`: that one covers the oracle you are authoring, this one the gate that has been green since before you arrived and was never re-proved. **Presence is not potency** — a non-empty required-checks list proves a gate exists, never that it bites. Method is negative control (inject a violation, confirm red) plus six mechanical audits for the ways a gate goes inert. The failure it prevents is the worst a verification methodology can have: confident, documented, auditable green over unverified code.
  - `verify-your-own-claims/` — the contract says ground every claim in a tool result; this catches the failures where the claim **was** grounded and still wrong, because it **reached further than the instrument could see**. Fires before reporting a finding, writing a PR body, or asserting anything that generalizes ("only X and Y do Z"), asserts a cause, asserts a negative, or reports a measurement as clean ("0 found"). Name the instrument, then name what it is blind to. The conversation-facing sibling of `claim-verification`, which gates documents with CI — here there is no build to fail, so the check has to be a procedure you run.
  - `evidence-transfer/` — the harder sibling of `gate-potency`: the check that **can** go red, **does** assert a real property, and reports something **true** — about a substrate that is not the one the claim is about. "On-target", "on silicon", "in production", "the released binary". More dangerous than a vacuous gate precisely because the result is correct, so reviewers read it, agree, and move on; the defect lives in one adjective in a test title. A passing test licenses a claim about the system it ran on and nothing else — every step from *that* system to *the* system is an inference needing its own evidence.
  - `delegate-by-cost/` — **choose `model:` before every Agent call**: from an opus or fable parent, mechanical work with an exact check goes to `haiku`, `sonnet` only where judgment short of top-tier is needed, and a call without `model:` runs at the parent's price by default. The reason is cache reads, which dominate delegated work: on the published rates the `haiku` cache read is a twentieth of `opus`'s (a quarter past 100K-token prompts) and `sonnet`'s is half, so a `haiku` hop removes about 95% of the bill (75% past 100K) and a `sonnet` hop half. Grade the worker against the oracle (not its summary), escalate *up* one rung at a time only on a mechanical failure, and at the top rung stop and ask the user. The gate is economic: with a cheap oracle the break-even is `p > r`; when verifying costs what producing costs the ladder is a cost *trap*. Rewritten in 0.47.0 after a transcript study found the first version invoked 0 times in 1,531 sessions.
  - `ci-status/` — **waiting on CI without polling blind**: before polling GitHub for a PR's checks, ask the self-hosted fleet's read-only status API whether the jobs are running, queued (with a measured start range from now, not a promise, and an `overdue` flag that is reported to the user once) or not queued at all, and wake after the API's own `recheck_after_s`. The API's address comes only from `PULSEENGINE_CI_STATUS_URL` / `PULSEENGINE_CI_STATUS_CACERT`, never from a file in a repo; when unset or unreachable the skill says so once and falls back to `gh pr checks` (0 pass, 1 fail or no checks, 8 pending), waking every 15–30 minutes. **Before opening a PR** it checks admission: warte's `/api/admission` via `PULSEENGINE_WARTE_URL` / `PULSEENGINE_WARTE_CACERT` once that endpoint exists (pulseengine/warte#55), else the repo's queued-run count from the fleet's `/api/state`, else from GitHub. `security` and red-`main` fixes always open; trivial changes batch onto the session's own PR; other changes hold locally while the repo has 5 or more queued runs. A claim fails the build if a private host or certificate path appears in the plugin.
  - `publication-review/` — **a role-split panel before public prose ships**: before `ready = true` on a post, or before any public page that quotes sources, cites standards, prints tool output or states numbers, three cold reviewers check it: a domain expert (claims at the strength the evidence supports, real standard and process IDs), a fact-checker (primaries fetched, quotes word for word, repo numbers re-derived with the pinned tool version) and an editor (the house prose rules). A separate fixer applies only confirmed findings, a fresh second round reviews the result, and three rounds without convergence stop and hand back to the user. Any refuted quote, number or citation, any overclaim about verification or proof, or any private infrastructure detail blocks publication. Written after four model-drafted posts shipped or were scheduled in three days with an invented quotation clause, invented CLI output, a non-existent book and wrong ASPICE process IDs, all under a green build.
  - `factory-notice/` — **the owner's inbox for unattended agents**: one notice per event (`shipped`, `blocked`, `session-summary`, `info`, `heartbeat`) and, at a fork the agent would otherwise ask about, a `needs-decision` option dialogue with each option's description, pros and cons, the agent's recommendation and why, what it blocks and whether it is reversible. The agent does not take the fork, carries on with independent work and `poll`s on each wake; it never applies its recommendation on a timeout, and irreversible actions always wait. `notice.py` (stdlib only, one versioned schema in `notice.schema.json`) writes to warte as `notice.v1` / `answer.v1` when `PULSEENGINE_WARTE_URL` answers, and always to a user-level store under `~/.local/state/pulseengine/notices/`, so it works with no warte and survives worktree deletion. Because an answer is an instruction and a row in warte is not proof the owner wrote it, an answer is accepted only for an option the agent offered, at the notice's current revision, for a notice id it posted, exactly once, checked against the agent's local copy; the answer's note is quoted as data. An attention budget rations the owner, on a schedule he sets in warte (`GET /api/attention`, then its cached copy, then `~/.config/pulseengine/attention.json`, then defaults; weekday windows, available hours, focus blocks and off periods): 3 flows ask at a time and the rest are queued, kept and promoted as flows clear (a `security` or `red-main` tag bypasses the cap, the windows and focus blocks, never an off period); questions reach him only in decision windows (08:30-09:00 and 17:00-17:30 by default), where `notice.py window-tick` refreshes one grouped `DIGEST.md` and posts one notification carrying only two counts; `notice.py review` answers them in one sitting.
  - `refactor-decision/` — **when to stop patching and refactor, and how**: four triggers (a feature that does not fit the structure, a second copy of a rule or a second path for one decision, a re-fix chain or review cluster, small cleanups in code already being edited), each with what counts as evidence. A re-fix chain or review cluster yields a recorded none/small/large decision rather than an automatic refactor, every refactor needs evidence that behaviour held, and a bare "refactor X" with no purpose is clarified first. Measured on relay (pulseengine.eu#294). It excludes pulseengine/rivet and pulseengine/spar until 2027-02-01, so the pre-registered hotspot experiment keeps its "no other process change" condition, and checks the repository's remotes before applying.

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

Equivalent from the shell: `claude plugin marketplace add https://github.com/pulseengine/pulseengine.eu`. A bare `github.com/owner/repo` (no scheme) and the old two-argument `<name> <coords>` form are **not** accepted by current Claude Code — the two-argument form fails with `✘ Invalid marketplace source format`.

### Using the skills from other agent runtimes

The skills are plain `SKILL.md` files, so runtimes other than Claude Code can
load them. Only `skills/` travels this way — `memory/` and `hooks/` are Claude
Code plugin mechanisms with no equivalent elsewhere, so those sessions get the
procedures without the always-on framing.

**GitHub Copilot CLI** — discovers skills from `.github/skills/`,
`.agents/skills/`, `.claude/skills/`, `~/.copilot/skills/`, installed plugins,
or a directory you add. This plugin's skills are under `claude-tooling/`, none
of those, so add the directory:

```sh
copilot skill add claude-tooling/plugins/pulseengine-claude/skills
copilot skill list                 # 23 custom skills, no failure section
copilot skill remove claude-tooling/plugins/pulseengine-claude/skills
```

**opencode** — scans `.opencode/skill(s)/<name>/SKILL.md` in a project and
`~/.config/opencode/skill(s)/` globally, and **auto-loads `~/.claude/skills/`
and `~/.agents/skills/`** without configuration. For a directory outside those,
add it to `opencode.json` (`skills.paths` is scanned recursively for
`**/SKILL.md`):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "skills": {
    "paths": ["/abs/path/to/pulseengine.eu/claude-tooling/plugins/pulseengine-claude/skills"]
  }
}
```

```sh
opencode debug skill      # lists every skill that resolved, with its location
```

Config is read once at startup and is not hot-reloaded, so restart opencode
after editing. `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` turns off the
`~/.claude/` scan if you want only the explicit paths.

### The description limit bites hardest here

**A description over 1024 characters does not warn — the skill fails to load.**
The runtime lists the others and says nothing where the missing one belongs:

```
✖ The following skills failed to load:
  • traceability-audit/SKILL.md: Skill description must be at most 1024 characters
```

Two skills were 11 and 35 characters over before this surfaced, and Claude Code
loaded them fine throughout — `claude plugin validate` checks manifests, not
skill frontmatter, so nothing caught it. `scripts/check-skill-frontmatter.py`
now gates it in CI (`name` ≤ 64 and matching its directory, `description`
≤ 1024). Run it after editing any frontmatter.

## Design

Partition rule: **belief / disposition / vocabulary stays in memory; multi-step procedure becomes a skill**. The memory files describe always-on framing for every session. The skills load only when their trigger fires — proposing a change, cutting a release, auditing findings, doing a feature end-to-end.

The skills compose: `pulseengine-feature-loop` orchestrates a feature; `oracle-gate-a-change` runs per change inside the loop; `clean-room-verification` is the verify step both feature-loop and oracle-gate point at; `release-execution` ships the result and gates the tag on V-model completeness; `report-tool-friction` runs as a standing practice across all of them, turning every workaround into a tracked issue.

The hooks and `capture-session-learnings` close the loop *across* sessions: the memory-persistence hooks save/restore the mechanical checkpoint, and the skill writes the narrative half they can't — promoting recurring patterns (including friction workarounds) into durable memory or new skills. The `pulseengine-repo-taxonomy` memory ensures each session applies the right lens for the repo it's in (tool-development vs consumer/application).
