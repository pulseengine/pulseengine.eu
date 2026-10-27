+++
title = "The orchestrator: who does what when bottlenecks won't go away"
description = "Hardware contention, CI queues, decision queues and cross-repo seams stay with us. jess integrates, relay builds the flight stack, gale provides the kernel, and one orchestrator directs the agents across all three. The contracts between them come from real issues."
date = 2026-10-28
draft = true
ready = true
[taxonomies]
tags = ["process", "ai-agents", "orchestration", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**Three repos, one orchestrator, four seams written down as contracts.**
jess integrates, relay builds the flight stack, gale provides the kernel.
Across the four contracts, jess's pin guard found one break that relay had
shipped (jess#293), and relay announced its two seam changes of 21 October
on jess#167 before a release carried them.
{% </insight> %}

This arc began with [The machine arrived before the
factory](/blog/the-machine-arrived-before-the-factory/) and [Agents don't tidy
up](/blog/agents-dont-tidy-up/). [SAFe was built for slow
humans](/blog/safe-was-built-for-slow-humans/) argued that the bottleneck in an
agent factory is verification and decisions, and [Can we deliver X by
January?](/blog/can-we-deliver-x-by-january/) estimated from gates and flow
history. This post is about who does what: the repos, the contracts between
them, and the one person who directs the agents.

## The roles

| Role | Repo | What it does | The bottleneck it owns |
|---|---|---|---|
| **Integrator** | jess | Hardware integration, release watch, the **ladder** from simulation to silicon | Hardware availability, release timing |
| **Flight stack** | relay | The control cascade, published as wasm components | Simulation fidelity, the HITL seam |
| **Kernel** | gale | The OS primitives and their proofs (work in progress) | Proof effort, silicon bring-up |

relay builds on gale and jess takes relay's components onto hardware, so a
delay at the bottom of that chain shows up at the top while the roles
themselves stay put.

## Contracts between the repos

A contract is the agreed interface at a seam between two repos. Four of them
are written down in the issue trackers, and each says which side owns what.

### HAL contract ([jess#62](https://github.com/pulseengine/jess/issues/62))

> **relay owns the hardware ABSTRACTION**: the bus/peripheral seam *traits*
> (SPI/I2C/UART/PWM/ADC/CAN) [...]
>
> **jess owns the BINDING to real silicon**: concrete impls of those seams
> over the i.MX RT1176 peripherals [...]
>
> Seam in the middle = the thin agreed interface. relay can't break it without
> telling jess; jess can swap silicon under it without touching the flight
> stack. [...]

The two sides hold different things. relay owns the stability promise of the
seam: it may not change a trait without telling jess. jess owns the binding to
silicon and can replace it as long as the traits hold. The seam inventory in
the issue body dates from June and has moved since: the two sides agreed to
anchor the seams on `embedded-hal-async` and `embedded-io-async` in place of
the bespoke `RegBus` and `SerialBus`, and by falcon v1.85 relay-hal had shipped
`PwmOut` and `AdcIn` as well.

### Consumption contract ([jess#167](https://github.com/pulseengine/jess/issues/167))

> `falcon-flight` is now a published, cosign-signed WASM OCI component on
> ghcr + indexed on wasm.directory [...]. But what's published today is a
> **sealed demo** [...] Nothing real crosses the boundary.

The issue put the shape of the seam to jess as two options: a synchronous
per-cycle `step(sensor-sample) -> actuator-cmd` that mirrors
`FlightCore::step`, or P3 `stream<sensor-sample> -> stream<actuator-cmd>`.
jess's first reply on 23 July proposed "both, layered": a synchronous `step`
per partition window at the core boundary, with stream composition inside each
bundle. The issue is still open. On 21 October relay decided the calibration
shape on its side (`configure-calibration` on the `pilot` interface,
relay#586) and left the calibration's fields to jess, alongside two earlier
questions: where `battery-v` lives, and the sign of `cruise-alt`.

### HITL wire binding ([relay#572](https://github.com/pulseengine/relay/issues/572))

The binding's source comment, quoted in the issue, says the 76-byte sensor
payload "carries no heading, no rotor RPM, and no battery that says ABSENT".
That was harmless while the published component never read a battery. With
[relay#571](https://github.com/pulseengine/relay/pull/571), the PR that makes
the published component wrap `FlightSupervisor`, it matters:

> A HITL host can only supply what the wire frame carries, and the frame has
> no battery element — so `battery_v` is `None` by construction, not by
> oversight.

relay's own 9 October comment on jess#167 had already flagged the gap, six
days before relay#571. A follow-up on 15 October corrected the issue's
"cannot arm it": a host that warms its estimator first is refused earlier, by
the calibration check, because the seam carries no calibration either. On 21
October the maintainer decided to add a battery element with an explicit
ABSENT validity bit rather than a 0.0 sentinel, which changes jess's decoder
offsets for the sensor frame.

### Interface identity ([relay#589](https://github.com/pulseengine/relay/issues/589))

The issue's title, then a line from its body:

> falcon-ekf (legacy Mahony) and falcon-iekf export the identical
> ekf@0.11.0 interface — a consumer cannot tell the flight estimator from the
> legacy one
>
> [...]
>
> jess has closed it on *their* side with `tools/deps/check-estimator-identity.sh`
> (a pin-identity guard with five negative controls).

The five controls listed in [jess#293](https://github.com/pulseengine/jess/pull/293),
the PR that found the problem, are one positive control and four negative
ones. The maintainer decided on 21 October 2026 to stop publishing
`falcon-ekf`, implemented in
[relay#590](https://github.com/pulseengine/relay/pull/590).

### What the four have in common

| Contract | relay owns | jess owns | Issue |
|---|---|---|---|
| **HAL** | The seam traits and the promise not to break them silently | The binding to RT1176 silicon | jess#62 |
| **Consumption** | The published flight components and their WIT | Fusing, lowering and signing per core; calibration fields, `battery-v`, `cruise-alt` | jess#167 |
| **HITL wire** | The sensor-frame layout, gaining a battery element with ABSENT | Its decoder, whose offsets change | relay#572 |
| **Interface identity** | One exporter per interface; `falcon-ekf` no longer published | The pin-identity guard | relay#589 |

One of the four surfaced on the jess side: jess's pin guard caught the
confusable estimators (jess#293). The integrator is the first consumer of
every seam, so it tends to see breaks first. jess#167 is also the channel
going the other way: relay announced both the `falcon-ekf` removal and the
battery element there before any release carried them.

The ladder in [jess#264](https://github.com/pulseengine/jess/issues/264)
shows where the work stands. Rung 1 is relay's, and when the issue was filed
on 10 September it reported the composed wasm cascade and the same crates
built natively as "BIT-IDENTICAL across 2000 ticks". That measurement was
taken against the older five-stage PID cascade; relay#393 made the component
wrap `FlightCore` the next day, and relay#571 (merged 23 October) wraps
`FlightSupervisor`. Rungs 2 to 4, from gust and Gazebo down to native code on
the hardware and real sensors, belong to jess, and nothing at rung 1 was
lowered to the target.

## The orchestrator

I am the **orchestrator**, and in this factory also the **owner**: there is no
Scrum master and no product owner. One owner today does not contradict [the
estimation post](/blog/can-we-deliver-x-by-january/), whose 6 to 11 humans
for relay come from relay's release rate and its decision backlog; that
formula is for scaling the factory, and one person is where it starts.

I enable and the agents do. The agents work from **skills**, procedures in
the pulseengine-claude plugin in the pulseengine.eu repository, and the
pulseengine.eu agent writes and updates them on my instruction. The agents
install the bench tools themselves; I plug in the boards and the cables.

| Skill | Pattern | Cadence (as I run it) |
|---|---|---|
| `issue-hunt` | Incremental bug/feature hunt over the issue tracker | 6-hour cron loop |
| `gate-potency` | Audit whether CI checks can still fail | Before a release |
| `oracle-gate-a-change` | Wire a mechanical check before merging | Per change |
| `pulseengine-feature-loop` | End-to-end feature: spar → rivet → code → witness → sigil | Per feature |
| `clean-room-verification` | A fresh-context subagent validates findings | Before reporting |
| `report-tool-friction` | File an issue when a tool errors, lacks a capability or forces a workaround | When friction is noticed |

Between triggers the agents file issues, fix bugs, run the gates and open PRs.
My main job is **prioritization** across three streams that compete for my
attention:

| Stream | What it looks like | Example (my own instructions to the agents) |
|---|---|---|
| **Friction** | Tools that don't work, workarounds, things that slow agents down | "I did not intend to create these layers to have to maintain them manually — either automated or I get an email with direct approval" |
| **Factory operations** | Cron jobs, CI, hardware, queues | "reestablish the cron job — had to restart the agent and it got lost" |
| **Real decisions** | Architecture direction, what to build next, what to merge | "yes these measurements we need to do" / "plan for the next varve release to support Zephyr, WASI, Yocto SDKs" |

In de Bono's terms these are the black, blue and green hats, and like his
sequences my cycle starts and ends with blue, deciding what comes
first[^thinking-hats]. The architecture work I do myself is small: I ask "what
should I do on pulseengine-layers?", the agents work out the options, and I
review, correct and choose. The decision-queue ratchet is merged but not yet
armed; until it is, I enforce the cap by hand.

{% <note kind="tip"> %}
My path ran from engineer through architect, team lead, product owner and
Scrum master to Distinguished Engineer, and the amount of architecture I
personally provide is shrinking as the agents write the first drafts. What
remains is deciding where my expertise still matters, and learning formal
methods and new verification techniques to keep that judgment sharp.
{% </note> %}

## Resource constraints and the critical path

The factory runs on limited resources: memory and disk on the build hosts, a
runner queue that backs up, a small bench of physical boards, and GitHub
outages that stop every agent at once. Scarcity is what makes oversight
necessary. If jess is waiting on relay and relay on gale, gale's jobs go to
the front of the runner queue, gale gets the board, and gale's decisions are
cleared first. When GitHub is down, the decision is whether to wait or switch
to work that does not need it.

To see the queue, the agents use a CI status service through the `ci-status`
skill. For a queued job it returns a measured range for when the job will
**start**, derived from how long recent jobs in the same runner pool waited,
and flags it `overdue` once it has waited longer than 90% of them. It gives no
finish forecast for running jobs, and the skill tells the agent not to invent
one.

### Hardware: one board, many agents

jess's device registry lists one real board, a Pixhawk 6X-RT, and one
synthetic device used by the self-test. In gale#356 the jess agent warned
that jess and gale were very likely about to share a NUCLEO-G474RE on an
STLINK-V3 probe, and that two agents driving one probe "fails as a corrupted
session that looks like a hardware fault". The same thread records a tty
measurement on the Pixhawk: one reader alone received 66,872 B in 5.0 s, and
two readers together 37,787 B and 40,053 B, about 57% and 60% of the solo
count, with no error on either side.

jess's answer is [`with-device`](https://github.com/pulseengine/jess/tree/main/tools/bench/with-device),
a zero-dependency Rust tool. A claim is an OS `flock(2)` held for exactly the
lifetime of the wrapped command, so there are no claim or release verbs and
nothing to clean up after a crash: when the holder dies, the kernel drops the
lock. The usage line is
`with-device <device>... [--purpose <text>] [--wait <s>] -- <command>...`,
and several devices are taken in sorted order with no hold-and-wait, so the
order you list them in cannot deadlock. gale#356 was closed on 21 October 2026
as delivered, with with-device 0.2.2 carried in gale's varve pin.

Here is a run of with-device 0.5.0, built from jess `main`, against a dummy
two-device registry and a scratch lock directory (the pid is replaced).
`--status` lists only devices that have a lock file, so `stlink-v1` appears
because it was claimed once and released:

```text
$ BENCH_WHO=jess with-device pixhawk-6xrt --purpose "hitl smoke" -- sleep 4 &
$ with-device stlink-v1 -- true

$ with-device --status
  pixhawk-6xrt       CLAIMED {"who":"jess","pid":<pid>,"purpose":"hitl smoke"}
  stlink-v1          free

$ BENCH_WHO=gale with-device pixhawk-6xrt --purpose flash -- true
DEVICE BUSY: 'pixhawk-6xrt' is claimed — {"who":"jess","pid":<pid>,"purpose":"hitl smoke"}
Nothing was run.
$ echo $?
3
```

The status shows who holds a device and why, and nothing about since when.
Exit code 3 means busy and nothing ran. A lock file that cannot even be opened
exits 4 instead, a distinction added after a permissions error on the lock
directory had rendered every device as claimed.

## Building your own tools

Anthropic replaced git with an in-house system, Scion, after merges grew from
around 2,500 per day in May 2026 to over 30,000 per day in September. In their
words, "Claude's ability to write code was both what put us in this situation
in the first place and how we were able to quickly build a high-quality,
scalable system to deal with it"[^anthropic-scion].

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
| Z3 | Answers we can re-check without trusting the solver | ordeal | Checker and DAG→CNF lowering proven in Lean 4; the layers above tested |
| gcov / llvm-cov | MC/DC on Wasm components (both report MC/DC for native code: GCC 14 `-fcondition-coverage`, clang `-fcoverage-mcdc`) | witness | MC/DC-style branch coverage for WebAssembly components |
| serde_yaml | A maintained, schema-driven YAML layer | rivet-yaml | Replaced in the rivet workspace; the separate `compose-witness` crate still uses serde_yaml |

Friction is the input to the build decision: build when the tool is on the
critical path and the workaround costs more than the tool would. The `report-tool-friction`
skill fires the moment an agent notices itself working around a tool instead
of with it, and the report lands in that tool's repo. The tools themselves
were grown this way: meld fuses components, loom optimizes them, synth
transcodes them to native code, kiln is the interpreter and runtime, and sigil
signs. All of it is work in progress.

## The control tower

The orchestrator needs one view of the gates, the runner queue, the critical
path, the boards and the outages. We are building it as
[**warte**](https://github.com/pulseengine/warte) (German for a lookout tower,
and also the imperative of "wait"). The repo is public; its twelve tagged
releases, v0.1.0 to v1.2.0, went out on 26–27 October, and most of the
planned views (overview, ask, queue, critical path, resources, outages) are
still open issues. Until they land, the agents read the queue through the
`ci-status` skill.

## What to take from this

**Write the contract into the issue, with owners.** jess#62 says which side
owns the promise and which owns the binding, and jess#167 puts concrete options
to the other side and records the answer.

**Give downstream a channel.** The integrator is the first consumer of every
seam, so it feels breaks first and is the right place to announce changes.

## Limits and sources

This is one factory: three repos in the drone stack, one orchestrator, and
seams that are still being defined. It has not been tried in a larger
organisation. The issue numbers, quotes and decisions are from the GitHub
issue trackers (pulseengine/jess, pulseengine/relay, pulseengine/gale), read
on 27 October 2026. The with-device output came from building the tool from
jess `main` and running it against a dummy registry, without hardware. The
interpretation, that clear roles and written contracts keep the bottlenecks
manageable, is the author's view, not a measured outcome.

[^anthropic-scion]: Anthropic, *Redesigning source control at Anthropic*, 13 October 2026. [anthropic.com/research/redesigning-source-control](https://www.anthropic.com/research/redesigning-source-control). Primary (company research publication). The article also reports a main-branch history of almost 100 GB and on the order of 25 million CI checkouts per day, which "Fetched naively, that would be over 600 PB of git traffic per day", a counterfactual for naive fetching rather than measured traffic.

[^thinking-hats]: Edward de Bono, *Six Thinking Hats*, 1985. Summary via [Wikipedia](https://en.wikipedia.org/wiki/Six_Thinking_Hats). Tertiary (encyclopedia summary of the original book). The hat descriptions and the statement that sequences begin and end with a blue hat are taken from that summary.

---

*This post is part of [PulseEngine](/) — a WebAssembly Component Model engine
for safety-critical systems, with machine-checked proofs for parts of it
(work in progress).*
