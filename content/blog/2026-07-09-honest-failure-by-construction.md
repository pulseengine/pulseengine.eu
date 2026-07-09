+++
title = "Jagged by nature, honest by construction: a state-of-the-art prover meets two real proofs"
description = "We pointed Leanstral 1.5 — Mistral's open-weights Lean prover, which its makers report scores 100% on the standard math benchmark — at two of our real proofs: the soundness of an SMT-certificate checker, and a suite of scheduling-theory lemmas. On one it couldn't converge; on the other it succeeded cleanly and even found a proof path we hadn't. In neither case, across any trial, did it produce a wrong proof the checker accepted. The value of an AI prover in safety-critical work isn't that it closes your proofs — it's that the architecture makes both its wins and its failures safe."
date = 2026-07-09
draft = false
ready = true
[taxonomies]
tags = ["verification", "ai-agents", "lean", "process"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
We gave **Leanstral 1.5** — Mistral's open-weights Lean 4 theorem-proving model, which
Mistral reports **scores 100% on the standard miniF2F mathematics benchmark** — two of
our *real* proofs: the soundness of
[ordeal](https://github.com/pulseengine/ordeal)'s SMT-certificate checker, and the
scheduling-theory suite in [gale](https://github.com/pulseengine/gale). (We didn't
re-measure the benchmark — we measured *our* proofs.)

On gale's Mathlib-flavoured lemmas it **converged cleanly** — axiom-clean, and it even
re-derived one of our theorems by a *different* valid path than the one already in our
repo. On ordeal's hardest leaf it engaged just as seriously — finding the right lemmas on
its own — and mapped, precisely and safely, the boundary where our fuller, human-guided
workflow still earns its keep. Same model, two surfaces: a **genuine win, and a genuinely
useful limit** — both of them good outcomes.

And the property that matters more than either result: **in neither evaluation, across
any trial, did it produce a wrong proof that Lean accepted.** Every failure was an honest
`sorry` or an elaboration error. The value of an AI prover in safety-critical
verification isn't that it discharges your obligations. It's that when you build on an
untrusted producer and a trusted checker, a brilliant-but-jagged prover *cannot corrupt
the result* — whether it wins or loses.
{% end %}

## The setup

Both proofs are real, and both trust only a small kernel-checked core.

**ordeal** is a pure-Rust SMT solver built on the **certifying-algorithm** pattern: the
solver is untrusted; every `UNSAT` verdict carries an LRAT certificate that a small,
**formally verified checker** replays before the answer is returned. Only the checker is
trusted. Its soundness theorem — *accept ⇒ UNSAT* — is discharged in Lean 4, with the
Rust checker translated via [Aeneas](https://github.com/AeneasVerif/aeneas) and the
obligation proved over that translation. This is the *hard* surface: the proofs are
dominated by the **Aeneas-simulation idiom**, not textbook mathematics.

**gale** carries a suite of scheduling-theory lemmas — utilisation bounds, RMA bounds —
in self-contained, **Mathlib-flavoured** Lean. This is the surface that looks most like
the mathematics the model was trained to saturate.

One thing to be plain about up front: **every proof in our repos is AI-assisted.** There
is no hand-authored baseline — the human's role is guidance, tactics, and gating, and the
kernel's role is to be the final judge; the proofs themselves are machine-generated and
machine-checked. The obligations we tested here were already closed and axiom-clean *that*
way. So the question was never "can the model save us." It was the honest one: **is this
particular benchmark-topping model, run on its own, worth adopting as a proving backend for
work like ours — and where?**

## How we ran it

So the result is reproducible — and falsifiable — here is the exact setup:

- **Model:** Leanstral 1.5, Mistral's Lean 4 prover — Apache-2.0 open weights
  (`mistralai/Leanstral-1.5-119B-A6B`), also reachable through Mistral's free hosted API.
- **Harness:** Mistral's `vibe --agent lean` agent wired to the **Lean-LSP MCP**
  (`lean-lsp-mcp`), so the model works against *live goal state* from the language server
  rather than blind text — `thinking = high`, `temperature = 1.0`.
- **Clean room:** every trial ran in a sandbox holding only the target statement (its
  proof replaced by `sorry`) and its dependencies. We scanned each transcript for reads of
  the real source or its compiled `.olean`, and diffed the produced statement
  byte-for-byte against ours — so a proof it *copied* could never be counted as a proof it
  *found*.
- **Oracle:** Lean itself, nothing else — `lake env lean` exit 0, no `sorry`, `#print
  axioms` restricted to the expected core, transcript leak-scan clean — then re-checked
  under each project's pinned toolchain. The model proposes; the kernel decides.

## What it did

**On ordeal's hard leaf** — isolated, 90 turns, live Lean-LSP goal state — it *genuinely
engaged*: 13 edits, 28 language-server calls, and it independently found the right
ingredients (`IScalar.hcast_inBounds_spec`, `numBits .I32 = 32`, a `congrArg … Int.toNat`
closer). It did not converge — it went down a long manual-bounds path, never found the
concise route our proof uses (`simp only [lift, WP.spec_ok]; scalar_tac`), and hit the turn
cap tangled in tactic detail. And it stopped *honestly*: three explicit elaboration errors
and a `sorry`, never a proof it hadn't earned. That is the boundary drawn cleanly — real
capability up to it, and no pretending past it.

**On gale's scheduling lemmas** it converged cleanly, twice:

- **Re-derivation** — handed the real `task_utilization_bounded` statement with the helper
  lemmas stripped, it produced a **passing, axiom-clean** proof by a *different* valid
  Mathlib path than ours (a general `calc` through `div_nonneg`/`div_self` where our
  existing proof went through `Rat.div_def`). The statement was diff-confirmed byte-identical to
  gale's source — the same theorem, an independent proof.
- **Extend** — asked for a genuinely new theorem (`rmaBound_le_one`, a universal upper
  bound gale didn't have), it correctly discovered it had to peel the argument down to
  expose the piecewise branches, and closed each — **passing, axiom-clean.**

Both gale proofs: `lake env lean` exit 0, no `sorry`, `#print axioms` reporting only
`{propext, Classical.choice, Quot.sound}`, transcript leak-scan clean.

## The jagged frontier, measured

Put those side by side and you have the **jagged frontier** in a single controlled
experiment: a model that saturates competition mathematics *converges cleanly* on
Mathlib-style scheduling theory and *does not yet reach* the Aeneas-simulation idiom that
dominates a real systems proof. Strong capability on one surface and a clear limit on
another coexist in the same model, the same week, the same harness. **You cannot read the
benchmark score as reliability on your workload** — you have to measure it on *your*
surface, because the answer is domain-specific and the two domains sat right next to each
other.

{% note(kind="tip") %}
One operational surprise worth flagging: you have to stop the model *cheating*. If the
real proof's source (or its compiled `.olean`) is reachable on disk, the agent will `grep`
and copy it. So we ran every trial in a sandbox containing only the target statement
(proof replaced by `sorry`) and its dependencies — clean-room verification, applied to
the model itself. A proof it copies is not a proof it found.
{% end %}

## Why it's safe either way

Here is the property that matters more than any success or failure rate: **across every
trial on both surfaces, it never produced a wrong proof that passed Lean.** Not once.
Every failure surfaced as an honest error or an explicit `sorry` — never a false green.

That is not luck; it is the architecture. The Lean kernel is *indifferent to brilliance* —
it rejects a sophisticated-but-unsound step and a dumb typo with equal force. So the
producer is *allowed* to be jagged — a savant on gale's surface, lost on ordeal's — because
the checker is incorruptible. This is the one setting where "superhuman but unreliable" is
fully tamed: the model proposes, Lean disposes, and a proof Lean has not accepted is simply
not a proof. It never enters the record.

The failure mode you have to fear from an AI in most domains — *plausible, confident, and
wrong* — cannot occur here. And the success came with a bonus the architecture makes free:
because gale's re-derivation was an *independent* proof of a statement we'd diffed to be
identical, it's corroboration — a second, kernel-checked derivation of the same theorem, the
proof-side echo of a second implementation confirming a spec.

## What we adopted

Falsification-first, the honest reading across both evaluations:

- **Adopt** it for gale's **Mathlib-flavoured / self-contained** Lean obligations and for
  **repo-aware navigation and lemma reuse** — it earns its keep there, cleanly and
  axiom-free.
- **Don't expect a single model, run solo, to author the Aeneas-simulation idiom** that
  dominates ordeal's hard leaves — for now that's where our fuller assisted loop earns its
  keep: human guidance on process and tactics, iteration, and the oracle-gated refine
  cycle, with the model as one contributor rather than a one-shot author. A workflow, not a
  lone prover.
- **Wire the language-server MCP** for any real use — live goal state was the difference
  between "zero attempts" and genuine engagement.
- **Re-verify under the pinned oracle.** gale's runs used a newer Lean/Mathlib than gale's
  pinned toolchain; a passing proof gets re-checked through the project's own build before
  it counts. The generator is never the oracle — not even when it succeeds.
- **Keep the human guiding the process** — steering tactics, spotting the shortcut the
  model missed — and owning the question no checker answers: *is this the right theorem,
  and does the proof match the code.*

## The falsification statement

This whole post rests on one falsifiable claim: **a model-authored proof can never pass our
checker while being unsound.** It held across every trial, on both the surface the model
failed and the surface it aced. The day one *doesn't* — the day a producer talks Lean into
accepting a false proof — the failure is in our *checker or its trusted base*, not the
model, and that is exactly where we would want to be looking. The producer being wrong is
expected and safe. The producer being *right* is welcome but still re-checked. The checker
being wrong is the only thing that could hurt us, and it is small, verified, and the thing
we guard.
