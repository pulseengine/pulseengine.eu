+++
title = "Can we deliver X by January? Estimation from gates and flow history"
description = "Customers ask for dates. SAFe answers with story points — a complexity measure dressed as a plan. The factory answers with two measurements: gate status for the present, and flow history from past projects for the future. Reference class forecasting, not estimation from scratch."
date = 2026-10-26
draft = true
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
        g1["Gate 1: Requirements — rivet validate"]
        g2["Gate 2: Architecture — spar solver"]
        g3["Gate 3: Code + tests — CI"]
        g4["Gate 4: Coverage — witness MC/DC"]
        g5["Gate 5: Proof — Verus/Kani"]
        g6["Gate 6: Hardware — Renode + silicon"]
        g7["Gate 7: Sign-off — human"]
        g1 --> g2 --> g3 --> g4 --> g5 --> g6 --> g7
        style g1 fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
        style g2 fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
        style g3 fill:#1a1d27,stroke:#f87171,color:#e1e4ed
        style g4 fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
        style g5 fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
        style g6 fill:#1a1d27,stroke:#8b90a0,color:#e1e4ed
        style g7 fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    end

    subgraph future["When will it be done? (flow history from corpus)"]
        direction TB
        h1["Past project A: 12 gates, 8 weeks, 1.5 gates/week"]
        h2["Past project B: 8 gates, 12 weeks, 0.67 gates/week"]
        h3["Past project C: 15 gates, 6 weeks, 2.5 gates/week"]
        h4["X matches B: 8 gates, 3 need decisions<br/>→ 4 weeks mechanical + 8 weeks decision-dependent"]
        h1 --> h2 --> h3 --> h4
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

## The corpus: every past project is a data point

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

## Reference class forecasting, not estimation from scratch

Don't estimate X from zero. **Find the similar past project and use its
actuals.** This is reference class forecasting (Flyvbjerg, *Reference Class
Forecasting in Planning and Forecasting*, 2021)[^flyvbjerg] — the same method
used for railways, bridges, and IT projects that consistently overrun.

> "X matches relay's profile. Relay took 12 weeks: 4 for mechanical gates,
> 8 waiting on decisions. If your hardware access is sorted by March, we're
> looking at June–July 2027. If not, add 8 weeks."

## Monte Carlo, not a single date

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

## The customer conversation

> "We don't guess. We measure. X has 8 gates. Two are green, one is red
> (the proof — we need a decision from your team on the safety argument),
> five haven't started. Based on 12 similar projects in our corpus, the
> mechanical gates take 8–16 weeks. The decision gates depend on you.
> If those land by March, we deliver June–July 2027 with 80% confidence.
> Here's the dashboard showing every gate's status, and here's the
> historical data behind the estimate."

## Why this beats SAFe estimation

| SAFe | Gate + flow model |
|---|---|
| Story points (guessed) | Gate count (measured) |
| Sprint velocity (throughput) | Flow velocity (gates/week from corpus) |
| PI commitment (fixed scope, fixed date) | Confidence interval (range, with assumptions) |
| "We'll try" | "Here's the data, here's the risk, here's what we need from you" |

{% <note kind="warning"> %}
**Story points are the wrong unit for the question being asked — and SAFe
doesn't even require them to be comparable.** Legacy SAFe (4.x/5.0) said
story points "must be normalized" across teams; SAFe 5.1 downgraded this to
optional ("can be aligned"); SAFe 6 removed the guidance entirely. Scaled
Agile's own blog says velocity "should never be compared across teams."
Cross-team calibration is a **common organizational practice** — driven by
portfolio management wanting to sum multi-team estimates — not a framework
requirement. And it's a known anti-pattern: Ron Jeffries, who coined story
points, calls comparing teams on estimates "harmful."
Story points measure *complexity*, not *time*. The customer asks "when is it
ready?" — not "how complex is it?" Calibrating points across teams to make
them comparable answers a question nobody asked, and invites the exact
behavior SAFe warns against: teams gaming the numbers.
{% </note> %}

## The key insight

Software is unknown. **Your factory is not.** The factory has a measurable
throughput. The gates are the units. The corpus is the history. You're not
estimating software — you're estimating **how fast your factory passes
gates**, and that's a measurement, not a guess.

## What we would tell you to take from this

**Don't estimate from scratch. Estimate from the corpus.** Every past project
with gates, deadlines, and requirements is a data point. Find the similar
one and use its actuals.

**Give confidence intervals, not single dates.** "June–July 2027 at 80%
confidence" is more honest than "January 2027" — and it separates the
predictable (mechanical gates) from the unpredictable (decision gates).

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

The corpus in this post is illustrative. Real flow velocity varies by team,
toolchain, and hardware access. The similarity matching is qualitative —
"high (same toolchain)" is a judgment, not a measurement. A larger corpus
with more similarity tags would improve the match.

The Monte Carlo intervals assume past projects are representative of future
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

**Caveats on the evidence.** The corpus table is illustrative — real flow
velocity data would come from the author's own project history. The SAFe
story points findings are from official SAFe documentation (live and archived
via Wayback Machine) plus practitioner blogs and forums; the archived SAFe
4.x/5.0 text is from web.archive.org, and the current SAFe 6 text was
verified on the live site. Some practitioner quotes (Schwaber, Coplien) are
via secondary attribution and were not independently verified.

*Footnotes render at the bottom of the page, grouped by category.*

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

---

*This post is part of [PulseEngine](/) — a formally verified WebAssembly
Component Model engine for safety-critical systems. Prior posts in the arc:
[SAFe was built for slow humans](/blog/safe-was-built-for-slow-humans/),
[The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/),
[Agents don't tidy up](/blog/agents-dont-tidy-up/).*
