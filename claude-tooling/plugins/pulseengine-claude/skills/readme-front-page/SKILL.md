---
name: readme-front-page
description: Use when writing, rewriting or reviewing a repository README ("rewrite the README", "pitch this repo", "the README is too long"). It sets one shape (vision, why use it, quick start, status, where to find more) and guards against both traps, hype and micro-documentation.
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# README front page: the vision, what we genuinely have, and where the rest lives

A README is a front page. A visitor decides in under a minute whether the tool
is for them and how to start. On 2026-11-27, 19 PulseEngine READMEs ran from 174
to 3,853 words, with no two in the same shape. In most of them the first screen
was caveats, requirement IDs and kernel ABI numbers, and none said in a few lines
why someone should use the tool.

An agent writing a README drifts into one of two traps. This skill holds both.

- **Hype.** "The only", "production-ready", "proven secure", a planned feature
  written in the present tense, a comparison with a tool nobody checked. It is
  close to hallucination: the sentence is fluent, but nothing stands behind it.
- **Micro-documentation.** Every caveat, errno, ABI level and design-decision ID
  goes on the front page. Each sentence is true, and together they hide the point.
  Honesty about scope belongs in **one Status block**, not in a caveat in every
  paragraph.

**The rule that separates them: the README says what and why at the level where
a user decides; the detail is one link away and complete there.** Nothing is
deleted. Detail moves to `docs/` in the same PR.

## The shape, in this order

Body length: 300 to 600 words, not counting code blocks.

1. **Name and one sentence.** What it is and who it is for, in plain words.
2. **Vision.** In 2 to 4 sentences: where this is going and why it matters. The
   future tense is allowed here and only here, and it is marked as direction
   ("The goal is …").
3. **Why use it.** At most three bullets. Each is something the repo has
   **today**, with its evidence one link away: a proof job, a test, a release
   verification command. Compare with another tool only after checking that
   tool's own docs or code in the last month. Phrase it as "we found no other … that …", never
   "the only".
4. **Quick start.** Install, then at most three commands, run on a clean machine
   before merge.
5. **Status.** A short list or table with each part marked works, prototype or
   planned, one line each. All the scope honesty goes here.
6. **Where to find more.** Links to `docs/`, the architecture model, proofs,
   release verification and the rivet requirements.
7. **Contributing and licence.** One or two lines that invite use, issues and
   PRs.

## What moves out of the README

- Requirement and decision IDs (`REQ-`, `DD-`, `SR-`) go to the artifacts and
  docs.
- Per-platform caveat lists, errno tables and kernel ABI matrices go to
  `docs/<platform>.md`.
- The full CLI reference goes to `docs/cli.md` or `--help`.
- Proof inventories go to `docs/proofs.md`. The README keeps one sentence and a
  link.
- How our agents and CI fleet work never goes in a README. Private
  infrastructure never goes anywhere public.

## Writing the pitch without hype

- Derive each "why" bullet from a tool result you can name: the CI job, the
  test, the command. If you cannot name one, cut the bullet or move it to Vision
  as a goal.
- One strong, checkable claim beats five soft ones. Keep each claim at the
  strength of its instrument (`claim-verification`).
- These words each need their evidence, or they go: only, first, guaranteed,
  secure, proven, production, seamless, fast.
- A prototype feature is listed in Status as a prototype and is never used as
  a reason to adopt the tool.

## Stopping before micro-documentation

- Status is the only place for caveats. A paragraph elsewhere that starts with
  "Note", "Not covered" or "Below version N" belongs in `docs/`.
- Over 600 words: move the longest section to `docs/` and link it from section 6.
- Stop when a reader can decide and start. Completeness is the job of `docs/`.

## Procedure

1. Read the current README and the repo. List what the repo has today, each item
   with its evidence, and separately what is planned.
2. Draft in the shape above. In the same PR, move the removed detail into `docs/`
   files and link them from section 6.
3. Check mechanically:
   - body word count: `sed '/^```/,/^```/d' README.md | wc -w` is 600 or less;
   - no requirement IDs: `grep -nE '\b(REQ|DD|SR)-[A-Z0-9-]+' README.md` is empty;
   - every "why" bullet carries a link;
   - the quick start runs on a clean machine.
4. Get one fresh-context fact-check of every claim and comparison
   (`publication-review` at small-edit depth), plus an editor pass for length. A
   new public README that compares with named tools gets the full panel.
5. One PR per repo, written by that repo's own session.

## Worked example: zwinger, 2026-11-27

The README was 2,168 words. Its first screen covered Landlock ABI levels and
errno values, and its "Why" section described other sandboxes as shell scripts,
which had gone out of date. A comparison against about a dozen agent sandboxes,
each checked against its own docs or code, found the following:

- **Pitch:** on Linux, we found no other agent sandbox whose seccomp filter and
  path rules are machine-checked (Kani and Verus) on the shipped code, with
  planted bugs that must fail the proofs on every CI run. This is the first
  "why" bullet. The fact-check added "on Linux", because the macOS Seatbelt
  policy has no proofs: a claim is narrowed to where its instrument reaches.
- **Pitch:** it refuses to start when it cannot enforce part of the profile, and
  prints what is not enforced. Another tool fails closed too, so this is the
  second bullet, without "only".
- **Status:** the macOS Endpoint Security client is planned. Seatbelt is a
  prototype, so the client is not a "why" bullet until it ships.
- **Vision:** confining an agent the same way on a developer Mac, a CI runner
  and a Raspberry Pi, from one typed profile.

## Anti-patterns

- **The caveat sprinkle:** scope honesty spread over every paragraph instead of
  one Status block.
- **Requirement IDs as prose.** They are for the trace, not for the reader.
- **An unchecked comparison**, or "the only" where "we found no other" is what
  the evidence supports.
- **A planned feature in the present tense.**
- **Deleting detail instead of moving it:** the long version still has to exist
  in `docs/`.
- **Writing another repo's README from the coordinator.** The repo's session
  owns it.

## Where this composes

- `claim-verification`: keeps every "why" bullet at the strength of its
  evidence.
- `publication-review`: the fact-check and editor passes.
- `pulseengine-prose-conventions`: sentence-level style.
- `outside-in-recheck`: when a comparison needs a fresh survey.
