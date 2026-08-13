---
name: release-execution
description: This skill should be used when cutting, shipping, or finishing a release — including "ship it", "cut a release", "tag this", "release v0.X.Y", "take this to release", "work the PR queue to green", "finish the release tail", "publish", or any end-to-end release work that involves PRs, reviewers, merging, CI, tagging, GitHub Release, and crates.io publish. ALWAYS use this skill when the user authorizes autonomous release work or asks to "go as long as you can" on a release campaign.
metadata:
  author: pulseengine.eu
  version: "0.3.0"
---

# Release execution

## Operating discipline — this is a deterministic driver, not an exploration

Execute the procedure in order; **do not deviate, refactor, or "improve" it.** The
gate rules below are restated here on purpose — they gate a safety-critical action,
so they must be reachable at execution time even if the operating-contract memory
isn't loaded; that file carries the rationale, this carries the operational
asserts. *This is the deliberate **reachability-redundancy exception** to the
plugin's single-source rule ([`pulseengine-operating-contract`] → "Single-source
by default — restate inline only where absence is unsafe"): keep these in sync with
the contract; a drift-sweep must **not** re-consolidate them away — the redundancy
is the safety property.*
- **Never merge around a red or absent gate.** Merge only through passing required
  status checks — not to clear a queue, not because you judged it done.
- **A merge that landed in seconds didn't wait for checks** — that's a red flag,
  not a convenience; confirm the merge actually blocked on the gate.
- **"Verified" requires the green CI result**, not the local oracles. A tag on a
  commit whose HEAD run was `cancelled`/`red`/`queued` is not a verified release.
- **Ground every claim in a tool result** (and trust a test *exit code*, not a
  grepped "all green" summary).

What's specific to *this* driver:
- **A step that fails stops the turn** — report it with output, don't work around
  it. The turn ends at "pushed, and checks requested", never on a promise ("I'll
  watch it…") without the tool call.
- This is routine, deterministic work: **medium effort, dropping to low if it
  over-deliberates**. The effort knob is not the guard against drift — the boundary
  + minimal-scope contract is, and it holds at any effort.

## When this fires

End-to-end release machinery on a PulseEngine project (or any Rust project Ralf maintains). Triggers include: cutting a release tag, working a PR queue to green-and-merged, shipping a milestone, verifying a GitHub Release and crates.io publish landed, or fixing a release tail (post-merge cleanup, doc updates, version bumps).

## Procedure

Carry the whole sequence autonomously — that's the point. Stop only at the named forks below.

### 1. Assemble the queue
- Identify the set of PRs/branches that belong to this release.
- Order them by dependency. Independent ones go in parallel; dependent ones serialize.
- Open PRs that don't exist yet. Use branch names + PR titles per the project's convention (check the project memory for spar / synth / wohl style).

### 2. Drive PRs to green
- Dispatch reviewer subagents (multi-persona or specialized). Use `isolation: "worktree"` for parallelism without contention.
- For each finding from a reviewer: fix in the PR, push, wait for CI, repeat. Apply [`clean-room-verification`] to non-trivial findings before claiming them resolved.
- Watch CI status (`gh pr checks`, `gh run watch`). Re-run flaky checks; investigate genuine failures.
- Rebase / merge main into the PR branch when needed.

### 3. Merge
- Merge each PR once green. Squash, rebase-and-merge, or merge-commit per project convention.
- After each merge, kick the next dependent PR's CI if it needs to pick up the new main.

### 4. Traceability completeness gate (blocking — before tag)
The release does not get tagged until the V-model is closed for everything it claims to ship. This is the "what did we approve, what did we implement, is it all there and tested" check, made mechanical.

- Run rivet over the project: `rivet validate`, `rivet check`, and `rivet coverage`. All green is the entry condition.
- For **every artifact whose status is `approved` or `implemented`**, confirm the full chain exists and is traced — left side down, right side up:
  - feature → requirement → architecture (spar/AADL) → design decision → implementation, and
  - implementation → verification evidence → up the right side of the V: test(s) linked via `verifies`, witness MC/DC truth-table with zero unresolved gap rows for any new decision, sigil attestation for any new build artifact.
- The gate is **mechanical, not narrative**: an `approved`/`implemented` artifact with no `verifies` link, an untested branch (witness gap row), a requirement with no architecture above it, or an implementation with no requirement tracing to it is a **release blocker** — not a follow-up. Fix the trace or the test, or explicitly demote the artifact's status, before tagging.
- The rivet **compliance report** (the signed bundle the release-artifact pipeline produces, surfaced on pulseengine.eu) is the human-readable view of this gate. The report passing is necessary; the per-artifact check above is what makes it sufficient.
- **Record the toolchain that produced the evidence, not just the evidence.** *"Which toolchain
  qualified this artifact?"* is an assessor question, and it must be answerable from the release
  record alone. A manifest naming `rustc` and `cargo-component` while rivet, spar, meld and
  wasm-tools stay invisible does not answer it. Under a pin, the layer name + manifest digest
  (`varve which <tool>`) is that answer in one line; without one, list the tool versions explicitly.
  A gate result quoted without the binary that produced it is not reproducible — see
  [`oracle-gate-a-change`] step 4b for the measured case where the verdict flips between versions.
- If a *tool* can't express or verify part of the chain, that's friction → [`report-tool-friction`], then carry on with the gate.

The level-by-level closure rules — every requirement decomposed to architecture/design/code, and verified up through **unit, integration, and requirements-qualification** tests (with passing results), not just "has a `verifies` link" — are defined in [`traceability-audit`]; this gate is that audit run before tagging. It composes [`pulseengine-feature-loop`] (which produces the artifacts this gate audits) and [`clean-room-verification`] (verify the "the V is closed" claim cold, don't infer it from a green dashboard).

### 4b. Independence gate (blocking — solo-agent-authored repos)

Step 4 checks that the V is *closed*. This checks **who closed it**. Where one agent both authored
the work and marked it `verified`, that status carries no independent evidence — the one gap no
mutation score or green board closes.

- Every requirement in the release scope needs a **fresh-context clean-room review**
  ([`clean-room-verification`]) that re-derives the verdict from evidence rather than reading the
  author's summary.
- **Record reviewer identity, date and outcome on the artifacts**, so independence is auditable
  later rather than asserted now.
- **Absent or dissenting review blocks the tag**, exactly like a broken trace link. Canonical
  statement: varve's `REQ-INDEP-001` — *"No requirement is verified on the author's word alone."*

### 4c. Published-contract check (blocking — before tag, not in the tail)

Ask, explicitly: **does this release change something a downstream consumer binds to?** Registry
path, namespace, interface identity, artifact name, media type, `:latest` semantics. If yes, tell
the consumers **before** tagging — and prefer dual-publishing (or an alias) through a transition
over a clean cut.

Step 8 treats dependent-repo updates as tail cleanup. That is too late by construction: once tagged,
the artifact is already the thing they cannot find, and the failure surfaces as *their* bug report.

Field case — the whole lesson in one release: publishing moved from flat
`ghcr.io/<org>/<product>-<stage>` to nested `<product>/<stage>`. It **moved**; it did not
dual-publish. The flat repositories froze at the previous release with a stale `:latest` still
resolving, so the consumer checked exactly the paths they had been given, saw nothing new, and
reported that publishing looked *"stalled"* two releases back. They were right for the contract they
held.

The instructive part: a WIT **namespace rename** in the same release *was* pre-announced, carefully,
with a before/after table. The **path move** was not. Only the unannounced one caused harm —
announcing one breaking change made the coordination feel handled. So make it a checklist item, not
a judgement call: enumerate *every* published surface this release touches, not the one you happened
to be thinking about.

### 5. Tag and release
- **First assert the campaign invariants** ([`pulseengine-operating-contract`] → "Verify the machinery"): the protected branch's `required_status_checks.contexts` is non-empty (the gate is real), **HEAD's CI completed `success`** — not `cancelled` by a merge-train `cancel-in-progress`, which leaves the commit unverified — and everything previously claimed "released" actually carries a tag + a `success` run. A green-looking dashboard over an empty gate or a cancelled HEAD run is not a tag-able state.
- Once the queue is empty, main is green, **and the traceability gate (step 4) and the independence gate (step 4b) pass**, **PAUSE for fork**: confirm the new tag (`v0.X.Y`) and whether this is the right moment to cut, vs. holding for more. Use `AskUserQuestion` — this is a genuine decision boundary, not a routine step.
- After confirmation: tag, push tag, watch the release workflow; the release is "verified" only once that run completes `success`.

### 5b. Mind the notes-vs-assets race
If the flow publishes release notes at tag time while a workflow builds and
uploads platform binaries afterwards, downstream consumers polling the release
see it asset-less for those minutes and may file it as broken (it happened).
Either state "binaries attach ~N min after the tag" in the notes, or hold the
notes publish until the asset upload lands — pick one and keep it consistent.

### 6. Verify the release shipped
- GitHub Release: artifacts present, notes correct.
- crates.io: `cargo search <crate>` shows the new version.
- Any downstream — Docker image, Bazel rules dep update, MCP server restart — kicked.
- Apply [`clean-room-verification`] to the "release looks good" claim before reporting done.

### 7. Write the falsification statement
- Per PulseEngine methodology, every release should carry a falsifiable kill-criterion: "this release would be wrong if X is observed in the field." Add it to release notes or a follow-up issue.
- The point is to make the claim measurable, not to draft prose. One sentence is fine.

### 8. Release tail cleanup
- Doc updates, version bumps in dependent repos, milestone close-out, follow-up issues opened for known-deferred items.
- **Sweep the residue this release left** with [`repo-hygiene`] — stale worktrees, squash-merged branches git can't see as merged, orphaned per-agent build caches, and the issue board (close what shipped on this tag). A release tick is exactly when the worktree/branch set is unambiguous; run the sweep here so residue doesn't compound into the next campaign.
- This is where most teams quit too early. Don't.

## Forks where you stop and ask

These are non-routine and consequential — `AskUserQuestion` here, don't decide silently:
- **Cutting a new tag** (merge-all-and-tag vs. hold for more).
- **Breaking-API or version-scheme changes** (semver bump direction, deprecations).
- **Destructive git** (force-push to main, branch deletion of unmerged work, history rewrites).
- **Putting RC / unproven code on a safety or signing path** (anything that affects wohl OTA verification, sigil attestation, synth-produced binaries on a cover target).
- **Milestone scope choices** (does this PR belong in v0.X.Y or v0.X+1.0).
- **Demoting an artifact's status to pass the traceability gate** (step 4). Marking an `approved`/`implemented` artifact down so the gate goes green is a scope decision, not a mechanical fix — confirm it, don't do it silently.

Between these forks: keep moving. Single-letter prompts like "c" mean continue.

## Anti-patterns

- Waiting on green for an in-flight PR when the next work doesn't depend on it. Treat CI as async.
- Asking for confirmation between routine steps (merge a green PR, rebase, re-run a flaky check). Don't.
- Stopping at "tag pushed" without verifying the artifacts actually shipped.
- Skipping the falsification statement because "the release is small." Small releases still need kill-criteria.
- **Tagging with an open traceability gap recorded as a "follow-up."** The gate (step 4) is blocking by design — an untested `implemented` artifact or a missing `verifies` link is a reason not to tag, not a TODO to ship around.
- **Carrying tool friction in your head through the release tail.** When a tool fails or forces a workaround during the release, file it via [`report-tool-friction`] as you hit it.
- Inlining clean-room verification of findings instead of pointing at [`clean-room-verification`]. Duplicate procedure = duplicate maintenance.

## Where this composes

`pulseengine-feature-loop` ends here when the feature lands. `oracle-gate-a-change` is what each PR in the queue *passes through* on the way to merge. The traceability completeness gate (step 4) audits the artifacts the feature loop produced and leans on [`clean-room-verification`]. [`report-tool-friction`] fires throughout — any tool that fails or forces a workaround during the release becomes a tracked issue.
