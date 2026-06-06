---
name: capture-session-learnings
description: This skill should be used to distill durable knowledge out of a working session before it is lost — at the end of substantive work, before a likely compaction, when the user says "remember this" / "capture what we learned" / "update the working context", or whenever a pattern, decision, or gotcha recurs often enough to be worth keeping. It turns ephemeral session work into (1) an updated working-context checkpoint for resuming next time and (2) durable memory or a new/updated skill when the learning generalizes. The continuous-learning counterpart to the memory-persistence hooks shipped with this plugin.
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# Capture session learnings

Sessions accumulate three things worth keeping that otherwise evaporate at
compaction or session end: **where the work stands** (resume state), **what
was decided and why** (rationale), and **patterns that will recur** (durable
knowledge). The plugin's hooks persist a *mechanical* checkpoint (git state);
this skill captures the *narrative* and promotes the generalizable parts.

## When this fires

- Wrapping up a substantive chunk of work, or before a likely compaction.
- The user says "remember this", "capture what we learned", "update the
  working context", or similar.
- A pattern, workaround, or decision has recurred enough to be worth keeping.

## Three tiers — route each learning to the right place

### 1. Working context (resume state) — almost always
Update the **`## Session notes`** section of
`.claude/pulseengine/working-context.md` (the hooks own the `## State` section
above it — leave that alone). Keep it tight:
- What this session is doing (one or two sentences).
- Key decisions made and *why* (so the next session doesn't relitigate them).
- What's in flight / next step / open question.
- Any landmark commits, PRs, branches.

This is per-repo, local-only (git-excluded), and is re-injected at the next
session start. It is for *this thread of work*, not permanent knowledge.

### 2. Durable memory — when it outlives this work
If the learning is true beyond this session — a project constraint, a
non-obvious fact about the codebase, a confirmed preference, an external
reference — write it to the **file-based memory store**, one fact per file with
frontmatter, and add the one-line pointer to `MEMORY.md`. Prefer updating an
existing memory over creating a duplicate. Don't save what the repo already
records (code structure, git history, things in CLAUDE.md).

### 3. A skill — when it's a repeatable procedure
If the learning is a *multi-step procedure* others will reuse, it belongs in a
skill, not memory (belief/vocabulary → memory; procedure → skill). Propose a
new skill under this plugin's `skills/`, or extend an existing one, following
the existing SKILL.md shape (frontmatter trigger + ordered steps + anti-patterns
+ cross-links). Don't inline a procedure into memory.

## How to decide the tier

> Is it just "where we are"? → working context.
> Will it be true next month regardless of this task? → memory.
> Is it a procedure someone will follow again? → skill.

A single session can produce all three. Capture the working context every
time; promote to memory/skill only when the learning genuinely generalizes —
over-capturing durable artifacts is as harmful as losing them (noise drowns
signal).

## Anti-patterns

- **Letting a session end without updating the working context** when work is
  unfinished — the next session starts cold and re-derives everything.
- **Dumping raw transcript into memory.** Memory is distilled facts, not logs.
- **Promoting one-off task state to durable memory** — it becomes stale noise.
  If it only matters to this thread, it stays in working context.
- **Writing a procedure as a memory file** instead of a skill (or vice-versa).
- Capturing the *mechanical* git state by hand — the hooks already do that;
  spend the effort on rationale and patterns a script can't infer.

## Where this composes

- The plugin's **memory-persistence hooks** save/restore the mechanical
  checkpoint; this skill writes the narrative half they can't.
- [`report-tool-friction`] captures friction *as it happens*; this skill is
  where a recurring friction or its workaround gets promoted into durable
  memory or a skill so it stops recurring.
- [`pulseengine-feature-loop`] / [`release-execution`] — capture the decisions
  and gotchas these produce so the next pass through the loop is faster.
