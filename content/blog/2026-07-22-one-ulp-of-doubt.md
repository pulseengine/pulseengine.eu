+++
title = "One ulp of doubt"
description = "A colleague asked whether our flight-control code should carry 32-bit floats or 64. Answering it honestly took a CI gate, 2.2 billion test cases, and a machine-checked proof — and each one caught something the last had missed. A small story about the three different things 'we verified it' can mean."
date = 2026-07-22
draft = true
ready = false
[taxonomies]
tags = ["verification", "floating-point", "embedded", "how-it-works"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
A colleague, looking at the flight core, asked the obvious and correct question:
*are we sure these floats should be `f32` and not `f64`? Have we actually
checked?* The honest first answer was that we hadn't **proven** it — we'd
**assumed** it. And an assumption you can't point at isn't engineering, it's
habit. So we went and checked, and the checking turned into a small story about
the three different things "we verified it" can mean.
{% end %}

## The question: 32 or 64?

Falcon — the multirotor flight stack we build under formal verification — is
wall-to-wall floating point: an invariant-EKF fusing IMU and GNSS, a geometric
attitude controller, a mixer, failsafes. Every one of those touches `sin`,
`cos`, `sqrt`, a quaternion, a covariance matrix. The precision of those floats
is not a detail; it is the difference between an estimate that holds and one that
quietly drifts.

The tempting answer to "32 or 64" is "64 is safer, use 64." It is also wrong
here, for a reason that lives in the silicon.

The estimator partition runs on a Cortex-M4 whose floating-point unit is
**FPv4-SP — single precision only**. There is no 64-bit float hardware on that
core. Every `f64` operation there is *software-emulated*, roughly an order of
magnitude slower, on the hottest loop in the whole system. In a stack whose
worst-case timing is part of the safety argument, that isn't "safer" — it's a
landmine.

And the wider world agrees: PX4's EKF2 and ArduPilot's NavEKF3 both fly
single-precision filters, with the same two mitigations we already had —
navigate in a *local* frame (so you never hold an absolute latitude in an `f32`,
where it would quantize to ~0.6 m), and keep the covariance matrix healthy. So
the real answer to the colleague was:

> 32-bit is the requirement, not the compromise. The one place 64-bit belongs is
> absolute latitude and longitude — and it was already there.

Clean answer. Except for one uncomfortable word: *already*. It was true, but it
was **tribal knowledge** — a fact in someone's head, not a rule the codebase
enforced. Nothing stopped the next commit from dropping an `f64` into the flight
path and soft-floating the M4 into a deadline miss. And when we looked closely at
the covariance code, we found exactly one genuine latent risk. That's where the
work started.

## Tier 1 — make it a rule

The first tier is the cheapest and the one people skip: turn the convention into
something a machine refuses to let you break. A CI gate now denies the `f64`
token anywhere in the 21 flight-partition crates, except in files that carry an
explicit, human-signed annotation saying "this is the geodetic boundary, and
here's why." Today exactly one file carries it.

The real find, though, was next door. The EKF's covariance update uses the cheap
textbook form `P ← (I − KH)·P`, which in `f32` can round a diagonal variance
slightly *negative* under a strong update — and a negative variance corrupts every
gain after it. The classic fix is to floor each diagonal. We wrote the floor and
asked [Kani](https://github.com/model-checking/kani), the bounded model checker,
to prove it total over all inputs.

Kani **rejected our first version.** A `+∞` variance sailed straight through a
naive `d ≥ floor` check — and the right repair for an infinite variance is to heal
it to the *ceiling* (maximal uncertainty), never the floor, which would fabricate
certainty exactly where there is none. The checker caught us reaching for the
wrong safe value. That is the whole point of a checker.

## Tier 2 — test harder

With the last `f64` gone from the flight path, we replaced `libm`'s `sinf` /
`cosf` — which are `f32` on the outside but compute with `f64` *inside* (the last
soft-float on the M4) — with kernels that are single-precision end to end. Then we
had to answer: how accurate are they, really?

Our first answer was a sampled sweep — four million points across the range —
reporting "within 2 ulp." It was also **quietly lying.** A sample of a continuum
cannot bound a worst case; it can step right over the bad arguments. So we did the
thing that is tractable precisely because a single-argument `f32` function is
finite: we checked *every one*.

| measure | value |
|---|---|
| inputs checked | **2.2 × 10⁹** — every `f32` in the envelope |
| worst absolute error | **1.19 × 10⁻⁷** — one ulp of unity |
| worst relative error | **≤ 2 ulp** everywhere the value isn't near zero |

Against a near-true `f64` reference, over all ~2.2 billion representable inputs in
range, the worst absolute error is `1.19e-7` — one ulp at unit magnitude. Clean.
But the exhaustive sweep also surfaced what the sample had walked past: near the
zeros of sine, the error blows up to ~14 ulp.

That looks alarming and isn't. Near a zero the *value* is almost nothing, so a
fixed tiny absolute error becomes many ulp of a vanishing magnitude — an artifact
of measuring in ulp, not a loss of accuracy. The absolute error there is still
`1.19e-7`, and the estimator consumes the value, not its ulp. The lesson kept:
**state the bound you can defend over the whole domain, not the one your sample
happened to see.**

## Tier 3 — prove it

Exhaustive testing is a genuine certification method — it's how the reference
single-precision libraries are validated. But it is still testing. The next tier
is a *proof*: a statement a proof kernel has checked, that holds by construction
rather than by enumeration.

Floating point has a purpose-built tool for this — **Gappa** — which bounds the
rounding error of a floating-point expression and emits a *Flocq/Coq proof term*
as its certificate. The discipline that matters: we never trust Gappa's own
success. Its output is compiled by `coqc`, and the proof only counts if the kernel
accepts it.

```gappa
# the f32 Horner evaluation of the sin polynomial,
# faithful to the exact math it implements:
@rnd = float<ieee_32,ne>;
z    rnd= r * r;
# ...
Msin rnd= r + pr;         # computed, each op rounds
Esin  =  r + Epr;         # exact, same coefficients

{ rin in [-0.8, 0.8] -> |Msin - Esin| <= 1b-24 }
```

The claim the kernel checked: over the reduced range, the `f32` evaluation of the
sine polynomial is within `2⁻²⁴` — one ulp of unity — of the exact value of the
same polynomial. And it is *tight*, and it has *teeth*: we binary-searched the
bound, and `coqc` accepts `2⁻²⁴` and **rejects `2⁻²⁵`**. A proof that passes at
any bound proves nothing; this one fails when it should. It runs as a required
check on every pull request, so it cannot quietly rot.

## The part most write-ups leave out: what we did *not* prove

Here is the honest boundary, because a proof described past its actual reach is
worse than no proof — it's a false one wearing a certificate.

{% note(kind="tip") %}
**Proven — the rounding layer.** Gappa proved that our floating-point computation
is faithful to the polynomial it implements. That's real, and it's half the story.
{% end %}

{% note(kind="warning") %}
**Not yet proven — the approximation layer.** That the polynomial itself is close
to *true* sine — the minimax remainder `|P(r) − sin r|` — is a different proof, in
a different tool (Coq-Interval), and it is a scoped follow-on, not something this
proof establishes. So is the argument-reduction cancellation. We know these are
open, and we say so.
{% end %}

There was a second piece of honesty the work forced on us. Swapping the trig
kernels — a change of at most 2 ulp — flipped a hover in one closed-loop test. It
would have been easy to shrug it off as "the new kernel is worse." The evidence
said otherwise: the baseline `libm` build flipped in the *same* test too. What
we'd actually exposed was a pre-existing fragility in an unrelated filter loop — a
real bug, kernel-agnostic, that the precision change merely *revealed*. We filed
it with the full data and left the affected claim untouched, because you correct a
shipped, verified result only *after* you understand it, not on a hunch.

## The takeaway: three tiers, one blind spot each

The thing worth carrying out of this isn't the number. It's the shape of the
answer. "We verified it" is not one claim; it is at least three, and they are not
interchangeable:

- **The gate** makes a fact enforceable — and its neighbour, Kani, caught a wrong
  safe-value.
- **The exhaustive sweep** found the worst case a sample was hiding.
- **The proof** established by construction what enumeration can only sample —
  and, checked cold, told us where it stops.

Each tier caught something the tier below it structurally could not. A gate can't
tell you an accuracy; a test can't bound a continuum from a sample; a proof is
only as honest as the claim you dared to write. Stacked, they answer a colleague's
one-line question with something you can actually stand behind — including the
part where you say what you haven't done.

> The most valuable output of the whole exercise might be the sentence we can now
> write without flinching: here is exactly what is proven, here is what is only
> tested, and here is what is still open.

32-bit was the right answer all along. It just took three kinds of proof, and one
honest paragraph, to earn the right to say so.

---

*This is work in progress. The proofs and the exhaustive harness live in the tree;
the machine-checked bound runs as a required gate. Toolchain: Kani (bounded model
checking), exhaustive `f32` enumeration, and Gappa + Flocq + Coq-Interval wired in
through our Rocq build rules.*
