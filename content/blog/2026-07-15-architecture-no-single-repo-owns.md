+++
title = "The architecture no single repo owns"
description = "This month the toolchain stopped being a line and became a graph: proofs flow from loom into synth, one solver (ordeal) is shared across repos, and agent coordination is mirrored into the traceability store. Those edges span repositories — so they're owned by no single repo's CI, and that's exactly where drift hides. Checking them takes a different kind of verification: architecture checks across repos, run by a fleet of agents."
date = 2026-07-15
draft = true
[taxonomies]
tags = ["verification", "process", "ai-agents", "how-it-works"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
For a long time the toolchain was a **line**: architecture → code → fuse →
optimize → transcode → sign → run. This month it quietly became a **graph**.
Proofs now flow *between* stages — loom hands synth machine-checked invariants;
one solver, [ordeal](https://github.com/pulseengine/ordeal), is shared as the
verification substrate across repos; and the agents' own coordination is mirrored
into the traceability store as typed facts. Every one of those edges **spans
repositories** — which means it is owned by *no single repo's CI*. That's where
drift hides, and it's why we've started running a different kind of check:
**architecture checks across repos**, by a fleet of agents.
{% end %}

## The pipeline grew feedback edges

A month ago you could draw the build path as a straight arrow. Look at what each
component *ingests* today and the arrow has folded back on itself:

- **One shared solver.** [synth](https://github.com/pulseengine/synth)'s
  translation validation — does the native ARM match the wasm? — no longer calls
  Z3. Since v0.27 its default engine is **ordeal**, a pure-Rust, certificate-checked
  QF_BV solver from a *different repo*; Z3 is kept only as a differential oracle
  (141/141 agreement, zero disagreements). loom is slated to follow. So a repo whose
  job used to be "a solver" is now the **verification substrate the build layer
  depends on** — a cross-repo edge that didn't exist before.
- **Proofs flow downstream, not just wasm.**
  [loom](https://github.com/pulseengine/loom) now emits a `wsc.facts` section
  carrying the invariants it *proved* while optimizing (this value is in range, this
  divisor is nonzero). synth (v0.31) **ingests those facts** as premises for its own
  codegen. The pipeline became *proof-carrying*: each stage hands the next not just
  bytes but machine-checked hypotheses about them.
- **The agents' coordination became an artifact.**
  [agora](https://github.com/pulseengine/agora) — where per-repo agents negotiate
  ("ship v0.1?") — mirrors its message log into
  [rivet](https://github.com/pulseengine/rivet) as typed `coordination-fact`
  entries. So rivet, which already ingested architecture models and test results,
  now also ingests **the interaction between the agents themselves**, durably and
  auditably. (agora is still a spike — two agents, one channel, stubbed signing —
  but the edge is real.)
- **A composition that only exists across repos.** `gust`, gale's verified-OS
  North Star, is not in any one repository: it's gale's primitives + kiln's async
  scheduler + app and driver components, **fused by meld, optimized by loom,
  transcoded by synth**, linked against a `kiln-builtins` crate that only started
  existing this month. That five-repo composition now runs *bit-identical on three
  real chips* (Cortex-M4, Cortex-M3, and RISC-V). It works only when all five repos
  line up.

None of these edges live inside a single repository. Each repo's CI is green — and
the interesting behaviour is in the wiring *between* them.

## No single repo's CI owns the seams

Here's the failure mode that graph creates. Every repo can be internally correct —
tests pass, proofs close, coverage is measured — and the **architecture spanning
them can still be wrong**, because nothing between two repos is anyone's build gate.

We keep finding exactly this. In one sweep this week:

- **[ordeal](https://github.com/pulseengine/ordeal)** — the *shipped* soundness
  proof is complete and CI-gated, but its `lean/README.md` still says the proof is
  open. The repo disagrees with itself.
- **[scry](https://github.com/pulseengine/scry)** — the opposite: the engine is real
  and its Rocq soundness proofs are admit-free, but the README still reads
  "v0.1.0, no real logic yet." A repo *underselling* its own code is drift too — it
  makes everything downstream that cites it look like an overclaim.
- **[sigil](https://github.com/pulseengine/sigil)** — began as a hard fork of
  Frank Denis's MIT-licensed `wasmsign2` and diverged ~18×, but carried no license
  or attribution. A cross-repo *lineage* fact that no per-repo check would ever flag.

Each is invisible to the repo's own CI, because "does this README match the shipped
proof," "does this claim match another repo's ledger," and "is this fork's license
retained" are not statements any single build can evaluate. They're **architecture
properties** — and the architecture is the thing no single repo owns.

## Checking it takes a fleet

You cannot verify a graph one node at a time. So the check has to span repos too —
and that is what the exploding agent interaction is *for*.

Per-repo agents already run their own loops (hunt issues, implement features, check
that a new release actually works), coordinating through GitHub issues and releases —
and, increasingly, through agora. An **architecture check** is one level up: a fleet
that sweeps *every* repo at once, reads each one's actual source, and cross-references
the claims against reality — the README against the shipped proof, the website against
each repo's own honesty ledger, one repo's "we depend on X" against X's actual API.

That's not hypothetical; it's how this very post was fact-checked. A fleet of agents
explored the repositories in parallel, mapped what each component ingests *today*
(the graph above), and surfaced the drift as filed issues — the three above among
them. The corrections you'll have seen land this week on the site — ordeal named as
the shared solver, gust corrected to real silicon, the flight stack kept honestly
emulated — all came from that cross-repo pass, not from any one repo's CI.

## The honest frontier

Two things make this more than a trick:

- **It catches a class of bug per-repo verification structurally cannot** — the
  "no single repo owns it" drift. As the graph grows more edges (proof-carrying
  facts, shared solvers, mirrored coordination), that class grows with it. Checking
  each repo harder does not help; only checking *between* them does.
- **The coordination is becoming auditable.** agora mirroring into rivet means the
  agents' cross-repo interaction is itself a typed, inspectable record — the same
  discipline we apply to requirements, applied to how the agents talk. Today it's a
  spike; the direction is that "how the fleet coordinated" becomes traceable
  evidence, not folklore.

And the positive proof that the graph is *right*, not just large: `gust` running
bit-identical on three real chips is a cross-repo composition verified end to end —
five repositories' outputs lining up on silicon. That's the thing no single repo
could have claimed, checked on the one surface that can't be argued with.

The pipeline was easy to verify because a line has no surprising interactions. A
graph does — and every one of them lives in the space between repositories. So that's
where we've pointed the agents. The architecture is the thing no single repo owns;
increasingly, it's the thing the fleet is there to check.

---

*How the pieces fit today: [how it works](@/how-it-works.md). The honest maturity
map: the [how-it-works series](/tags/how-it-works/).*
