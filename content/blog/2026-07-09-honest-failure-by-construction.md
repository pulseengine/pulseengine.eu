+++
title = "Honest failure by construction: a state-of-the-art prover meets a real soundness proof"
description = "We pointed a Lean model that scores 100% on the standard math benchmark at our hardest real proof — the soundness of an SMT-certificate checker. It engaged deeply, found the right lemmas, and still couldn't close it. That was the good result: across every trial it never once produced a wrong proof that passed the checker. The value of an AI prover in safety-critical work isn't that it closes your proofs — it's that the architecture makes its failures safe."
date = 2026-07-09
draft = true
[taxonomies]
tags = ["verification", "ai-agents", "lean", "process"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
We gave a state-of-the-art Lean 4 theorem-proving model — one that **saturates the
standard mathematics benchmark (100% on miniF2F)** — our *hardest* real proof: the
soundness of [ordeal](https://github.com/pulseengine/ordeal)'s SMT-certificate
checker. It engaged deeply, found the right lemmas on its own, and **still could not
close it.**

That was the result we were hoping for. Not because we wanted it to fail — but
because *how* it failed is the whole point: across four graded trials it **never once
produced a wrong proof that Lean accepted.** Every failure was an honest `sorry` or
an elaboration error. The value of an AI prover in safety-critical verification isn't
that it discharges your obligations. It's that when you build on an untrusted producer
and a trusted checker, a brilliant-but-jagged prover *cannot corrupt the result.*
{% end %}

## The setup

ordeal is a pure-Rust SMT solver built on the **certifying-algorithm** pattern: the
solver is untrusted; every `UNSAT` verdict carries an LRAT certificate that a small,
**formally verified checker** replays before the answer is returned. Only the checker
is trusted. Its soundness theorem — *accept ⇒ UNSAT* — is discharged in Lean 4 (the
Rust checker is translated via [Aeneas](https://github.com/AeneasVerif/aeneas) and its
`accept ⇒ UNSAT` obligation proved over the translation).

That obligation was already closed by hand — zero `sorry`, axiom-clean. So the
question wasn't "can the model save us." It was the honest one: **is a
benchmark-topping Lean model worth adopting as a proving backend for work like this?**
We ran four graded trials to find out.

## What it did

- **Self-contained, math-flavoured obligations:** *passed* — cleanly, axiom-free.
- **Repo-aware navigation and lemma reuse:** *worked* — it found and reused the right
  ingredients.
- **The hard leaf, minimal budget, no live goal state:** *failed* — zero proof
  attempts, pure orientation.
- **The hard leaf, best shot** (isolated, 90 turns, live Lean-LSP goal state): it
  *genuinely engaged* — 13 edits, 28 language-server calls, and it independently found
  the right ingredients (`IScalar.hcast_inBounds_spec`, `numBits .I32 = 32`, a
  `congrArg … Int.toNat` closer). And it *still did not converge*: it went down a long
  manual-bounds path, never found the concise route our proof uses
  (`simp only [lift, WP.spec_ok]; scalar_tac`), and hit the turn cap tangled in tactic
  detail — leaving three elaboration errors and a `sorry`.

This is the **jagged frontier** in one experiment: a model that saturates competition
mathematics could not nail the *Aeneas-simulation* idiom that dominates a real
systems proof. Peak benchmark capability and a floor on this specific idiom coexist in
the same run. You cannot read the benchmark score as reliability on your workload.

{% note(kind="tip") %}
One operational surprise worth flagging: you have to stop the model *cheating*. If the
real proof's source (or its compiled `.olean`) is reachable on disk, the agent will
`grep` and copy it. So we ran every trial in a sandbox containing only the target
statement (proof replaced by `sorry`) and its dependencies — clean-room verification,
applied to the model itself. A proof it copies is not a proof it found.
{% end %}

## Why the failure is the good news

Here is the property that matters more than any success rate: **across all four trials,
it never produced a wrong proof that passed Lean.** Not once. Every failure surfaced as
an honest error or an explicit `sorry` — never a false green.

That is not luck; it is the architecture. The Lean kernel is *indifferent to
brilliance* — it rejects a sophisticated-but-unsound step and a dumb typo with equal
force. So the producer is *allowed* to be jagged — to be a savant one line and lost the
next — because the checker is incorruptible. This is the one setting where "superhuman
but unreliable" is fully tamed: the model proposes, Lean disposes, and a proof that
Lean has not accepted is simply not a proof. It never enters the record.

The failure mode you have to fear from an AI in most domains — *plausible, confident,
and wrong* — cannot occur here. That is what the untrusted-producer / trusted-checker
architecture buys, and this experiment is it, measured.

## What we actually adopted

Falsification-first, the honest reading of four trials:

- **Adopt** it for **self-contained / math-flavoured** Lean obligations and for
  **repo-aware navigation and lemma reuse** — it earns its keep there.
- **Do not** rely on it to author **Aeneas-simulation proofs** from scratch — the
  idiom that dominates the hard leaves. Even the best-shot run couldn't close them; the
  hand-written path stays necessary.
- **Wire the language-server MCP** for any real use — live goal state was the
  difference between "zero attempts" and genuine engagement.
- **Keep the human on the idiom the model can't reach** — and on the question no
  checker answers: *is this the right theorem, and does the model match the code.*

The next surface is a better fit for the model's strength — the Mathlib-flavoured Lean
suite in [gale](https://github.com/pulseengine/gale), where the obligations look more
like the mathematics it saturates. That evaluation is running now.

## The falsification statement

This whole post rests on one falsifiable claim: **a model-authored proof can never pass
our checker while being unsound.** It held across four trials. The day one *doesn't* —
the day a producer talks Lean into accepting a false proof — the failure is in our
*checker or its trusted base*, not the model, and that is exactly where we would want
to be looking. The producer being wrong is expected and safe. The checker being wrong
is the only thing that could hurt us, and it is small, verified, and the thing we
guard.
