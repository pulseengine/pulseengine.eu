---
name: publication-review
description: This skill should be used before a blog post or any other public, claim-heavy prose goes live — before adding `ready = true` to a post, before setting `draft = false`, before publishing a README section, landing page, talk abstract or announcement that quotes sources, cites standards, prints tool output or states numbers. Use it when the user says "is this post ready", "review this before it ships", "schedule this", "fact-check the draft", or when the text was drafted by a model. It gates publication on a role-split clean-room panel — a domain expert, a fact-checker who fetches primaries and re-derives repo numbers with the pinned tool version, and an editor holding the house prose rules — then a fixer that applies only confirmed findings, then a fresh second round. Any refuted quote, number or citation, any overclaim about verification or proof, and any private infrastructure detail blocks publication. Composes with clean-room-verification and claim-verification.
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# Publication review: a role-split panel before public prose ships

## When this fires

Before `ready = true` goes onto a post in `content/blog/`, and before `draft = false` on one
published by hand. Also before any other public page that makes claims a reader will repeat: a
README section, the landing page, a talk abstract, an announcement. The trigger is the content,
not the file type. If the text quotes a source, cites a standard or a book, prints CLI output,
states a number, or says what a PulseEngine tool verifies or proves, it goes through the panel.
Text drafted by a model goes through it regardless.

## Why this exists, measured

Between 2026-10-25 and 2026-10-27 four posts drafted with another model were published or
scheduled with these defects, none of which any build gate could see: a quotation carrying an
invented clause, and that clause was the post's thesis; CLI output that no tool run had produced;
citations with the wrong author names and a book that does not exist; arithmetic that did not add
up; numbers presented as measured that were assumptions; and ASPICE process IDs cited wrongly.
`zola build`, the link checks and `claim-check.py` were green throughout, because a well-formed
false sentence is not a build error.

A panel found and fixed all of it: a domain expert, a fact-checker and an editor, each briefed
cold, then a fixer applying the confirmed findings, then a second round. This skill is that
procedure, written down so the next post gets it before publication instead of after.

## The panel

Run each reviewer as its own subagent with a fresh context. One reviewer holding all three roles
does none of them well: the fact-checker's job is to distrust the text, and the editor's is to
improve it.

| role | checks | evidence it must return |
|---|---|---|
| **domain expert** (pick per post: an ASPICE assessor, a PulseEngine architect, a safety assessor, a Wasm runtime engineer) | the technical claims are right and stated at the strength the evidence supports; standard and process IDs are the real ones (ASPICE `SWE.4`, ISO 26262 part and clause); PulseEngine terminology per `CLAUDE.md` (synth *transcodes*, kiln is an *interpreter and runtime*, lowercase names, everything work in progress) | the clause, ID or file it checked against |
| **fact-checker** | every quotation word for word against the primary; every citation's author, title, year and publisher; every number that comes from a repo re-derived by running the command with the tool version the post names; every printed CLI output reproduced; every sum, ratio and percentage recomputed | the URL it fetched or the command it ran, with `<tool> --version` |
| **editor** | the house prose rules in `pulseengine-prose-conventions` (one em-dash per paragraph, no reveal structure, no one-line beat paragraphs, numbers instead of adjectives); crispness; the claim a reader will repeat is stated once and plainly | the paragraph and the rule |

The fact-checker fetches primaries. A quotation checked against a secondary source, a search
snippet or the model's memory is unchecked. A repo number re-derived with a different tool version
than the post names is a different measurement, for the reason in
[`clean-room-verification`] step 3: the same tree can pass under one rivet and fail under another.

## Briefing the reviewers cold

The brief is the procedure in [`clean-room-verification`], specialised for prose:

- **Give files and rules, not reasoning.** Each reviewer gets the post path, any co-located
  images, the role's row from the table above, and the rule files it applies. It does not get the
  author's notes, the drafting conversation, or why the post argues what it argues. A reviewer
  who knows the intent reads the intent back out of the text.
- **"cannot-verify beats a guess."** Say it in the brief, in those words. Each finding is
  `confirm`, `refute` or `cannot-verify`, with the evidence column filled. A primary that is
  paywalled or offline is a `cannot-verify`, never a `confirm` from memory.
- **One finding per claim, quoted.** Location, the exact sentence, the verdict, the evidence and a
  proposed fix. Vague findings ("the tone is off in places") cannot be applied or checked.
- **No edits.** Reviewers report; they do not change the file. Otherwise the second round has
  nothing stable to review.

## The fixer round

A separate fixer agent applies the findings. It receives the post and the findings list, nothing
else, and follows three rules.

1. Apply every `refute` that carries evidence, using the evidence, not the reviewer's prose.
2. A `cannot-verify` claim is cut, or softened to what the evidence supports, and marked as such
   ("assumed", "estimated", "not measured"). It is never left at its original strength.
3. Add no new claims. A fix that needs a new number, quote or citation goes back to the
   fact-checker before it lands.

Editor findings are applied only where they do not change a checked claim's meaning. When style
and accuracy conflict, accuracy wins and the sentence is rewritten until both hold.

## The second round

Fresh reviewers, new contexts, the same three roles. They get the revised file and the list of
changed locations (line ranges only, not the findings or the reasons), and review the whole post,
not only the diff. Fixes introduce errors: a softened number that no longer matches the chart, a
corrected quote whose citation now points at the wrong edition.

**Stop rule.** Stop when a round returns no blocking finding (the list below). If round two still
has blockers, run the fixer and a third round. If round three still has blockers, stop: keep the
post held, and hand the user the open findings with their evidence. Do not loop a fourth time;
three rounds that cannot converge mean the post's argument needs its author, not another pass.

## What blocks publication

A post does not get `ready = true`, and a page is not published, while any of these is open:

- **Any refuted quote, number or citation blocks publication.** One is enough, whatever the rest
  of the post is worth.
- **Any overclaim about verification or proof blocks publication.** "Verified", "proven",
  "sound", "formally verified" must be scoped to what a machine-checked result covers. The
  phrasing is held by [`claim-verification`]; a claim that should stay true after publication
  belongs in `claims.yaml`, not only in this review.
- **Any private infrastructure detail blocks publication.** Hostnames, internal IPs, mDNS names,
  certificate paths, runner names, and anything the plugin keeps in environment variables.
- **Any `cannot-verify` still stated at full strength blocks publication.** Soften it or cut it.

Editor findings alone do not block. A post with a dash too many may ship; a post with an invented
clause may not.

## The autopublish hold detail

`scripts/blog-autopublish.py` reads the frontmatter with line-anchored regexes, so **`hold = true`
must be on its own line.** `HOLD_RE` is `^hold\s*=\s*(true|false)\s*$`. A trailing comment
(`hold = true  # until review`) does not match, the hold is not seen, and a post that also has
`ready = true` publishes on its date. Put the reason on the line above. The same anchoring makes
a commented `ready` line read as absent, which fails safe (the post stays held). Check the result
with `python3 scripts/blog-autopublish.py --mode scan` and confirm the post lands in the bucket
you meant.

While the panel runs, the post stays `draft = true` with no `ready`, or with `hold = true` on its
own line. `ready = true` is added last, after the final round clears.

## Anti-patterns

- **Reviewing your own draft.** The author's context is the one that produced the invented clause.
- **Briefing reviewers with the thesis.** They will confirm it.
- **A fact-checker that searches instead of fetching.** A snippet is a secondary source.
- **Re-deriving a repo number with whatever rivet is on `PATH`.** Use the pinned version the post
  names, and record it next to the verdict.
- **Merging the fixer and a reviewer into one agent.** The second round needs a fixer it did not
  write.
- **Publishing on round one's green.** The second round exists because fixes introduce errors.

## Where this composes

[`clean-room-verification`] holds the cold-verifier procedure this specialises;
[`claim-verification`] gates the claims that must stay true after publication;
[`verify-your-own-claims`] covers the assertions in the PR body that ships the post. The prose
rules are `pulseengine-prose-conventions`; the publishing states are in `CONTRIBUTING.md`.
