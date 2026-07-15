---
name: repo-hygiene
description: This skill should be used to run a complete hygiene sweep over a repo after a release or on a standing cadence — stale worktrees, dead local/remote branches (including squash-merge artifacts git cannot see as merged), ancient stashes, agent build caches, status noise, and the open-issue board. Use it when the user says "clean up", "hygiene", "check worktrees and branches", "what's stale", or when a release tick finishes and residue has accumulated. Closure is evidence-based: an issue closes because its fix is on a tagged release (close with ref), because it is obsolete/superseded/captured elsewhere (close with rationale), or it stays open with an explicit "remaining:" note — never silently. Composes with issue-hunt (the board is its watermark surface), release-execution (fire this as the release tail), and the operating contract.
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# Repo hygiene — the post-release residue sweep

Multi-agent, multi-release campaigns shed residue at a rate manual habits don't
match: one shipped hub can leave a dozen worktrees, dozens of branches, tens of
GB of per-agent build caches, and a tracker where "fixed" issues sit open. Left
alone this compounds into disk-full incidents, 200-branch listings nobody can
read, and an issue board that no longer means anything. This skill is one
bounded sweep; run it as the tail of every release (or on a cadence) and it
stays cheap.

## The sweep, in order

### 1. Open PRs — the only thing that blocks the rest
`gh pr list --state open`. Anything open is either in-flight work (leave it and
its worktree/branch alone — list them as EXCLUDED for the steps below) or a
zombie PR whose lane died (salvage or close it first). Everything after this
step applies only to refs with no open PR.

### 2. Worktrees
`git worktree list`. An agent worktree whose branch merged is dead weight;
remove it (`git worktree remove <path> --force`, then `git worktree prune`).
**Before removing, check for uncommitted work** (`git -C <wt> status --short`,
`git -C <wt> log <base>..HEAD`) — a dead agent's worktree can hold salvageable
committed-but-unpushed work; push or cherry-pick it first, never assume merged.

### 3. Local branches — the squash-merge trap
`git branch --merged main` catches almost nothing on a squash-merge repo: the
branch tips were never merged as commits, so git sees every shipped branch as
"unmerged". Delete the truly-merged first (`-d`), then for the rest verify the
CONTENT shipped — the branch corresponds to a merged PR (`gh pr list --head
<branch> --state merged`) or a released version — and force-delete (`-D`).
A branch with neither a merged PR nor released content is real unfinished work:
leave it and say so.

### 4. Remote branches
Repos with delete-branch-on-merge still accumulate stragglers: manually-pushed
release branches, held rivet branches, pre-setting-era refs. Same verification
as step 3, then `git push origin --delete <branch>` and `git fetch --prune`.
Target end-state: `origin/main` (+ genuinely active branches) only.

### 5. Stashes — shared and dangerous
`git stash list`. Worktrees share the repo-wide stash stack, so stashes are
both cross-contaminating (an agent's `stash pop` can consume another lane's
stash) and near-always ancient. Read the list, confirm each entry's era is
long-shipped, then `git stash clear`. A recent stash from an identifiable
in-flight task gets applied or explicitly owned, not cleared.

### 6. Build caches
Per-agent `CARGO_TARGET_DIR`s (and equivalent) are the top disk-full culprit —
tens of GB per hub. Once the lanes merged, purge them (`rm -rf` the per-lane
cache dirs; they are rebuildable by construction). Check `df` before/after and
report the reclaimed number.

### 7. Status noise
`git status` must end the sweep CLEAN. Recurring noise (an uninitialized
submodule, a generated lockfile, a tool's scratch dir) hides real changes and
trips automation; fix the cause — `.git/info/exclude` for local-only noise,
`.gitignore` for repo-wide, submodule init/ignore config for submodules. Noise
you silence without understanding is a future surprise: name what each entry
was.

### 8. The issue board — evidence-based closure
For every open issue, one of exactly three dispositions:

- **Close with the shipping ref** — the fix is on a *tagged release* (not just
  merged). Say which release and which PR.
- **Close with rationale** — obsolete, superseded, or captured elsewhere (e.g.
  absorbed into a roadmap artifact); link what replaced it.
- **Stays open with a "remaining:" note** — a genuine residual, named
  precisely, ideally with an owner.

Two disciplines make this honest:
- **Re-verify before closing as fixed.** If an issue *might* have been fixed
  incidentally (a lever landed near it), reproduce it against the current
  binary before closing — "verified fixed on vX.Y, repro now shows N" beats
  "probably covered by #NNN". If it still reproduces, it stays open; you just
  learned the levers missed it.
- **The closure comment is the audit trail.** Include the evidence (the repro
  command and observed result, or the release/PR refs), and attribute the
  comment if the account is shared.

## Cadence and composition

Fire this as the **tail of release-execution** (residue is freshest and the
worktree/branch set is unambiguous) or on the issue-hunt loop's idle tick. The
issue-board step is the same surface issue-hunt watermarks — hygiene closes
what shipped; issue-hunt triages what's new. If the sweep keeps finding the
same class of residue (e.g. every hub leaves N caches), automate that class at
the source (the lane prompt purges its own cache on success) rather than
growing the sweep.

## Anti-patterns

- **`git branch --merged` as the whole story on a squash-merge repo** — it
  proves almost nothing; verify content shipped (merged PR / released tag)
  before `-D`.
- **Removing a worktree without reading it** — dead agents leave salvageable
  work; check status + unpushed commits first.
- **Closing an issue "probably fixed by #NNN"** — reproduce it or leave it
  open. A wrong closure costs a user a re-report; a re-verified closure costs
  one compile.
- **Silently closing** — every closure carries evidence or rationale in a
  comment; a bare close is indistinguishable from an accident.
- **Clearing stashes without listing them** — the stack is shared across
  worktrees; read before you clear.
- **Treating the sweep as optional when disk is fine** — the branch/issue rot
  is the expensive part, not the bytes; the board's meaning degrades silently.
