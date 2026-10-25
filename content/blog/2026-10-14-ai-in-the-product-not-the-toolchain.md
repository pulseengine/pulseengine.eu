+++
title = "AI in the product, not AI in the toolchain"
description = "We went looking for published guidance on using an AI agent inside a development process that has to satisfy a certification standard. What is published is one informative Technical Report from 2024 and a VDA Guidelines chapter we have only second-hand. The FAA planned a rule, and it asks you to disclose the use rather than to establish anything about the output. Every tool-qualification framework makes verifying the output the hinge, and nothing we could read says what the verification has to produce."
date = 2026-10-14
draft = false
ready = true
[taxonomies]
tags = ["verification", "process", "traceability", "ai-agents", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
There are two questions here, and they get run together: certifying a system that
*contains* machine learning, and using an agent that *writes code for* a certified
product. The standards bodies have
answered the first one at length and the second one barely at all — one informative
Technical Report, one chapter we can only read second-hand, and a regulator's planned
rule that asks you to disclose the use rather than establish anything about the output.
The tool-qualification frameworks that already cover an agent all turn on verifying its
output, and nothing we could read says what that verification has to produce. That is
the gap, and the measurements below are what is in it.
{% </insight> %}

Two questions get confused, and the confusion matters because the standards bodies
have answered one of them and not the other.

The first question is how to certify a system that contains machine learning. A
perception stack, a classifier in a control loop, a model that makes a decision the
safety case depends on. Call that AI in the product.

The second question is what happens when an agent writes code that goes into a
certified product. The agent never ships inside the artifact, so in certification
language it is a development tool and the question is tool qualification. Call that
AI in the toolchain.

The standards do have a generic answer to the second question, and it is older than
the problem. DO-178C requires a tool to be qualified only when it eliminates,
reduces or automates a process **and** its output is not otherwise verified.
ISO 26262-8 works the same way: the tool confidence level follows from the tool's
impact and the likelihood of detecting a malfunction, so a tool whose output is
independently checked needs no qualification measures. Both frameworks are
deliberately technology-neutral, and both therefore already cover an agent.

Which means the interesting question is not whether a standard applies. It is that
every one of these frameworks makes "verify the output" the hinge, and none of them
says what verifying the output consists of when the output is a four-hundred-file
diff that no human will read line by line. That is the gap this post is about.

We went looking for published guidance on the second one. The section below is longer
than what it found, because most of its length is caveats about what we could not read.

<figure class="standards-map">
<svg viewBox="0 0 760 500" width="100%" role="img"
     aria-labelledby="sm-title sm-desc"
     style="max-width:760px;height:auto;font-family:'Atkinson Hyperlegible Next',system-ui,sans-serif">
  <title id="sm-title">Two spaces: AI in the product and AI in the toolchain</title>
  <desc id="sm-desc">Published and in-flight standards for certifying systems that contain
  machine learning, next to the near-empty space of guidance for using an AI agent as a
  development tool. The second panel holds one informative Technical Report from 2024, one
  chapter published in 2026 whose content we have only second-hand, a planned regulator policy
  statement that asks for disclosure and whose publication we could not confirm, the supporting-processes
  part of ISO 26262 whose third edition is in ballot and whose text we have not read, and a
  tool-qualification standard whose own forward-work plan carries no AI item.</desc>
  <rect x="8" y="44" width="354" height="448" rx="10"
        fill="var(--surface,#1a1d27)" stroke="var(--border,#2b2f3e)"/>
  <text x="26" y="26" font-size="13" font-weight="700" fill="var(--text,#e1e4ed)">(A) AI in the product</text>
  <text x="26" y="40" font-size="11" fill="var(--text-dim,#8b90a0)">certifying a system that CONTAINS machine learning</text>
  <text x="26" y="72" font-size="11" font-weight="700" fill="var(--green,#4ade80)">PUBLISHED</text>
  <rect x="26" y="82" width="318" height="30" rx="5" fill="var(--surface-raised,#242836)" stroke="var(--border-subtle,#242836)"/>
  <text x="38" y="95" font-size="11.5" fill="var(--text,#e1e4ed)">ISO/PAS 8800</text>
  <text x="38" y="107" font-size="10" fill="var(--text-dim,#8b90a0)">Dec 2024 · PAS, not a full standard</text>
  <rect x="26" y="118" width="318" height="30" rx="5" fill="var(--surface-raised,#242836)" stroke="var(--border-subtle,#242836)"/>
  <text x="38" y="131" font-size="11.5" fill="var(--text,#e1e4ed)">EASA AI Concept Paper, Issue 02</text>
  <text x="38" y="143" font-size="10" fill="var(--text-dim,#8b90a0)">Mar 2024 · Levels 1 and 2</text>
  <text x="26" y="176" font-size="11" font-weight="700" fill="var(--amber,#fbbf24)">IN FLIGHT</text>
  <rect x="26" y="186" width="318" height="30" rx="5" fill="var(--surface-raised,#242836)" stroke="var(--border-subtle,#242836)"/>
  <text x="38" y="199" font-size="11.5" fill="var(--text,#e1e4ed)">ED-324 / SAE ARP6983</text>
  <text x="38" y="211" font-size="10" fill="var(--text-dim,#8b90a0)">consensus 24 Aug 2026 per EASA slides</text>
  <rect x="26" y="222" width="318" height="30" rx="5" fill="var(--surface-raised,#242836)" stroke="var(--border-subtle,#242836)"/>
  <text x="38" y="235" font-size="11.5" fill="var(--text,#e1e4ed)">ISO/IEC TS 22440-1, Requirements</text>
  <text x="38" y="247" font-size="10" fill="var(--text-dim,#8b90a0)">CD at stage 30.60 · comments closed 11 Apr 2026</text>
  <rect x="26" y="258" width="318" height="30" rx="5" fill="var(--surface-raised,#242836)" stroke="var(--border-subtle,#242836)"/>
  <text x="38" y="271" font-size="11.5" fill="var(--text,#e1e4ed)">EASA Concept Paper, Issue 03</text>
  <text x="38" y="283" font-size="10" fill="var(--text-dim,#8b90a0)">consultation 3 Jun 2026 · adds Level 3</text>
  <rect x="26" y="294" width="318" height="30" rx="5" fill="var(--surface-raised,#242836)" stroke="var(--border-subtle,#242836)"/>
  <text x="38" y="307" font-size="11.5" fill="var(--text,#e1e4ed)">ISO/DIS 26262 Edition 3</text>
  <text x="38" y="319" font-size="10" fill="var(--text-dim,#8b90a0)">12 parts · DIS ballot opened 14 Oct 2026</text>
  <text x="26" y="356" font-size="11" fill="var(--text-dim,#8b90a0)">Six documents. Four of them moved</text>
  <text x="26" y="371" font-size="11" fill="var(--text-dim,#8b90a0)">in 2026 alone.</text>
  <rect x="398" y="44" width="354" height="448" rx="10"
        fill="var(--surface,#1a1d27)" stroke="var(--accent,#6c8cff)" stroke-opacity="0.55"/>
  <text x="416" y="26" font-size="13" font-weight="700" fill="var(--text,#e1e4ed)">(B) AI in the toolchain</text>
  <text x="416" y="40" font-size="11" fill="var(--text-dim,#8b90a0)">an agent WRITES code for a certified product</text>
  <text x="416" y="72" font-size="11" font-weight="700" fill="var(--green,#4ade80)">PUBLISHED</text>
  <rect x="416" y="82" width="318" height="30" rx="5" fill="var(--surface-raised,#242836)" stroke="var(--border-subtle,#242836)"/>
  <text x="428" y="95" font-size="11.5" fill="var(--text,#e1e4ed)">ISO/IEC TR 5469</text>
  <text x="428" y="107" font-size="10" fill="var(--text-dim,#8b90a0)">Jan 2024 · informative only, cannot be assessed</text>
  <text x="416" y="138" font-size="11" font-weight="700" fill="var(--amber,#fbbf24)">PUBLISHED, CONTENT SECOND-HAND</text>
  <rect x="416" y="148" width="318" height="30" rx="5" fill="var(--surface-raised,#242836)" stroke="var(--border-subtle,#242836)"/>
  <text x="428" y="161" font-size="11.5" fill="var(--text,#e1e4ed)">VDA Guidelines, 3rd edition chapter</text>
  <text x="428" y="173" font-size="10" fill="var(--text-dim,#8b90a0)">Jul 2026 · print only · AI output "needs verification"</text>
  <text x="416" y="204" font-size="11" font-weight="700" fill="var(--cyan,#22d3ee)">PLANNED, PUBLICATION NOT CONFIRMED</text>
  <rect x="416" y="214" width="318" height="42" rx="5" fill="var(--surface-raised,#242836)" stroke="var(--border-subtle,#242836)"/>
  <text x="428" y="227" font-size="11.5" fill="var(--text,#e1e4ed)">FAA policy statement on AI in certification</text>
  <text x="428" y="239" font-size="10" fill="var(--text-dim,#8b90a0)">4Q2024 draft target · disclose AI use in systems</text>
  <text x="428" y="251" font-size="10" fill="var(--text-dim,#8b90a0)">"or in the development of documents"</text>
  <text x="416" y="282" font-size="11" font-weight="700" fill="var(--amber,#fbbf24)">IN BALLOT, TEXT NOT READ</text>
  <rect x="416" y="292" width="318" height="30" rx="5" fill="var(--surface-raised,#242836)" stroke="var(--border-subtle,#242836)"/>
  <text x="428" y="305" font-size="11.5" fill="var(--text,#e1e4ed)">ISO/DIS 26262-8, supporting processes</text>
  <text x="428" y="317" font-size="10" fill="var(--text-dim,#8b90a0)">Edition 3 · 12-week DIS ballot opened 14 Oct 2026</text>
  <text x="416" y="348" font-size="11" font-weight="700" fill="var(--text-faint,#5c6070)">NO AI ITEM IN ITS FORWARD PLAN</text>
  <rect x="416" y="358" width="318" height="30" rx="5" fill="none" stroke="var(--border,#2b2f3e)" stroke-dasharray="4 3"/>
  <text x="428" y="371" font-size="11.5" fill="var(--text-faint,#5c6070)">DO-330 / ED-215, tool qualification</text>
  <text x="428" y="383" font-size="10" fill="var(--text-faint,#5c6070)">2011/2012 · one open revision item, and it is COTS</text>
  <rect x="416" y="404" width="318" height="56" rx="6"
        fill="var(--accent-glow,rgba(108,140,255,0.12))" stroke="var(--accent,#6c8cff)"/>
  <text x="428" y="422" font-size="11.5" font-weight="700" fill="var(--accent,#6c8cff)">where we are</text>
  <text x="428" y="437" font-size="10.5" fill="var(--text,#e1e4ed)">substrate Mar 2026 · rivet, spar</text>
  <text x="428" y="451" font-size="10.5" fill="var(--text,#e1e4ed)">agent output gated mechanically, May 2026</text>
  <text x="416" y="480" font-size="11" fill="var(--text-dim,#8b90a0)">Nothing we could read states what the verification must produce.</text>
</svg>
<figcaption>Measured 14 and 15 October 2026. The right-hand panel is everything we could find
that speaks to using an AI agent inside a development process which has to satisfy a certification
standard. Two of its five entries are documents we have not been able to read.</figcaption>
</figure>

## What exists for AI in the product

A lot, and more arriving. Slides presented at the EASA AI Days on 9 and 10 September 2026 record EUROCAE
WG-114 and SAE G-34 reaching consensus on ED-324 / ARP6983 on 24 August 2026, list
it for Q4 2026, and scope Issue 1 to non-adaptive supervised machine learning up to
IDAL C.[^ed324] Those figures come from the slide deck rather than from a published
standard. ISO/IEC JTC 1/SC 42 has ISO/IEC TS 22440 in parts, and Part 1,
*Requirements*, is at stage 30.60: the committee draft was registered on
9 February 2026, consultation opened on 13 February, and the comment period closed on
11 April 2026.[^ts22440] EASA released Issue 03 of its AI Concept Paper for consultation on
3 June 2026, adding Level 3, reinforcement learning and symbolic AI, and closed
comments on 12 August.[^easa03] ISO/PAS 8800 was published in December 2024.[^pas8800] And ISO 26262
Edition 3 has reached Draft International Standard in all twelve parts, with the
12-week DIS ballot opening on 14 October 2026.[^dis26262]

One of them is worth pulling out of the list, because it is the most concrete thing
either half of this post has to point at. VDA published the Automotive SPICE process
assessment model version 4.1 on 24 August 2026, free and in the open, and it carries a
Machine Learning Engineering process group: MLE.1 Machine Learning Requirements
Analysis, MLE.2 Machine Learning Architecture, MLE.3 Machine Learning Training, MLE.4
Machine Learning Model Testing, and SUP.11 Machine Learning Data Management, each with
numbered base practices an assessor can rate.[^vdapam41] Across its roughly 41,000
words, "machine learning" appears 59 times. "Artificial intelligence" appears zero
times, "generative" zero, "large language" zero. That is the shape of the whole
problem in one document: when the AI is the product, the working group gives you five
numbered processes with rateable base practices; when the AI is the tool, its normative
model says nothing at all, and what it reportedly gives you instead is a chapter in a
separate book you have to buy on paper.

## What exists for AI in the toolchain

Across the standards pages we fetched and read, one published document whose scope we
could actually read covers using AI to build safety-related functions: **ISO/IEC TR
5469:2024**, published 8 January 2024.[^tr5469] It is a Technical Report, so it carries no
normative requirements and there is no conformity claim to make against it.

That is a weaker statement than "only one document exists", deliberately. The scope of
ISO/IEC TS 22440 does reach this half of the post. Its third bullet covers "use of AI
technology to design, develop and verify safety-related functions", alongside AI
inside a safety-related function and conventional safety functions guarding an AI
system.[^ts22440wd] The catch is which draft that bullet belongs to. It is recorded
against **ISO/IEC WD TS 22440**, the single-document working draft, which reached
stage 20.98 and was deleted on 6 May 2024 — the same day the multipart project was
approved and registered.[^ts22440] The scope preview for the current Part 1 committee
draft is blank on every page we can reach, so we cannot tell you whether the bullet
survived the restructuring. If it did, the normative successor is already in progress,
and the honest version of this section is that the published guidance is thin rather
than absent.

The second item is the VDA QMC Working Group 13 Guidelines, 3rd edition, which VDA's
own publications page dates to July 2026, lists as English, print-only, and describes
as "Process assessment using the Automotive SPICE PAM 4.1".[^vdapubs] It reportedly
adds a chapter on AI-assisted development. We have not read the VDA text, and our
source for what the chapter says is second-hand, so treat every detail of it as
unconfirmed: that the chapter does not mandate or restrict specific tools, that
AI-generated output **needs verification before it is accepted**, and that assessors
weigh AI use under SUP.8, SUP.1 and PA 2.2 — Configuration Management and Quality
Assurance, to name the two the PAM does define.[^vdapam41] The publications page itself
says nothing about AI.

The third item is a regulator's, and it is the one that most directly addresses an
agent in a development process. The FAA's *Roadmap for Artificial Intelligence Safety
Assurance*, Version I, digitally signed on 23 July 2024, plans a policy statement that
would inform applicants who intend to use AI "in their systems, **or in the
development of documents**, that they should disclose that use and discuss a
certification path with the FAA early in the development phase", with a 4Q2024 draft
target.[^faaroadmap] Note what the obligation is: disclose, and come talk to us. The
same table plans a policy memo on considerations for AI and machine learning "Used in
the Development of Airborne Systems and Equipment", also targeted at 4Q2024. We could
not establish that either document was published. The FAA's own AI technical discipline
page, last updated 9 April 2026, lists the roadmap as its only resource,[^faadiscipline]
and a Federal Register query for FAA documents mentioning artificial intelligence since
July 2024 returns three, none of them a certification policy statement.[^fedreg] That
is the absence of a listing rather than evidence of non-publication, and FAA policy
statements do not always travel through the Federal Register.

Then the absences. DO-330 and ED-215, the tool qualification standard everyone
reaches for, dates from 2011 or 2012 depending on which catalogue you read, with a
corrigendum announced on 15 February 2021.[^do330] We have not read the standard itself, so
we make no claim about its contents. What we did read is the RTCA Program Management
Committee summaries from 16 December 2025 and 10 March 2026, and SC-240's accepted
plan for future work on DO-330, DO-331 and DO-248C lists one open revision item. It
is commercial off-the-shelf software at Levels A and B, and there is no AI item.[^rtcapmc]

ISO 26262-8 is a different kind of entry, and one number on its own would file it under
absences. The published 2018 edition does sit at stage 90.92, "to be revised", and has
since 8 July 2024.[^iso26262-8-2018] But the revision is not idle. ISO/DIS 26262-8, *Supporting processes*, Edition 3 — the part that carries
confidence in the use of software tools — moved through two working-draft rounds, was
approved for registration as a DIS on 4 August 2026, and its 12-week ballot opened on
14 October 2026.[^dis26262-8] We have not read the draft: it is CHF 67 behind a
paywall, its public abstract is the generic series abstract, and that abstract contains
no occurrence of "artificial intelligence" or "machine learning". So we can tell you
that the clause is being revised right now and not what the revision says.

One scope statement draws the boundary explicitly. ISO/PAS 8800:2024 states that
"This document does not provide specific guidelines for software tools that use AI methods."[^pas8800]

The EU AI Act does cover agents, and it is worth knowing how.[^aiact]

{% <note kind="tip"> %}
The AI Act Service Desk FAQ states that the rules applicable to AI systems and GPAI
models also apply to AI agents, and that agents are not a separate category of AI. The
same page describes the Commission's views as preliminary. That FAQ answer does not
address an agent used as a software development tool.
{% </note> %}

## The sentence that is the whole problem

Three bodies have now written down the same obligation, independently, and none of them
has written down what satisfying it produces.

The VDA chapter, reported second-hand, says AI-generated output needs verification
before it is accepted. The Eclipse Foundation's *Generative Artificial Intelligence
Usage Guidelines for Eclipse Committers*, version 1.0 of April 2024, asks committers to
"take reasonable effort to ensure the accuracy of generated content".[^eclipsegenai] And
the FAA, for its own staff, has twice issued an interim notice carrying the sentence
"All GAI output, including all information, content, or data created by GAI within the
FAA, must undergo human review for validity, accuracy and completeness."[^faanotices]

Each is correct. Each is also where the difficulty starts rather than ends, because
"review" carries the whole obligation and none of the three says what review means.
If it means a human reads the diff and agrees, nobody has measured that at all. What
four 2026 results do measure is automated agreement, and the numbers are not
reassuring.

An evaluation of specification autoformalization in Verus found that an
LLM-as-judge misses 26% of the failures an executable specification test catches.[^specgym]
A repository-level study found that roughly a quarter of
test-passing patches admit counterexamples, and that only 56% of agent-written
specifications pass that study's own audit, with the dominant failure being faithfulness: a
specification that constrains part of the behaviour and leaves the rest free.[^sweproof]
Work on Dafny reinforcement learning reports models learning
"specification hacking" against weak specifications, which the author found after
verifier-reward training had already raised the verified reward from 2.2% to 58.1%.
On a separately filtered and refined benchmark the same work
reports a pass rate of 9.7% rising to 31.1%, so the two figures are different
experiments rather than a before and after.[^dafnyrl]

Machine checking is not automatically sufficient either. A proof repair study on Isabelle
found that of 144 candidates Isabelle accepted, 6 had modified text that was
supposed to be protected, and every one came from a workflow permitted to edit the
whole theory file.[^capri] A green build answers whether the checker was
satisfied. It does not answer whether only the permitted text changed.

For anyone gating proofs by grep, the relevant result is this. Proofs have been produced that
compile and pass the standard `sorry`-token scan while depending on `sorryAx`, Lean's
underlying sorry axiom. Running DeepSeek-Prover-V2-7B on PutnamBench, an axiom-level
audit removed 4 and 8 such proofs from whole-proof sampling and 11 and 19 from
search, across two sampling budgets each. The authors note the counts should not be
read as a property of the search procedure.[^kernelaudit]

So three bodies name the right obligation and leave the mechanism open. Making review
mechanical is the open problem, and it is open in a standards sense as well as a
technical one.

## Our dates, stated plainly

The dates are worth separating rather than rounding into one claim, and worth
deflating first. The January to March 2026 work is a generic verification substrate.
Nothing about typed traceability or an AADL parser is specific to an agent having
written the code, so it is not evidence of having seen this gap early. ISO/IEC TR
5469 is dated 8 January 2024 and predates all of it by two years. These are dates,
not a priority claim.

The verification substrate dates to the first week of March 2026. `rivet`, our SDLC
traceability tool, has its initial commit on 7 March 2026; `spar`, the AADL
architecture analysis, on 8 March. The proof rule sets are older still, with
`rules_rocq_rust` starting 11 January 2026 and `rules_verus` on 20 February.

The agent-facing half is later, and it needs a distinction this post would be
dishonest without. The methodology became an installable artifact on 24 May 2026, and
the skill that makes V-closure a release precondition landed on 2 June 2026. That
second commit touches six files and every one is Markdown or JSON. It is a procedure
an agent is told to follow, not a check that fails. By this post's own argument it
does not count, and we are not exempt from the argument.

The mechanically enforced part is older. `rivet audit`, the AI-session and commit
traceability gate, landed on 18 May 2026 as 799 lines of Rust with CLI tests
(rivet #297). That is the date that means what the other two only look like they
mean. Anyone who wants to check any of the three can read the git log, and the pull
request merge timestamps are the stronger instrument because commit dates are
author-set.

We are not claiming to predate the Five Eyes agentic AI guidance, which CISA dates
to 1 May 2026.[^fiveeyes] That guidance is about securing agents, through
least privilege and prompt injection defence, and it is a different axis from
assuring what an agent produced.

## Where our own gates stand

A post about mechanical review should say where ours failed. One did, and it failed
in the way the literature above predicts.

A Lean gate in `spar` counted unproven obligations and excluded any line carrying a
`-- TODO` comment. That exclusion was a deliberate no-op when written, because the
tracked sorries kept their TODO on the previous line. The sorries then grew from 5 to
12 and moved the comment onto the same line, and the no-op became universal. Twelve
went in and zero came out, while the step printed that the gate was green. We found
it in our own audit and track it as spar #385. The replacement counts `sorry`,
`sorryAx`, `admit` and a bare `axiom` over comment-stripped text, with no
comment-based exemption, against a declared floor. The lesson we kept is that an
exemption keyed on a pattern the exempted code itself controls cannot hold, because
the proof author writes both the `sorry` and the comment that excuses it.

The axiom-level check is a separate gate and it exists. `ordeal/lean/AxiomCheck.lean`
pins the exact axiom list of each capstone theorem with `#guard_msgs`, so any new
axiom changes the message and fails elaboration, and the file is a default lake
target, which makes the required Lean CI job fail with it. Its header states the
division of labour: the sorry budget is guarded separately, and this file "guards
everything `sorry`-shaped guards miss", naming `sorryAx` and `native_decide`
(`ofReduceBool`) as the holes it closes.

The two techniques are complementary rather than ordered, which is worth stating
because it is tempting to rank them. A token scan cannot see a transitive dependency,
so it misses a proof that inherits `sorryAx` from an imported lemma. An axiom audit
over selected capstone theorems cannot see a `sorry` in a file nothing imports, which
the token scan catches. `spar`'s scan does not match `native_decide`; `ordeal`'s audit
does. Running one is not a substitute for running the other, and the gap we have is a
rollout gap: the axiom gate runs in one repository, and the others carrying Lean have
not adopted it.

## Where this is being discussed

Mostly not in the safety-critical rooms, with a caveat about our instrument. On
14 October 2026 we read the published pages of the Eclipse SDV Working Group,
Eclipse S-CORE, the Bytecode Alliance, ELISA's Tools and Open Source Engineering
Process working groups, the Xen Safety Committee, the Safety-Critical Rust
Consortium and CNCF TAG Security, and found none of them publishing a workstream on
qualifying agent-written code against a safety standard. That is a narrower claim
than "no AI work": CNCF has AI security material and an agentic-systems effort under
other TAGs, and a group's published pages are weaker evidence than its minutes.

AUTOSAR belongs on that list too, and it is the most pointed entry. Its published
concept roadmap runs four release buckets and roughly thirty named concepts — time-sensitive
networking, CANsec, SOME/IP metadata, safe hardware-acceleration APIs, feature graphs,
over-the-air update machinery — and not one of them concerns AI, in the product or in
the toolchain.[^autosarconcepts] Its cross-standard working groups are Architecture,
Methodology and Templates, Security and Safety as lead groups, plus Application
Interfaces, In-Vehicle Communication, Diagnostics, Timing and Tracing, Time
Synchronization and Update and Configuration Management, with WG-CP and WG-AP for the
two platforms. We read every working-group page the site publishes and found no AI group
among them. WG-SAF's scope is ISO 26262 with no AI item, and WG-MT — which owns "the overall
AUTOSAR methodology and all template-, manifest-documents / exchange formats", the
natural home for how AI-assisted development fits the process — lists no AI item
either.[^autosarwgs] That matters because of who is aligning with whom, below.

Eclipse S-CORE publishes no AI policy of its
own, but it does not need to: it inherits the Eclipse Foundation's Generative AI
Usage Guidelines, v1.0 of April 2024, which require a committer to make reasonable
effort to ensure generated content is accurate and to put all output through the
project's normal vetting for testing, intellectual property and security.[^score][^eclipsegenai] A
project-level policy template requiring contributors to validate generated code
before submission exists as a proposed draft rather than an adopted rule, and the
guidelines are written for committers rather than all contributors.

So the review obligation is already stated at open-source governance level, which
makes the gap sharper rather than wider. Eclipse says vet the output. ASPICE says
verify the output. The FAA told its own staff to put it through human review, and
planned to tell applicants to disclose that they used it. DO-178C says qualify the tool unless
the output is verified. Nobody we could read says what the verification has to
produce, or how anyone would check that it happened.

One room is closest to it. The COVESA Generative AI Group's stated mission is
making generative AI tooling "interoperable, standardized, and accessible across
the entire automotive V-model", organised by V-model stage from requirements to
homologation, aligning with AUTOSAR, ISO 26262 and ASPICE. Its current pilot stage is
requirements management, and it is still finalising its charter.[^covesa]

Read that alongside the paragraph on AUTOSAR. The group writing the charter is
aligning with three targets: one whose published roadmap and working-group scopes
contain no AI item at all, one whose tool-confidence part is in ballot this quarter
with contents we cannot read, and one whose process assessment model gives machine
learning five numbered processes and AI-assisted development none.

## What we would tell you to take from this

Three things, and the first is the only one that needs no argument.

**The generic answer already covers you, and it is the weakest kind of coverage.**
DO-178C and ISO 26262-8 both exempt a tool whose output is independently verified.
An agent is a tool. So the question a certification authority will ask is not "did
you use AI" but "show me the verification", and the frameworks hand you that word
without a definition. Anyone building an agentic development process for a certified
product is writing the missing definition whether they mean to or not.

**The window is narrower than it looks.** The ISO 26262-8 Edition 3 ballot opened on
14 October 2026 and runs twelve weeks; COVESA's Generative AI Group was still finalising
its charter when we read its page on the same day. One of those documents is circulating
right now in a form we cannot read, and the other has not been written. Whatever either
says about tool confidence, it is being decided this quarter — an unusual amount of
still-wet concrete for this industry.

**Pick the mechanism before anyone picks it for you, and prefer one that fails.**
Every result in the literature section above is a case where a check was satisfied and
the property did not hold — the judge that agreed, the test suite that passed, the
proof the kernel accepted, the token scan that saw no `sorry`. Our own worst gate
failure is the same shape. The useful form of "verify the output" is not a reviewer's
signature; it is an oracle that goes red, that the author of the output cannot
reconfigure, and whose red state blocks the release. Everything else is a process
statement, including, by our own argument, two of our three dates.

## Appendix: what `sorry` and `sorryAx` are, and why a grep for them is not enough

This post leans on Lean vocabulary that is obvious to proof engineers and opaque to
everyone else, including most of the audience for a certification argument. Here is
the short version, measured rather than recalled: every output below is from
Lean 4.29.0-rc6 on the examples as written.[^leanprobe]

**`sorry` is an admitted hole.** Writing `sorry` where a proof should go makes the
declaration typecheck anyway. It is how you record "this statement is what I want and
I have not proved it yet", and it is indispensable while drafting. Lean emits a
warning, `declaration uses 'sorry'`. `admit` is a second spelling of the same thing,
which is why a gate that counts one should count both.

**`sorryAx` is what it leaves behind.** `sorry` is not a syntactic placeholder that
disappears; it elaborates to an application of an axiom, `sorryAx : (α : Sort u) → Bool → α`,
which asserts that every type is inhabited. That is false, and anything proved through
it is proved from a contradiction. You can ask the kernel what a theorem actually rests
on:

```
theorem unproved (n : Nat) : n + 1 = 1 + n := by sorry
#print axioms unproved
-- 'unproved' depends on axioms: [sorryAx]

theorem proved (n : Nat) : n + 0 = n := rfl
#print axioms proved
-- 'proved' does not depend on any axioms
```

**Here is why grep is the wrong instrument.** Axiom dependency is transitive and the
token is not. This theorem contains no `sorry` anywhere in its text:

```
theorem downstream : 5 + 1 = 1 + 5 := unproved 5
#print axioms downstream
-- 'downstream' depends on axioms: [sorryAx]
```

A scan of `downstream` finds a clean file. The kernel reports an unproved theorem. In a
real project the admitted lemma lives in another file, often in another module written
by someone else, and the scan that is supposed to be your gate reports green on every
file that imports it. The same asymmetry runs the other way: `#print axioms` over a
chosen list of capstone theorems cannot see a `sorry` sitting in a file that nothing
imports, which the token scan catches immediately. Neither subsumes the other, which is
why the body says we run both.

**Not every axiom is a problem, and that is the hard part.** Lean's own classical
reasoning rests on three, and a theorem depending on them is perfectly respectable:

```
#print axioms Classical.em
-- 'Classical.em' depends on axioms: [propext, Classical.choice, Quot.sound]
```

So "contains no axioms" is the wrong requirement. The requirement is "contains exactly
these axioms", which is a statement about an artifact and can be pinned. One more
measurement shows why it has to be an allowlist and not a blocklist. The `native_decide`
tactic discharges a decidable goal by compiling it, running it, and trusting the answer —
which drags the compiler, the runtime and the C toolchain into your trusted base. In
current Lean it registers a *generated, per-declaration* axiom:

```
theorem by_native : (List.range 50).length = 50 := by native_decide
#print axioms by_native
-- 'by_native' depends on axioms: [by_native._native.native_decide.ax_1_1]
```

The older spelling, `Lean.ofReduceBool`, is now deprecated with the message
"in-kernel native reduction is deprecated; assert native evaluations with axioms
instead". A gate holding a blocklist of bad axiom names would have been written against
the old name and would silently pass the new one, because the new name did not exist
when the blocklist was written and contains the theorem's own name. A gate that pins the
expected axiom list and fails on any difference catches it without being told about it.

That is the whole argument of this post in one mechanism, which is why the appendix
exists. "Review the proof" is a process statement: it names an obligation and leaves
the artifact unspecified. "`#print axioms` on each capstone theorem, pinned with
`#guard_msgs`, as a default build target, so the required CI job fails on any change to
the axiom list" is an artifact: a reviewer can read the pinned list, an auditor can
re-run it, and the proof author cannot widen it without the diff showing it. The
standards ask for the first. Nothing we could read asks for the second.

## Corrections

The first version of this post, published 14 October 2026, said the following. Each item
is corrected or superseded below; the first two were wrong when published, and the rest
were true then and are no longer the best we can do.

- **ISO 26262 Edition 3 is at Draft International Standard, not awaiting one.** All
  twelve parts are at stage 40.20 and the 12-week DIS ballot opened on
  14 October 2026. The post said the edition was in progress with secondary sources
  expecting a DIS around Q4 2026.[^dis26262]
- **ISO 26262-8 does not belong under "absences".** The published 2018 edition does
  sit at stage 90.92, "to be revised", but the Edition 3 revision of that same part
  was approved for registration as a DIS on 4 August 2026 and is in ballot now.[^dis26262-8]
- **AUTOSAR is not unknown to us.** The post said a TLS failure left it unchecked.
  Its published concept roadmap and the scopes of all ten of its cross-standard
  working groups carry no AI item, in the product or in the toolchain.[^autosarconcepts][^autosarwgs]
- **FAA policy is not absent from this post.** The post said `faa.gov` returned 403 on
  every attempt. The *Roadmap for Artificial Intelligence Safety Assurance*, Version I,
  is signed 23 July 2024 and plans a policy statement telling applicants that they
  "should disclose" AI use "in their systems, or in the development of documents".[^faaroadmap]
- **The ISO/IEC TS 22440 scope bullet is confirmed, for the wrong draft.** "Use of AI
  technology to design, develop and verify safety-related functions" is recorded
  verbatim against the single-document working draft that was deleted on 6 May 2024.
  Whether it survived into the current Part 1 committee draft is still unknown to
  us.[^ts22440wd][^ts22440]
- **"None of them is about the agent that wrote the code" is withdrawn.** On the
  recorded scope above, one of them partly is.
- **The page count is dropped.** The post said we read 40 standards pages. We did not
  keep the list, so we cannot stand behind the exact number and no longer give one.

## Sources and caveats

Every item below was opened and read, except where the entry says otherwise. Numbers
quoted in the post were checked against the source rather than against a summary of it.

Two access notes apply throughout. `iso.org` returns HTTP 403 to automated readers, so
every ISO entry here was read on `committee.iso.org`, which serves the same project
records under the same numeric identifiers and is not blocked; ISO draft texts
themselves are paywalled and we did not buy them. `www.autosar.org` presents a leaf
certificate with no intermediate in the chain, which strict TLS verifiers reject and
clients that follow the certificate's authority-information-access extension accept —
a configuration on their side, not a reachability problem. Where a standard is sold
rather than published, the entry says we have not read it, and claims about those
documents rest on named secondary interpretations or on the bodies' own project
records rather than on the text.

### Research

[^specgym]: Agarwal et al. — *Verus-SpecGym: An Agentic Environment for Evaluating Specification Autoformalization*. arXiv:2605.26457, 26 May 2026. [arxiv.org/abs/2605.26457](https://arxiv.org/abs/2605.26457). Primary (open access preprint).

[^sweproof]: Ma et al. — *SWE-Proof: Can Language Models Resolve Real-World Issues with Machine-Checked Proofs?* arXiv:2609.21190, 18 September 2026. [arxiv.org/abs/2609.21190](https://arxiv.org/abs/2609.21190). Primary (open access preprint).

[^dafnyrl]: Tan — *Automating Formal Verification with Reinforcement Learning and Recursive Inference*. arXiv:2605.30914, 29 May 2026. [arxiv.org/abs/2605.30914](https://arxiv.org/abs/2605.30914). Primary (open access). A master's thesis, not peer reviewed.

[^capri]: Woodcock, Leite, Sampaio and Wei — *CAPRI: Contract-Aware Proof Repair for Isabelle*. arXiv:2608.13459, 13 August 2026. [arxiv.org/abs/2608.13459](https://arxiv.org/abs/2608.13459). Primary (open access preprint).

[^kernelaudit]: Bodla and Yang — *Reward-Oracle MCTS for Formal Theorem Proving: Sample-Efficient Search and the Need for Kernel-Level Proof Auditing*. arXiv:2608.28639, 11 August 2026. [arxiv.org/abs/2608.28639](https://arxiv.org/abs/2608.28639). Primary (open access preprint).

[^leanprobe]: Measured by us on 15 October 2026 with Lean 4.29.0-rc6 (arm64-apple-darwin, commit `00659f8e`), running the declarations exactly as shown. Primary (our own measurement, reproducible from the snippets in this appendix). `#print axioms` is Lean's own command for the transitive axiom dependencies of a declaration; the generated `native_decide` axiom name and the `Lean.ofReduceBool` deprecation message are quoted from that run's output.

### Standards and regulatory documents

[^tr5469]: ISO/IEC TR 5469:2024 — *Artificial intelligence — Functional safety and AI systems*. Technical Report, published 8 January 2024. [committee.iso.org/standard/81283.html](https://committee.iso.org/standard/81283.html). Primary for status and scope statement; **text not read** (paywalled).

[^pas8800]: ISO/PAS 8800:2024 — *Road vehicles — Safety and artificial intelligence*. Published 13 December 2024. [committee.iso.org/standard/83303.html](https://committee.iso.org/standard/83303.html). Primary for the scope statement quoted, which appears in the public record; **full text not read**.

[^iso26262-8-2018]: ISO 26262-8:2018 — *Road vehicles — Functional safety — Part 8: Supporting processes*. Stage 90.92, "To be revised", since 8 July 2024. [committee.iso.org/standard/68390.html](https://committee.iso.org/standard/68390.html). Primary for stage; **text not read**.

[^dis26262-8]: ISO/DIS 26262-8 — *Road vehicles — Functional safety — Part 8: Supporting processes*, Edition 3. Stage 40.20. Lifecycle read 15 October 2026: CD approved for registration as DIS and DIS registered 4 August 2026; DIS ballot initiated 14 October 2026, 12 weeks. [committee.iso.org/standard/90027.html](https://committee.iso.org/standard/90027.html). Primary for stage and dates; **draft text not read** (CHF 67).

[^dis26262]: ISO/DIS 26262 Edition 3, Parts 1 to 12. Each part's record read individually on 15 October 2026; all twelve at stage 40.20 with DIS ballot initiated 14 October 2026, 12 weeks. [Part 1](https://committee.iso.org/standard/90020.html) through [Part 12](https://committee.iso.org/standard/90031.html). Primary for stage and dates; **draft texts not read**.

[^ts22440]: ISO/IEC CD TS 22440-1 — *Artificial intelligence — Functional safety and AI systems — Part 1: Requirements*, Edition 1. ISO/IEC JTC 1/SC 42. Stage 30.60. Lifecycle: new project approved and registered 6 May 2024; CD registered 9 February 2026; CD consultation initiated 13 February 2026; close of comment period 11 April 2026. [committee.iso.org/standard/89535.html](https://committee.iso.org/standard/89535.html). Primary for stage and dates. **The scope preview is blank on this record**, which is why this post makes no claim about the current draft's scope.

[^ts22440wd]: ISO/IEC WD TS 22440 — *Artificial intelligence — Functional safety and AI systems — Requirements*. Stage 20.98, effective 6 May 2024, lifecycle "Project deleted, May 6, 2024". Scope quoted verbatim, including the third bullet. [iss.rs/en/project/show/iso:proj:87118](https://iss.rs/en/project/show/iso:proj:87118). A national standards body's mirror of the ISO project database (Institute for Standardization of Serbia) — primary for the project record, secondary as a route to it. This is the *withdrawn* single-document draft, not the current committee draft.

[^do330]: DO-330 / ED-215 — *Software Tool Qualification Considerations*. Corrigendum 1 announced 15 February 2021; catalogues disagree on whether the original is dated 2011 or 2012. [eurocae.net](https://www.eurocae.net/product/ed-215-software-tool-qualification-considerations/). **We have not read the standard.**

[^rtcapmc]: RTCA Program Management Committee summaries, 16 December 2025 and 10 March 2026. Source for SC-240's accepted plan for future work on DO-330, DO-331 and DO-248C. [rtca.org PMC summary (PDF)](https://www.rtca.org/wp-content/uploads/2026/03/2-A-PMC-Summary-2025-12-16_approved.pdf). Primary (open access).

[^ed324]: ED-324 / SAE ARP6983 status, from slides presented at the EASA AI Days, 9 and 10 September 2026. The consensus date, the Q4 2026 listing and the IDAL C scope come from that deck, not from a published standard. [easa.europa.eu](https://www.easa.europa.eu/en/downloads/144162/en). Primary (open access) for the slides; secondary for the standard.

[^easa03]: EASA — *Artificial Intelligence Concept Paper, Proposed Issue 03*. Released for consultation 3 June 2026, comments closed 12 August 2026. [easa.europa.eu](https://www.easa.europa.eu/en/newsroom-and-events/news/easa-releases-latest-issue-its-concept-paper-artificial-intelligence). Primary (open access).

[^vdapubs]: VDA QMC — *Automotive SPICE® Publications*. Lists "Automotive SPICE® Guidelines. Process assessment using the Automotive SPICE PAM 4.1 — Version: 3rd edition, July 2026; Language: English; Format: Print". [vda-qmc.de](https://vda-qmc.de/en/automotive-spice/automotive-spice-veroeffentlichungen/). Primary for the edition, date, language and format. **The Guidelines text itself is print-only and we have not read it**; everything this post says about its AI chapter is second-hand and flagged as such in the body.

[^vdapam41]: VDA Working Group 13 — *Automotive SPICE® Process Reference Model / Process Assessment Model*, version 4.1, dated 2026-08-24. [Direct PDF](https://vda-qmc.de/wp-content/uploads/2026/09/Automotive-SPICE-PAM-v41.pdf). Primary (open access, free). Read in full for term counts: "machine learning" 59, "artificial intelligence" 0, "generative" 0, "large language" 0. Source for the MLE.1–MLE.4 and SUP.11 process names and for SUP.8 Configuration Management and SUP.1 Quality Assurance.

[^faaroadmap]: FAA — *Roadmap for Artificial Intelligence Safety Assurance*, Version I. Digitally signed David H. Boulter, 23 July 2024; 31 pages. [faa.gov (PDF)](https://www.faa.gov/aircraft/air_cert/step/roadmap_for_AI_safety_assurance). Primary (open access), read in full. Source for the planned policy statement and policy memo and their 4Q2024 draft targets, and for the "AI in Safety Lifecycle" research row scoping a large language model to report generation in the FAA's own System Safety Review process, target TBD.

[^faadiscipline]: FAA — *Technical Discipline: Artificial Intelligence – Machine Learning*. Last updated 9 April 2026; lists the roadmap as its only resource. [faa.gov](https://www.faa.gov/aircraft/air_cert/step/disciplines/artificial_intelligence). Primary (open access).

[^faanotices]: FAA Notice N 1370.51, *Use of Generative AI Tools and Services*, issued 3 October 2024, cancelled 23 March 2025 by N 1370.52 ([FAA document record](https://www.faa.gov/regulations_policies/orders_notices/index.cfm/go/document.information/documentID/1042513)); and FAA Notice [N 1370.52](https://www.faa.gov/documentLibrary/media/Notice/N_1370.52_Generative_AI_Tools_and_Services.pdf), same subject, effective 23 March 2025 with a printed cancellation date of 23 March 2026. Primary (open access), both read. Both are interim policy addressed to FAA employees and contractors, not to applicants, and both carry the quoted human-review sentence. We could not establish whether a successor to N 1370.52 exists.

[^fedreg]: Federal Register API query, 15 October 2026: FAA documents mentioning "artificial intelligence" published since 1 July 2024. Three results, none a certification policy statement. [federalregister.gov](https://www.federalregister.gov/api/v1/documents.json?conditions%5Bagencies%5D%5B%5D=federal-aviation-administration&conditions%5Bterm%5D=artificial%20intelligence&conditions%5Bpublication_date%5D%5Bgte%5D=2024-07-01). Primary (open access). Absence of a listing, not evidence of non-publication.

[^fiveeyes]: CISA, NSA, ASD ACSC, Canadian Centre for Cyber Security, NZ NCSC and UK NCSC — *Careful Adoption of Agentic AI Services*, 1 May 2026. [cisa.gov](https://www.cisa.gov/resources-tools/resources/careful-adoption-agentic-ai-services). Primary (open access).

[^aiact]: European Commission — AI Act Service Desk FAQ, *How are AI agents addressed within the AI Act?* The page describes the Commission's views as preliminary. [ai-act-service-desk.ec.europa.eu](https://ai-act-service-desk.ec.europa.eu/en/faq). Primary (open access).

### Projects and governance

[^eclipsegenai]: Eclipse Foundation — *Generative Artificial Intelligence Usage Guidelines for Eclipse Committers*, Version 1.0, April 2024. Page current as of 25 September 2026. [eclipse.org/projects/guidelines/genai](https://www.eclipse.org/projects/guidelines/genai). Primary (open access). Quoted phrase read at source. The stronger "review and validate" wording belongs to a *proposed* project policy template, not to these guidelines.

[^score]: Eclipse S-CORE project site. Source for the ASPICE, ISO 26262 and ISO 21434 listing and for the absence of a project-level AI policy. [eclipse.dev/score](https://eclipse.dev/score/). Primary (open access) for what the project publishes; a published page is weaker evidence than minutes.

[^covesa]: COVESA Generative AI Group. Source for the mission statement, the requirements-management pilot stage and the charter status, read 14 October 2026. [covesa.atlassian.net](https://covesa.atlassian.net/wiki/spaces/WIK4/pages/176029697/Generative+Artificial+Intelligence+AI+Group). Primary (open access).

[^autosarconcepts]: AUTOSAR — *AUTOSAR Concept Roadmap & Upcoming Standards*. Read 15 October 2026. [autosar.org](https://www.autosar.org/standards/autosar-concept-roadmap). Primary (open access). Four release buckets (R2X-11 backlog, R26-11, R25-11, R24-11); no concept names AI.

[^autosarwgs]: AUTOSAR — working groups. Read 15 October 2026: [Cross-Standard](https://www.autosar.org/working-groups/cross-standard) (four lead groups — WG-A Architecture, WG-MT Methodology & Templates, WG-SEC Security, WG-SAF Safety — plus six further cross-standard groups; WG-MT scope quoted from this page), [Classic Platform](https://www.autosar.org/working-groups/classic-platform) (WG-CP), [Adaptive Platform](https://www.autosar.org/working-groups/adaptive-platform) (WG-AP) and [Artop](https://www.autosar.org/working-groups/cross-standard/artop). Primary (open access). That is every working-group page the site publishes; none matched artificial intelligence, machine learning, LLM or generative.
