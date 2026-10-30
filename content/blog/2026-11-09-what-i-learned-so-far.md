+++
title = "What I learned so far: an index over the first 29 posts"
description = "One entry per post from March to November 2026: what it set out to show, what it actually found, and what changed afterwards, including the corrections and the claims nobody has revisited yet. Grouped into five phases, with a short list of what changed in how I work."
date = 2026-11-09
draft = true
[taxonomies]
tags = ["process", "knowledge-base"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**This blog is my own knowledge base, and this page is its index.** Each of the 29 posts gets
three lines: what I expected going in, what the post actually found, and what changed
afterwards. Where an early post claims more than later evidence supports, the entry says so
and points to the correction or the later post. Where nothing has corrected it, the entry says
*not yet revisited*.
{% </insight> %}

I wrote this on 29 October 2026, from the post texts and the git history of `content/blog/`.
The four posts dated 29 October to 5 November were scheduled drafts at that point, not
published, and their entries are marked *scheduled*. "Changed" lists only what the record
shows: a dated correction note in the post, a commit that edited it, or a later post that
measured the same thing again. A rewrite of the site tagline on 27 October (#263) touched most
footers and is not repeated in every entry.

## March: the promise

Four posts in two weeks, written before anything had been measured from the outside. The
opening post promised a proof for every transformation and a qualification that products would
inherit. The rivet post reported coverage figures of 100% and 97%, which count links between
artifacts, not results. The formal-verification post said proof effort had dropped by orders
of magnitude. Only the formal-verification post had an explicit section on what was open; the
others had at most a roadmap. Seven months later, on 27 and 28 October, only *Hello, World*'s
opening and engine paragraphs, one sentence in the rivet post and the footers were corrected
in place. The other overclaims were narrowed by later posts, not
edited, so a reader of the March posts alone still gets the March picture.

- **[Hello, World](@/blog/2026-03-02-hello-world.md)**, 2 Mar. *Expected:* a home for "This
  Week in PulseEngine" roundups, deep-dives and design notes, opening on a proof for each
  transformation and an inherited qualification. *Found:* none of the 29 posts is a roundup.
  *Changed:* corrected 27 and 28 Oct (#263, #267): loom is translation-validated per run, synth is
  differentially tested and not proven, nothing is qualified, and sigil signs artifacts while
  the end-to-end attestation chain is still being built. The roundup promise: not yet revisited.
- **[meld v0.1.0](@/blog/2026-03-02-meld-v0.1.0.md)**, 2 Mar. *Expected:* static fusion
  removes the trade-off between typed composition and flat deployment. *Found:* a C hello-world
  went from 4 core modules and 23 instances to 1 module, 304 KB to 292 KB. *Changed:* rewritten
  for accuracy the next day (#9). By 18 July meld fused an app and a kernel component into one
  (gust); the 5 Nov post records that meld's default output keeps one memory per component and
  its P3 async lowering is partial. The claim that no embedded runtime supports the Component
  Model natively: not yet revisited.
- **[rivet: because AI agents don't remember why](@/blog/2026-03-15-rivet-v0.1.0.md)**, 15 Mar.
  *Expected:* traceability as YAML in git, validated on every commit, maintained by agents.
  *Found:* rivet tracking 344 of its own artifacts at 100% coverage, gale 268 at 97%, 402 tests,
  and "Kani proofs and Verus specs on core data structures". *Changed:* three weeks later the
  7 Apr post said that verification of rivet's core was planned and not implemented; the
  sentence here is not yet revisited, and neither is the footer's "Synth transpiles" (synth
  transcodes). The 29 Oct post showed what the coverage figures count: in gale, 302 of 329
  software requirements linked to a check, none with a recorded result.
- **[Formal verification just became practical](@/blog/2026-03-15-formal-verification-ai-agents.md)**,
  15 Mar. *Expected:* agents collapse the cost of proofs. *Found:* a description of gale's
  stack as three provers checking the same properties, Verus contracts on all public functions,
  sanitizers and mutation testing, all in CI, plus an honest open-questions section. *Changed:*
  the MC/DC section was rewritten on 11 May when witness shipped. The rest was narrowed
  elsewhere: the 12 Jul post states that several proofs run over hand-transcribed models and
  some modules are admitted stubs; the overdoing table, corrected in October (#220), counts sanitizers in
  2 of 13 Rust repos; gale had 0 recorded results on 26 Oct. No later post measures
  "orders of magnitude", and the 5 Nov post says "We do not publish productivity figures": not yet revisited.

## April: method

Six posts that turned the March promise into a method. The core is the oracle-gated pattern:
a narrow prompt, a mechanical check that either fires or does not, parallel agents and a
fresh-session validator before anything lands. In the slop hunt the second round exposed three
bugs in the first round's oracle, which is evidence the pattern can check itself. The pattern later became the
plugin's skills (May, per the [timeline](@/timeline.md)). What did not hold was the status
reporting: tables in April described adoption that an October count cut back, and two
arguments, the union of three patterns and the variant-pruning inversion, have stayed
arguments without a measurement.

- **[What comes after test suites](@/blog/2026-04-07-what-comes-after-test-suites.md)**, 7 Apr.
  *Expected:* in regulated work, test suites are necessary and not sufficient, and proofs close
  the gap. *Found:* the claimed stack: Verus on all 39 gale modules, Rocq over abstract models
  with zero admitted lemmas, rivet at 447 artifacts and 100% coverage, sigil with "SLSA L4
  provenance predicates", kiln down to 36 test-suite failures, adoption in "one organization.
  Mine." *Changed:* the 23 Apr post says sigil ships SLSA L2 and L3 and that L4 needs
  reproducibility work; the L4 sentence here is not yet revisited. The 12 Jul post records
  admitted stubs in gale.
- **[Spec-driven development is half the loop](@/blog/2026-04-23-spec-driven-development-is-half-the-loop.md)**,
  23 Apr. *Expected:* a QA agent reading the spec back is a soft oracle; replace it with a
  mechanical one. *Found:* two sigil pipelines, one that found a swallowed `cert_count` parse
  error (PR #87) and one that closed 9 of 12 `rivet validate` errors (PR #90). *Changed:* one
  link fixed on 15 Oct (#227). The plan for `spar-codegen` to emit build files from the
  AADL model, so the model drives the build: not yet revisited in any later post.
- **[Mythos slop-hunt](@/blog/2026-04-25-mythos-slop-hunt.md)**, 25 Apr. *Expected:* the same
  scaffold can hunt typed-but-unwired code. *Found:* the second round exposed three bugs in the
  first round's oracle (file-level trailer credit, a `cfg` that fabricated lint errors,
  blindness to inline annotations); PR #205 as a whole deleted about 370 lines, wired 3
  requirements and moved rivet's coverage from 36.9% to 39.5%; one agent invented a fifth symbol that grep refuted.
  *Changed:* link fixes only (#169, #227). "Weeks of human review" for the same depth is an
  estimate: not yet revisited.
- **[Three patterns colliding](@/blog/2026-04-25-three-patterns-colliding.md)**, 25 Apr.
  *Expected:* Karpathy's LLM wiki, oracle-gated agents and typed compliance together, a union
  the post calls "unheard of". *Found:* the evidence is the same PR #205, said to have produced
  "no LLM hallucinations". *Changed:* link fixes only (#169). The companion post records a
  hallucination that the check caught, so the accurate wording is that none survived the
  oracle: not yet revisited. This index is the wiki idea applied to the blog.
- **[Overdoing the verification chain](@/blog/2026-04-29-overdoing-the-verification-chain.md)**,
  29 Apr. *Expected:* run every technique, because the next assessor's question is unknown, and
  map the chain to six standards. *Found:* a status table and a credit matrix, with
  abstract interpretation and checkable proof certificates named as the missing pieces.
  *Changed:* the table was corrected to measured counts (note dated 6 Oct, merged 8 Oct, #220):
  proptest in 4 of 13 Rust repos, sanitizers in 2, tokio-rs/loom in no CI, cargo-mutants in 5,
  more than the post had said. Both named gaps later got a tool: scry for abstract
  interpretation (May) and ordeal, a solver whose answers a small proven checker re-checks
  (July).
- **[MC/DC for AI-authored Rust is tractable](@/blog/2026-04-30-variant-pruning-rust-mcdc.md)**,
  30 Apr. *Expected:* five layers of variant pruning make MC/DC for Rust "strictly less"
  effort than for C. *Found:* an argument with a multiplicative formula, its independence
  assumption stated, and no layer-5 tool yet. *Changed:* on 11 May the formal-verification
  post reported witness v0.14 shipping Wasm-level MC/DC; later posts call it MC/DC-style branch
  coverage. The 21 Oct post records that relay's witness coverage had silently stopped being
  produced (#397). The "strictly less" claim has no measurement: not yet revisited.

## May to July: reality

Nine posts, mostly measurements. The first published a wrong prediction, and the rest kept the
habit: say what the number was, what it was measured on, and what it does not show. The
dissolved OS ran on a real STM32F100 at 1.73× native against a 10 to 20% goal. A prover whose
makers report 100% on miniF2F did not converge on our hardest proof and never produced a false
one. The seams post introduced three words for maturity: wired, demonstrated, manual. The two
floating-point posts set the pattern of publishing what is not proven and then closing it.
June had no posts, although the timeline records gust booting bit-identical on three chips
that month.

- **[Cross-language LTO on Cortex-M](@/blog/2026-05-01-cross-language-lto-three-quiet-barriers.md)**,
  1 May. *Expected:* 10 to 30% faster handoffs from inlining Rust into Zephyr's C. *Found:* LTO
  came out 1.1 points slower than GCC with gale (−2.0% against −3.1% versus baseline), after
  clearing three undocumented barriers; the FFI was under 1% of a 340-cycle handoff, and LTO
  saved 360 bytes of flash. *Changed:* corrected 28 Oct (#272): gale is a Rust replacement with
  Verus contracts, and `nm` shows that no gale symbol survives, not that what was proved
  shipped. The cycle counts come from Renode while the method list says "measure on real
  hardware", and the fourth variant was never run: not yet revisited.
- **[Dissolving the OS](@/blog/2026-07-08-dissolving-the-os.md)**, 8 Jul. *Expected:* kernel,
  scheduler and driver as components, transcoded by synth, with no runtime on the device.
  *Found:* `run-demo` returns 53 on wasmtime and on a Cortex-M3; 1.73× native on an STM32F100;
  synth levers took one function from 2.81× to 1.81×; driver code gained 0% from them; a rivet
  coverage rule raised a false warning on every requirement, fixed in one line; a hand-lowered proof-carrying floor at 0.45×,
  not emitted by the pipeline. *Changed:* softened on the day (#109) and corrected 28 Oct
  (#272): the native code is differentially tested, not proven equivalent. The post calls the
  semaphore release "honestly, cuttable"; the 29 Oct post (scheduled) measures v0.1.0 as not
  cuttable, with its ten requirements `approved`.
- **[Jagged by nature, honest by construction](@/blog/2026-07-09-honest-failure-by-construction.md)**,
  9 Jul. *Expected:* see whether Leanstral 1.5 can prove real obligations. *Found:* it
  converged on gale's Mathlib-style scheduling lemmas, re-deriving one by a different path, and
  did not converge on ordeal's Aeneas-style leaf in 90 turns; no trial produced a wrong proof
  Lean accepted; given access it copies the real proof, so trials ran in a sandbox. *Changed:*
  nothing corrected. The 14 Oct post adds the limit: a `sorry` scan can pass while a proof
  depends on `sorryAx`, so the checker decides only if the gate asks it the right question.
- **[Someone else's spec](@/blog/2026-07-11-someone-elses-spec.md)**, 11 Jul. *Expected:* test
  rivet on a corpus I did not write. *Found:* 2,985 Eclipse S-CORE artifacts converted, with a
  log of every gap the corpus exposed; in example-kvs only the rivet layer is live, the witness
  and sigil entries are skeletons and the verification gate is a stub. *Changed:* a link fix
  (#227). The stub status: not yet revisited.
- **[Where the seams still show](@/blog/2026-07-12-where-the-seams-show.md)**, 12 Jul.
  *Expected:* label every joint as wired, demonstrated or manual. *Found:* `rivet validate`
  wired; loom checked with Z3 only where in scope, plus a differential backstop; synth
  demonstrated; the proof gate wired with an asterisk, because several proofs cover
  hand-transcribed models; the flight stack only in simulation. Two rules: "verified" names a
  property and a checker, and every hand-written bridge is named as trusted base. *Changed:*
  this is the first post in this list to name hand-transcribed models and admitted stubs.
- **[From a browser tab to a real drone](@/blog/2026-07-13-browser-to-bare-metal-to-drone.md)**,
  13 Jul. *Expected:* one component set on four substrates, with an honest label on each
  boundary. *Found:* wasm to native is differentially tested, not proven; gust runs
  bit-identical on three chips; the flight stack runs only in Gazebo and on an emulated
  Cortex-M7; witness coverage stops at the wasm boundary. *Changed:* by 21 Oct the falcon
  cascade had run bit-exact on the real Pixhawk; the 29 Oct post records that as one manual
  bench run, with no hardware in the automated loop.
- **[A verified OS, composed to 3.5 KB on real silicon](@/blog/2026-07-18-verified-os-on-silicon.md)**,
  18 Jul. *Expected:* gust composed from verified components into one small native image.
  *Found:* 53 on wasmtime, qemu and a real STM32F100; 1.73×, 1.45× and 1.84× native on M3, M4
  and RISC-V, better on M4 and RISC-V than ten days earlier; the MPU region arithmetic proven, its enforcement
  unbuilt. *Changed:* corrected 28 Oct: "certified hot path" removed. The title says "verified
  OS" while its own table lists only the semaphore as shipped, "rest in progress", and the
  29 Oct post finds no recorded result for the semaphore either: not yet revisited.
- **[One ulp of doubt](@/blog/2026-07-22-one-ulp-of-doubt.md)**, 22 Jul. *Expected:* answer
  "f32 or f64?" for the flight code. *Found:* f32 is the requirement on a single-precision M4;
  a CI gate now denies `f64` in 21 flight crates; Kani rejected the first covariance floor; a
  4-million-point sample said 2 ulp where the exhaustive 2.2 billion inputs showed about 14 near
  the zeros of sine; Gappa proved 2⁻²⁴ and rejects 2⁻²⁵. The approximation layer was stated as
  unproven. *Changed:* closed in the next post.
- **[Closing the other half](@/blog/2026-07-29-closing-the-other-half.md)**, 29 Jul.
  *Expected:* prove the approximation layer with Coq-Interval. *Found:* the tool was in the
  build but did not work, because the smoke test only checked the download; sine bounded at
  1e-8 and cosine at 1e-9, the cosine still in review; a suggested timestamp workaround did not
  remove the instruction after four attempts, reported the same day. *Changed:* the composition
  of the two bounds and the argument reduction were open on 29 Jul: not yet revisited.

## July to September: the factory being built

No posts in August or September. The [timeline](@/timeline.md) carries the period. In July
ordeal arrived, a QF_BV solver whose answers are no longer believed because it said so: each
UNSAT verdict carries a certificate that a small checker re-derives. The 28 Oct post scopes it:
the checker is proven sound in Lean 4 over an Aeneas translation of its Rust source, the
lowering to CNF is proven too, and the layers above are tested and checked against Z3. In August varve made the build machine
answerable: the whole tool set as one signed, dated, digest-pinned layer, with shims that
refuse to run outside a pinned project; the `gate-potency` audit for checks that cannot fail
landed on 5 August (#147). In September wasm-layers put the Bytecode Alliance tools into signed
layers and covalent-layers composed the two realms; rivet began replacing serde_yaml on
17 September, while spar merged four changes all month.

## October and November: the factory and the human

Ten posts, after eleven weeks without one. The subject moved from the tools to the system
around them, and then to me as its bottleneck. Two posts measured the repositories against
manufacturing's standards and against human-written projects. The `publication-review`
skill (#265, 27 Oct) records that four posts drafted with another model between 25 and 27
October carried an invented quotation clause, invented CLI output, wrong citations and wrong
arithmetic under a green build. The SAFe and estimation posts were corrected on 27 October, the
orchestrator post was held and corrected before it shipped, and the review panel that found the
defects became that skill. The last four posts, scheduled at the time of writing, date every
number, say whether code or an instruction enforces each mechanism, and in one case list what
would make me concede.

- **[AI in the product, not AI in the toolchain](@/blog/2026-10-14-ai-in-the-product-not-the-toolchain.md)**,
  14 Oct. *Expected:* find published guidance on using an agent in a certified development
  process. *Found:* one informative Technical Report, one VDA chapter known second-hand and a
  planned FAA disclosure policy; DO-178C and ISO 26262-8 exempt a tool whose output is
  verified, and nothing says what the verification must produce; our own spar Lean gate let
  sorries grow from 5 to 12 while green (spar#385). *Changed:* a correction list (#225, #227):
  seven items, two of them wrong on publication, including ISO 26262 Edition 3 already being at
  DIS.
- **[The machine arrived before the factory](@/blog/2026-10-21-the-machine-arrived-before-the-factory.md)**,
  21 Oct. *Expected:* measure the production system, not the people. *Found:* over 20 repos the
  feature share fell in 16 (p = 0.006) and coupling fell, the fix share rise was not
  significant; rivet's surfaces computed the same fact differently; at least 26 issue titles
  describe checks that pass without checking; open issues grew from 6 to 34 in rivet and 8 to
  67 in relay, mostly filed by the agents. *Changed:* the SAFe and orchestrator posts both
  restate that the decision-queue ratchet (#232) is merged and not armed; arming it is still
  open.
- **[Agents don't tidy up](@/blog/2026-10-22-agents-dont-tidy-up.md)**, 22 Oct. *Expected:* a
  baseline against projects written by people. *Found:* judged from diffs, Hubris and
  Cranelift refactor in 25 and 30% of commits, the agent projects in 3 to 13%; fix share,
  fix-on-fix, coupling and bug lifetime in commits do not separate the groups. A fix-hotspot
  trigger was pre-registered with spar as control. *Changed:* updated 28 Oct (#281): the
  trigger shipped (rivet#1133), the window is November 2026 to January 2027, and the classifier
  was re-scored after a model change; the first report is due 1 December.
- **[SAFe was built for slow humans](@/blog/2026-10-25-safe-was-built-for-slow-humans.md)**,
  25 Oct. *Expected:* argue that verification and decisions are the bottleneck, and that
  Kanban with gates should replace SAFe. *Found:* an argument, which its limits section says no
  controlled experiment backs. *Changed:* corrected 27 Oct (#260): the Harvard authors and
  findings, several quotes, the Faros figures, the ratchet's status, the CI gate's proven
  potency, and the claim that two terms were coined here; style pass 28 Oct (#266).
- **[Can we deliver X by January?](@/blog/2026-10-26-can-we-deliver-x-by-january.md)**, 26 Oct.
  *Expected:* answer date questions from gate status and flow history. *Found:* a real corpus of
  release cadence across seven repos, but no end-to-end durations, so the worked example is
  illustrative. *Changed:* corrected 27 Oct (#260, #261): the 80% confidence claim removed,
  arithmetic, issue counts and five citations fixed, jess relabelled as the integrator. An
  estimate built from measured durations: not yet revisited.
- **[The orchestrator](@/blog/2026-10-28-the-orchestrator-who-does-what.md)**, 28 Oct.
  *Expected:* write down who does what across jess, relay and gale. *Found:* four contracts
  taken from real issues; jess's pin guard caught two estimators exporting the same interface
  (jess#293), and relay stopped publishing one; `with-device` lets agents share one board; the
  warte views are still mostly open issues; I enforce the decision cap by hand. *Changed:* held
  and corrected before publication (#260, #261), own-chat quotes marked as edited (#269).
- **[Read ASPICE as a pattern](@/blog/2026-10-29-aspice-is-not-a-queue.md)**, 29 Oct,
  scheduled. *Expected:* a requirement is real when a check can fail against it and its result
  is recorded. *Found:* in gale, 302 of 329 software requirements have a check linked and none
  has a result; 25 marked `verified` by hand sit in releases rivet reports as cuttable; the
  instrument decides the count (485 by marker scan, 27 by link census). *Changed:* hardware
  wording fixed 28 Oct (#281). The tagline gate's comment in `claims.yaml` cites this
  measurement.
- **[The scarce resource is the orchestrator's attention](@/blog/2026-10-30-the-scarce-resource-is-attention.md)**,
  30 Oct, scheduled. *Expected:* ration my attention across about 22 parallel sessions.
  *Found:* a decision inbox (plugin 0.44.0), an attention budget capping routine asks at three
  flows with decision windows (0.45.0), and PR admission (0.43.0); nothing measured yet and no
  baseline. The criterion is stated first: the oldest open decision under 48 hours at every
  weekly reading. *Changed:* nothing yet; a follow-up is due around 25 November.
- **[Trust at machine speed](@/blog/2026-11-02-trust-at-machine-speed.md)**, 2 Nov, scheduled.
  *Expected:* trust is an advantage only when a machine can check it. *Found:* claims checked in
  CI, gale's links without results, and a witness release archive whose keyless signature I
  checked with cosign without our key, where one appended byte made the check fail; it shows
  origin, not correctness. Agent workflows audited 28 Oct, one finding fixed, further fixes in
  progress. *Changed:* nothing yet.
- **[Eight ways we could be wrong](@/blog/2026-11-05-eight-ways-we-could-be-wrong.md)**, 5 Nov,
  scheduled. *Expected:* the eight strongest objections, each dated, with what would make me
  concede. *Found:* one stronger since April (agents as an attack surface), one weaker (WASI
  0.3.0 released), one conceded outright (our gates do not run on our own engine, #287).
  *Changed:* objection 3 revised before publication (#293): the MISRA study measured one-shot
  generation, not an agent with a checker in its loop, and that experiment is filed (#292).

## Not yet revisited, in one place

The claims above that no correction or later post has dealt with, oldest first: the roundups
promised in *Hello, World*; meld's statement that no embedded runtime supports the Component
Model natively; rivet's Kani proofs and Verus specs on core data structures, and its footer's
"transpiles"; the "orders of magnitude" effort drop; sigil's SLSA L4 sentence; `spar-codegen`
driving the build; the "weeks of human review" estimate; "no LLM hallucinations"; the "strictly
less" MC/DC effort; LTO's Renode numbers under a "real hardware" method and its missing fourth
variant; example-kvs's stub gate; the "verified OS" title; the composed sine and cosine bound
with argument reduction; arming the decision ratchet; and an estimate from measured durations.

## What changed in how I work

- **From claims to measured statements.** March reported "100% coverage". October reports
  "302 of 329 linked, 0 results, at commit `463b3a3` on 26 October", and says which instrument
  produced the number and what it cannot see.
- **Corrections in public, in the post.** Dated notes at the foot of seven posts, a
  corrections section in the 14 Oct post that states the facts rather than the drafting
  history (#225), and the overdoing table recounted even where the count went up.
- **Publish what is not proven, and the negative result.** The ulp post named its open layer
  and the next one closed it; the LTO post led with the wrong prediction; the failed timestamp
  workaround was reported the same day.
- **A check counts only if it can fail.** The Gappa and Coq-Interval bounds were tested for
  teeth, the spar Lean gate that stayed green on 12 sorries was replaced, the `gate-potency`
  audit arrived in August, and on 28 October a claim was broken on purpose and `claim-check.py`
  exited 1.
- **Pre-register before changing the process.** The hotspot trigger's criteria and control
  were fixed on 22 October before the trigger existed, and the attention budget states its
  48-hour criterion before the first reading.
- **A review gate before publishing.** After the 25 to 27 October corrections, a cold,
  role-split panel runs before `ready = true` (#265), and a review used as evidence must record
  its model, context, commit and outcome (#275).
- **My attention is the budget.** Asks go to an inbox with a cap and windows instead of
  arriving in the chat, and the decision queue, not agent runtime, is the queue to limit.
