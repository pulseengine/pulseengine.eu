+++
title = "SAFe was built for slow humans. My factory needs Kanban with gates."
description = "The bottleneck in an AI-agent factory is not code production — it is decisions, verification, and integration. SAFe optimises for slow human cycles: PI Planning, sprints, ceremonies. What an agent-driven line needs is flow with gates, WIP limits on the decision queue, and machine-readable contracts between stations. This is the operating model that replaced Scrum where I work, and why."
date = 2026-10-25
draft = true
[taxonomies]
tags = ["process", "ai-agents", "kanban", "verification", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
SAFe was designed to coordinate large organisations of people who think and
deliver in months. An AI-agent factory delivers in hours, and its bottleneck is
no longer writing code — it is deciding, verifying, and integrating. The
framework that optimises for sprint ceremonies and PI Planning adds friction
exactly where the flow needs to be fastest. What replaces it is not "less
process" but a different process: Kanban for the flow, gates for the checks,
machine-readable contracts between stations, and a translation layer to the
corporation that must not be called SAFe — because the name is the trap.
{% </insight> %}

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

## What the research says

The shift is not my observation alone. It is measured, and the measurements
converge on the same conclusion from three directions: industry telemetry,
controlled studies, and the practitioners running agent fleets in production.

**Industry telemetry shows throughput up, quality down.** Faros AI's 2026
report, covering 22,000 developers across 4,000 teams, found that high AI
adoption brought +33.7% task completion and +66.2% epic completion — but
median PR review time rose **441%**, PRs merged with no review climbed from
31% to 76%, PR size grew 51–72%, bugs per developer rose 54%, and incidents
per PR rose 242.7%[^faros-2026]. Faros calls it "the Acceleration Whiplash:
real throughput gains at the top, compounding quality costs at every stage
below." The 2025 edition, covering 10,000+ developers, found +98% merged PRs
and +21% task completion with +91% review time and +154% PR size — and no
correlation with company-level delivery[^faros-2025].

**Controlled studies show the same shape.** A Harvard working paper (Chen &
Stratton, August 2026) analysed ~300 million work events across 718 firms:
after coding-agent adoption, lines of code rose 30%, commits 20%, PRs 23% —
but there was **no statistically significant increase in resolved Jira issues
or epics**[^harvard-2026]. PR review time rose 49%, requests for changes
nearly doubled, and comments per PR rose 35%. The authors' summary: "AI coding
agents are not productivity multipliers — they are throughput
redistributors." METR's randomised trial is the most careful measurement in
this space: 16 experienced open-source developers took **19% longer** with AI
on real tasks — while expecting a 24% speedup beforehand and still estimating
a 20% speedup after experiencing the slowdown[^metr-2025].

**DORA frames it as amplification, not fix.** Google's DORA 2025 report
concludes: "AI doesn't fix a team; it amplifies what's already there," with
a negative relationship between AI adoption and delivery stability[^dora-2025].
The report's own prescription — "the value of AI will be unlocked by
reimagining the system of work it inhabits" — concedes that the process layer
must change, not just the tooling.

**Practitioners converge on the same operating model.** The teams running
agent fleets in production — Stripe, OpenAI, Cursor, mabl, Cloudflare —
independently landed on the same primitives: sandboxed environments, context
connectivity, triggers, fleet orchestration, and governance[^ona-summit].
Stripe's Minions produce 1,300+ PRs per week with zero human-written code,
every one human-reviewed[^stripe-minions]. OpenAI's harness engineering team
wrote ~1M lines in five months with 3→7 engineers at 3.5 PRs per engineer per
day — "Humans steer. Agents execute"[^openai-harness]. The pattern across all
of them: stages with human gates at specification and merge, not sprints with
story points.

Addy Osmani, who has written the most-cited practitioner account of software
factories, puts the constraint in one line: "Generation is a wide mouth;
verification is the narrow neck"[^osmani-factories]. And on what that means
for process: "Verification, not generation, is the real constraint on a
factory"[^osmani-factories].

{% <note kind="tip"> %}
**The test is simple.** If your process has a ceremony that exists to
coordinate people writing code, and your agents write the code, the ceremony
is now overhead. If your process has a gate that exists to catch a defect
before it ships, and your agents pass through it, the gate is now load-bearing.
Keep the gates. Question the ceremonies.
{% </note> %}

## Why Scrum and SAFe do not fit

Scrum enforces artificial cycles. Sprint planning, review, retro — all on a
fixed time window. Work in an agent-driven line is event-driven: a customer
meeting produces a transcript, an agent run produces a finding, a gate fires
and produces a decision request. Forcing that into two-week boxes means either
waiting for the box to open or padding the work to fill it. Neither is flow.

The practitioners who built Scrum and the Agile Manifesto say so themselves.
Ron Jeffries, co-creator of Extreme Programming, writes: "SAFe gives some lip
service to [continuous delivery] with its 'build on cadence, release on demand'
mantra, but its training and focus push toward synchronizing, not continuous
delivery"[^jeffries]. A curated collection of comments from ten Agile
Manifesto co-authors concludes they "all advise against adopting SAFe"[^safe-delusion]:
Andy Hunt calls it "not an agile approach"; Ken Schwaber says it "does not
adhere to the Agile Manifesto values… as it is highly process-centric."

The mismatch is not theoretical. doubleSlash, a German consultancy, put it
directly: "AI coding agents deliver features in hours instead of weeks. If code
is ready at any time — why do we still plan in two-week sprints?… Technically,
we can deliver at any time. Organizationally, we are often still stuck in
sprints"[^doubleslash]. Their prescription: "a continuously prioritized
backlog instead of sprint planning, WIP limits instead of sprint commitments
and retrospectives that are not tied to a two-week cycle."

SAFe adds layers on top of Scrum: PI Planning, ART syncs, portfolio kanban,
architectural runway, WSJF prioritisation. Each layer exists to coordinate
more people across more time. In an agent factory the coordination problem is
different: not "how do 200 people align on a plan" but "how do 5 stations pass
work to each other without a meeting." SAFe's answer to that is a meeting.
The factory's answer is a contract.

The ceremony overhead is measurable. CMU's Software Engineering Institute
studied 111 teams and found developers averaged just 10.3 direct hours per
week; "limiting time spent in meetings can be worth a 15–25% productivity
boost"[^sei-meetings]. Fixed-cadence ceremony is a tax on the exact resource
— human attention — that gates an agent factory.

Even Scrum.org has conceded the point. In 2026 they published "AI Augmented
Scrum Framework: When Half Your Team is Autonomous Agents," which states that
bot tasks "should be measured by their compute cost, API token utilization,
and, most importantly, the human validation time required"[^scrum-org-ai] —
an admission that story points stop proxying for effort once agents write the
code. And the market has voted: the 17th State of Agile report shows Scrum's
share dropping from 87% in 2022 to 63% in 2024[^state-of-agile].

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

The research backs this up. Yuval Yeret, who writes on Kanban for the AI era,
puts it precisely: "WIP limits should still mainly reflect human capacity and
attention… Human attention for steering, review, integration, and deciding
what matters is usually more scarce than agent runtime"[^yeret-wip]. His
defaults: one actively guided feature per pod; cap specs in flight at 1–2 per
person — "The constraint is not how many the agents can handle. It is how many
finished diffs you can actually read carefully in a day." He names the
phenomenon "acceleration whiplash": when coding is 10x'd, the bottleneck
shifts downstream to review, testing, and validation — "a system-level flow
problem, not a tooling problem."

BusinessMap's research on decision queues adds the missing piece: "WIP limits
controlled the number of active tasks — not the number of pending decisions.
Cards could sit neatly within our WIP boundaries yet remain frozen because no
one had moved the decision forward. The board looked calm, but progress had
quietly stopped"[^businessmap-decisions]. The CHAOS Report data they cite:
roughly one decision per $1,000 of labour cost; decision latency under one
hour correlates with ~58% project success versus ~18% at five hours or more.

For the metrics, the Flow Framework (Dr. Mik Kersten, *Project to Product*,
2018) gives five: Flow Time, Flow Velocity, Flow Efficiency, Flow Load, and
Flow Distribution[^kersten-flow]. Flow Efficiency — active time divided by
total flow time — is the headline number for an agent factory. LinearB reports
teams typically measure 15–25%: "Most engineering teams are shocked to discover
their Flow Efficiency hovers between 15–25%, meaning that 75–85% of the time,
work items are simply waiting"[^linearb-flow]. In an agent factory, that
waiting is almost always at the human gate. Flow Distribution gives the
guardrails: LinearB's balanced distribution is Features 40–50%, Defects
15–25%, Risks 10–15%, Debt 20–25%, with risk indicators at Features >70%,
Defects >30%, or Debt <10%[^linearb-flow].

The gates are the other half. A Kanban board without gates is a conveyor belt
that moves defects as fast as features. Every station transition is a gate:
can this artifact be checked mechanically? Does the check fail when it should?
The `gate-potency` discipline from the previous post — proving that a gate can
fail, not just that it runs — is what separifies a factory from a workshop with
a kanban board painted on the wall. The Toyota Production System has names for
this, older than software: **jidoka** (the andon cord — a machine stops itself
when it detects a defect) and **poka-yoke** (error-proofing — design the
mistake out of the agent's reach)[^remojansen-tps]. One practitioner's
operationalization: a "verification-debt budget" where 0 means the agent
proceeds freely, 3 means it must verify before further actions, and 5 means it
is stopped completely[^remojansen-tps].

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

This is not a new idea; it is the oldest one in the book, restated for agents.
Addy Osmani defines the orchestrator role as: "You're orchestrating AI agents
— coding assistants that can execute, test, and refine code — while you act as
architect, reviewer, and decision-maker… You own the codebase. You maintain
documentation. You use version control and CI. You monitor production. The AI
accelerates the work, but you're responsible for the system"[^osmani-agentic].
O'Reilly Radar traces the arc: "from coder to conductor and ultimately
orchestrator… Our jobs are shifting from 'How do I code this?' to 'How do I get
the right code built?'"[^oreilly-orchestrator]. One practitioner puts the
shift in time terms: "80% of engineer time becomes requirements, architecture
calls, and output validation. It looks more like product management than
software development… The orchestration is the engineering"[^andresmax].

The delegation pattern has academic framing too. Herrmann & Schmidt (AutomationXP
2026) propose "delegation interaction": "AI can actively decide when and how it
executes tasks, but humans are still in the mode of being a responsible
supervisor as is the case with managers who delegate tasks to employees…
Similar to how management principles like 'management by delegation' and
'management by objectives' replaced the step-by-step task prescription
characteristic of Taylorism, we expect a paradigm shift"[^herrmann-delegation].
Andrej Karpathy's "autonomy slider" captures the same idea from the other side:
"we will move the autonomy slider from left to right over time" — the human
sets how far right the slider sits per task[^karpathy-software3].

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

This is not a new idea either. Jeff Bezos's 2002 API Mandate at Amazon is the
canonical edict: "All teams will henceforth expose their data and functionality
through service interfaces. Teams must communicate with each other through these
interfaces. There will be no other form of interprocess communication allowed:
no direct linking, no direct reads of another team's data store, no shared-memory
model, no back-doors whatsoever"[^bezos-mandate]. Coordination happens through
the interface contract; the org chart and the calendar are secondary.

Team Topologies (Skelton & Pais) formalizes this as the **X-as-a-service**
interaction mode: "one team provides a service to another team with an API and
service level expectations," and the design guidance is to "avoid heavyweight
scaled coordination when structure can remove dependencies"[^team-topologies].
Google's SRE practice extends the idea to reliability: error budgets are
machine-readable contracts — "If the service has exceeded its error budget for
the preceding four-week window, we will halt all changes and releases other than
P01 issues or security fixes until the service is back within its SLO"[^google-sre].
The producer/consumer negotiation happens in the SLO document, not in a meeting.

In automotive and aerospace — the domains closest to a hardware-software
factory — the pattern is industry standard. AUTOSAR's stated objective is
"cooperation between different partners," and its main deliverable is
specifications: the layered architecture (application / RTE / basic software)
decouples application software from hardware, so OEM, Tier-1, and software
teams integrate against the **RTE contract**, not against each other[^autosar].
ISO 26262 formalizes the **Hardware-Software Interface (HSI) specification** as
the safety contract between HW and SW teams[^iso26262-hsi]. COVESA's Vehicle
Signal Specification is "a common language independent of the protocol or
serialisation format"[^covesa-vss]. In aerospace, the **digital thread** ties
engineering, manufacturing and maintenance data into one authoritative,
machine-readable fabric[^lockheed-digital-thread].

This is SAFe's idea without SAFe's bureaucracy. SAFe says "coordinate through
ceremonies." The factory says "coordinate through artifacts and cadence."

## The translation layer — and why it must not be called SAFe

None of this means the corporation outside stops existing. Portfolio
management speaks a language, and you need to speak it back. But the name
you give the translation layer matters, because the name is the trap.

**"SAFe" is not safe.** The name implies safety — security, reliability,
predictability. What it delivers is coordination overhead: PI Planning,
ART syncs, programme boards, certification paths. None of those produce
a safer product. A team that hears "we are keeping a thin SAFe shell" hears
"we are still doing SAFe, just less of it" — and keeps doing the ceremonies
that add friction without adding safety. The name launders the framework:
people think they are being safe because the word says so.

So do not call it SAFe. Call it what it is: a **portfolio translation layer**,
a **governance interface**, a **corporate compatibility layer**. Produce the
artifacts the corporation expects — programme board, PI objectives, epic
breakdowns — from your machine-readable data, on demand. Keep the names where
they match: a programme board is a programme board, PI objectives are PI
objectives. But the framework name stays out. When someone asks "are you
doing SAFe?", the answer is "no — we produce the artifacts your portfolio
tooling reads, from the same data our gates already generate."

Three things the translation layer does:

**Translation to the corporation.** When portfolio management speaks in
programme increments and value streams, you translate. The artifacts —
programme board, PI objectives, epic breakdowns — are a translation layer,
not a process. You produce them on demand, from your machine-readable data,
and you do not let them drive your internal flow.

**Traceability and compliance.** For safety work, ASPICE and ISO 26262 want a
structured trail. That structure comes from rivet artifacts and git history
without a single SAFe ceremony. The compliance officer reads the trail; the
team does not perform a ceremony to produce it. This is the real safety —
the kind the name "SAFe" promises but does not deliver.

**Cross-team synchronisation.** A thin sync — one short meeting per week —
keeps teams from drifting apart. That is a Scrum shell, not a Scrum process.
No sprint commitment, no story points, no retro. Just "here is what changed,
here is what you are blocked on."

The model is: **Kanban inside, translation outside, and the boundary between
them is a layer you control — named for what it does, not for what it
pretends to be.**

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

**Do not call the translation layer SAFe.** The name implies safety; the
framework delivers coordination overhead. A "thin SAFe shell" invites people
to keep doing SAFe. Call it a portfolio translation layer, a governance
interface, a corporate compatibility layer — produce the artifacts, keep the
names where they match, but keep the framework name out. When someone asks
"are you doing SAFe?", the answer is "no — we produce the artifacts your
portfolio tooling reads, from the same data our gates already generate."

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

The "portfolio translation layer" is a design, not a tested implementation.
I produce programme-board artifacts from my data when the portfolio asks; I
have not measured whether that satisfies a real SAFe portfolio or just a
checkbox. And the naming discipline — refusing to call it SAFe — is a
communication choice I have not yet tested at scale. It may confuse more
than it clarifies.

## Sources and caveats

The argument in this post is grounded in the author's own operating practice
and in the measurements from [The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/).
The research section draws on industry telemetry, controlled studies, and
practitioner accounts; each is cited with its tier below.

**Caveats on the evidence.** Faros AI's telemetry is correlation across its own
customers, not a controlled study — the company says so itself. The Harvard
working paper (Chen & Stratton) is a working paper, not yet peer-reviewed, and
its "no increase in shipped software" finding is measured over a short window
after adoption. METR's RCT is the most rigorous single study cited, but its
sample is 16 experienced open-source developers on familiar repositories, and
METR itself has revised its methodology since. DORA's findings are survey-based
self-report. The practitioner accounts (Osmani, Yeret, doubleSlash, remojansen)
are blogs, not peer-reviewed research — strong for patterns and quotes, weaker
for generalisation. The company figures (Stripe, OpenAI, Cursor, mabl) are
self-reported and not independently audited. The SAFe critiques from Agile
Manifesto signatories are curated collections of quotes, not systematic
reviews; the underlying sources are linked where available.

The Kanban principles are from the standard references (Anderson, *Kanban:
Successful Evolutionary Change for Your Technology Business*, 2010) and are
quoted from memory — the four principles listed are the canonical set but the
wording is paraphrased. The Flow Framework metrics are from Kersten, *Project
to Product* (2018); the Flow Efficiency baselines are from DeGrandis, *Making
Work Visible* (2012), as reported by LinearB.

The work-model table (orchestrator / colleague / team) describes the author's
own delegation pattern. It is presented as a model that works, not as a
recommendation that generalises. The specific split — hardware to a colleague,
production to a team — is context-dependent and would differ in an
organisation without physical hardware constraints.

The metrics "gate potency," "decision latency," and "agent-closed vs
human-decided ratio" are the author's own terms, coined for this post. The
research found no established public literature using these exact terms; the
closest neighbours are BusinessMap's Kanban "decision latency" and Faros's
"PRs merged with no review." A search on 25 October 2026 found no prior use.

### Industry telemetry and controlled studies

[^faros-2026]: Faros AI, *AI Engineering Report 2026* (22,000 developers, 4,000 teams). Vendor research; correlation across Faros customers, not a controlled study. [faros.ai](https://www.faros.ai/blog/lab-vs-reality-ai-productivity-study-findings). Secondary (vendor telemetry).

[^faros-2025]: Faros AI, *The AI Productivity Paradox Report 2025* (10,000+ developers, 1,255 teams). Vendor research. [faros.ai](https://www.faros.ai/blog/key-takeaways-from-the-dora-report-2025). Secondary (vendor telemetry).

[^harvard-2026]: Mark Chen and Alex Stratton, *Artificial Intelligence in the Firm: Bottlenecks in Software Production*, Harvard working paper, August 2026. ~300M work events across 718 firms. Primary (working paper, not yet peer-reviewed). [fion.ac/jellyfish.pdf](https://fion.ac/jellyfish.pdf). Coverage: [Ars Technica](https://arstechnica.com/ai/2026/10/ai-coding-agents-generate-more-code-but-not-more-software/).

[^metr-2025]: Joel Becker, Nate Rush, Beth Barnes, David Rein (METR), *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity*, arXiv:2507.09089, July 2025. Primary (RCT, 16 developers, 246 tasks). [arxiv.org/abs/2507.09089](https://arxiv.org/abs/2507.09089). METR's Feb 2026 update [metr.org](https://metr.org/blog/2026-02-24-uplift-update/) revises the methodology; the 19% figure is restated, not withdrawn.

[^dora-2025]: Google Cloud and DORA, *State of AI-assisted Software Development 2025*. Primary (survey-based). [dora.dev](https://dora.dev/dora-report-2025/).

### Practitioner accounts and operating models

[^osmani-factories]: Addy Osmani, *Software Factories, Light and Dark*, 20 July 2026. [addyosmani.com](https://addyosmani.com/blog/software-factories/). Primary (practitioner essay).

[^osmani-agentic]: Addy Osmani, *Agentic Engineering*. [addyosmani.com](https://addyosmani.com/blog/agentic-engineering/). Primary (practitioner essay).

[^oreilly-orchestrator]: O'Reilly Radar, *Conductors to Orchestrators: The Future of Agentic Coding*. [oreilly.com](https://www.oreilly.com/radar/conductors-to-orchestrators-the-future-of-agentic-coding/). Secondary (interview/essay).

[^andresmax]: Andres Max, *The AI Orchestrator*. [andresmax.com](https://andresmax.com/the-ai-orchestrator/). Primary (practitioner blog).

[^herrmann-delegation]: Werner Herrmann and Maximilian Schmidt, *Delegation Interaction: A Paradigm Shift in Human-AI Collaboration*, AutomationXP 2026. [matthiasbaldauf.com](https://matthiasbaldauf.com/automationxp26/papers/AutomationXP26_paper_8866.pdf). Primary (workshop paper).

[^karpathy-software3]: Andrej Karpathy, *Software Is Changing (Again)*, YC Startup Library, February 2026. Primary (talk transcript). [ycombinator.com](https://www.ycombinator.com/library/MW-andrej-karpathy-software-is-changing-again).

[^stripe-minions]: Stripe, *Minions: Stripe's one-shot end-to-end coding agents* (part 2). [stripe.dev](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2). Primary (engineering blog, self-reported figures).

[^openai-harness]: OpenAI, *Harness Engineering: Leveraging Codex in an Agent-First World*. [openai.com](https://openai.com/index/harness-engineering/). Primary (engineering blog, self-reported figures).

[^ona-summit]: Ona, *Background Agents Summit* recap (Stripe, Uber, Monzo, Cloudflare, Harvey, AWS, Genentech). [ona.com](https://ona.com/stories/background-agents-summit). Secondary (event recap).

### SAFe and Scrum critiques

[^jeffries]: Ron Jeffries, *Issues with SAFe*. [ronjeffries.com](https://ronjeffries.com/xprog/articles/issues-with-safe/). Primary (practitioner critique, XP co-creator).

[^safe-delusion]: SAFe Delusion, *A Collection of Comments from Leading Experts* (10 Agile Manifesto co-authors, 74 sources). [safedelusion.com](https://safedelusion.com/). Secondary (curated collection).

[^doubleslash]: doubleSlash, *Sprints in the AI Age: Why AI Coding Agents Break the Two-Week Cycle*. [blog.doubleslash.de](https://blog.doubleslash.de/en/software-technologien/devops/sprints-in-the-ai-age-ai-coding-agents/). Primary (practitioner blog).

[^sei-meetings]: Bill Nichols, CMU Software Engineering Institute, *Stop Wasting Time: Manage Time as the Limiting Resource* (study of 111 teams). [sei.cmu.edu](https://www.sei.cmu.edu/blog/stop-wasting-time-manage-time-as-the-limiting-resource/). Primary (research blog).

[^scrum-org-ai]: Scrum.org, *AI Augmented Scrum Framework: When Half Your Team is Autonomous Agents*, 2026. [scrum.org](https://www.scrum.org/resources/blog/ai-augmented-scrum-framework-when-half-your-team-autonomous-agents). Primary (framework vendor publication).

[^state-of-agile]: 17th State of Agile Report, 2024. Scrum market share 87% (2022) → 63% (2024). Secondary (industry survey).

### Kanban, Flow, and Lean

[^yeret-wip]: Yuval Yeret, *Calculate Kanban WIP Limits in the AI Age* and *Limiting Work-in-Progress (WIP) in Scrum with Kanban*. [yuvalyeret.com](https://yuvalyeret.com/blog/calculate-kanban-wip-limits-ai-age/). Primary (practitioner blog).

[^businessmap-decisions]: BusinessMap/ProofHub, *Using Kanban for Better Decision Making*. [businessmap.io](https://businessmap.io/blog/using-kanban-for-better-decision). Secondary (vendor blog, cites CHAOS Report).

[^kersten-flow]: Mik Kersten, *Project to Product: How to Survive and Thrive in the Age of Digital Disruption with the Flow Framework*, IT Revolution, 2018. Primary (book). Flow Framework: [flowframework.org](https://flowframework.org/).

[^linearb-flow]: LinearB, *5 Key Flow Metrics*. [linearb.io](https://linearb.io/blog/5-key-flow-metrics). Secondary (vendor blog, cites DeGrandis).

[^remojansen-tps]: remojansen, *Revisiting the Toyota Production System (TPS) in the Age of Coding Agents*. [dev.to](https://dev.to/remojansen/revisiting-the-toyota-production-system-tps-in-the-age-of-coding-agents-2bb5). Primary (practitioner blog).

### Coordination at scale

[^bezos-mandate]: Jeff Bezos, *API Mandate*, Amazon, 2002. Widely circulated; original memo not publicly released. [nordicapis.com](https://nordicapis.com/the-bezos-api-mandate-amazons-manifesto-for-externalization/). Secondary (reconstruction from multiple accounts).

[^team-topologies]: Matthew Skelton and Manuel Pais, *Team Topologies: Organizing Business and Technology Teams for Fast Flow*, 2019. Primary (book). [teamtopologies.com](https://teamtopologies.com/key-concepts).

[^google-sre]: Google, *SRE Workbook: Error Budget Policy*. [sre.google](https://sre.google/workbook/error-budget-policy/). Primary (practitioner handbook).

[^autosar]: AUTOSAR, *Adaptive Platform ARACom API* and Classic Platform specifications. [autosar.org](https://www.autosar.org/). Primary (standards body).

[^iso26262-hsi]: ISO 26262, *Road vehicles — Functional safety*, Hardware-Software Interface (HSI) specification. Standard text paywalled; description from public summaries. Secondary for the HSI concept.

[^covesa-vss]: COVESA, *Vehicle Signal Specification (VSS)*. [covesa.github.io](https://covesa.github.io/vehicle_signal_specification/). Primary (open standard).

[^lockheed-digital-thread]: Lockheed Martin, *Visualizing the Digital Thread and Digital Twins*, 2021. [lockheedmartin.com](https://www.lockheedmartin.com/en-us/news/features/2021/visualizing-the-digital-thread-and-digital-twins.html). Secondary (vendor publication).

---

*This post is part of [PulseEngine](/) — a formally verified WebAssembly
Component Model engine for safety-critical systems. Prior posts in the arc:
[The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/),
[Agents don't tidy up](/blog/agents-dont-tidy-up/),
[AI in the product, not AI in the toolchain](/blog/ai-in-the-product-not-the-toolchain/).*
