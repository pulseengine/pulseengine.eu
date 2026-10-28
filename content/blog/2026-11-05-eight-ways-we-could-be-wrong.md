+++
title = "Eight ways we could be wrong"
description = "The eight strongest objections to PulseEngine we know of, each with the date of its evidence, how the picture moved in the last six months, our counter, where the counter stops, and what would make us concede. Valid as of 28 October 2026."
date = 2026-11-05
draft = true
[taxonomies]
tags = ["deep-dive", "process", "verification", "ai-agents"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**These are the eight strongest objections to PulseEngine we know of, and each one is dated.**

- Every objection names when its evidence was published and how the picture
  moved since. The debate in April 2026 was a different debate: no Black Hat
  disclosure and no WASI 0.3 release.
- Two objections are stronger now than six months ago (agents as an attack
  surface, verification giving false confidence). One is weaker (building on
  an unfinished standard). One we concede outright: our own gates do not run
  on our own engine yet.
- Each objection ends with what would make us concede it. If you have a
  stronger objection, open an issue and we will add it with its date.
{% </insight> %}

PulseEngine is a WebAssembly Component Model engine for safety-critical
systems, built largely by AI agents under one owner, and everything in it is
work in progress. The two posts before this one,
[on attention](/blog/the-scarce-resource-is-attention/) and
[on trust at machine speed](/blog/trust-at-machine-speed/), each closed with
a short section on what a critic would say. This post collects the critic's
case in one place and gives it room.

Each section gives the objection and its dated evidence, how the evidence
moved, our counter, where the counter stops, and dates for when it was read
and when to read it again.

## The timeline

The dated evidence behind each objection, in order. The line at 28 April 2026 marks six months before the evidence
date of this post.

| Date | Event | Objection |
|---|---|---|
| 2016-04-22 | Avelino et al. estimate truck factors for 133 GitHub projects[^avelino] | 5 |
| 2022-09 | AssemblyScript publishes its objections to WASI and the Component Model[^assemblyscript] | 6 |
| 2025-05-29 | VERINA v1: best model o4-mini, 3.6% proof success[^verina-v1] | 2 |
| 2025-06-30 | MISRA C++ study of LLM-generated code, v1[^misra] | 3 |
| 2025-07-12 | METR randomised trial, v1: AI tools made experienced developers 19% slower[^metr-rct] | 4 |
| 2025-07-17 | Peter Bernard Ladkin on the SystemSafety list: LLM-written procedural code cannot meet the standards[^ladkin] | 3 |
| 2025-11-18 | MISRA C++ study, v2[^misra] | 3 |
| 2026-02-09 | Clinejection disclosed by Adnan Khan[^clinejection]; ISO/IEC CD TS 22440-1 registered[^iso22440] | 1, 3 |
| 2026-02-17 | Tampered `cline@2.3.0` published with a stolen npm token[^clinejection] | 1 |
| 2026-02-24 | METR says it is changing its experiment design and calls its newer data unreliable[^metr-2026] | 4 |
| 2026-03-16 | VERINA v3: best model o3, 4.9% proof success[^verina] | 2 |
| 2026-04-11 | Comment period on ISO/IEC CD TS 22440-1 closes[^iso22440] | 3 |
| 2026-04-24 | Google advisory GHSA-wpqr-6v78-jr5g for Gemini CLI, rated critical[^gemini-ghsa] | 1 |
| **2026-04-28** | **Six months before this post's evidence date** | |
| 2026-05-07 | Political agreement on the AI Act's Digital Omnibus[^ec-omnibus] | context |
| 2026-06-08 | Bytecode Alliance: the road to Component Model 1.0[^cm-road] | 6 |
| 2026-06-11 | WASI 0.3.0 released[^wasi03] | 6 |
| 2026-07-27 | Digital Omnibus on AI enters into force[^ec-ai-act] | context |
| 2026-08-05 | Novee Security at Black Hat USA 2026, reported in a CSA note of 8 August[^csa-blackhat] | 1 |
| 2026-08-11 | WASI 0.3.1 released[^wasi-p3] | 6 |
| 2026-10-19 | Formal-mathematics survey, v2[^solvers] | 2 |
| 2026-10-22 | Our hotspot experiment pre-registered | 4 |
| 2026-10-28 | Our agent workflows audited and first fix merged (plugin 0.45.1, 0.45.2); `claim-check.py` negative control; hotspot trigger shipped; review records required (#275); issue #287 opened | 1, 2, 4, 7, 8 |

The two AI Act rows are context for objection 3 rather than evidence for any
one objection. In April 2026 these dates were not yet agreed. Since the
agreement, the high-risk rules apply from 2 December 2027 for systems in areas such as critical infrastructure, and from 2 August
2028 for AI systems built into regulated products such as lifts or
toys[^ec-omnibus].

## 1. "Your agents are the attack surface"

**The objection and its evidence.** PulseEngine runs agents that read issue
trackers, write code and open pull requests. According to a Cloud Security
Alliance research note, itself AI-assisted, an issue title in the
Clinejection case reached the prompt of a triage agent that had shell access
and was open to any GitHub user. The note traces the chain through cache
poisoning to leaked publishing credentials, and on 17 February 2026 someone
used a stolen npm token to publish a tampered `cline@2.3.0`[^clinejection].
Google's advisory for Gemini CLI, published 24 April 2026, rates critical a
flaw that let headless runs on untrusted content execute attacker-supplied
code[^gemini-ghsa]. On 5 August 2026 Novee Security gave a security research
demonstration at Black Hat USA. A second Cloud Security Alliance note, which
says of itself that it was generated with AI assistance and "has not
undergone official CSA review and approval processes", reports that the
researchers reached CI secrets in the vendors' own repositories for Claude
Code, Gemini CLI and OpenAI Codex from an issue opened by an account with no
repository rights[^csa-blackhat].

**How it moved.** This objection is stronger now than in April. Six months
ago the evidence was one incident in one project and the first published
piece of Novee's research: the Gemini CLI advisory, which credits Elad Meged
of Novee Security[^gemini-ghsa] and which the CSA note ties to the 5 August
talk. August added Claude Code and Codex, reached in the three vendors' own
repositories, and the note reports comparable configurations in well over a
hundred other public repositories[^csa-blackhat].

**Our counter.** On 28 October 2026 we audited our own agent workflows
against this class of attack and fixed one finding the same day.
Skills no longer execute commands taken from issue text, and issue, PR and
comment text is treated as untrusted data, never as instructions. The fix
shipped as plugin 0.45.1 and 0.45.2 in
[#288](https://github.com/pulseengine/pulseengine.eu/pull/288) and
[#289](https://github.com/pulseengine/pulseengine.eu/pull/289). The rule is a
claim in this repository's `claims.yaml` (`ISSUE-TEXT-IS-UNTRUSTED-DATA`),
so a skill that again uses one of the instruction phrasings the claim forbids
fails the build.

**Where the counter stops.** The audit's other findings are open. The audit was our own; nobody outside the
project has reviewed our agent workflows. A rule in a skill constrains an
agent that follows the skill; it does not stop a model that ignores it. Valid
as of 28 October 2026; re-check by 28 January 2027, because this
is the fastest-moving of the eight.

## 2. "Verification gives false confidence"

**The objection and its evidence.** A proof is only as good as its
statement, and with models writing both the statement and the proof, the
statement is the weak part. On the VERINA benchmark, v3 of March 2026, the
best model, OpenAI o3, wrote correct code for 72.6% of tasks, sound and
complete specifications for 52.3% and successful proofs for 4.9%, based on
one trial per task[^verina]. A survey of model-driven formal mathematics puts
the gap plainly: "A formal statement can elaborate successfully while still
mistranslating its informal source"[^solvers]. A reader who sees "proved"
may take it to mean "correct", and the two differ by exactly the
specification.

**How it moved.** VERINA v1 of May 2025 reported its best model, then
o4-mini, at 61.4% code, 51.0% specifications and 3.6% proofs[^verina-v1].
Between v1 and v3 the best model changed and code correctness rose by about
11 points, while specification quality rose by 1.3 points and proof success
by 1.3. Models got better at writing code much faster than at stating what
the code should do. The objection is stronger than in April: the survey
(July 2026, revised 19 October[^solvers]) adds to the evidence that
specifications are the bottleneck.

**Our counter.** We try to see a check fail before we rely on it. On 28
October 2026 we did that for one of the 41 claims: we changed one pinned
sentence in the operating contract that
`ISSUE-TEXT-IS-UNTRUSTED-DATA` binds. `claim-check.py` reported 40 of 41
claims holding and exited 1; with the change reverted it reported 41 of 41.
Claims in `claims.yaml` are written so they can fail, and the gale
repository keeps a
[verification-honesty ledger](https://github.com/pulseengine/gale/blob/main/docs/safety/verification-honesty.md)
that lists what its proofs do not cover and which words not to use about
them. The site's tagline says "machine-checked proofs for parts of it"
because a claim in `claims.yaml` fails the build on the broader phrasings.

**Where the counter stops.** `claims.yaml` pins text and patterns, not
behaviour. A claim can hold while the system it describes is wrong, if the
sentence and the evidence drift together. A negative control shows the check
can fail; it does not show the specification is the right one. Valid as of
28 October 2026; re-check by 28 April 2027 or at VERINA's next version.

## 3. "You can't certify LLM-written code"

**The objection and its evidence.** On 17 July 2025, replying to Les
Chambers on the SystemSafety mailing list, Peter Bernard Ladkin argued that
safety-critical
code is governed by standards (DO-178C, ISO 26262, IEC 61508), and that if
you ask whether LLM-written procedural code can meet them, the quick answer
is no. IEC 61508 Part 3 has over 50 documentation requirements, he wrote; an
LLM might claim to have met them all, but "no wetware will take such a claim
seriously"[^ladkin]. An arXiv study of C++ from five assistants found that
"none of the evaluated LLMs generated MISRA-compliant code despite clear
prompts"[^misra].

**How it moved.** Little. We read the list's 2026
monthly archives that were online on 28 October 2026 (July and August were
not) and found no later post by Ladkin on this question. The standard he
pointed to for neural networks, ISO/IEC TS 22440, is still a draft: Part 1
was registered as a committee draft on 9 February 2026 and its comment
period closed on 11 April 2026[^iso22440]. By Ladkin's description it covers
encapsulated neural-network modules in critical systems, not procedural code
written with a model's help, so it does not answer this objection either way.
The MISRA study's v2 is from November 2025 and tested 2025 assistants; we
have not checked whether newer models do better.

**Our counter.** We agree with Ladkin's sentence: a model's claim to have met
a requirement is worth nothing. That is why our claims are bound to evidence
a script can re-derive. Our argument is that certification judges whether
lifecycle objectives were met and evidenced, and none of those objectives
names who or what typed the code, so model-written code is held to the same
objectives, including the documentation Ladkin points to. Any tool whose
output is not checked again, whether it generates code like synth or checks
it, needs qualification under RTCA DO-330, the tool qualification guidance
used with DO-178C[^do330]. For a code generator that means its own
development is held to lifecycle objectives, which puts this objection
squarely on synth and meld.

**Where the counter stops.** Nothing in PulseEngine is certified or
qualified. Tool-qualification records exist in the public
[relay](https://github.com/pulseengine/relay/blob/main/docs/dossier/tool-qualification/README.md)
and
[rivet](https://github.com/pulseengine/rivet/blob/main/docs/reference/tool-qualification.md)
repositories; no assessor has reviewed them. No assessor has accepted this
argument for our code. Valid as of 28 October 2026; re-check
by 28 April 2027 or when ISO/IEC TS 22440-1 moves to its next stage.

## 4. "Your productivity is a feeling"

**The objection and its evidence.** In METR's randomised trial, published in
July 2025, 16 experienced open-source developers worked 246 tasks in mature
projects. With early-2025 AI tools they took 19% longer, after forecasting a
24% saving and while estimating afterwards that they had saved
20%[^metr-rct]. If experienced developers cannot tell a slowdown from a
speedup, an owner who feels his agent factory is fast is not evidence.

**How it moved.** On 24 February 2026 METR said it was changing its
experiment design.
Its follow-up, run from August 2025 with 57 developers, gave point estimates
of 18% and 4% faster for two groups, with confidence intervals that include a
slowdown, and METR called the data "an unreliable signal of the current
productivity effect of AI tools"[^metr-2026]. The main reason was selection:
more developers declined to work without AI. METR thinks developers were
probably more sped up in early 2026 than in early 2025 and says its data is
only very weak evidence for how much. So the 19% is a historical result for
early-2025 tools. The objection was sharper in late 2025, when that slowdown
was the latest number, and it is still unanswered: no one has a reliable
number in either direction.

**Our counter.** We do not publish productivity figures, and where we claim
that a process change has an effect, we pre-register the test. On 22 October
2026 we pre-registered an
[experiment](https://github.com/pulseengine/pulseengine.eu/blob/main/docs/experiments/2026-10-hotspot-trigger.md)
on a fix-hotspot trigger in rivet, with spar as the control, before the
trigger existed. Its four criteria and window are bound by a claim in
`claims.yaml`, so changing a threshold fails the build unless the claim
changes in the same pull request. The
trigger shipped on 28 October 2026, and the window is November 2026 to
January 2027.

**Where the counter stops.** It is n=1: one factory, one owner, one treated
repository and one control. The experiment measures refactoring share and fix
counts on one file, not productivity, so even a clean pass would not answer
METR. Valid as of 28 October 2026; re-check by 28 February 2027, after the
window's results are in.

## 5. "Bus factor 1"

**The objection and its evidence.** PulseEngine has one owner who decides
what is built and publishes what ships. If he stops, the agents stop with
him. Being small is common: Avelino and colleagues estimated truck factors
for 133 popular GitHub projects in 2016 and found that 65% had a truck factor
of two or less[^avelino]. Being common is no comfort to a buyer who needs a
supplier for the life of a safety-critical product.

**How it moved.** It has not. The 2016 figure is old, and we cite it only to
show the risk is ordinary, not to measure ours.

**Our counter.** What gets built and how it is checked is written where a
successor can read it. Requirements, design links and verification measures live in
rivet; load-bearing claims live in `claims.yaml` with their evidence; release
archives of witness and varve carry signatures that anyone can check without
a key from us; and the
agents' working rules live in this repository's plugin as skills and memory
files, which a new owner's agents would load the same way.

**Where the counter stops.** Design decisions are the gap. Why a component
boundary sits where it does, which trade-offs were rejected and why, mostly
live in the owner's head and in chat sessions that are not kept. Nobody has
tried to take over a PulseEngine tool from its artifacts alone, so the
counter is untested. Valid as of 28 October 2026; re-check by 28 April 2027.

## 6. "You build on an unfinished standard"

**The objection and its evidence.** The Component Model has no 1.0. Its
repository describes it as developed incrementally through WASI "Developer
Preview" releases[^cm-readme]. The Bytecode Alliance names "a stable,
formally specified Component Model 1.0" as the next milestone and gives no
date for it[^cm-road]. The AssemblyScript project has objected to the
Component Model since September 2022, arguing among other things that it is
not defined in the same semantic framework as core
WebAssembly[^assemblyscript].

**How it moved.** This objection is weaker than in April, when WASI 0.3 was
still a release candidate. WASI 0.3.0 was ratified and released on 11 June
2026, which the Bytecode Alliance calls official[^wasi03]. The same release
shows the churn: it removed `wasi:io` entirely and moved async into the
Component Model, and 0.3.1 on 11 August 2026 required further Component
Model features, including a `map` type[^wasi-p3].

**Our counter.** On PulseEngine's ahead-of-time path, meld fuses components
into a single core module at build time and synth transcodes it to native
code for embedded targets. For a module that is fully dissolved and imports
no WASI interfaces, the resulting binary does not depend on a runtime's
Component Model implementation. Our tools ship as signed, dated varve
layers, and a project pins one, so a change in the standard reaches a
project only when the project moves its pin.

**Where the counter stops.** Standard churn still moves our stack. meld has
to follow each change in the Component Model, and its README describes its
lowering of P3 async as partial. synth's README says WASI on embedded
targets needs kiln-builtins, which does not exist yet, and that piece will
have to follow the standard. A project that wants a new WASI feature has to
move its pin and take everything else with it.
varve's qualified channel is not open yet, and today's layers are signed with
a provisional rolling key that makes no qualification promise. Valid as of
28 October 2026; re-check by 28 April 2027 or at Component Model 1.0.

## 7. "You don't use your own engine"

**The objection and its evidence.** We argue that components are the
trustworthy way to run code, and the code that decides whether our own claims
hold is unsigned Python. `claim-check.py` and the answer validation in the
factory's notice inbox run with the user's full permissions. The objection
dates from our own critic review on 28 October 2026 and is recorded as
[issue #287](https://github.com/pulseengine/pulseengine.eu/issues/287).

**How it moved.** It is new: six months ago none of these gates existed in
their current form.

**Our counter.** None yet. Issue #287 proposes moving the gates into WASI
components with no network, no subprocesses and no writes, signing them with
sigil, and running them under wasmtime first. kiln, our interpreter and
runtime, is the planned second host, and requiring both hosts to agree would
make our own gates a differential test of our engine.

**Where the counter stops.** We concede this objection. It is true until
#287 is done. Valid as of 28 October 2026; re-check when #287 closes.

## 8. "Agents reviewing agents isn't independence"

**The objection and its evidence.** Our posts and many of our pull requests
are reviewed by fresh-context agents in split roles. A reviewer from the same
model family as the author can share its blind spots, and a label saying
"independent review" hides that. No standard we work to treats an AI
reviewer as an independent assessor.

**How it moved.** The objection has not moved; our practice has. On 28 October
2026, in [#275](https://github.com/pulseengine/pulseengine.eu/pull/275), the
`clean-room-verification` skill started requiring a record for every review
used as evidence: reviewer model, whether it inherited context, run id,
reviewed commit, date and outcome. A review missing a field counts as
absent, and the skill says to hand the reviewer a deliberately poisoned
claim at least once per release whose gate rests on AI review, and confirm
it refutes it.

**Our counter.** The record makes the review checkable. A reader can see
which model reviewed which commit, with what context, and what it found. The
pull request that ships this post carries that record for its own panel. The
human step is the owner deciding to publish a post.

**Where the counter stops.** The reviewers share a model family with the
author, and recording that fact does not make them independent. The review is
advisory; it is not an assessment. Valid as of 28 October 2026; re-check by
28 April 2027.

## What would make us concede

| # | Objection | We concede if |
|---|---|---|
| 1 | Agents are the attack surface | Text in an issue, PR or comment makes one of our agent workflows run a command or follow an instruction after plugin 0.45.2, or any finding of this class, ours or reported to us, stays unfixed 30 days after it is known |
| 2 | Verification gives false confidence | Someone shows a claim in `claims.yaml` holding green while the property it states is false, and that false claim was live on the site or in a release |
| 3 | You can't certify LLM-written code | An assessor or authority states that a DO-330 route is closed to tools built this way, for reasons rooted in how the code was written, or an assessor rejects model-written product code that meets the same objectives |
| 4 | Productivity is a feeling | The hotspot experiment fails its pre-registered criteria and we still claim the trigger works, or anyone finds a productivity figure of ours with no measurement behind it |
| 5 | Bus factor 1 | Someone competent tries to build and release one PulseEngine tool from its repository and artifacts alone and cannot |
| 6 | Unfinished standard | A pinned project has to move its pin to get a fix, and the move forces a Component Model or WASI migration it did not choose |
| 7 | You don't use your own engine | Conceded until #287 is done |
| 8 | Agents reviewing agents | A human or a reviewer from another model family finds a blocking error in a post our panel cleared |

If you have a stronger objection than these eight, or better evidence for one
of them, open an issue on the
[pulseengine.eu tracker](https://github.com/pulseengine/pulseengine.eu/issues).
We will add it to the next version of this list with its date, whether or not
we have a counter. For a security hole in our agent workflows, do not post
exploit details in a public issue; open an issue asking for a private
contact.

## Sources and caveats

All sources were read on 28 October 2026. Quotations are checked word for
word against the primary page. The Black Hat findings are known to us only
through the Cloud Security Alliance note, which describes itself as
AI-assisted and not officially reviewed; we did not read Novee Security's own
write-up. The Clinejection note is also AI-assisted. The ISO page for ISO/IEC TS 22440-1 refused our client, and its
stage dates were read from ISO's committee mirror. We dropped a NASA position
on LLMs in safety-critical development, reported by a vendor blog we could not
load, and Lean soundness issues, for which we found no primary source. The
PulseEngine statements come from this repository, the gale, meld, synth,
varve and witness READMEs and releases, and one `claim-check.py` run on 28 October 2026.

[^avelino]: Guilherme Avelino, Leonardo Passos, Andre Hora and Marco Tulio Valente, *A Novel Approach for Estimating Truck Factors*, 24th International Conference on Program Comprehension (ICPC), 2016; arXiv:1604.06766, 22 April 2016. [arxiv.org](https://arxiv.org/abs/1604.06766). Peer-reviewed (conference paper, read as the arXiv preprint). Source of the 133 projects and the 65%.

[^assemblyscript]: AssemblyScript, *Standards objections*, sections "WASI, 2022-09" and "Component Model, 2022-09". [assemblyscript.org](https://www.assemblyscript.org/standards-objections.html). Primary (project position page). The page shows no last-updated date.

[^verina-v1]: Zhe Ye, Zhengxu Yan, Jingxuan He, Timothe Kasriel, Kaiyu Yang and Dawn Song, *VERINA: Benchmarking Verifiable Code Generation*, arXiv:2505.23135, v1, 29 May 2025. [arxiv.org](https://arxiv.org/abs/2505.23135v1). Primary (benchmark paper). Figures from the v1 abstract.

[^verina]: The same paper, v3, 16 March 2026. [arxiv.org](https://arxiv.org/abs/2505.23135v3). Primary (benchmark paper). Figures from the v3 abstract; v2 is dated 18 October 2025.

[^misra]: Malik Muhammad Umer, *Comparative Analysis of the Code Generated by Popular Large Language Models (LLMs) for MISRA C++ Compliance*, arXiv:2506.23535, v1 30 June 2025, v2 18 November 2025. [arxiv.org](https://arxiv.org/abs/2506.23535). Primary (preprint, not peer-reviewed). The assistants tested were ChatGPT, Gemini, DeepSeek, Meta AI and Microsoft Copilot.

[^metr-rct]: Joel Becker, Nate Rush, Elizabeth Barnes and David Rein, *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity*, arXiv:2507.09089, v1 12 July 2025, v2 25 July 2025. [arxiv.org](https://arxiv.org/abs/2507.09089). Primary (randomised controlled trial). Source of the 16 developers, 246 tasks, 19%, 24% and 20%.

[^metr-2026]: Joel Becker, Nate Rush, Tom Cunningham, David Rein and Khalid Mahamud, *We are Changing our Developer Productivity Experiment Design*, METR, 24 February 2026. [metr.org](https://metr.org/blog/2026-02-24-uplift-update/). Primary (research update). Source of the 57 developers, the two point estimates (−18%, confidence interval −38% to +9%; −4%, CI −15% to +9%, where negative means faster), and the selection explanation.

[^ladkin]: Peter Bernard Ladkin, *[SystemSafety] AI Hallucination Cases*, SystemSafety mailing list, 17 July 2025. [lists.techfak.uni-bielefeld.de](https://lists.techfak.uni-bielefeld.de/pipermail/systemsafety/2025-July/006228.html). Primary (list archive). A reply to Les Chambers; source of the standards named, the 50 documentation requirements and the description of ISO/IEC 22440.

[^iso22440]: ISO/IEC CD TS 22440-1, *Artificial intelligence — Functional safety and AI systems — Part 1: Requirements*, lifecycle record. [committee.iso.org](https://committee.iso.org/standard/89535.html). Primary (ISO lifecycle record; www.iso.org returned 403). Stage 30.60, close of comment period, 11 April 2026; committee draft registered 9 February 2026.

[^do330]: RTCA, *DO-330: Software Tool Qualification Considerations*, 13 December 2011. [my.rtca.org](https://my.rtca.org/productdetails?id=a1B36000001IcfkEAC). Primary (product page only; the standard is paywalled and was not read).

[^clinejection]: Cloud Security Alliance AI Safety Initiative, *Clinejection: Prompt Injection in GitHub Issue Titles Enables CI/CD Cache Poisoning and Supply Chain Compromise*, research note, 10 March 2026. [labs.cloudsecurityalliance.org](https://labs.cloudsecurityalliance.org/research/csa-research-note-clinejection-prompt-injection-cicd-cache-p/). Secondary, and AI-assisted: the note says it was generated with AI assistance and has not undergone official CSA review. It reports Adnan Khan's disclosure of 9 February 2026. Source of the 9 and 17 February dates and the chain.

[^gemini-ghsa]: Google, *Gemini CLI: Remote Code Execution via workspace trust and tool allowlisting bypasses*, GitHub security advisory GHSA-wpqr-6v78-jr5g, 24 April 2026. [github.com/advisories](https://github.com/advisories/GHSA-wpqr-6v78-jr5g). Primary (vendor advisory).

[^csa-blackhat]: Cloud Security Alliance, *Three AI Coding Agents, One GitHub Issue: CI/CD Secrets Exposed*, research note, 8 August 2026. [labs.cloudsecurityalliance.org](https://labs.cloudsecurityalliance.org/wp-content/uploads/2026/08/CSA_research_note_ai_coding_agent_cicd_secrets_20260808-csa-styled.pdf). Secondary, and AI-assisted: the note says it was generated with AI assistance and has not undergone official CSA review. It reports Novee Security's Black Hat USA talk of 5 August 2026.

[^solvers]: Eric Jiang et al., *From Solvers to Research: Large Language Model-Driven Formal Mathematics at the Research Frontier*, arXiv:2607.07779, v1 8 July 2026, v2 19 October 2026. [arxiv.org](https://arxiv.org/abs/2607.07779). Primary (survey and position paper). The quotation is from section 2.5 of v2.

[^cm-readme]: WebAssembly Community Group, *Component Model* repository README. [github.com/WebAssembly/component-model](https://github.com/WebAssembly/component-model). Primary (specification repository). Lists 0.2.0, 0.3.0 and 0.3.1 as the current Developer Preview releases.

[^cm-road]: Eric Gregory, *The Road to Component Model 1.0*, Bytecode Alliance, 8 June 2026. [bytecodealliance.org](https://bytecodealliance.org/articles/the-road-to-component-model-1-0). Primary (project blog). Gives no target date; says WASI 1.0 follows Component Model 1.0.

[^wasi03]: Bailey Hayes and Yosh Wuyts, *WASI 0.3 Launched*, Bytecode Alliance, 11 June 2026. [bytecodealliance.org](https://bytecodealliance.org/articles/WASI-0.3). Primary (project blog). Source of the ratification by the WASI Subgroup.

[^wasi-p3]: WASI, *WASI 0.3* release page. [wasi.dev](https://wasi.dev/releases/wasi-p3). Primary (release notes). Source of the 11 June and 11 August 2026 dates, the removal of `wasi:io` and the 0.3.1 Component Model requirements.

[^ec-omnibus]: European Commission, *EU agrees to simplify AI rules to boost innovation and ban 'nudification' apps to protect citizens*, press release IP/26/1024, 7 May 2026. [ec.europa.eu](https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1024). Primary (official press release). Source of the agreement date and the two application dates.

[^ec-ai-act]: European Commission, *AI Act*, Shaping Europe's digital future. [digital-strategy.ec.europa.eu](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai). Primary (official policy page). Source of the entry into force on 27 July 2026.

---

*This post is part of [PulseEngine](/) — a WebAssembly Component Model engine
for safety-critical systems, with machine-checked proofs for parts of it
(work in progress).*
