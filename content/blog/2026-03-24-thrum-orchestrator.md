+++
title = "thrum: autonomous AI-driven development with formal verification gates"
description = "AI agents write code. Formal verification gates catch errors. Humans approve the result. thrum is the pipeline orchestrator that makes this loop work — with Z3 proofs, cross-repo integration testing, and convergence-aware retries."
date = 2026-03-24
draft = true
[taxonomies]
tags = ["deep-dive", "thrum", "series"]
authors = ["Ralf Anton Beier"]
+++

*This is part 9 of a series on building a verified WebAssembly pipeline for safety-critical embedded systems. [Part 1](/blog/zero-cost-component-model/) introduces the approach. [Part 8](/blog/temper-governance/) covers repository governance.*

{% insight() %}
Development velocity and safety assurance are traditionally in tension. thrum resolves this: AI agents handle implementation, formal verification gates enforce correctness, and humans approve results before merge. The pipeline has already produced its own features — tasks TASK-0003 through TASK-0009 in thrum's commit history were implemented by thrum's own agents. This is not a prototype. It is a working development loop where every change is mathematically checked before it reaches the codebase.
{% end %}

## What thrum does

[thrum](https://github.com/pulseengine/thrum) is a gate-based pipeline orchestrator for AI-driven development. It maintains a task queue, dispatches AI coding agents to implement changes, and requires every change to pass through formal verification gates before merging.

The name refers to the low continuous hum of a machine running — fitting for a system that drives development continuously in the background.

### The gate model

Every task flows through a state machine with three verification gates:

```text
Pending → Claimed → Implementing → Gate 1 → Reviewing → Gate 2
  → AwaitingApproval → Approved → Integrating → Gate 3 → Merged
```

**Gate 1 (Quality):** `cargo fmt --check`, `cargo clippy`, `cargo test` — standard code quality checks. Fast feedback on basic correctness.

**Gate 2 (Proof):** [Z3](https://github.com/Z3Prover/z3) SMT solver verification and [Rocq](https://rocq-prover.org/) formal proofs — mathematical proof that the change preserves correctness. This is the gate that makes thrum different from a CI pipeline.

**Gate 3 (Integration):** Cross-repo pipeline execution — meld (fuse) → loom (optimize) → synth (compile) — verifying that the entire PulseEngine toolchain still works end-to-end after the change.

Between Gate 2 and Gate 3, **human approval is required**. This is the deliberate human-in-the-loop checkpoint. An AI agent implements, formal verification checks, but a human decides whether the change should integrate.

Failed gates cycle back to implementation with the retry count incremented. After 10 retries, the task is flagged for human intervention.

## The agents

thrum dispatches multiple AI coding agents in parallel, each isolated in its own git worktree:

- A **Planner** agent analyzes roadmaps and consistency reports to generate prioritized task backlogs
- **Implementer** agents write code, tests, and proofs
- A **Reviewer** agent reviews changes for correctness and style
- An **Integrator** agent verifies the full cross-repo pipeline

The agents are backend-agnostic. thrum supports Claude Code (CLI), OpenCode, Aider, the Anthropic Messages API, and any OpenAI-compatible endpoint. Backends are registered declaratively in TOML configuration and resolved by role.

### Convergence-aware retries

When an agent fails a gate, thrum does not blindly retry. It tracks failure signatures — normalized error hashes that strip ANSI codes, line numbers, and timestamps — and escalates the retry strategy:

1. **First failure:** Normal retry with failure feedback
2. **Same error repeats:** Expanded context (full stderr, related files)
3. **Third repeat:** Prompt rotation ("do NOT repeat the same fix")
4. **Fourth repeat:** Flag for human review — the agent is stuck

### Agent memory with semantic decay

thrum stores error patterns, successful approaches, and decisions from prior runs. Each memory entry has a decay score with a configurable half-life — recent experiences are weighted more heavily, but old patterns that keep being relevant get refreshed. This memory is injected into agent prompts, so agents learn from previous failures without accumulating stale context.

## Cross-repo awareness

PulseEngine is a multi-repo toolchain. A change to loom's type definitions can break synth. A wasmparser version bump in meld needs to propagate to kiln. thrum understands this.

### Consistency checking

The consistency checker scans all repos' `Cargo.toml` files and detects:

- wasmparser version drift
- Z3 version mismatches
- rules_rust version drift
- Rust edition inconsistencies

The Planner agent uses consistency reports to generate cross-repo synchronization tasks at the highest priority (P0).

### Safety classification

Repos are configured with safety targets from ISO 26262:

| Repo | Safety Target | Why |
|------|---------------|-----|
| synth | ASIL D | Native code output runs on the safety-critical target |
| loom | ASIL B | Optimization must preserve semantics |
| meld | QM | Fusion output is verified downstream |

Higher safety classifications get stricter gate configurations and higher task priority.

## The dashboard

thrum includes an embedded HTMX-powered web dashboard — no separate frontend build, no JavaScript framework. Three views:

- **Main dashboard** — pipeline status overview, task list with action buttons, budget summary
- **Live view** — real-time agent output streaming via Server-Sent Events
- **Review view** — side-by-side diff review with approve/reject buttons

The dashboard also exposes memory state, convergence history, and OpenTelemetry traces — useful for understanding why an agent succeeded or failed.

## The A2A protocol

thrum implements the [Agent-to-Agent (A2A)](https://github.com/a2aproject/A2A) protocol — Google's standard for inter-agent communication:

- `GET /.well-known/agent.json` — Agent Card discovery
- `POST /a2a` — JSON-RPC 2.0 (SendMessage, GetTask, ListTasks, CancelTask)
- `GET /a2a/subscribe/{task_id}` — per-task SSE streaming

This means thrum can participate in multi-agent systems beyond PulseEngine. External agents can submit tasks, subscribe to progress, and receive results through a standardized protocol.

## Self-hosting

thrum is already producing its own features. Looking at the commit history:

- **TASK-0003:** Diff endpoint — thrum's agent added the API endpoint for viewing code diffs
- **TASK-0004:** Embedded HTMX dashboard — the dashboard was built by thrum's own agents
- **TASK-0005:** Budget enforcement — cost tracking and ceiling enforcement
- **TASK-0006:** Test subsampling — faster gate iterations
- **TASK-0008:** File watcher — real-time change detection
- **TASK-0009:** TUI watch command — terminal UI

Each of these went through the full gate pipeline: quality checks, verification, human approval, integration testing. The tool is building itself through its own process.

## Architecture

thrum is a Rust workspace with five crates:

| Crate | Purpose |
|-------|---------|
| `thrum-core` | Domain types — task state machine, gates, memory, safety classifications, A2A protocol |
| `thrum-db` | Persistence via [redb](https://github.com/cberner/redb) — pure Rust embedded key-value store, zero external dependencies |
| `thrum-runner` | Agent execution — backend registry, parallel engine, worktree isolation, git operations |
| `thrum-api` | HTTP API + dashboard — axum, HTMX, SSE streaming |
| `thrum-cli` | Binary — `thrum run`, `thrum task`, `thrum status`, `thrum watch`, `thrum serve` |

The entire system — agents, gates, persistence, API, dashboard — runs as a single binary. No database server, no message queue, no container orchestration. This is deliberate: for a safety-critical development tool, fewer moving parts means fewer failure modes.

{% note(kind="warning") %}
thrum is at v0.1.0 and under active development. The gate pipeline works and is self-hosting, but the formal verification gates (Z3, Rocq) depend on the maturity of rules_verus and rules_rocq_rust. The Docker sandbox exists but defaults to no isolation. This is an early but functional system — the architectural decisions are deliberate, and the tool is already producing real output.
{% end %}

## temper + thrum: the development loop

Together, [temper](/blog/temper-governance/) and thrum form an autonomous development loop:

1. **thrum** receives tasks (from the planner, from humans, or from external agents via A2A)
2. AI agents implement the changes in isolated worktrees
3. **Gate 1** checks code quality
4. **Gate 2** runs formal verification (Z3, Rocq)
5. A human reviews and approves via the dashboard
6. **Gate 3** runs cross-repo integration (the full meld → loom → synth pipeline)
7. The agent creates a pull request
8. **temper** enforces governance (signed commits, branch protection, CI attestation) and auto-merges

The human is in the loop at step 5. Everything else is automated. The safety assurance comes not from slowing down development, but from making every change pass through mathematical verification before it reaches the codebase.

If you are working on AI-driven development for safety-critical systems, formal verification in CI/CD, or multi-agent orchestration — we would like to hear from you. Everything is at [github.com/pulseengine](https://github.com/pulseengine).
