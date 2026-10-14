+++
title = "AI in the product, not AI in the toolchain"
description = "We read 40 standards pages looking for guidance on using an AI agent inside a certified development process. There is one informative Technical Report from 2024 and one draft ASPICE chapter from July 2026. The draft says review the AI-generated output before acceptance, and stops there."
date = 2026-10-14
draft = false
ready = true
[taxonomies]
tags = ["verification", "process", "traceability", "ai-agents"]
authors = ["Ralf Anton Beier"]
+++

Two questions get confused, and the confusion matters because the standards bodies
have answered one of them and not the other.

The first question is how to certify a system that contains machine learning. A
perception stack, a classifier in a control loop, a model that makes a decision the
safety case depends on. Call that AI in the product.

The second question is what happens when an agent writes code that goes into a
certified product. The agent is not in the shipped artifact at all. It is a
development tool, which in certification language means the question is tool
qualification. Call that AI in the toolchain.

We went looking for published guidance on the second one. The result is a short
section below, because there almost isn't any.

## What exists for AI in the product

A lot, and more arriving. EUROCAE WG-114 and SAE G-34 reached consensus on
ED-324 / ARP6983 on 24 August 2026, targeting Q4 2026, with Issue 1 scoped to
non-adaptive supervised machine learning up to IDAL C. ISO/IEC JTC 1/SC 42 has
ISO/IEC TS 22440 at Committee Draft, stage 30.60, with its consultation closed on
11 April 2026. EASA released Issue 03 of its AI Concept Paper for consultation on
3 June 2026, adding Level 3, reinforcement learning and symbolic AI, and closed
comments on 12 August. ISO/PAS 8800 was published in December 2024. ISO 26262
Edition 3 is in progress, with secondary sources expecting a Draft International
Standard around Q4 2026.

That is a healthy pipeline. None of it is about the agent that wrote the code.

## What exists for AI in the toolchain

Across 40 standards pages we fetched and read, exactly one document's scope
explicitly covers using AI to build safety-related functions: **ISO/IEC TR
5469:2024**, published 8 January 2024. It is a Technical Report, which means
informative rather than normative. You cannot be assessed against it.

The second item is a draft. The VDA QMC Working Group 13 Guidelines, 3rd edition,
reportedly adds a chapter on AI-assisted development. Our source for the content is
a consultancy blog from 13 July 2026 rather than VDA itself, so treat the detail as
unconfirmed. What it reports is that the chapter does not mandate or restrict
specific tools, that it **requires review of AI-generated output before
acceptance**, and that assessors weigh AI use under SUP.8, SUP.1 and PA 2.2.

Then the absences. DO-330 and ED-215, the tool qualification standard everyone
reaches for, was published in January 2012 with a corrigendum in February 2021, and
contains no AI material. We read the RTCA Program Management Committee summaries
from 16 December 2025 and 10 March 2026: SC-240's accepted plan for future work on
DO-330, DO-331 and DO-248C has one open revision item, and it is commercial
off-the-shelf software at Levels A and B. ISO 26262-8:2018, whose clause 11 covers
confidence in the use of software tools, has sat at stage 90.92, "to be revised",
since 8 July 2024.

One body says the gap out loud. The ISO page for ISO/PAS 8800:2024 states that it
"does not give specific guidelines for software tools that use AI."

{% note(kind="tip") %}
The EU AI Act does cover agents, and it is worth knowing how. The AI Act Service
Desk FAQ states that the rules applicable to AI systems and GPAI models also apply
to AI agents, and that agents are not a separate category. Nothing there addresses
an agent used as a software development tool.
{% end %}

## The sentence that is the whole problem

The only guidance we found that speaks to AI in the toolchain, and it is a draft
reported second-hand, says to review AI-generated output before acceptance.

That is correct. It is also where the difficulty starts rather than ends, because
"review" is doing enormous work in that sentence. If review means a human reads the
diff and agrees, the 2026 literature is fairly brutal about what that catches.

An evaluation of specification autoformalization in Verus found that an
LLM-as-judge misses 26% of the failures an executable specification test catches
(arXiv:2605.26457). A repository-level study found that roughly a quarter of
test-passing patches admit counterexamples, and that only 56% of agent-written
specifications pass audit, with the dominant failure being faithfulness: a
specification that constrains part of the behaviour and leaves the rest free
(arXiv:2609.21190). Work on Dafny reinforcement learning reports models learning
"specification hacking" against weak specifications, with the verified pass rate
dropping from 58.1% to between 9.7% and 31.1% once underspecified tasks were
filtered out (arXiv:2605.30914).

Machine checking is not automatically safe either. A proof repair study on Isabelle
found that of 144 candidates Isabelle accepted, 6 had modified text that was
supposed to be protected, and every one came from a workflow permitted to edit the
whole theory file (arXiv:2608.13459). A green build answers whether the checker was
satisfied. It does not answer whether only the permitted text changed.

The sharpest result for anyone gating proofs by grep: proofs have been produced that
compile and pass the standard `sorry`-token scan while depending on `sorryAx`, Lean's
underlying sorry axiom. An axiom-level audit removed 4, 8, 11 and 19 such proofs
across four configurations (arXiv:2608.28639).

So the honest reading of the draft ASPICE sentence is that it names the right
obligation and leaves the mechanism open. Making review mechanical is the open
problem, and it is open in a standards sense as well as a technical one.

## Our dates, stated plainly

We have been building on the second question since before we knew it was a gap, and
the dates are worth separating rather than rounding into one claim.

The verification substrate dates to the first week of March 2026. `rivet`, our SDLC
traceability tool, has its initial commit on 7 March 2026; `spar`, the AADL
architecture analysis, on 8 March. The proof rule sets are older still, with
`rules_rocq_rust` starting 11 January 2026 and `rules_verus` on 20 February.

The agent-facing half is later. The methodology became an installable artifact on
24 May 2026, and the traceability gate that blocks a release until the V closes
landed on 2 June 2026. Anyone who wants to check either date can read the git log.

We are not claiming to predate the Five Eyes agentic AI guidance, which the agencies
released on 30 April and 1 May 2026. That guidance is about securing agents, through
least privilege and prompt injection defence, and it is a different axis from
assuring what an agent produced.

## What we got wrong in our own gates

A post about mechanical review should say where ours failed, because both failures
are the kind the literature above predicts.

The first was a self-exemption. A Lean gate in `spar` counted unproven obligations
and excluded any line carrying a `-- TODO` comment. That exclusion was a deliberate
no-op when written, because the tracked sorries kept their TODO on the previous
line. The sorries then grew from 5 to 12 and moved the comment onto the same line,
and the no-op became universal. Twelve went in and zero came out, while the step
printed that the gate was green. The replacement counts every form including
`sorryAx`, with no comment-based exemption, against a ratchet floor. The lesson we
kept is that an exemption keyed on a pattern the exempted code itself controls cannot
hold, because the proof author writes both the `sorry` and the comment that excuses
it.

The second is still open. Our proof-honesty gates are token scans over a set of
paths, and a token scan cannot see a transitive dependency. A proof that inherits
`sorryAx` from an imported lemma carries no local token to match. `#print axioms` and
a kernel-level audit follow the dependency graph and are strictly stronger, and we do
not run one yet. Four of our repositories carry Lean files with no equivalent gate at
all.

## Where this is being discussed

Mostly not in the safety-critical rooms. We checked the pages of the Eclipse SDV
Working Group, Eclipse S-CORE, the Bytecode Alliance, two ELISA working groups, the
Xen Safety Committee, the Safety-Critical Rust Consortium and CNCF TAG Security, and
found no AI-agent workstream on any of them. Eclipse S-CORE publishes no AI policy,
while listing ASPICE, ISO 26262 and ISO 21434 as the standards it addresses.

One room is working on exactly this. The COVESA Generative AI Group's stated mission
is making generative AI tooling "interoperable, standardized, and accessible across
the entire automotive V-model", organised by V-model stage from requirements to
homologation, aligning with AUTOSAR, ISO 26262 and ASPICE. Its current pilot stage is
requirements management, and it is still finalising its charter.

A charter being written now will decide whether "review the AI output" stays a
process statement or becomes a mechanical obligation with a defined artifact. That is
a narrow window, and it is open.
