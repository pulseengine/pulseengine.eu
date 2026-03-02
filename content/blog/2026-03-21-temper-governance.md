+++
title = "temper: automated governance for a safety-critical toolchain"
description = "Every repository in the PulseEngine organization adheres to the same standards automatically. temper is the GitHub App that enforces signed commits, branch protection, CI attestation, and consistent configuration — no manual enforcement, no drift."
date = 2026-03-21
draft = true
[taxonomies]
tags = ["deep-dive", "temper", "series"]
authors = ["Ralf Anton Beier"]
+++

*This is part 8 of a series on building a verified WebAssembly pipeline for safety-critical embedded systems. [Part 1](/blog/zero-cost-component-model/) introduces the approach. [Part 7](/blog/hermetic-toolchain/) covers the build system and supply chain attestation.*

{% insight() %}
In safety-critical industries, every audit starts with the same question: can you prove your development process is consistent? temper eliminates configuration drift across the entire toolchain — signed commits, branch protection, CI attestation, dependency tracking — enforced automatically on every repository. The result: when an assessor asks about your development governance, the answer is a dashboard, not a spreadsheet.
{% end %}

## Why governance matters

PulseEngine is not one repository. It is over 25 repositories spanning a Wasm runtime, a fusion tool, an optimizer, a native transcoder, build rules, verification tools, and MCP servers. Each repository needs the same branch protection, the same signed-commit requirements, the same CI attestation, the same Dependabot configuration.

In a safety-critical context, this consistency is not optional. ISO 26262 requires configuration management. DO-178C requires that the development environment is controlled. If repository A requires signed commits but repository B does not, the governance claim applies to neither.

Manual enforcement does not scale. A developer forgets to enable branch protection on a new repo. A fork relaxes merge settings. Dependabot falls out of sync. These are not hypothetical — they are the default state of any growing organization without automation.

## What temper does

[temper](https://github.com/pulseengine/temper) is a [Probot](https://probot.github.io/) v14 GitHub App that automatically configures and hardens every repository in the PulseEngine organization. It reacts to webhook events and enforces compliance through a declarative configuration.

### Repository hardening

When a new repository is created — or on demand via ChatOps commands — temper applies:

- **Merge settings** — squash-only merges (rebase disabled), with fork-aware overrides that allow all strategies for forked repos
- **Branch protection** — required status checks, signed commits, linear history, conversation resolution, admin enforcement, no force-pushes or deletions
- **Issue labels** — synchronizes a standard label set across all repos
- **PR and issue templates** — pushes `.github/PULL_REQUEST_TEMPLATE.md`, issue templates, and `CODEOWNERS`
- **Dependabot configuration** — auto-detects ecosystems (supports 14: npm, cargo, gomod, pip, maven, docker, terraform, and more) and generates appropriate `dependabot.yml`

### CI attestation

temper's own CI pipeline generates SPDX SBOMs and attests build provenance via [Sigstore](https://www.sigstore.dev/) — the same attestation framework that [sigil](/blog/hermetic-toolchain/) uses for the pipeline artifacts. This creates consistency: the governance tool and the build tool use the same supply chain security infrastructure.

### Signed-commit handling

For repositories that require signed commits (all PulseEngine repos do), temper manages the merge strategy:

- Temporarily enables merge commits (which preserve GPG signatures) when a PR contains signed commits
- Auto-reverts to rebase-only after a timeout
- This solves the common problem of losing signature verification during squash merges

### ChatOps

Ten commands, triggered by commenting `/command` on any issue or PR:

| Command | Action |
|---------|--------|
| `/configure-repo` | Apply full configuration to the current repo |
| `/sync-all-repos` | Bulk-apply configuration to every org repo |
| `/check-config` | Generate a compliance report |
| `/generate-dependabot` | Auto-detect ecosystems and generate config |
| `/analyze-org` | Full organization analysis report |
| `/review-pr` | Trigger an AI-powered code review |

## The compliance dashboard

temper includes an operations dashboard — an embedded HTMX-based web UI that provides:

- **Organization-wide compliance score** with per-repo breakdown (merge settings, branch protection, signed commits, CI status, labels)
- **Active PR tracker** with check status, labels, and CI status
- **Signal feed** for real-time webhook events and configuration drift detection
- **AI review tracking** with review history and statistics

This dashboard is not a separate service — it is built into temper and served directly. For audit purposes, it provides a live view of organizational compliance without requiring manual reports.

## The thrum integration

temper works in concert with [thrum](/blog/thrum-orchestrator/) — the pipeline orchestrator that dispatches AI coding agents across PulseEngine repositories. When thrum's agents create pull requests:

1. temper recognizes the `thrum` bot user
2. After CI passes, temper auto-enables GitHub's auto-merge (squash method)
3. The PR merges without manual intervention

This creates an autonomous development loop: thrum generates and verifies code through formal gates, temper enforces governance and handles the merge. The human-in-the-loop checkpoint lives in thrum (approval gate), not in temper.

## Architecture

temper is a Node.js application built on Probot v14:

- **Configuration** — a single declarative `config.yml` controls all behavior, validated at startup
- **Persistence** — SQLite with WAL mode for task scheduling and idempotent webhook processing
- **Self-update** — a compiled Rust binary handles zero-downtime deployments when the temper repo itself is updated
- **Deployment** — Docker (multi-stage Alpine), PM2, or shared hosting

### For safety-critical context

temper is not itself a safety-critical tool — it does not produce artifacts that run on target devices. It is a development environment tool. But its role is essential for the qualification story: it provides *evidence* that the development process meets the governance requirements of ISO 26262 and DO-178C.

A formally verified compiler that runs in an ungoverned development environment is still a compliance gap. temper closes that gap.

{% note(kind="warning") %}
temper is at v1.0.0 and actively deployed against the PulseEngine organization. It is not a general-purpose governance tool — it is purpose-built for PulseEngine's specific requirements. The AI review feature uses a local endpoint and is not suitable for all environments.
{% end %}

*Next in the series: [part 9 — thrum: autonomous AI-driven development with formal verification gates](/blog/thrum-orchestrator/).*

If you are building governance automation for safety-critical development environments — we would like to hear from you. Everything is at [github.com/pulseengine](https://github.com/pulseengine).
