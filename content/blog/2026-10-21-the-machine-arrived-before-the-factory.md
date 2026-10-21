+++
title = "The machine arrived before the factory"
description = "Software has called itself a factory since 1968. It never was one, because its production step was a person. Agents turn that step into a machine, and they arrive before the standards a factory depends on: checks that can fail, one source per fact, flow limits, process measurement. What research, practitioners and standards bodies say, and every repository PulseEngine authors, measured from git and the issue trackers."
date = 2026-10-21
draft = false
ready = true
[taxonomies]
tags = ["verification", "process", "ai-agents", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
**Agents are the machine. The factory is everything that checks them, and it has not been built yet.**

- Manufacturing built its standards before its machines. Software got the machine first.
- In PulseEngine's own repositories the gaps are concrete: checks that pass without checking, the same fact computed in several places, and a backlog that outruns the decisions.
- Each gap has a mechanical answer older than software. Four things stay human: deciding what correct means, deciding what no oracle can, acting on an alarm, and the signature.
{% end %}

## Three positions

Three pieces from the last four months describe AI in software development from three directions. Dex Horthy's talk at the AI Engineer World's Fair on 30 June 2026 argues that a lights-off software factory, one where nobody reads the code, fails within months[^horthy]. Coding models are trained with rewards for passing tests, nothing in that reward measures maintainability, and in HumanLayer's experience a code base nobody reads starts to defeat its agents after three to six months. His remedy is planning up front and reading every line again.

David Heinemeier Hansson's opening keynote at Rails World in Austin on 23 September 2026 takes the other side[^dhh]. He calls Opus 4.5, released on 24 November 2025, the Kodak Brownie of software. 37signals has stopped writing code by hand, and a hand-written change is now treated like an exception in an error tracker, a sign that the agent setup needs fixing. He evaluates the Rust his agents write from the outside, the way a business owner evaluates commissioned work, and argues that abstractions matter less now that repetition and keeping copies in sync have become cheap.

Gergely Orosz collected AI spending and pull-request data from 27 companies, published on 20 October 2026[^orosz]. Outside Big Tech, spend per engineer ranged from under $300 to $3,000 a month and was unrelated to company size. Pull-request counts roughly doubled on CodeRabbit's platform, stayed flat at a 5,000-person company where the average change tripled in size, and at a 600-engineer SaaS company a staff engineer reported that speed barely moved once the team kept its previous quality bar. Few of the companies could say whether the spending paid back.

All three describe people and agents. None measures the system the code is produced in, and that system is what makes a factory a factory.

## A term from 1968

At the NATO Software Engineering conference in Garmisch in October 1968, Doug McIlroy gave a talk titled "Mass produced software components"[^mcilroy]. One of its section headings states that the software industry is not industrialized, and he compared his colleagues with the hardware engineers: "we are the crofters", they "the industrialists". His proposal was an industry of standard component families.

The same five days produced another word that is still in use, and it undercuts McIlroy's proposal from the next seat along. Presenting what the proceedings label d'Agapeyeff's Inverted Pyramid, Alex d'Agapeyeff described a stack with control programs at the bottom, service routines above them, application programs on top, and assemblers and compilers as buttresses that "don't help to maintain the thing, but if they fail you have a skew". Between the service routines and the applications he put a layer he had to name: "Further up we have what I call middleware."[^dagapeyeff] His reason for needing it is the part worth reading next to McIlroy. However good the manufacturer's software for something like file handling was, it was "just not suitable; it's either inefficient or inappropriate", so his teams rewrote the file handling, the initial message analysis and above all the real-time schedulers. One conference proposed an industry of standard reusable components and coined a name for the layer people write because the standard components do not fit.

Hitachi, Toshiba, NEC and Fujitsu launched organisations they called software factories between the late 1960s and the late 1970s, with standard methods, reuse goals and metrics[^cusumano-wp]. Michael Cusumano studied them in detail and published the book-length account in 1991[^cusumano]. One of his findings from the cooperative tool projects of the 1970s and 1980s reads like a warning for today: tools alone had limited value, and firms needed their own management and training infrastructure to get anything out of them.

All of them still had a person at the production step. The 1968 study DHH cites in his keynote put the spread between programmers at five to thirty times on the same task. A process whose central machine varies by an order of magnitude cannot be scheduled or inspected like a production line, which is why estimates kept missing and defects kept surfacing late. Continuous integration added conveyors around that step. The step itself stayed a workshop.

## The machine arrived first

In manufacturing the order was standard work and division of labour first, the machine second. The manufactory came before the factory, and by the time machines arrived there were specifications, gauges and inspection to put them into. Software receives the machine first. The standards a factory presupposes were never built, because people absorbed the ambiguity: specifications that can be checked mechanically, gates that can fail, flow control between stations, measurement of the process rather than the product.

<figure class="standards-map">
<svg viewBox="0 0 760 330" width="100%" role="img" aria-labelledby="fo-title fo-desc" style="max-width:760px;height:auto;font-family:'Atkinson Hyperlegible Next',system-ui,sans-serif">
<title id="fo-title">The same four stations, in a different order</title>
<desc id="fo-desc">Manufacturing went from craft workshop to manufactory, with standard work and inspection, then to the machine, then to the factory. Software went from craft workshop to conveyors such as continuous integration, then received the machine in the form of coding agents, while the manufactory step of standard work, checks that can fail, flow limits and process measurement is still missing.</desc>
<defs>
<marker id="fo-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
<path d="M0,0 L10,5 L0,10 z" fill="var(--text-dim,#8b90a0)"/>
</marker>
</defs>
<text x="12" y="30" font-size="13" font-weight="700" fill="var(--text,#e1e4ed)">Manufacturing</text>
<text x="12" y="46" font-size="10.5" fill="var(--text-dim,#8b90a0)">standards first, then the machine</text>
<rect x="12" y="60" width="160" height="64" rx="8" fill="var(--surface,#1a1d27)" stroke="var(--border-subtle,#3d4258)"/>
<text x="92" y="86" font-size="12.5" font-weight="700" text-anchor="middle" fill="var(--text,#e1e4ed)">Craft workshop</text>
<text x="92" y="104" font-size="10" text-anchor="middle" fill="var(--text-dim,#8b90a0)">quality = the master</text>
<rect x="204" y="60" width="160" height="64" rx="8" fill="var(--surface,#1a1d27)" stroke="var(--green,#4ade80)"/>
<text x="284" y="86" font-size="12.5" font-weight="700" text-anchor="middle" fill="var(--text,#e1e4ed)">Manufactory</text>
<text x="284" y="104" font-size="10" text-anchor="middle" fill="var(--text-dim,#8b90a0)">standard work · gauges</text>
<text x="284" y="117" font-size="10" text-anchor="middle" fill="var(--text-dim,#8b90a0)">division of labour</text>
<rect x="396" y="60" width="160" height="64" rx="8" fill="var(--surface,#1a1d27)" stroke="var(--border-subtle,#3d4258)"/>
<text x="476" y="86" font-size="12.5" font-weight="700" text-anchor="middle" fill="var(--text,#e1e4ed)">Machine</text>
<text x="476" y="104" font-size="10" text-anchor="middle" fill="var(--text-dim,#8b90a0)">put into a process</text>
<text x="476" y="117" font-size="10" text-anchor="middle" fill="var(--text-dim,#8b90a0)">that already exists</text>
<rect x="588" y="60" width="160" height="64" rx="8" fill="var(--surface,#1a1d27)" stroke="var(--border-subtle,#3d4258)"/>
<text x="668" y="86" font-size="12.5" font-weight="700" text-anchor="middle" fill="var(--text,#e1e4ed)">Factory</text>
<text x="668" y="104" font-size="10" text-anchor="middle" fill="var(--text-dim,#8b90a0)">jidoka · kanban</text>
<text x="668" y="117" font-size="10" text-anchor="middle" fill="var(--text-dim,#8b90a0)">process control</text>
<line x1="172" y1="92" x2="200" y2="92" stroke="var(--text-dim,#8b90a0)" stroke-width="1.5" marker-end="url(#fo-arrow)"/>
<line x1="364" y1="92" x2="392" y2="92" stroke="var(--text-dim,#8b90a0)" stroke-width="1.5" marker-end="url(#fo-arrow)"/>
<line x1="556" y1="92" x2="584" y2="92" stroke="var(--text-dim,#8b90a0)" stroke-width="1.5" marker-end="url(#fo-arrow)"/>
<text x="12" y="178" font-size="13" font-weight="700" fill="var(--text,#e1e4ed)">Software</text>
<text x="12" y="194" font-size="10.5" fill="var(--text-dim,#8b90a0)">the machine first, the standards still missing</text>
<rect x="12" y="208" width="160" height="64" rx="8" fill="var(--surface,#1a1d27)" stroke="var(--border-subtle,#3d4258)"/>
<text x="92" y="234" font-size="12.5" font-weight="700" text-anchor="middle" fill="var(--text,#e1e4ed)">Craft workshop</text>
<text x="92" y="252" font-size="10" text-anchor="middle" fill="var(--text-dim,#8b90a0)">1968: "we are the crofters"</text>
<rect x="204" y="208" width="160" height="64" rx="8" fill="var(--surface,#1a1d27)" stroke="var(--border-subtle,#3d4258)"/>
<text x="284" y="234" font-size="12.5" font-weight="700" text-anchor="middle" fill="var(--text,#e1e4ed)">Conveyors</text>
<text x="284" y="252" font-size="10" text-anchor="middle" fill="var(--text-dim,#8b90a0)">CI/CD around a person</text>
<text x="284" y="265" font-size="10" text-anchor="middle" fill="var(--text-dim,#8b90a0)">who still writes the code</text>
<rect x="396" y="208" width="160" height="64" rx="8" fill="var(--surface,#1a1d27)" stroke="var(--accent,#6c8cff)"/>
<text x="476" y="234" font-size="12.5" font-weight="700" text-anchor="middle" fill="var(--text,#e1e4ed)">Machine</text>
<text x="476" y="252" font-size="10" text-anchor="middle" fill="var(--text-dim,#8b90a0)">coding agents</text>
<text x="476" y="265" font-size="10" text-anchor="middle" fill="var(--text-dim,#8b90a0)">from late 2025</text>
<rect x="588" y="206" width="160" height="72" rx="8" fill="none" stroke="var(--amber,#fbbf24)" stroke-dasharray="5 4"/>
<text x="668" y="226" font-size="12.5" font-weight="700" text-anchor="middle" fill="var(--amber,#fbbf24)">Manufactory?</text>
<text x="668" y="243" font-size="10" text-anchor="middle" fill="var(--text-dim,#8b90a0)">checks that can fail · one</text>
<text x="668" y="256" font-size="10" text-anchor="middle" fill="var(--text-dim,#8b90a0)">source per fact · flow limits</text>
<text x="668" y="269" font-size="10" text-anchor="middle" fill="var(--text-dim,#8b90a0)">· process measurement</text>
<line x1="172" y1="240" x2="200" y2="240" stroke="var(--text-dim,#8b90a0)" stroke-width="1.5" marker-end="url(#fo-arrow)"/>
<line x1="364" y1="240" x2="392" y2="240" stroke="var(--text-dim,#8b90a0)" stroke-width="1.5" marker-end="url(#fo-arrow)"/>
<line x1="556" y1="240" x2="584" y2="240" stroke="var(--amber,#fbbf24)" stroke-width="1.5" stroke-dasharray="4 3" marker-end="url(#fo-arrow)"/>
<text x="12" y="312" font-size="10" fill="var(--text-faint,#808698)">Green: the step that made machines useful in manufacturing. Amber, dashed: the same step, not yet built around coding agents.</text>
</svg>
<figcaption>The same four stations in manufacturing and in software. The step that made machines useful in manufacturing is the one software has not built.</figcaption>
</figure>

PulseEngine has run the experiment in the other order since March 2026: oracles and gates first, agents inside them. Before measuring what that produced, it is worth collecting what others have measured.

## What research, industry and standards bodies say

**Output rises, stability does not follow.** Google's DORA report for 2025, *State of AI-assisted Software Development*, found AI adoption associated with higher delivery throughput and, as in 2024, with lower delivery stability[^dora]. Faros AI's telemetry from more than 10,000 developers across 1,255 teams found teams with high AI adoption completing 21% more tasks and merging 98% more pull requests without a matching improvement at the organisation level[^faros-2025]; the vendor's 2026 report states that the probability of a production incident per merged pull request has more than tripled[^faros-2026]. A Stanford group measuring output from the git history of more than 100,000 developers puts the median lift at 10 to 15%, with developers slower for their first 30 to 100 hours of AI use[^stanford].

METR's randomised trial is the most careful measurement in this list and the most often misquoted. Its early-2025 study found that allowing AI increased completion time by 19%, with a confidence interval from +2% to +39%, while the same developers had forecast a 24% reduction beforehand and still estimated a 20% reduction after doing the work[^metr-2025]. In February 2026 METR reported that it is changing the design, because the signal had become unreliable: a significant increase in developers declining to participate rather than work without AI, a pay rate cut from $150 to $50 an hour, and time measurements that break down when one developer runs several agents at once. That post restates the 19% figure rather than withdrawing it, reports late-2025 estimates it states as a speedup of -18% for returning participants and -4% for new recruits, with confidence intervals that both cross zero, and says its own data is very weak evidence for how much faster developers now are[^metr-2026].

**Code quality degrades in specific, measurable ways.** Liu and colleagues analysed 302,600 verified AI-authored commits across 6,299 GitHub repositories in 2026[^liu]. Between 7.5% and 14.8% of each assistant's commits introduce at least one issue found by static analysis, 89.3% of those issues are code smells, and 22.7% of them are still present in the latest revision. GitClear and GitKraken's analysis of 623 million code changes from 2023 to 2026, as reported by LeadDev, finds duplication up 81%, where duplication means five or more consecutive repeated meaningful lines, moved code down 70%, and obfuscation up 47%, defined there as the density of rescue and catch blocks, safe-navigation operators and stubbed methods that squelch unexpected-input signals[^gitclear]. Two of those trends reappear below in PulseEngine's own repositories: duplication as surfaces that drift apart, and squelched signals as checks that report green without checking.

**Practitioners converge on verification as the limit.** Addy Osmani's essay on light and dark software factories, published on 20 July 2026, puts it in one rule: autonomy should grow only as far as the output can be verified cheaply and reliably[^osmani]. He names the cost of skipping it "comprehension debt", the gap between how much code exists and how much of it anyone understands, and moves engineers to an outer loop of direction, plans and approval. PostHog's newsletter of 11 August 2026 asks whether software factories can work at all and concludes that agent output has to be validated to the point of mergeability, with production signals fed back to the agents[^posthog]. Horthy's talk is the third voice, from the side that tried the dark version.

**Standards bodies name the obligation and leave the mechanism open.** The last post on this site went through them in detail[^toolchain-post]. Automotive SPICE 4.1 gives machine learning five numbered processes and AI-assisted development none. The VDA guidelines reportedly say AI output needs verification. The FAA planned to ask applicants to disclose AI use. The Eclipse Foundation asks committers to vet generated content. ISO 26262-8, the part that governs confidence in software tools, is in a 12-week DIS ballot for Edition 3 that opened on 14 October 2026, and COVESA's generative AI group was still writing its charter in October. None of them states what the verification has to produce.

Research measures output and code. Practitioners measure their own loops and report where they broke. Standards describe obligations. Nobody in this list measures the production system around the agents over time, which is what the next section tries for PulseEngine's own repositories.

## What the repositories show

**Is it only two?** Picking two repositories invites the question whether they were picked to show the pattern, so the measures ran first over every repository PulseEngine authors and has not archived: 34, after excluding 11 forks whose history is upstream's. Twenty have enough history and use conventional prefixes on at least half their changes, which a feature or fix share needs before it means anything.

| across the 20 | holds in | sign test |
|---|---:|---:|
| median change touches one or two source files | 20 of 20 | n/a |
| 90th percentile of files per change fell | 13 of 20 | p = 0.025 |
| feature share fell, first half to second | 16 of 20 | p = 0.006 |
| fix share rose, first half to second | 11 of 20 | p = 0.32 |
| at least one issue title in the silent-check vocabulary | 12 of 20 | n/a |

Treating each repository as one vote, falling coupling and a falling feature share are clearly better than chance, p = 0.025 and 0.006 in a one-sided sign test, and the rising fix share is not, p = 0.32, so it is a tendency rather than a law. The 20 share one author and the same tooling, so they are not independent votes and the p-values are a guide rather than proof. Pooling the repositories into one series would be worse: three of them make up 40% of all changes and none of the three shows the full pattern. Between them the 20 carry 142 issue titles in the vocabulary of a check that passed without checking, and 443 open issues, 160 of them older than 60 days.

Five repositories show all five patterns: rivet, relay, spar, witness and pulseengine.eu. The two with the most history among them, rivet with 639 changes and relay with 428, are the worked examples below. rivet is the traceability tool, first commit 7 March 2026. relay is the flight software framework, first commit 12 April. The numbers come from first-parent history and the GitHub issue trackers, read on 21 October 2026 at rivet `cc3b8075` and relay `46eb314`. Agents write most of both, and how much cannot be counted: the commit trailer that records agent co-authorship is on 91% of relay's changes but 54% of rivet's, where it ranges from 9% to 98% between months, so it records a convention followed unevenly rather than a census. The scripts that produce every number and the figure are listed at the end.

<figure class="standards-map">
<svg viewBox="0 0 760 420" width="100%" role="img" aria-labelledby="fm-title fm-desc" style="max-width:760px;height:auto;font-family:'Atkinson Hyperlegible Next',system-ui,sans-serif">
<title id="fm-title">rivet and relay, by month</title>
<desc id="fm-desc">Small multiples for rivet and relay: the 90th percentile of source files per change, the feature and fix share of changes, and the number of open issues with bots excluded, month by month. Open issues end at 34 and 67. Generated from factory-metrics.py output.</desc>
<text x="52" y="26" font-size="12" font-weight="700" fill="var(--text,#e1e4ed)">Files per change, 90th percentile</text>
<text x="292" y="26" font-size="12" font-weight="700" fill="var(--text,#e1e4ed)">Share of changes: feat vs fix</text>
<text x="532" y="26" font-size="12" font-weight="700" fill="var(--text,#e1e4ed)">Open issues, CI alerts excluded</text>
<text x="292" y="42" font-size="10" fill="var(--accent,#6c8cff)">feat</text>
<text x="322" y="42" font-size="10" fill="var(--amber,#fbbf24)">fix</text>
<text x="8" y="56" font-size="12" font-weight="700" fill="var(--text,#e1e4ed)">rivet</text>
<rect x="52" y="64" width="210" height="120" rx="6" fill="var(--surface,#1a1d27)" stroke="var(--border-subtle,#3d4258)"/><line x1="52" y1="126.8" x2="262" y2="126.8" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="46" y="129.8" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">15</text><line x1="52" y1="77.6" x2="262" y2="77.6" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="46" y="80.6" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">30</text><text x="66.0" y="197" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Mar</text><text x="144.0" y="197" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Jun</text><text x="248.0" y="197" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Oct</text><polyline points="66.0,110.4 92.0,143.2 118.0,159.6 144.0,166.2 170.0,169.4 196.0,162.9 222.0,162.9 248.0,162.9" fill="none" stroke="var(--accent,#6c8cff)" stroke-width="1.8"/><circle cx="66.0" cy="110.4" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="92.0" cy="143.2" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="118.0" cy="159.6" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="144.0" cy="166.2" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="170.0" cy="169.4" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="196.0" cy="162.9" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="222.0" cy="162.9" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="248.0" cy="162.9" r="2.4" fill="var(--accent,#6c8cff)"/>
<rect x="292" y="64" width="210" height="120" rx="6" fill="var(--surface,#1a1d27)" stroke="var(--border-subtle,#3d4258)"/><line x1="292" y1="126.8" x2="502" y2="126.8" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="286" y="129.8" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">30%</text><line x1="292" y1="77.6" x2="502" y2="77.6" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="286" y="80.6" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">60%</text><text x="306.0" y="197" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Mar</text><text x="384.0" y="197" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Jun</text><text x="488.0" y="197" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Oct</text><polyline points="306.0,114.8 332.0,98.1 358.0,134.7 384.0,120.1 410.0,129.9 436.0,158.5 462.0,148.9 488.0,161.6" fill="none" stroke="var(--accent,#6c8cff)" stroke-width="1.8"/><circle cx="306.0" cy="114.8" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="332.0" cy="98.1" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="358.0" cy="134.7" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="384.0" cy="120.1" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="410.0" cy="129.9" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="436.0" cy="158.5" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="462.0" cy="148.9" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="488.0" cy="161.6" r="2.4" fill="var(--accent,#6c8cff)"/><polyline points="306.0,107.4 332.0,136.3 358.0,142.1 384.0,117.6 410.0,140.1 436.0,123.4 462.0,98.8 488.0,112.7" fill="none" stroke="var(--amber,#fbbf24)" stroke-width="1.8"/><circle cx="306.0" cy="107.4" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="332.0" cy="136.3" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="358.0" cy="142.1" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="384.0" cy="117.6" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="410.0" cy="140.1" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="436.0" cy="123.4" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="462.0" cy="98.8" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="488.0" cy="112.7" r="2.4" fill="var(--amber,#fbbf24)"/>
<rect x="532" y="64" width="210" height="120" rx="6" fill="var(--surface,#1a1d27)" stroke="var(--border-subtle,#3d4258)"/><line x1="532" y1="126.8" x2="742" y2="126.8" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="526" y="129.8" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">20</text><line x1="532" y1="77.6" x2="742" y2="77.6" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="526" y="80.6" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">40</text><text x="546.0" y="197" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Mar</text><text x="624.0" y="197" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Jun</text><text x="728.0" y="197" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Oct</text><polyline points="546.0,161.2 572.0,141.6 598.0,156.3 624.0,114.5 650.0,139.1 676.0,121.9 702.0,117.0 728.0,92.4" fill="none" stroke="var(--red,#f87171)" stroke-width="1.8"/><circle cx="546.0" cy="161.2" r="2.4" fill="var(--red,#f87171)"/><circle cx="572.0" cy="141.6" r="2.4" fill="var(--red,#f87171)"/><circle cx="598.0" cy="156.3" r="2.4" fill="var(--red,#f87171)"/><circle cx="624.0" cy="114.5" r="2.4" fill="var(--red,#f87171)"/><circle cx="650.0" cy="139.1" r="2.4" fill="var(--red,#f87171)"/><circle cx="676.0" cy="121.9" r="2.4" fill="var(--red,#f87171)"/><circle cx="702.0" cy="117.0" r="2.4" fill="var(--red,#f87171)"/><circle cx="728.0" cy="92.4" r="2.4" fill="var(--red,#f87171)"/>
<text x="8" y="246" font-size="12" font-weight="700" fill="var(--text,#e1e4ed)">relay</text>
<rect x="52" y="254" width="210" height="120" rx="6" fill="var(--surface,#1a1d27)" stroke="var(--border-subtle,#3d4258)"/><line x1="52" y1="316.8" x2="262" y2="316.8" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="46" y="319.8" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">18.5</text><line x1="52" y1="267.6" x2="262" y2="267.6" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="46" y="270.6" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">37</text><text x="66.0" y="387" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Apr</text><text x="126.7" y="387" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Jun</text><text x="248.0" y="387" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Oct</text><polyline points="66.0,267.6 96.3,342.1 126.7,350.0 157.0,350.0 187.3,360.7 217.7,358.0 248.0,360.7" fill="none" stroke="var(--accent,#6c8cff)" stroke-width="1.8"/><circle cx="66.0" cy="267.6" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="96.3" cy="342.1" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="126.7" cy="350.0" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="157.0" cy="350.0" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="187.3" cy="360.7" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="217.7" cy="358.0" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="248.0" cy="360.7" r="2.4" fill="var(--accent,#6c8cff)"/>
<rect x="292" y="254" width="210" height="120" rx="6" fill="var(--surface,#1a1d27)" stroke="var(--border-subtle,#3d4258)"/><line x1="292" y1="316.8" x2="502" y2="316.8" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="286" y="319.8" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">30%</text><line x1="292" y1="267.6" x2="502" y2="267.6" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="286" y="270.6" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">60%</text><text x="306.0" y="387" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Apr</text><text x="366.7" y="387" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Jun</text><text x="488.0" y="387" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Oct</text><polyline points="336.3,241.2 366.7,266.3 397.0,304.2 427.3,303.4 457.7,344.2 488.0,328.9" fill="none" stroke="var(--accent,#6c8cff)" stroke-width="1.8"/><circle cx="336.3" cy="241.2" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="366.7" cy="266.3" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="397.0" cy="304.2" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="427.3" cy="303.4" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="457.7" cy="344.2" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="488.0" cy="328.9" r="2.4" fill="var(--accent,#6c8cff)"/><polyline points="336.3,351.7 366.7,352.4 397.0,352.6 427.3,337.1 457.7,300.4 488.0,326.3" fill="none" stroke="var(--amber,#fbbf24)" stroke-width="1.8"/><circle cx="336.3" cy="351.7" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="366.7" cy="352.4" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="397.0" cy="352.6" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="427.3" cy="337.1" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="457.7" cy="300.4" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="488.0" cy="326.3" r="2.4" fill="var(--amber,#fbbf24)"/>
<rect x="532" y="254" width="210" height="120" rx="6" fill="var(--surface,#1a1d27)" stroke="var(--border-subtle,#3d4258)"/><line x1="532" y1="316.8" x2="742" y2="316.8" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="526" y="319.8" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">20</text><line x1="532" y1="267.6" x2="742" y2="267.6" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="526" y="270.6" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">40</text><text x="546.0" y="387" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Apr</text><text x="606.7" y="387" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Jun</text><text x="728.0" y="387" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Oct</text><polyline points="546.0,346.3 576.3,348.8 606.7,338.9 637.0,309.4 667.3,299.6 697.7,230.7 728.0,201.2" fill="none" stroke="var(--red,#f87171)" stroke-width="1.8"/><circle cx="546.0" cy="346.3" r="2.4" fill="var(--red,#f87171)"/><circle cx="576.3" cy="348.8" r="2.4" fill="var(--red,#f87171)"/><circle cx="606.7" cy="338.9" r="2.4" fill="var(--red,#f87171)"/><circle cx="637.0" cy="309.4" r="2.4" fill="var(--red,#f87171)"/><circle cx="667.3" cy="299.6" r="2.4" fill="var(--red,#f87171)"/><circle cx="697.7" cy="230.7" r="2.4" fill="var(--red,#f87171)"/><circle cx="728.0" cy="201.2" r="2.4" fill="var(--red,#f87171)"/>
<text x="52" y="412" font-size="9.5" fill="var(--text-faint,#808698)">Hollow: fewer than 10 changes. Feat and fix are omitted for months under half conventional. Source: factory-metrics.py, read 21 October 2026.</text>
</svg>
<figcaption>Coupling fell and stayed low in both repositories. The mix moved from features to fixes, and the open backlog grew.</figcaption>
</figure>

| | rivet, March | rivet, October | relay, April | relay, October |
|---|---:|---:|---:|---:|
| changes merged | 67 | 57 | 30 | 62 |
| source files per change, 90th percentile | 20 | 4 | 37 | 2 |
| feature share | 37% | 9% | n/a | 23% |
| fix share | 42% | 39% | n/a | 24% |
| fix cadence: days since the fixed file last changed | 1 | 6 | n/a | 4 |
| fix age: days since the changed lines were written | n/a | 177 | n/a | 57 |
| lines of Rust at month end | 55,566 | 190,734 | 14,341 | 75,051 |
| open issues, CI alerts excluded | 6 | 34 | 8 | 67 |

relay's April changes are 3% conventional, so its feature and fix shares start in May, at 76% and 9%.

**Coupling fell and stayed low.** The 90th percentile of source files per change fell from 20 to 4 in rivet and from 37 to 2 in relay. rivet's median change touches one or two source files in every month. relay started as a scaffold, with a third of April's changes spanning four or more areas of the tree; in October none does, and 4% of rivet's do. Shotgun surgery, Horthy's marker of a code base its agents can no longer change, does not show up in either.

**The lifecycle compressed.** The feature share fell to 9% in rivet and 23% in relay, and fixes are now 39% and 24% of changes. Whether those fixes repair recent work depends on how age is measured. Counting days since the fixed file last changed gives 6 for rivet and 4 for relay, which reads as rework. That number is only a lower bound, because the lines a fix changes were last edited at or before the file's previous touch. Blaming the lines rivet's October fixes actually changed gives a median of 177 days, and 27 of 59 of its file-level previous touches were other October fixes, so the file-level figure was mostly reporting how concentrated the fix wave was. relay's six October fixes that changed Rust lines touched lines a median of 57 days old, too few to read much into. Lehman's laws of software evolution describe the shape: a system in use must keep being adapted, and its complexity grows unless work is done to reduce it[^lehman]. The laws still hold, faster.

**Surfaces drift.** The rivet fixes of September and October cluster on one class: the same fact computed in several places that disagreed. One change title reads "five surfaces that disagreed about the same fact" (#1014), others "every surface states the same coverage" (#1019), "`rivet_validate` reaches the same verdict as `rivet validate`" (#1052) and "one STPA type list; the export's EU AI Act badge matches the dashboard" (#1054). The command line, the MCP server, the HTML export and the dashboard each computed their own answer. That clustering is also why so many of October's fixes landed on files another October fix had just touched. This is the duplication trend from the GitClear data, at the scale of one tool. Agents made it cheap to add surfaces; they did not make it cheap to keep them consistent, which is the part of DHH's argument this data does not support. A planned rewrite ran through the same window, replacing serde_yaml with rivet's own value model on 17 September and its own parser and emitter on 14 October (#1085), but only 6 of September's 40 fixes and 2 of October's 22 touch Rust on a YAML or parser path.

**Checks report green without checking.** Searching issue titles for the vocabulary of this failure, words such as silent, no-op, masked, blind, exits 0 and cannot fail, matches 23 titles in rivet and 5 in relay. Reading all 28, two are something else: a missing feature in rivet (#856) and an audit proposal in relay (#257). The remaining 26 are instances. In relay, a clean-room review found that the FLEET-002 check cannot fail (#497), a verification artifact cites a test that cannot fail for the branch it names (#483), the required verification gate's scope filter was blind to `wasm/` (#410), and witness MC/DC coverage of the flight cascade silently stopped being produced because its build target had not built since #393 (#397). In rivet, the supply-chain gate cannot fail because CI creates the configuration it should be checking (#1110), and the pinned rivet version a compliance action uses can freeze without anyone noticing (#1113). The search also undercounts: rivet #1037, where `verify` promoted a requirement to verified because a link existed, never uses the vocabulary, so 26 is a floor. This is the squelched-signal trend from the GitClear data, appearing inside verification tools, and it is the class the last post called the hinge of tool qualification.

**The backlog grows because discovery works.** Three kinds of author file issues, and the tracker separates only one of them. Bots are CI jobs posting automated alerts: rivet's tracker holds 369 issues, 109 of them runner-liveness alerts, and relay's holds 109, 5 of them alerts. They are excluded, because nobody decided anything to file them. AI agents and the owner both file under the owner's account, so the account cannot tell them apart. The Claude Code marker in an issue body is a lower bound on agent filing, 22 of rivet's 260 issues and 29 of relay's 104, and every marked issue has a body of at least 981 characters in rivet and 1,003 in relay. The owner files only short issues, and of the owner-account issues without the marker, 14 of rivet's 236 and 1 of relay's 72 are shorter than 300 characters. The backlog is therefore overwhelmingly the agents' own inspection, with little from outside: two external authors in rivet and three in relay. What can be measured is the flow. Open issues went from 6 to 34 in rivet and from 8 to 67 in relay, with 10 and 26 older than 60 days. The audits that find these issues run faster than the loop decides about them.

## What a factory needs

Manufacturing has a name for each of these, older than software. **Jidoka**, Toyota's principle that a machine stops itself when it detects a defect, is a gate, with the precondition that the gate can actually stop the line. The `gate-potency` skill in the PulseEngine plugin records a mutation gate that read a path the tool never wrote and reported 210 surviving mutants as 0 for four months. spar now runs a meta-guard in CI that fails when a guard's self-test does not depend on the code it guards. rivet does not have it yet, and #1110 is the result.

**Poka-yoke**, making an error impossible by construction, is the answer to drifting surfaces: one evaluation core, every surface a renderer, and a differential test that feeds the same inputs through every surface and fails on any disagreement. Each of the four rivet fixes above repaired a disagreement after it had shipped; a differential test would have failed on the change that introduced it.

**Kanban** limits work in progress, and the data says where the limit belongs. Discovery is the most valuable thing the agents do and should not be throttled. The queue that needs a limit is the one waiting for a human decision. pulseengine.eu#232, merged on 21 October 2026 and shipped in plugin v0.37.0, splits the backlog on that axis: an issue whose fix a mechanical oracle can confirm goes to the agents without a cap, and only issues that need a scope, architecture or priority decision count against a ratchet. Membership in the uncapped queue is earned rather than claimed, because an agent that could label its own work exempt would be writing both the fix and the exemption. The proof is a reference instead of a command: a link to a failing Actions run in the issue's own repository whose head commit touches a test path, checked over the API, so only reviewed repository code ever executes. The brake itself is not running yet. Its schedule stays unarmed until a cross-repo token exists and the first classification pass has recorded the floors, because a gate that is red on its first day for a reason everyone already knows teaches a team to ignore red.

**Statistical process control** measures the process instead of the product. The figure above was produced by hand on one morning. Run monthly, the same script becomes a control chart, with the erosion signature defined in advance: a rising fix share together with a falling line-level fix age, or a rising number of files per change. The line-level qualifier is load-bearing. The file-level cadence number falls whenever fixes cluster in the same files, so an alert built on it would fire on a concentrated fix wave and call it erosion.

{% mermaid() %}
flowchart TB
    subgraph intake["intake"]
        direction LR
        disc["discovery<br/>agent audits, uncapped"] --> tri{"triage<br/>oracle exists?"}
        tri -->|yes| fix["agents fix<br/>against the oracle"]
        tri -->|no| dec["decision queue<br/>human, capped"]
        dec --> fix
    end
    subgraph line["production"]
        direction LR
        gate["gates<br/>potency proven in spar,<br/>not yet in rivet"] --> core["surfaces<br/>one verdict core, planned"]
        core --> sil["silicon<br/>run by hand"]
        sil --> rel["release<br/>human sign-off"]
    end
    fix --> gate

    classDef auto fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
    classDef partial fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef hand fill:#1a1d27,stroke:#f87171,color:#e1e4ed;
    classDef human fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef phase fill:#13161f,stroke:#3d4258,color:#8b90a0;

    class disc,fix auto;
    class tri,gate,core partial;
    class sil hand;
    class dec,rel human;
    class intake,line phase;
{% end %}

The line as it stands. Green stations run without a person, amber ones exist in part, the red one is done by hand, and blue marks the places where a person is meant to stay. The triage split is built and merged; it is amber because it has not yet run a pass.

None of this is exotic, and the plugin already carries most of it as skills. A skill is a procedure an agent is told to follow, and by the argument of the last post a procedure does not count until a check fails without it. The plugin's own README still annotates its `copilot skill list` example with a count of 18 skills while the directory holds 19, which is the same drift at the smallest possible scale.

## The station still run by hand

Hardware is the station where PulseEngine is furthest from a factory. gale runs its benchmarks in Renode on every change and uses real boards as an anchor. The protocol is written for a factory: every silicon run goes into an immutable, dated directory with the raw capture, a manifest with the gale commit and toolchain versions, the exact ELF and its hash, and the ratio of silicon cycles to Renode cycles is recorded as a calibration factor[^gale-silicon]. The same document says silicon runs are manual, periodic and done on a single shared board, and the run directory for the engine-control benchmark holds nothing but a `.gitkeep`.

jess, which takes the relay flight stack onto a Pixhawk 6X-RT, shows why the hardware oracle cannot be replaced by the simulator. Renode models the MPU register file and does not enforce it, so an isolation obligation from gale cannot be validated without silicon (AFD-076). In the other direction, Renode, QEMU and the real i.MX RT1176 agreed with each other and all three disagreed with wasmtime (AFD-125); with silicon in the comparison, the simulator was ruled out as the source of the difference. The falcon cascade has run bit-exact on the real Pixhawk with an attributive negative control. And access is a constraint of its own: the vehicle's STM32F100 I/O coprocessor has no debug port, so a discovery board is the only route to on-silicon evidence for it (AFD-091).

The protocol exists, the data format exists and the oracles have found real defects. What is missing is the automation: boards behind a self-hosted runner, flashing through probe-rs, and silicon runs as scheduled jobs that write into the run directories without a person carrying a cable.

## Dark production, lit release

The lights-out factory is where the software discussion keeps pointing, so it is worth looking at what lights-out manufacturing does. FANUC has run lights-out production since 2001; robots build about 50 robots per 24-hour shift and can run unsupervised for up to 30 days[^lightsout]. Few factories run exclusively dark, most use it between shifts, and Philips keeps nine people for quality assurance at the end of an otherwise automated line. The people in those plants define how machines behave in faults and restarts, design inspection systems that replace human checks, analyse breakdown data, specify interlocks and set standards[^dsj]. The production floor is dark. Engineering, maintenance and acceptance are not.

Two differences matter for software. A lights-out plant repeats one fixed design, while an agent loop produces a new design with every change, which makes it closer to a prototype shop and raises the share of judgement. And in safety work the acceptance step has named owners by design: ISO 26262 assigns responsibility for the safety case to people and requires confirmation measures whose independence grows with the integrity level.

The target that follows is dark production with a lit release, which is Osmani's light factory with the light concentrated where the standard requires it. Agents produce and check everything for which an oracle exists, around the clock. People set the standards, decide what the oracles cannot, and sign.

{% mermaid() %}
flowchart LR
    subgraph first["1. build these first"]
        direction TB
        pot["gates whose failure<br/>has been measured"]
        core["one verdict core<br/>per fact"]
        ora["an oracle for every<br/>item agents may close"]
    end
    subgraph dark["2. then these run dark"]
        direction TB
        disc["discovery"]
        fix["fixing against<br/>the oracle"]
        gate["gating"]
        spc["process control,<br/>monthly, line-level"]
        sil["silicon runs,<br/>boards on a runner"]
    end
    subgraph lit["stays white"]
        direction TB
        std["deciding what<br/>correct means"]
        dec["deciding what<br/>no oracle can"]
        alarm["acting on<br/>a process alarm"]
        rel["independent review<br/>and the signature"]
    end
    first --> dark
    std --> ora
    dec --> ora
    spc --> alarm
    dark --> rel

    classDef auto fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
    classDef partial fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef human fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef phase fill:#13161f,stroke:#3d4258,color:#8b90a0;

    class pot,core,ora partial;
    class disc,fix,gate,spc,sil auto;
    class std,dec,alarm,rel human;
    class first,dark,lit phase;
{% end %}

Read as a plan, the order is the one manufacturing followed. The amber column has to exist before anything goes dark: gates whose ability to fail has been measured, one evaluation core per fact, and an oracle for every item the agents are trusted to close. With those in place, discovery, fixing, gating, process measurement and the silicon runs can go unattended. Four things stay white however far the rest goes: deciding what correct means, deciding what no oracle can, deciding what to do when the process alarm fires, and the independent review and signature a safety case names a person for.

## Limits

The worked examples are two repositories, picked by a stated rule from a census of all 34 PulseEngine authors. All 34 share one human author, so the census shows the pattern is not an artifact of choosing two; it does not show that it holds for other teams. Commit types are the prefixes the agents chose, and `fix:` includes dependency and CI changes. The share of agent-written code cannot be established from the history, because the co-authorship trailer was applied unevenly. The first and last months are partial: rivet starts on 7 March and relay on 12 April, and October is measured to the 21st, so October's change count covers three weeks and its line count is a reading on that date rather than a month end. Almost all issues are self-filed, so the trackers measure the agents' own inspection and very little external use. The count of checks that report green without checking starts from a keyword search over titles, which is why the 28 matches are read down to 26 above rather than quoted as a class.

## Take-away

The factory was never missing its machine. It was missing everything around the machine, and agents make that absence expensive within months instead of years. The repositories measured here kept their structure, but the checks that report green without checking, the surfaces that drift, the decision queue and the hand-run hardware station each have an answer from manufacturing, and the answers are mechanical: gates proven to fail, one source per fact, a limit on the queue that waits for people, and a process that measures itself.

## Reproduce

`scripts/factory-metrics.py <clone> --issues pulseengine/<repo> --line-age 2026-10 --json <out>` produces every number in this post from a full clone and the GitHub REST API, and `scripts/factory-charts.py rivet=rivet.json relay=relay.json` renders the figure from that output; the `label=` prefix names each row, so the figure does not depend on what the files are called. `scripts/factory-census.py <dir-of-clones> --issues-org pulseengine` produces the cross-repository table from one clone per repository, pinned to each one's default branch. Each script's header lists its instruments and what they cannot see, including why the two fix-age numbers differ.

## Sources and caveats

Three items could not be read in full. The Pragmatic Engineer issue is a subscriber issue and was read up to its Big Tech section. The DORA 2025 report's findings were read through summaries; only its title was confirmed at source. Cusumano's book was not available; his 1989 working paper was read instead. The three talks and essays were read as transcripts or web pages, not watched.

[^horthy]: Dex Horthy (HumanLayer), *Harness Engineering is not Enough: Why Software Factories Fail*, AI Engineer World's Fair 2026, 30 June 2026, [video](https://www.youtube.com/watch?v=Ib5GBkD555M). Primary, read as a transcript.
[^dhh]: David Heinemeier Hansson, *Opening Keynote*, Rails World 2026, Austin, 23 September 2026; video published 24 September 2026, [video](https://www.youtube.com/watch?v=vDjW_dRyKXY). Primary, read as a transcript.
[^orosz]: Gergely Orosz, *What's the ROI of software engineers' spending on AI?*, The Pragmatic Engineer, 20 October 2026. Primary, read up to the Big Tech section (subscriber content).
[^mcilroy]: M. D. McIlroy, *Mass Produced Software Components*, NATO Software Engineering Conference, Garmisch, 7 to 11 October 1968, [text](https://www.cs.dartmouth.edu/~doug/components.txt). Primary.
[^dagapeyeff]: Alex d'Agapeyeff, remarks and Figure 3, "d'Agapeyeff's Inverted Pyramid", in Peter Naur and Brian Randell (eds), *Software Engineering: Report on a conference sponsored by the NATO Science Committee*, Garmisch, 7 to 11 October 1968; report dated January 1969, page 14, with the index entry "Middleware 23". [PDF](http://homepages.cs.ncl.ac.uk/brian.randell/NATO/nato1968.PDF). Primary, read at source. The hosted edition carries its own note that it was produced by scanning and OCR of the original and that errors may remain, so the quoted wording is from that transcription rather than the 1969 print.
[^cusumano-wp]: Michael A. Cusumano, *Japanese Cooperative R&D Projects in Software Technology*, MIT Sloan working paper, 18 October 1989, [PDF](https://dspace.mit.edu/bitstream/1721.1/2280/1/SWP-3087-24832363.pdf). Primary.
[^cusumano]: Michael A. Cusumano, *Japan's Software Factories: A Challenge to U.S. Management*, Oxford University Press, 1991. Not read; cited for its existence and scope.
[^dora]: Google Cloud and DORA, *State of AI-assisted Software Development 2025*, [dora.dev](https://dora.dev/research/2025/dora-report/). Title and framing confirmed at source; the throughput and stability findings were read through summaries, not in the report itself.
[^faros-2025]: Faros AI, *The AI Productivity Paradox Report 2025*, telemetry from over 10,000 developers across 1,255 teams. Secondary, vendor research.
[^faros-2026]: Faros AI, statement on its *AI Engineering Report 2026* (22,000 developers, 4,000 teams) on the vendor's site. Vendor claim; the report itself not read.
[^stanford]: Yegor Denisov-Blanch (Stanford), interview on the 100,000-developer study, Aviator podcast. Secondary.
[^metr-2025]: Joel Becker, Nate Rush, Beth Barnes, David Rein, *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity*, [arXiv:2507.09089](https://arxiv.org/abs/2507.09089), July 2025. Primary; abstract read at source for the 19%, 24% forecast and 20% post-hoc figures.
[^metr-2026]: METR, *We are Changing our Developer Productivity Experiment Design*, 24 February 2026, [metr.org](https://metr.org/blog/2026-02-24-uplift-update/). Primary, read at source. It restates the early-2025 figure rather than withdrawing it, and calls its own late-2025 estimates very weak evidence biased downward by participants who declined to work without AI.
[^liu]: Yue Liu, Ratnadira Widyasari, Yanjie Zhao, Ivana Clairine Irsan, Junkai Chen, David Lo, *Debt Behind the AI Boom: A Large-Scale Empirical Study of AI-Generated Code in the Wild*, arXiv:2603.28592, March 2026. Primary, preprint.
[^gitclear]: Bill Doerrfeld, *Code maintainability plummets in the AI coding era*, [LeadDev](https://leaddev.com/software-quality/code-maintainability-plummets-in-the-ai-coding-era), 7 July 2026, reporting GitClear and GitKraken research over 623 million code changes. Secondary for the underlying research, read at source for every number and definition quoted here.
[^osmani]: Addy Osmani, *Software Factories, Light and Dark*, 20 July 2026, [addyosmani.com](https://addyosmani.com/blog/software-factories/). Primary.
[^posthog]: Jina Yoon, *Can software factories actually work?*, PostHog newsletter, 11 August 2026. Primary.
[^toolchain-post]: *AI in the product, not AI in the toolchain*, pulseengine.eu, 14 October 2026. [Post](/blog/ai-in-the-product-not-the-toolchain/). Primary.
[^lehman]: M. M. Lehman, *Programs, Life Cycles, and Laws of Software Evolution*, Proceedings of the IEEE 68(9), 1980; law wording as listed in *Lehman's laws of software evolution*, Wikipedia. Secondary for the wording.
[^gale-silicon]: `benches/engine_control/silicon/README.md` in pulseengine/gale, with the `runs/` directory listing read through the GitHub contents API on 21 October 2026. Primary.
[^lightsout]: *Lights out (manufacturing)*, Wikipedia, read 21 October 2026. Secondary.
[^dsj]: DSJ Global, *The talent required to run lights-out manufacturing operations*, December 2025. Secondary.
