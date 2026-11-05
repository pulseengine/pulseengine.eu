---
name: claim-verification
description: Use before a claim is reported or written, such as findings, audit results, PR or issue text, "0 found", "all green", "because", "verify this", an AI review used as evidence, or a README, badge or doc asserting what the system proves.
metadata:
  author: pulseengine.eu
  version: "1.0.0"
---

# Claim verification: is it true, and does it stay true?

**When to use:** before a claim leaves your head or lands in a document. Three situations, one question (what is the evidence, and what is the evidence blind to?):

| You are about to | Go to |
|---|---|
| say, report or post an assertion: findings, an audit result, a PR body or issue comment, a claim that generalizes ("only X and Y do Z", "all of them pass"), asserts a cause or a negative, or reports a measurement as clean ("0 found", "all green"), especially one resting on a grep, search or script you just wrote | Part 1, the five checks |
| validate findings, code-review results, audits or an agent's summary before reporting ("verify this", "double-check this", "is this actually true", "before we merge this"), or an agent-produced hash, digest, version, path or flag name appears in a report; or record an AI review as evidence | Part 2, the clean-room review |
| write or edit a README, badge, project description, blog claim, honesty ledger or dossier that asserts what the system does, is or proves ("formally verified", "verified N/N", trusted-base counts); audit a doc whose claims may have drifted; stand up the claim-check gate in a repo | Part 3, mark, bind, gate |

The parts stack. A sentence in a PR body has no build to fail, so Part 1 is a procedure you run. A claim that survives Part 1 and is still consequential goes cold to a fresh reviewer (Part 2), the expensive pass. A claim that must stay true after you have written it goes into the gate (Part 3). The other half of verification, whether the checks behind a claim can fail and are about the right system, is [`gate-potency`].

## Part 1: assertions you emit (conversation, PR body, issue comment, audit result)

The operating contract already says: ground every progress claim in a tool
result. That rule catches the model that reports work it never did.

**It does not catch this.** Every failure below *had* a tool result behind it.
The claim was grounded — and still wrong, because the claim reached further
than the instrument could see.

> **The one principle.** A tool result behind a claim is **necessary, not
> sufficient.** The claim must not exceed what the instrument can measure. So
> before asserting, name the instrument, and name what it is blind to.

This is [`oracle-gate-a-change`]'s red-first discipline turned on your own
sentences, and it is [`gate-potency`]'s question — *can this check fail?* —
asked about the check you just ran on yourself.

### Why this is a real class, not a hypothetical

Five instances, one session, same author, all with evidence in hand:

| the instrument | the claim | what it could not see |
|---|---|---|
| `grep 'z3::\|use z3\|Z3_\|z3_sys'` over `.rs` + Cargo deps | *"Only loom and synth link Z3."* | Z3 as a **subprocess** and as a **Bazel toolchain** — so gale, relay and rules_verus, the largest un-certificate-checked Z3 surface in the org, were invisible |
| a link checker matching `href="([^"]+)"` | *"0 dead links."* | **Zero links.** The output is minified and emits unquoted `href=/docs/`. Six were dead, four on a nav-linked page |
| `gh run list` conclusions | *"cancelled by dependabot storms + cancel-in-progress."* | The **cause**. The concurrency group was per-branch; the durations sitting in the same output showed a 30-minute timeout |
| *(no probe ran)* | *"gale: cross-check none."* | Everything. An asserted **negative** with no instrument behind it at all |
| `--version` / exit-code conformance | *"these tools are fine"* (so they went unexercised) | **Behaviour.** The two most severe defects of the survey were in tools that passed every convention cleanly |

Note what is *not* in that table: a single instance of reporting work that was
never done. The contract's rule was satisfied every time.

### The five checks

Run these against the claim you are about to make. Each one is named after the
instance it would have caught.

#### 1. Does the instrument have a zero-case that looks like success?

A checker that matched nothing prints the same triumphant `0 problems` as a
checker that matched everything and found nothing wrong. **Print the
denominator, and fail on zero.**

```
75 pages, 94 internal links checked, 0 dead     <- evidence
0 dead links                                    <- not evidence
```

If a count of *things examined* cannot be produced, the result is not a
measurement. This is [`gate-potency`]'s vacuity check applied to a one-off
script.

#### 2. What shape of the thing would this probe be blind to?

Before generalizing from a search, enumerate the forms the target can take, and
confirm the pattern covers each. A dependency can arrive as a linked crate, a
spawned binary, a build-system toolchain, a vendored source tree, a container
image. One grep sees one form.

State the scope you actually searched — *"no crate links Z3"* is defensible;
*"nothing uses Z3"* is not, from the same grep.

#### 3. Is this a cause, or a correlation the data also permits?

Reporting *what happened* needs the observation. Reporting **why** needs the
alternatives ruled out. Before writing "because", ask what else predicts the
same data, and check whether the answer is already in the output you have —
it usually is.

#### 4. Did I probe every member of the population I am generalizing over?

A table with a row per repo asserts a result per repo. If one row was never
probed, it does not get a value — it gets **"unprobed"**. An absent instrument
never produces a negative finding; it produces no finding.

The tell: you are about to write a confident cell for something you have not
run a command against.

#### 5. Is the instrument valid in the environment where it just ran?

Checks 1 to 4 all assume the instrument ran. An instrument can be correct where
you wrote it and inert where it executed, and then its output — green, red or
silent — is not a measurement at all. **Name the environment, not just the
instrument.**

This is the one that produces false ALARM as readily as false confidence. The
other four guard against over-claiming; this one also catches hours spent fixing
something that was never broken.

Measured, one session, six instances:

| the instrument | where it was valid | where it ran | what it reported |
|---|---|---|---|
| `gh api` in a freshness check | a laptop with the CLI | a self-hosted runner without it | `0 projects checked`, exit 0 — read as "nothing is stale" |
| `requestAnimationFrame` timing | a visible tab | a backgrounded tab, where rAF never fires | a timeout — read as "the renderer is frozen" |
| `rivet coverage --tests` | a tree with `src/`, `tests/` | a repo whose scripts live in `scripts/` | `0/9 (0.0%)` — read as "the markers do not work" |
| `env!("CARGO_BIN_NAME")` | `cargo build` | `rules_rust` under Bazel | compiled locally, failed the real build |
| `zola check --skip-external-links` | Zola `@/path.md` links | content using raw absolute hrefs | exit 0 with a dead link present |
| a CSS transition's computed value | a painting tab | a hidden tab, where transitions do not advance | `opacity: 0` — read as "the rule is not applying" |

Three of those six were false alarms, and two cost a detour before the
instrument itself was questioned.

The tell: **you are about to report a number you did not watch the instrument
produce in this environment.** A zero, a timeout, and a silence all look the
same from a tool that is not running.

The move is cheap: run the instrument against something you *know* it should
find, in the same environment. If the positive control also comes back empty,
the instrument is the finding.

```sh
# before trusting "0 dead links" from CI, make CI find one
# before trusting "no markers", point the scanner at a file you just marked
# before concluding "frozen", check document.visibilityState
```

### Then: separate what you measured from what you concluded

In the report itself, keep them visibly apart. The measurement is durable and
someone else can re-run it; the conclusion is yours and may be wrong.

```
Measured:   57 cancelled, 3 failure, 0 success across 60 runs (2026-07-15 → 08-25);
            durations 30.4–102.5 min against timeout-minutes: 30
Concluded:  the job cannot finish inside its budget
```

Anyone can falsify the second line without re-deriving the first. That is the
property worth having, and it is the same reason a rivet artifact separates the
requirement from its verifying evidence.

### Anti-patterns

- **Treating "I ran a tool" as the end of the check.** It is the beginning. The
  contract's rule is the floor, not the ceiling — this skill exists because five
  claims cleared that floor and were still wrong.
- **Conformance as a proxy for correctness.** Passing a convention audit says a
  tool meets the convention. It says nothing about whether the tool works. Both
  of the worst defects in one survey were in tools with impeccable `--version`.
- **A confident cell for an unprobed row.** Fill it with *unprobed*, or delete
  the row. Do not let table symmetry manufacture a finding.
- **Rewriting the claim smaller after being challenged, without saying so.**
  If the scope was wrong, correct it plainly once and move on — see the
  operating contract on corrections.
- **Running this on trivia.** It is for load-bearing claims: ones that route
  work, close an issue, or land in a PR body someone will act on. Not for "the
  file is at `src/main.rs`."

## Part 2: independent review before reporting (the clean-room ritual)

### When this fires

Any time you're about to report findings from an investigation, audit, code review, or analysis — *especially* when those findings include claims about behavior, state, version pins, hashes, file paths, flag names, or "everything is green / done." Also fires when reviewing another agent's deliverable: a summary describes intent, not what landed.

This is the smithy ritual in PulseEngine vocabulary. The point is to catch hallucinations and over-claims before they ship.

### Procedure

1. **Write the findings as discrete falsifiable claims.** Each one should be specific enough that an independent checker can confirm, refute, or say "cannot verify." Examples of good claims:
   - "Function `foo::bar` in `crates/foo/src/lib.rs` returns `Result<(), Error>` and propagates errors via `?`."
   - "The image `docker.io/nixos/nix@sha256:abcdef...` is pullable from a fresh client."
   - "`rivet check` on this branch reports zero unsatisfied predicates."
   - "All four Kani harnesses in `wohl-ota` pass with `cargo kani`."

   Avoid vague claims like "the refactor is clean" or "tests pass" — those aren't checkable.

2. **Spawn a clean-room verification subagent.** Brief it cold — no inherited framing, no access to the original reasoning, no narrative about why the work was done. Give it only:
   - The list of falsifiable claims.
   - Whatever read/exec tools it needs to confirm them (Read, Grep, Bash).
   - An explicit instruction: "Return one of `confirm`, `refute`, or `cannot-verify` per claim. Do not guess. `cannot-verify` is a valid and preferred answer over a guess."

   **A clean-room reviewer is a fresh agent. A fork is the author.** In Claude Code, `subagent_type: "fork"` inherits the parent's full conversation context, so its verdict is the author reviewing itself, in the shape of an independent review. Spawn the reviewer with no `subagent_type`, or `general-purpose` / `Explore`, which start fresh. `fork` is the natural reach when you want the reviewer to "know what we're doing", which is the framing this step exists to keep out.

3. **Treat agent-produced artifacts as unverified claims.** Hashes, digests, version pins, file paths, flag names, symbol names — even when produced by a tool that *should* be authoritative — count as claims until checked against the real artifact. The verifier should pull the image, grep the binary, read the file, run the command.

   **Including the version of the verifier itself** — the one nobody checks. A tool's own build is
   as much a claim as anything it reports, and it decides what the report *can* say: an older binary
   may not implement the rule you are relying on, or may flag a type it simply does not know. Record
   `<tool> --version` (or `varve which <tool>` for the layer + digest) next to the verdict, and note
   whether it matches CI. Measured: `rivet validate` on one unchanged tree returns **FAIL (exit 1)**
   under 0.19.0 and **PASS (exit 0)** under 0.32.0. A verdict quoted without its binary is not
   reproducible, and therefore not evidence.

4. **Reconcile.** Compare the verifier's confirm/refute/cannot-verify against your draft findings:
   - `refute` → the claim is wrong; rewrite or drop it.
   - `cannot-verify` → either add the evidence the verifier needs, or downgrade the claim to "this is suspected, not verified."
   - `confirm` → the claim ships as-is.

5. **Report.** Include the verifier's verdict alongside the claim, so the reader can see what was independently checked vs. what was asserted.

### The independence record

For a human reviewer, identity does the work: B is not A. For an AI reviewer, identity is a label, and four situations report alike as "independent review performed":

| Reviewer | Independent? |
|---|---|
| different model (`model:` on a fresh agent), fresh context | yes, the strongest available without a second human |
| same model, fresh context | weakly: shared weights, no shared framing |
| same model, inherited context (a fork) | no, this is the author |
| same session, a later turn | no |

Only a record tells them apart. **Record these fields for every review used as evidence: reviewer model, inherited context (yes/no), reviewer run id, reviewed commit SHA, date, outcome.** The run id must differ from the author's session. A review missing any field is unrecorded, not independent, and a release gate counts it as absent. `inherited context: yes` is an authored review whatever the other fields say.

When the reviewer is an AI added to a PR as a cloud reviewer:

- It does not commit into the branch under review. A contributor to a change cannot independently approve it, and on the PR author's own account GitHub refuses the approval outright. Reviewer-authored fixes go in a separate PR.
- Its record names the model, not a generic `ai-assisted` label. Two agents of the same model are not two reviewers.
- Its verdict cites the command it ran and the output it observed, per Part 1.

### The negative control: give the reviewer something it must refute

[`gate-potency`] proves a mechanical gate can still fail. The judgement gate needs the same check. **Periodically hand the reviewer a deliberately poisoned artifact or claim, and confirm it refutes it.** Good poisons are cheap and mechanical: a requirement whose cited test does not exist, a `verified` status with no verifying evidence, a claimed digest one character off. Mix the poison in with real claims and do not tell the reviewer it is there. A reviewer that confirms the poison is not a reviewer, and its earlier verdicts are suspect. Record the date the control was last exercised, and its outcome, beside the independence record, the way a fire alarm records its last test. Exercise it at least once per release whose gate rests on AI review.

### The rules baked in

- **The verifier may say "cannot verify" rather than guess.** A "cannot verify" with evidence beats a guess with confidence.
- **An agent's summary describes intent, not what landed.** Check the diff. Check the file. Check the symbol. Check the digest.
- **"It passed CI" is a statement about the gate's coverage that day, not a timeless guarantee.** Re-verify on the current artifact, not on the historical green check.
- **Evidence-backed "blocked" beats forced "done."** If verification surfaces a real blocker, report the blocker — that's the honest path the user explicitly prefers.
- **In a solo-agent-authored repo, this stops being on-demand and becomes a release gate.** Automation
  can close almost every gap in such a repo except one: **the authoring agent assigning itself
  `verified` status.** No mutation score, coverage number or green board closes that — it is a
  structural independence gap, and it is the finding that repeated audits keep returning. The
  standing expectation: a release's scope gets a fresh-context reviewer who re-derives every claimed
  verdict from evidence (runs the named tests, re-checks the oracles, attempts to refute), with
  **reviewer identity, date and outcome recorded on the artifacts** — and the release gate refuses a
  scope whose independent review is absent or dissenting. Canonical statement: varve's
  `REQ-INDEP-001`, *"No requirement is verified on the author's word alone"* (approved, v0.14.0).
  This is the strongest independence achievable without a second human; treat it as the default for
  any repo where one agent both writes and blesses the work.

### Anti-patterns

- Skipping verification because "the agent ran successfully." The agent's exit code is not evidence the claim is true.
- Re-using the verifier's *own* prior context to verify its findings. The whole point is clean-room.
- **Using a fork as the clean-room reviewer.** It inherits the author's context; its verdict is self-review.
- **"Independent review: present" with no record behind it.** Without the fields above nobody can tell which row of the table happened.
- **Marking a requirement `verified` on the strength of having implemented it.** Authorship and
  verification collapsing into one agent is the gap; a stronger mutation score does not fill it.
- Burying the verifier's verdict in a footnote. Lead with what was independently confirmed; the rest is suspected.
- Verifying with a soft oracle (asking an LLM to read the spec back). See [`oracle-gate-a-change`] — mechanical oracle preferred.

### Where this is referenced from

`oracle-gate-a-change` and `pulseengine-feature-loop` both point here for their verify step; `release-execution`'s independence gate and `publication-review`'s reviewers point here for the fork rule and the independence record; [`refactor-decision`], which checks its own scope first (not in pulseengine/rivet or pulseengine/spar before 2027-02-01), points here before a refactor is reported as behaviour-preserving. The pattern is single-source-of-truth here; if you're inlining the procedure elsewhere, you're duplicating a known dependency.

## Part 3: documents, mark then bind then gate

A README is not documentation — it is a **claim about the system**, the same
species as a requirement, pointing the other way. A requirement says what the
system *shall do*; a README says what it *does and is*. Both are assertions that
must stay true, and both rot for the identical reason: a requirement stays honest
because it's a typed artifact with a `verifies` link and `rivet validate` fails the
build the moment the evidence disappears — a README claim has none of that, so it's
a requirement with the safety mechanism removed.

> **The one principle.** Truth-over-time is a property of the **gate**, not the
> author. You do not make a document honest by writing it honestly once; you make it
> honest by making *dishonesty fail the build*. Docs rot because they're the one
> claim you don't gate.

This is oracle-gating ([`oracle-gate-a-change`]) turned on your own prose. It is the
mechanical answer to "how do you keep your public claims honest as the code moves?" —
*your claims are traced artifacts; when the evidence moves, the claim fails on every
commit.*

### The three moves: mark → bind → gate

1. **Mark the load-bearing claims** — a `claims.yaml` sidecar (or `<!-- claim … -->`
   markers) pins each *assertion* to (a) the verbatim string as it appears in the
   doc, (b) checkable evidence, (c) the honest wording. **Mark the claims, not the
   narrative** (see the boundary below).
2. **Bind each claim to evidence a machine can re-derive** — never a number typed in
   prose (it goes stale the day the code changes). Evidence is a predicate:
   - `file-exists` — the proof/harness the claim rests on is present.
   - `count-max` — an *upper bound*: re-count `external_body` / `admit` / `sorry` /
     `assume` from the *actual source*; fail if it exceeds the recorded trusted-base
     size. Use it only for growth claims — it greens a 0-match (`0 > max` is false),
     so it must **not** gate a presence claim.
   - `count-min` — the *presence* dual: fail when the pattern appears *fewer* than
     `min` times. Use for must-exist claims (a version string, a required proof
     marker) — it catches drift-to-absent, which `count-max` silently passes.
   - `no-new` — no new `sorry`/`admit` since the ledger's recorded count.
   - `set-equal` — two artifacts that must agree, checked as a pair: a set of names from
     paths on disk against a set listed in a doc (optionally between two headings), in
     **both** directions. Either side yielding nothing **fails**, so "0 mismatches" can
     never mean "nothing compared". `waive:` lists existing debt, printed on every run.
   - `count-equals` — a number stated in prose against the size of a set on disk. The
     plugin README said 18 skills against 19 for weeks while a roster check that read the
     same file passed, because it checked the bullets, not the number.
   - `verbatim` — the README badge or tagline matches the ledger's honest
     wording exactly (a badge can't say "Formally Verified" while the ledger says
     "133 external_body + 74 admitted").
3. **Gate it** — `claim-check` runs in CI, re-derives every predicate, and diffs the
   doc against the ledger. Drift = red. This is the exact shape the org already runs
   (ordeal's `regen.sh` freshness gate guarding `Kernel.lean` against `kernel.rs`;
   gale's `verification-honesty.md` ledger). A reference implementation ships next to
   this skill: `claim-check.py` + `claims.example.yaml`.

4. **Name the epoch — what expires this claim even while its evidence still passes.**
   A claim's validity is bounded in time and context, so record the condition that
   should force re-validation: the model generation it was measured on, the layer
   that can no longer be re-derived, the tool version, the standard's revision. Then
   give it a **proof surface** — something that *notices* the condition changed. The
   first three moves catch a doc drifting from its evidence; this one catches the
   evidence drifting out from under a claim that still greens.

   Field case, 2026-10-14: the operating contract's routing rule carried the epoch
   in prose ("no model versions — this file named two that were superseded") and the
   gate bound only the sentence. Editing the rule tripped the gate on wording while
   the *claim* had silently narrowed — the string was checked, the scope was not. The
   fix was to gate the narrower claim (no version-pinned name reached by a routing
   verb; the tier table in exactly one place), which then immediately found a stale
   version pinned in a second document. An epoch with no proof surface is a comment.

   This is DO-330's requalification-trigger idea applied to prose, and it has a name
   in the literature now: **epoch limits** and **proof surfaces**, from *Fifty Years
   of Specification Completeness* (arXiv:2606.25120), which maps DO-178C traceability
   and DO-330 triggers onto AI governance documents — system prompts, `AGENTS.md`,
   policies — and finds 37% of them below a structural-quality threshold, with no
   standards body requiring these properties of a governance document at all. Use
   their vocabulary when explaining this to a certification audience; it converts
   "we have a claim gate" into a term they already hold.

### The discipline (the prose half — derived empirically across the repos)

- **Never flatten the techniques.** Verus (SMT, partial-correctness, declared trusted
  base) · Kani (**bounded** model checking) · Rocq (theorem proving, but
  coq-of-rust translation is trusted) · translation-validation (per-run, not the tool)
  · Lean (specific theorems). "Formally verified" as a flat badge is the claim to kill
  — it's what a formal-methods reviewer distrusts on sight.
- **The badge *is* the evidence.** A green "Formally Verified" badge must be a claim
  artifact whose evidence check passes. If it can't be backed, relabel it to what's
  true (loom: `Formally Verified` → `Translation-Validated (Z3)`).
- **Name the trusted base — and re-derive it, don't type it.** gale's ledger enumerates
  133 `external_body` + 2 `assume_specification`; that number must be a `count-max`
  predicate, not a hand-written figure that drifts (synth's Qed/Admitted counts already
  disagree across three files precisely because they're hand-maintained).
- **Single-source shared claims.** The org tagline ("formally verified WebAssembly
  toolchain") copy-pasted into every README is the drift source. Define it once,
  reference it — the plugin's own single-source rule.
- **Scope to what's proven, not the whole thing.** relay: "formally verified flight
  software" → "formal proofs of *specific* safety properties (Kani + Lean)".

### The boundary — gate the claims, NOT the narrative

A document is claims + motivation + examples. Only the **claims** must be
true-for-a-long-time. If you try to formalize the prose, docs become brittle and no
one writes them. Mark the *assertions* (verification status, capabilities, "proven X",
"sound Y", the numbers); leave the story, the rationale, and the examples free. This is
the same split you already live — rivet gates the requirement, not the design rationale
around it.

### How it plugs into rivet (the durable end-state)

The sidecar is the pragmatic gate today. The end-state is to make each marked claim a
first-class **rivet artifact** (`type: claim`) with a `verifies` link to its evidence
artifact, so `rivet validate` covers your prose the way it covers requirements — the
README claim joins the same V-model, on the same gate. Until the `claim` type lands in
the rivet schema, `claim-check` is the standalone gate that enforces the same property.

### Anti-patterns

- **An unbacked badge / a claim with no evidence link.** The single failure this skill
  exists to kill — a green claim nothing gates.
- **A count typed in prose instead of re-derived.** It is stale the next commit; make
  it a `count-max` predicate over the actual source.
- **Flattening distinct techniques into "formally verified."** The overclaim a
  reviewer pounces on.
- **Formalizing the narrative.** Gating motivation/examples makes docs unwritable —
  mark assertions only.
- **Copy-pasting a shared claim** (the org tagline) into every repo where it drifts —
  single-source it.
- **"Fixing" a red claim-check by softening the *ledger* instead of the claim** — when
  the evidence genuinely weakened, the honest move is to change the public claim, not
  to loosen what the ledger demands.

## Where this composes

- [`gate-potency`]: the other half. A claim bound to a check that cannot fail, or filed on the wrong machine, is
  an unbacked claim; check 1 of Part 1 is its vacuity audit applied to a script you wrote five minutes ago.
- [`traceability-audit`]: requirements to tests to evidence; Part 3 is the same discipline for
  *public claims* to evidence. Both are "a claim is only trustworthy bound to evidence and gated."
- [`oracle-gate-a-change`]: `claim-check` is the mechanical oracle; the diff that flips it green is the
  honest doc. Part 2 prefers a mechanical oracle to a soft one.
- [`proof-synthesis`]: its honesty ledger and trusted-base numbers are the *evidence* the claims in Part 3
  bind to; keep the two in sync (the ledger is the single source).
- [`report-tool-friction`]: an instrument that cannot see a whole shape of the thing it searches, or a gate that
  cannot re-derive a predicate, is a *tool* gap worth filing, not a licence to hand-wave the claim.
- [`pulseengine-operating-contract`]: *"Ground every progress claim in a tool result"* is the always-on floor
  Part 1 builds on.
