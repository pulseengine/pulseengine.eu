+++
title = "The machine arrived before the factory"
description = "Software has called itself a factory since 1968. It never was one, because its production step was a person. Agents turn that step into a machine, and they arrive before the standards a factory depends on: checks that can fail, one source per fact, flow limits, process measurement. What research, practitioners and standards bodies say, and seven months of two PulseEngine repositories measured from git and the issue trackers."
date = 2026-10-21
draft = true
[taxonomies]
tags = ["verification", "process", "ai-agents", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
The software factory has been a hope since 1968, because its production step, turning a specification into code, was a person whose output varied by an order of magnitude. Agents turn that step into a machine. In manufacturing the standards came first and the machine second; software is getting the machine first. Research measures more output, more duplication and lower stability. Practitioners converge on verification as the limit on autonomy. Standards bodies name the obligation without the mechanism. Measured over seven months, rivet and spar keep their structure, while surfaces drift, checks report green without checking, and the backlog grows because the agents find more than one person can decide. Each of these has a factory answer that is older than software, and the hardware station is still run by hand.
{% end %}

## Three positions

Three pieces from the last four months describe AI in software development from three directions. Dex Horthy's talk at the AI Engineer World's Fair on 30 June 2026 argues that a lights-off software factory, one where nobody reads the code, fails within months[^horthy]. Coding models are trained with rewards for passing tests, nothing in that reward measures maintainability, and in HumanLayer's experience a code base nobody reads starts to defeat its agents after three to six months. His remedy is planning up front and reading every line again.

David Heinemeier Hansson's opening keynote at Rails World in Austin on 23 September 2026 takes the other side[^dhh]. He calls Opus 4.5, released on 24 November 2025, the Kodak Brownie of software. 37signals has stopped writing code by hand, and a hand-written change is now treated like an exception in an error tracker, a sign that the agent setup needs fixing. He evaluates the Rust his agents write from the outside, the way a business owner evaluates commissioned work, and argues that abstractions matter less now that repetition and keeping copies in sync have become cheap.

Gergely Orosz collected AI spending and pull-request data from 27 companies, published on 20 October 2026[^orosz]. Outside Big Tech, spend per engineer ranged from under $300 to $3,000 a month and was unrelated to company size. Pull-request counts roughly doubled on CodeRabbit's platform, stayed flat at a 5,000-person company where the average change tripled in size, and at a 600-engineer SaaS company a staff engineer reported that speed barely moved once the team kept its previous quality bar. Few of the companies could say whether the spending paid back.

All three describe people and agents. None measures the system the code is produced in, and that system is what makes a factory a factory.

## A term from 1968

At the NATO Software Engineering conference in Garmisch in October 1968, Doug McIlroy gave a talk titled "Mass produced software components"[^mcilroy]. One of its section headings states that the software industry is not industrialized, and he compared his colleagues with the hardware engineers: "we are the crofters", they "the industrialists". His proposal was an industry of standard component families.

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

METR's randomised trial is the most careful measurement in this list and the most often misquoted. Its early-2025 study found that allowing AI increased completion time by 19%, with a confidence interval from +2% to +39%, while the same developers had forecast a 24% reduction beforehand and still estimated a 20% reduction after doing the work[^metr-2025]. In February 2026 METR reported that it is changing the design, because the signal had become unreliable: a significant increase in developers declining to participate rather than work without AI, a pay rate cut from $150 to $50 an hour, and time measurements that break down when one developer runs several agents at once. That post restates the 19% figure rather than withdrawing it, offers late-2025 estimates of a 18% speedup for returning participants and 4% for new recruits with confidence intervals that both cross zero, and says its own data is very weak evidence for how much faster developers now are[^metr-2026].

**Code quality degrades in specific, measurable ways.** Liu and colleagues analysed 302,600 verified AI-authored commits across 6,299 GitHub repositories in 2026[^liu]. Between 7.5% and 14.8% of each assistant's commits introduce at least one issue found by static analysis, 89.3% of those issues are code smells, and 22.7% of them are still present in the latest revision. GitClear and GitKraken's analysis of 623 million code changes from 2023 to 2026, as reported by LeadDev, finds duplication up 81%, where duplication means five or more consecutive repeated meaningful lines, moved code down 70%, and obfuscation up 47%, defined there as the density of rescue and catch blocks, safe-navigation operators and stubbed methods that squelch unexpected-input signals[^gitclear]. Two of those trends reappear below in PulseEngine's own repositories: duplication as surfaces that drift apart, and squelched signals as checks that report green without checking.

**Practitioners converge on verification as the limit.** Addy Osmani's essay on light and dark software factories, published on 20 July 2026, puts it in one rule: autonomy should grow only as far as the output can be verified cheaply and reliably[^osmani]. He names the cost of skipping it "comprehension debt", the gap between how much code exists and how much of it anyone understands, and moves engineers to an outer loop of direction, plans and approval. PostHog's newsletter of 11 August 2026 asks whether software factories can work at all and concludes that agent output has to be validated to the point of mergeability, with production signals fed back to the agents[^posthog]. Horthy's talk is the third voice, from the side that tried the dark version.

**Standards bodies name the obligation and leave the mechanism open.** The last post on this site went through them in detail[^toolchain-post]. Automotive SPICE 4.1 gives machine learning five numbered processes and AI-assisted development none. The VDA guidelines reportedly say AI output needs verification. The FAA planned to ask applicants to disclose AI use. The Eclipse Foundation asks committers to vet generated content. ISO 26262-8, the part that governs confidence in software tools, is in a 12-week DIS ballot for Edition 3 that opened on 14 October 2026, and COVESA's generative AI group was still writing its charter in October. None of them states what the verification has to produce.

Research measures output and code. Practitioners measure their own loops and report where they broke. Standards describe obligations. Nobody in this list measures the production system around the agents over time, which is what the next section tries for two repositories.

## Seven months, measured

The numbers come from the first-parent history of two repositories and from their GitHub issue trackers, read on 21 October 2026 at rivet `cc3b8075` and spar `02e0df5`. rivet is the traceability tool, first commit 7 March 2026. spar is the AADL architecture analysis, first commit 8 March. Both are written predominantly by agents working under a single human author, and that share cannot be counted precisely: the commit trailer that records agent co-authorship is present on 48% of rivet's changes and 69% of spar's, ranging from 4% to 100% between months, so it is a convention that was followed unevenly rather than a census. The scripts that produce every number and the figure are listed at the end.

<figure class="standards-map">
<svg viewBox="0 0 760 420" width="100%" role="img" aria-labelledby="fm-title fm-desc" style="max-width:760px;height:auto;font-family:'Atkinson Hyperlegible Next',system-ui,sans-serif">
<title id="fm-title">Seven months of rivet and spar, by month</title>
<desc id="fm-desc">Small multiples for two repositories, March to October 2026: the 90th percentile of source files per change falls in both; the feature share falls and the fix share rises in both; the number of open issues rises in both from single digits to 33 and 37. Generated from factory-metrics.py output.</desc>
<text x="52" y="26" font-size="12" font-weight="700" fill="var(--text,#e1e4ed)">Files per change, 90th percentile</text>
<text x="292" y="26" font-size="12" font-weight="700" fill="var(--text,#e1e4ed)">Share of changes: feat vs fix</text>
<text x="532" y="26" font-size="12" font-weight="700" fill="var(--text,#e1e4ed)">Open issues (bots excluded)</text>
<text x="292" y="42" font-size="10" fill="var(--accent,#6c8cff)">feat</text>
<text x="322" y="42" font-size="10" fill="var(--amber,#fbbf24)">fix</text>
<text x="8" y="56" font-size="12" font-weight="700" fill="var(--text,#e1e4ed)">rivet</text>
<rect x="52" y="64" width="210" height="120" rx="6" fill="var(--surface,#1a1d27)" stroke="var(--border-subtle,#3d4258)"/><line x1="52" y1="126.8" x2="262" y2="126.8" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="46" y="129.8" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">15</text><line x1="52" y1="77.6" x2="262" y2="77.6" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="46" y="80.6" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">30</text><text x="66.0" y="197" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Mar</text><text x="144.0" y="197" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Jun</text><text x="248.0" y="197" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Oct</text><polyline points="66.0,110.4 92.0,143.2 118.0,159.6 144.0,166.2 170.0,169.4 196.0,162.9 222.0,162.9 248.0,162.9" fill="none" stroke="var(--accent,#6c8cff)" stroke-width="1.8"/><circle cx="66.0" cy="110.4" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="92.0" cy="143.2" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="118.0" cy="159.6" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="144.0" cy="166.2" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="170.0" cy="169.4" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="196.0" cy="162.9" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="222.0" cy="162.9" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="248.0" cy="162.9" r="2.4" fill="var(--accent,#6c8cff)"/>
<rect x="292" y="64" width="210" height="120" rx="6" fill="var(--surface,#1a1d27)" stroke="var(--border-subtle,#3d4258)"/><line x1="292" y1="126.8" x2="502" y2="126.8" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="286" y="129.8" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">30%</text><line x1="292" y1="77.6" x2="502" y2="77.6" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="286" y="80.6" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">60%</text><text x="306.0" y="197" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Mar</text><text x="384.0" y="197" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Jun</text><text x="488.0" y="197" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Oct</text><polyline points="306.0,114.8 332.0,98.1 358.0,134.7 384.0,120.1 410.0,129.9 436.0,158.5 462.0,148.9 488.0,161.6" fill="none" stroke="var(--accent,#6c8cff)" stroke-width="1.8"/><circle cx="306.0" cy="114.8" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="332.0" cy="98.1" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="358.0" cy="134.7" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="384.0" cy="120.1" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="410.0" cy="129.9" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="436.0" cy="158.5" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="462.0" cy="148.9" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="488.0" cy="161.6" r="2.4" fill="var(--accent,#6c8cff)"/><polyline points="306.0,107.4 332.0,136.3 358.0,142.1 384.0,117.6 410.0,140.1 436.0,123.4 462.0,98.8 488.0,112.7" fill="none" stroke="var(--amber,#fbbf24)" stroke-width="1.8"/><circle cx="306.0" cy="107.4" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="332.0" cy="136.3" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="358.0" cy="142.1" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="384.0" cy="117.6" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="410.0" cy="140.1" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="436.0" cy="123.4" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="462.0" cy="98.8" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="488.0" cy="112.7" r="2.4" fill="var(--amber,#fbbf24)"/>
<rect x="532" y="64" width="210" height="120" rx="6" fill="var(--surface,#1a1d27)" stroke="var(--border-subtle,#3d4258)"/><line x1="532" y1="126.8" x2="742" y2="126.8" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="526" y="129.8" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">20</text><line x1="532" y1="77.6" x2="742" y2="77.6" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="526" y="80.6" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">40</text><text x="546.0" y="197" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Mar</text><text x="624.0" y="197" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Jun</text><text x="728.0" y="197" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Oct</text><polyline points="546.0,161.2 572.0,141.6 598.0,156.3 624.0,114.5 650.0,139.1 676.0,121.9 702.0,117.0 728.0,94.8" fill="none" stroke="var(--red,#f87171)" stroke-width="1.8"/><circle cx="546.0" cy="161.2" r="2.4" fill="var(--red,#f87171)"/><circle cx="572.0" cy="141.6" r="2.4" fill="var(--red,#f87171)"/><circle cx="598.0" cy="156.3" r="2.4" fill="var(--red,#f87171)"/><circle cx="624.0" cy="114.5" r="2.4" fill="var(--red,#f87171)"/><circle cx="650.0" cy="139.1" r="2.4" fill="var(--red,#f87171)"/><circle cx="676.0" cy="121.9" r="2.4" fill="var(--red,#f87171)"/><circle cx="702.0" cy="117.0" r="2.4" fill="var(--red,#f87171)"/><circle cx="728.0" cy="94.8" r="2.4" fill="var(--red,#f87171)"/>
<text x="8" y="246" font-size="12" font-weight="700" fill="var(--text,#e1e4ed)">spar</text>
<rect x="52" y="254" width="210" height="120" rx="6" fill="var(--surface,#1a1d27)" stroke="var(--border-subtle,#3d4258)"/><line x1="52" y1="316.8" x2="262" y2="316.8" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="46" y="319.8" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">15</text><line x1="52" y1="267.6" x2="262" y2="267.6" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="46" y="270.6" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">30</text><text x="66.0" y="387" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Mar</text><text x="144.0" y="387" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Jun</text><text x="248.0" y="387" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Oct</text><polyline points="66.0,274.2 92.0,346.3 118.0,352.9 144.0,352.9 170.0,346.3 196.0,359.4 222.0,359.4 248.0,343.0" fill="none" stroke="var(--accent,#6c8cff)" stroke-width="1.8"/><circle cx="66.0" cy="274.2" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="92.0" cy="346.3" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="118.0" cy="352.9" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="144.0" cy="352.9" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="170.0" cy="346.3" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="196.0" cy="359.4" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="222.0" cy="359.4" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="248.0" cy="343.0" r="2.4" fill="var(--accent,#6c8cff)"/>
<rect x="292" y="254" width="210" height="120" rx="6" fill="var(--surface,#1a1d27)" stroke="var(--border-subtle,#3d4258)"/><line x1="292" y1="316.8" x2="502" y2="316.8" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="286" y="319.8" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">30%</text><line x1="292" y1="267.6" x2="502" y2="267.6" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="286" y="270.6" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">60%</text><text x="306.0" y="387" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Mar</text><text x="384.0" y="387" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Jun</text><text x="488.0" y="387" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Oct</text><polyline points="306.0,304.5 332.0,284.0 358.0,284.0 384.0,301.7 410.0,311.4 436.0,293.2 462.0,366.0 488.0,341.1" fill="none" stroke="var(--accent,#6c8cff)" stroke-width="1.8"/><circle cx="306.0" cy="304.5" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="332.0" cy="284.0" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="358.0" cy="284.0" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="384.0" cy="301.7" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="410.0" cy="311.4" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="436.0" cy="293.2" r="2.4" fill="var(--accent,#6c8cff)"/><circle cx="462.0" cy="366.0" r="2.8" fill="var(--surface,#1a1d27)" stroke="var(--accent,#6c8cff)" stroke-width="1.4"/><circle cx="488.0" cy="341.1" r="2.4" fill="var(--accent,#6c8cff)"/><polyline points="306.0,345.5 332.0,348.5 358.0,323.5 384.0,340.3 410.0,346.5 436.0,356.8 462.0,325.0 488.0,271.5" fill="none" stroke="var(--amber,#fbbf24)" stroke-width="1.8"/><circle cx="306.0" cy="345.5" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="332.0" cy="348.5" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="358.0" cy="323.5" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="384.0" cy="340.3" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="410.0" cy="346.5" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="436.0" cy="356.8" r="2.4" fill="var(--amber,#fbbf24)"/><circle cx="462.0" cy="325.0" r="2.8" fill="var(--surface,#1a1d27)" stroke="var(--amber,#fbbf24)" stroke-width="1.4"/><circle cx="488.0" cy="271.5" r="2.4" fill="var(--amber,#fbbf24)"/>
<rect x="532" y="254" width="210" height="120" rx="6" fill="var(--surface,#1a1d27)" stroke="var(--border-subtle,#3d4258)"/><line x1="532" y1="316.8" x2="742" y2="316.8" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="526" y="319.8" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">20</text><line x1="532" y1="267.6" x2="742" y2="267.6" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/><text x="526" y="270.6" font-size="9" text-anchor="end" fill="var(--text-faint,#808698)">40</text><text x="546.0" y="387" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Mar</text><text x="624.0" y="387" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Jun</text><text x="728.0" y="387" font-size="9" text-anchor="middle" fill="var(--text-faint,#808698)">Oct</text><polyline points="546.0,363.5 572.0,361.1 598.0,346.3 624.0,353.7 650.0,309.4 676.0,326.6 702.0,311.9 728.0,275.0" fill="none" stroke="var(--red,#f87171)" stroke-width="1.8"/><circle cx="546.0" cy="363.5" r="2.4" fill="var(--red,#f87171)"/><circle cx="572.0" cy="361.1" r="2.4" fill="var(--red,#f87171)"/><circle cx="598.0" cy="346.3" r="2.4" fill="var(--red,#f87171)"/><circle cx="624.0" cy="353.7" r="2.4" fill="var(--red,#f87171)"/><circle cx="650.0" cy="309.4" r="2.4" fill="var(--red,#f87171)"/><circle cx="676.0" cy="326.6" r="2.4" fill="var(--red,#f87171)"/><circle cx="702.0" cy="311.9" r="2.4" fill="var(--red,#f87171)"/><circle cx="728.0" cy="275.0" r="2.4" fill="var(--red,#f87171)"/>
<text x="52" y="412" font-size="9.5" fill="var(--text-faint,#808698)">Hollow points: fewer than 10 changes that month. Source: factory-metrics.py over first-parent history and the GitHub issue API, read 21 October 2026.</text>
</svg>
<figcaption>Coupling fell and stayed low in both repositories. The mix moved from features to fixes, and the open backlog grew.</figcaption>
</figure>

| | rivet, March | rivet, October | spar, March | spar, October |
|---|---:|---:|---:|---:|
| changes merged | 67 | 57 | 16 | 33 |
| source files per change, 90th percentile | 20 | 4 | 28 | 7 |
| feature share | 37% | 9% | 38% | 15% |
| fix share | 42% | 39% | 12% | 58% |
| fix cadence: days since the fixed file last changed | 1 | 6 | 1 | 87 |
| fix age: days since the changed lines were written | n/a | 177 | n/a | 209 |
| lines of Rust at month end | 55,566 | 190,734 | 96,721 | 171,516 |
| open issues, bots excluded | 6 | 33 | 1 | 37 |

**Coupling stayed healthy.** The median change touches one or two source files in every month of both repositories, and the 90th percentile fell from 20 files to 4 in rivet and from 28 to 7 in spar. In October, 4% of rivet's changes and 6% of spar's span four or more areas of the tree. Shotgun surgery, Horthy's marker of a code base its agents can no longer change, does not show up in seven months of these two repositories.

**The lifecycle compressed, and both repositories are now fixing old code.** Growth flattened, the feature share fell from about half of all changes to 9% in rivet and 15% in spar, and the fix share rose to 39% and 58%. The obvious next question is whether those fixes repair recent work or defects that surfaced later, and the answer depends entirely on how the question is measured. Counting days since the fixed file last changed gives 6 days for rivet and 87 for spar, which reads as rework in one repository and maturity in the other. That number is only a lower bound, because the lines a fix changes were last edited at or before the file's previous touch. Blaming the lines each fix actually changed gives a median of 177 days in rivet and 209 in spar, and the gap between the two measures is itself measurable: 27 of 59 of rivet's file-level previous touches were other October fixes, against 13 of 45 in spar. The file-level figure was largely reporting how concentrated each repository's fix wave was. Both are repairing code around half a year old, which is what defects surfacing through use look like, and the difference between them is cadence rather than quality. Lehman's laws of software evolution describe the shape: a system in use must keep being adapted, and its complexity grows unless work is done to reduce it[^lehman]. The laws still hold, faster. Problems that used to arrive in year three arrive in month seven.

**Surfaces drift.** The rivet fixes of September and October cluster on one class: the same fact computed in several places that disagreed. One change title reads "five surfaces that disagreed about the same fact" (#1014), others "every surface states the same coverage" (#1019), "`rivet_validate` reaches the same verdict as `rivet validate`" (#1052) and "one STPA type list; the export's EU AI Act badge matches the dashboard" (#1054). The command line, the MCP server, the HTML export and the dashboard each computed their own answer. That clustering is also why so many of October's fixes landed on files another October fix had just touched. This is the duplication trend from the GitClear data, at the scale of one tool. Agents made it cheap to add surfaces; they did not make it cheap to keep them consistent, which is the part of DHH's argument this data does not support. A planned rewrite ran through the same window, replacing serde_yaml with rivet's own value model on 17 September and its own parser and emitter on 14 October (#1085), but only 6 of September's 40 fixes and 2 of October's 22 touch Rust on a YAML or parser path.

**Checks report green without checking.** Searching issue titles for the vocabulary of this failure, words such as silent, no-op, masked, blind, exits 0 and cannot fail, matches 22 titles in rivet and 18 in spar. Reading all 40, three are something else: a missing feature in rivet (#856), and in spar a proposal for future conformance testing (#246) and a missing job timeout (#398). The remaining 37 are instances. In spar, `analyze` exited 0 on analysis errors on the documented CI path (#469, #472), `--pmoo` did nothing on any TSN model (#482), a worst-case traversal budget was checked on the first hop only (#481), and a 0 ps bound passed its budget (#478). In rivet, `verify` promoted a requirement to verified because a link existed (#1037), and the supply-chain gate cannot fail because CI creates the configuration it should be checking (#1110). This is the squelched-signal trend from the same data, appearing inside verification tools, and it is the class the last post called the hinge of tool qualification.

**The backlog grows because discovery works.** rivet's tracker holds 367 issues, 108 of them automated runner-liveness alerts. Of the remaining 259, all but two come from the owner's account, and spar has three external issues out of 128. Agents file under that account, so who filed an issue cannot be recovered from the tracker. The Claude Code marker in the issue body gives a lower bound only: 21 of rivet's 259 and 27 of spar's 128. What can be measured is the flow. The open count went from 6 in March to 33 in rivet and from 1 to 37 in spar, with 10 and 14 issues older than 60 days. The audits that find these issues run faster than the loop decides about them.

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

Two differences matter for software. A lights-out plant repeats one fixed design, while an agent loop produces a new design with every change, which makes it closer to a prototype shop and raises the share of judgement. And in safety work the acceptance step has named owners by design: ISO 26262 assigns responsibility for the safety case to people and requires confirmation measures whose independence grows with the integrity level. That is part of what a safety case is.

The target that follows is dark production with a lit release, which is Osmani's light factory with the light concentrated where the standard requires it. Agents produce and check everything for which an oracle exists, around the clock. People set the standards, decide what the oracles cannot, and sign.

## Limits

These are two repositories with one human author, so they show what the approach can produce and say nothing about how common the result is. Commit types are the prefixes the agents chose, and `fix:` includes dependency and CI changes. The share of agent-written code cannot be established from the history, because the co-authorship trailer was applied unevenly. The first and last months are partial: both repositories start on 7 and 8 March, and October is measured to the 21st, so October's change count covers three weeks and its line count is a reading on that date rather than a month end. Almost all issues are self-filed, so the trackers measure the agents' own inspection and very little external use. Some months are small: spar merged four changes in September. The count of checks that report green without checking starts from a keyword search over titles, which is why the 40 matches are read down to 37 above rather than quoted as a class.

## Take-away

The factory was never missing its machine. It was missing everything around the machine, and agents make that absence expensive within months instead of years. The repositories measured here kept their structure, but the checks that report green without checking, the surfaces that drift, the decision queue and the hand-run hardware station each have an answer from manufacturing, and the answers are mechanical: gates proven to fail, one source per fact, a limit on the queue that waits for people, and a process that measures itself.

## Reproduce

`scripts/factory-metrics.py <clone> --issues pulseengine/<repo> --line-age 2026-10 --json <out>` produces every number in this post from a full clone and the GitHub REST API, and `scripts/factory-charts.py rivet.json spar.json` renders the figure from that output. The metrics script's header lists each instrument and what it cannot see, including why the two fix-age numbers differ.

## Sources and caveats

Three items could not be read in full. The Pragmatic Engineer issue is a subscriber issue and was read up to its Big Tech section. The DORA 2025 report's findings were read through summaries; only its title was confirmed at source. Cusumano's book was not available; his 1989 working paper was read instead. The three talks and essays were read as transcripts or web pages, not watched.

[^horthy]: Dex Horthy (HumanLayer), *Harness Engineering is not Enough: Why Software Factories Fail*, AI Engineer World's Fair 2026, 30 June 2026, [video](https://www.youtube.com/watch?v=Ib5GBkD555M). Primary, read as a transcript.
[^dhh]: David Heinemeier Hansson, *Opening Keynote*, Rails World 2026, Austin, 23 September 2026; video published 24 September 2026, [video](https://www.youtube.com/watch?v=vDjW_dRyKXY). Primary, read as a transcript.
[^orosz]: Gergely Orosz, *What's the ROI of software engineers' spending on AI?*, The Pragmatic Engineer, 20 October 2026. Primary, read up to the Big Tech section (subscriber content).
[^mcilroy]: M. D. McIlroy, *Mass Produced Software Components*, NATO Software Engineering Conference, Garmisch, 7 to 11 October 1968, [text](https://www.cs.dartmouth.edu/~doug/components.txt). Primary.
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
