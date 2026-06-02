+++
title = "rivet"
description = "Traceability as code — requirements to evidence in git"
template = "docs-section.html"
sort_by = "weight"
weight = 10
+++

## What it does

rivet keeps requirements, architecture decisions, safety analysis, and test links as YAML files in your git repository. You write artifacts. You link them. `rivet validate` checks that the traceability chain is complete on every commit. The compliance report generates itself.

**Input:** YAML artifact files + schemas defining types, links, and rules.
**Output:** validation results, traceability matrices, coverage reports, compliance HTML, Zola exports.

## When to use it

Use rivet when you need to show an auditor — or yourself — that every requirement traces to a design decision, every design decision traces to a test, and nothing is orphaned or missing. This applies to ISO 26262, ASPICE, DO-178C, IEC 61508, IEC 62304, EU AI Act, and any standard that requires lifecycle traceability.

Also use it when AI agents produce code and you need the traceability to keep pace automatically.

## Getting started

### Install

```sh
git clone https://github.com/pulseengine/rivet
cd rivet && cargo install --path rivet-cli
```

### Initialize a project

```sh
cd your-project
rivet init --preset aspice
```

This creates `rivet.yaml` and a `schemas/` directory. Available presets: `dev`, `aspice`, `stpa`, `cybersecurity`, `do-178c`, `iec-61508`, `iec-62304`, `aadl`.

### Add an artifact and validate

```sh
rivet add --type requirement --title "Watchdog timeout shall not exceed 100ms"
rivet validate
```

If the graph is complete, you see `Result: PASS`. If a link is missing or an artifact is orphaned, the build fails.

### See what you have

```sh
rivet stats        # artifact counts
rivet coverage     # traceability coverage per rule
rivet serve --watch  # dashboard in the browser
```

## How it connects

- **spar** → rivet imports AADL architecture components from spar as artifacts
- **meld** → rivet consumes STPA safety analysis from meld's YAML format
- **sigil** → rivet tracks supply chain attestations (planned)
- **AI agents** → `rivet mcp` exposes tools for agents to add, link, validate, and stamp provenance
- **Zola** → `rivet export --format zola --shortcodes` publishes artifacts and data to a static site
- **CI** → `rivet validate` runs as a pre-merge check; `rivet export --format html` generates compliance reports

## Limitations

- Not published to crates.io — install from source or download binary releases
- Cross-repo validation requires `rivet sync` to clone external projects
- Formal verification of rivet's own core (Verus/Kani proofs) is planned but not yet in CI
- Import from DOORS/Polarion via OSLC is planned, not yet implemented; ReqIF import works

## Reference

- [Getting Started (full)](/docs/rivet/getting-started/) — detailed setup and configuration
- [Schema Reference](/docs/rivet/schemas/) — all artifact types, link types, traceability rules
- [Architecture](/docs/rivet/architecture/) — system design and design decisions
