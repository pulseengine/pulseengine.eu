---
name: release-execution
description: This skill should be used when cutting, shipping, or finishing a release — including "ship it", "cut a release", "tag this", "release v0.X.Y", "take this to release", "work the PR queue to green", "finish the release tail", "publish", or any end-to-end release work that involves PRs, reviewers, merging, CI, tagging, GitHub Release, and crates.io publish. ALWAYS use this skill when the user authorizes autonomous release work or asks to "go as long as you can" on a release campaign.
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# Release execution

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

### 4. Tag and release
- Once the queue is empty and main is green, **PAUSE for fork**: confirm the new tag (`v0.X.Y`) and whether this is the right moment to cut, vs. holding for more. Use `AskUserQuestion` — this is a genuine decision boundary, not a routine step.
- After confirmation: tag, push tag, watch the release workflow.

### 5. Verify the release shipped
- GitHub Release: artifacts present, notes correct.
- crates.io: `cargo search <crate>` shows the new version.
- Any downstream — Docker image, Bazel rules dep update, MCP server restart — kicked.
- Apply [`clean-room-verification`] to the "release looks good" claim before reporting done.

### 6. Write the falsification statement
- Per PulseEngine methodology, every release should carry a falsifiable kill-criterion: "this release would be wrong if X is observed in the field." Add it to release notes or a follow-up issue.
- The point is to make the claim measurable, not to draft prose. One sentence is fine.

### 7. Release tail cleanup
- Doc updates, version bumps in dependent repos, milestone close-out, follow-up issues opened for known-deferred items.
- This is where most teams quit too early. Don't.

## Forks where you stop and ask

These are non-routine and consequential — `AskUserQuestion` here, don't decide silently:
- **Cutting a new tag** (merge-all-and-tag vs. hold for more).
- **Breaking-API or version-scheme changes** (semver bump direction, deprecations).
- **Destructive git** (force-push to main, branch deletion of unmerged work, history rewrites).
- **Putting RC / unproven code on a safety or signing path** (anything that affects wohl OTA verification, sigil attestation, synth-produced binaries on a cover target).
- **Milestone scope choices** (does this PR belong in v0.X.Y or v0.X+1.0).

Between these forks: keep moving. Single-letter prompts like "c" mean continue.

## Anti-patterns

- Waiting on green for an in-flight PR when the next work doesn't depend on it. Treat CI as async.
- Asking for confirmation between routine steps (merge a green PR, rebase, re-run a flaky check). Don't.
- Stopping at "tag pushed" without verifying the artifacts actually shipped.
- Skipping the falsification statement because "the release is small." Small releases still need kill-criteria.
- Inlining clean-room verification of findings instead of pointing at [`clean-room-verification`]. Duplicate procedure = duplicate maintenance.

## Where this composes

`pulseengine-feature-loop` ends here when the feature lands. `oracle-gate-a-change` is what each PR in the queue *passes through* on the way to merge.
