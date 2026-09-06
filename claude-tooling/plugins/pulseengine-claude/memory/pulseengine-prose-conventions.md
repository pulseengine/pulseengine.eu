# PulseEngine prose conventions — how the text we write should read

Applies to commit messages, PR titles and bodies, issue and tracker text, and
blog posts. **Not** code comments, where density is usually earned.

Most of this text is written by agents. That is why the rules live here, in
always-on memory, and not in `CONTRIBUTING.md`. An agent does not read a human
style guide before writing a commit message.

## The rules

1. **Say what changed.** The title states the change. Reasoning goes in the body.
2. **At most one em-dash per paragraph.** Prefer a full stop. Two dashes in one
   paragraph is a rewrite, not a style choice.
3. **No reveal structure in titles.** Not "X looked correct. It was not." State
   the finding.
4. **Numbers and file paths instead of adjectives.** "57 of 60 runs cancelled"
   rather than "the gate is badly broken".
5. **Cut any sentence that exists for rhythm.** If removing it loses no
   information, remove it.
6. **A one-line paragraph is a beat, not a fact.** Use full paragraphs. This is
   the most common tell in our repos; see the measurement below.

## The tells

Ordered by how often they appear in PulseEngine repos:

1. Em-dash as the main connector, two or three per paragraph.
2. Reveal structure: a claim, then a reversal.
3. Trailing counts: "and eight more".
4. Not-X-but-Y: "This is not a packaging problem, it is a linking problem."
5. Triads where two items would be honest.
6. One-line paragraphs for emphasis, especially as a closer.
7. Stock closers: "That is the point."

## Measured, so the ranking is not a guess

13 commits and 10 merged PR bodies from this repo, 2026-08-19 to 2026-09-06,
all agent-written:

| tell | commit messages | PR bodies |
|---|---|---|
| em-dashes per paragraph | 0.43 | 0.56 |
| paragraphs with 2+ em-dashes | 8% | 12% |
| single-line "beat" paragraphs | — | **33%** |
| not-X-but-Y | 0 | 0 |
| trailing "and N more" | 0 | 0 |
| stock closers | 0 | 0 |

Two things this changes.

The rhetorical tells in the list above (3, 4, 7) did not appear at all in this
corpus. They are still worth naming, because they appear elsewhere in the org,
but they are not this author's problem.

The actual problem is tell 6. A third of PR-body paragraphs are single lines.
That is the habit to break first, and it is invisible without counting, which is
why rule 6 is stated as a rule rather than left in the tell list.

PR bodies are worse than commit messages on every measure. They are also the
text reviewers read. Weight effort accordingly.

## No linter

The tells are context-dependent and a checker would flag writing that is fine. A
written convention agents load, and reviewers can point at, is enough. The table
above can be re-derived when someone wants to know whether this is working.

See [[pulseengine-cli-conventions]] for the same treatment applied to tool
behaviour. Tracked as pulseengine.eu#179.
