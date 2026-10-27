+++
title = "The orchestrator: who does what when bottlenecks won't go away"
description = "Hardware contention, CI queues, decision queues and cross-repo seams stay with us. jess integrates, relay builds the flight stack, gale provides the kernel, and one orchestrator directs the agents across all three. The contracts between them come from real issues."
date = 2026-10-28
draft = true
ready = true
# held 2026-10-27: quotes and tool output need correcting before publication
hold = true
[taxonomies]
tags = ["process", "ai-agents", "orchestration", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**The roles stay while the bottlenecks move.** jess integrates and owns the
ladder from simulation to silicon. relay builds the flight stack. gale
provides the kernel underneath.

Behind the agents working on those repos sits one **orchestrator**, who
enables them, reviews their output and makes the decisions the oracles cannot.
The interfaces between the repos are contracts, and the clearest ones are
written down in issues.
{% </insight> %}

[The first post](/blog/safe-was-built-for-slow-humans/) argued that the
bottleneck in an agent factory is verification and decisions, not generation.
[The second post](/blog/can-we-deliver-x-by-january/) showed how to estimate
from gates and flow history. This one is about who does what: the repos, the
agents and the orchestrator who directs them, and the contracts that keep the
repos from colliding.

## The roles

Three repos carry the drone work. Each has one job and owns the bottleneck
that comes with it.

{% <mermaid> %}
flowchart TB
    gale["<b>gale</b><br/>KERNEL<br/>OS primitives<br/>silicon bring-up"]
    relay["<b>relay</b><br/>FLIGHT STACK<br/>control cascade<br/>as wasm components"]
    jess["<b>jess</b><br/>INTEGRATOR<br/>release watch<br/>ladder: sim → silicon"]

    gale -->|"kernel underneath"| relay
    relay -->|"flight components"| jess

    style jess fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style relay fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
    style gale fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed
{% </mermaid> %}

| Role | Repo | What it does | The bottleneck it owns |
|---|---|---|---|
| **Integrator** | jess | Hardware integration, release watch, the **ladder** from simulation to silicon | Hardware availability, release timing |
| **Flight stack** | relay | The control cascade, published as wasm components | Simulation fidelity, the HITL seam |
| **Kernel** | gale | The OS primitives and their proofs (work in progress) | Proof effort, silicon bring-up |

"Integrator" means you integrate, you watch the release, and you own the
ladder: the deployment path from simulation to silicon, one rung at a time.
relay builds the flight stack on top of gale. jess takes relay's components
onto hardware, and the ladder in
[jess#264](https://github.com/pulseengine/jess/issues/264) splits the work
that way: relay owns rung 1 in simulation, and the lowering to the target is
jess's rung. A delay at the bottom of that chain shows up
at the top.

Fix the hardware bottleneck and the CI queue becomes the bottleneck. Add
runners and the decision queue is next. None of that changes who integrates,
who builds the flight stack and who provides the kernel.

## The skills are the process

The agents work from **skills**: procedures defined in this repository's
plugin. Each one says when it fires, which steps to follow, which gates to
pass and when to stop and ask the orchestrator.

| Skill | Pattern | Cadence |
|---|---|---|
| `issue-hunt` | Incremental bug/feature hunt over the issue tracker | 6-hour cron loop |
| `gate-potency` | Audit whether CI checks can still fail (the first post's gate-potency metric) | Before a release |
| `oracle-gate-a-change` | Wire a mechanical check before merging | Per change |
| `pulseengine-feature-loop` | End-to-end feature: spar → rivet → code → witness → sigil | Per feature |
| `release-planning` | Plan what lands in a release and drive toward it | Per release |
| `clean-room-verification` | A fresh-context subagent validates findings | Before reporting |
| `report-tool-friction` | File an issue when a tool errors, lacks a capability or forces a workaround | When friction is noticed |

My part is to direct, trigger, review and decide. I tell the pulseengine.eu
agent which skills to write or update, start the loops on a 6-hour cron, read
the reports and gates that come back, and clear the decision queue. Between
triggers the agents file issues, fix bugs, run the gates and open PRs without
me.

## The orchestrator

I am the **orchestrator**, and in this factory also the **owner**: there is no
Scrum master and no product owner. One owner today does not contradict [the
estimation post](/blog/can-we-deliver-x-by-january/), whose 6 to 11 humans
for relay come from relay's release rate and its decision backlog; that
formula is for scaling the factory, and one person is where it starts.

The pattern is that I enable and the agents do. I do not write the skills,
because the pulseengine.eu agent writes them on my instruction. I do not
install the bench tools; the agents install `with-device` and configure varve
layers themselves. I do plug in the boards and the cables. The main job is
**prioritization** across three streams that compete for my attention:

| Stream | What it looks like | Example (my own instructions to the agents) |
|---|---|---|
| **Friction** | Tools that don't work, workarounds, things that slow agents down | "I did not intend to create these layers to have to maintain them manually — either automated or I get an email with direct approval" |
| **Factory operations** | Cron jobs, CI, hardware, queues | "reestablish the cron job — had to restart the agent and it got lost" |
| **Real decisions** | Architecture direction, what to build next, what to merge | "yes these measurements we need to do" / "plan for the next varve release to support Zephyr, WASI, Yocto SDKs" |

Friction reports pile up from `report-tool-friction`. Cron jobs die when an
agent restarts, boards get unplugged, and CI queues back up. The decisions
need judgment about direction, priority and what to merge.

Edward de Bono's *Six Thinking Hats* gives a vocabulary for switching between
these modes[^thinking-hats]. Friction is the black hat (the negative,
evaluation), factory operations the blue hat (the big picture and managing,
with tools such as FIP, First Important Priorities), and real decisions the
green hat (new ideas). His hat sequences begin and end with blue, which is
also how my cycle runs:

{% <mermaid> %}
flowchart LR
    blue1["Blue<br/>factory status"]
    black["Black<br/>friction reports"]
    green["Green<br/>what to build"]
    blue2["Blue<br/>FIP: what first?"]
    blue1 --> black --> green --> blue2
    blue2 -.->|"next cycle"| blue1
    style blue1 fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style blue2 fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed
    style black fill:#1a1d27,stroke:#f87171,color:#e1e4ed
    style green fill:#1a1d27,stroke:#4ade80,color:#e1e4ed
{% </mermaid> %}

The concrete architecture work I do myself is small. I ask "what should I do
on pulseengine-layers?" and the agents work out the options; I review, correct
and choose. This is the role table from the first post in practice: the coder
becomes the orchestrator, and the scarce resource moves from code production
to prioritization. The WIP limit on the decision queue caps how many decisions
can wait, and I prioritize inside that cap.

{% <note kind="tip"> %}
**The title stayed; the work moved.** My own path ran from engineer writing
software, through software architect, system architect and team lead, to
product owner and Scrum master, which are the SAFe roles. Today my title is
Distinguished Engineer, and I help decide how things are done: architecture,
approach, design. The amount of architecture I personally have to provide is
shrinking. The agents produce the first draft, and I decide where my expertise
still matters, learning formal methods and new verification techniques along
the way to keep that judgment sharp.
{% </note> %}

## Resource constraints and the critical path

The factory runs on limited resources: memory and disk on the build hosts, a
runner queue that backs up, a handful of physical boards, and GitHub outages
that stop every agent at once. Scarcity is what makes oversight necessary,
because someone has to decide who gets what.

| Question | What it means |
|---|---|
| **Who has a need?** | Which agent or repo needs which resource: memory, disk, a runner, a board |
| **What is the critical path?** | The longest chain of dependent gates, which sets the minimum release time |
| **Is it properly queued?** | Whether the critical path is at the front of the queue or behind non-critical work |

If jess is waiting on relay and relay on gale, gale's jobs go to the front of
the runner queue, gale gets the board, and gale's decisions are cleared first.
When GitHub is down, the agents cannot file issues, open PRs or run CI, and
the decision is whether to wait or switch to work that does not need GitHub.

To see the queue, the agents use a CI status service through the `ci-status`
skill. For a queued job it returns a measured range for when the job will
**start**, derived from how long recent jobs in the same runner pool waited,
and it flags a job as `overdue` once it has waited longer than 90% of them.
It gives no finish forecast for running jobs, and the skill tells the agent
not to invent one.

### Hardware: one board, many agents

Physical hardware is where collisions are silent. In
[gale#356](https://github.com/pulseengine/gale/issues/356) the jess agent
warned that jess and gale were very likely about to share one STLINK-V3 board,
next to the single Pixhawk 6X-RT, and that two agents driving one debug probe "fails as a corrupted
session that looks like a hardware fault". jess measured the tty case on a
Pixhawk: one reader alone received 66,872 bytes in 5 seconds, two readers
together 37,787 and 40,053 bytes, each roughly half, and neither saw an error.

jess's answer is [`with-device`](https://github.com/pulseengine/jess/tree/main/tools/bench/with-device),
a zero-dependency Rust tool. A claim is an OS `flock(2)` held for exactly the
lifetime of the wrapped command, so there are no claim or release verbs and
no stale lock to clean up after a crash: when the holder dies, the kernel
drops the lock. Its usage line is
`with-device <device>... [--purpose <text>] [--wait <seconds>] -- <command>...`,
and several devices are taken in sorted order with no hold-and-wait, so the
order you list them in cannot deadlock. gale#356 was closed on 21 October 2026
as delivered: with-device 0.2.2 is carried in gale's varve pin, and gale's
silicon xtask routes probe attach through it.

Here is a run of with-device 0.5.0, built from jess `main`, against a dummy
two-device registry and a scratch lock directory (the pid is replaced):

```text
$ BENCH_WHO=jess with-device pixhawk-6xrt --purpose "hitl smoke" -- sleep 4 &

$ with-device --status
  pixhawk-6xrt       CLAIMED {"who":"jess","pid":<pid>,"purpose":"hitl smoke"}
  stlink-v1          free

$ BENCH_WHO=gale with-device pixhawk-6xrt --purpose flash -- true
DEVICE BUSY: 'pixhawk-6xrt' is claimed — {"who":"jess","pid":<pid>,"purpose":"hitl smoke"}
Nothing was run.
$ echo $?
3
```

The status shows who holds a device and why, and nothing about since when or
for how long. Exit code 3 means busy and nothing ran. A lock file that cannot
even be opened exits 4 instead, a distinction added after a permissions
error on the lock directory had rendered every device as claimed.

## Building your own tools

When a tool sits on the critical path and causes friction every day, building
a replacement can be cheaper than working around it.

Anthropic did this with source control. Their article reports that "In May
2026, Anthropic averaged around 2,500 code changes merged per day; as of
September, we merged over 30,000 per day." The history of their main branch
alone is almost 100 GB, and they perform on the order of 25 million checkouts
per day for CI; fetched naively, the article says, that would be over 600 PB
of git traffic per day. Git's distributed, offline-first design is right for
most repositories, but "As our monorepo grows, it increasingly doesn't fit
that design space." They built
[Scion](https://www.anthropic.com/research/redesigning-source-control) and
migrated their monorepo from git in five months[^anthropic-scion]. In their
words: "Claude's ability to write code was both what put us in this situation
in the first place and how we were able to quickly build a high-quality,
scalable system to deal with it."

We built [ordeal](https://github.com/pulseengine/ordeal), a
certificate-checked QF_BV SMT solver in pure Rust with no external
dependencies, which also runs as a `wasm32-wasip2` component. The solver
itself is untrusted. Its answers are re-checked by `ordeal-lrat`, a small
checker whose Rust source is translated to Lean 4 with Aeneas and proven
sound, and the lowering from the term DAG to CNF is proven too. Everything
above the DAG (building it from the terms, rewriting, the front ends) is, in
the README's words, "defended by tests and by a differential against Z3, not
by proof". Z3 stays in development as that differential.

| Existing tool | What we needed | Our tool | Status |
|---|---|---|---|
| Git (Anthropic's case) | Over 30,000 merges/day, a main-branch history near 100 GB | Scion | Migrated in five months |
| Z3 | Answers we can re-check without trusting the solver | ordeal | Checker and DAG→CNF lowering proven in Lean 4; the layers above tested |
| gcov / llvm-cov | MC/DC on Wasm components (llvm-cov reports MC/DC for native code built with clang's `-fcoverage-mcdc`) | witness | MC/DC-style branch coverage for WebAssembly components |
| serde_yaml | A maintained, schema-driven YAML layer | rivet-yaml | Replaced in the rivet workspace; the separate `compose-witness` crate still uses serde_yaml |
| Manual traceability | Links that a build can check | rivet | Git-native, schema-driven |

Friction is the input to that decision. The `report-tool-friction` skill fires
the moment an agent notices itself working around a tool instead of with it,
and the report lands in that tool's repo. The toolchain itself was grown this
way: meld fuses components, loom optimizes them, synth transcodes them to
native code, kiln is the interpreter and runtime, and sigil signs. All of it
is work in progress.

## Contracts between the stations

A contract is the agreed interface at a seam between two repos. Four of them
are written down in the issue trackers, and each one says which side owns
what.

### HAL contract ([jess#62](https://github.com/pulseengine/jess/issues/62))

> **relay owns the hardware ABSTRACTION**: the bus/peripheral seam *traits*
> (SPI/I2C/UART/PWM/ADC/CAN) [...]
>
> **jess owns the BINDING to real silicon**: concrete impls of those seams
> over the i.MX RT1176 peripherals [...]
>
> Seam in the middle = the thin agreed interface. relay can't break it without
> telling jess; jess can swap silicon under it without touching the flight
> stack.

The two sides hold different things. relay owns the stability promise of the
seam: it may not change a trait without telling jess. jess owns the binding to
silicon and can replace it freely as long as the traits hold. The issue's seam
inventory lists `RegBus` as existing on the relay side but duplicated across
two crates, and `AdcIn`, `PwmOut`, `SerialBus` and `CanBus` as still to be
added.

### Consumption contract ([jess#167](https://github.com/pulseengine/jess/issues/167))

> `falcon-flight` is now a published, cosign-signed WASM OCI component on
> ghcr + indexed on wasm.directory [...]. But what's published today is a
> **sealed demo** [...] Nothing real crosses the boundary.

The issue then puts the shape of the seam to jess as a choice between two
options: a per-cycle `step(sensor-sample) -> actuator-cmd` that is
synchronous and mirrors `FlightCore::step`, or P3 `stream<sensor-sample> ->
stream<actuator-cmd>`, which is relay-native and composable. jess's first reply
on 23 July proposed "both, layered": a synchronous `step` per partition window
at the core boundary, with stream composition inside each bundle. The issue is
still open. On 21 October relay announced that the calibration shape is
decided on its side (`configure-calibration` on the `pilot` interface,
relay#586) and left the calibration's fields open to jess, alongside two
earlier questions: where `battery-v` lives, and the sign of `cruise-alt`.

### HITL wire binding ([relay#572](https://github.com/pulseengine/relay/issues/572))

The binding's own source comment, quoted in the issue, says the 76-byte sensor
payload "carries no heading, no rotor RPM, and no battery that says ABSENT".
That was harmless while the published component wrapped `FlightCore`. With
[relay#571](https://github.com/pulseengine/relay/pull/571), the PR that makes
the published component wrap `FlightSupervisor`, it is not:

> A HITL host can only supply what the wire frame carries, and the frame has
> no battery element — so `battery_v` is `None` by construction, not by
> oversight.

The issue credits @cpetig with predicting the gap on jess#167 six days before
#571 existed. A follow-up comment on 15 October corrected the issue's
"cannot arm it": a host that warms its estimator first is refused earlier, by
the calibration check, because the seam carries no calibration either. The
maintainer decided on 21 October to add a battery element with an explicit
ABSENT validity bit rather than a 0.0 sentinel, and relay told jess on jess#167
the same day that the decoder offsets for the sensor frame will change.

### Interface identity ([relay#589](https://github.com/pulseengine/relay/issues/589))

> falcon-ekf (legacy Mahony) and falcon-iekf export the identical
> ekf@0.11.0 interface — a consumer cannot tell the flight estimator from the
> legacy one
>
> jess has closed it on *their* side with `tools/deps/check-estimator-identity.sh`
> (a pin-identity guard with five negative controls).

The first line is the issue's title. jess found this as the integrator, in
[jess#293](https://github.com/pulseengine/jess/pull/293). The issue offered
three options: stop publishing `falcon-ekf`, give it a distinct identity, or
annotate it. The maintainer decided on 21 October 2026 to stop publishing
`falcon-ekf`, implemented in
[relay#590](https://github.com/pulseengine/relay/pull/590), and announced the
removal to jess on jess#167 before any tag carried it.

### What the four have in common

| Contract | relay owns | jess owns | Issue |
|---|---|---|---|
| **HAL** | The seam traits and the promise not to break them silently | The binding to RT1176 silicon | jess#62 |
| **Consumption** | The published flight components and their WIT | Fusing, lowering and signing per core; calibration fields, `battery-v`, `cruise-alt` | jess#167 |
| **HITL wire** | The sensor-frame layout, now gaining a battery element with ABSENT | Its decoder, whose offsets change | relay#572 |
| **Interface identity** | One exporter per interface; `falcon-ekf` no longer published | The pin-identity guard | relay#589 |

Two of the four surfaced on the jess side. jess's pin guard caught the
confusable estimators, and @cpetig predicted the missing battery element in a
comment on jess#167 before relay's PR existed. The integrator sees the seams
first because it is the first consumer of every one of them. The contracts
also travel in both directions as announcements: relay#589 and relay#572 were
both announced on jess#167 before any release carried them.

The ladder in [jess#264](https://github.com/pulseengine/jess/issues/264) shows
where the work stands. Rung 1, relay's, is done: the composed wasm cascade and
the same crates built natively are "BIT-IDENTICAL across 2000 ticks". Rungs 2 to
4 belong to jess. The issue is explicit that rung 1 is easy to over-read: the
shipped components wrap the older PID cascade rather than the controller
`falcon-core` flies, and nothing at rung 1 has been lowered to the target.

## The control tower

The orchestrator needs one view of the whole factory: the gates, the runner
queue, the critical path, the boards and the outages. We are building that
view as [**warte**](https://github.com/pulseengine/warte) (German for a lookout
tower, and also the imperative of "wait", as in "bitte warte auf mich"). The repo is public and has
twelve releases, v0.1.0 to v1.2.0, published on 26 and 27 October 2026.

| View | What it shows | Where the pattern comes from |
|---|---|---|
| **Overview** | All repos, all gates, green/red/pending | First post: gates |
| **Ask** | When a queued job will start, from measured waits | Second post: estimation |
| **Queue** | Runner pools, waiting jobs, hardware availability | This post: resources |
| **Critical path** | The longest chain of dependent gates | Second post: critical path |
| **Outages** | GitHub status, fleet health | This post: outages |

warte is built the same way as the other tools, by agents working from the
skills; today the agents still read the queue through the `ci-status` skill
and its CI status service. Nothing in the pattern is specific to our stack; any CI
system can expose the same data.

The model also repeats per domain. jess is the integrator for the drone
software. wohl, the home-supervision system built on PulseEngine, has its own
issues, CI and gates, and will probably need its own integrator and its own
critical path. One control tower can show both.

## What to take from this

**Name the roles.** "Integrator" describes a responsibility: who integrates,
who watches the release, who owns the ladder. Write it down where the agents
read it.

**Write the contract into the issue, with owners.** jess#62 works because it
says which side owns the promise and which owns the binding. jess#167 is useful
because it puts concrete options to the other side and records the answer.

**Expect downstream to find upstream bugs.** The integrator is the first
consumer of every seam, so it feels the bottlenecks first. Give it a channel,
and announce changes there before a release carries them.

**Bottlenecks will stay.** Hardware contention, CI queues, decision queues and
cross-repo seams can be managed and moved, and with-device, the CI status
service and the decision-queue WIP limit are how we manage them today.

## Limits

This is one factory: three repos in the drone stack, one orchestrator, and
seams that are still being defined. It has not been tried in a larger
organisation with more layers and more people. The claim is that the roles are
clear and the bottlenecks are managed, not that this is the only way to
structure a factory.

The issue numbers, quotes and decisions are from the GitHub issue trackers,
read on 27 October 2026. The interpretation, that clear roles and written
contracts keep the bottlenecks manageable, is the author's view, not a measured
outcome.

## Sources and caveats

The roles are from the author's own repositories (pulseengine/jess,
pulseengine/relay, pulseengine/gale). The with-device output was produced by
building the tool from jess `main` and running it against a dummy registry; it
touched no hardware.

[^anthropic-scion]: Anthropic, *Redesigning source control at Anthropic*, 13 October 2026. [anthropic.com/research/redesigning-source-control](https://www.anthropic.com/research/redesigning-source-control). Primary (company research publication). The article reports around 2,500 merges per day in May 2026 and over 30,000 per day in September, a main-branch history of almost 100 GB, and on the order of 25 million CI checkouts per day, which "Fetched naively, that would be over 600 PB of git traffic per day." The 600 PB figure is a counterfactual for naive fetching, not measured traffic.

[^thinking-hats]: Edward de Bono, *Six Thinking Hats*, 1985. Summary via [Wikipedia](https://en.wikipedia.org/wiki/Six_Thinking_Hats). Tertiary (encyclopedia summary of the original book). The hat descriptions, the FIP tool and the statement that sequences begin and end with a blue hat are taken from that summary.

---

*This is the last post in the arc. The series: [SAFe was built for slow humans](/blog/safe-was-built-for-slow-humans/) → [Can we deliver X by January?](/blog/can-we-deliver-x-by-january/) → [The orchestrator: who does what](/blog/the-orchestrator-who-does-what/).*

---

*This post is part of [PulseEngine](/) — a WebAssembly Component Model engine
for safety-critical systems, with formally verified components (work in
progress). Recent posts:
[SAFe was built for slow humans](/blog/safe-was-built-for-slow-humans/),
[Can we deliver X by January?](/blog/can-we-deliver-x-by-january/),
[The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/).*
