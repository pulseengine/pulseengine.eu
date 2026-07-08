---
name: claim-verification
description: This skill should be used whenever writing or editing a README, a badge, a project description, a blog claim, an honesty ledger, a dossier, or ANY document that asserts what the system does, is, or proves — especially verification claims ("formally verified", "proven", "sound", "verified N/N", trusted-base counts). It treats a document's load-bearing claims as requirements that must stay true over time: mark the assertion, bind it to checkable evidence, and gate it so drift fails the build. Use it to author an honest claim, to audit a doc whose claims may have drifted from reality, or to stand up the claim-check gate in a repo. Composes with traceability-audit (requirements↔tests), oracle-gate-a-change (the gate), and clean-room-verification (review the claim cold).
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# Claim verification

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

## The three moves: mark → bind → gate

1. **Mark the load-bearing claims** — a `claims.yaml` sidecar (or `<!-- claim … -->`
   markers) pins each *assertion* to (a) the verbatim string as it appears in the
   doc, (b) checkable evidence, (c) the honest wording. **Mark the claims, not the
   narrative** (see the boundary below).
2. **Bind each claim to evidence a machine can re-derive** — never a number typed in
   prose (it goes stale the day the code changes). Evidence is a predicate:
   - `file-exists` — the proof/harness the claim rests on is present.
   - `count-max` — re-count `external_body` / `admit` / `sorry` / `assume` from the
     *actual source*; fail if it exceeds the recorded trusted-base size.
   - `no-new` — no new `sorry`/`admit` since the ledger's recorded count.
   - `badge` / `verbatim` — the README badge/tagline matches the ledger's honest
     wording exactly (a badge can't say "Formally Verified" while the ledger says
     "133 external_body + 74 admitted").
3. **Gate it** — `claim-check` runs in CI, re-derives every predicate, and diffs the
   doc against the ledger. Drift = red. This is the exact shape the org already runs
   (ordeal's `regen.sh` freshness gate guarding `Kernel.lean` against `kernel.rs`;
   gale's `verification-honesty.md` ledger). A reference implementation ships next to
   this skill: `claim-check.py` + `claims.example.yaml`.

## The discipline (the prose half — derived empirically across the repos)

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

## The boundary — gate the claims, NOT the narrative

A document is claims + motivation + examples. Only the **claims** must be
true-for-a-long-time. If you try to formalize the prose, docs become brittle and no
one writes them. Mark the *assertions* (verification status, capabilities, "proven X",
"sound Y", the numbers); leave the story, the rationale, and the examples free. This is
the same split you already live — rivet gates the requirement, not the design rationale
around it.

## How it plugs into rivet (the durable end-state)

The sidecar is the pragmatic gate today. The end-state is to make each marked claim a
first-class **rivet artifact** (`type: claim`) with a `verifies` link to its evidence
artifact, so `rivet validate` covers your prose the way it covers requirements — the
README claim joins the same V-model, on the same gate. Until the `claim` type lands in
the rivet schema, `claim-check` is the standalone gate that enforces the same property.

## Anti-patterns

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

- [`traceability-audit`] — requirements↔tests↔evidence; this is the same discipline for
  *public claims*↔evidence. Both are "a claim is only trustworthy bound to evidence and
  gated."
- [`oracle-gate-a-change`] — `claim-check` is the mechanical oracle; the diff that flips
  it green is the honest doc.
- [`clean-room-verification`] — review a load-bearing claim cold ("is this actually
  true and does the evidence support it?") before it ships, especially before a public
  post.
- [`proof-synthesis`] — its honesty ledger + trusted-base numbers are the *evidence*
  the claims here bind to; keep the two in sync (the ledger is the single source).
- [`report-tool-friction`] — if the gate can't re-derive a predicate, that's a tooling
  gap, not a licence to hand-wave the claim.
