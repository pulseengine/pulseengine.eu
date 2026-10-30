---
name: clean-room-verification
description: This skill should be used whenever findings, audits, code-review results or analysis output need validating before reporting, such as "verify this", "double-check this", "is this actually true" or "before I report this". Use it before claiming a property holds.
metadata:
  author: pulseengine.eu
  version: "0.4.1"
---

# Clean-room verification

**When to use:** before reporting audit or code-review results, before claiming a property holds, before we merge this, and whenever an agent's summary needs independent confirmation, or agent-produced hashes, digests, versions, file paths or flag names appear in a report.

## When this fires

Any time you're about to report findings from an investigation, audit, code review, or analysis — *especially* when those findings include claims about behavior, state, version pins, hashes, file paths, flag names, or "everything is green / done." Also fires when reviewing another agent's deliverable: a summary describes intent, not what landed.

This is the smithy ritual in PulseEngine vocabulary. The point is to catch hallucinations and over-claims before they ship.

## Procedure

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

## The independence record

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
- Its verdict cites the command it ran and the output it observed, per [`verify-your-own-claims`].

## The negative control: give the reviewer something it must refute

[`gate-potency`] proves a mechanical gate can still fail. The judgement gate needs the same check. **Periodically hand the reviewer a deliberately poisoned artifact or claim, and confirm it refutes it.** Good poisons are cheap and mechanical: a requirement whose cited test does not exist, a `verified` status with no verifying evidence, a claimed digest one character off. Mix the poison in with real claims and do not tell the reviewer it is there. A reviewer that confirms the poison is not a reviewer, and its earlier verdicts are suspect. Record the date the control was last exercised, and its outcome, beside the independence record, the way a fire alarm records its last test. Exercise it at least once per release whose gate rests on AI review.

## The rules baked in

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

## Anti-patterns

- Skipping verification because "the agent ran successfully." The agent's exit code is not evidence the claim is true.
- Re-using the verifier's *own* prior context to verify its findings. The whole point is clean-room.
- **Using a fork as the clean-room reviewer.** It inherits the author's context; its verdict is self-review.
- **"Independent review: present" with no record behind it.** Without the fields above nobody can tell which row of the table happened.
- **Marking a requirement `verified` on the strength of having implemented it.** Authorship and
  verification collapsing into one agent is the gap; a stronger mutation score does not fill it.
- Burying the verifier's verdict in a footnote. Lead with what was independently confirmed; the rest is suspected.
- Verifying with a soft oracle (asking an LLM to read the spec back). See [`oracle-gate-a-change`] — mechanical oracle preferred.

## Where this is referenced from

`oracle-gate-a-change` and `pulseengine-feature-loop` both point here for their verify step; `release-execution`'s independence gate and `publication-review`'s reviewers point here for the fork rule and the independence record; [`refactor-decision`], which checks its own scope first (not in pulseengine/rivet or pulseengine/spar before 2027-02-01), points here before a refactor is reported as behaviour-preserving. The pattern is single-source-of-truth here; if you're inlining the procedure elsewhere, you're duplicating a known dependency.
