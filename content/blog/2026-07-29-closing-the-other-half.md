+++
title = "Closing the other half"
description = "Last time we published a proof and an honest paragraph about what it did not cover. This is the follow-up: the missing half is proven — but first the tool didn't work, then the compiler refused a fix, and the cosine turned out ten times better than the sine."
date = 2026-07-29
draft = false
ready = true
[taxonomies]
tags = ["verification", "floating-point", "embedded", "how-it-works"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
In [One ulp of doubt](/blog/one-ulp-of-doubt/) we ended on a deliberately
uncomfortable note: the rounding layer of our `f32` sine kernel was
machine-checked, and the *approximation* layer — whether the polynomial is
actually close to true sine — was not. We wrote it down as open. This is what
happened when we went to close it.
{% end %}

Publishing "here is what we have **not** proven" creates a small, useful debt.
Ours came due quickly, and paying it went through three surprises: a tool that
didn't work, a compiler that wouldn't cooperate, and a result that was better
than expected for a reason worth understanding.

## The tool didn't work

The plan was straightforward. Rounding error — is the floating-point computation
faithful to the polynomial it implements? — is Gappa's job, and that half was
done. Approximation error — is the polynomial close to true sine? — is
[Coq-Interval](https://coqinterval.gitlabpages.inria.fr/)'s job. Wire up
Coq-Interval, write the analogous proof, done.

Coq-Interval was already in our build rules. The smoke test was one line:

```coq
Require Import Interval.Tactic.
```

```
Error: Cannot load mathcomp.boot.seq
```

The package had been *fetched*, but not its dependency closure — bignums,
mathcomp-boot, mathcomp-fingroup, and transitively hierarchy-builder and the
coq-elpi plugin. Nothing had noticed, because the build only ever checked that
the package downloaded, never that a proof using it compiled.

That is a familiar failure with an unglamorous fix: make the toolchain compose
the whole closure in one go, and — the part that matters — **add a test that
actually uses the tactic**, not one that merely fetches the package. A capability
you have not exercised is a capability you do not have. The smoke test is now
four lines and it proves `1 + 1 <= 3` by interval arithmetic, which sounds
trivial and is the entire point: if that compiles, the tactic is real.

## The proof, and giving it teeth

With the tool working, the proof is short. The claim, kernel-checked by `coqc`:

```
|P(r) − sin r| ≤ 1e-8   for all r ∈ [−0.8, 0.8]
```

where `P` is the exact real value of the kernel's polynomial and the range is
the interval the argument reduction clamps to.

Two details carry all the weight.

**The coefficients are copied verbatim from the Gappa proof.** Not
re-derived, not rounded from a paper — the identical `f32` dyadic constants,
character for character. This is not tidiness; it is the whole reason the two
results compose. The rounding proof bounds *computed vs. the polynomial*; the
approximation proof bounds *the polynomial vs. true sine*. They chain by
triangle inequality **only if both mean the same polynomial**. Different
coefficients would give you two true theorems about two different functions and
a conclusion about neither.

**The bound is tested for teeth.** A bound that passes at any value proves
nothing, so we binary-searched it: the tactic proves `1e-8`, and **fails** to
prove `8e-9` — even when given more computational budget. It stops working just
below where we claim it works. A proof that cannot fail is a proof that is not
checking anything.

{% note(kind="tip") %}
**A useful cross-check.** The approximation error (`1e-8`) is an order of
magnitude *below* the total error we measured by exhaustively testing all 2.2
billion inputs (`1.19e-7`). That is the right relationship: the total is
dominated by rounding, not by the polynomial fit. If the approximation bound had
come out *larger* than the measured total, something would be wrong with one of
them.
{% end %}

## The compiler said no

Then a neighbouring team ran our components through their compile-to-ARM
pipeline, per-stage, and reported something sharp: three of the five control
stages failed to lower — and the thing being skipped was **the public entry
point of each one**. The blocker was a single instruction their backend couldn't
yet emit: a 64-bit-integer-to-float conversion.

They even found the source line, and suggested a workaround: narrow the value to
32 bits and the instruction disappears — three stages unblocked without waiting
on a compiler fix.

The diagnosis was exactly right. The conversion came from a timestamp helper
that turned a `u64` seconds field into `f32`. The three crates that call it were
precisely the three blocked stages. (A fourth stage defines the same type but
never calls the helper — and it was blocked by a *different* defect. The
correlation was clean.)

So we made the fix. The control loops only ever use the *difference* between two
timestamps, never an absolute one, so the delta can be computed in integer
arithmetic and converted once, when it is small.

And then we checked the output. The instruction was still there.

We tried four formulations — a bounds check, a `min`, a bit-mask truncation, an
early narrowing with a small cap. We disassembled the compiled component after
each one. Every time, the optimiser hoisted the conversion back: it clamped in
integer arithmetic exactly as asked, then converted the 64-bit value anyway and
capped in *floating-point*. On this target both forms cost the same, so it had no
reason to prefer ours. We even deleted the original helper outright to be sure we
were not chasing a ghost. The instruction stayed.

{% note(kind="warning") %}
**We reported the negative result the same day.** It would have been easy to
write "three stages unblocked" — the change was in, the tests were green, the
reasoning was sound. But the artifact said otherwise, and the artifact wins.
Telling a colleague their workaround succeeded when it did not would have sent
them to build on a foundation that was not there.
{% end %}

The change shipped anyway, on its own merits. Subtracting two large absolute
`f32` timestamps is a genuinely bad idea: at a million seconds, one `f32` step is
about 60 milliseconds — enough to swallow a 1-millisecond control period whole.
Differencing in integers and converting the small result is simply more accurate.
It just does not solve the lowering problem, and we said so.

## The cosine is ten times better, and that is not luck

With sine closed, the cosine kernel followed the same recipe. Same tools, same
verbatim-coefficient discipline, same teeth test. The result:

| kernel | approximation error | fails to prove |
|---|---|---|
| sine | `1e-8` | `8e-9` |
| **cosine** | **`1e-9`** | `1e-10` |

An order of magnitude better, from the same method on the same range. The reason
is visible in the source. The cosine kernel is

```
1 − 0.5·z + z²·(C₁ + z·(C₂ + z·C₃))
```

The first two terms are the exact leading terms of cosine's Taylor series — no
approximation at all. Only the small residual is fitted. The sine kernel fits a
larger share of its value, so it carries more of the error. The polynomial that
has to invent less is more accurate. Obvious in hindsight; visible only because
both numbers came from the same machine-checked process rather than two different
estimates.

## What is proven now, and what is not

The same accounting as last time, updated. Four bounds, all kernel-checked, all
running as required checks:

| | rounding (Gappa) | approximation (Coq-Interval) |
|---|---|---|
| **sine** | ≤ 2⁻²⁴ | ≤ 1e-8 |
| **cosine** | ≤ 2⁻²³ | ≤ 1e-9 * |

<small>\* The cosine approximation bound is proven and checked by CI, but at the
time of writing it is still in review rather than merged — so treat that one cell
as "landing", not "landed". We would rather say that than round it up.</small>

And the boundary, stated as carefully as before:

{% note(kind="warning") %}
**Still open — and worth being precise about.** Having both halves proven is not
the same as having the *composed* result proven. The triangle inequality that
chains them into a single statement about the reduced range is a further proof
obligation, and it is not discharged yet. Neither is the argument-reduction
cancellation — the step that brings an arbitrary input into the range these
proofs cover — which remains the hardest piece of the four. Until that lands, we
have strong bounds on a *reduced range*, not on the whole input domain.
{% end %}

That distinction is easy to blur and would be the most flattering possible thing
to blur. Two proofs that could compose are not a composition.

## What we would tell you to take from this

Three things, none of which are about floating point.

**A tool you have not exercised is not a capability.** Coq-Interval was in our
build, listed as available, and did not work. The test that would have caught it
is the test that uses it for its actual purpose, not the one that checks it
downloaded.

**Check the artifact, not the reasoning.** The timestamp fix was correct in
every way that a code review would examine — right diagnosis, sound argument,
passing tests — and did not do the thing it was written to do. Four times. The
only reason we know is that we disassembled the output each time instead of
trusting that a plausible change had a plausible effect.

**Publishing what you have not proven is what makes the follow-up meaningful.**
The open item in the last post is why this one exists. If we had written "the
kernels are verified" and left it there, nobody — including us — would have had a
concrete reason to come back and close the other half.

---

*Falcon / relay-math · the proofs and the exhaustive harness are in the tree, and
the machine-checked bounds run as required checks. Toolchain: Gappa + Flocq +
Coq-Interval, wired in through our Rocq build rules. This is work in progress:
the composition and the argument-reduction bound are still open, and we will say
so until they are not.*
