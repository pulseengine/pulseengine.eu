+++
title = "SAFe was built for slow humans. My factory needs Kanban with gates."
description = "The bottleneck in an AI-agent factory is not code production — it is decisions, verification, and integration. SAFe optimises for slow human cycles: PI Planning, sprints, ceremonies. What an agent-driven line needs is flow with gates, WIP limits on the decision queue, and machine-readable contracts between stations. This is the operating model that replaced Scrum where I work, and why."
date = 2026-10-25
draft = true
[taxonomies]
tags = ["process", "ai-agents", "kanban", "verification", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
SAFe was designed to coordinate large organisations of people who think and
deliver in months. An AI-agent factory delivers in hours, and its bottleneck is
no longer writing code — it is deciding, verifying, and integrating. The
framework that optimises for sprint ceremonies and PI Planning adds friction
exactly where the flow needs to be fastest. What replaces it is not "less
process" but a different process: Kanban for the flow, gates for the checks,
machine-readable contracts between stations, and a thin SAFe shell only where
the corporation outside demands it.
{% end %}

I have spent the last ten years inside SAFe organisations. PI Planning events
where the same three stakeholders attended and forty others were represented by
a proxy. Big Room Planning sessions that produced a wall of sticky notes and a
programme board nobody looked at again until the next one. Retrospectives that
named the same three impediments for six quarters running. None of it was
stupid — it was coordination overhead calibrated for teams that ship in
sprints. What it was not calibrated for is a line where agents produce reviewed,
gated changes in hours and the queue that grows is the one waiting for a human
decision.

[The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/)
measured what that looks like in our own repositories: coupling fell, the fix
share rose, the backlog grew because discovery outruns decision-making. The
post named the answer — Kanban with gates — without saying what it replaces
and why. This post is that argument.

## The bottleneck moved

In a team of humans, the bottleneck is usually writing the code. Sprints,
standups and story points exist to keep that bottleneck supplied and visible.
When agents write the code, the bottleneck moves downstream: to requirements
clarification, to review, to verification, to the decision of whether this
change is the right change. The queue that matters is no longer "what are we
building this sprint" but "what are we deciding this week."

This is not a small shift. It changes what the process is for. A sprint
process optimises for predictable delivery of a committed scope. A flow process
optimises for throughput of decisions and the artifacts that enable them. The
metrics change with it: not velocity and burndown, but decision latency, gate
potency, and the ratio of agent-closed to human-decided items.

{% note(kind="tip") %}
**The test is simple.** If your process has a ceremony that exists to
coordinate people writing code, and your agents write the code, the ceremony
is now overhead. If your process has a gate that exists to catch a defect
before it ships, and your agents pass through it, the gate is now load-bearing.
Keep the gates. Question the ceremonies.
{% end %}

## Why Scrum and SAFe do not fit

Scrum enforces artificial cycles. Sprint planning, review, retro — all on a
fixed time window. Work in an agent-driven line is event-driven: a customer
meeting produces a transcript, an agent run produces a finding, a gate fires
and produces a decision request. Forcing that into two-week boxes means either
waiting for the box to open or padding the work to fill it. Neither is flow.

SAFe adds layers on top of Scrum: PI Planning, ART syncs, portfolio kanban,
architectural runway, WSJF prioritisation. Each layer exists to coordinate
more people across more time. In an agent factory the coordination problem is
different: not "how do 200 people align on a plan" but "how do 5 stations pass
work to each other without a meeting." SAFe's answer to that is a meeting.
The factory's answer is a contract.

| SAFe element | What it optimises for | What an agent factory needs |
|---|---|---|
| PI Planning | Alignment across teams in a quarter | Event-driven intake, continuous triage |
| Sprints | Predictable delivery of committed scope | Flow of decisions and gated artifacts |
| ART syncs | Cross-team coordination | Machine-readable contracts between stations |
| WSJF | Economic prioritisation of features | Oracle-gated triage: can a machine check this? |
| Portfolio kanban | Visibility of epics across portfolios | WIP limits on the decision queue |
| Architectural runway | Pre-building infrastructure for future work | Gates that fail, built before they are needed |

The last row is the one SAFe gets closest to and still misses. "Architectural
runway" is the idea of building the factory before the machine arrives. But
SAFe builds it as a plan with owners and dates, reviewed at the next PI
Planning. The factory needs it as a gate that fails when the precondition is
absent — which is what [the previous post](/blog/the-machine-arrived-before-the-factory/)
called "gates whose failure has been measured."

## What fits: Kanban with gates

Kanban is the operating model that matches an agent factory, because it was
built for flow, not for cycles. Four principles, each with a direct analogue
in the line:

| Kanban principle | In the agent factory |
|---|---|
| Visualise the flow | Agent runs, reviews, gates, decision queue — all on one board |
| Limit WIP | Not "how many agents can run" but "how many decisions can wait" |
| Manage flow | The bottleneck is the decision queue, not the code queue |
| Improve continuously | Process metrics: files per change, fix share, decision latency |

The WIP limit is the part that matters most. In [The machine arrived before
the factory](/blog/the-machine-arrived-before-the-factory/) we split the
backlog on the oracle axis: issues whose fix a mechanical check can confirm go
to the agents without a cap, and only issues that need a scope, architecture
or priority decision count against a ratchet. That split is Kanban's WIP limit
applied to the right queue. Discovery is the most valuable thing the agents do
and should never be throttled. The queue that needs a limit is the one waiting
for a human.

The gates are the other half. A Kanban board without gates is a conveyor belt
that moves defects as fast as features. Every station transition is a gate:
can this artifact be checked mechanically? Does the check fail when it should?
The `gate-potency` discipline from the previous post — proving that a gate can
fail, not just that it runs — is what separifies a factory from a workshop with
a kanban board painted on the wall.

## The work model that makes it real

A process on paper does not run a line. What runs it is a division of labour
that matches where each role's leverage is. The model I use:

| Role | Responsibility | Why |
|---|---|---|
| Orchestrator (me) | Architecture, agent orchestration, verification, fast iteration | This is where the leverage is: designing the gates, reviewing the output, deciding what the oracles cannot |
| Colleague | Hardware setup, bench configuration | Hardware setup costs time that belongs to orchestration. Delegating it is not weakness — it is keeping the lever free |
| Team | Productionisation, final OS/hardware tests, the nitty-gritty | The last gaps — final OS, physical hardware access — can only be closed where the hardware is. Handing off three months of prep at that point is not throwing work away; it is handing it to the role whose leverage starts where mine ends |

The pattern is the same in both rows: **give away the work that blocks you,
keep the work that multiplies you.** Hardware setup blocks the orchestrator and
multiplies nobody. Productionisation blocks the team and multiplies the
orchestrator — because every hour the orchestrator spends on hardware is an
hour not spent on gates and verification.

This is what "dark production, lit release" means in practice. The production
floor runs without a person. The release, the decisions, the signature —
those stay lit. And the orchestrator's job is to keep the dark part dark and
the lit part small.

## Scaling beyond one station

Kanban alone does not scale to a large organisation with many stations. It
regulates flow within a station. Between stations you need three more things:

| Layer | What it regulates | Mechanism |
|---|---|---|
| Kanban (station) | Flow within a team | Board, WIP limits, gates |
| Interface contracts | What station A expects from B | AADL models, API specs, traceability links — as code |
| Integration cadence | When stations come together | Weekly merge to an integration stand, KPIs generated automatically |
| Dependency management | Who blocks whom | Shared board, visible blockers, no Excel |
| Factory control tower | Overview across all stations | Machine-readable metrics layer over all teams |

The key insight is **scale-out through contracts, not meetings**. Each station
has a contract: input, output, quality gate, responsible party. Integration
runs on a cadence — weekly, not at the end. Dependencies are visible on a
shared board, not in someone's head. The control tower is machine-readable,
which is where a verification-oriented stack has an advantage: AADL, SysML and
rivet models are contracts as code, and agents can check dependencies against
them mechanically.

This is SAFe's idea without SAFe's bureaucracy. SAFe says "coordinate through
ceremonies." The factory says "coordinate through artifacts and cadence."

## SAFe as interface, not as operating model

None of this means SAFe is worthless. It is the wrong internal operating
model and the right external interface. Three things it still does well:

**Translation to the corporation.** When portfolio management speaks SAFe,
you speak SAFe back. The artifacts — programme board, PI objectives, epic
breakdowns — are a translation layer, not a process. You produce them on
demand, from your machine-readable data, and you do not let them drive your
internal flow.

**Traceability and compliance.** For safety work, ASPICE and ISO 26262 want a
structured trail. That structure can come from rivet artifacts and git history
without a single SAFe ceremony. The compliance officer reads the trail; the
team does not perform a ceremony to produce it.

**Cross-team synchronisation.** A thin sync — one short meeting per week —
keeps teams from drifting apart. That is a Scrum shell, not a Scrum process.
No sprint commitment, no story points, no retro. Just "here is what changed,
here is what you are blocked on."

The model is: **Kanban inside, SAFe outside, and the boundary between them
is a translation layer you control.**

## What this is not

This is not an argument against structure. It is an argument against the wrong
structure. The factory needs:

- **Gates that can fail** — not review meetings that can be skipped
- **One source per fact** — not three dashboards that disagree
- **WIP limits on the decision queue** — not sprint commitments on the code queue
- **Machine-readable contracts** — not slide decks about alignment
- **Process measurement** — not velocity as a target

And it needs people in exactly four places, as [the previous post](/blog/the-machine-arrived-before-the-factory/)
argued: deciding what correct means, deciding what no oracle can, acting on a
process alarm, and the signature. Everything else is a station that should run
dark.

## What we would tell you to take from this

**The bottleneck moved. Your process did not.** If your agents write the code
and your process still optimises for people writing code, you are managing the
wrong queue. Measure where the wait is. Put the WIP limit there.

**Kanban is the operating model, gates are the safety system.** A board without
gates moves defects. Gates without a board have no flow. You need both, and the
gates need to be proven to fail — not just present.

**Delegate what blocks you, keep what multiplies you.** The orchestrator's
leverage is in designing gates and verifying output. Hardware setup, final
production tests, the nitty-gritty that needs physical access — hand those to
the roles whose leverage starts where yours ends. That is not losing control;
it is scaling it.

**SAFe is a translation layer, not a process.** Speak it to the corporation.
Do not run your factory on it. The boundary between your Kanban flow and their
SAFe view is a layer you build, from your machine-readable data, on demand.

**Scale through contracts, not ceremonies.** Between stations, the contract is
the interface: AADL, API specs, traceability links, as code. The cadence is the
integration rhythm. The control tower is the metrics layer. None of it needs a
meeting to exist.

## Limits

This is one person's operating model, developed in a specific context: a
safety-critical embedded software organisation, building verification tooling,
with agents that produce gated, reviewed changes. It has not been tested in a
large corporation with hundreds of engineers, regulatory auditors, and a
portfolio layer that genuinely needs PI Planning to function. The claim is not
"SAFe never works" but "SAFe optimises for a bottleneck that no longer exists
in an agent-driven line, and the replacement is flow with gates."

The metrics I cite — decision latency, gate potency, agent-closed vs
human-decided ratio — are the ones I track. They are not industry-standard
metrics, and I have not benchmarked them against a SAFe organisation running
the same workload. The comparison is theoretical, grounded in the shape of the
work, not in a controlled experiment.

The "thin SAFe shell" is a design, not a tested implementation. I produce
programme-board artifacts from my data when the portfolio asks; I have not
measured whether that satisfies a real SAFe portfolio or just a checkbox.

## Sources and caveats

The argument in this post is grounded in the author's own operating practice
and in the measurements from [The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/).
No external sources were consulted for the SAFe critique; it is a practitioner's
view, not a literature review. The Kanban principles are from the standard
references (Anderson, *Kanban: Successful Evolutionary Change for Your
Technology Business*, 2010) and are quoted from memory — the four principles
listed are the canonical set but the wording is paraphrased.

The claim that "AI-Native SAFe" exists as a marketed variant is based on
vendor marketing pages read in October 2026; the specific features attributed
to it (outcomes, token governance, human-in-the-loop) are from those pages and
were not independently verified against a working implementation.

The work-model table (orchestrator / colleague / team) describes the author's
own delegation pattern. It is presented as a model that works, not as a
recommendation that generalises. The specific split — hardware to a colleague,
production to a team — is context-dependent and would differ in an
organisation without physical hardware constraints.

---

*This post is part of [PulseEngine](/) — a formally verified WebAssembly
Component Model engine for safety-critical systems. Prior posts in the arc:
[The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/),
[Agents don't tidy up](/blog/agents-dont-tidy-up/),
[AI in the product, not AI in the toolchain](/blog/ai-in-the-product-not-the-toolchain/).*
