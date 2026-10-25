+++
title = "The orchestrator: who does what when bottlenecks won't go away"
description = "Bottlenecks will always exist — hardware contention, CI queues, decision queues, cross-repo dependencies. But the principle is clear: jess orchestrates, relay flies, gale provides the kernel. The roles don't move. The bottlenecks do."
date = 2026-10-30
draft = true
ready = true
[taxonomies]
tags = ["process", "ai-agents", "orchestration", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**Bottlenecks will always exist. But the principle — who does what — is
clear.** jess orchestrates. relay flies. gale provides the kernel. The
bottlenecks move — hardware contention, CI queues, decision queues,
cross-repo dependencies. The roles don't. The factory is not a hierarchy.
It is a set of roles, each with a clear job, connected by contracts.
{% </insight> %}

[The first post](/blog/safe-was-built-for-slow-humans/) argued that the
bottleneck in an agent factory is not generation — it is verification and
decisions. [The second post](/blog/can-we-deliver-x-by-january/) showed how
to estimate from gates and flow history. This post is about the people: who
does what, and why the roles are clear even when the bottlenecks are not.

## The roles

Three repos, three roles, one factory:

| Role | Repo | What they do | The bottleneck they own |
|---|---|---|---|
| **Orchestrator** | jess | Hardware integration, release watch, the ladder from sim to silicon | Hardware availability, release timing |
| **Flight stack** | relay | The control cascade, the verified flight software | Simulation fidelity, HITL binding |
| **Kernel** | gale | The verified OS primitives, the foundation | Formal proofs, silicon bring-up |

The names are not labels. They are **principles**. "Orchestrator" means: you
integrate, you watch the release, you own the ladder. "Flight stack" means:
you fly, you verify, you ship the cascade. "Kernel" means: you provide the
primitives, you prove them, you're the foundation.

## The full dependency graph

The chain is not just gale → relay → jess. Every repo has dependencies.
Here is the full picture, measured from the issue trackers and READMEs on
26 October 2026:

{% <mermaid> %}
flowchart TB
    subgraph toolchain["Toolchain (foundation)"]
        direction LR
        meld["meld<br/>fuse"]
        loom["loom<br/>optimize"]
        synth["synth<br/>AOT compile"]
        kiln["kiln<br/>runtime"]
        sigil["sigil<br/>signing"]
    end

    subgraph verification["Verification & architecture"]
        direction LR
        rivet["rivet<br/>traceability"]
        spar["spar<br/>architecture"]
        witness["witness<br/>coverage"]
        ordeal["ordeal<br/>SMT solver"]
    end

    subgraph app["Application stack"]
        direction TB
        gale["gale<br/>kernel"]
        relay["relay<br/>flight stack"]
        jess["jess<br/>orchestrator"]
    end

    %% Toolchain pipeline
    meld --> loom --> synth --> kiln

    %% Verification chain
    rivet --> witness --> sigil

    %% gale depends on toolchain + ordeal
    meld --> gale
    loom --> gale
    synth --> gale
    ordeal --> gale

    %% relay depends on toolchain + gale + rivet
    meld --> relay
    synth --> relay
    gale --> relay
    rivet --> relay

    %% jess depends on everything
    relay --> jess
    meld --> jess
    loom --> jess
    synth --> jess
    gale --> jess
    rivet --> jess
    spar --> jess
    sigil --> jess

    %% Cross-repo issue references
    loom -.-> ordeal
    loom -.-> spar
    loom -.-> synth
    loom -.-> gale
    sigil -.-> synth
    sigil -.-> loom
    spar -.-> rivet
    witness -.-> rivet
    kiln -.-> rivet
    ordeal -.-> synth

    style meld fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style loom fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style synth fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style kiln fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style sigil fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style rivet fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed
    style spar fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed
    style witness fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed
    style ordeal fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed
    style gale fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style relay fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style jess fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed

    classDef tool fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
    classDef verify fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed;
    classDef app fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef orch fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
{% </mermaid> %}

**Three layers:**

| Layer | Repos | What they do |
|---|---|---|
| **Toolchain** | meld, loom, synth, kiln, sigil | Fuse, optimize, compile, run, sign |
| **Verification** | rivet, spar, witness, ordeal | Trace, architect, cover, solve |
| **Application** | gale, relay, jess | Kernel, flight stack, orchestrator |

**The pipeline:** meld → loom → synth → kiln (fuse → optimize → compile → run)

**The verification chain:** rivet → witness → sigil (trace → cover → sign)

**The application stack:** gale → relay → jess (kernel → flight → orchestrator)

jess depends on **everything**. relay depends on the toolchain + gale + rivet.
gale depends on the toolchain + ordeal. The bottlenecks propagate up the
chain — and across it.

## The skills are the process

The agents don't work ad-hoc. They work from **skills** — patterns defined
in this repository. Each skill is a procedure: when it fires, what steps to
follow, which gates to pass, when to stop and ask a human.

| Skill | Pattern | Loop |
|---|---|---|
| `issue-hunt` | Incremental bug/feature hunt over the issue tracker | Every X hours |
| `gate-potency` | Audit whether CI checks can still fail | Before every release |
| `oracle-gate-a-change` | Wire a mechanical check before merging | Per change |
| `pulseengine-feature-loop` | End-to-end feature: spar → rivet → code → witness → sigil | Per feature |
| `release-planning` | Land + ship, accumulate toward a release | Per release |
| `clean-room-verification` | Fresh-context subagent validates findings | Per campaign |

The orchestrator's job is not to do the work. It is to:

1. **Define the skills** — the patterns, the procedures, the gates
2. **Trigger the agents** — start the loops, every X hours
3. **Review the output** — check the gates, read the reports
4. **Decide what's next** — clear the decision queue, re-prioritize

The agents work autonomously between triggers. They file issues, fix bugs,
run the gates, open PRs. The orchestrator stays away — and comes back to
review.

This is the **vocabulary is the process** insight in action. The skills are
the vocabulary. The loops are the cadence. The agents are the workers. The
orchestrator is the human who defines, triggers, reviews, decides.

## Resource constraints and the critical path

The factory has real limitations. Sixteen gigabytes of RAM. Limited disk
space. A runner queue that backs up. GitHub outages that take the whole
fleet offline for hours. These are not theoretical — they are the constraints
we fight with every day.

These limitations make the **overseeing part even more important**. When
resources are scarce, someone has to decide who gets what. Someone has to
see the critical path. Someone has to ensure the queue is prioritized.

That someone is the orchestrator.

**What the orchestrator needs to define in the process:**

| Question | What it means | Where it shows |
|---|---|---|
| **Who has a need?** | Which agent/repo needs which resource (RAM, disk, runner, hardware) | Resource allocation table |
| **What is the critical chain?** | The longest chain of dependent gates — the minimum release time | Critical path diagram |
| **Is it properly queued?** | Is the critical path at the front of the queue, or buried behind non-critical work? | Queue dashboard |

**The dashboard is the control tower.** It shows the runner queue, the
hardware availability, the GitHub outage status. The orchestrator looks at
the dashboard and sees: 69 jobs queued on one runner pool, 5 minutes waiting,
no estimate because fewer than 5 recent jobs in this pool. The orchestrator
decides: does this job go to the front of the queue, or does it wait?

**GitHub outages are a bottleneck.** When GitHub goes down, the whole fleet
stops. The agents can't file issues, can't open PRs, can't run CI. The
orchestrator sees the outage on the dashboard and decides: do we wait, or do
we work on something that doesn't need GitHub?

**The critical path needs priority.** If jess is blocked on relay, and relay
is blocked on gale, then gale is the critical path. The orchestrator ensures
that gale's jobs are at the front of the runner queue, that gale's hardware
is available, that gale's decisions are cleared first. The critical path
gets the resources. The non-critical path waits.

**The principle:** resource constraints make the orchestrator's role
critical. When resources are scarce, someone has to see the whole picture,
visualize the critical path, and ensure the queue is prioritized. That
someone is the orchestrator.

## Building your own tools

The toolchain is not fixed. It is built as needed. When a tool is a
bottleneck, you build your own.

**Anthropic wrote their own git replacement.** Git was a bottleneck — slow,
complex, error-prone. So they built [Jujutsu](https://github.com/jj-vcs/jj)
(a Git-compatible VCS in Rust). The new tool fits their stack: fast, simple,
no C++.

**We wrote ordeal.** Z3 was a bottleneck — slow build time (C++), friction
with our Rust stack, licensing concerns. So we built
[ordeal](https://github.com/pulseengine/ordeal) — a certificate-checked
QF_BV SMT solver in pure Rust. Untrusted solver + formally-verified LRAT
checker (CompCert pattern). Fast build, no C++, fits our stack.

The pattern:

| Existing tool | Bottleneck | Your tool | Why it fits |
|---|---|---|---|
| Git | Slow, complex, error-prone | Jujutsu (jj) | Rust, fast, simple |
| Z3 | Slow build (C++), friction with Rust | ordeal | Pure Rust, fast build, certificate-checked |
| gcov / llvm-cov | No MC/DC vocabulary | witness | MC/DC truth tables for Wasm |
| serde_yaml | Slow, unsafe | rivet value model | Rust-native, schema-driven |
| Manual traceability | Error-prone, slow | rivet | Git-native, schema-driven, LSP |

**The orchestrator's decision:** when a tool is a bottleneck, do you build
your own, or work around it? The orchestrator decides:

- **Build** — if the bottleneck is on the critical path, if it causes
  friction every day, if the workaround is worse than the tool
- **Work around** — if the bottleneck is rare, if the workaround is cheap,
  if the tool is not on the critical path

**Friction is data.** When a tool errors, produces wrong output, lacks a
capability, or forces a workaround — file it. The friction report is the
input to the build decision. A workaround you don't report is friction the
next agent re-hits.

The toolchain layer of the factory — meld, loom, synth, kiln, sigil,
ordeal, rivet, spar, witness — was built this way. Each one removed a
bottleneck. Each one fits the stack. None of them were bought off-the-shelf.

## Cross-repo issues: the bottlenecks are real

The issues don't stay in one repo. They propagate.

**jess depends on relay:**

- jess #264: "Ladder: develop in wasm → deploy unchanged. Rung 1 (relay) is
  bit-exact" — jess can't deploy to hardware until relay's wasm cascade is
  bit-exact in simulation.
- jess #167: "Consumption contract: how jess integrates relay's flight
  components" — jess needs a **contract** for how to consume relay's WASM
  components.

**relay depends on jess:**

- relay #572: "HITL wire binding carries no battery element" — relay's
  Hardware-in-the-Loop binding needs jess's hardware to test.
- relay #589: "falcon-ekf and falcon-iekf export identical interface" —
  **discovered by jess** (jess#293), confirmed by relay. Downstream finds
  upstream bugs.

**gale and jess collide:**

- gale #356: "Shared bench: jess and gale are about to collide on the same
  STLINK-V3 / G474" — both need the **same physical hardware**. Two agents,
  one debug probe.

## The pattern

1. **Downstream dependencies** — jess can't ship until relay is bit-exact.
2. **Upstream feedback** — jess discovers issues in relay that relay didn't
   know about.
3. **Resource contention** — gale and jess compete for the same hardware.
4. **Contracts solve it** — jess #167 is literally about defining a
   "consumption contract" between jess and relay.

The bottlenecks are there. They won't go away. But the roles are clear.

## Multiple factories: one orchestrator per domain

The factory model scales horizontally. Each domain is its own factory, with
its own stations, its own machines, its own orchestrator.

| Domain | Orchestrator | Stations | Machines |
|---|---|---|---|
| **Drone software** | jess | gale (kernel), relay (flight stack) | CI, agents, gates, hardware |
| **Home automation** | wohl | sensors, hub, matter composition | CI, agents, gates, Thread/STM32 |

**jess is the overarching for the drone software.** It integrates relay's
flight stack onto hardware. It watches the release. It owns the ladder from
simulation to silicon.

**wohl is home automation and orchestration as its own.** It is a home
supervision system built on PulseEngine — sensors, hub, matter composition,
Thread/STM32 firmware. It has its own issues, its own CI, its own gates.
And it probably needs its own layer — its own orchestrator, its own control
tower, its own critical path.

**Each part of the software is a station with its own machine.** gale has
its own CI, its own agents, its own gates. relay has its own. jess has its
own. wohl has its own. Each station is a factory cell — it produces, it
verifies, it ships. The orchestrator coordinates the cells.

**The control tower shows all factories.** The meta-layer. The dashboard
that shows: drone factory (jess, relay, gale), home automation factory
(wohl), the toolchain (meld, loom, synth), the verification chain (rivet,
witness, sigil). One view. All factories. All orchestrators. All stations.

**The principle scales.** One orchestrator per domain. One control tower
per factory. One meta-layer across all factories. The model is not "one
big factory" — it is "many small factories, each with its own orchestrator."

## The principle

> **Who does what is more important than how fast.**

The factory is not a hierarchy. It is a set of roles, each with a clear job,
connected by contracts. The bottlenecks move — hardware, CI, decisions,
cross-repo dependencies. The roles don't.

jess orchestrates. relay flies. gale provides the kernel. Everyone knows
their role. The bottlenecks are managed, not eliminated.

## What we would tell you to take from this

**Name the roles.** The names define the responsibilities. "Orchestrator"
is not a title — it's a principle. Who integrates? Who watches the release?
Who owns the ladder?

**Bottlenecks will exist.** Hardware contention, CI queues, decision queues,
cross-repo dependencies. You can't eliminate them. You can only manage them.

**Contracts connect the roles.** The interface between jess and relay is a
contract. The interface between relay and gale is a contract. Define the
contract, and the agents don't collide.

**Downstream finds upstream bugs.** jess discovers issues in relay that
relay didn't know about. The integrator is the canary — they feel the
bottlenecks first.

**The roles don't move.** The bottlenecks do. Fix the hardware contention,
and the CI queue becomes the bottleneck. Add more runners, and the decision
queue moves. The roles stay. The principle stays.

## Limits

This is one factory's structure: three repos, three roles, one dependency
chain. It has not been tested in a larger organisation with more layers,
more roles, and more complex dependencies. The claim is not "this is the
only way to structure a factory" but "the roles are clear, and the
bottlenecks are managed."

The cross-repo issues are real, measured from the issue trackers on 26
October 2026. The dependency chain (gale → relay → jess) is the actual
structure of our repos. The contracts are being defined — jess #167 is the
first consumption contract.

## Sources and caveats

The roles and dependency chain are from the author's own repositories
(pulseengine/jess, pulseengine/relay, pulseengine/gale). The cross-repo
issues are from the GitHub issue trackers, read on 26 October 2026.

The issue numbers and titles are real. The interpretation — that the roles
are clear and the bottlenecks are managed — is the author's view, not a
measured outcome.

---

*This post is part of [PulseEngine](/) — a formally verified WebAssembly
Component Model engine for safety-critical systems. Prior posts in the arc:
[SAFe was built for slow humans](/blog/safe-was-built-for-slow-humans/),
[Can we deliver X by January?](/blog/can-we-deliver-x-by-january/),
[The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/).*
