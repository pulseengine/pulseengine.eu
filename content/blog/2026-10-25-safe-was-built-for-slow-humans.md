+++
title = "SAFe was built for slow humans. My factory needs Kanban with gates."
description = "The bottleneck in an AI-agent factory is not generation — it is verification and decisions. This holds whether agents produce code, requirements, architecture, or tests. SAFe optimises for slow human cycles. What an agent-driven line needs is flow with gates, WIP limits on the decision queue, and machine-readable contracts between stations."
date = 2026-10-25
draft = false
[taxonomies]
tags = ["process", "ai-agents", "kanban", "verification", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**SAFe was designed in 2011, before coding agents existed, for people who
think and deliver in months. An AI-agent factory delivers in hours.**

Whatever the agents produce, whether code, requirements, architecture or
tests, the bottleneck is *who verifies it and who decides*. Making everything
code leaves it at the human gate.

What replaces SAFe is a different process rather than "less process": Kanban
for the flow, gates for the checks, machine-readable contracts between
stations, and a translation layer to the corporation. That layer must not be
called SAFe, because the name is the trap.
{% </insight> %}

I have spent ten years inside SAFe organisations[^safe-history], with PI Planning
events where the same three stakeholders attended and forty others were
represented by a proxy, and retrospectives that named the same three
impediments for six quarters running. That coordination overhead was
calibrated, sensibly, for teams that ship in sprints. It fits badly on a line
where agents produce reviewed, gated changes in hours and the queue that grows
is the one waiting for a human decision.

[The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/)
measured what that looks like in our own repositories. This post argues for
what should replace that process.

## The bottleneck is not the artifact

{% <mermaid> %}
flowchart TB
    subgraph artifacts["Agent-produced artifacts (all 'code')"]
        direction LR
        r["Requirements<br/>(machine-readable requirements)"]
        a["Architecture<br/>(architecture models)"]
        c["Code<br/>(Rust/Wasm)"]
        t["Tests<br/>(executable checks)"]
    end
    subgraph bottleneck["The real bottleneck (human time)"]
        direction TB
        h["Comprehend<br/>(understand the concept)"]
        d["Decide<br/>(what is correct?)"]
        v["Verify<br/>(does the gate fail?)"]
        s["Sign-off<br/>(human accountability)"]
        h --> d --> v --> s
    end
    artifacts --> bottleneck
    style r fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style a fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style c fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style t fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style h fill:#1a1d27,stroke:#f87171,color:#e1e4ed
    style d fill:#1a1d27,stroke:#f87171,color:#e1e4ed
    style v fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style s fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed

    classDef auto fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
    classDef gate fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef human fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef slow fill:#1a1d27,stroke:#f87171,color:#e1e4ed;
{% </mermaid> %}

In a team of humans, the bottleneck is writing the code. When agents write the
code, the bottleneck moves downstream to comprehension, decisions,
verification and integration. **Making everything code does not move it any
further.** Requirements become machine-readable artifacts, architecture becomes
machine-readable models, tests become executable checks, and agents can produce
all of it. A human still needs time to *comprehend* the concept, *decide* what
"correct" means, *verify* the output, and *sign*, and comprehending
requirements, architecture or tests is as slow for a human as comprehending
code.

**Any step in the process can be the constraint, including steps no human
touches.** Hardware availability is a common one: a flight stack cannot
pass its hardware gate until a board is free. The fix is simulation first:
run the gate in Renode, check the logic, then confirm on silicon when the
board is available. The CI queue is another: 69 jobs waiting on one runner
pool is a bottleneck even if every human is free. The network, dependencies
and external services become bottlenecks whenever they limit throughput.

This is the Theory of Constraints: **the bottleneck is whatever limits the
throughput of the entire system, and it moves as you improve other steps.**
Fix the human decision queue, and hardware becomes the bottleneck. Add
simulation, and real hardware becomes the bottleneck. Add more runners, and
the CI queue moves. The factory is a chain whose throughput is set by the
weakest link, and that link changes.

Osmani puts it as "Generation is a wide mouth; verification is the
narrow neck."[^osmani-factories] The gate is the bottleneck, and the queue that
matters has changed from "what are we building this sprint" to
"what are we deciding this week." The metrics change with it, from velocity and
burndown to **decision latency**, **gate potency**, and the ratio of
**agent-closed to human-decided** items.

## What the research says

The shift is measured, and the measurements converge from three directions:

| Source | Finding |
|---|---|
| **Faros AI 2026** (22k devs, 4k teams) | +33.7% tasks, +66% epics, but **+441.5% review time**, +54% bugs, and incidents per pull request up 242.7%[^faros-2026] |
| **Harvard** (Chen & Stratton, 718 firms) | +30% lines of code, +20% commits, and **no statistically significant increase** in shipped software (an increase above 12% is ruled out)[^harvard-2026] |
| **METR RCT** (16 experienced devs) | **19% slower** with AI while believing 20% faster[^metr-2025] |
| **DORA 2025** | "AI's primary role is as an amplifier, magnifying an organization's existing strengths and weaknesses"[^dora-2025] |
| **Background Agents Summit** (Stripe, Uber, Monzo, Cloudflare and others) | Converged on sandboxed environments, context connectivity, triggers, fleet orchestration and governance[^ona-summit] |

Faros calls the pattern "the Acceleration Whiplash". The Harvard paper finds
the same shape: more code and more commits without a measurable increase in
shipped software.

{% <note kind="tip"> %}
**The test is simple.** If your process has a ceremony that exists to
coordinate people writing code, and your agents write the code, the ceremony
is now overhead. If your process has a gate that catches defects, and your
agents pass through it, the gate is now load-bearing. Keep the gates.
Question the ceremonies.
{% </note> %}

## Why Scrum and SAFe do not fit

The diagram puts the two operating models side by side. When agents arrive,
Kanban with gates **replaces** the SAFe process, because agents compress weeks
of human work into hours.

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
        k1["Continuous intake"] --> k2{"Oracle exists?<br/>(can a machine check?)"}
        k2 -->|yes| k3["Agents fix<br/>(uncapped)"]
        k2 -->|no| k4["Decision queue<br/>(WIP-limited)"]
        k4 --> k3
        k3 --> k5["Gates<br/>(proven to fail)"] --> k6["Ship<br/>(human sign-off)"]
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
delivery] … but its training and focus push toward synchronizing, not continuous
delivery"[^jeffries]. Eight Agile Manifesto signatories are among the critics
collected at safedelusion.com[^safe-delusion]. CMU SEI measured the overhead: developers
average 10.3 direct hours per week; "limiting time spent in meetings can be
worth a 15–25% productivity boost"[^sei-meetings].

doubleSlash puts the mismatch directly: "AI coding agents deliver features in
hours instead of weeks. If code is ready at any time — why do we still plan in
two-week sprints?"[^doubleslash]. A community post on Scrum.org, "AI Augmented
Scrum Framework", argues that bot tasks "should be measured by... the human
validation time required"[^scrum-org-ai], which concedes that story points stop
proxying for effort once agents write the code.

| SAFe element | What it optimises for | What an agent factory needs |
|---|---|---|
| PI Planning | Alignment across teams in a quarter | Event-driven intake, continuous triage |
| Sprints | Predictable delivery of committed scope | Flow of decisions and gated artifacts |
| ART syncs | Cross-team coordination | Machine-readable contracts between stations |
| WSJF | Economic prioritisation of features | Oracle-gated triage: can a machine check this? |
| Portfolio kanban | Visibility of epics across portfolios | WIP limits on the decision queue |

An **oracle** is a mechanical check that can confirm or deny correctness —
a test that fails when the code is wrong, a proof that fails when the
property doesn't hold, a coverage check that fails when the code is
untested. The oracle axis splits work into two classes: what an oracle
can verify (agents handle it, uncapped) and what needs a human decision
(the decision queue, WIP-limited).

## What fits: Kanban with gates

Kanban was built for flow. Four of the five core practices in David
Anderson's method have a direct analogue in the line:

| Kanban practice | In the agent factory |
|---|---|
| Visualise the flow | Agent runs, reviews, gates, decision queue — all on one board |
| Limit WIP | Not "how many agents can run" but "how many decisions can wait" |
| Manage flow | The bottleneck is the verification queue, not the generation queue |
| Improve collaboratively | Process metrics: files per change, fix share, decision latency |

The WIP limit is the part that matters most. In [The machine arrived before
the factory](/blog/the-machine-arrived-before-the-factory/) we split the
backlog on the oracle axis: issues whose fix a mechanical check can confirm go
to the agents without a cap, and only issues that need a scope, architecture
or priority decision count against a **ratchet**: a WIP limit that only
counts issues needing human decisions, and can only tighten, never loosen.
The ratchet is merged but not yet armed on a schedule, and floors are
recorded for three of five repositories.

Yuval Yeret puts it precisely: "Human attention for steering, review,
integration, and deciding what matters is usually more scarce than agent
runtime." And further on: "WIP limits should still mainly reflect human
capacity and attention"[^yeret-wip].
BusinessMap adds the missing piece: "WIP limits controlled the number of active
tasks — not the number of pending decisions. Cards could sit neatly within our
WIP boundaries yet remain frozen because no one had moved the decision
forward"[^businessmap-decisions].

For metrics, the Flow Framework (Kersten, *Project to Product*, 2018) gives
five: Flow Time, Flow Velocity, Flow Efficiency, Flow Load, Flow Distribution[^kersten-flow].
Flow Efficiency, active time divided by total flow time, is the headline
number. LinearB reports teams typically measure 15–25%: "75–85% of the time,
work items are simply waiting"[^linearb-flow]. In an agent factory, that
waiting is almost always at the human gate.

The gates are the other half. A Kanban board without gates is a conveyor belt
that moves defects as fast as features. The Toyota Production System has names
for this: **jidoka** (the andon cord: a machine stops itself when it detects a
defect) and **poka-yoke** (error-proofing: design the mistake out of the
agent's reach)[^remojansen-tps]. One practitioner's operationalization: a
"verification-debt budget" where 0 means the agent proceeds freely, 3 means it
must verify before further actions, and 5 means it is stopped completely.

## The CI gate: a dashboard as oracle

A gate is only useful if you can see it. A CI dashboard is the control tower
for the CI gate: every required check, every repo and every branch in one
view. The overview shows the status of every CI gate across the fleet, which
repos are green or red and which checks are pending, so status needs no
meeting and no email.

The ask feature turns the dashboard into an oracle. You ask "when will this
PR run?" and get an answer from measured data (an edited sample; the job and
pool names are real, the PR number is illustrative):

```
When will it run?
repo: rivet    PR: 511    [ask]

running on runner1: CI · Mutation Testing (rivet-core 00-of-64) for 5m
queued: 69 job(s) of CI on lean-mem, waiting 5m

Estimated from measured waits: how long jobs in the same pool actually
waited before starting over the last 3 hours. Not from queue position,
because GitHub does not start jobs in creation order.
```

The answer uses **measured data**, the same reference-class method as the
next post. There is an API behind it: `GET /api/eta?repo=rivet&pr=511` returns JSON
with status, running jobs, queued jobs, and scan age. This is one of several
metrics we now work on:

| Metric | What it measures | Source |
|---|---|---|
| CI gate status | green / red / pending per repo | Dashboard overview |
| CI gate ETA | when will this PR run? | Ask feature + API |
| CI gate duration | how long did CI take? | API |
| Release velocity | releases per week | GitHub releases |
| Decision queue | issues waiting for human decisions | Issue tracker |
| Flow efficiency | active time / total time | Flow Framework |

The CI gate is the most mechanical gate in the factory. It runs on every
commit, its ability to fail is proven in spar and not yet in rivet, and the
dashboard makes its status visible without a meeting.

*We are considering open-sourcing this dashboard. A CI control tower with an
ask feature and an API is not specific to our stack, and any CI system can
expose the same data.*

## Scaling beyond one station

{% <mermaid> %}
flowchart TB
    subgraph layers["Coordination mechanisms"]
        direction TB
        l1["<b>Kanban</b> (station)<br/>Board, WIP limits, gates"]
        l2["<b>Interface contracts</b><br/>Architecture models, API specs, SLOs, traceability — as code"]
        l3["<b>Integration cadence</b><br/>Weekly merge, KPIs generated automatically"]
        l4["<b>Dependency management</b><br/>Shared board, visible blockers"]
        l5["<b>Cross-factory metrics layer</b><br/>Machine-readable metrics over all teams"]
    end
    l1 --> l2 --> l3 --> l4 --> l5

    style l1 fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
    style l2 fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style l3 fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style l4 fill:#1a1d27,stroke:#22d3ee,color:#e1e4ed
    style l5 fill:#1a1d27,stroke:#c084fc,color:#e1e4ed
{% </mermaid> %}

Kanban alone does not scale to a large organisation. Between **stations**,
the self-contained units with their own board, WIP limits and gates, you
need **contracts instead of meetings**. The Bezos API Mandate (2002) is the canonical
example: "Teams must communicate with each other through these interfaces.
There will be no other form of interprocess communication allowed"[^bezos-mandate].
Team Topologies formalizes this as **X-as-a-service**, where "one team provides
and one team consumes something 'as a Service'"[^team-topologies].

In automotive and aerospace, the domains closest to a hardware-software
factory, the pattern is industry standard. AUTOSAR's main deliverable is
specifications: the layered architecture decouples application software from
hardware, so teams integrate against the **RTE contract**, not against each
other[^autosar]. ISO 26262 formalizes the **Hardware-Software Interface (HSI)**
as the safety contract between HW and SW teams[^iso26262-hsi]. COVESA's
Vehicle Signal Specification describes vehicle data independently of the
protocol that carries it[^covesa-vss].

This is SAFe's idea without SAFe's bureaucracy. SAFe says "coordinate through
ceremonies." The factory says "coordinate through artifacts and cadence."

## The translation layer — and why it must not be called SAFe

**"SAFe" is not safe.** The name implies safety: security, reliability,
predictability. What the framework delivers is coordination overhead. A team
that hears "we are keeping a thin SAFe shell" hears "we are still doing SAFe, just less
of it", and keeps doing the ceremonies.

Call it a **portfolio translation layer**, a **governance interface** or a
**corporate compatibility layer** instead. Produce the artifacts the
corporation expects (programme board, PI objectives, epic breakdowns) from
your machine-readable data, on demand. Keep the artifact names where they
match and leave the framework name out. When someone asks "are you
doing SAFe?", the answer is "no — we produce the artifacts your portfolio
tooling reads, from the same data our gates already generate."

The model is **Kanban inside, translation outside, and a boundary layer you
control, named for what it does.** The translation layer does three things:

- **Translation.** Portfolio management speaks in programme increments, and
  the layer translates into them without becoming a process of its own.
- **Traceability.** ASPICE and ISO 26262 want a structured trail. That comes
  from requirements artifacts and git history without a single SAFe ceremony,
  and it is the safety that the name "SAFe" promises and does not deliver.
- **Synchronisation.** A thin sync of one short meeting per week keeps teams
  from drifting apart: a Scrum shell, without the Scrum process.

## The vocabulary is the process

The translation layer handles the outside. Inside, the vocabulary has to
change as well. The trap is *"same as SAFe, but with X
done here."* A team that hears this keeps the SAFe process, ceremonies and
vocabulary, adds agents to one step, and ends up with SAFe plus extra steps
and a bottleneck that has not moved.

The words you use shape the process you do. "Sprint" implies a fixed time
box. "Story point" implies complexity, not time. "PI Planning" implies
quarterly alignment theater. Keep the words and you keep the process, and
with it the bottleneck.

| Old vocabulary (SAFe) | New vocabulary (factory) | Why |
|---|---|---|
| Sprint | Flow | Work is event-driven, not time-boxed |
| Story point | Gate | A gate is a check that can fail; a point is a guess |
| PI Planning | Continuous triage | Intake is continuous; triage splits on the oracle axis |
| Velocity | Flow velocity | Gates per week, measured from history |
| Epic / Feature | Work item with gates | Decomposed into gates, not estimated in points |
| Release train | Integration cadence | Weekly merge to an integration stand, not a train |
| ART sync | Contract check | Machine-readable contracts, not a meeting |
| Coder | Orchestrator | Designs gates, verifies output, decides what oracles cannot |
| Product owner | Decision owner | Owns the decision queue, not the backlog |
| Story | Gate-passing work item | Work that passes gates, not work that fits in a sprint |

The table describes a **change of process**, and a change of process needs
three people:

| Role | What they do | Why they're needed |
|---|---|---|
| **Process person** | Designs the new flow, the gates, the WIP limits | Someone who understands process change — not just tools, but how work moves |
| **Quality owner** | Designs the oracles, proves the gates can fail | Someone who understands verification — the gates are the safety system |
| **User of the vocabulary** | Uses the new words daily, corrects the old ones | Someone who speaks the new language — if nobody uses it, it's dead |

Without all three, the vocabulary change fails. The process person designs a
flow nobody follows. The quality person designs gates nobody trusts. The
user speaks words nobody understands. The old vocabulary creeps back in with
"just this once, for the sprint review", and the process creeps back with it.

The translation layer serves the corporation outside and the vocabulary change
serves the team inside. The team needs both, and only the inside change moves
the bottleneck.

## What we would tell you to take from this

**Your process is the bottleneck when it optimises for artifacts.** Whether
agents produce code, requirements, architecture or tests, the constraint is
verification and decisions. If your process optimises for producing artifacts,
you are managing the wrong queue. Measure where the wait is and put the WIP
limit there.

**Kanban is the operating model, gates are the safety system.** A board without
gates moves defects, and gates without a board have no flow. You need both,
and each gate must be proven able to fail.

**Delegate what blocks you, keep what multiplies you.** The orchestrator's
leverage is in designing gates and verifying output. Hand hardware setup,
final production tests and the rest of the work that needs physical access to
the roles whose leverage starts where yours ends.

**Do not call the translation layer SAFe.** The name implies safety and the
framework delivers coordination overhead, so a "thin SAFe shell" invites people
to keep doing SAFe. Call it a portfolio translation layer, a governance
interface, a corporate compatibility layer.

**Scale through contracts instead of ceremonies.** Between stations, the
contract is the interface (architecture models, API specs, traceability links,
as code), the cadence is the integration rhythm, and the control tower is the
metrics layer.

---

*Next in the arc: [Can we deliver X by January?](/blog/can-we-deliver-x-by-january/)
Estimation from gates and flow history, for when the bottleneck is
verification.*

## Limits

This is one person's operating model, developed in a specific context: a
safety-critical embedded software organisation, building verification tooling,
with agents that produce gated, reviewed changes. It has not been tested in a
large corporation with hundreds of engineers, regulatory auditors, and a
portfolio layer that genuinely needs PI Planning to function.

The metrics I cite (decision latency, gate potency, agent-closed vs
human-decided ratio) are the ones I track. They are not industry-standard
metrics, and I have not benchmarked them against a SAFe organisation running
the same workload. The comparison is theoretical: it rests on the shape of the
work, and no controlled experiment backs it.

The "portfolio translation layer" is an untested design. The naming discipline
of refusing to call it SAFe is a communication choice I have not yet tested at
scale, and it may confuse more than it clarifies.

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

The Kanban practices are from Anderson, *Kanban: Successful Evolutionary
Change for Your Technology Business*, 2010, which lists five core practices;
four are used here. The Flow Framework metrics are from Kersten, *Project to
Product* (2018); the Flow Efficiency range is LinearB's.

"Decision latency" is an established management term. "Gate potency" is
PulseEngine's own term, introduced with the `gate-potency` skill in August
2026, and "agent-closed vs human-decided ratio" is the author's. Their
application to an agent factory is ours.


[^faros-2026]: Faros AI, *AI Engineering Report 2026* (22,000 developers, 4,000 teams). Vendor research; correlation across Faros customers, not a controlled study. [faros.ai](https://www.faros.ai/blog/ai-acceleration-whiplash-takeaways). Secondary (vendor telemetry).


[^harvard-2026]: Fiona Chen and James Stratton, *Artificial Intelligence in the Firm: Bottlenecks in Software Production*, Harvard working paper, August 2026. ~300M work events across 718 firms. Primary (working paper, not yet peer-reviewed). [fion.ac/jellyfish.pdf](https://fion.ac/jellyfish.pdf). Coverage: [Ars Technica](https://arstechnica.com/ai/2026/10/ai-coding-agents-generate-more-code-but-not-more-software/).

[^metr-2025]: Joel Becker, Nate Rush, Beth Barnes, David Rein (METR), *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity*, arXiv:2507.09089, July 2025. Primary (RCT, 16 developers, 246 tasks). [arxiv.org/abs/2507.09089](https://arxiv.org/abs/2507.09089). METR's Feb 2026 update [metr.org](https://metr.org/blog/2026-02-24-uplift-update/) revises the methodology; the 19% figure is restated, not withdrawn.

[^dora-2025]: Google Cloud and DORA, *State of AI-assisted Software Development 2025*. Primary (survey-based). [dora.dev](https://dora.dev/dora-report-2025/).


[^osmani-factories]: Addy Osmani, *Software Factories, Light and Dark*, 20 July 2026. [addyosmani.com](https://addyosmani.com/blog/software-factories/). Primary (practitioner essay).







[^ona-summit]: Ona, *Background Agents Summit* recap (Stripe, Uber, Monzo, Cloudflare, Harvey, AWS, Genentech). [ona.com](https://ona.com/stories/background-agents-summit). Secondary (event recap).


[^jeffries]: Ron Jeffries, *Issues with SAFe*. [ronjeffries.com](https://ronjeffries.com/xprog/articles/issues-with-safe/). Primary (practitioner critique, XP co-creator).

[^safe-history]: Dean Leffingwell, *Scaling Software Agility: Best Practices for Large Enterprises*, Addison-Wesley, 2007 (first formal description); SAFe 1.0 released 2011; SAFe 6.0 released March 2023. [Wikipedia](https://en.wikipedia.org/wiki/Scaled_agile_framework). Secondary (encyclopedia). The framework was designed in 2011, before coding agents existed, for organisations where humans wrote code in months.

[^safe-delusion]: SAFe Delusion, *A Collection of Comments from Leading Experts* (8 Agile Manifesto signatories among 74 cited sources). [safedelusion.com](https://safedelusion.com/). Secondary (curated collection).

[^doubleslash]: doubleSlash, *Sprints in the AI Age: Why AI Coding Agents Break the Two-Week Cycle*. [blog.doubleslash.de](https://blog.doubleslash.de/en/software-technologien/devops/sprints-in-the-ai-age-ai-coding-agents/). Primary (practitioner blog).

[^sei-meetings]: Bill Nichols, CMU Software Engineering Institute, *Stop Wasting Time: Manage Time as the Limiting Resource* (study of 111 teams). [sei.cmu.edu](https://www.sei.cmu.edu/blog/stop-wasting-time-manage-time-as-the-limiting-resource/). Primary (research blog).

[^scrum-org-ai]: Sanjay Saini, *AI Augmented Scrum Framework: When Half Your Team is Autonomous Agents*, community post on Scrum.org, 2026. [scrum.org](https://www.scrum.org/resources/blog/ai-augmented-scrum-framework-when-half-your-team-autonomous-agents). Secondary (community post).


[^yeret-wip]: Yuval Yeret, *Calculate Kanban WIP Limits in the AI Age* and *Limiting Work-in-Progress (WIP) in Scrum with Kanban*. [yuvalyeret.com](https://yuvalyeret.com/blog/calculate-kanban-wip-limits-ai-age/). Primary (practitioner blog).

[^businessmap-decisions]: BusinessMap/ProofHub, *Using Kanban for Better Decision Making*. [businessmap.io](https://businessmap.io/blog/using-kanban-for-better-decision). Secondary (vendor blog, cites CHAOS Report).

[^kersten-flow]: Mik Kersten, *Project to Product: How to Survive and Thrive in the Age of Digital Disruption with the Flow Framework*, IT Revolution, 2018. Primary (book).


[^linearb-flow]: LinearB, *5 Key Flow Metrics*. [linearb.io](https://linearb.io/blog/5-key-flow-metrics). Secondary (vendor blog, cites DeGrandis).

[^remojansen-tps]: remojansen, *Revisiting the Toyota Production System (TPS) in the Age of Coding Agents*. [dev.to](https://dev.to/remojansen/revisiting-the-toyota-production-system-tps-in-the-age-of-coding-agents-2bb5). Primary (practitioner blog).


[^bezos-mandate]: Jeff Bezos, *API Mandate*, Amazon, 2002. Widely circulated; original memo not publicly released. [nordicapis.com](https://nordicapis.com/the-bezos-api-mandate-amazons-manifesto-for-externalization/). Secondary (reconstruction from multiple accounts).

[^team-topologies]: Matthew Skelton and Manuel Pais, *Team Topologies: Organizing Business and Technology Teams for Fast Flow*, 2019. Primary (book). [teamtopologies.com](https://teamtopologies.com/key-concepts).

[^autosar]: AUTOSAR, *Adaptive Platform ARACom API* and Classic Platform specifications. [autosar.org](https://www.autosar.org/). Primary (standards body).

[^iso26262-hsi]: ISO 26262, *Road vehicles — Functional safety*, Hardware-Software Interface (HSI) specification. Standard text paywalled; description from public summaries. Secondary for the HSI concept.

[^covesa-vss]: COVESA, *Vehicle Signal Specification (VSS)*. [covesa.github.io](https://covesa.github.io/vehicle_signal_specification/). Primary (open standard).


*Corrected on 27 October 2026: the Harvard authors' names and findings, the DORA, Team Topologies, COVESA and Yeret quotes, the Faros figures and link, the Background Agents Summit participants, the safedelusion.com count, the Kanban practices, the ratchet's status, the CI gate's proven potency, and the claim that "gate potency" and "decision latency" were coined here.*

---

*This post is part of [PulseEngine](/) — a WebAssembly Component Model engine
for safety-critical systems, with machine-checked proofs for parts of it
(work in progress). Recent posts:
[The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/),
[Agents don't tidy up](/blog/agents-dont-tidy-up/),
[AI in the product, not AI in the toolchain](/blog/ai-in-the-product-not-the-toolchain/).*
