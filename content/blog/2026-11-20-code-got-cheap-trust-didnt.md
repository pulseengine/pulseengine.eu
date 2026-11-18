+++
title = "Code got cheap. Trust didn't."
description = "When AI makes writing code cheap, the hard part is showing that it is right. Germany once turned boiler explosions into independent inspection; this post asks what that means for verifying AI-built software in Europe."
date = 2026-11-20
draft = true
[taxonomies]
tags = ["verification", "europe", "standards", "ai-agents", "process"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**When writing code becomes cheap, the scarce thing is evidence that it is
right.** Such evidence counts only if its checks can fail, if someone other than
the author checks it and anyone can re-run it, and if it is tied to an agreed
definition of "right". Our argument, from a small project, is that standards,
independent review and evidence before release are what safety-critical buyers
need from AI-built software, and that the work now is to make them cheap and open.
{% </insight> %}

## The shift: generation is cheap, checking is not

For most of software's history, writing the code was the expensive part.
Reviews, tests and proofs were overhead you paid on top. Coding agents have
turned that around: writing got cheap, and the question "is it right?" did not.

Microsoft's CEO said in an episode of The Pragmatic Engineer published on
16 November 2026: "In a world where code generation has become cheap, what has
become hard is verification"
([The Pragmatic Engineer](https://newsletter.pragmaticengineer.com/p/software-engineering-after-code-becomes),
at 11:50). In this post we ask what turns a claim about code into evidence. Our
working answer has three properties, numbered as in the list further down.

{% <mermaid> %}
flowchart LR
    D["3. Agreed definition of right"] --> B
    A["Claim"] --> B["1. Check that can fail"]
    B --> C["2. Checked by someone other than the author, re-runnable by anyone"]
    C --> E["Evidence"]
{% </mermaid> %}

## A boiler explodes in Mannheim, and the three properties

In January 1865 a steam boiler exploded at a brewery in Mannheim, and on
6 January 1866 a group of boiler owners founded an inspection association
([Deutschlandmuseum](https://www.deutschlandmuseum.de/en/geschichte/kalender/1866-01-06-origin-of-the-tuev)).
Its aim was regular inspection of the members' boilers, its first full-time
expert started in 1868, and it became the starting point for technical
inspection in Germany
([TÜV SÜD history](https://www.tuvsud.com/en-gb/about-us/history/our-foundation-years-1866-1900)).

Our working definition is that evidence is worth something only if it has three
properties:

1. **It can fail.** A check that cannot go red on bad input proves nothing. You
   find out by feeding it something it must reject. Nadella describes the same
   habit in the agent teams he watches: "how do you take every failure and then
   build back the test case and make sure you truly verify the test" (12:19).
2. **It is checked by someone other than the author, and re-runnable by
   anyone.** These are two separate demands. Independence means the author does
   not mark their own work; re-checkability means a result does not have to be
   taken on anyone's word. A signature shows which key signed the bundle and that
   it has not changed since; it says nothing about whether the bundle is right.
   For agents, independence includes the model: "How do you have the critique?
   There's so much to be said about having a separate model family" (17:05).
3. **It is tied to an agreed definition of right.** "Correct" needs a
   requirement or a standard that says what correct means, written without
   ambiguity.

In our reading, the boiler story has all three. An inspection that can find a
fault is a check that can fail. An expert of the association, not the operator,
is a checker other than the author, and a boiler inspected regularly is checked
again and again. An association that examines many boilers gives its
examiners a shared idea of what a sound boiler is, which ties the check to a
definition.

Independence can also be lost along the way. The final report on the Boeing
737 MAX prepared by the majority staff of the US House transportation committee
states, as one of several findings: "Excessive FAA delegation of certification functions to Boeing on the
737 MAX eroded FAA's oversight effectiveness and the safety of the public"
([House Transportation Committee report](https://democrats-transportation.house.gov/imo/media/doc/final_boeing_737_max_report.pdf)).
We read this as the same lesson as in Mannheim: the check has to be independent.

Our reading is also that standards work as a collective memory. They record
lessons in a rule, so that the next team does not have to learn them again, and
they supply the agreed definition that the third property asks for.

## When a constraint becomes the product

**It worked for certification.** Independent testing is a cost for every
manufacturer, and it became a paid business for the testers. TÜV SÜD reported
€3.4 billion of 2024 revenue
([press release](https://www.tuvsud.com/en-gb/press-and-media/2025/may/tuev-sued-achieves-significant-revenue-growth-in-2024))
and TÜV Rheinland €2.71 billion
([press release](https://www.tuv.com/press/en/press-releases/tuev-rheinland-results-2024.html)),
across all their services. In our reading, much of that demand exists because
inspection is required by law, so this trust business rests on a mandate, and
its weak spot is that certifiers are paid by the firms they certify.

**It failed for solar.** After feed-in tariffs drove a boom, Germany was once
the world's largest solar market. In May 2017 SolarWorld, the last major German cell maker,
filed for insolvency amid Chinese competition
([Clean Energy Wire](https://www.cleanenergywire.org/news/last-major-german-solar-cell-maker-surrenders-chinese-competition)).
The feed-in tariffs were a subsidy that created demand, not a constraint on
producers, and the demand was for a commodity that others could make more
cheaply.

The pattern, as we read the cases: **a constraint becomes a strength when it
produces a trust good that is hard to copy and that buyers must pay for. It stays
a cost when it only creates demand that anyone can serve more cheaply.** That is
our synthesis from a handful of cases, not a tested law.

This seems to clash with our call for open evidence: if anyone can copy it, how
can it be hard to copy? Our answer is that open evidence stays hard to fake
because its checks can fail and anyone can re-run them. What gets cheap is
producing and publishing evidence, not trusting it. Verification evidence for
safety-critical software falls on the certification side of our line, as long
as it keeps those properties.

## Rulebooks and tooling are late

A March 2026 NBER working paper by Bick, Blandin, Deming, Fuchs-Schündeln and
Jessen reports that output per hour increased by 85% in the US between 1995 and
2025 against 29% in Europe, a gap that opened long before AI, and that about 43%
of US workers use AI at work against about 32% in its survey of European
workers. Industries that adopted
AI more saw faster productivity growth, with no clear employment changes. The
authors report a correlation and do not claim it is causal
([NBER working paper 34995](https://www.nber.org/papers/w34995)).

The rulebooks for AI-built and connected products are arriving late. The Council
gave final approval on 29 June 2026 to move the AI Act's high-risk deadlines to
2 December 2027 for stand-alone systems and 2 August 2028 for systems embedded in
regulated products
([Council via EEAS](https://www.eeas.europa.eu/delegations/chile/artificial-intelligence-council-gives-final-green-light-simplify-and-streamline-rules_en)).
The Cyber Resilience Act is a cybersecurity law for products with digital
elements, not a functional-safety law. Its reporting obligations have applied
since 11 September 2026, and its main obligations apply from 11 December 2027
([European Commission](https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act)).

On the tooling side, rust-lang/rust#144999, merged on 8 August 2025, removed the
unstable MC/DC instrumentation
([rust-lang/rust#144999](https://github.com/rust-lang/rust/pull/144999)). The
2026 project goal aims at unstable support, and the goal page names DO-178C
level A among the standards that require MC/DC
([goal page](https://goals.rust-lang.org/2026/mcdc-coverage-support.html)).
Qualified Rust tooling does exist: Ferrous Systems announced in November 2023
that TÜV SÜD had qualified the Ferrocene 23.06.0 toolchain, which is open
source, as a tool for ISO 26262 (ASIL D) and IEC 61508 (SIL 4)
([Ferrous Systems](https://ferrous-systems.com/blog/officially-qualified-ferrocene/)).
That qualifies the compiler, not the software built with it. In the same
episode the host, Gergely Orosz, expects "blueprints and certifications in, I
don't know, five to 10 years" for agent-built systems (52:09). We read late
rulebooks and MC/DC support that is still only a goal as room for open
verification evidence in the meantime.

## What we are doing about it

PulseEngine is a work-in-progress WebAssembly Component Model engine aimed at
safety-critical targets, built largely by AI agents. Its job, as we see it, is to
make the "slow" parts fast and open. Our recent work maps onto the three
properties as follows.

- **Property 1, checks that can fail.** Our [previous post](/blog/green-by-default/)
  described planting bad inputs to see whether a check turns red. That is now a
  tool, [plant](https://github.com/pulseengine/plant).
- **Properties 2 and 3, review against a definition.** Two reviewers, AI agents
  started without the author's context, read the 29 requirements of our wohl
  project for ambiguity ([wohl#97](https://github.com/pulseengine/wohl/issues/97));
  the mechanical fixes are in [wohl#98](https://github.com/pulseengine/wohl/pull/98).
  Reading the code turned one finding, a safety check that never triggered in
  the scenario its own requirement describes, into a safety finding, which is
  still waiting for a design decision. Both
  reviewers came from the same project and the same model family as the author,
  so they were independent of the author's context, not of the organisation or
  the model, and every lead was checked against the code before anything
  changed.
- **Properties 1 and 2, evidence anyone can re-run.** wohl's
  [v0.7.0 release](https://github.com/pulseengine/wohl/releases/tag/v0.7.0)
  ships a signed evidence bundle with one verify command. A monthly workflow now
  runs it, with two planted failures that must go red
  ([pulseengine.eu#377](https://github.com/pulseengine/pulseengine.eu/pull/377)).
  That shows the bundle is intact and its checks can still fail, not that the
  software is correct.

Next we concentrate on verifiers designed so that their qualification evidence
can be produced and published openly; on signed, machine-readable evidence
bundles that can be mapped onto the Cyber Resilience Act's standards if and when
they are published; on traceability from each proof or test to the clause it
covers, including changes written by AI agents; and on MC/DC coverage for Rust
and WebAssembly.

## Limits

This is an argument from a small project, not a market study. We found no
reliable figure for the size of the market for safety-critical verification
tools, and no buyer has paid us anything. The rule about when a constraint
becomes a strength is our reading of a few cases. Most evidence we found about
the quality of AI-written code still comes from vendors.

What would change our mind: a published evidence format for the Cyber Resilience
Act that makes our bundles irrelevant, a pilot in which nobody cares about open
qualification evidence, or an independent study showing that AI-written
safety-critical code needs less checking, not more.
