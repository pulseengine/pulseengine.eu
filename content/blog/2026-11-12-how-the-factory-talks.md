+++
title = "How the factory talks: four channels, one record, and who owns what"
description = "Agent sessions coordinate over four channels: direct messages between sessions, subagents inside one session, issues read on a schedule, and option dialogs to me. What lasts is the rivet artifact an issue becomes. Three recent events went through these channels: a low disk on 8 November, a check that passed by being skipped and settings that never reached the agents."
date = 2026-11-12
draft = true
hold = true
[taxonomies]
tags = ["process", "ai-agents", "orchestration"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**Decisions that are mine come from me, in an option dialog, a merge or a released message, and never from another session; messages between sessions are requests, and rivet keeps the record.**

Issues take work in, messages coordinate, and subagents do bounded work
inside one session. On one workstation, messages received from other sessions
went from none in the week of 12 October to 129 in the partial week of 2
November (as of 8 November), a week with 10 sessions.
{% </insight> %}

## What this is about, from the outside

PulseEngine is an open-source, pre-1.0 project. It builds a WebAssembly
Component Model engine meant for safety-critical systems, together with the
tools that check the work: rivet for traceability from requirement to test,
spar for architecture models, witness, which measures test coverage of the
compiled WebAssembly, and sigil for signing what ships. Most of the day-to-day work in these repositories,
code, tests, issues and these posts, is done by Claude agent sessions, each
looking after one repository, while I decide what ships. I call that setup the
factory.

Each session knows its own repository well and knows little about the others.
With about ten of them running side by side on one workstation, the hard part
is keeping them in step with each other and with me: who tells whom what,
where a decision is recorded, and how a mistake made in one repository gets
caught in another.

Two earlier posts cover the neighbouring ground: [The orchestrator: who does
what](/blog/the-orchestrator-who-does-what/) on the repos and the contracts
between them, and [The scarce resource is the orchestrator's
attention](/blog/the-scarce-resource-is-attention/) on the decision inbox that
rations me. This one covers which channel carries which kind of message, who
owns which job, and three recent events, the first on 8 November 2026. Below,
"the checker" is the Claude session that writes this site and the plugin every
session loads, and "I" is the owner of the factory.

## The four channels

**Issues and comments, on a schedule.** Agents run the `issue-hunt` loop on a
cron: each pass reads what is new since its last watermark, triages it, and
works it in the repo that owns it. Issues are where work enters, from outside
reporters as much as from agents, and where the reporter hears back. Most are
public and outlive every session. They are also slow: an agent learns about a
comment at its next pass.

**Direct messages between sessions.** The Claude Code changelog entry in
version 2.1.224 reads "Added cross-session `SendMessage`": a session can
send a message to another. Version 2.1.166 had already hardened relayed
messages: "receivers refuse relayed permission requests" ([Claude Code
changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)).
A session running with bypassed permissions holds incoming messages until I
release them, unless I changed that setting. Releasing a held message is not a
decision on what it asks. Messages leave no public trace, which suits "can you free your disk" and
"is this yours" and does not suit a decision.

**Subagents.** A session starts a subagent for a bounded task, such as a scan
over many files or a fresh-context review of its own claims, and gets one
report back. A subagent reports back to its parent. The `delegate-by-cost`
skill picks its model: mechanical work with an exact check goes to the cheapest
tier.

**Option dialogs to me.** A fork that is mine to take becomes a
question with a few options, the trade-offs and a recommendation. Agents
never take such a fork on a peer's word. When an agent is not in a session I
am watching, the question goes to the decision inbox, which surfaces at
most three routine flows at a time.

{% <mermaid> %}
flowchart LR
    owner["me<br/><i>decides</i>"]
    subgraph sessions["agent sessions"]
        direction TB
        repo["repo sessions<br/><i>one repo each</i>"]
        checker["the checker"]
        sub["subagents"]
    end
    gh["GitHub issues<br/>and comments"]
    warte["warte<br/><i>reports the fleet</i>"]
    rivet["rivet artifacts<br/><i>the record</i>"]

    repo ---|"direct messages"| checker
    checker -->|"bounded task"| sub
    sub -->|"one report"| checker
    repo ---|"read on a schedule"| gh
    gh -->|"actionable item"| rivet
    sessions -->|"option dialog"| owner
    owner -->|"answer"| sessions
    warte -.->|"queue, admission"| sessions
    sessions -.->|"notices"| warte
    temper["temper<br/><i>org-wide repo rules</i>"] -.-> gh
{% </mermaid> %}

## Behind the issues: the record (rivet)

An issue holds the conversation; the rivet artifact holds the requirement. When
`issue-hunt` finds an item actionable, it lands it in rivet as a typed
artifact (a requirement, a design decision, a verification), links it into the
trace and assigns it to a release. A regression later re-opens the
requirement, not a closed thread. The release gate checks those artifacts, and
the issue closes against the tagged release. So the durable layer is rivet;
issues are its intake and its customer-facing side.

{% <mermaid> %}
flowchart LR
    m["message<br/><i>coordination, no public trace</i>"] --> i["issue<br/><i>intake, the reporter's thread</i>"]
    i --> a["rivet artifact<br/><i>requirement, decision, verification</i>"]
    a --> r["release<br/><i>gate checks the trace</i>"]
    r --> c["issue closes<br/><i>against the tagged release</i>"]
{% </mermaid> %}

## Who sits where

| component | its job | what it never does |
|---|---|---|
| repo sessions | own one repo: its code, CI and issues | change another repo's branches or settings |
| warte | report the fleet: CI queue, admission advice, wait estimates, notices | decide or delete anything |
| temper | configure repos to org-wide rules (merge settings, branch protection, labels) and sync them across the organisation; a change-filter check is planned, detection first | enforce that planned check before I decide |
| machine configuration (a private repo and its session) | apply configuration to the machines, and would apply the planned check per repo | merge its own changes; I merge |
| the checker session | coordinate across sessions and re-check their claims | fix another session's repo |
| me, the owner | take every decision that is mine | — |

In these events the checker did more coordinating than checking, and the
mistakes showed, as the last section records.

## Three events

**A low disk (14 GB free).** On 8 November the workstation's data volume had 14 GB free.
The checker measured who held the space: per-session scratch directories under
the temporary directory, and build caches in one repo's checkout and three of
its worktrees. The four build caches of that repo (meld) held 22.3, 12.4, 9.8 and
9.8 GB, about 54 GB, and four session scratchpads of about 5 to 14 GB each came on
top. It messaged five sessions, each with the
size and location of what it held, and asked each to clean only its own data
and report what it freed. The five sessions reported freeing about 57, 14, 12, 8
and 5 GB. They measured at overlapping moments, and the 57 included removed
worktrees, so the number to trust is the net rise in free space, from 14 to 82
GB. Two Rust toolchains that nothing pinned were removed
after I approved it in a dialog, because the toolchain directory is
shared.

I then asked for the check to become mechanical. The checker proposed
an endpoint in warte that would name the holders. pulseengine.eu#356 records the outcome as
"Design revised the same day in warte: names only locally, pressure per
volume". The
plugin side is drafted as a hook that will read a local command before a disk-heavy
command and will say, with the command's result, who holds what when a volume
is low. That needs warte to ship the local command; without it, the hook
reports volume pressure only. #356 is a draft until warte releases the
command.

**A check that passed by being skipped.** The rivet session found that a PR
changing only `supply-chain/` files had skipped its cargo-vet check. A job
that a condition skips counts as passing a required check on GitHub, so the filter that decides
"did code change?" also decides what is gated. The checker scanned 45 repos
and their 143 required checks:

- rivet's case is a skipped job: its filter listed code paths, so any file type
  it did not name made the job skip, and the skip counted as passing;
- meld's case is different: a stub workflow reports success under the same check
  names on the paths the real workflow ignores. It excluded `safety/**` (meld#580),
  and its session then found a second gap, Markdown compiled into the binary (`meld-cli/docs/*.md`, meld
  PR #581);
- spar, varve and gale list what is not code and treat everything else as
  code, which fails closed;
- relay's gate rejects a skipped check unless the detector job succeeded,
  which also fails closed.

temper configures repositories to org-wide rules today. A change-filter check
is planned (meld#580), detection first. A probe that would feed each repo's change filter files that
must count as code is proposed. Enforcement waits for me. The configuration session would apply it per repo, because
organisation-wide rulesets are the alternative and the free plan does not offer
them for private repositories. Both would ask me before building it. The
finding started in a direct message and ended, so far, as an issue (meld#580), a meld PR
(#581), PRs in the repos that own the fix, and a decision waiting on me.

**Settings that never reached the agents.** The gale session reported, in a
direct message, that a call to an address warte had retired came back empty.
Checking showed the
four warte settings lived in a shell startup file whose exports never reached the agents' tool
shell. Agents had been running without them, so every warte call fell
back silently: admission advice, wait estimates and notice sync. The change that
puts the values into Claude Code's own settings on both machines is an open PR
in the private configuration repo; I set them by hand on one machine. The same pattern as the skipped check: the configuration existed, did
nothing, and no check failed.

## What the numbers say

The table counts sessions, messages received from other sessions, SendMessage
calls and option dialogs per week. Message use rose from none to 129 received
in the partial week of 2 November, as of 8 November.

{% <mermaid> %}
xychart-beta
    title "Messages received from other sessions, per week (one workstation, as of 8 November)"
    x-axis ["12 Oct", "19 Oct", "26 Oct", "2 Nov (partial)"]
    y-axis "messages" 0 --> 140
    bar [0, 5, 12, 129]
{% </mermaid> %}

| week of | sessions | messages received from other sessions | SendMessage calls | option dialogs |
|---|---|---|---|---|
| 12 Oct | 230 | 0 | 11 | 32 |
| 19 Oct | 125 | 5 | 38 | 53 |
| 26 Oct | 209 | 12 | 104 | 76 |
| 2 Nov | 10 | 129 | 242 | 114 |

Counts come from one workstation's local transcripts, up to 8 November. The week of 2 November is partial.

The feature was installed for weeks before the first message between sessions
arrived, on 22 October. In my own account, use took off in the week I told the
sessions to talk to each other directly. The session shape changed in the same
week: 10 sessions in the week, against 125 to 230 earlier, so there was
always someone to message. The two cannot be separated. SendMessage counts may
include messages to a session's own subagents.

## What I keep, and what I would change

Messages coordinate, issues take work in and answer the people who filed it,
and rivet keeps the record. Each thread this post describes is now an
issue, a PR or a dialog, and the draft plugin change (#356) would add its requirement and
verification to rivet (REQ-DISK-PRESSURE and VER-DISK-PRESSURE), so that its
decision would not live only in a transcript. I would not move the scheduled
issue sync onto messages, and I would not let issues stand in for rivet: an
issue can be read by someone who was not there, and a rivet artifact can also
be checked, traced and gated, which neither a thread nor a transcript can.

Names are the weak point. One session is called one thing on its own machine
and another over Remote Control, and the probe sees process ids, not session
names. The ci-status skill, not the hook, carries the rule that the agent asks
me when a match is ambiguous. The disk-pressure hook will name holders
by repo and session id once warte ships the local command.

The checker needs checking too. The checker misrouted a brief and drafted a
design the warte session sent back. In both cases the session that owned the
affected thing caught the error.
