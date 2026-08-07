---
name: repo-hygiene
description: This skill should be used to run a complete hygiene sweep over a repo after a release or on a standing cadence — stale worktrees, dead local/remote branches (including squash-merge artifacts git cannot see as merged), ancient stashes, agent build caches, status noise, and the open-issue board. Use it when the user says "clean up", "hygiene", "check worktrees and branches", "what's stale", or when a release tick finishes and residue has accumulated. It is quiesce-gated so it is safe to run inside a live multi-agent campaign, not only after everything has stopped. Closure is evidence-based — an issue closes because its fix is on a tagged release (close with ref), because it is obsolete/superseded/captured elsewhere (close with rationale), or it stays open with an explicit "remaining:" note — never silently. Composes with issue-hunt (the board is its watermark surface), release-execution (fire this as the release tail), and the operating contract.
metadata:
  author: pulseengine.eu
  version: "0.2.0"
---

# Repo hygiene — the post-release residue sweep

Multi-agent, multi-release campaigns shed residue at a rate manual habits don't
match: one shipped hub can leave a dozen worktrees, dozens of branches, tens of
GB of per-agent build caches, and a tracker where "fixed" issues sit open. Left
alone this compounds into disk-full incidents, 200-branch listings nobody can
read, and an issue board that no longer means anything. This skill is one
bounded sweep; run it as the tail of every release (or on a cadence) and it
stays cheap.

The sweep *mutates* — it removes worktrees, deletes branches, `rm -rf`s caches,
and cleans the tree. Every step below assumes the thing it touches is dead. In a
live multi-agent repo that assumption is often false, so the sweep starts by
proving the tree is idle, then acts.

## 0. Quiesce — before you touch anything

The sweep is written for multi-agent campaigns, and in one a background lane may
own the working tree, a worktree, or a cache *right now*. Assert idle first, or
the sweep races live work and corrupts it:

- **No compiler running.** `pgrep -x 'cargo|rustc|bazel'` is empty. A step-6
  `rm -rf` on a `target/` an active build is writing is corruption, not reclaim.
  **Match the command *name*, not the command line:** `ps aux | grep cargo` also
  matches every tool installed under `~/.cargo/bin`, so on a normal developer
  machine it is near-permanently non-empty and would abort every valid sweep.
  (`ps -eo comm= | awk -F/ '{print $NF}' | grep -cxE 'cargo|rustc|bazel'` is the
  portable equivalent.) The same name-vs-path care applies anywhere this skill
  greps `ps`.
- **No agent owns the tree.** No agent lock held (e.g.
  `.claude/scheduled_tasks.lock`), no background implementer mid-edit — `git
  status` in the root *and* every worktree shows only what you expect.
- **If something is live:** wait, or exclude exactly the worktree / branch /
  cache it owns and sweep around it. Never mutate under a running lane.

## The sweep, in order

### 1. Open PRs — the only thing that blocks the rest
`gh pr list --state open`. Anything open is either in-flight work (leave it and
its worktree/branch alone — list them as EXCLUDED for the steps below) or a
zombie PR whose lane died (salvage or close it first). Everything after this
step applies only to refs with no open PR.

### 2. Worktrees
`git worktree list`. An agent worktree whose branch merged is dead weight —
but a stale worktree is also an *active hazard*: it keeps its branch checked out
and locked, so a later `git worktree add <that-branch>` silently falls through
and your next `git` op runs on the wrong branch. Before any branch/worktree op,
confirm location: `git worktree list` + `git branch --show-current`.

Three gates before removing one:

- **Untracked work is the bigger loss than unpushed commits.** `git -C <wt>
  status --short` must be empty **including `??` lines** — an agent that yields
  mid-task leaves modified + untracked files that `--force` deletes silently,
  with no reflog to recover. Commit or stash in place; never `--force` past a
  dirty tree. (Also `git -C <wt> log <base>..HEAD` for committed-but-unpushed.)
- **A live process may be rooted in it.** `lsof +D <path> | head` — a background
  build or bench running from the worktree dies when you remove it.
- **Locked worktrees refuse removal.** Agent worktrees are often locked; `git
  worktree unlock <path>` first, then `git worktree remove <path> --force`, then
  `git worktree prune`.

### 3. Local branches — the squash-merge trap
`git branch --merged main` catches almost nothing on a squash-merge repo: the
branch tips were never merged as commits, so git sees every shipped branch as
"unmerged". Delete the truly-merged first (`-d`), then verify the rest's CONTENT
shipped — mechanically, not by eye:

- **Merged PR by head:** `gh pr list --head <branch> --state merged --json
  number` — non-empty ⇒ content shipped ⇒ `-D` is safe.
- **Content fallback** (head-match is necessary-not-sufficient — PRs get
  retargeted, renamed, or squashed under a different title): compare **trees, not
  commits**. `git diff --quiet main <branch>` exiting 0 means the branch's tree is
  fully present in `main` ⇒ shipped. Do **not** reach for `git cherry` /
  `git log --cherry` here — they match *patch-ids*, and a squash collapses N
  commits into one with a different id, so they flag a fully-shipped branch as
  unmerged (verified empirically). A non-empty tree diff is ambiguous (main may
  have simply advanced), so treat it as "don't auto-delete", not "unshipped".
- **When neither confirms, leave it** — it is real unfinished work; say so.
  (`gh pr merge --squash --delete-branch` already deleted the *remote*, so the
  local branch is the entire residue class.)

### 4. Resync the branch you build from
Local `main` silently drifts behind `origin/main` on a squash-merge repo — every
merge lands a commit you don't have — so new worktrees/branches cut from it get
the wrong base. Fast-forward, or `git checkout main && git reset --hard
origin/main`, as part of the sweep. Same blind spot as step 3, for the branch
you build *from*.

### 5. Remote branches
Repos with delete-branch-on-merge still accumulate stragglers: manually-pushed
release branches, held rivet branches, pre-setting-era refs. Same verification
as step 3, then `git push origin --delete <branch>` and `git fetch --prune`.
Target end-state: `origin/main` (+ genuinely active branches) only.

### 6. Stashes — shared and dangerous
`git stash list`. Worktrees share the repo-wide stash stack, so stashes are both
cross-contaminating (an agent's `stash pop` can consume another lane's stash) and
near-always ancient. Don't clear on era alone — **cross-reference each stash's
`On <branch>` against that branch's step-3 disposition**: a stash on a branch you
just classified *unfinished/unshipped* is salvage by construction (e.g.
`stash@{0}: On feat/gust-v0.4.0-syscall-seam: v04-wip-park`); only stashes on
shipped/dead branches are clear-eligible. The flip side of clearing is naming —
push wip with `git stash push -m <campaign>-wip` so the next sweep's decision is
mechanical. Then `git stash clear` the clear-eligible set.

### 7. Build caches — gate the purge
Per-agent `CARGO_TARGET_DIR`s (and equivalent) are the top disk-full culprit —
tens of GB per hub — but they are not free to delete. A cache dir can belong to
an open PR's worktree or a *shared* workspace target (e.g. `benches/gust/target`
across a tree), not only a dead lane; purging one mid-session is a rebuild storm,
lock contention, or a corrupted incremental dir. Gate each purge on **all
three**: no open PR references the path, no `git worktree` maps to it, no
compiler running (step 0). Then `rm -rf` the per-lane dirs (rebuildable by
construction); `df` before/after; report the reclaim.

- **Threshold-trigger on standing loops**, not only the release tail: `df` >
  ~85% ⇒ purge now. A days-long loop accrues residue *between* releases.
- **Recognize the symptom.** A *hanging* commit or CI (not a clean error)
  usually means the shared target is full — a build-running pre-commit hook
  deadlocks. Kill it, purge, re-commit.
- **Redirected/external cache volumes can silently corrupt outputs** — all-zero
  wasm magic, a vanished `TMPDIR` that breaks `git commit`, a crashed build
  sandbox. Keep the *permanent* output base on reliable storage (transient
  sandbox can go elsewhere); if you redirect, treat produced artifacts as
  suspect — verify magic/checksum (prefer `cargo metadata`-based discovery over
  hardcoded paths) before consuming.

### 8. Status noise
`git status` must end the sweep CLEAN. Recurring noise (an uninitialized
submodule, a generated lockfile, a tool's scratch dir) hides real changes and
trips automation; fix the cause — `.git/info/exclude` for local-only noise,
`.gitignore` for repo-wide, submodule init/ignore config for submodules. Noise
you silence without understanding is a future surprise: name what each entry was.
One thing that *looks* like noise but isn't: on a federated repo with sibling
path-deps (CI rebases them independently), `Cargo.lock` churn is **inherent** —
`--locked` can't be used and the lock will move; don't mistake it for silenceable
noise or gitignore it.

### 9. The issue board — evidence-based closure
For every open issue, one of exactly three dispositions:

- **Close with the shipping ref** — the fix is on a *tagged release* (not just
  merged). Say which release and which PR.
- **Close with rationale** — obsolete, superseded, or captured elsewhere (e.g.
  absorbed into a roadmap artifact); link what replaced it.
- **Stays open with a "remaining:" note** — a genuine residual, named
  precisely, ideally with an owner.

Disciplines that make this honest:

- **Re-verify before closing as fixed, and trust the binary over any done-flag.**
  If an issue *might* have been fixed incidentally, reproduce it against the
  current binary before closing — "verified fixed on vX.Y, repro now shows N"
  beats "probably covered by #NNN". A task list or status note can say "done"
  while the shipped artifact isn't (a "fix" whose tests passed vacuously), so
  never close on a tracker marker alone; also spot-check recently-*closed* issues
  for regression.
- **Cite the release, not the merge.** Merged ≠ released — close on the
  tagged-release ref, never a merge commit alone; the tag is the evidence an
  outsider can check.
- **Guard the auto-close cascade on umbrella issues.** A PR body saying `closes
  #30` auto-closes the *entire* multi-item umbrella when it fixed *one* item.
  When a PR addresses one item of a multi-item issue, use `Refs #N`, **never**
  `closes/fixes #N`. After a merge wave, re-check that umbrella issues weren't
  auto-closed — reopen, tick the one box, keep the rest open.
- **The closure comment is the audit trail.** Include the evidence (repro command
  + observed result, or the release/PR refs), and attribute it if the account is
  shared.

## Cadence and composition

Fire this as the **tail of [`release-execution`]** (residue is freshest and the
worktree/branch set is unambiguous) or on the [`issue-hunt`] loop's idle tick —
both skills invoke it at those points. The issue-board step is the same surface
issue-hunt watermarks: hygiene closes what shipped; issue-hunt triages what's new.

- **Report-then-act on unattended runs.** At scale a pass proposes dozens of `-D`
  plus remote deletes; emit the **full disposition list first** (mirroring
  issue-hunt's "state the count up front") and cap or gate the destructive batch,
  so one misclassification can't silently nuke dozens of refs in an unsupervised
  sweep.
- If the sweep keeps finding the same residue class (e.g. every hub leaves N
  caches), automate that class at the source (the lane prompt purges its own
  cache on success) rather than growing the sweep.

## Anti-patterns

- **Sweeping under live work** — every step mutates; a running build or a
  mid-edit agent turns the sweep into corruption. Quiesce (step 0) first.
- **A precondition that cries wolf** — a check that reports "busy" on a machine
  that is idle gets routed around by habit, and then the once it fires for real
  it is ignored. This is the human-factors twin of the vacuous gate: one check
  can never fail, the other always "fails", and neither carries information.
  A guard that misfires is a bug in the guard — fix it, don't learn to skip it.
- **`git branch --merged` (or `git cherry`) as squash-merge detectors** — both
  miss squashes (verified); `--merged` sees the tip as unmerged and `git cherry`
  flags it `+` on a patch-id mismatch. Verify content shipped by merged PR, a
  tree diff (`git diff --quiet main <branch>`), or a released tag before `-D`.
- **Removing a worktree without reading it** — dead agents leave salvageable
  work, *including untracked files with no reflog*; check `status --short`
  (including `??`), unpushed commits, and rooted processes first.
- **`closes #N` on one item of an umbrella** — it false-completes the whole
  issue; use `Refs #N` and re-check umbrellas after every merge wave.
- **Closing "probably fixed by #NNN", or trusting a done-flag over the binary** —
  reproduce it or leave it open. A wrong closure costs a user a re-report; a
  re-verified closure costs one compile.
- **Silently closing** — every closure carries evidence or rationale in a
  comment; a bare close is indistinguishable from an accident.
- **Clearing stashes without matching them to a branch** — the stack is shared;
  a stash on an unshipped branch is salvage, not age-cleared residue.
- **`rm -rf` a cache without gating** — it may be a shared target or an open PR's;
  gate on no-open-PR + no-worktree + no-compiler before deleting.
- **An unsupervised destructive batch without a disposition list** — report the
  count and the refs before deleting dozens.
- **Treating the sweep as optional when disk is fine** — the branch/issue rot is
  the expensive part, not the bytes; the board's meaning degrades silently.

The robustifiers above (quiesce gate, untracked-worktree salvage, tree-diff
shipping check, main resync, stash-to-branch matching, cache-purge gating,
umbrella cascade, trust-the-binary) were folded in from field application on
wohl, relay, loom, and gale — each a live specimen of the residue class it names,
and the git/gh behaviors were verified empirically before shipping.
