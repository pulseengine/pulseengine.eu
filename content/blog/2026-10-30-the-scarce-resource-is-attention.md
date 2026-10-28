+++
title = "The scarce resource is the orchestrator's attention"
description = "On 28 October one machine ran about 22 agent sessions in parallel, and survey research published in March 2026 identifies overseeing AI agents as the strongest driver of the strain. We built a decision inbox with an attention budget: three flows may ask at a time, and questions wait for a decision window and one digest. It is days old and unmeasured; this post says what we will measure."
date = 2026-10-30
draft = true
[taxonomies]
tags = ["process", "ai-agents", "orchestration"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**With about 22 agent sessions running, the bottleneck is the one person they ask.**

- On 28 October this machine had about 22 agent sessions open in parallel,
  with meetings on top, by the owner's own count.
- A BCG survey of 1,488 US workers was published in HBR in March 2026. As
  reported by The Decoder, it identifies overseeing AI agents as the strongest
  driver of the strain, and self-rated productivity peaks at three
  simultaneous AI tools.
- In response we shipped a decision inbox (plugin 0.44.0) and an attention
  budget (0.45.0): at most three flows ask at a time, questions wait for a
  decision window, one digest collects them, and security or red-`main`
  decisions skip the queue. All of it is days old and nothing about it has
  been measured yet.
{% </insight> %}

[SAFe was built for slow humans](/blog/safe-was-built-for-slow-humans/)
argued that the bottleneck in an agent factory is verification and decisions,
and quoted Yuval Yeret's point that human attention is scarcer than agent
runtime. [The orchestrator](/blog/the-orchestrator-who-does-what/) described
the one person who directs the agents. This post is about what happens to
that person's day when the number of agents grows, and about the mechanism we
built to ration his attention among them.

## What the research measured

In March 2026 six authors working with BCG published "When Using AI Leads to
'Brain Fry'" in the Harvard Business Review[^hbr-brainfry]. The article is
paywalled, so the figures below are as reported by The Decoder and The
Register, not read from the article itself. The survey covered 1,488
full-time US workers. The Decoder reports that 14% of the respondents who use
AI described the condition the authors call brain fry, which it attributes to
excessive use or oversight of AI, and names direct oversight of AI agents as
the strongest driver. Workers with high oversight demands reported 14% more
mental effort and 12% more mental fatigue[^decoder-brainfry]. Those affected
reported 33% more decision fatigue and 39% more major errors. The Register
gives the 39% for a slightly different group, workers who felt they used too
much AI[^register-brainfry].

The finding that matters for an orchestrator concerns concurrency. Perceived
productivity rises from one simultaneous AI tool to two and drops beyond
four; in The Decoder's words, "At three tools, it peaks." The study counted
tools a person works with at once, and its productivity measure is
self-reported. Neither is the same as the number of agent sessions on one
machine, so we use it as a direction and do not carry the number three over.

A second line of work looks at volume rather than oversight. Aruna
Ranganathan and Xingqi Maggie Ye of Berkeley Haas published "AI Doesn't
Reduce Work—It Intensifies It" in HBR in February 2026[^hbr-intensify]. As
reported by heise, it is an eight-month field study, April to December 2025,
of a US tech company with about 200 employees, in which people using AI took
on more tasks, worked longer and switched between tasks more
often[^heise-intensify]. The study is still running and heise gives no
percentages.

## Our own case

On 28 October, with those sessions open and meetings on top, the owner
reported himself overloaded. The same morning the record in
[#280](https://github.com/pulseengine/pulseengine.eu/pull/280) counts 53 pull
requests opened across the organisation by 07:00 UTC, many of them one-line
documentation edits, while all 14 self-hosted runners were busy.

Each session that reaches a fork asks in the chat. With 22 sessions and
meetings in between, one person answers questions in arrival order, and each
answer costs a context switch into a repository he was not thinking about.
Nothing limited how many could ask at once.

## What we built

Three changes landed on 28 October, all in the pulseengine-claude plugin that
lives in this site's repository.

### A decision inbox, so agents do not block

The `factory-notice` skill
([#282](https://github.com/pulseengine/pulseengine.eu/pull/282), plugin
0.44.0) gives an unattended agent a place to put a fork instead of asking in
the chat and waiting. A needs-decision notice carries the question, the
options with pros and cons, a recommendation and why, whether the step is
reversible and what it blocks. The skill tells the agent not to take the
fork but to continue with work that does not depend on the answer, and to
poll for the answer each time it wakes. It is told never to apply its own
recommendation because nobody replied, and that an irreversible step always
waits. These are instructions in the skill; no code enforces them.

An answer is an instruction to an agent, so `notice.py` enforces four rules
before it accepts one, each checked against the agent's local copy of the
notice: the agent posted that notice, the option is one it offered, the
answer is for the current revision, and that revision has not already been
answered. The consumed record is created with `O_EXCL`, so the first accepted
answer wins. A note attached to an answer is printed quoted and labelled as
data, and the skill tells the agent not to follow it.

### An attention budget, so the inbox does not become the next queue

An inbox alone moves the sessions' questions into one list. The attention
budget ([#284](https://github.com/pulseengine/pulseengine.eu/pull/284), plugin
0.45.0) limits what reaches the owner from that list.

| Rule | What it does |
|---|---|
| **Flow cap** | At most `max_asking_flows` flows ask at a time, default 3. Every other decision is queued, kept, and promoted as the flows ahead of it clear |
| **Decision windows** | Outside a window the session hook shows answers waiting and a count, never a routine question. The defaults are 08:30 to 09:00 and 17:00 to 17:30 |
| **Focus blocks and off periods** | No notification in a focus block. During an off period nothing surfaces and nothing notifies, and the next window's digest covers the gap |
| **One digest** | `notice.py digest` writes one file grouped by flow, and `notice.py review` walks it so the decisions are answered in one sitting |
| **Urgent bypass** | A decision tagged `security` or `red-main` skips the cap, the windows and focus blocks, and takes no slot. It still waits during an off period |

A macOS notification carries two counts and the command to run, and nothing
from any decision, because a notification shows on a locked screen and stays
in the notification history.

The cap of three is our choice, informed by the study's peak at three
simultaneous tools. The study did not test a cap on asking flows. The cap
limits how many flows may put a question to the owner, and all 22 sessions
keep working.

### Admission and batching, so pull requests do not flood the same person

[#280](https://github.com/pulseengine/pulseengine.eu/pull/280) (plugin
0.43.0) attacks the same problem from the CI side. Before an agent opens a
pull request, the `ci-status` skill tells it to check the queue. A
documentation change is batched onto the session's own open pull request in
that repository, or held, when the repository has a queued run or the session
already has an open pull request there. A fix or feature is held at five or
more queued runs. Security fixes and fixes for a red `main` always open.
These are starting thresholds, and the skill treats admission as advice to
the agent rather than a gate. Fewer, larger pull requests mean fewer CI runs
and fewer reviews to schedule.

### One schedule for every machine, still planned

The owner should set his windows once and have every agent use them.
[warte#63](https://github.com/pulseengine/warte/issues/63) asks the warte
control tower for a settings page and a `GET /api/attention` route that
serves the schedule, with owner-only writes. The issue is open and, as of
28 October, the route does not exist yet. Until it does, `notice.py` falls
back to its last cached copy of warte's answer, then a local file, then the
built-in defaults, and says which source it used.

## What is not true yet

As of 28 October, the scheduled `window-tick` that writes the digest every 10
minutes is not installed on this machine, and one agent has posted one
notice. Writes to the deployed warte need a bearer token that no warte route
or CLI command we found issues yet, so notices stay in the local outbox and
the owner answers locally. An agent picks up an answer when it next wakes and
polls; nothing wakes it. There is no baseline for the old setup either,
because nobody counted the load while 22 sessions asked in the chat.

## What we will measure

The instrument is the load line the digest opens with: open decisions, how
many are surfaced and how many queued, flows asking, the age of the oldest
open decision, and
decisions answered in the last 7 days. The first digest after `window-tick`
is installed is week 0, a reading of the budget itself rather than of the old
setup, and we will record the line once a week from then. Alongside it we
will record decisions posted per week and the number of agents posting,
which the digest does not print.

Three readings would show the budget working. The oldest open decision
should stay under 48 hours at every weekly reading, because a cap that makes
questions wait for weeks means the bottleneck has only moved; a weekly
snapshot can miss a spike between readings. Decisions answered should hold
steady or rise as a share of decisions posted, since the raw count will rise
with adoption anyway. How often the owner is interrupted is not measured, and
nothing records it. If the oldest age climbs week on week, the cap is too
tight or the windows too short, and the settings change. We will report the
first four weeks of readings in a follow-up post, with every settings change
and its date.

These readings cover throughput and latency. They say nothing about the
owner's strain, which the study measured by self-report.

## Limits and sources

This is one factory with one orchestrator. The session count is the owner's
own count from 28 October, not an instrumented measurement. The research
figures are a single survey of US workers, reported through secondary
coverage because the primary article is paywalled, and they measure
simultaneous AI tools, not agent sessions. The mechanism is described from
the merged pull requests and the skill's documentation in this repository,
read on 28 October 2026. Whether it reduces the load is not yet known.

[^hbr-brainfry]: Julie Bedard, Matthew Kropp, Megan Hsu, Olivia T. Karaman, Jason Hawes and Gabriella Rosen Kellerman, *When Using AI Leads to "Brain Fry"*, Harvard Business Review, 5 March 2026. [hbr.org](https://hbr.org/2026/03/when-using-ai-leads-to-brain-fry). Primary, paywalled; authors and date read from the article page. The figures in this post come from the coverage below.

[^decoder-brainfry]: Maximilian Schreiner, *Study warns of "AI Brain Fry" as workers hit cognitive limits overseeing AI agents*, The Decoder, 9 March 2026. [the-decoder.com](https://the-decoder.com/study-warns-of-ai-brain-fry-as-workers-hit-cognitive-limits-overseeing-ai-agents/). Secondary (news report of the HBR article). Source of the 14%, 12%, 33% and 39% figures, the strongest-driver finding and the three-tool peak.

[^register-brainfry]: Brandon Vigliarolo, *'AI brain fry' affects employees managing too many agents*, The Register, 9 March 2026. [theregister.com](https://www.theregister.com/2026/03/09/ai_brain_fry_managing_agents). Secondary (news report). Gives the 39% as "self-reported error rates among those who felt they were using too much AI".

[^hbr-intensify]: Aruna Ranganathan and Xingqi Maggie Ye, *AI Doesn't Reduce Work—It Intensifies It*, Harvard Business Review, 9 February 2026. [hbr.org](https://hbr.org/2026/02/ai-doesnt-reduce-work-it-intensifies-it). Primary, paywalled; authors, affiliation and date read from the article page.

[^heise-intensify]: Malte Kirchner, *Study: AI does not make work easier, but more intense*, heise online, 10 February 2026. [heise.de](https://www.heise.de/en/news/Study-AI-does-not-make-work-easier-but-more-intense-11171288.html). Secondary (news report). Source of the study design: eight months, April to December 2025, about 200 employees.

---

*This post is part of [PulseEngine](/) — a WebAssembly Component Model engine
for safety-critical systems, with machine-checked proofs for parts of it
(work in progress).*
