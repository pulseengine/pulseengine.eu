+++
title = "Agents don't tidy up"
description = "Nine projects, one ruler: three written by people, six written mostly by coding agents, PulseEngine's rivet and spar among them. Coupling, fix share, bugs caused by fixes and bug lifetime do not separate the groups. Refactoring does: 18 to 24% of commits in every human project, 7 to 12% in every agent project. What that means for the factory, and the experiment that tests the remedy."
date = 2026-10-22
draft = true
[taxonomies]
tags = ["verification", "process", "ai-agents", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
**Agents repair what breaks. They do not tidy what still works.**

- Across nine projects, refactoring is the only measure that separates code written by people from code written mostly by agents: 18 to 24% of commits against 7 to 12%, with no overlap.
- Fix share, bugs introduced by earlier fixes, coupling and bug lifetime in commits do not separate the groups once the measurement is controlled.
- Redesign from insight still happens in PulseEngine. The everyday tidying that good teams do on the side does not, because no gate asks for it. The next step is a gate that does, introduced in one repository with the other as control.
{% end %}

## What the first post could not say

[The machine arrived before the factory](@/blog/2026-10-21-the-machine-arrived-before-the-factory.md) measured PulseEngine's own repositories and found the structure stable, the checks partly hollow and the decision queue growing. It had no baseline. Every repository it measured shares one human author, so it could not say whether what it saw comes from agents, from young software, or from one person's habits.

This post adds the baseline. It measures rivet and spar against three projects written by people and four written mostly by coding agents, with one definition for all nine, and it reports which differences survive once the instrument has been checked.

## Nine projects, one ruler

| group | project | sampled history | source |
|---|---|---|---|
| written by people | Hubris, Oxide's embedded kernel | 1,864 commits, 2020-04 to 2026-10 | `.rs` |
| | Cranelift, inside wasmtime | first 2,000 commits, 2016-03 to 2018-05 | `.rs` |
| | PX4 autopilot | first 2,000 commits, 2011-12 to 2013-01 | `.c .cpp .h .hpp` |
| written mostly by agents | Anthropic's C compiler | 1,710 commits, 2026-01-23 to 2026-02-05 | `.rs .c .h` |
| | beads | first 2,000 commits, 2025-10 to 2026-01 | `.go` |
| | gastown | first 2,000 commits, 2025-12 to 2026-02 | `.go` |
| | OpenClaw | first 2,000 commits, 2025-11 to 2026-01 | `.ts .tsx .swift` |
| PulseEngine | rivet | 517 commits, 2026-03 to 2026-10 | `.rs` |
| | spar | 312 commits, 2026-03 to 2026-10 | `.rs` |

A commit counts when it touches a source file. Each history is cut into buckets of 250 commits, and 15 commits per bucket are drawn at random: 120 per project where the history is long enough, 45 for rivet and 30 for spar. The four agent projects are popular public projects built largely with coding agents; the human projects are systems projects whose early history predates coding agents.

**The classifier is checked before it is used.** A small model, Claude Haiku, reads each full commit message with any conventional prefix (`feat:`, `fix:`) stripped from every line and labels it feature, fix, refactor or maintenance. It was scored against two references before any project was labelled. On 160 rivet and spar commits, where the stripped prefix is the answer, fix precision was 0.84 and recall 0.89, and four-class agreement 86%. On 400 human-written commits from Levin and Yehudai's labelled dataset[^levin], fix precision was 0.92 and recall 0.89. Re-running the same commits gave the same label 91 to 96% of the time. The keyword rule that counts "fix" in a subject scored precision 0.38 and recall 0.06 on the agent commits, and is not used for any result below.

{% note(kind="tip") %}
**Can a small local model do this?** Three downloadable classifiers were run on the same references on a laptop. LiquidAI's d1-3B, a 2026 decision model, passed on human messages (fix precision 0.78, recall 0.86) and failed on agent messages (precision 0.69), so it would inflate the agent fix share relative to the human one, which is the comparison this post makes. fastino's GLiNER2.5-Decide scored precision 0.43 on agent subjects, and a GPT-2 fine-tuned for commit intent did not separate fixes from other commits. Haiku stays the instrument until a local model passes the same bar.
{% end %}

## What separates the groups: refactoring

<svg viewBox="0 0 760 378" width="100%" role="img" aria-labelledby="rf-title rf-desc" style="max-width:760px;height:auto;font-family:'Atkinson Hyperlegible Next',system-ui,sans-serif">
<title id="rf-title">Share of commits that refactor, per project</title>
<desc id="rf-desc">Refactor share of classified commits with 95% Wilson intervals. Hubris 24% (17 to 33, n=120); Cranelift 23% (17 to 32, n=120); PX4 18% (12 to 25, n=120); C compiler 10% (6 to 18, n=105); beads 7% (3 to 13, n=120); gastown 12% (8 to 20, n=120); OpenClaw 11% (6 to 18, n=120); rivet 7% (2 to 18, n=45); spar 7% (2 to 21, n=30).</desc>
<text x="12" y="22" font-size="13" font-weight="700" fill="var(--text,#e1e4ed)">Refactor share of commits</text>
<text x="12" y="40" font-size="10.5" fill="var(--text-dim,#8b90a0)"><tspan fill="var(--green,#4ade80)">●</tspan> written by people   <tspan fill="var(--accent,#6c8cff)">●</tspan> written mostly by agents</text>
<line x1="150.0" y1="52" x2="150.0" y2="326" stroke="var(--border-subtle,#3d4258)" stroke-width="0.6"/>
<text x="150.0" y="342" font-size="10" text-anchor="middle" fill="var(--text-faint,#808698)">0%</text>
<line x1="264.0" y1="52" x2="264.0" y2="326" stroke="var(--border-subtle,#3d4258)" stroke-width="0.6"/>
<text x="264.0" y="342" font-size="10" text-anchor="middle" fill="var(--text-faint,#808698)">10%</text>
<line x1="378.0" y1="52" x2="378.0" y2="326" stroke="var(--border-subtle,#3d4258)" stroke-width="0.6"/>
<text x="378.0" y="342" font-size="10" text-anchor="middle" fill="var(--text-faint,#808698)">20%</text>
<line x1="492.0" y1="52" x2="492.0" y2="326" stroke="var(--border-subtle,#3d4258)" stroke-width="0.6"/>
<text x="492.0" y="342" font-size="10" text-anchor="middle" fill="var(--text-faint,#808698)">30%</text>
<line x1="606.0" y1="52" x2="606.0" y2="326" stroke="var(--border-subtle,#3d4258)" stroke-width="0.6"/>
<text x="606.0" y="342" font-size="10" text-anchor="middle" fill="var(--text-faint,#808698)">40%</text>
<line x1="720.0" y1="52" x2="720.0" y2="326" stroke="var(--border-subtle,#3d4258)" stroke-width="0.6"/>
<text x="720.0" y="342" font-size="10" text-anchor="middle" fill="var(--text-faint,#808698)">50%</text>
<line x1="20" y1="146" x2="740" y2="146" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="3 4"/>
<text x="140" y="75.0" font-size="12" text-anchor="end" fill="var(--text,#e1e4ed)">Hubris</text>
<line x1="348.2" y1="71.0" x2="521.1" y2="71.0" stroke="var(--green,#4ade80)" stroke-width="2" opacity="0.55"/>
<circle cx="425.5" cy="71.0" r="5" fill="var(--green,#4ade80)"/>
<text x="529.1" y="75.0" font-size="10.5" fill="var(--text-dim,#8b90a0)">24%  (n=120)</text>
<text x="140" y="105.0" font-size="12" text-anchor="end" fill="var(--text,#e1e4ed)">Cranelift</text>
<line x1="340.0" y1="101.0" x2="510.9" y2="101.0" stroke="var(--green,#4ade80)" stroke-width="2" opacity="0.55"/>
<circle cx="416.0" cy="101.0" r="5" fill="var(--green,#4ade80)"/>
<text x="518.9" y="105.0" font-size="10.5" fill="var(--text-dim,#8b90a0)">23%  (n=120)</text>
<text x="140" y="135.0" font-size="12" text-anchor="end" fill="var(--text,#e1e4ed)">PX4</text>
<line x1="283.8" y1="131.0" x2="438.1" y2="131.0" stroke="var(--green,#4ade80)" stroke-width="2" opacity="0.55"/>
<circle cx="349.5" cy="131.0" r="5" fill="var(--green,#4ade80)"/>
<text x="446.1" y="135.0" font-size="10.5" fill="var(--text-dim,#8b90a0)">18%  (n=120)</text>
<text x="140" y="165.0" font-size="12" text-anchor="end" fill="var(--text,#e1e4ed)">C compiler</text>
<line x1="217.8" y1="161.0" x2="352.8" y2="161.0" stroke="var(--accent,#6c8cff)" stroke-width="2" opacity="0.55"/>
<circle cx="269.4" cy="161.0" r="5" fill="var(--accent,#6c8cff)"/>
<text x="360.8" y="165.0" font-size="10.5" fill="var(--text-dim,#8b90a0)">10%  (n=105)</text>
<text x="140" y="195.0" font-size="12" text-anchor="end" fill="var(--text,#e1e4ed)">beads</text>
<line x1="188.9" y1="191.0" x2="293.7" y2="191.0" stroke="var(--accent,#6c8cff)" stroke-width="2" opacity="0.55"/>
<circle cx="226.0" cy="191.0" r="5" fill="var(--accent,#6c8cff)"/>
<text x="301.7" y="195.0" font-size="10.5" fill="var(--text-dim,#8b90a0)">7%  (n=120)</text>
<text x="140" y="225.0" font-size="12" text-anchor="end" fill="var(--text,#e1e4ed)">gastown</text>
<line x1="238.0" y1="221.0" x2="373.5" y2="221.0" stroke="var(--accent,#6c8cff)" stroke-width="2" opacity="0.55"/>
<circle cx="292.5" cy="221.0" r="5" fill="var(--accent,#6c8cff)"/>
<text x="381.5" y="225.0" font-size="10.5" fill="var(--text-dim,#8b90a0)">12%  (n=120)</text>
<text x="140" y="255.0" font-size="12" text-anchor="end" fill="var(--text,#e1e4ed)">OpenClaw</text>
<line x1="223.4" y1="251.0" x2="351.3" y2="251.0" stroke="var(--accent,#6c8cff)" stroke-width="2" opacity="0.55"/>
<circle cx="273.5" cy="251.0" r="5" fill="var(--accent,#6c8cff)"/>
<text x="359.3" y="255.0" font-size="10.5" fill="var(--text-dim,#8b90a0)">11%  (n=120)</text>
<text x="140" y="285.0" font-size="12" text-anchor="end" fill="var(--text,#e1e4ed)">rivet</text>
<line x1="176.1" y1="281.0" x2="353.6" y2="281.0" stroke="var(--accent,#6c8cff)" stroke-width="2" opacity="0.55"/>
<circle cx="226.0" cy="281.0" r="5" fill="var(--accent,#6c8cff)"/>
<text x="361.6" y="285.0" font-size="10.5" fill="var(--text-dim,#8b90a0)">7%  (n=45)</text>
<text x="140" y="315.0" font-size="12" text-anchor="end" fill="var(--text,#e1e4ed)">spar</text>
<line x1="171.1" y1="311.0" x2="393.1" y2="311.0" stroke="var(--accent,#6c8cff)" stroke-width="2" opacity="0.55"/>
<circle cx="226.0" cy="311.0" r="5" fill="var(--accent,#6c8cff)"/>
<text x="401.1" y="315.0" font-size="10.5" fill="var(--text-dim,#8b90a0)">7%  (n=30)</text>
<text x="12" y="368" font-size="9.5" fill="var(--text-faint,#808698)">Bars: 95% Wilson interval. Full commit messages, prefixes stripped, labelled by Haiku; 15 commits per 250-commit bucket. Source: commit-classify.py, 22 October 2026.</text>
</svg>

Every project written by people refactors in 18 to 24% of its commits. Every project written mostly by agents does so in 7 to 12%. With no overlap between six values and three, the chance of this ordering arising by accident is 1 in 84 (exact permutation test, one-sided). The intervals for rivet and spar are wide because their samples are small, and their point values sit with the agent group.

Squash merging could hide refactoring inside pull requests, since rivet and spar merge each PR as one commit. The individual commits of the last 91 merged rivet PRs and 93 merged spar PRs say otherwise: 5 of 175 and 2 of 201 carry a `refactor:` prefix. The agents do not refactor inside the PR either.

## What does not separate them

**Fix share.** PX4 spends 37% of its commits on fixes, Hubris 28% and Cranelift 7%. The agent projects range from 22% (OpenClaw) to 46% (C compiler), with rivet at 40% and spar at 30%. The groups overlap.

**A rising fix curve.** Counted with the keyword rule over every commit, the fix share rises steeply in beads, gastown and OpenClaw. Most of that rise is the writing style changing. beads and OpenClaw went from a quarter to two fifths conventional commit messages in their first buckets to 97 and 98% in their last, and a `fix:` prefix is what the keyword finds. With the model labels, OpenClaw's fix share falls from 27% to 13% and beads stays between 27% and 47%. gastown, which used conventional messages from its first bucket, does rise, from 33% to 67%, though with 15 commits per bucket those two intervals overlap.

**Bugs introduced by fixes.** For each sampled fix, the source lines it deleted or changed were blamed in its parent commit, the standard SZZ procedure[^szz], and the commit owning most of those lines was labelled with the same classifier.

<svg viewBox="0 0 760 318" width="100%" role="img" aria-labelledby="ff-title ff-desc" style="max-width:760px;height:auto;font-family:'Atkinson Hyperlegible Next',system-ui,sans-serif">
<title id="ff-title">Fixes that repair an earlier fix, against the share of code fixes write</title>
<desc id="ff-desc">Share of traced fixes whose main introducing commit was itself a fix, with 95% Wilson intervals, and as a marker the share of added source lines written by fix commits. Hubris 4 of 28 (14%, interval 6 to 31) against 7%; Cranelift 0 of 8 (0%, interval 0 to 32) against 3%; C compiler 11 of 43 (26%, interval 15 to 40) against 25%; beads 8 of 37 (22%, interval 11 to 37) against 27%; gastown 4 of 37 (11%, interval 4 to 25) against 13%; rivet 5 of 21 (24%, interval 11 to 45) against 14%; spar 1 of 12 (8%, interval 1 to 35) against 9%.</desc>
<text x="12" y="22" font-size="13" font-weight="700" fill="var(--text,#e1e4ed)">Bugs introduced by an earlier fix</text>
<text x="12" y="40" font-size="10.5" fill="var(--text-dim,#8b90a0)"><tspan fill="var(--amber,#fbbf24)">▮</tspan> expected if fixes broke things at the rate they write code</text>
<line x1="150.0" y1="52" x2="150.0" y2="266" stroke="var(--border-subtle,#3d4258)" stroke-width="0.6"/>
<text x="150.0" y="282" font-size="10" text-anchor="middle" fill="var(--text-faint,#808698)">0%</text>
<line x1="264.0" y1="52" x2="264.0" y2="266" stroke="var(--border-subtle,#3d4258)" stroke-width="0.6"/>
<text x="264.0" y="282" font-size="10" text-anchor="middle" fill="var(--text-faint,#808698)">10%</text>
<line x1="378.0" y1="52" x2="378.0" y2="266" stroke="var(--border-subtle,#3d4258)" stroke-width="0.6"/>
<text x="378.0" y="282" font-size="10" text-anchor="middle" fill="var(--text-faint,#808698)">20%</text>
<line x1="492.0" y1="52" x2="492.0" y2="266" stroke="var(--border-subtle,#3d4258)" stroke-width="0.6"/>
<text x="492.0" y="282" font-size="10" text-anchor="middle" fill="var(--text-faint,#808698)">30%</text>
<line x1="606.0" y1="52" x2="606.0" y2="266" stroke="var(--border-subtle,#3d4258)" stroke-width="0.6"/>
<text x="606.0" y="282" font-size="10" text-anchor="middle" fill="var(--text-faint,#808698)">40%</text>
<line x1="720.0" y1="52" x2="720.0" y2="266" stroke="var(--border-subtle,#3d4258)" stroke-width="0.6"/>
<text x="720.0" y="282" font-size="10" text-anchor="middle" fill="var(--text-faint,#808698)">50%</text>
<line x1="20" y1="116" x2="740" y2="116" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="3 4"/>
<text x="140" y="75.0" font-size="12" text-anchor="end" fill="var(--text,#e1e4ed)">Hubris</text>
<line x1="215.0" y1="71.0" x2="509.0" y2="71.0" stroke="var(--green,#4ade80)" stroke-width="2" opacity="0.55"/>
<rect x="231.2" y="63.0" width="3" height="16" fill="var(--amber,#fbbf24)"/>
<circle cx="312.9" cy="71.0" r="5" fill="var(--green,#4ade80)"/>
<text x="517.0" y="75.0" font-size="10.5" fill="var(--text-dim,#8b90a0)">4/28</text>
<text x="140" y="105.0" font-size="12" text-anchor="end" fill="var(--text,#e1e4ed)">Cranelift</text>
<line x1="150.0" y1="101.0" x2="519.8" y2="101.0" stroke="var(--green,#4ade80)" stroke-width="2" opacity="0.55"/>
<rect x="178.7" y="93.0" width="3" height="16" fill="var(--amber,#fbbf24)"/>
<circle cx="150.0" cy="101.0" r="5" fill="var(--green,#4ade80)"/>
<text x="527.8" y="105.0" font-size="10.5" fill="var(--text-dim,#8b90a0)">0/8</text>
<text x="140" y="135.0" font-size="12" text-anchor="end" fill="var(--text,#e1e4ed)">C compiler</text>
<line x1="320.2" y1="131.0" x2="608.7" y2="131.0" stroke="var(--accent,#6c8cff)" stroke-width="2" opacity="0.55"/>
<rect x="430.7" y="123.0" width="3" height="16" fill="var(--amber,#fbbf24)"/>
<circle cx="441.6" cy="131.0" r="5" fill="var(--accent,#6c8cff)"/>
<text x="616.7" y="135.0" font-size="10.5" fill="var(--text-dim,#8b90a0)">11/43</text>
<text x="140" y="165.0" font-size="12" text-anchor="end" fill="var(--text,#e1e4ed)">beads</text>
<line x1="279.8" y1="161.0" x2="574.0" y2="161.0" stroke="var(--accent,#6c8cff)" stroke-width="2" opacity="0.55"/>
<rect x="459.9" y="153.0" width="3" height="16" fill="var(--amber,#fbbf24)"/>
<circle cx="396.5" cy="161.0" r="5" fill="var(--accent,#6c8cff)"/>
<text x="582.0" y="165.0" font-size="10.5" fill="var(--text-dim,#8b90a0)">8/37</text>
<text x="140" y="195.0" font-size="12" text-anchor="end" fill="var(--text,#e1e4ed)">gastown</text>
<line x1="198.9" y1="191.0" x2="431.7" y2="191.0" stroke="var(--accent,#6c8cff)" stroke-width="2" opacity="0.55"/>
<rect x="301.2" y="183.0" width="3" height="16" fill="var(--amber,#fbbf24)"/>
<circle cx="273.2" cy="191.0" r="5" fill="var(--accent,#6c8cff)"/>
<text x="439.7" y="195.0" font-size="10.5" fill="var(--text-dim,#8b90a0)">4/37</text>
<text x="140" y="225.0" font-size="12" text-anchor="end" fill="var(--text,#e1e4ed)">rivet</text>
<line x1="271.2" y1="221.0" x2="664.0" y2="221.0" stroke="var(--accent,#6c8cff)" stroke-width="2" opacity="0.55"/>
<rect x="307.8" y="213.0" width="3" height="16" fill="var(--amber,#fbbf24)"/>
<circle cx="421.4" cy="221.0" r="5" fill="var(--accent,#6c8cff)"/>
<text x="672.0" y="225.0" font-size="10.5" fill="var(--text-dim,#8b90a0)">5/21</text>
<text x="140" y="255.0" font-size="12" text-anchor="end" fill="var(--text,#e1e4ed)">spar</text>
<line x1="166.9" y1="251.0" x2="553.4" y2="251.0" stroke="var(--accent,#6c8cff)" stroke-width="2" opacity="0.55"/>
<rect x="250.9" y="243.0" width="3" height="16" fill="var(--amber,#fbbf24)"/>
<circle cx="245.0" cy="251.0" r="5" fill="var(--accent,#6c8cff)"/>
<text x="561.4" y="255.0" font-size="10.5" fill="var(--text-dim,#8b90a0)">1/12</text>
<text x="12" y="308" font-size="9.5" fill="var(--text-faint,#808698)">B-SZZ on the sampled fixes; the introducer is the commit owning most blamed lines. Source: szz.py, 22 October 2026.</text>
</svg>

The share of fixes repairing an earlier fix ranges from 0% in Cranelift to 26% in the C compiler. Each value sits close to the share of source lines that the project's fix commits write, the marker in the figure, and every interval contains it. Fixes break things at about the rate at which they write code, in both groups. rivet's 5 of 21 is above its marker of 14%, with an interval from 11 to 45%; that is a hint at best. Features introduce 65 to 71% of the traced bugs in Hubris, beads, gastown, rivet and spar, 38% in Cranelift (8 fixes) and 33% in the C compiler.

**How long a bug lives.** Measured in days, agent projects repair bugs within a week (C compiler 1 day, beads 5, gastown 7) and the human projects take months (Hubris 105, Cranelift 58). Measured in commits, the gap disappears: the median bug lives 61 to 242 commits in every project, rivet 232 and spar 129. The day count measures how fast a project commits.

**Coupling.** The 90th percentile of source files per commit stays between 4 and 15 in every bucket of every project, so none of them shows the shotgun surgery that marks a code base its agents can no longer change.

## Two kinds of refactoring

The word covers two different activities, and only one of them is missing. The first is maintenance refactoring: a behaviour-preserving change to make code easier to change next time, in Martin Fowler's definition[^fowler], done in small steps because the code has started to resist. Kent Beck's *Tidy First?* is about when to do it, and his talk *Features Versus Futures* puts the trade in one picture: every feature spends some of the options a code base still has, and tidying buys them back[^beck]. People do this because they feel friction in the code. Agents do not feel it. They repair the same place again, and the commit counts above are what that looks like from the outside.

The second is redesign from insight: a new idea about the problem. PulseEngine has these. Its runtime, kiln, an interpreter, is being joined by meld, which fuses components when they are built, and synth, which transcodes them ahead of time to ARM and RISC-V. kiln's history shows quarters in which more source was deleted than added: 2025's fourth quarter at 1.31 lines deleted per line added and 2026's second at 3.39, against at most 0.25 for rivet and 0.09 for spar in any quarter. The largest of those deletions remove dead and duplicated code: 40,064 lines of broken tests in one commit, a 33,905-line unused async surface in another, a duplicated crate in a third (16,164 lines deleted). No commit statistic can attribute those deletions, or the features growing in synth, to one architectural decision. Only the decision can, if it is recorded and the pull requests reference it.

## Where it shows in rivet

`rivet-cli/src/main.rs` holds 23,764 lines. From 1 August to 22 October 2026, 60 commits touched it and 35 of them were fixes. The file with the most fixes in spar over the same window has 6. In a team, a file like this gets split because the people working in it complain. Here nobody does, and the next fix lands in the same file.

The other difference is who finds the bugs. In Hubris, 12 of 33 sampled fixes come from authors outside the five most active; in beads and gastown, 8 of 44 and 8 of 48. rivet and spar have two authors each and no outside fixes. Every bug in them is found by the owner's agents and their checks, which is why the gates of the first post matter as much as they do.

## What PulseEngine does next

The measurement says which gate is missing. The agents optimise for what the oracle checks, and nothing yet checks structure. The proposal is a **fix-hotspot trigger**: when a file collects more than a set number of fixes in a window, the next fix to it opens a refactoring task instead of another spot fix. It does not exist yet, and it will be introduced as an experiment so that the next post can say whether it worked:

- **One change at a time.** The trigger alone, without other process changes in the same period.
- **A control.** rivet gets the trigger; spar runs unchanged.
- **The same measurement monthly.** The scripts below, run on a schedule, with the classifier re-scored against its frozen references before every run and the report withheld if it misses the bar.
- **The criterion fixed in advance.** It is recorded as a checked claim in the repository before the trigger ships, so that no curve can be read as success afterwards. Fix-on-fix is not a usable criterion at this sample size: rivet's 5 of 21 has an interval from 11 to 45%. Refactor share inside pull requests and fixes per month on the hotspot file are. The result, after three to six months, is the next post.

## Limits

The samples are small: 30 to 120 classified commits per project and 8 to 43 traced fixes, which is why every share comes with its interval. The classifier reads messages, and messages cannot show a fix nobody mentioned; agents mention side fixes more often (11% of rivet's and 17% of spar's commits, at most 4% elsewhere). SZZ blames the last commit to touch a line, which misattributes across moves and refactorings, and fixes that only add lines have nothing to blame (9 to 30% per project). PX4 and OpenClaw were not traced. Hubris's sample runs into 2026, when its authors may also use agents. "Outside the five most active authors" approximates outside contributors. The agent projects were chosen because they are the popular public examples, not at random, and PulseEngine's two share one human author.

## Reproduce

The scripts are in the repository under `scripts/`, and the guide [Measure your own repository](@/docs/guide/measure-your-repository.md) explains how to run them on yours.

```sh
commit-classify.py oracle <rivet> <spar> --ext .rs      # agent reference, prefixes stripped
commit-classify.py levin all_changes.csv                # human reference
commit-classify.py score oracle <labels.json>           # fix precision/recall, Wilson intervals
commit-classify.py sample <clone> --ext ... --name N    # 15 commits per 250-commit bucket
commit-classify.py mix N ... --by-bucket                # shares and the fix curve
szz.py <full clone> --ext ... --fixes szz/N-fixes.json --out szz/N.json
szz-introducers.py <dir>                                # introducers to label, and the null
tidy-charts.py refactor | fixonfix                      # the two figures
churn-ratio.py <clone> ...                              # deleted per added line, per quarter
```

The labels come from a model and are not deterministic, so the reference score is re-run and reported whenever the model changes. Projects were read on 22 October 2026, rivet at `9e6fb60b` and spar at `02094f96`.

[^levin]: Stanislav Levin and Amiram Yehudai, "Boosting Automatic Commit Classification Into Maintenance Activities By Utilizing Source Code Changes", PROMISE 2017. Dataset: [zenodo.org/record/835534](https://zenodo.org/record/835534), CC BY-SA 4.0. Corrective commits are mapped to fix, everything else to not-fix.

[^szz]: Jacek Śliwerski, Thomas Zimmermann and Andreas Zeller, "When do changes induce fixes?", MSR 2005. The variant here blames in the fix's parent and ignores whitespace, blank and comment-only lines.

[^fowler]: Martin Fowler, *Refactoring: Improving the Design of Existing Code*, Addison-Wesley, 1999; second edition 2018.

[^beck]: Kent Beck, *Tidy First? A Personal Exercise in Empirical Software Design*, O'Reilly, 2023. *Features Versus Futures*, IT Revolution Enterprise AI Summit 2026, [videos.itrevolution.com/watch/1183714411](https://videos.itrevolution.com/watch/1183714411); the talk's framing is taken from the event listing and from Beck's interview on the *Maintainable* podcast, [maintainable.fm](https://maintainable.fm/episodes/kent-l-beck-youre-ignoring-optionality-and-paying-for-it).
