+++
title = "The scarce resource is the orchestrator's attention"
description = "On 28 October one machine ran about 22 agent sessions in parallel, and survey research published in March 2026, as reported, identifies overseeing AI agents as the strongest driver of cognitive strain. We built a decision inbox with an attention budget: it surfaces at most three routine flows at a time, and questions wait for a decision window and one digest. It is days old and unmeasured; this post says what we will measure."
date = 2026-10-30
draft = false
ready = true
[taxonomies]
tags = ["process", "ai-agents", "orchestration"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**With about 22 agent sessions running, the bottleneck is the one person they ask.**

- By the owner's own count, this machine had about 22 agent sessions open in
  parallel on 28 October, with meetings on top.
- A BCG survey of 1,488 US workers was published in HBR in March 2026. As
  reported by The Decoder, it identifies overseeing AI agents as the strongest
  driver of cognitive strain in a study of what the authors call AI brain
  fry, and self-rated productivity peaks at three simultaneous AI tools.
- In response we shipped a decision inbox (plugin 0.44.0) and an attention
  budget (0.45.0): the digest, the session hook and review surface at most
  three routine flows at a time, questions wait for a decision window, one
  digest collects them, and security or red-`main` decisions skip the queue.
  Three is a starting value suggested by the study's peak; the study did not
  test a cap on asking flows. All of it is days old and nothing about it has
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
AI described what the authors call AI brain fry, which the authors, as
reported by The Decoder, define as mental fatigue from excessive use or
oversight of AI tools beyond one's cognitive capacity. The Decoder names
direct oversight of AI agents as the strongest driver of cognitive strain. Workers with high oversight
demands reported 14% more mental effort and 12% more mental
fatigue[^decoder-brainfry]. Respondents with AI brain fry reported 33% more
decision fatigue and 39% more major errors. The Register gives the 39% for a
slightly different group, workers who felt they used too much
AI[^register-brainfry].

For an orchestrator the finding on concurrency matters most. Perceived
productivity rises from one simultaneous AI tool to two and drops beyond
four; in The Decoder's words, "At three tools, it peaks." The study counted
tools a person works with at once, and its productivity measure is
self-reported. Neither is the same as the number of agent sessions on one
machine, so we read the finding as a direction. Three is a starting value
suggested by the study's peak; the study does not test a cap on asking flows,
and we will tune it.

A second line of work looks at volume rather than oversight. Aruna
Ranganathan and Xingqi Maggie Ye of Berkeley Haas published "AI Doesn't
Reduce Work—It Intensifies It" in HBR in February 2026[^hbr-intensify]. As
reported by heise, it is an eight-month field study, April to December 2025,
of a US tech company with about 200 employees, in which people using AI took
on a broader range of tasks, worked longer hours and switched constantly
between tasks[^heise-intensify]. The study is still running and heise gives
no percentages.

## Our own case

On 28 October, with about 22 agent sessions open and meetings on top, the
owner reported himself overloaded. The same morning the record in
[#280](https://github.com/pulseengine/pulseengine.eu/pull/280) counts 53 pull
requests opened across the organisation by 07:00 UTC, in its words "many of
them one-line docs edits", while all 14 self-hosted runners were busy.

Each session that reaches a fork asks in the chat. With about 22 sessions and
meetings in between, one person answers questions in arrival order, and each
answer costs a context switch into a repository he was not thinking about.
Nothing limited how many could ask at once.

## What we built

Three changes landed on 28 October, all in the pulseengine-claude plugin that
lives in this site's repository; a fourth is planned.

### A decision inbox, so agents do not block

The `factory-notice` skill
([#282](https://github.com/pulseengine/pulseengine.eu/pull/282), plugin
0.44.0) gives an unattended agent a place to put a fork instead of asking in
the chat and waiting. A needs-decision notice carries the question, the
options with pros and cons, a recommendation and why, whether the step is
reversible and what it blocks. The skill tells the agent to leave the fork
open, continue with work that does not depend on the answer, and poll for the
answer each time it wakes. It is told never to apply its own recommendation
because nobody replied, and that an irreversible step always waits. These are
instructions in the skill; no code enforces them.

An answer is an instruction to an agent, so `notice.py` enforces at least
four rules before it accepts one, each checked against the agent's local copy
of the notice: the agent posted that notice, the option is one it offered,
the answer is for the current revision, and that revision has not already
been answered. The consumed record is created with `O_EXCL`, so the first
accepted answer wins. A note attached to an answer is printed quoted and
labelled as data, and the skill tells the agent not to follow it. These rules
guard against forged rows on warte, the control tower described below; their
known limits are listed in the skill.

### An attention budget, so the inbox does not become the next queue

An inbox alone moves the sessions' questions into one list. The attention
budget ([#284](https://github.com/pulseengine/pulseengine.eu/pull/284), plugin
0.45.0) limits what reaches the owner from that list.

| Rule | What it does |
|---|---|
| **Flow cap** | At most `max_asking_flows` flows ask at a time, default 3. Every other decision is queued and promoted as the flows ahead of it clear |
| **Decision windows** | Outside a window the session hook shows answers waiting and a count, never a routine question. The defaults are 08:30 to 09:00 and 17:00 to 17:30 |
| **Focus blocks and off periods** | No routine notification in a focus block. During an off period nothing surfaces and nothing notifies, and the next window's digest covers the gap |
| **One digest** | `notice.py digest` writes one file grouped by flow, and `notice.py review` walks it so the decisions are answered in one sitting |
| **Urgent bypass** | A decision tagged `security` or `red-main` skips the cap, the windows and focus blocks, and takes no slot. It still waits during an off period |

The cap governs what `notice.py` shows the owner, directly or through the
agent's session hook: the digest, the hook's output, `review` and the
notification. The windows govern the session hook and
`window-tick`; a `digest` or `review` the owner runs by hand ignores them.
Nothing stops a session from asking in the chat instead, and the budget's
known limits are listed in the skill.

A macOS notification carries two counts and the command to run, and nothing
from any decision, because a notification shows on a locked screen and stays
in the notification history.

### Admission and batching, so pull requests do not flood the same person

[#280](https://github.com/pulseengine/pulseengine.eu/pull/280) (plugin
0.43.0) attacks the same problem from the CI side. Before an agent opens a
pull request, the `ci-status` skill tells it to check the queue. When the
repository has a queued run, or the session already has an open pull request
there, a documentation change is added to that pull request if one exists
and held otherwise. A fix or feature is held at five or more queued runs.
Security fixes and fixes for a red `main` always open. These are starting
thresholds. All of admission is an instruction in the skill; no code enforces
it, and when no source answers the agent opens anyway. Fewer, larger pull
requests mean fewer CI runs and fewer reviews to schedule.

### One schedule for every machine, still planned

The owner should set his windows once and have every agent use them.
[warte#63](https://github.com/pulseengine/warte/issues/63) asks the warte
control tower for a settings page and a `GET /api/attention` route that
serves the schedule, with owner-only writes. The issue is open and, as of
28 October, the route does not exist yet. Until it does, `notice.py` falls
back to its last cached copy of warte's answer, then a local file, then the
built-in defaults, and says which source it used.

## What is not true yet

The scheduled `window-tick`, which runs every 10 minutes and writes the
digest in each window, was installed on this machine on 28 October 2026. As
of that day, one agent had posted one notice, a `session-summary`, so no decision has gone
through the budget yet. Writes to the deployed warte need a bearer token, and
we found no warte route or CLI command that issues one yet, so notices stay
in the local outbox and the owner answers locally. An agent picks up an
answer when it next wakes and polls; nothing wakes it. There is no baseline
for the old setup either, because nobody counted the load while the sessions
asked in the chat.

## What we will measure

The instrument is the load line the digest opens with: open decisions, how
many are surfaced and how many queued, flows asking, the age of the oldest
open decision, and decisions answered in the last 7 days. Flows asking counts
every flow with an open decision, queued ones included, so it can exceed
three. Week 0 is the week of 28 October 2026, when `window-tick` was
installed; it is a reading of the budget itself rather than of the old setup,
and we record the line once a week from then. Alongside it we will record
decisions posted per week, counted from the `needs-decision` notices by `opened_at` in the local
store, and the number of agents posting, counted from the agent directories
that hold at least one `needs-decision` notice. The digest prints neither,
and the store is per machine, so both counts cover this machine only.

The budget is working if the oldest open decision stays under 48 hours at
every weekly reading. A cap that makes questions wait for weeks has only moved
the bottleneck. A weekly reading can miss a spike between readings. The
criterion assumes windows on every day, as the defaults have; a
Monday-to-Friday schedule leaves about 63 hours from Friday 17:30 to Monday
08:30. If the oldest age climbs week on
week, the cap is too tight or the windows too short, and the settings change.
If it stays over 48 hours for two weekly readings after a settings change,
the budget has moved the bottleneck and we will say so. We will also report
decisions answered against decisions posted, as a figure without a
threshold, because the answered count includes answers to older decisions and
the ratio can exceed one. The first four weekly readings go into a follow-up
post due around 25 November 2026, with every settings change and its date.

These readings cover throughput and latency. `window-tick` logs on every
tick inside a window whether it notified, which gives a partial count of inbox notifications. Nothing records how often the owner is
interrupted in the chat, and nothing measures his strain, which the study
measured by self-report.

## What a critic would say

**"This is one person who opened 22 sessions. Run fewer."** Fair, and the cap
is a version of that: no more than three flows reach the owner at once. But
this is n=1 on one machine, and the cap leaves the session count alone, so we
cannot say the budget beats simply running fewer sessions.

**"You answered tool overload with another tool."** The budget exists to cut
interruptions, so a fall in interruptions is the real test. The 48-hour
criterion above measures latency, and the interruption test cannot be run
yet: the `window-tick` log shows the inbox notifications sent inside
windows, and nothing counts the questions that still arrive in the
chat.

**"You feel faster, so you think it works."** In METR's randomised trial,
experienced open-source developers took 19% longer with early-2025 AI tools,
after forecasting that AI would cut their time by 24% and while estimating
afterwards that it had cut it by 20%[^metr]. Our sense that the budget helps
is not evidence, which is why the plan above counts decision age and
throughput.

**"The brain-fry study is self-reported, paywalled, and counts tools."** All
three are true. We cite it through The Decoder and The Register because of
the paywall, and take three from it as a starting value only. No study we
found tests a cap on asking flows.

## Limits and sources

This is one factory with one orchestrator. The session count is the owner's
own count from 28 October, not an instrumented measurement. The research
figures are a single survey of US workers, and they measure simultaneous AI
tools, not agent sessions. The mechanism is described from
the merged pull requests, the skill's documentation and `notice.py` in this
repository, read on 28 October 2026. Questions an agent moves to the chat do
not appear in the load line, so the line can look better than the owner's
day was. Whether the budget reduces the load is not yet known.

[^hbr-brainfry]: Julie Bedard, Matthew Kropp, Megan Hsu, Olivia T. Karaman, Jason Hawes and Gabriella Rosen Kellerman, *When Using AI Leads to "Brain Fry"*, Harvard Business Review, 5 March 2026. [hbr.org](https://hbr.org/2026/03/when-using-ai-leads-to-brain-fry). Primary, paywalled; authors and date read from the article page. The figures in this post come from the coverage below.

[^decoder-brainfry]: Maximilian Schreiner, *Study warns of "AI Brain Fry" as workers hit cognitive limits overseeing AI agents*, The Decoder, 9 March 2026. [the-decoder.com](https://the-decoder.com/study-warns-of-ai-brain-fry-as-workers-hit-cognitive-limits-overseeing-ai-agents/). Secondary (news report of the HBR article). Source of the 14%, 12%, 33% and 39% figures, the strongest-driver finding and the three-tool peak.

[^register-brainfry]: Brandon Vigliarolo, *'AI brain fry' affects employees managing too many agents*, The Register, 9 March 2026. [theregister.com](https://www.theregister.com/2026/03/09/ai_brain_fry_managing_agents). Secondary (news report). Gives the 39% as "self-reported error rates among those who felt they were using too much AI".

[^hbr-intensify]: Aruna Ranganathan and Xingqi Maggie Ye, *AI Doesn't Reduce Work—It Intensifies It*, Harvard Business Review, 9 February 2026. [hbr.org](https://hbr.org/2026/02/ai-doesnt-reduce-work-it-intensifies-it). Primary, paywalled; authors, affiliation and date read from the article page.

[^heise-intensify]: Malte Kirchner, *Study: AI does not make work easier, but more intense*, heise online, 10 February 2026. [heise.de](https://www.heise.de/en/news/Study-AI-does-not-make-work-easier-but-more-intense-11171288.html). Secondary (news report). Source of the study design: eight months, April to December 2025, about 200 employees.

[^metr]: Joel Becker, Nate Rush, Elizabeth Barnes and David Rein, *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity*, arXiv:2507.09089, July 2025. [arxiv.org](https://arxiv.org/abs/2507.09089). Primary (randomised controlled trial). Source of the 19%, the 24% forecast and the 20% estimate, all from the abstract.

---

*This post is part of [PulseEngine](/) — a WebAssembly Component Model engine
for safety-critical systems, with machine-checked proofs for parts of it
(work in progress).*
