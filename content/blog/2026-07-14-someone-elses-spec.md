+++
title = "Someone else's spec: running an external corpus through the whole chain"
description = "It's easy to make a toolchain look integrated on a demo you built to flatter it. The honest test is to feed it a specification you didn't write and can't edit. We did that with Eclipse S-CORE — 2,985 real safety artifacts through rivet, and one component expressed through the whole stack — and kept a running log of every place our tools didn't fit."
date = 2026-07-14
draft = true
[taxonomies]
tags = ["traceability", "verification", "process"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
The honest test of whether a toolchain "works together" is not a demo you built
to show it off. It's feeding it a real specification you **didn't design and can't
edit** — and seeing where the seams hold. We ran [Eclipse
S-CORE](https://github.com/eclipse-score)'s safety corpus through
[rivet](https://github.com/pulseengine/rivet), and kept a log of every gap it
surfaced.
{% end %}

A pipeline diagram always looks clean. Every arrow connects; every box is the
right size. The trouble is that the person who drew it also chose the example — so
of course the pieces fit. The interesting question is what happens when the input
comes from someone else.

Eclipse S-CORE is a good someone else: an open, ISO 26262 / ASPICE-shaped body of
automotive safety engineering, actively maintained by a working group with real
domain expertise, published as a [sphinx-needs](https://sphinx-needs.com) typed
graph. We don't control it, we can't edit it to suit our tools, and it's far
larger than anything we'd hand-write. Perfect.

## The real one: 2,985 artifacts through rivet

[playground-eclipse-score](https://github.com/pulseengine/playground-eclipse-score)
converts a pinned snapshot of that corpus — **2,985 actual sphinx-needs
artifacts** — into rivet's typed YAML. Upstream repositories are pinned by exact
SHA and materialised on demand; nothing is vendored.

The point was never to look impressive. It was to answer one question we couldn't
answer with bespoke examples: *does rivet's schema actually cover real ASIL-rated
artifact shapes?* Measured against 2,985 of them, not five we made up.

The most valuable file in that repo is not the converted output — it's
`tools/falsification-journey.md`: a running log of **every gap the corpus surfaced
in our tool, and how we closed it.** A requirement shape rivet's schema didn't
model. A cross-repo reference its externals mechanism couldn't express. A field
that didn't round-trip. Each one is a place reality didn't fit the tool — written
down, not smoothed over. That log is the actual deliverable. Anything polished
about the corpus itself belongs to Eclipse; the metamodel, the process
documentation, and the artifact discipline are theirs.

## The illustrative one: one component, the whole stack

[example-kvs](https://github.com/pulseengine/example-kvs) zooms in on a single
component from that world — `persistency::kvs`, a key-value store — and expresses
it through the *entire* PulseEngine stack, layer by layer:

| Layer | What it adds |
|---|---|
| rivet typed YAML | 8 requirements + 8 architecture elements + FMEA + decisions + test-specs, schema-checked by `rivet validate` |
| spar AADL | a typed architecture model with ARP4761 safety properties — a file Eclipse's setup doesn't have at all |
| WIT contract | a binary interface that `wit-bindgen` turns into a Rust trait the implementation must satisfy at link time |
| witness | an MC/DC harness carrying truth-table evidence per predicate |
| sigil | a signed manifest tying artifact + contract + evidence hashes to a release |
| verification gate | walks the artifact list and reports `PASSED / FAILED / MISSING` per artifact, red on any gap |

Here's the part most write-ups would leave out, and we won't: **not all of that is
live yet.** The rivet artifacts validate today. The AADL → WIT → Rust component
chain is real PulseEngine infrastructure, exercised on other projects — this is its
first application to Eclipse content. But the witness and sigil entries are
*skeletons that show the shape* of the evidence, and the verification gate runs
today as a stub. The Rust implementation lives in a separate crate behind the WIT
contract, not in the repo.

So example-kvs is an honest **map** of how the pieces interlock on a real
component, with the traceability layer working now and the rest drawn to scale. It
shows what "the whole chain, applied to this" looks like — and marks clearly which
boxes are filled and which are outlined.

## Why feed it something you didn't make

Two things you cannot learn from a demo you built:

- **Whether the schemas fit shapes you didn't choose.** Our own examples are shaped
  by what rivet already models. 2,985 foreign artifacts are not — and every mismatch
  is signal, not noise.
- **Whether the seams hold under an upstream you don't control.** Pinned by SHA,
  materialised on demand, re-converted on change — the integration has to survive a
  moving target it can't edit.

That's the difference between a pipeline that *looks* integrated and one that has
been *tested* for it. The clean arrows are the easy part. The log of where the
arrows didn't connect is the honest one.

---

*See [how it all fits together](@/how-it-works.md) for the full pipeline, and
[playground-eclipse-score](https://github.com/pulseengine/playground-eclipse-score)
/ [example-kvs](https://github.com/pulseengine/example-kvs) for the two repos above.
Not affiliated with the Eclipse Foundation.*
