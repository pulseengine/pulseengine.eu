+++
title = "Can we deliver X by January? Estimation from gates and flow history"
description = "Customers ask for dates. SAFe answers with story points — a complexity measure dressed as a plan. The factory answers with two measurements: gate status for the present, and flow history from past projects for the future. Reference class forecasting, not estimation from scratch."
date = 2026-10-26
draft = true
ready = true
[taxonomies]
tags = ["process", "ai-agents", "kanban", "estimation", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**The customer asks "can we deliver X by January?" SAFe answers with story
points — a complexity measure, not a time measure.**

The factory answers with **two measurements**: gate status for where we are,
and **flow history** from past projects for when we'll be done.

Don't estimate from scratch. Find the similar past project and use its
actuals. Give confidence intervals, not false precision. Software is unknown;
your factory is not.
{% </insight> %}

[The previous post](/blog/safe-was-built-for-slow-humans/) argued that the
bottleneck in an agent factory is not generation — it is verification and
decisions. This holds whether agents produce code, requirements, architecture,
or tests. But that raises the next question: if the bottleneck is the gate,
how do we answer the customer who asks for a date?

## The customer question

> "Can we deliver X in January 2027?"

SAFe answers with story points and sprint velocity. Story points measure
*complexity* — how hard is this? Sprint velocity measures *throughput* — how
many points per sprint? Neither answers the question the customer actually
asks: **when will it be ready?**

The factory answers with **two measurements**: gate status for the present,
and **flow history** for the future.

{% <mermaid> %}
flowchart TB
    subgraph present["Where are we? (gate status)"]
        direction TB
        g1["Gate 1: Requirements — requirements validation"]
        g2["Gate 2: Architecture — architecture solver"]
        g3["Gate 3: CI — continuous integration"]
        g4["Gate 4: Tests — test suite"]
        g5["Gate 5: Coverage — coverage check"]
        g6["Gate 6: Proof — formal proof"]
        g7["Gate 7: Hardware — simulation + silicon"]
        g8["Gate 8: Sign-off — human"]
        g1 --> g2 --> g3 --> g4 --> g5 --> g6 --> g7 --> g8
        style g1 fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
        style g2 fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
        style g3 fill:#1a1d27,stroke:#f87171,color:#e1e4ed
        style g4 fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
        style g5 fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
        style g6 fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
        style g7 fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
        style g8 fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    end

    subgraph future["When will it be done? (release history from corpus)"]
        direction TB
        h1["synth: 156 releases, 6 months, ~6/week (fast, rudimentary)"]
        h2["rivet: 57 releases, 8 months, 1.8/week (mechanical)"]
        h3["relay: 163 releases, 7 months, ~6/week, 57 in decision queue"]
        h4["X matches relay: 8 gates, 3 need decisions<br/>→ 3–4 weeks mechanical + 2–20 weeks decision-dependent"]
        h1 --> h2 --> h3 --> h4
        style h1 fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
        style h2 fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
        style h3 fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
        style h4 fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    end

    present -->|"gate status"| answer["Answer:<br/>May–June 2027 (80% confidence)<br/>June–July 2027 (with buffer)"]
    future -->|"flow history"| answer
    style answer fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed

    classDef green fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
    classDef red fill:#1a1d27,stroke:#f87171,color:#e1e4ed;
    classDef neutral fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed;
    classDef human fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef estimate fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
{% </mermaid> %}

## The corpus: every past project is a data point

To estimate X, you need history. Every project you've shipped with gates,
deadlines, and requirements is a reference. Here is the actual corpus from
our repositories, measured on 26 October 2026 — seven projects spanning
application, verification, and toolchain layers:

**The gate is the release, not the issue.** In rivet, `rivet release` cuts a
release — that is the bound, the thing that ships. The issues are the work
that goes into the release. One release closes many issues; the release is
what the customer sees. Each gate passage is a release: the mechanical gates
(requirements, architecture, CI, tests, coverage) are **oracle-gated** — a
machine can check them (Blog 1's "oracle axis"). The decision gates (safety
argument, hardware access, sign-off) need a human.

| Project | Releases (gates) | Issues (work)[^issues-prs] | Months active | Release velocity | Issues/release | Decision queue floor |
|---|---|---|---|---|---|---|
| **synth** | 156 | 432 | 6 (May–Oct 2026) | **~6/week** | 2.8 | not yet measured |
| **rivet** | 57 | 264 | 8 (Mar–Oct 2026) | **1.8/week** | 4.6 | not yet measured |
| **relay** | 163 (falcon)[^falcon] | 108 | 7 (Apr–Oct 2026) | **~6/week** | 0.7 | **57** |
| **spar** | 48 | 132 | 8 (Mar–Oct 2026) | **1.6/week** | 2.8 | not yet measured |
| **gale** | 10 | 89 | 3 (Jul–Sep 2026) | **0.77/week** | 8.9 | **30** |
| **jess** | 4 | 12 | 4 (Jun–Sep 2026) | **0.24/week** | 3.0 | not yet measured |
| **loom** | 36 | — | 8 (Jan–Aug 2026) | **1.1/week** | — | **26** |

The decision queue column is the `needs-decision` **floor** from
`scripts/issue-class-floors.json` — a ratchet measured at the first fully
classified pass. It can only tighten, never loosen. It is the brake
threshold: when the queue of undecided issues exceeds this floor, the
issue-hunt skill stops filing new agent-closable work until a human
clears decisions. Relay's floor is 57; gale's is 30; loom's is 26.
These floors set the minimum team size — the number of humans needed
to keep the decision queue from growing.

**Cross-repo dependencies.** jess (hardware integration) has open issues
referencing relay (flight stack) and gale (kernel) — the hardware layer
cannot close its gates until the software layers pass theirs. These
dependencies are managed through **contracts** — the thin agreed
interfaces between stations (see [the next post](/blog/the-orchestrator-who-does-what/)).
synth and relay tie for the highest release velocity (~6/week) but synth
is still rudimentary: many small releases, fast cadence, but the
releases themselves need more work. Speed of release is not the same as
maturity of the gate.

X has 8 gates: 5 mechanical (requirements validation, architecture solver,
CI, tests, coverage), 3 decision-dependent (safety argument, hardware
access, sign-off). That matches relay's profile: hardware-dependent, slow
decisions, a decision queue of 57. If your hardware access is sorted by
March, we're looking at May–June 2027 with 80% confidence, June–July 2027
with a buffer. If not, add 8 weeks.

## Reference class forecasting, not estimation from scratch

Don't estimate X from zero. **Find the similar past project and use its
actuals.** This is reference class forecasting (Flyvbjerg, *Reference Class
Forecasting in Planning and Forecasting*, 2021)[^flyvbjerg] — the same method
used for railways, bridges, and IT projects that consistently overrun.

> "X matches relay's profile. Relay took 12 weeks end-to-end: 4 weeks of
> mechanical gates, 8 weeks waiting on decisions. The critical path allocates
> 8 weeks to relay's portion — the mechanical work plus the decision wait
> that runs in parallel with gale's and jess's work. If your hardware access
> is sorted by March, we're looking at May–June 2027 with 80% confidence,
> June–July 2027 with a buffer. If not, add 8 weeks."

## Confidence intervals, not a single date

Give confidence intervals, not false precision. From the corpus:

- **Mechanical gates** (rivet 1.8 releases/week, spar 1.6/week, synth
  ~6/week): 5 gates take **3–4 weeks** (80% confidence). Each release
  closes ~3–5 issues of mechanical work.
- **Decision gates** (relay ~6/week but 57 in queue, gale 0.77/week with
  30 in queue, jess 0.24/week hardware-blocked): 3 gates take **2–20 weeks**
  depending on hardware access and queue position.

> "Based on 7 projects in our corpus, the mechanical gates take 3–4 weeks.
> The decision gates depend on your hardware access. If that's sorted by
> March, we deliver **May–June 2027** with 80% confidence. With a buffer
> for queue position, **June–July 2027**. If hardware access slips, add
> the slip."

This is honest because:
- You're using **real data** from your corpus
- You're giving **ranges**, not false precision
- You're separating **mechanical gates** (predictable) from **decision gates**
  (unpredictable)

## The critical path

Confidence intervals give you a range. But what determines the **minimum**
time? The **critical path** — the longest chain of dependent gates.

A release is a chain: gate A must pass before gate B can start, gate B before
gate C, and so on. Some chains are short (mechanical gates, fast). Some are
long (decision gates, hardware-blocked). The **critical path** is the longest
chain — the one that sets the minimum release time.

{% <mermaid> %}
flowchart TB
    subgraph parallel["All three run in parallel (agents active)"]
        direction LR
        gale["gale<br/>kernel<br/>4 weeks"]
        relay["relay<br/>flight stack<br/>8 weeks"]
        jess["jess<br/>orchestrator<br/>12 weeks"]
    end

    subgraph chain["Critical path (dependency chain)"]
        direction LR
        cg["gale"] --> cr["relay"] --> cj["jess"]
    end

    gale -.->|"provides primitives"| relay
    relay -.->|"provides flight stack"| jess
    jess -.->|"notices issues,<br/>feeds back upstream"| relay
    jess -.->|"notices issues,<br/>feeds back upstream"| gale

    style gale fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style relay fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style jess fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style cg fill:#1a1d27,stroke:#8b90a0,color:#8b90a0
    style cr fill:#1a1d27,stroke:#8b90a0,color:#8b90a0
    style cj fill:#1a1d27,stroke:#8b90a0,color:#8b90a0

    classDef app fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef orch fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef chain fill:#1a1d27,stroke:#8b90a0,color:#8b90a0;
{% </mermaid> %}

**Critical path: 24 weeks** (application layer). gale (4) + relay (8) + jess (12) = 24 weeks.
But the work runs in parallel — agents are active in all three repos at the
same time. The critical path is the **dependency chain**: jess cannot ship
until relay is bit-exact, relay cannot ship until gale provides its
primitives. Meanwhile, jess notices issues in relay and gale (downstream
finds upstream bugs) and feeds them back. The 24 weeks is the minimum time
for the chain, not a waterfall — the parallel work fills the gaps.

If gale takes 4 weeks, relay takes 8 weeks, and jess takes 12 weeks, the
critical path is **24 weeks** for the application layer. That is the
minimum time to release the software chain. But the delivery estimate of
May–July 2027 includes the hardware constraint: the hardware gate cannot
start until boards are available (sorted by March 2027). The 24-week
critical path runs from now (October 2026) to ~April 2027 for the
software; the hardware gate adds the remaining wait until boards are
free, landing delivery in May–July 2027.

This 24-week critical path covers the **application layer** (gale → relay
→ jess). The full dependency chain — including the toolchain and
verification layers — is longer and is traced in [the next post](/blog/the-orchestrator-who-does-what/).

**How to find the critical path:**

1. **List the gates** — every gate in the release, with its duration
2. **List the dependencies** — which gates must pass before each gate can start
3. **Trace the chains** — follow the dependencies from start to finish
4. **Find the longest chain** — that's the critical path
5. **The critical path duration is the minimum release time**

**Why it matters:**

- **Estimation** — the critical path duration is the minimum estimate. Add
  buffer for the non-critical paths.
- **Bottlenecks** — the critical path is where the bottlenecks are. Fix the
  critical path, and the release gets faster.
- **Prioritization** — work on the critical path first. Work on non-critical
  paths can wait.
- **Communication** — tell the customer the critical path. "We can deliver
  in 24 weeks minimum, because this chain of dependencies takes 24 weeks."

**The critical path moves.** Fix the hardware bottleneck, and the decision
queue becomes the critical path. Add more runners, and the CI queue moves.
The critical path is not fixed — it moves as you improve other steps.

## What you need to collect

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

## Who does the estimation

Estimation is not a solo guess. It is a **collaborative measurement** across
the roles from [the previous post](/blog/safe-was-built-for-slow-humans/):

| Role | Contribution to the estimate |
|---|---|
| **Orchestrator** | Decomposes X into gates, identifies which need customer decisions, matches X to similar past projects |
| **Team** | Measures flow velocity from past projects, reports which gates are mechanical vs decision-dependent |
| **Colleague** | Runs the hardware gates, reports silicon status and hardware-access blockers |
| **Customer** | Provides the decisions that unblock the decision gates — the variance is in their hands, not the code |

The pattern: **give away the work that blocks you, keep the work that
multiplies you.** The orchestrator's leverage is in designing gates and
matching to history. Hardware setup, final production tests, the nitty-gritty
that needs physical access — hand those to the roles whose leverage starts
where yours ends.

Osmani defines the orchestrator role: "You're orchestrating AI agents — while
you act as architect, reviewer, and decision-maker… You own the codebase"[^osmani-agentic].
O'Reilly Radar traces the arc: "from coder to conductor and ultimately
orchestrator… Our jobs are shifting from 'How do I code this?' to 'How do I get
the right code built?'"[^oreilly-orchestrator]. Herrmann & Schmidt frame
delegation as "management by objectives" replacing "step-by-step task
prescription"[^herrmann-delegation]. Karpathy's "autonomy slider" captures the
same idea: "we will move the autonomy slider from left to right over time" —
the human sets how far right the slider sits per task[^karpathy-software3].

## How many humans do we need?

The question everyone asks after "how do we estimate?" is "how many people
does this take?" The answer changes when agents write the code.

**Before agents:** 100 humans writing code. The bottleneck was code
production. Team size scaled with lines of code.

**After agents:** agents write the code. The bottleneck is decisions and
verification. Team size scales with **release throughput** — how many
releases per week can humans decide and verify?

The math is simple:

```
Steady-state team size = (releases per week) / (releases per human per week)
```

If your factory ships 6 releases per week (like relay), and one human can
decide/verify 1 release per week, you need **6 humans** to keep up. Not
100. Not 50. Six.

But there is a second number: the **queue capacity**. The decision queue
floor (the ratchet from Blog 1) sets a minimum. Relay's floor is 57 —
meaning at the first classified pass, 57 issues were waiting for human
decisions. To clear that backlog at 1 decision per human per day, you
need enough humans to drain it within your target cycle time. The WIP
limit on the decision queue caps how many items can wait; the team size
must be large enough to clear the queue within that limit.

| Measure | Formula | Relay example |
|---|---|---|
| Steady-state team size | releases/week ÷ releases/human/week | 6 ÷ 1 = **6 humans** |
| Queue capacity | decision queue floor ÷ decisions/human/day × target days | 57 ÷ 5 × 5 = **~6 humans** |

Both formulas converge on the same answer when the WIP limit is set
correctly: the team size is the number of humans needed to keep the
decision queue from growing. The WIP limit is the brake; the team size
is the engine that keeps the brake from firing.

The ratio is the insight: **one human can oversee many agents, but the
limit is release throughput.** An agent can produce a thousand lines in an
hour. A human can decide whether a release is correct in a day. The
factory's throughput is set by the humans, not the agents.

| Before agents | After agents |
|---|---|
| 100 humans writing code | 6 humans deciding and verifying |
| Bottleneck: code production | Bottleneck: release throughput |
| Team size scales with KLOC | Team size scales with releases/week |
| Velocity = story points/sprint | Release velocity = releases/week |
| Hire more coders to go faster | Add decision capacity to go faster |

{% <note kind="tip"> %}
**The people stay. The work changes.** This is not about letting people go.
The question is: *with whom can we do this, and how should they do it?* The
coders become orchestrators — they design gates, review output, decide what
the oracles cannot. The reviewers become quality owners — they prove the
gates can fail. The team leads become decision owners — they clear the
decision queue. Same people, different leverage. The factory needs fewer
hands on the line, but more hands on the gates.
{% </note> %}

The WIP limit on the decision queue is the brake. If you cap the
decision queue at 10 items, you need roughly 10 humans to clear it
within a week (at 1 decision per human per day, 5 working days). If
you cap it at 50, you need 50. The cap is the team size — but only
if the cap matches the throughput. A cap of 50 with 6 releases per
week means the queue grows faster than humans can drain it. Set the
cap to match the throughput, and the team size follows.

This is why the vocabulary matters. "Team size" in SAFe means "how many
people write code." In the factory, it means "how many people ship
releases." The number is smaller. The leverage is higher.

## The customer conversation

> "We don't guess. We measure. X has 8 release gates. Two are green, one is
> red (the proof — we need a decision from your team on the safety
> argument), five haven't started. Based on 7 projects in our corpus, the
> mechanical gates take 3–4 weeks. The decision gates depend on your
> hardware access. If that's sorted by March, we deliver May–June 2027
> with 80% confidence, June–July 2027 with a buffer. Here's the dashboard
> showing every gate's status, and here's the historical data behind the
> estimate."

## Why this beats SAFe estimation

| SAFe | Gate + flow model |
|---|---|
| Story points (guessed) | Gate count (measured) |
| Sprint velocity (throughput) | Flow velocity (gates/week from corpus) |
| PI commitment (fixed scope, fixed date) | Confidence interval (range, with assumptions) |
| "We'll try" | "Here's the data, here's the risk, here's what we need from you" |

**Story points are the wrong unit for the question being asked — and SAFe
doesn't even require them to be comparable.** Legacy SAFe (4.x/5.0) said
story points "must be normalized" across teams[^safe-normalization-legacy];
SAFe 5.1 downgraded this to optional ("can be aligned")[^safe-normalization-51];
SAFe 6 removed the guidance entirely[^safe-normalization-current]. Scaled
Agile's own blog says velocity "should never be compared across teams"[^safe-velocity-never-compare].
Cross-team calibration is a **common organizational practice** — driven by
portfolio management wanting to sum multi-team estimates — not a framework
requirement. And it's a known anti-pattern: Ron Jeffries, who coined story
points, calls comparing teams on estimates "harmful"[^jeffries-points].
Story points measure *complexity*, not *time*. The customer asks "when is it
ready?" — not "how complex is it?" Calibrating points across teams to make
them comparable answers a question nobody asked, and invites the exact
behavior SAFe warns against: teams gaming the numbers.

## The key insight

Software is unknown. **Your factory is not.** The factory has a measurable
throughput. The gates are the units. The corpus is the history. You're not
estimating software — you're estimating **how fast your factory passes
gates**, and that's a measurement, not a guess.

## What we would tell you to take from this

**Don't estimate from scratch. Estimate from the corpus.** Every past project
with gates, deadlines, and requirements is a data point. Find the similar
one and use its actuals.

**Give confidence intervals, not single dates.** "May–June 2027 at 80%
confidence, June–July 2027 with a buffer" is more honest than "January
2027" — and it separates the predictable (mechanical gates) from the
unpredictable (decision gates).

**Story points measure complexity, not time.** SAFe doesn't require
cross-team calibration — it's an organizational practice, and a known
anti-pattern. The customer asks "when," not "how complex."

**Estimation is a collaborative measurement.** The orchestrator decomposes
and matches. The team measures flow. The colleague runs hardware gates. The
customer provides decisions. Nobody guesses alone.

**Software is unknown. Your factory is not.** You're not estimating software
— you're estimating how fast your factory passes gates. That's a
measurement, not a guess.

## Limits

This estimation model depends on having a **corpus** — past projects with
gate-level history. If you have no history, you cannot do reference class
forecasting. COCOMO (Boehm, 1981; COCOMO II, 2000) can give a rough
order-of-magnitude for very early estimation ("30–80 KLOC, high reliability
→ 6–12 months"), but it is a size-based model from the waterfall era with no
concept of gates, oracles, or decision queues. Once you have gates, switch
to the flow model.

The corpus in this post is real data from the author's repositories,
measured on 26 October 2026. Real flow velocity varies by team,
toolchain, and hardware access. The similarity matching is qualitative —
"X matches relay's profile" is a judgment, not a measurement. A larger
corpus with more similarity tags would improve the match.

The confidence intervals assume past projects are representative of future
ones. If your factory's throughput is changing (new tools, new team members,
new gate types), the corpus may not predict the future.

## Sources and caveats

The estimation model is grounded in the author's own practice and in the
measurements from [The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/)
and [SAFe was built for slow humans](/blog/safe-was-built-for-slow-humans/).
The reference class forecasting method is from Flyvbjerg (2021). The Flow
Framework metrics are from Kersten (2018). The SAFe story points research
is from archived and current scaledagileframework.com documentation plus
practitioner sources; each is cited with its tier below.

**Caveats on the evidence.** The corpus table is real data from the
author's own repositories, measured on 26 October 2026. The similarity
matching is qualitative — "X matches relay's profile" is a judgment, not
a measurement. A larger corpus with more similarity tags would improve
the match. The confidence intervals are derived from the corpus
statistics, not from a Monte Carlo simulation. The SAFe story points
findings are from official SAFe documentation (live and archived via
Wayback Machine) plus practitioner blogs and forums; the archived SAFe
4.x/5.0 text is from web.archive.org, and the current SAFe 6 text was
verified on the live site. Some practitioner quotes (Schwaber, Coplien)
are via secondary attribution and were not independently verified.


[^flyvbjerg]: Bent Flyvbjerg, *Reference Class Forecasting in Planning and Forecasting*, 2021. Primary (book). The method: estimate from the actuals of similar past projects, not from a bottom-up estimate of the current project.

[^kersten-flow]: Mik Kersten, *Project to Product: How to Survive and Thrive in the Age of Digital Disruption with the Flow Framework*, IT Revolution, 2018. Primary (book). Flow Framework: [flowframework.org](https://flowframework.org/).

[^osmani-agentic]: Addy Osmani, *Agentic Engineering*. [addyosmani.com](https://addyosmani.com/blog/agentic-engineering/). Primary (practitioner essay).

[^oreilly-orchestrator]: O'Reilly Radar, *Conductors to Orchestrators: The Future of Agentic Coding*. [oreilly.com](https://www.oreilly.com/radar/conductors-to-orchestrators-the-future-of-agentic-coding/). Secondary (interview/essay).

[^herrmann-delegation]: Werner Herrmann and Maximilian Schmidt, *Delegation Interaction: A Paradigm Shift in Human-AI Collaboration*, AutomationXP 2026. [matthiasbaldauf.com](https://matthiasbaldauf.com/automationxp26/papers/AutomationXP26_paper_8866.pdf). Primary (workshop paper).

[^karpathy-software3]: Andrej Karpathy, *Software Is Changing (Again)*, YC Startup Library, February 2026. Primary (talk transcript). [ycombinator.com](https://www.ycombinator.com/library/MW-andrej-karpathy-software-is-changing-again).

[^jeffries-points]: Ron Jeffries, *Story Points*, 2019. [ronjeffries.com](https://ronjeffries.com/articles/019-01ff/story-points/Index.html). Primary (practitioner critique, coined the term). "Some approaches to 'Agile' actually recommend normalizing story points across teams... it's too easy to fall into the trap of comparing teams... I think comparing teams on quality of estimates or velocity is harmful."

[^safe-normalization-legacy]: Scaled Agile, Inc., *Iteration Planning* (SAFe 4.x/5.0, archived 2021–2022). [web.archive.org](https://web.archive.org/web/2021id_/https://scaledagileframework.com/iteration-planning/). Primary (archived official documentation). "In SAFe, however, story point estimation must be normalized, so that estimates for features or epics that require the support of multiple teams, are based on the same story point definition."

[^safe-normalization-51]: Scaled Agile, Inc., *Iteration Planning* (SAFe 5.1, archived 2023). [web.archive.org](https://web.archive.org/web/2023id_/https://scaledagileframework.com/iteration-planning/). Primary (archived official documentation). "Story points can be aligned (approximately normalized) by teams in the ART" — modal verb "can be," optional.

[^safe-normalization-current]: Scaled Agile, Inc., *Iteration Planning* (SAFe 6, current). [scaledagileframework.com](https://scaledagileframework.com/iteration-planning/). Primary (current official documentation). Normalization guidance removed entirely; zero occurrences of "normalized," "aligned," or "shared basis."

[^safe-velocity-never-compare]: Scaled Agile, Inc., *SAFe Metrics at the Team Level: Sales Ops*, August 2024. [scaledagile.com](https://scaledagile.com/blog/safe-metrics-at-the-team-level-sales-ops/). Primary (official blog). "Velocity metrics should never be compared across teams or used as a productivity measurement."

[^wibas-alignment-optional]: WIBAS, *A tricky slide about Story Points and Capacity in SAFe* and *Agile Estimation in SAFe: Debunking Myths*. [wibas.com](https://www.wibas.com/blog/a-tricky-slide-about-story-points-and-capacity-in-safe-and-how-to-get-it-right/). Secondary (training/consulting firm). "Aligning is an option in SAFe, but not a requirement ('can be')."

[^lindenbaum-dangers]: Densmore Lindenbaum, *The Dangers of Normalized Story Point Estimation*. [densmore.lindenbaum.us](https://densmore.lindenbaum.us/lean-agile/scaling/the-dangers-of-normalized-story-point-estimation/). Primary (practitioner paper). "The Scaled Agile Framework® (SAFe) contains a method for initializing and normalizing an Agile team's effort and/or complexity estimates, the use of which can result in poor behavior by Agile teams."

[^rothman-comparing-teams]: Johanna Rothman, *Comparing Teams is Not Useful: Exposing Another Management Myth*, 2013. [jrothman.com](https://www.jrothman.com/mpd/management/2013/08/comparing-teams-is-not-useful-exposing-another-management-myth/). Primary (practitioner blog). "Managers want to compare teams to see which teams are more productive. This is even crazier... The teams will start to game the measurements if you try."

[^safe-wsjf]: Scaled Agile, Inc., *Weighted Shortest Job First (WSJF)*. [scaledagileframework.com](https://scaledagileframework.com/wsjf/). Primary (official documentation). "WSJF is estimated as the relative cost of delay divided by the relative job duration" — deliberately relative, no cross-team point comparability needed.

[^safe-measure-grow]: Scaled Agile, Inc., *Measure and Grow* (updated September 2025). [scaledagileframework.com](https://scaledagileframework.com/measure-and-grow/). Primary (official documentation). "Business agility requires measuring outcomes, flow, and competency... Flow metrics measure delivery efficiency and predictability."

[^falcon]: relay's releases are tagged under the `falcon-` prefix — the flight stack component family within the relay repository. All 163 releases are falcon-component releases.

[^issues-prs]: The "Issues (work)" column counts GitHub issues only (excluding pull requests). GitHub shares the number space between issues and PRs, so the highest issue/PR number in a repo is much larger than the issue count — e.g. jess has 12 issues but the highest number is #297 because PRs occupy the intervening numbers.

---

*Next in the arc: [The orchestrator: who does what when bottlenecks won't go away](/blog/the-orchestrator-who-does-what/) — the roles, the contracts, and the human who defines the skills, triggers the agents, and clears the decision queue.*

---

*This post is part of [PulseEngine](/) — a formally verified WebAssembly
Component Model engine for safety-critical systems. Prior posts in the arc:
[SAFe was built for slow humans](/blog/safe-was-built-for-slow-humans/),
[The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/),
[Agents don't tidy up](/blog/agents-dont-tidy-up/).*
