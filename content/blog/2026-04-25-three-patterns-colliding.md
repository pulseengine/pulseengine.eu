+++
title = "Three patterns colliding: Karpathy's LLM Wiki, oracle-gated agents, and typed compliance"
description = "Andrej Karpathy posted his LLM Wiki gist in April 2026. From most LLM-tooling vantage points it's a clean idea about knowledge bases. From a cybersecurity and safety-critical vantage point it's the third pillar of a pattern that has been forming for years. The other two — oracle-gated agent verification, and typed compliance traceability — are running here already. This is the reflection on what the three together actually mean."
date = 2026-04-25
draft = false
[taxonomies]
tags = ["knowledge-base", "process", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% note(kind="tip") %}
**Reading order for this stack** — start here for the synthesis. Then [*Mythos slop-hunt: oracle-gated audits in practice*](/blog/mythos-slop-hunt/) for the audit method that produced PR #205. The [v0.1.0 announcement](/blog/rivet-v0.1.0/) covers what rivet is and how to install it.
{% end %}

{% insight() %}
Karpathy named the missing piece. From most LLM-tooling vantage points his April 2026 LLM Wiki gist is a clean idea about personal knowledge bases. From the desk of someone who has spent fifteen years in cybersecurity and safety-critical engineering, it is the third pillar of a pattern that has been forming since early 2025 — alongside [oracle-gated agent verification](/blog/spec-driven-development-is-half-the-loop/) and [typed compliance traceability in rivet](/blog/rivet-v0.1.0/). Each pillar by itself is incomplete. Knowledge accumulation alone hallucinates over time. Oracle-gated verification alone has nothing to remember. Typed compliance alone has no narrative and no acceleration. Together — agents read sources, run oracles, write typed artifacts, humans curate at the edges, the auditor queries the result — they are a candidate state of the art for AI-assisted engineering on systems that have to be both fast and provable. From where I sit, in my direct experience of both communities, that union is unheard of. This post is why.
{% end %}

## The three patterns

### Karpathy's LLM Wiki — *knowledge compounds*

Andrej Karpathy's [gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) describes a persistent, LLM-maintained, interlinked knowledge corpus as a replacement for RAG. The LLM does the bookkeeping. You curate sources and ask questions; the LLM writes summary pages, updates indexes, flags contradictions, maintains cross-references. The output compounds across sessions instead of being re-derived on every query.

Three quotes that change how you read it:

> *"The LLM writes and maintains all of the data of the wiki. I rarely touch it directly."*

> *"Obsidian is the IDE; the LLM is the programmer; the wiki is the codebase."*

> *"This document is intentionally abstract. It describes the idea, not a specific implementation. The exact directory structure, the schema conventions, the page formats, the tooling — all of that will depend on your domain, your preferences, and your LLM of choice."*

Markdown shows up in his stack because Obsidian renders markdown. He's explicit that the format is open. The pattern is what matters.

### Oracle-gated agents — *verification mechanically gates*

From [the spec-driven-development-is-half-the-loop post](/blog/spec-driven-development-is-half-the-loop/): a minimal prompt, a strong mechanical oracle, parallel agents, a fresh-session validator. The oracle either fires or it does not. Findings that pass the oracle land as artifacts; findings that don't are rejected. The same shape Anthropic's red team uses for vulnerability research; we run two pipelines on it — bug hunting in sigil's `scripts/mythos/`, traceability-gap closure across rivet-managed corpora — and the oracle is interchangeable. Different domains; same scaffold.

This is the verification half of the loop spec-driven development omits. SDD's QA-lens agent is a soft oracle: another LLM reading the spec back. A soft oracle cannot find what the spec did not think to say, and bug classes are almost by definition what the spec did not think to say.

### rivet — *audit reads the result*

[rivet](/blog/rivet-v0.1.0/) keeps SDLC traceability — requirements, design decisions, hazards, tests — as YAML in git, validated on every commit, designed for an LLM agent to read and write. Two co-equal content layers: typed atomic artifacts with typed links between them, and Markdown documents that cite the atoms by ID. One Rust binary the agent drives three ways — CLI, [MCP](https://modelcontextprotocol.io) server, or LSP backend.

The data-model lineage runs through [sphinx-needs](https://sphinx-needs.readthedocs.io/) (which we used across PulseEngine projects from early 2025 through early 2026, before rivet replaced it everywhere) and DOORS-style typed traceability with decades of safety-critical practice on it. Stable typed IDs, typed link predicates, schema-validated fields. The auditor queries the graph and the graph answers.

## Why each is incomplete alone

| Pattern | What it does well | What it cannot do alone |
|---|---|---|
| LLM Wiki | Compounds knowledge across sessions; LLM does the bookkeeping | No mechanical truth signal — *@SEO-Warlord* on Karpathy's gist: *"prose that may have been silently revised three ingests ago"* |
| Oracle-gated agents | Catches what spec-as-oracle misses; rejects hallucinations | Has nothing to accumulate into; verification with no memory |
| Typed compliance | Audit-grade; queryable; provenance-stamped | No narrative; no agent-scale labor; no compounding outside the typed graph |

Run any one in isolation and you reproduce one of three failure modes that experienced engineers know by heart: the wiki that drifted into fiction, the test suite that goes green on stale assumptions, the traceability matrix nobody actually consults. Run all three together — agent reads sources, runs the oracle, writes the typed artifact, the auditor and the next agent both query it — and the failure modes cancel.

## What this looks like, drawn

{% mermaid() %}
flowchart TB
    src["external sources<br/>papers · clippings · mirrored wikis · transcripts"]
    agent["LLM agent<br/><i>reads · runs the oracle · writes typed artifacts</i>"]
    oracle["mechanical oracle<br/>fires pass/fail · never maybe<br/><i>(rivet validate · failing PoC · Kani · sanitizer)</i>"]

    subgraph dests["where the work lands"]
        direction LR
        subgraph rivetBox["rivet — one binary"]
            direction TB
            rivetContent["<b>typed atoms · documents · link graph</b><br/><i>auditor and human both read this</i>"]
            rivetCli["CLI"]
            rivetMcp["MCP"]
            rivetLsp["LSP"]
        end
        blog["<b>pulseengine.eu</b><br/>cross-project memory<br/>long-form posts"]
    end

    src --> agent
    agent <-. "validates" .-> oracle
    agent --> rivetCli
    agent --> rivetMcp
    agent --> rivetLsp
    agent --> blog
    rivetBox -. "context" .-> agent
    blog -. "context" .-> agent

    classDef src fill:#13161f,stroke:#4a5068,color:#8b90a0;
    classDef agent fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef oracle fill:#1a1d27,stroke:#f87171,color:#e1e4ed;
    classDef tspine fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
    classDef tcross fill:#1a1d27,stroke:#c084fc,color:#e1e4ed;
    classDef grp fill:#13161f,stroke:#3d4258,color:#8b90a0;
    classDef inner fill:#0f1117,stroke:#4ade80,color:#8b90a0;

    class src src;
    class agent agent;
    class oracle oracle;
    class rivetContent tspine;
    class rivetCli,rivetMcp,rivetLsp inner;
    class blog tcross;
    class dests,rivetBox grp;
{% end %}

The agent is the verb. The oracle is the gate. The typed corpus is the auditable result. The blog is the cross-project compounding layer that survives session resets and seeds context for the next agent. Karpathy's pattern names the third surface; the SDD post named the second; rivet was already the first.

## Why this is unheard from where I sit

Cybersecurity and safety-critical engineering have their own knowledge architectures. Threat models, hazard analyses, traceability matrices, safety cases. Most of the people doing this work are still doing the bookkeeping by hand and doubting AI agents as too unreliable to trust with the audit artifact. The view from there is: agents accelerate code production, and that's a problem because traceability cannot keep up.

The LLM-tooling community lives elsewhere. Building knowledge bases, building agent scaffolds, building MCP integrations — but typically without knowing what an ASPICE assessor actually asks for, what an ISO 26262 auditor reads, what a safety case argues. The view from there is: knowledge bases are interesting; rigor is a separate problem.

The pattern that bridges both communities — agents do the labor, mechanical oracles do the verification, typed schemas do the bookkeeping, humans curate the inputs and approve the outputs — sits at an intersection that almost nobody occupies. The first community thinks AI is unreliable; the second community has not met an auditor. It is genuinely rare to see a working stack that takes both seriously, and it took the three patterns landing in public over the same six-week window — Karpathy's gist (April 2026), Anthropic's Mythos preview (April 2026), rivet's v0.1.0 (March 2026) — for me to articulate why the union is the thing that matters, not any one of the patterns.

This is not a foresight claim. The data model in rivet is sphinx-needs and DOORS lineage; the agent scaffold in our `scripts/mythos/` is openly modeled on Anthropic's preview. What the lineage gives me is a vantage point: when the LLM-tooling community independently arrives at structural patterns the safety-critical community settled decades ago, I can recognise the convergence quickly and ship a Rust-native MCP-exposed implementation faster than someone who has to rediscover the pattern. That advantage is real and durable but it is community arbitrage, not prediction. The thing genuinely worth saying is that the *union* is unheard of, not that I anticipated any single pillar of it.

## What rivet should borrow from Karpathy

Two small things — both extending the typed model rather than loosening it. Both are open as issues against the rivet repo:

- **[#206](https://github.com/pulseengine/rivet/issues/206) — `rivet bundle <ID> --depth N`.** Emit one self-contained YAML or JSONL document with the root + transitively-linked neighbours, link types as inline annotations. Format-equivalent to Karpathy's whole-wiki-paste; YAML preserves typed structure where markdown would flatten it.
- **[#207](https://github.com/pulseengine/rivet/issues/207) — Inline ID-reference detection.** When a description names `REQ-028`, `rivet validate` warns if no typed link exists. The `[[wikilinks]]` discipline for the typed-graph world.

Notably absent: an ingest verb. The agent runs the ingest. rivet's job is the validators.

## What rivet should not borrow

The format. Several gist commenters argue forcefully that LLM-generated markdown is *"linguistic fraud"*[^gnusupport-comment] — un-audited prose written by the same LLM that reads it is a closed loop with no external truth. rivet's escape from that loop is the typed schema and the mechanical validators. A free-form markdown surface inside rivet would bypass both, and that is exactly the failure mode the safety-critical community has spent decades learning to refuse.

The librarian metaphor — *"the librarian writes index cards and essays, not revised encyclopedia entries"*[^seo-warlord-comment] — is the rivet stance. Atoms are typed artifacts; synthesis is a future `synthesis` artifact type that links to its atoms via `derived-from`.

## What this changes

[PR #205](https://github.com/pulseengine/rivet/pull/205) is the union doing the work. The Mythos slop-hunt audit pipeline at `scripts/mythos/` ran the oracle-gated pattern over rivet's own codebase: it confirmed three orphan-slop chains (DD-064, DD-065, DD-066), wired three approved-but-unrealized requirements (REQ-027, REQ-006, FEAT-011) into live tested implementations, and moved traceability coverage from 87/236 (36.9%) to 94/238 (39.5%) on a single branch. Twelve typed artifacts, mechanical oracles confirming each, ~370 lines of orphan code deleted, no LLM hallucinations because the oracle either fires or it doesn't.

That run does not happen — not in the same way, not with the same audit-readable evidence — if you take any one of the three pillars away. Without typed compliance, there is no place for the audit findings to land. Without oracle-gated agents, there is no mechanical signal separating real findings from confident-sounding hallucinations. Without LLM-maintained knowledge, there is no agent doing the labor that lets you do an audit at this depth in a session, instead of in a quarter.

That is the synthesis worth defending. Not as a roadmap claim, not as foresight, but as a working observation from a cybersecurity and safety-critical desk: anyone running fewer than all three of these pillars is leaving rigor or labor on the table. Karpathy named the third one. PR #205 gave it teeth.

[^seo-warlord-comment]: Comment by `@SEO-Warlord` on Karpathy's gist, 2026-04-23. The thread itself is worth reading end-to-end — the architectural debate between "LLM Wiki" and "Zettelkasten" framings is more useful than the gist alone.

[^gnusupport-comment]: Comment by `@gnusupport` on the same gist. The post is intemperate ("ARCHITECTURAL CRIME SCENE") but the underlying critique — un-audited LLM prose summarising LLM prose with no source provenance is dangerous — is the exact failure mode rivet's typed schema and `Provenance.reviewed_by` are designed to prevent.
