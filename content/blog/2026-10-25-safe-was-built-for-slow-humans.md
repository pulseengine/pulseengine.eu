+++
title = "SAFe was built for slow humans. My factory needs Kanban with gates."
description = "The bottleneck in an AI-agent factory is not generation — it is verification and decisions. This holds whether agents produce code, requirements, architecture, or tests. SAFe optimises for slow human cycles. What an agent-driven line needs is flow with gates, WIP limits on the decision queue, and machine-readable contracts between stations."
date = 2026-10-25
draft = true
[taxonomies]
tags = ["process", "ai-agents", "kanban", "verification", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
SAFe was designed to coordinate large organisations of people who think and
deliver in months. An AI-agent factory delivers in hours. The bottleneck is
not *what* the agents produce — code, requirements, architecture, tests — but
*who verifies it and who decides*. Make everything code and the bottleneck
does not move: it is still the human gate. What replaces SAFe is not "less
process" but a different process: Kanban for the flow, gates for the checks,
machine-readable contracts between stations, and a translation layer to the
corporation that must not be called SAFe — because the name is the trap.
{% </insight> %}

I have spent ten years inside SAFe organisations. PI Planning events where the
same three stakeholders attended and forty others were represented by a proxy.
Retrospectives that named the same three impediments for six quarters running.
None of it was stupid — it was coordination overhead calibrated for teams that
ship in sprints. What it was not calibrated for is a line where agents produce
reviewed, gated changes in hours and the queue that grows is the one waiting for
a human decision.

[The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/)
measured what that looks like in our own repositories. This post is the argument
for what replaces the process that measured it.

## The bottleneck is not the artifact

{% <mermaid> %}
flowchart TB
    subgraph artifacts["Agent-produced artifacts (all 'code')"]
        direction LR
        r["Requirements<br/>(rivet artifacts)"]
        a["Architecture<br/>(AADL/SysML)"]
        c["Code<br/>(Rust/Wasm)"]
        t["Tests<br/>(executable checks)"]
    end
    subgraph bottleneck["The real bottleneck"]
        direction TB
        d["Decide<br/>(what is correct?)"]
        v["Verify<br/>(does the gate fail?)"]
        s["Sign<br/>(human accountability)"]
    end
    artifacts --> bottleneck
    style r fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style a fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style c fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style t fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style d fill:#1a1d27,stroke:#f87171,color:#e1e4ed
    style v fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style s fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed

    classDef auto fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
    classDef gate fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef human fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef slow fill:#1a1d27,stroke:#f87171,color:#e1e4ed;
{% </mermaid> %}

In a team of humans, the bottleneck is writing the code. When agents write the
code, the bottleneck moves downstream: to decisions, verification, and
integration. But here is the deeper point: **make everything code and the
bottleneck does not move.** Requirements as rivet artifacts. Architecture as
AADL models. Tests as executable checks. Agents can produce all of it — and
the constraint is still the same: who decides what "correct" means, who
verifies the output, who signs.

This is what Osmani means by "Generation is a wide mouth; verification is the
narrow neck."[^osmani-factories] The artifact is not the bottleneck. The gate
is. The queue that matters is no longer "what are we building this sprint" but
"what are we deciding this week."

The metrics change with it: not velocity and burndown, but **decision latency**,
**gate potency**, and the ratio of **agent-closed to human-decided** items.

## What the research says

The shift is measured, and the measurements converge from three directions:

| Source | Finding |
|---|---|
| **Faros AI 2026** (22k devs, 4k teams) | +33.7% tasks, +66.2% epics — but **+441% review time**, +54% bugs, +242.7% incidents[^faros-2026] |
| **Harvard** (Chen & Stratton, 718 firms) | +30% code, +20% commits — **zero** additional shipped software[^harvard-2026] |
| **METR RCT** (16 experienced devs) | **19% slower** with AI while believing 20% faster[^metr-2025] |
| **DORA 2025** | "AI doesn't fix a team; it amplifies what's already there"[^dora-2025] |
| **Stripe, OpenAI, Cursor, mabl** | Independently converged on: sandboxed environments, triggers, fleet orchestration, governance, human gates[^ona-summit] |

Faros calls it "the Acceleration Whiplash: real throughput gains at the top,
compounding quality costs at every stage below." The Harvard study's summary:
"AI coding agents are not productivity multipliers — they are throughput
redistributors."

{% <note kind="tip"> %}
**The test is simple.** If your process has a ceremony that exists to
coordinate people writing code, and your agents write the code, the ceremony
is now overhead. If your process has a gate that catches defects, and your
agents pass through it, the gate is now load-bearing. Keep the gates.
Question the ceremonies.
{% </note> %}

## Why Scrum and SAFe do not fit

Two operating models, side by side. The arrow shows what happens when agents
arrive: the SAFe process is **replaced by** Kanban with gates, because agents
compress weeks of human work into hours.

{% <mermaid> %}
flowchart LR
    subgraph safe["SAFe / Scrum (before agents)"]
        direction TB
        s1["PI Planning<br/>(quarterly alignment)"] --> s2["Sprints<br/>(2-week boxes)"] --> s3["Ceremonies<br/>(standup, retro, review)"] --> s4["Ship"]
        style s1 fill:#1a1d27,stroke:#f87171,color:#e1e4ed
        style s2 fill:#1a1d27,stroke:#f87171,color:#e1e4ed
        style s3 fill:#1a1d27,stroke:#f87171,color:#e1e4ed
        style s4 fill:#1a1d27,stroke:#f87171,color:#e1e4ed
    end

    subgraph kanban["Kanban with gates (after agents)"]
        direction TB
        k1["Continuous intake"] --> k2{"Oracle exists?"}
        k2 -->|yes| k3["Agents fix<br/>(uncapped)"]
        k2 -->|no| k4["Decision queue<br/>(WIP-limited)"]
        k4 --> k3
        k3 --> k5["Gates<br/>(proven to fail)"] --> k6["Release<br/>(human sign-off)"]
        style k1 fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
        style k2 fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
        style k3 fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
        style k4 fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
        style k5 fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
        style k6 fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    end

    safe ==>|"agents arrive:<br/>weeks → hours"| kanban

    classDef auto fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
    classDef gate fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef human fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef slow fill:#1a1d27,stroke:#f87171,color:#e1e4ed;
    classDef neutral fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed;
{% </mermaid> %}

Scrum enforces artificial cycles. Work in an agent-driven line is event-driven:
a customer meeting produces a transcript, an agent run produces a finding, a
gate fires and produces a decision request. Forcing that into two-week boxes
means either waiting for the box to open or padding the work to fill it.

The practitioners who built Scrum and the Agile Manifesto say so themselves.
Ron Jeffries, XP co-creator: "SAFe gives some lip service to [continuous
delivery] but its training and focus push toward synchronizing, not continuous
delivery"[^jeffries]. Ten Agile Manifesto co-authors: they "all advise against
adopting SAFe"[^safe-delusion]. CMU SEI measured the overhead: developers
average 10.3 direct hours per week; "limiting time spent in meetings can be
worth a 15–25% productivity boost"[^sei-meetings].

doubleSlash puts the mismatch directly: "AI coding agents deliver features in
hours instead of weeks. If code is ready at any time — why do we still plan in
two-week sprints?"[^doubleslash]. Even Scrum.org published an "AI Augmented
Scrum Framework" conceding that bot tasks "should be measured by... the human
validation time required"[^scrum-org-ai] — an admission that story points stop
proxying for effort once agents write the code.

| SAFe element | What it optimises for | What an agent factory needs |
|---|---|---|
| PI Planning | Alignment across teams in a quarter | Event-driven intake, continuous triage |
| Sprints | Predictable delivery of committed scope | Flow of decisions and gated artifacts |
| ART syncs | Cross-team coordination | Machine-readable contracts between stations |
| WSJF | Economic prioritisation of features | Oracle-gated triage: can a machine check this? |
| Portfolio kanban | Visibility of epics across portfolios | WIP limits on the decision queue |

## What fits: Kanban with gates

Kanban was built for flow, not for cycles. Four principles, each with a direct
analogue in the line:

| Kanban principle | In the agent factory |
|---|---|
| Visualise the flow | Agent runs, reviews, gates, decision queue — all on one board |
| Limit WIP | Not "how many agents can run" but "how many decisions can wait" |
| Manage flow | The bottleneck is the verification queue, not the generation queue |
| Improve continuously | Process metrics: files per change, fix share, decision latency |

The WIP limit is the part that matters most. In [The machine arrived before
the factory](/blog/the-machine-arrived-before-the-factory/) we split the
backlog on the oracle axis: issues whose fix a mechanical check can confirm go
to the agents without a cap, and only issues that need a scope, architecture
or priority decision count against a ratchet.

Yuval Yeret puts it precisely: "WIP limits should still mainly reflect human
capacity and attention… Human attention for steering, review, integration, and
deciding what matters is usually more scarce than agent runtime"[^yeret-wip].
BusinessMap adds the missing piece: "WIP limits controlled the number of active
tasks — not the number of pending decisions. Cards could sit neatly within our
WIP boundaries yet remain frozen because no one had moved the decision
forward"[^businessmap-decisions].

For metrics, the Flow Framework (Kersten, *Project to Product*, 2018) gives
five: Flow Time, Flow Velocity, Flow Efficiency, Flow Load, Flow Distribution[^kersten-flow].
Flow Efficiency — active time divided by total flow time — is the headline
number. LinearB reports teams typically measure 15–25%: "75–85% of the time,
work items are simply waiting"[^linearb-flow]. In an agent factory, that
waiting is almost always at the human gate.

The gates are the other half. A Kanban board without gates is a conveyor belt
that moves defects as fast as features. The Toyota Production System has names
for this: **jidoka** (the andon cord — a machine stops itself when it detects a
defect) and **poka-yoke** (error-proofing — design the mistake out of the
agent's reach)[^remojansen-tps]. One practitioner's operationalization: a
"verification-debt budget" where 0 means the agent proceeds freely, 3 means it
must verify before further actions, and 5 means it is stopped completely.

## Answering the customer: can we deliver X by January?

The gate model answers "where are we" — but customers ask "when will it be
done." SAFe answers with story points and sprint velocity, which is a guess
dressed as a plan. The factory answers with **two measurements**: gate status
for the present, and **flow history** for the future.

{% <mermaid> %}
flowchart TB
    subgraph present["Where are we? (measurement)"]
        direction TB
        g1["Gate 1: Requirements<br/>rivet validate"]
        g2["Gate 2: Architecture<br/>spar solver"]
        g3["Gate 3: Code + tests<br/>CI"]
        g4["Gate 4: Coverage<br/>witness MC/DC"]
        g5["Gate 5: Proof<br/>Verus/Kani"]
        g6["Gate 6: Hardware<br/>Renode + silicon"]
        g7["Gate 7: Sign-off<br/>human"]
        style g1 fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
        style g2 fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
        style g3 fill:#1a1d27,stroke:#f87171,color:#e1e4ed
        style g4 fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
        style g5 fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
        style g6 fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
        style g7 fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    end

    subgraph future["When will it be done? (estimation from corpus)"]
        direction TB
        h1["Past project A<br/>12 gates, 8 weeks<br/>1.5 gates/week"]
        h2["Past project B<br/>8 gates, 12 weeks<br/>0.67 gates/week"]
        h3["Past project C<br/>15 gates, 6 weeks<br/>2.5 gates/week"]
        h4["X matches B's profile:<br/>8 gates, 3 need decisions<br/>→ 4 weeks mechanical<br/>→ 8 weeks decision-dependent"]
        style h1 fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
        style h2 fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
        style h3 fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
        style h4 fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    end

    present -->|"gate status"| answer["Answer:<br/>June–July 2027 (80% confidence)<br/>September 2027 (95% confidence)"]
    future -->|"flow history"| answer
    style answer fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed

    classDef green fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
    classDef red fill:#1a1d27,stroke:#f87171,color:#e1e4ed;
    classDef neutral fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed;
    classDef human fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef estimate fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
{% </mermaid> %}

### The corpus: every past project is a data point

To estimate X, you need history. Every project you've shipped with gates,
deadlines, and requirements is a reference:

| Project | Gates | Weeks | Flow velocity | Gate types | Similarity to X |
|---|---|---|---|---|---|
| rivet v0.9 | 12 | 8 | 1.5/week | mostly mechanical | high (same toolchain) |
| relay flight stack | 8 | 12 | 0.67/week | 5 mechanical, 3 decision | **matches X** |
| spar v0.9.x | 15 | 6 | 2.5/week | mostly mechanical | high (same team) |
| gale kernel | 6 | 10 | 0.6/week | 2 mechanical, 4 proof | low (formal proofs) |

X has 8 gates: 5 mechanical (CI, tests, coverage), 3 decision-dependent
(safety argument, hardware access, sign-off). That matches relay's profile:
8 gates, 12 weeks, 0.67 gates/week. The mechanical gates took 4 weeks; the
decision gates took 8 weeks because hardware access was late.

### Reference class forecasting, not estimation from scratch

Don't estimate X from zero. **Find the similar past project and use its
actuals.** This is reference class forecasting (Flyvbjerg, *Reference Class
Forecasting in Planning and Forecasting*, 2021)[^flyvbjerg] — the same method
used for railways, bridges, and IT projects that consistently overrun.

> "X matches relay's profile. Relay took 12 weeks: 4 for mechanical gates,
> 8 waiting on decisions. If your hardware access is sorted by March, we're
> looking at June–July 2027. If not, add 8 weeks."

### Monte Carlo, not a single date

Give confidence intervals, not false precision:

> "Based on 12 similar projects, the mechanical gates take 8–16 weeks
> (80% confidence). The decision gates take 4–12 weeks depending on your
> team. So: **June 2027 with 80% confidence, September 2027 with 95%
> confidence.** The variance is in the decisions, not the code."

This is honest because:
- You're using **real data** from your corpus
- You're giving **ranges**, not false precision
- You're separating **mechanical gates** (predictable) from **decision gates**
  (unpredictable)

### What you need to collect

To make this work, track per project:

| Field | Why |
|---|---|
| Gate ID + type (mechanical / decision / sign-off) | Separate predictable from unpredictable |
| Date gate entered queue | Flow Time start |
| Date gate passed | Flow Time end |
| Blocker reason (if red > 1 week) | Learn what slows you down |
| Similarity tags (toolchain, hardware, team) | Match future projects to past ones |

This is **Flow Time** from the Flow Framework — the metric that predicts
delivery, not velocity[^kersten-flow].

### The customer conversation

> "We don't guess. We measure. X has 8 gates. Two are green, one is red
> (the proof — we need a decision from your team on the safety argument),
> five haven't started. Based on 12 similar projects in our corpus, the
> mechanical gates take 8–16 weeks. The decision gates depend on you.
> If those land by March, we deliver June–July 2027 with 80% confidence.
> Here's the dashboard showing every gate's status, and here's the
> historical data behind the estimate."

### Why this beats SAFe estimation

| SAFe | Gate + flow model |
|---|---|
| Story points (guessed) | Gate count (measured) |
| Sprint velocity (throughput) | Flow velocity (gates/week from corpus) |
| PI commitment (fixed scope, fixed date) | Confidence interval (range, with assumptions) |
| "We'll try" | "Here's the data, here's the risk, here's what we need from you" |

{% <note kind="warning"> %}
**Story points are the wrong unit for the question being asked.** In SAFe,
teams had to calibrate story points — make them synchronous across teams so
a "5" meant the same thing everywhere. That calibration is busywork: it
measures *complexity*, not *time*. But the customer never asks "how complex
is it?" They ask "when is it ready?" Story points answer a question nobody
asked, and the calibration to make them comparable across teams makes them
even less useful for the question that matters.
{% </note> %}

### The key insight

Software is unknown. **Your factory is not.** The factory has a measurable
throughput. The gates are the units. The corpus is the history. You're not
estimating software — you're estimating **how fast your factory passes
gates**, and that's a measurement, not a guess.

## The work model that makes it real

{% <mermaid> %}
flowchart TB
    subgraph model["Division of labour"]
        direction TB
        orch["<b>Orchestrator</b><br/>Architecture, agent orchestration,<br/>verification, fast iteration<br/><i>Leverage: designing gates,<br/>deciding what oracles cannot</i>"]
        coll["<b>Colleague</b><br/>Hardware setup,<br/>bench configuration<br/><i>Leverage: keeps the<br/>orchestrator unblocked</i>"]
        team["<b>Team</b><br/>Productionisation, final OS/hardware<br/>tests, the nitty-gritty<br/><i>Leverage: closes gaps that<br/>need physical access</i>"]
    end
    orch -->|"delegates what blocks"| coll
    orch -->|"hands off what multiplies"| team
    coll -.->|"unblocks"| orch
    team -.->|"productionises"| orch

    style orch fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style coll fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style team fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
{% </mermaid> %}

A process on paper does not run a line. What runs it is a division of labour
that matches where each role's leverage is. The pattern: **give away the work
that blocks you, keep the work that multiplies you.**

Osmani defines the orchestrator role: "You're orchestrating AI agents — while
you act as architect, reviewer, and decision-maker… You own the codebase"[^osmani-agentic].
O'Reilly Radar traces the arc: "from coder to conductor and ultimately
orchestrator… Our jobs are shifting from 'How do I code this?' to 'How do I get
the right code built?'"[^oreilly-orchestrator]. Herrmann & Schmidt frame
delegation as "management by objectives" replacing "step-by-step task
prescription"[^herrmann-delegation]. Karpathy's "autonomy slider" captures the
same idea: "we will move the autonomy slider from left to right over time" —
the human sets how far right the slider sits per task[^karpathy-software3].

This is "dark production, lit release" in practice. The production floor runs
without a person. The release, the decisions, the signature — those stay lit.

## Scaling beyond one station

{% <mermaid> %}
flowchart TB
    subgraph layers["Coordination layers"]
        direction TB
        l1["<b>Kanban</b> (station)<br/>Board, WIP limits, gates"]
        l2["<b>Interface contracts</b><br/>AADL, API specs, SLOs, traceability — as code"]
        l3["<b>Integration cadence</b><br/>Weekly merge, KPIs generated automatically"]
        l4["<b>Dependency management</b><br/>Shared board, visible blockers"]
        l5["<b>Factory control tower</b><br/>Machine-readable metrics over all teams"]
    end
    l1 --> l2 --> l3 --> l4 --> l5

    style l1 fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style l2 fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style l3 fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style l4 fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed
    style l5 fill:#1a1d27,stroke:#c084fc,color:#e1e4ed
{% </mermaid> %}

Kanban alone does not scale to a large organisation. Between stations you need
**contracts, not meetings**. The Bezos API Mandate (2002) is the canonical
example: "Teams must communicate with each other through these interfaces.
There will be no other form of interprocess communication allowed"[^bezos-mandate].
Team Topologies formalizes this as **X-as-a-service**: "one team provides a
service to another team with an API and service level expectations"[^team-topologies].

In automotive and aerospace — the domains closest to a hardware-software
factory — the pattern is industry standard. AUTOSAR's main deliverable is
specifications: the layered architecture decouples application software from
hardware, so teams integrate against the **RTE contract**, not against each
other[^autosar]. ISO 26262 formalizes the **Hardware-Software Interface (HSI)**
as the safety contract between HW and SW teams[^iso26262-hsi]. COVESA's
Vehicle Signal Specification is "a common language independent of the protocol
or serialisation format"[^covesa-vss].

This is SAFe's idea without SAFe's bureaucracy. SAFe says "coordinate through
ceremonies." The factory says "coordinate through artifacts and cadence."

## The translation layer — and why it must not be called SAFe

**"SAFe" is not safe.** The name implies safety — security, reliability,
predictability. What it delivers is coordination overhead. A team that hears
"we are keeping a thin SAFe shell" hears "we are still doing SAFe, just less
of it" — and keeps doing the ceremonies. The name launders the framework.

So do not call it SAFe. Call it a **portfolio translation layer**, a
**governance interface**, a **corporate compatibility layer**. Produce the
artifacts the corporation expects — programme board, PI objectives, epic
breakdowns — from your machine-readable data, on demand. Keep the names where
they match. But the framework name stays out. When someone asks "are you
doing SAFe?", the answer is "no — we produce the artifacts your portfolio
tooling reads, from the same data our gates already generate."

Three things the translation layer does:

- **Translation.** Portfolio management speaks in programme increments; you
  translate. The artifacts are a translation layer, not a process.
- **Traceability.** ASPICE and ISO 26262 want a structured trail. That comes
  from rivet artifacts and git history without a single SAFe ceremony. This is
  the real safety — the kind the name "SAFe" promises but does not deliver.
- **Synchronisation.** A thin sync — one short meeting per week — keeps teams
  from drifting apart. That is a Scrum shell, not a Scrum process.

The model is: **Kanban inside, translation outside, and the boundary between
them is a layer you control — named for what it does, not for what it
pretends to be.**

## What we would tell you to take from this

**The bottleneck is not the artifact. Your process still is.** Whether agents
produce code, requirements, architecture, or tests — the constraint is
verification and decisions. If your process optimises for producing artifacts,
you are managing the wrong queue. Measure where the wait is. Put the WIP
limit there.

**Kanban is the operating model, gates are the safety system.** A board without
gates moves defects. Gates without a board have no flow. You need both, and the
gates need to be proven to fail — not just present.

**Delegate what blocks you, keep what multiplies you.** The orchestrator's
leverage is in designing gates and verifying output. Hardware setup, final
production tests, the nitty-gritty that needs physical access — hand those to
the roles whose leverage starts where yours ends.

**Do not call the translation layer SAFe.** The name implies safety; the
framework delivers coordination overhead. A "thin SAFe shell" invites people
to keep doing SAFe. Call it a portfolio translation layer, a governance
interface, a corporate compatibility layer.

**Scale through contracts, not ceremonies.** Between stations, the contract is
the interface: AADL, API specs, traceability links, as code. The cadence is the
integration rhythm. The control tower is the metrics layer. None of it needs a
meeting to exist.

## Limits

This is one person's operating model, developed in a specific context: a
safety-critical embedded software organisation, building verification tooling,
with agents that produce gated, reviewed changes. It has not been tested in a
large corporation with hundreds of engineers, regulatory auditors, and a
portfolio layer that genuinely needs PI Planning to function.

The metrics I cite — decision latency, gate potency, agent-closed vs
human-decided ratio — are the ones I track. They are not industry-standard
metrics, and I have not benchmarked them against a SAFe organisation running
the same workload. The comparison is theoretical, grounded in the shape of the
work, not in a controlled experiment.

The "portfolio translation layer" is a design, not a tested implementation.
And the naming discipline — refusing to call it SAFe — is a communication
choice I have not yet tested at scale. It may confuse more than it clarifies.

## Sources and caveats

The argument is grounded in the author's own operating practice and in the
measurements from [The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/).
The research section draws on industry telemetry, controlled studies, and
practitioner accounts; each is cited with its tier below.

**Caveats on the evidence.** Faros AI's telemetry is correlation across its own
customers, not a controlled study. The Harvard working paper is not yet
peer-reviewed. METR's RCT is the most rigorous single study cited, but its
sample is 16 experienced open-source developers. DORA's findings are
survey-based self-report. The practitioner accounts are blogs, not peer-reviewed
research. The company figures (Stripe, OpenAI, Cursor, mabl) are self-reported.
The SAFe critiques from Agile Manifesto signatories are curated collections of
quotes, not systematic reviews.

The Kanban principles are from Anderson, *Kanban: Successful Evolutionary
Change for Your Technology Business*, 2010 (quoted from memory). The Flow
Framework metrics are from Kersten, *Project to Product* (2018); the Flow
Efficiency baselines are from DeGrandis, *Making Work Visible* (2012), as
reported by LinearB.

The metrics "gate potency," "decision latency," and "agent-closed vs
human-decided ratio" are the author's own terms, coined for this post. A search
on 25 October 2026 found no prior use in the public literature.

*Footnotes render at the bottom of the page, grouped by category.*

[^faros-2026]: Faros AI, *AI Engineering Report 2026* (22,000 developers, 4,000 teams). Vendor research; correlation across Faros customers, not a controlled study. [faros.ai](https://www.faros.ai/blog/lab-vs-reality-ai-productivity-study-findings). Secondary (vendor telemetry).

[^faros-2025]: Faros AI, *The AI Productivity Paradox Report 2025* (10,000+ developers, 1,255 teams). Vendor research. [faros.ai](https://www.faros.ai/blog/key-takeaways-from-the-dora-report-2025). Secondary (vendor telemetry).

[^harvard-2026]: Mark Chen and Alex Stratton, *Artificial Intelligence in the Firm: Bottlenecks in Software Production*, Harvard working paper, August 2026. ~300M work events across 718 firms. Primary (working paper, not yet peer-reviewed). [fion.ac/jellyfish.pdf](https://fion.ac/jellyfish.pdf). Coverage: [Ars Technica](https://arstechnica.com/ai/2026/10/ai-coding-agents-generate-more-code-but-not-more-software/).

[^metr-2025]: Joel Becker, Nate Rush, Beth Barnes, David Rein (METR), *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity*, arXiv:2507.09089, July 2025. Primary (RCT, 16 developers, 246 tasks). [arxiv.org/abs/2507.09089](https://arxiv.org/abs/2507.09089). METR's Feb 2026 update [metr.org](https://metr.org/blog/2026-02-24-uplift-update/) revises the methodology; the 19% figure is restated, not withdrawn.

[^dora-2025]: Google Cloud and DORA, *State of AI-assisted Software Development 2025*. Primary (survey-based). [dora.dev](https://dora.dev/dora-report-2025/).


[^osmani-factories]: Addy Osmani, *Software Factories, Light and Dark*, 20 July 2026. [addyosmani.com](https://addyosmani.com/blog/software-factories/). Primary (practitioner essay).

[^osmani-agentic]: Addy Osmani, *Agentic Engineering*. [addyosmani.com](https://addyosmani.com/blog/agentic-engineering/). Primary (practitioner essay).

[^oreilly-orchestrator]: O'Reilly Radar, *Conductors to Orchestrators: The Future of Agentic Coding*. [oreilly.com](https://www.oreilly.com/radar/conductors-to-orchestrators-the-future-of-agentic-coding/). Secondary (interview/essay).

[^herrmann-delegation]: Werner Herrmann and Maximilian Schmidt, *Delegation Interaction: A Paradigm Shift in Human-AI Collaboration*, AutomationXP 2026. [matthiasbaldauf.com](https://matthiasbaldauf.com/automationxp26/papers/AutomationXP26_paper_8866.pdf). Primary (workshop paper).

[^karpathy-software3]: Andrej Karpathy, *Software Is Changing (Again)*, YC Startup Library, February 2026. Primary (talk transcript). [ycombinator.com](https://www.ycombinator.com/library/MW-andrej-karpathy-software-is-changing-again).

[^stripe-minions]: Stripe, *Minions: Stripe's one-shot end-to-end coding agents* (part 2). [stripe.dev](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2). Primary (engineering blog, self-reported figures).

[^openai-harness]: OpenAI, *Harness Engineering: Leveraging Codex in an Agent-First World*. [openai.com](https://openai.com/index/harness-engineering/). Primary (engineering blog, self-reported figures).

[^ona-summit]: Ona, *Background Agents Summit* recap (Stripe, Uber, Monzo, Cloudflare, Harvey, AWS, Genentech). [ona.com](https://ona.com/stories/background-agents-summit). Secondary (event recap).


[^jeffries]: Ron Jeffries, *Issues with SAFe*. [ronjeffries.com](https://ronjeffries.com/xprog/articles/issues-with-safe/). Primary (practitioner critique, XP co-creator).

[^safe-delusion]: SAFe Delusion, *A Collection of Comments from Leading Experts* (10 Agile Manifesto co-authors, 74 sources). [safedelusion.com](https://safedelusion.com/). Secondary (curated collection).

[^doubleslash]: doubleSlash, *Sprints in the AI Age: Why AI Coding Agents Break the Two-Week Cycle*. [blog.doubleslash.de](https://blog.doubleslash.de/en/software-technologien/devops/sprints-in-the-ai-age-ai-coding-agents/). Primary (practitioner blog).

[^sei-meetings]: Bill Nichols, CMU Software Engineering Institute, *Stop Wasting Time: Manage Time as the Limiting Resource* (study of 111 teams). [sei.cmu.edu](https://www.sei.cmu.edu/blog/stop-wasting-time-manage-time-as-the-limiting-resource/). Primary (research blog).

[^scrum-org-ai]: Scrum.org, *AI Augmented Scrum Framework: When Half Your Team is Autonomous Agents*, 2026. [scrum.org](https://www.scrum.org/resources/blog/ai-augmented-scrum-framework-when-half-your-team-autonomous-agents). Primary (framework vendor publication).


[^yeret-wip]: Yuval Yeret, *Calculate Kanban WIP Limits in the AI Age* and *Limiting Work-in-Progress (WIP) in Scrum with Kanban*. [yuvalyeret.com](https://yuvalyeret.com/blog/calculate-kanban-wip-limits-ai-age/). Primary (practitioner blog).

[^businessmap-decisions]: BusinessMap/ProofHub, *Using Kanban for Better Decision Making*. [businessmap.io](https://businessmap.io/blog/using-kanban-for-better-decision). Secondary (vendor blog, cites CHAOS Report).

[^kersten-flow]: Mik Kersten, *Project to Product: How to Survive and Thrive in the Age of Digital Disruption with the Flow Framework*, IT Revolution, 2018. Primary (book). Flow Framework: [flowframework.org](https://flowframework.org/).

[^flyvbjerg]: Bent Flyvbjerg, *Reference Class Forecasting in Planning and Forecasting*, 2021. Primary (book). The method: estimate from the actuals of similar past projects, not from a bottom-up estimate of the current project.

[^linearb-flow]: LinearB, *5 Key Flow Metrics*. [linearb.io](https://linearb.io/blog/5-key-flow-metrics). Secondary (vendor blog, cites DeGrandis).

[^remojansen-tps]: remojansen, *Revisiting the Toyota Production System (TPS) in the Age of Coding Agents*. [dev.to](https://dev.to/remojansen/revisiting-the-toyota-production-system-tps-in-the-age-of-coding-agents-2bb5). Primary (practitioner blog).


[^bezos-mandate]: Jeff Bezos, *API Mandate*, Amazon, 2002. Widely circulated; original memo not publicly released. [nordicapis.com](https://nordicapis.com/the-bezos-api-mandate-amazons-manifesto-for-externalization/). Secondary (reconstruction from multiple accounts).

[^team-topologies]: Matthew Skelton and Manuel Pais, *Team Topologies: Organizing Business and Technology Teams for Fast Flow*, 2019. Primary (book). [teamtopologies.com](https://teamtopologies.com/key-concepts).

[^autosar]: AUTOSAR, *Adaptive Platform ARACom API* and Classic Platform specifications. [autosar.org](https://www.autosar.org/). Primary (standards body).

[^iso26262-hsi]: ISO 26262, *Road vehicles — Functional safety*, Hardware-Software Interface (HSI) specification. Standard text paywalled; description from public summaries. Secondary for the HSI concept.

[^covesa-vss]: COVESA, *Vehicle Signal Specification (VSS)*. [covesa.github.io](https://covesa.github.io/vehicle_signal_specification/). Primary (open standard).

---

*This post is part of [PulseEngine](/) — a formally verified WebAssembly
Component Model engine for safety-critical systems. Prior posts in the arc:
[The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/),
[Agents don't tidy up](/blog/agents-dont-tidy-up/),
[AI in the product, not AI in the toolchain](/blog/ai-in-the-product-not-the-toolchain/).*
