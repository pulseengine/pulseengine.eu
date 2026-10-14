+++
title = "AI in the product, not AI in the toolchain"
description = "We read 40 standards pages looking for guidance on using an AI agent inside a development process that has to satisfy a certification standard. What is published is one informative Technical Report from 2024, and a VDA Guidelines chapter we have only second-hand. Every framework makes verifying the output the hinge, and none says what the verification has to produce."
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

We went looking for published guidance on the second one. The result is a short
section below, because there almost isn't any.

<figure class="standards-map">
<svg viewBox="0 0 760 416" width="100%" role="img"
     aria-labelledby="sm-title sm-desc"
     style="max-width:760px;height:auto;font-family:'Atkinson Hyperlegible Next',system-ui,sans-serif">
  <title id="sm-title">Two spaces: AI in the product and AI in the toolchain</title>
  <desc id="sm-desc">Published and in-flight standards for certifying systems that contain
  machine learning, next to the near-empty space of guidance for using an AI agent as a
  development tool. The second panel holds one informative Technical Report from 2024, one
  chapter published in 2026 whose content we have only second-hand, and a tool-qualification standard whose own forward-work plan carries no AI item.</desc>
  <rect x="8" y="44" width="354" height="364" rx="10"
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
  <text x="38" y="235" font-size="11.5" fill="var(--text,#e1e4ed)">ISO/IEC TS 22440</text>
  <text x="38" y="247" font-size="10" fill="var(--text-dim,#8b90a0)">Committee Draft · comments closed Apr 2026</text>
  <rect x="26" y="258" width="318" height="30" rx="5" fill="var(--surface-raised,#242836)" stroke="var(--border-subtle,#242836)"/>
  <text x="38" y="271" font-size="11.5" fill="var(--text,#e1e4ed)">EASA Concept Paper, Issue 03</text>
  <text x="38" y="283" font-size="10" fill="var(--text-dim,#8b90a0)">consultation 3 Jun 2026 · adds Level 3</text>
  <rect x="26" y="294" width="318" height="30" rx="5" fill="var(--surface-raised,#242836)" stroke="var(--border-subtle,#242836)"/>
  <text x="38" y="307" font-size="11.5" fill="var(--text,#e1e4ed)">ISO 26262 Edition 3</text>
  <text x="38" y="319" font-size="10" fill="var(--text-dim,#8b90a0)">in progress</text>
  <text x="26" y="358" font-size="11" fill="var(--text-dim,#8b90a0)">Five documents. None of them is about</text>
  <text x="26" y="373" font-size="11" fill="var(--text-dim,#8b90a0)">the agent that wrote the code.</text>
  <rect x="398" y="44" width="354" height="364" rx="10"
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
  <text x="428" y="173" font-size="10" fill="var(--text-dim,#8b90a0)">Jul 2026 · AI output "needs verification" before accepted</text>
  <text x="416" y="204" font-size="11" font-weight="700" fill="var(--text-faint,#5c6070)">EXISTS, NO AI ITEM IN ITS FORWARD PLAN</text>
  <rect x="416" y="214" width="318" height="30" rx="5" fill="none" stroke="var(--border,#2b2f3e)" stroke-dasharray="4 3"/>
  <text x="428" y="227" font-size="11.5" fill="var(--text-faint,#5c6070)">DO-330 / ED-215, tool qualification</text>
  <text x="428" y="239" font-size="10" fill="var(--text-faint,#5c6070)">2011/2012 · one open revision item, and it is COTS</text>
  <rect x="416" y="250" width="318" height="30" rx="5" fill="none" stroke="var(--border,#2b2f3e)" stroke-dasharray="4 3"/>
  <text x="428" y="263" font-size="11.5" fill="var(--text-faint,#5c6070)">ISO 26262-8, clause 11</text>
  <text x="428" y="275" font-size="10" fill="var(--text-faint,#5c6070)">"to be revised" since 8 Jul 2024</text>
  <rect x="416" y="306" width="318" height="56" rx="6"
        fill="var(--accent-glow,rgba(108,140,255,0.12))" stroke="var(--accent,#6c8cff)"/>
  <text x="428" y="324" font-size="11.5" font-weight="700" fill="var(--accent,#6c8cff)">where we are</text>
  <text x="428" y="339" font-size="10.5" fill="var(--text,#e1e4ed)">substrate Mar 2026 · rivet, spar</text>
  <text x="428" y="353" font-size="10.5" fill="var(--text,#e1e4ed)">agent output gated mechanically, May 2026</text>
  <text x="416" y="386" font-size="11" fill="var(--text-dim,#8b90a0)">One informative report and one draft sentence.</text>
</svg>
<figcaption>Measured 14 October 2026 across 40 standards pages. The right-hand panel is
the whole published guidance for using an AI agent inside a development process that has to satisfy a certification standard.</figcaption>
</figure>

## What exists for AI in the product

A lot, and more arriving. Slides presented at the EASA AI Days on 9 and 10 September 2026 record EUROCAE
WG-114 and SAE G-34 reaching consensus on ED-324 / ARP6983 on 24 August 2026, list
it for Q4 2026, and scope Issue 1 to non-adaptive supervised machine learning up to
IDAL C. Those figures come from the slide deck rather than from a published
standard. ISO/IEC JTC 1/SC 42 has ISO/IEC TS 22440 at
Committee Draft, in parts, with a comment period that closed in April 2026. The ISO
pages for it returned 403 to us, so the stage detail is second-hand. EASA released Issue 03 of its AI Concept Paper for consultation on
3 June 2026, adding Level 3, reinforcement learning and symbolic AI, and closed
comments on 12 August. ISO/PAS 8800 was published in December 2024. ISO 26262
Edition 3 is in progress, with secondary sources expecting a Draft International
Standard around Q4 2026.

Five documents, four of them still moving. None of them is about the agent that
wrote the code.

## What exists for AI in the toolchain

Across 40 standards pages we fetched and read, one published document whose scope we
could actually read covers using AI to build safety-related functions: **ISO/IEC TR
5469:2024**, published 8 January 2024. It is a Technical Report, so it carries no
normative requirements and there is no conformity claim to make against it.

That is a weaker statement than "only one document exists", deliberately. ISO/IEC
TS 22440 is reported to carry the same third scope bullet, covering the use of AI
technology to design, develop and verify safety-related functions, and it is a
Technical Specification with a Part 1 titled *Requirements*. We could not confirm it:
`iso.org` returns HTTP 403 to us, and the committee mirror's page for 22440-1 shows
the title and stage with the scope preview blank. If that bullet is in the current
draft then the normative successor is already in progress, and the honest version of
this section is that the published guidance is thin rather than absent.

The second item is the VDA QMC Working Group 13 Guidelines, 3rd edition, which
VDA's publications page dates to July 2026 after a public review that ran to
12 May 2026. It reportedly adds a chapter on AI-assisted development. We have not
read the VDA text, and our source for what the chapter says is second-hand, so
treat every detail of it as unconfirmed: that the chapter does not mandate or
restrict specific tools, that AI-generated output **needs verification before it is
accepted**, and that assessors weigh AI use under SUP.8, SUP.1 and PA 2.2.

Then the absences. DO-330 and ED-215, the tool qualification standard everyone
reaches for, dates from 2011 or 2012 depending on which catalogue you read, with a
corrigendum announced on 15 February 2021. We have not read the standard itself, so
we make no claim about its contents. What we did read is the RTCA Program Management
Committee summaries from 16 December 2025 and 10 March 2026, and SC-240's accepted
plan for future work on DO-330, DO-331 and DO-248C lists one open revision item. It
is commercial off-the-shelf software at Levels A and B, and there is no AI item. ISO 26262-8:2018, whose scope covers
confidence in the use of software tools, has sat at stage 90.92, "to be revised",
since 8 July 2024.

One scope statement draws the boundary explicitly. ISO/PAS 8800:2024 states that it
"This document does not provide specific guidelines for software tools that use AI methods."

{% note(kind="tip") %}
The EU AI Act does cover agents, and it is worth knowing how. The AI Act Service
Desk FAQ states that the rules applicable to AI systems and GPAI models also apply
to AI agents, and that agents are not a separate category of AI. The same page
describes the Commission's views as preliminary. That FAQ answer does not address an
agent used as a software development tool.
{% end %}

## The sentence that is the whole problem

The only guidance we found that speaks to AI in the toolchain, and it is a draft
reported second-hand, says to review AI-generated output before acceptance.

That is correct. It is also where the difficulty starts rather than ends, because
"review" carries the whole obligation in that sentence, and the sentence does not
say what review means. If it means a human reads the diff and agrees, nobody
has measured that at all. What four 2026 results do measure is automated agreement,
and the numbers are not reassuring.

An evaluation of specification autoformalization in Verus found that an
LLM-as-judge misses 26% of the failures an executable specification test catches
(arXiv:2605.26457). A repository-level study found that roughly a quarter of
test-passing patches admit counterexamples, and that only 56% of agent-written
specifications pass that study's own audit, with the dominant failure being faithfulness: a
specification that constrains part of the behaviour and leaves the rest free
(arXiv:2609.21190). Work on Dafny reinforcement learning reports models learning
"specification hacking" against weak specifications, which the author found after
verifier-reward training had already raised the verified reward from 2.2% to 58.1%
(arXiv:2605.30914). On a separately filtered and refined benchmark the same work
reports a pass rate of 9.7% rising to 31.1%, so the two figures are different
experiments rather than a before and after.

Machine checking is not automatically sufficient either. A proof repair study on Isabelle
found that of 144 candidates Isabelle accepted, 6 had modified text that was
supposed to be protected, and every one came from a workflow permitted to edit the
whole theory file (arXiv:2608.13459). A green build answers whether the checker was
satisfied. It does not answer whether only the permitted text changed.

For anyone gating proofs by grep, the relevant result is this. Proofs have been produced that
compile and pass the standard `sorry`-token scan while depending on `sorryAx`, Lean's
underlying sorry axiom. Running DeepSeek-Prover-V2-7B on PutnamBench, an axiom-level
audit removed 4 and 8 such proofs from whole-proof sampling and 11 and 19 from
search, across two sampling budgets each. The authors note the counts should not be
read as a property of the search procedure (arXiv:2608.28639).

So the ASPICE sentence names the right obligation and leaves the mechanism open. Making review mechanical is the open
problem, and it is open in a standards sense as well as a technical one.

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
to 1 May 2026. That guidance is about securing agents, through
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
other TAGs, and a group's published pages are weaker evidence than its minutes. Eclipse S-CORE publishes no AI policy of its
own, but it does not need to: it inherits the Eclipse Foundation's Generative AI
Usage Guidelines, v1.0 of April 2024, which require a committer to make reasonable
effort to ensure generated content is accurate and to put all output through the
project's normal vetting for testing, intellectual property and security. A
project-level policy template requiring contributors to validate generated code
before submission exists as a proposed draft rather than an adopted rule, and the
guidelines are written for committers rather than all contributors.

So the review obligation is already stated at open-source governance level, which
makes the gap sharper rather than wider. Eclipse says vet the output. ASPICE says
verify the output. DO-178C says qualify the tool unless the output is verified.
Nobody says what the verification has to produce, or how anyone would check that it
happened.

One room is closest to it. The COVESA Generative AI Group's stated mission is
making generative AI tooling "interoperable, standardized, and accessible across
the entire automotive V-model", organised by V-model stage from requirements to
homologation, aligning with AUTOSAR, ISO 26262 and ASPICE. Its current pilot stage is
requirements management, and it is still finalising its charter.

A charter being written now will shape whether "review the AI output" stays a
process statement or acquires a defined artifact. The
group listed charter and operating procedures as in progress when we read its page
on 14 October 2026.

## References

Every item below was opened and read, except where the entry says otherwise.
Numbers quoted in the post were checked against the source rather than against a
summary of it.

### Research

1. Agarwal et al., *Verus-SpecGym: An Agentic Environment for Evaluating
   Specification Autoformalization*, arXiv:2605.26457, 26 May 2026.
   <https://arxiv.org/abs/2605.26457>
2. Ma et al., *SWE-Proof: Can Language Models Resolve Real-World Issues with
   Machine-Checked Proofs?*, arXiv:2609.21190, 18 September 2026.
   <https://arxiv.org/abs/2609.21190>
3. Tan, *Automating Formal Verification with Reinforcement Learning and Recursive
   Inference*, arXiv:2605.30914, 29 May 2026. A master's thesis, not peer reviewed.
   <https://arxiv.org/abs/2605.30914>
4. Woodcock, Leite, Sampaio and Wei, *CAPRI: Contract-Aware Proof Repair for
   Isabelle*, arXiv:2608.13459, 13 August 2026. <https://arxiv.org/abs/2608.13459>
5. Bodla and Yang, *Reward-Oracle MCTS for Formal Theorem Proving: Sample-Efficient
   Search and the Need for Kernel-Level Proof Auditing*, arXiv:2608.28639,
   11 August 2026. <https://arxiv.org/abs/2608.28639>

### Standards and regulatory documents

6. ISO/IEC TR 5469:2024, *Artificial intelligence — Functional safety and AI
   systems*. Technical Report, published 8 January 2024.
   <https://committee.iso.org/standard/81283.html>
7. ISO/PAS 8800:2024, *Road vehicles — Safety and artificial intelligence*.
   Published 13 December 2024. <https://committee.iso.org/standard/83303.html>
8. ISO 26262-8:2018, *Road vehicles — Functional safety — Part 8: Supporting
   processes*. At stage 90.92, "to be revised", since 8 July 2024.
   <https://committee.iso.org/standard/68390.html>
9. ISO/IEC TS 22440 (in parts), *Functional safety and AI systems*. Committee Draft,
   comment period closed April 2026. The ISO pages returned HTTP 403 to us, so the
   stage detail in this post is second-hand.
10. DO-330 / ED-215, *Software Tool Qualification Considerations*. Corrigendum 1
    announced 15 February 2021; catalogues disagree on whether the original is dated
    2011 or 2012. We have not read the standard.
    <https://www.eurocae.net/product/ed-215-software-tool-qualification-considerations/>
11. RTCA Program Management Committee summaries, 16 December 2025 and 10 March 2026.
    Source for SC-240's accepted plan for future work on DO-330, DO-331 and DO-248C.
    <https://www.rtca.org/wp-content/uploads/2026/03/2-A-PMC-Summary-2025-12-16_approved.pdf>
12. ED-324 / SAE ARP6983 status, from slides presented at the EASA AI Days,
    9 and 10 September 2026. The consensus date, the Q4 2026 listing and the IDAL C
    scope come from that deck, not from a published standard.
    <https://www.easa.europa.eu/en/downloads/144162/en>
13. EASA, *Artificial Intelligence Concept Paper, Proposed Issue 03*. Released for
    consultation 3 June 2026, comments closed 12 August 2026.
    <https://www.easa.europa.eu/en/newsroom-and-events/news/easa-releases-latest-issue-its-concept-paper-artificial-intelligence>
14. VDA QMC Working Group 13, *Automotive SPICE Guidelines*, 3rd edition, dated
    July 2026 on VDA's publications page after a public review that ran to
    12 May 2026. **We have not read the VDA text.** Everything this post says about
    its AI chapter is second-hand and flagged as such in the body.
15. CISA, NSA, ASD ACSC, Canadian Centre for Cyber Security, NZ NCSC and UK NCSC,
    *Careful Adoption of Agentic AI Services*, 1 May 2026.
    <https://www.cisa.gov/resources-tools/resources/careful-adoption-agentic-ai-services>
16. European Commission, AI Act Service Desk FAQ, *How are AI agents addressed
    within the AI Act?* The page describes the Commission's views as preliminary.
    <https://ai-act-service-desk.ec.europa.eu/en/faq>

### Projects

17. Eclipse S-CORE project site. Source for the ASPICE, ISO 26262 and ISO 21434
    listing and for the absence of an AI policy. <https://eclipse.dev/score/>
18. COVESA Generative AI Group. Source for the mission statement, the requirements
    management pilot stage and the charter status, read 14 October 2026.
    <https://covesa.atlassian.net/wiki/spaces/WIK4/pages/176029697/Generative+Artificial+Intelligence+AI+Group>

### What we could not establish

Four things in this area resisted checking, and we would rather name them than imply
coverage we do not have. `iso.org` returns HTTP 403 to automated readers, so the ISO
entries above were read on the committee mirror. `faa.gov` returned HTTP 403 on every
attempt, so FAA policy and the FAA AI safety assurance roadmap are absent from this
post rather than assessed. `autosar.org` failed with a TLS certificate error, so
AUTOSAR is genuinely unknown to us here. And the negative claims about which
working groups have no AI-agent workstream rest on the pages those groups publish,
which is weaker evidence than their meeting minutes would be.
