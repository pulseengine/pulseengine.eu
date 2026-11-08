+++
title = "How the factory talks: four channels and who sits on each"
description = "Agent sessions coordinate over four channels: direct messages between sessions, subagents inside one session, issues read on a schedule, and option dialogs to the owner. What lasts is neither a message nor an issue but the rivet artifact an issue turns into. warte reports the fleet, temper checks the rules across repos, smithy applies them to the machines, and one session checks the others. On 8 November a full disk and a check that passed by being skipped went through all of it in one day."
date = 2026-11-12
draft = true
hold = true
[taxonomies]
tags = ["process", "ai-agents", "orchestration"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**Four channels, each with one job; the record is rivet, and approval travels on only one channel.**

- Issues and comments, read by agents on a schedule, are the intake and the
  public conversation: bugs, requests, and replies to whoever filed them.
- rivet artifacts are the durable record. An actionable issue becomes a
  requirement, decision or verification in rivet, traced and assigned to a
  release, and the issue closes against that release.
- Direct messages between sessions are for coordination. On one workstation
  they went from none in the week of 28 September to 117 received in the week
  of 2 November.
- Subagents do bounded work inside one session and report back to it.
- Option dialogs are where the owner decides. A message from another session
  is a teammate's request and never counts as the owner's approval.
{% </insight> %}

[The orchestrator: who does what](/blog/the-orchestrator-who-does-what/)
described the repos and the contracts between them, and [The scarce resource
is the orchestrator's attention](/blog/the-scarce-resource-is-attention/)
described the decision inbox that rations the owner. This post is about the
wiring underneath: which channel carries which kind of message, which
component owns which job, and what happened when all of it was used at once on
8 November 2026.

## The four channels

**Issues and comments, on a schedule.** Agents run the `issue-hunt` loop on a
cron: each pass reads what is new since its last watermark, triages it, and
works it in the repo that owns it. Issues are where work enters, from outside
reporters as much as from agents, and where the reporter hears back. They are
public and outlive every session. They are also slow: an agent learns about a
comment at its next pass, hours later.

**Behind the issues: rivet.** An issue is a conversation, not a record. When
`issue-hunt` finds an item actionable, it lands it in rivet as a typed
artifact (a requirement, a design decision, a verification), links it into the
trace and assigns it to a release. A regression later re-opens the
requirement, not a closed thread. The release gate checks those artifacts, and
the issue closes against the tagged release. So the durable layer is rivet;
issues are its intake and its customer-facing side.

**Direct messages between sessions.** Claude Code added `SendMessage` and
`ListAgents` between sessions in version 2.1.224: a session can find the other
sessions on the same machine and on the owner's other machines, and send one
plain text. Earlier, in 2.1.166, relayed messages lost user authority:
"receivers refuse relayed permission requests" ([Claude Code
changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)).
A session running with bypassed permissions holds incoming messages for the
owner's approval unless the owner changed that setting. Messages arrive in
seconds and leave no public trace, which suits "can you free your disk" and
"is this yours" and does not suit a decision.

**Subagents.** A session starts a subagent for a bounded task, such as a scan
over many files or a fresh-context review of its own claims, and gets one
report back. The subagent talks only to its parent. The `delegate-by-cost`
rule picks its model: mechanical work with an exact check goes to the cheapest
tier.

**Option dialogs to the owner.** A fork that is the owner's to take becomes a
question with two to four options, the trade-offs and a recommendation. Agents
never take such a fork on a peer's word. When an agent is not in a session the
owner is watching, the question goes to the decision inbox, which surfaces at
most three routine flows at a time.

## Who sits where

| component | its job | what it never does |
|---|---|---|
| repo sessions | own one repo: its code, CI and issues | change another repo's branches or settings |
| warte | report the fleet: CI queue, admission advice, wait estimates, notices | decide or delete anything |
| temper | check rules across all repos, then propose enforcement | apply settings without the owner's yes |
| smithy | apply configuration to machines and runners | merge its own changes; the owner merges |
| the checker session | coordinate across sessions and re-check their claims | fix another session's repo |
| the owner | take every decision that is theirs | — |

The checker is the session that writes this site and the plugin every session
loads. On 8 November it did more coordinating than checking, and the
overreach showed: it sent one brief to the wrong session, and drafted a design
that the warte session sent back.

## One day through all four channels

**A full disk.** On 8 November the workstation's data volume had 14 GB free.
The checker measured who held the space: per-session scratch directories under
the temporary directory, and build caches in one repo's checkout and three of
its worktrees, about 54 GB of them. It messaged five sessions, each with the
size and location of what it held, and asked each to clean only its own data
and report what it freed. They reported about 57, 14, 12, 8 and 5 GB. Free
space reached 82 GB. Two Rust toolchains that nothing pinned were removed
after the owner approved it in a dialog, because the toolchain directory is
shared.

The owner then asked for the check to become mechanical. The checker proposed
an endpoint in warte that would name the holders. The warte session objected
that warte's public read API never names sessions, paths or process ids, and
that pressure is per volume, since checkouts can live on a different volume
than the system's. The owner revised the design in the warte session: the
public answer carries totals only, and a local command on each machine names
the holders. The plugin side became a hook that reads that local command
before a disk-heavy command and says, with the command's result, who holds
what when a volume is low. It is pulseengine.eu#356, a draft until warte
releases the command.

**A check that passed by being skipped.** The rivet session found that a PR
changing only `supply-chain/` files had skipped its cargo-vet check. GitHub
counts a skipped job as passing a required check, so the filter that decides
"did code change?" also decides what is gated. The checker scanned 45 repos
and their 143 required checks:

- rivet's filter listed code paths, so any file type it did not name went
  ungated;
- meld excluded `safety/**` from CI, which admits any file type; its session
  then found a second gap, Markdown that is compiled into the binary;
- spar, varve, gale and relay list what is not code and treat everything else
  as code, which fails closed.

temper will check this across all repos with a probe that feeds each repo's
change filter files that must count as code. smithy will enforce it per repo,
since organisation-wide rulesets are not available on the free plan. Both
asked the owner in a dialog before building anything. The finding started in
a direct message and ended as an issue (meld#580), PRs in the repos that own
the fix, and an owner decision.

**Settings that never reached the agents.** The gale session reported that a
call to an address warte had retired came back empty. Checking that showed the
four warte settings lived in a shell startup file that Claude Code's tool shell
never reads. Agents had been running without them, so every warte call fell
back silently: admission advice, wait estimates and notice sync. The values
now sit in Claude Code's own settings, and smithy carries that to both
machines. This is the same pattern as the skipped check: wired in
appearance, inert in effect, and nothing went red.

## What the numbers say

From one workstation's local transcripts, which keep about 30 days:

| week of | sessions | messages received from other sessions | SendMessage calls | option dialogs |
|---|---|---|---|---|
| 28 Sep | 8 | 0 | 1 | 22 |
| 5 Oct | 176 | 0 | 1 | 33 |
| 12 Oct | 230 | 0 | 11 | 32 |
| 19 Oct | 125 | 5 | 38 | 53 |
| 26 Oct | 209 | 12 | 104 | 76 |
| 2 Nov | 10 | 117 | 207 | 104 |

The feature was installed for weeks before the first message between sessions
arrived, on 22 October. Use took off in the week the owner told the sessions
to talk to each other directly, and in the same week the sessions changed
shape: ten sessions ran for most of the week instead of a hundred or more
short ones, so there was always someone to message. SendMessage counts include
messages to a session's own subagents.

## What we keep, and what we would change

Messages coordinate, issues take work in and answer the people who filed it,
and rivet keeps the record. Every message thread on 8 November ended in an
issue, a PR or a dialog, and the plugin change carries its requirement and its
verification in rivet (REQ-DISK-PRESSURE and VER-DISK-PRESSURE in #356). None
of the decisions lives only in a transcript. We would not move the scheduled
issue sync onto messages, and we would not let issues stand in for rivet: an
issue can be read by someone who was not there, and a rivet artifact can also
be checked, traced and gated, which neither a thread nor a transcript can.

Names are the weak point. One session is called one thing on its own machine
and another over Remote Control, and the probe sees process ids, not session
names. The disk-pressure hook therefore names holders by repo and session id,
and tells the agent to ask the owner when the match is ambiguous.

The checker needs checking too. It misrouted a brief and proposed a design
that broke a privacy rule it had not read. Both were caught by the receiving
session, which is the argument for keeping every role narrow: a session that
owns one thing notices when someone else gets that thing wrong.
