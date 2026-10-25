+++
title = "The orchestrator: who does what when bottlenecks won't go away"
description = "Bottlenecks will always exist — hardware contention, CI queues, decision queues, cross-repo dependencies. But the principle is clear: jess integrates, relay flies, gale provides the kernel. The roles don't move. The bottlenecks do."
date = 2026-10-28
draft = true
ready = true
[taxonomies]
tags = ["process", "ai-agents", "orchestration", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**The roles are the factory.** jess integrates — watches the
release, owns the ladder. relay flies — the control cascade, verified.
gale provides the kernel — the primitives, the proofs, the foundation.

The names are not labels. They are **principles**. The bottlenecks move —
hardware, CI, decisions, dependencies. The roles don't.

And behind the agents is the **orchestrator** — the one who owns the
factory, enables the agents, reviews the output, and makes the decisions
the oracles cannot. One orchestrator. Many agents. The orchestrator is the owner.
{% </insight> %}

[The first post](/blog/safe-was-built-for-slow-humans/) argued that the
bottleneck in an agent factory is not generation — it is verification and
decisions. [The second post](/blog/can-we-deliver-x-by-january/) showed how
to estimate from gates and flow history. This post is about the roles: who
does what — the agents, the repos, and the orchestrator who enables them —
and why the roles are clear even when the bottlenecks are not.

## The roles

Three repos, three roles, one factory. The roles are not a hierarchy — they
are **principles**. Each role has a clear job, a clear bottleneck, and a
clear connection to the others.

{% <mermaid> %}
flowchart TB
    subgraph roles["The roles (principles, not labels)"]
        direction TB
        jess["<b>jess</b><br/>INTEGRATOR<br/>integrates · watches the release<br/>owns the ladder<br/>sim → silicon"]
        relay["<b>relay</b><br/>FLIGHT STACK<br/>flies · verifies<br/>ships the cascade<br/>control → motors"]
        gale["<b>gale</b><br/>KERNEL<br/>provides the primitives<br/>proves them<br/>the foundation"]
    end

    gale -->|"provides primitives"| relay
    relay -->|"provides flight stack"| jess

    style jess fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style relay fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style gale fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed

    classDef orch fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef flight fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef kernel fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
{% </mermaid> %}

| Role | Repo | What they do | The bottleneck they own |
|---|---|---|---|
| **Integrator** | jess | Hardware integration, release watch, the **ladder** from sim to silicon | Hardware availability, release timing |
| **Flight stack** | relay | The control cascade, the verified flight software | Simulation fidelity, HITL binding |
| **Kernel** | gale | The verified OS primitives, the foundation | Formal proofs, silicon bring-up |

**The names are principles.** "Integrator" means: you integrate, you watch
the release, you own the **ladder** — the deployment path from simulation to
silicon, rung by rung. "Flight stack" means: you fly, you verify,
you ship the cascade. "Kernel" means: you provide the primitives, you prove
them, you're the foundation.

**The roles connect.** gale provides the primitives. relay builds the flight
stack on top of gale. jess integrates relay's flight stack onto hardware.
Each role depends on the one below. The bottlenecks propagate up the chain.

**The roles don't move.** The bottlenecks do. Fix the hardware bottleneck,
and the CI queue becomes the bottleneck. Add more runners, and the decision
queue moves. The roles stay. The principles stay.

## The skills are the process

The agents don't work ad-hoc. They work from **skills** — patterns defined
in this repository. Each skill is a procedure: when it fires, what steps to
follow, which gates to pass, when to stop and ask the orchestrator.

| Skill | Pattern | Loop |
|---|---|---|
| `issue-hunt` | Incremental bug/feature hunt over the issue tracker | Every X hours |
| `gate-potency` | Audit whether CI checks can still fail (Blog 1's "gate potency" metric) | Before every release |
| `oracle-gate-a-change` | Wire a mechanical check before merging | Per change |
| `pulseengine-feature-loop` | End-to-end feature: spar → rivet → code → witness → sigil | Per feature |
| `release-planning` | Land + ship, accumulate toward a release | Per release |
| `clean-room-verification` | Fresh-context subagent validates findings | Per campaign |
| `report-tool-friction` | File a report when a tool errors, lacks capability, or forces a workaround | When friction is noticed |

The orchestrator's job is not to do the work. It is to:

1. **Direct the agents** — tell the pulseengine.eu agent to write or update skills, set the patterns, define the gates
2. **Trigger the agents** — start the loops, every X hours
3. **Review the output** — check the gates, read the reports
4. **Decide what's next** — clear the decision queue, re-prioritize

The agents work autonomously between triggers. They file issues, fix bugs,
run the gates, open PRs. The orchestrator stays away — and comes back to
review.

This is the **vocabulary is the process** insight in action. The skills are
the vocabulary. The loops are the cadence. The agents are the workers. The
orchestrator is the one who directs, triggers, reviews, decides.

## The human in the loop

I am not an agent. I am the **orchestrator** — the one who enables the
agents, reviews the output, and makes the decisions the oracles cannot.
In this factory, I am also the **owner**: the only stakeholder. There is
no team, no Scrum master, no product owner. There are the agents and me.

The pattern is simple: **I enable, the agents do.** I do not write skills —
I tell the pulseengine.eu agent to write or update them based on triggers.
I do not install tools — the agents install `with-device`, configure varve
layers, and claim hardware themselves. I do not write code — the agents do.

But enabling is not the main job. The main job is **prioritization** across
three streams that constantly compete for my attention:

| Stream | What it looks like | Example |
|---|---|---|
| **Friction** | Tools that don't work, workarounds, things that slow agents down | "I did not intend to create these layers to have to maintain them manually — either automated or I get an email with direct approval" |
| **Factory operations** | Keeping the factory running — cron jobs, CI, hardware, queues | "reestablish the cron job — had to restart the agent and it got lost" |
| **Real decisions** | Architecture direction, what to build next, what to merge | "yes these measurements we need to do" / "plan for the next varve release to support Zephyr, WASI, Yocto SDKs" |

My day is spent moving between these three streams. Friction reports pile
up from the agents (`report-tool-friction` skill). Factory operations need
constant nudging — cron jobs die, hardware gets unplugged, CI queues back
up. Real decisions need my judgment — what architecture direction, what to
prioritize, what to merge.

De Bono called this "thinking hats"[^thinking-hats] — different modes of attention for
different kinds of problems. The three streams map onto three hats:

| Stream | Hat | De Bono's description |
|---|---|---|
| **Friction** | **Black** | Negative, evaluation, PMI (Plus, Minus, Interesting) — what's broken, what slows us down |
| **Factory operations** | **Blue** | The big picture, managing, CAF (Consider All Factors), FIP (First Important Priorities) — keep the factory running, decide what matters most |
| **Real decisions** | **Green** | New ideas, lateral thinking, concept challenge — what should we build next, what direction |

But it is not just three hats worn independently. De Bono's sequences show
that blue frames everything — you start with the big picture, move through
the other hats, and return to blue for FIP. My day follows the same
pattern:

{% <mermaid> %}
flowchart LR
    blue1["Blue<br/>factory status<br/>big picture"]
    black["Black<br/>friction reports<br/>what's broken"]
    green["Green<br/>what to build<br/>new ideas"]
    blue2["Blue<br/>FIP<br/>what first?"]
    blue1 --> black --> green --> blue2
    blue2 -.->|"next cycle"| blue1
    style blue1 fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style blue2 fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style black fill:#1a1d27,stroke:#f87171,color:#e1e4ed
    style green fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    classDef blue fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef black fill:#1a1d27,stroke:#f87171,color:#e1e4ed;
    classDef green fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
{% </mermaid> %}

Check the factory (blue). Read what's broken (black). Think about what to
build (green). Prioritize (blue, FIP). Repeat. The blue hat is the one I
wear most — FIP, First Important Priorities. That is the job. I switch
between hats so often that I no longer notice which one I'm wearing. The
prioritization is the thinking; the hats are just the lenses.

What I actually do, day to day:

| Activity | What it looks like |
|---|---|
| **Enable agents** | "continue with the new pulseengine skills" across gale, relay, jess, ordeal, varve — set up a 6-hour cron loop with a one-week timeout |
| **Direct skill work** | Tell the pulseengine.eu agent to write or update skills based on triggers — the agent writes them, not me |
| **Prioritize friction** | Read friction reports, decide: build a new tool, work around, or ignore |
| **Keep the factory running** | Reestablish cron jobs, check CI queues, ensure hardware is available |
| **Make real decisions** | "yes these measurements we need to do" — prioritize the decision queue, plan the next release, allocate hardware |
| **Set up hardware** | Physically set up the test boards, connect cables, power on devices — the agents install `with-device`, configure varve, and claim devices themselves |
| **Review output** | Read the agent reports, check the gates, verify the claims — spawn a clean-room subagent to cross-check |

The concrete architecture work is small. I do not design the architecture —
I ask "what should I do on pulseengine-layer?" and the agents figure it out.
My leverage is in **enabling the agents, prioritizing across
friction/operations/decisions, and verifying the output** — not in writing
code, writing skills, or designing interfaces. The agents do all of that.
One orchestrator, many agents. I am the owner, the only stakeholder, and the
only decision-maker.

This is the same pattern as Blog 1's orchestrator role: the coder becomes
the orchestrator. I used to write code; now I enable the agents, prioritize
across friction/operations/decisions, and verify the output. The bottleneck
moves from code production to prioritization — and I am the prioritizer.

{% <note kind="tip"> %}
**The title stayed; the work moved.** My own path: engineer writing software
and coordinating work, then software architect, then system architect, then
team lead, product owner, Scrum master — the SAFe roles. Now I hold the
title Distinguished Engineer, and I have started to actually orchestrate:
down to the agents. As a DE, I help decide how things are done — the
architecture, the approach, the design. But even that is shifting: the
amount of architecture I personally have to provide is shrinking. The
agents produce the first draft; I review, correct, and decide where my
expertise still matters. I learn along the way — formal methods, new
toolchains, new verification techniques — to keep my judgment sharp where
it counts. The agents do the work; I do the deciding.
{% </note> %}

The WIP limit on the decision queue (Blog 1) caps how many decisions can
wait. I prioritize within that cap. In this factory, the team size is one:
me. The agents do the work — writing code, writing skills, installing tools,
claiming hardware; I enable, prioritize, and own the factory.

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
| **What is the critical path?** | The longest chain of dependent gates — the minimum release time | Critical path diagram |
| **Is it properly queued?** | Is the critical path at the front of the queue, or buried behind non-critical work? | Queue dashboard |

**The dashboard is the control tower.** It shows the runner queue, the
hardware availability, the GitHub outage status. The orchestrator looks at
the dashboard and sees: 69 jobs queued on one runner pool, 5 minutes waiting.
The ask feature estimates when a job will run — but only when the pool has
enough recent history (at least 5 recent jobs in the last 3 hours). A pool
with sparse history returns "no estimate" rather than a guess. The
orchestrator decides: does this job go to the front of the queue, or does
it wait?

**GitHub outages are a bottleneck.** When GitHub goes down, the whole fleet
stops. The agents can't file issues, can't open PRs, can't run CI. The
orchestrator sees the outage on the dashboard and decides: do we wait, or do
we work on something that doesn't need GitHub?

**The critical path needs priority.** If jess is blocked on relay, and relay
is blocked on gale, then gale is the critical path. The orchestrator ensures
that gale's jobs are at the front of the runner queue, that gale's hardware
is available, that gale's decisions are cleared first. The critical path
gets the resources. The non-critical path waits.

**Hardware scheduling is a contract.** jess releases `with-device` — a small
tool that claims and releases hardware. An agent runs `with-device claim
pixhawk-6xrt`, and the device is locked. Other agents see: CLAIMED, by whom,
since when. The agent runs `with-device release pixhawk-6xrt`, and the
device is free. The tool informs the other agents: who has the device, when
they got it, for how long they need it. The dashboard shows the same: which
boards are free, which are busy, who's holding them.

```
$ with-device --status
  pixhawk-6xrt       CLAIMED by agent-7 since 14:32 (needs 2h)
  stlink-v1          FREE
  stlink-v1-f100     CLAIMED by agent-3 since 09:15 (needs 30m)
```

The contract is the lock. The visibility is the status. The orchestrator
sees the whole picture — and decides who waits.

**The principle:** resource constraints make the orchestrator's role
critical. When resources are scarce, someone has to see the whole picture,
visualize the critical path, and ensure the queue is prioritized. That
someone is the orchestrator. The orchestrator manages **flow** across the
stations — the same flow Blog 1 defined as the replacement for sprints.
The WIP limit on the decision queue caps how many items wait; the
orchestrator prioritizes within that cap.

## Building your own tools

The toolchain is not fixed. It is built as needed. When a tool is a
bottleneck, you build your own.

**Anthropic wrote their own source control.** Git was a bottleneck — too
slow for their scale. In May 2026 they averaged 2,500 merges per day; by
September, 30,000 per day. Their monorepo history alone is almost 100 GB,
and they perform 25 million checkouts per day for CI — over 600 PB of git
traffic per day. Git's decentralized design doesn't fit that scale. So they
built [Scion](https://www.anthropic.com/research/redesigning-source-control),
an in-house version control system, and migrated their monorepo in five
months[^anthropic-scion]. The key insight from their article: *"Claude's
ability to write code was both what put us in this situation in the first
place and how we were able to quickly build a high-quality, scalable system
to deal with it."* The agents created the bottleneck — and built the tool
to remove it.

**We wrote ordeal.** Z3 was a bottleneck — slow build time (C++), friction
with our Rust stack, licensing concerns. So we built
[ordeal](https://github.com/pulseengine/ordeal) — a certificate-checked
QF_BV SMT solver in pure Rust. Untrusted solver + formally-verified LRAT
checker (CompCert pattern). Fast build, no C++, fits our stack.

The pattern:

| Existing tool | Bottleneck | Your tool | Why it fits |
|---|---|---|---|
| Git | Too slow for 30k merges/day, 100 GB monorepo, 600 PB traffic/day | Scion (Anthropic) | Built for their scale, migrated in 5 months |
| Z3 | Slow build (C++), friction with Rust | ordeal | Pure Rust, fast build, certificate-checked |
| gcov / llvm-cov | No MC/DC vocabulary | witness | MC/DC truth tables for Wasm |
| serde_yaml | Unsafe, unmaintained | rivet-yaml (complete replacement) | Rust-native, schema-driven, fully replaced |
| Manual traceability | Error-prone, slow | rivet | Git-native, schema-driven, LSP |

**The orchestrator's decision:** when a tool is a bottleneck, do you build
your own, or work around it? The orchestrator decides:

- **Build** — if the bottleneck is on the critical path, if it causes
  friction every day, if the workaround is worse than the tool
- **Work around** — if the bottleneck is rare, if the workaround is cheap,
  if the tool is not on the critical path

**Friction is data.** When a tool errors, produces wrong output, lacks a
capability, or forces a workaround — file it. The agents have a skill for
this: `report-tool-friction`. It fires the moment an agent notices itself
working *around* a tool instead of *with* it. The friction report is the
input to the build decision. A workaround you don't report is friction the
next agent re-hits.

The toolchain layer of the factory — meld, loom, synth, kiln, sigil,
varve, warte — was built this way. Each one removed a
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

## The contracts: what relay provides to jess, what jess provides to relay

The issues propagate because the **contracts** are not clear. A contract is
the thin agreed interface between two stations. relay can't break it without
telling jess. jess can't break it without telling relay.

Here are the real contracts, from the issue trackers:

### HAL contract (jess #62)

> **relay owns the hardware ABSTRACTION**: the bus/peripheral seam *traits*
> (SPI/I2C/UART/PWM/ADC/CAN). **jess owns the BINDING to real silicon**:
> concrete impls of those seams over the i.MX RT1176 peripherals.
>
> Seam in the middle = the thin agreed interface. relay can't break it
> without telling jess; jess can't break it without telling relay.

| Seam (relay trait) | Status on relay side | jess binds |
|---|---|---|
| `RegBus` (read_reg/write_reg/read_burst) | exists — but duplicated | LPSPI/LPI2C bindings + pinmux |
| `CanBus` (frame tx/rx) + DroneCAN | relay to ADD | CAN peripheral binding |

### Consumption contract (jess #167)

> `falcon-flight` is a published, cosign-signed WASM OCI component. With a
> **WASM Component Model runtime now on all three cores**, the deployment
> substrate is settled.
>
> **Interface shape at the seam:** per-cycle
> `step(sensor-sample) -> actuator-cmd` (synchronous).
>
> **Seam types:** the `sensor-sample` / `actuator-cmd` WIT will be
> **spar-generated from the AADL**.

### HITL wire binding (relay #572)

> The seam's `sensor-frame` is a flat **76 B** payload (imu 24 + dt 4 +
> three ...). Carries no heading, no rotor RPM, and **no battery**.
>
> A HITL host can only supply what the wire frame carries, and the frame
> has no battery element — so a host driving the supervised component over
> the HITL transport **cannot arm it. Ever.**
>
> Predicted by jess #167 six days before relay #571 (the original report;
> #572 is the tracking issue) existed.

### Interface identity (relay #589)

> `falcon-ekf` (legacy Mahony) and `falcon-iekf` export the **identical**
> `ekf@0.11.0` interface — a consumer cannot tell the flight estimator from
> the legacy one.
>
> jess has closed it on their side with `tools/deps/check-estimator-identity.sh`
> (a pin-identity guard). Fix: give it a **distinct identity** — e.g. a
> `legacy-ekf` interface.

### The pattern

| Contract | relay provides | jess provides | Issue |
|---|---|---|---|
| **HAL contract** | Hardware abstraction (seam traits) | Binding to real silicon | jess #62 |
| **Consumption contract** | Flight stack (WASM components) | Integration, release watch | jess #167 |
| **HITL wire binding** | HITL protocol (sensor-frame) | HITL host (hardware) | relay #572 |
| **Interface identity** | Distinct interface per component | Pin-identity guard | relay #589 |

**The contract is the interface.** It is thin, agreed, and bidirectional.
relay can't break it without telling jess. jess can't break it without
telling relay. When the contract is clear, the issues don't propagate.
When the contract is missing, the issues propagate.

## The pattern

1. **Downstream dependencies** — jess can't ship until relay is bit-exact.
2. **Upstream feedback** — jess discovers issues in relay that relay didn't
   know about.
3. **Resource contention** — gale and jess compete for the same hardware.
4. **Contracts solve it** — jess #167 is literally about defining a
   "consumption contract" between jess and relay.

The bottlenecks are there. They won't go away. But the roles are clear.

## Multiple factories: one integrator per domain

The factory model scales horizontally. Each domain is its own factory, with
its own stations, its own machines, its own integrator.

| Domain | Integrator | Stations | Machines |
|---|---|---|---|
| **Drone software** | jess | gale (kernel), relay (flight stack) | CI, agents, gates, hardware |
| **Home automation** | wohl | sensors, hub, matter composition | CI, agents, gates, Thread/STM32 |

**jess is the integrator for the drone software.** It integrates relay's
flight stack onto hardware. It watches the release. It owns the ladder from
simulation to silicon.

**wohl is home automation and orchestration as its own.** It is a home
supervision system built on PulseEngine — sensors, hub, matter composition,
Thread/STM32 firmware. It has its own issues, its own CI, its own gates.
And it probably needs its own layer — its own integrator, its own control
tower, its own critical path.

**Each part of the software is a station with its own machine.** gale has
its own CI, its own agents, its own gates. relay has its own. jess has its
own. wohl has its own. Each station produces, verifies, ships. The
integrator coordinates the stations.

**The control tower shows all factories.** The **meta-layer** — the
cross-factory view that shows all control towers in one dashboard. The
dashboard that shows: drone factory (jess, relay, gale), home automation
factory (wohl), the toolchain (meld, loom, synth), the verification chain
(rivet, witness, sigil). One view. All factories. All integrators. All
stations.

**The principle scales.** One integrator per domain. One control tower
per factory. One meta-layer across all factories. The model is not "one
big factory" — it is "many small factories, each with its own integrator."

## The jess dependency tree

jess is the integrator for the drone software. It depends on everything.
Here is the full tree, from jess down, grouped by layer:

{% <mermaid> %}
flowchart TD
    subgraph app["Layer 3: Application"]
        direction TB
        jess["jess<br/>integrator<br/>drone software"]
        relay["relay<br/>flight stack"]
        gale["gale<br/>kernel"]
    end

    subgraph verify["Layer 2: Verification & architecture"]
        direction TB
        rivet["rivet<br/>traceability"]
        spar["spar<br/>architecture"]
        witness["witness<br/>coverage"]
        ordeal["ordeal<br/>SMT solver"]
    end

    subgraph tool["Layer 1: Toolchain"]
        direction TB
        meld["meld<br/>fuse"]
        loom["loom<br/>optimize"]
        synth["synth<br/>AOT compile"]
        kiln["kiln<br/>runtime"]
        sigil["sigil<br/>signing"]
        varve["varve<br/>toolchain layer manager"]
        warte["warte<br/>control tower"]
    end

    subgraph agents["Agents (external tools)"]
        direction TB
        claude["Claude Code<br/>(Anthropic)"]
        vibe["Vibe<br/>(Mistral)"]
    end

    subgraph skills["Skills (pulseengine.eu)"]
        direction TB
        pe["pulseengine.eu<br/>plugin + skills<br/>issue-hunt · gate-potency<br/>oracle-gate-a-change"]
    end

    %% jess depends on application layer
    jess --> relay
    jess --> gale

    %% jess depends on verification layer
    jess --> rivet
    jess --> spar

    %% jess depends on toolchain
    jess --> meld
    jess --> loom
    jess --> synth
    jess --> sigil

    %% relay depends on application + verification + toolchain
    relay --> gale
    relay --> rivet
    relay --> meld
    relay --> synth

    %% gale depends on toolchain + verification
    gale --> meld
    gale --> loom
    gale --> synth
    gale --> ordeal

    %% Verification layer dependencies
    spar --> rivet
    witness --> rivet
    witness --> sigil
    ordeal --> rivet
    ordeal --> synth

    %% Toolchain layer dependencies
    loom --> rivet
    loom --> ordeal
    loom --> spar
    loom --> synth
    synth --> meld
    sigil --> rivet
    sigil --> synth
    sigil --> loom
    rivet --> meld
    kiln --> rivet

    %% All repos depend on agents (Claude Code, Vibe)
    jess --> claude
    jess --> vibe
    relay --> claude
    relay --> vibe
    gale --> claude
    gale --> vibe
    meld --> claude
    meld --> vibe
    loom --> claude
    loom --> vibe
    synth --> claude
    synth --> vibe
    kiln --> claude
    kiln --> vibe
    sigil --> claude
    sigil --> vibe
    rivet --> claude
    rivet --> vibe
    spar --> claude
    spar --> vibe
    witness --> claude
    witness --> vibe
    ordeal --> claude
    ordeal --> vibe
    varve --> claude
    varve --> vibe
    warte --> claude
    warte --> vibe

    %% Tools depend on the toolchain layer they are in (varve manages toolchain layers)
    meld --> varve
    loom --> varve
    synth --> varve
    kiln --> varve
    sigil --> varve
    warte --> varve

    %% Agents depend on skills (used by all)
    claude --> pe
    vibe --> pe

    style jess fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style relay fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style gale fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style meld fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style loom fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style synth fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style kiln fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style sigil fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style varve fill:#1a1d27,stroke:#c084fc,color:#e1e4ed
    style warte fill:#1a1d27,stroke:#f87171,color:#e1e4ed
    style rivet fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed
    style spar fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed
    style witness fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed
    style ordeal fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed
    style claude fill:#13161f,stroke:#c084fc,color:#e1e4ed
    style vibe fill:#13161f,stroke:#c084fc,color:#e1e4ed
    style pe fill:#13161f,stroke:#fbbf24,color:#e1e4ed

    classDef orch fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef app fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef tool fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
    classDef verify fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed;
    classDef agent fill:#13161f,stroke:#c084fc,color:#e1e4ed;
    classDef skill fill:#13161f,stroke:#fbbf24,color:#e1e4ed;
{% </mermaid> %}

**The full chain:** repos → agents → skills

- **jess, relay, gale** (and all repos) depend on **agents** — Claude Code
  (Anthropic), Vibe (Mistral). The agents do the work.
- The **agents** depend on **skills** — defined in **pulseengine.eu** (the
  plugin). The skills are the patterns: issue-hunt, gate-potency,
  oracle-gate-a-change, release-planning.
- The **skills** are the process. The **agents** are the workers. The
  **repos** are the stations.

**My view:** jess doesn't just depend on relay and gale.
jess depends on **Claude Code** and **Vibe**. Those agents depend on the
**skills** in pulseengine.eu. The whole chain is visible in the control
tower.

**Reading the tree:**

- **jess** (blue) depends on **8 repos** directly: relay, meld, loom, synth,
  gale, rivet, spar, sigil
- **relay** (amber) depends on meld, synth, gale, rivet
- **gale** (amber) depends on meld, loom, synth, ordeal
- **Toolchain** (green): meld, loom, synth, kiln, sigil — the pipeline
- **Layer manager** (purple): varve — pinned, signed, dated toolchain
  bundles. One layer per release. Each tool relies on the layer it is
  based upon.
- **Control tower** (red): warte — the dashboard, a tool like the others
- **Verification** (cyan): rivet, spar, witness, ordeal — trace, architect,
  cover, solve
- **All repos** depend on **agents** (Claude Code, Vibe) — the agents do
  the work on every repo
- **Agents** depend on **skills** (pulseengine.eu) — the skills are the
  patterns, used by all agents on all repos

{% <note kind="tip"> %}
**Projects and tools.** rivet and synth appear in Blog 2's corpus as
projects (they ship releases). Here they appear as tools in the
verification and toolchain layers. A repo can be both: it ships releases
(it's a project) and it provides a capability to other repos (it's a
tool). The corpus measures release velocity; the dependency tree shows
what depends on what.
{% </note> %}

{% <note kind="tip"> %}
**Two kinds of "layer."** varve manages **toolchain layers** — pinned,
signed, dated bundles of tools (one layer per release). The **architectural
layers** in this post (toolchain, verification, application) are a
different concept — they describe what each group of tools *does*, not
which bundle they ship in. A tool can be in the toolchain architectural
layer and still ship in a varve layer with other tools. The varve layer
is the bundle; the architectural layer is the role.
{% </note> %}

**The critical path from jess:** jess → relay → gale → ordeal → synth → meld

That is the longest chain. If any link in that chain is delayed, jess is
delayed. The critical path runs through the toolchain and the verification
chain — not just the application stack. (Blog 2's 24-week critical path
covers the application layer only: gale → relay → jess. This post's
critical path is the full dependency chain for jess's build.)

### The issue-level dependency tree

The repos depend on each other. But the **issues** depend on each other too.
One issue blocks another. That one blocks the next. Downstream.

Here are illustrative issue-level chains, traced from the issue trackers on
26 October 2026. The issue numbers and titles are real; the dependency
edges show the *pattern* — how issues propagate across repos — not a
complete trace of every dependency:

{% <mermaid> %}
flowchart TD
    subgraph jess_issues["jess issues (integrator)"]
        j264["jess #264<br/>Ladder: deploy unchanged<br/>Rung 1 (relay) bit-exact"]
        j167["jess #167<br/>Consumption contract<br/>how jess integrates relay"]
        j280["jess #280<br/>with-device: EACCES<br/>on lock file"]
        j266["jess #266<br/>hardware-catalog<br/>name three new boards"]
    end

    subgraph relay_issues["relay issues (flight stack)"]
        r202["relay #202<br/>witness MC/DC harness<br/>async-lift exports"]
        r382["relay #382<br/>wasm seam v0.8<br/>host tick rate"]
        r380["relay #380<br/>wasm cascade<br/>cannot hold altitude"]
        r214["relay #214<br/>relay-hal: peripheral<br/>abstraction seams"]
        r506["relay #506<br/>req: 'largest 192 KB'<br/>premise in question"]
    end

    subgraph gale_issues["gale issues (kernel)"]
        g398["gale #398<br/>dissolved objects<br/>address wasm data"]
        g397["gale #397<br/>bench: four boards<br/>shared hardware"]
    end

    subgraph synth_issues["synth issues (toolchain)"]
        s1301["synth #1301<br/>ARMv6-M target<br/>cortex-m0 profile"]
    end

    subgraph other_issues["other"]
        j62["jess #62<br/>(referenced by relay #214)"]
    end

    j264 --> r202
    j264 --> r382
    j264 --> r380

    j167 --> r214
    r214 --> j62

    j280 --> r506
    r506 --> g398
    r506 --> j266

    j266 --> s1301
    j266 --> g397
    s1301 --> g397

    style j264 fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style j167 fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style j280 fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style j266 fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style j62 fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style r202 fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style r382 fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style r380 fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style r214 fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style r506 fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style g398 fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed
    style g397 fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed
    style s1301 fill:#1a1d27,stroke:#4ade80,color:#e1e4ed

    classDef orch fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef app fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef verify fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed;
    classDef tool fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
{% </mermaid> %}

**Reading the issue tree:**

- **jess #264** (Ladder) depends on **relay #202, #382, #380** — jess can't
  deploy until relay's wasm is bit-exact. 2 levels.
- **jess #167** (Consumption contract) depends on **relay #214**, which
  depends on **jess #62**. 3 levels. The contract goes both ways.
- **jess #280** (with-device) depends on **relay #506**, which depends on
  **gale #398** and **jess #266**. 3 levels.
- **jess #266** (hardware-catalog) depends on **synth #1301** and
  **gale #397**. synth #1301 depends on **gale #397**. 3 levels.

**The longest chain:** jess #280 → relay #506 → jess #266 → synth #1301 →
gale #397

That is **5 levels** of issue dependencies. If gale #397 is delayed, synth
#1301 is delayed, jess #266 is delayed, relay #506 is delayed, jess #280 is
delayed. The critical path runs through the issues, not just the repos.

**Why this matters:**

- **Estimation** — the critical path of issues determines the minimum time
- **Bottlenecks** — the issues on the critical path are the bottlenecks
- **Prioritization** — work on the critical path issues first
- **Communication** — "jess #280 is blocked on this chain of 5 issues"

## The layered factory: each layer built by a machine

The factory is not a flat list of repos. It is **layers**. Each layer is
built by a **machine** — the combination of agents, CI, and gates that
produces, verifies, and ships. The layers stack: application on top of
verification on top of toolchain.

{% <mermaid> %}
flowchart TB
    subgraph app["Layer 3: Application (built by agents)"]
        direction TB
        jess["jess<br/>integrator"]
        relay["relay<br/>flight stack"]
        gale["gale<br/>kernel"]
        app_machine["⚙️ machine:<br/>agents · CI · gates<br/>skills: issue-hunt,<br/>oracle-gate-a-change"]
    end

    subgraph verify["Layer 2: Verification (built by agents)"]
        direction TB
        rivet["rivet<br/>traceability"]
        spar["spar<br/>architecture"]
        witness["witness<br/>coverage"]
        ordeal["ordeal<br/>SMT solver"]
        verify_machine["⚙️ machine:<br/>agents · CI · gates<br/>skills: gate-potency,<br/>clean-room-verification"]
    end

    subgraph tool["Layer 1: Toolchain (built by agents)"]
        direction TB
        meld["meld<br/>fuse"]
        loom["loom<br/>optimize"]
        synth["synth<br/>AOT compile"]
        kiln["kiln<br/>runtime"]
        sigil["sigil<br/>signing"]
        varve["varve<br/>toolchain layer manager"]
        warte["warte<br/>control tower"]
        tool_machine["⚙️ machine:<br/>agents · CI · gates<br/>skills: release-planning,<br/>release-execution"]
    end

    app --> verify
    verify --> tool

    style jess fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style relay fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style gale fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style rivet fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed
    style spar fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed
    style witness fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed
    style ordeal fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed
    style meld fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style loom fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style synth fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style kiln fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style sigil fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style varve fill:#1a1d27,stroke:#c084fc,color:#e1e4ed
    style warte fill:#1a1d27,stroke:#f87171,color:#e1e4ed
    style app_machine fill:#13161f,stroke:#8b90a0,color:#8b90a0
    style verify_machine fill:#13161f,stroke:#8b90a0,color:#8b90a0
    style tool_machine fill:#13161f,stroke:#8b90a0,color:#8b90a0

    classDef orch fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef app fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef verify fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed;
    classDef tool fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
    classDef machine fill:#13161f,stroke:#8b90a0,color:#8b90a0;
{% </mermaid> %}

**Reading the layers:**

| Layer | Repos | Built by | Machine |
|---|---|---|---|
| **3: Application** | jess, relay, gale | Agents | CI, gates, skills (issue-hunt, oracle-gate-a-change) |
| **2: Verification** | rivet, spar, witness, ordeal | Agents | CI, gates, skills (gate-potency, clean-room-verification) |
| **1: Toolchain** | meld, loom, synth, kiln, sigil, **varve**, **warte** | Agents | CI, gates, skills (release-planning, release-execution) |

**Each layer contains stations, each with its own machine.** The application
layer has jess, relay, gale — each with its own agents, CI, gates. The
verification layer has rivet, spar, witness, ordeal — each with its own.
The toolchain layer has meld, loom, synth, kiln, sigil — each with its own.
Each station produces, verifies, ships.

**The layers stack.** Application depends on verification. Verification
depends on toolchain. The toolchain is the foundation — meld fuses, loom
optimizes, synth compiles, kiln runs, sigil signs. The verification layer
traces, architects, covers, solves. The application layer flies, integrates,
ships.

**Each layer is built by agents.** The agents don't just write code — they
build the tools, verify the output, ship the releases. The machine is the
agents, the CI, the gates. The orchestrator oversees all three layers.

## The control tower: the to-be-OSSed dashboard

The patterns in this series are not just theory. They are implemented in a
**control tower** — a dashboard that shows the whole factory. We are
planning to open-source it. The pattern is not specific to our stack. Any
CI system can expose the same data.

{% <mermaid> %}
flowchart TB
    subgraph ct["Control Tower (dashboard)"]
        direction TB
        overview["Overview<br/>all repos · all gates<br/>green / red / pending"]
        ask["Ask<br/>when will this PR run?<br/>ETA from measured waits"]
        queue["Queue<br/>runner pool · waiting jobs<br/>hardware availability"]
        critical["Critical path<br/>longest chain of<br/>dependent gates"]
        resources["Resources<br/>who needs what<br/>RAM · disk · runners · boards"]
        outages["Outages<br/>GitHub status<br/>fleet health"]
        friction["Friction<br/>tool errors · workarounds<br/>build decisions"]
    end

    subgraph patterns["Patterns from this series"]
        direction TB
        p1["Blog 1: gates, bottlenecks"]
        p2["Blog 2: estimation, critical path"]
        p3["Blog 3: orchestrator, resources"]
    end

    overview --> p1
    ask --> p2
    critical --> p2
    queue --> p3
    resources --> p3
    outages --> p3
    friction --> p3

    style overview fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style ask fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style queue fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style critical fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style resources fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style outages fill:#1a1d27,stroke:#f87171,color:#e1e4ed
    style friction fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed
    style p1 fill:#13161f,stroke:#8b90a0,color:#8b90a0
    style p2 fill:#13161f,stroke:#8b90a0,color:#8b90a0
    style p3 fill:#13161f,stroke:#8b90a0,color:#8b90a0

    classDef ct fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef tool fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
    classDef warn fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef danger fill:#1a1d27,stroke:#f87171,color:#e1e4ed;
    classDef info fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed;
    classDef pattern fill:#13161f,stroke:#8b90a0,color:#8b90a0;
{% </mermaid> %}

**The control tower features:**

| Feature | What it shows | Pattern from |
|---|---|---|
| **Overview** | All repos, all gates, green/red/pending | Blog 1: gates, bottlenecks |
| **Ask** | "When will this PR run?" — ETA from measured waits | Blog 2: estimation |
| **Queue** | Runner pool, waiting jobs, hardware availability | Blog 3: resource constraints |
| **Critical path** | Longest chain of dependent gates | Blog 2: critical path |
| **Resources** | Who needs what (RAM, disk, runners, boards) | Blog 3: resource allocation |
| **Outages** | GitHub status, fleet health | Blog 3: GitHub outages |
| **Friction** | Tool errors, workarounds, build decisions | Blog 3: building your own tools |

**The orchestrator's cockpit.** The control tower is what the orchestrator
looks at. Not to do the work — to **see** the work. To see the gates, the
queue, the critical path, the resources. To decide: who gets what, what
goes first, what waits.

**To be OSSed.** The control tower is currently internal. We are building
the open-source version as [**warte**](https://github.com/pulseengine/warte)
(German: "watchtower" — and "bitte warte auf mich", "please wait for me").
The repo is public, with issues in order: migrate from the existing
internal dashboard, build the overview, add the ask feature, add the
queue view, add the critical path, add resource allocation, add outage
detection, add friction reporting, build the API, prepare for OSS release.
The pattern — a CI control tower with an ask feature and an API — is not
specific to our stack. Any CI system can expose the same data.

**warte is a tool like the others.** It sits at the same level as meld,
loom, synth, kiln, sigil — in the toolchain layer. It is not a dashboard
on top of the factory. It is a tool in the factory. The skills tell the
agents how to use it: when to ask for an ETA, when to check the queue,
when to look at the critical path. And warte itself is built by agents
using the skills — the same pattern, applied to itself.

## The principle

> **Who does what is more important than how fast.**

The factory is not a hierarchy. It is a set of roles, each with a clear job,
connected by contracts. The bottlenecks move — hardware, CI, decisions,
cross-repo dependencies. The roles don't.

jess integrates. relay flies. gale provides the kernel. Everyone knows
their role. The bottlenecks are managed, not eliminated.

## What we would tell you to take from this

**Name the roles.** The names define the responsibilities. "Integrator"
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
chain, **one orchestrator** — the one who owns the factory and makes every
decision the oracles cannot. It has not been tested in a larger organisation
with more layers, more roles, and more complex dependencies. The claim is
not "this is the only way to structure a factory" but "the roles are clear,
and the bottlenecks are managed."

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

[^anthropic-scion]: Anthropic, *Redesigning source control at Anthropic*, October 2026. [anthropic.com/research/redesigning-source-control](https://www.anthropic.com/research/redesigning-source-control). Primary (company research publication). The article describes building Scion, an in-house version control system, after git became a bottleneck at 30,000 merges/day and 600 PB of daily git traffic. Key quote: "Claude's ability to write code was both what put us in this situation in the first place and how we were able to quickly build a high-quality, scalable system to deal with it."

[^thinking-hats]: Edward de Bono, *Six Thinking Hats*, 1985. [Wikipedia](https://en.wikipedia.org/wiki/Six_Thinking_Hats). Primary (encyclopedia summary of the original framework). The six hats: White (facts), Red (emotions), Black (negative/evaluation), Yellow (positive), Green (new ideas), Blue (big picture/managing). Hat sequences for common activities are listed in the Wikipedia article.

---

*This is the last post in the arc. The series: [SAFe was built for slow humans](/blog/safe-was-built-for-slow-humans/) → [Can we deliver X by January?](/blog/can-we-deliver-x-by-january/) → [The orchestrator: who does what](/blog/the-orchestrator-who-does-what/).*

---

*This post is part of [PulseEngine](/) — a formally verified WebAssembly
Component Model engine for safety-critical systems. Prior posts in the arc:
[SAFe was built for slow humans](/blog/safe-was-built-for-slow-humans/),
[Can we deliver X by January?](/blog/can-we-deliver-x-by-january/),
[The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/).*
