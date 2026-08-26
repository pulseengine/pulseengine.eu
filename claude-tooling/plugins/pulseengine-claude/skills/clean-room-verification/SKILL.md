---
name: clean-room-verification
description: This skill should be used whenever findings, audits, code-review results, claims, or analysis output need to be validated before reporting — including "verify this", "double-check this", "audit", "is this actually true", "before I report this", "before we merge this", or whenever an agent's summary needs independent confirmation. ALWAYS use this skill before delivering non-trivial inspection results, before claiming a property holds, and whenever agent-produced hashes, digests, versions, file paths, or flag names appear in a report.
metadata:
  author: pulseengine.eu
  version: "0.3.0"
---

# Clean-room verification

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
- **Marking a requirement `verified` on the strength of having implemented it.** Authorship and
  verification collapsing into one agent is the gap; a stronger mutation score does not fill it.
- Burying the verifier's verdict in a footnote. Lead with what was independently confirmed; the rest is suspected.
- Verifying with a soft oracle (asking an LLM to read the spec back). See [`oracle-gate-a-change`] — mechanical oracle preferred.

## Where this is referenced from

`oracle-gate-a-change` and `pulseengine-feature-loop` both point here for their verify step. The pattern is single-source-of-truth here; if you're inlining the procedure elsewhere, you're duplicating a known dependency.
