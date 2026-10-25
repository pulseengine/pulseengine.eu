+++
title = "The orchestrator: who does what when bottlenecks won't go away"
description = "Bottlenecks will always exist — hardware contention, CI queues, decision queues, cross-repo dependencies. But the principle is clear: jess orchestrates, relay flies, gale provides the kernel. The roles don't move. The bottlenecks do."
date = 2026-10-30
draft = true
ready = true
[taxonomies]
tags = ["process", "ai-agents", "orchestration", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**Bottlenecks will always exist. But the principle — who does what — is
clear.** jess orchestrates. relay flies. gale provides the kernel. The
bottlenecks move — hardware contention, CI queues, decision queues,
cross-repo dependencies. The roles don't. The factory is not a hierarchy.
It is a set of roles, each with a clear job, connected by contracts.
{% </insight> %}

[The first post](/blog/safe-was-built-for-slow-humans/) argued that the
bottleneck in an agent factory is not generation — it is verification and
decisions. [The second post](/blog/can-we-deliver-x-by-january/) showed how
to estimate from gates and flow history. This post is about the people: who
does what, and why the roles are clear even when the bottlenecks are not.

## The roles

Three repos, three roles, one factory:

| Role | Repo | What they do | The bottleneck they own |
|---|---|---|---|
| **Orchestrator** | jess | Hardware integration, release watch, the ladder from sim to silicon | Hardware availability, release timing |
| **Flight stack** | relay | The control cascade, the verified flight software | Simulation fidelity, HITL binding |
| **Kernel** | gale | The verified OS primitives, the foundation | Formal proofs, silicon bring-up |

The names are not labels. They are **principles**. "Orchestrator" means: you
integrate, you watch the release, you own the ladder. "Flight stack" means:
you fly, you verify, you ship the cascade. "Kernel" means: you provide the
primitives, you prove them, you're the foundation.

## The dependency chain

```
gale (kernel) → relay (flight stack) → jess (orchestrator)
```

gale provides the verified kernel primitives. relay builds the flight stack
on top of gale. jess integrates relay's flight stack onto hardware.

Each layer depends on the one below. jess cannot deploy until relay is
bit-exact. relay cannot fly until gale is proven. The bottlenecks propagate
up the chain.

## Cross-repo issues: the bottlenecks are real

The issues don't stay in one repo. They propagate.

**jess depends on relay:**

- jess #264: "Ladder: develop in wasm → deploy unchanged. Rung 1 (relay) is
  bit-exact" — jess can't deploy to hardware until relay's wasm cascade is
  bit-exact in simulation.
- jess #167: "Consumption contract: how jess integrates relay's flight
  components" — jess needs a **contract** for how to consume relay's WASM
  components.

**relay depends on jess:**

- relay #572: "HITL wire binding carries no battery element" — relay's
  Hardware-in-the-Loop binding needs jess's hardware to test.
- relay #589: "falcon-ekf and falcon-iekf export identical interface" —
  **discovered by jess** (jess#293), confirmed by relay. Downstream finds
  upstream bugs.

**gale and jess collide:**

- gale #356: "Shared bench: jess and gale are about to collide on the same
  STLINK-V3 / G474" — both need the **same physical hardware**. Two agents,
  one debug probe.

## The pattern

1. **Downstream dependencies** — jess can't ship until relay is bit-exact.
2. **Upstream feedback** — jess discovers issues in relay that relay didn't
   know about.
3. **Resource contention** — gale and jess compete for the same hardware.
4. **Contracts solve it** — jess #167 is literally about defining a
   "consumption contract" between jess and relay.

The bottlenecks are there. They won't go away. But the roles are clear.

## The principle

> **Who does what is more important than how fast.**

The factory is not a hierarchy. It is a set of roles, each with a clear job,
connected by contracts. The bottlenecks move — hardware, CI, decisions,
cross-repo dependencies. The roles don't.

jess orchestrates. relay flies. gale provides the kernel. Everyone knows
their role. The bottlenecks are managed, not eliminated.

## What we would tell you to take from this

**Name the roles.** The names define the responsibilities. "Orchestrator"
is not a title — it's a principle. Who integrates? Who watches the release?
Who owns the ladder?

**Bottlenecks will exist.** Hardware contention, CI queues, decision queues,
cross-repo dependencies. You can't eliminate them. You can only manage them.

**Contracts connect the roles.** The interface between jess and relay is a
contract. The interface between relay and gale is a contract. Define the
contract, and the agents don't collide.

**Downstream finds upstream bugs.** jess discovers issues in relay that
relay didn't know about. The integrator is the canary — they feel the
bottlenecks first.

**The roles don't move.** The bottlenecks do. Fix the hardware contention,
and the CI queue becomes the bottleneck. Add more runners, and the decision
queue moves. The roles stay. The principle stays.

## Limits

This is one factory's structure: three repos, three roles, one dependency
chain. It has not been tested in a larger organisation with more layers,
more roles, and more complex dependencies. The claim is not "this is the
only way to structure a factory" but "the roles are clear, and the
bottlenecks are managed."

The cross-repo issues are real, measured from the issue trackers on 26
October 2026. The dependency chain (gale → relay → jess) is the actual
structure of our repos. The contracts are being defined — jess #167 is the
first consumption contract.

## Sources and caveats

The roles and dependency chain are from the author's own repositories
(pulseengine/jess, pulseengine/relay, pulseengine/gale). The cross-repo
issues are from the GitHub issue trackers, read on 26 October 2026.

The issue numbers and titles are real. The interpretation — that the roles
are clear and the bottlenecks are managed — is the author's view, not a
measured outcome.

---

*This post is part of [PulseEngine](/) — a formally verified WebAssembly
Component Model engine for safety-critical systems. Prior posts in the arc:
[SAFe was built for slow humans](/blog/safe-was-built-for-slow-humans/),
[Can we deliver X by January?](/blog/can-we-deliver-x-by-january/),
[The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/).*
