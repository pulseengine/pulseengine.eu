+++
title = "What comes after test suites"
description = "AI agents can complete person-years of software work if test suites close the feedback loop. In safety-critical systems, test suites are necessary but not sufficient. Here is the verification stack I built to close the gap."
date = 2026-04-07
[taxonomies]
tags = ["verification", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
Greenblatt showed that AI excels when verification is cheap — build a test suite, iterate, ship. Beck and Fowler warn that quality is getting dropped. Both are right. In regulated domains, both problems compound: more code needs more verification, and test suites do not satisfy the standards. The question is not whether AI can write the code. It is whether you can prove the code is correct after AI wrote it.
{% end %}

## Two articles in one week

Ryan Greenblatt at Redwood Research [published data](https://blog.redwoodresearch.org/p/ais-can-now-often-do-massive-easy) showing AI completing software projects equivalent to 3–30 person-years of human effort. The mechanism is simple: the AI builds a test suite, iterates against it, catches its own mistakes. He calls these "easy-and-cheap-to-verify" tasks. On these tasks, AI performance is 20–100x better than on tasks where verification is expensive. The gap is larger than anyone expected.

The same week, Kent Beck and Martin Fowler [spoke at the Pragmatic Summit](https://newsletter.pragmaticengineer.com/). Beck called AI "an amplifier" — the circular saw for carpenters. Fowler said every business is optimizing for speed while quality gets dropped. Beck added that the periodic "let's get rid of programmers" trend is back.

I read both pieces over the weekend. I work on safety-critical automotive systems, and both observations land differently here.

## The gap

A test suite proves that code does the right thing for the inputs you tested. A formal proof proves it does the right thing for all inputs. Different claims.

Safety standards go further than test coverage. ISO 26262 highly recommends formal verification methods for ASIL-D and requires verification of the absence of unintended functionality. DO-178C Level A requires MC/DC structural coverage; its supplement [DO-333](https://visuresolutions.com/do-178-guide/do-333/) defines how formal methods can complement — and in some cases replace — certain testing activities, though the conditions are specific. IEC 61508 marks formal methods as "highly recommended" for SIL 3 and SIL 4 in its technique tables.

Greenblatt acknowledges the limits. He notes that AI produces "low quality" code, has "quite bad taste and judgment," and considers work done prematurely. His answer: human oversight, "15 minutes of tips every so often."

In regulated domains, 15 minutes of tips does not produce an audit trail.

When AI agents produce code at the velocity he describes, the verification surface does not shrink. It grows. More code, more interfaces, more places where test coverage is not the whole story.

## What I have been doing

I spent the past year building verification tooling for WebAssembly components in safety-critical systems — the [PulseEngine](/) toolchain. I did not set out to build a response to Greenblatt. I set out to build what I needed. But reading his article, I realized the work maps directly to the gap he describes.

### Proving kernel code correct

[gale](https://github.com/pulseengine/gale) is a Rust port of Zephyr RTOS kernel primitives — semaphores, mutexes, message queues, scheduler, memory slabs, pipes, the full surface — targeting ASIL-D. 39 modules covering the complete Zephyr kernel API. Every public function carries a contract: preconditions (`requires`), postconditions (`ensures`), and an invariant that every operation must preserve.

The verification is not one technique. It is layers:

- **[Verus](https://github.com/verus-lang/verus)** (SMT/Z3) — all modules verified, hundreds of properties. Exhaustive check across all inputs. An agent writes the annotation, Z3 discharges the proof or reports a counterexample.
- **[Rocq](https://rocq-prover.org/)** (theorem prover) — abstract invariant proofs over mathematical models. Zero admitted lemmas. These reason about the algebra of the primitives, not the Rust implementation directly.
- **[Lean 4](https://lean-lang.org/)** — mathematical proofs for scheduling theory: rate-monotonic analysis, priority ceiling protocol, priority queue ordering. The math that underpins the implementation.
- **[Kani](https://model-checking.github.io/kani/)** — bounded model checking harnesses. Exhaustive state space exploration within finite bounds.
- **Hundreds of runtime tests** — cargo test on the stripped (non-Verus) code.
- **Zephyr upstream test suites** on QEMU and Renode-emulated boards (Cortex-M3, M4F, M33, R5).
- **Proptest** — property-based testing with random operation sequences.
- **Fuzz testing** — coverage-guided mutation.
- **Miri** — undefined behavior detection.
- **Differential testing** — POSIX and FreeRTOS reference models validate specification independence.

AI agents write both the implementation and the proof annotations. The solvers and tests check them. I wrote about the details — and what still does not work — in [Formal verification just became practical](/blog/formal-verification-ai-agents/).

### Tracing from architecture to evidence

When an agent produces code, someone has to answer: which requirement does this satisfy? Which test covers it? Which architecture decision drove it?

[rivet](https://github.com/pulseengine/rivet) validates that chain on every commit. It ships with 15 safety standard schemas — STPA, ASPICE, IEC 61508, IEC 62304, DO-178C, EN 50128, EU AI Act — so the structure is there from the start, not configured after the fact. An [MCP server](https://modelcontextprotocol.io/) exposes rivet to AI agents, so the traceability chain stays current as agents work. Currently: 447 artifacts across 19 types, 100% coverage, zero warnings.

[spar](https://github.com/pulseengine/spar) parses AADL and SysML v2 architecture models and feeds them into the same traceability graph. Requirements trace not just to code and tests but upstream to architecture decisions — component allocation, timing budgets, interface contracts. spar hit v0.6.0 last week with modal filtering and per-system-of-models analysis.

Formal verification of rivet's own core data structures — Verus specs and Kani proofs — is planned but not yet implemented. More in [rivet: because AI agents don't remember why](/blog/rivet-v0-1-0/).

### Signing what agents build

[sigil](https://github.com/pulseengine/sigil) embeds cryptographic signatures inside WebAssembly modules. Verification works offline — no registry, no network. This matters for embedded systems and air-gapped environments where you cannot call out to a signing authority at verification time.

The signing chain covers Sigstore keyless signing (OIDC → Fulcio → Rekor), SLSA L4 provenance predicates, and transformation attestations — so each step from source through fusion through optimization to binary is signed independently. Post-quantum signature support (SLH-DSA / FIPS 205) is in progress.

### Keeping governance at velocity

[temper](https://github.com/pulseengine/temper) is a GitHub App that enforces branch protection, signed commits, CI attestation, and Dependabot configuration across 30+ repositories automatically. When a new repository is created, it inherits the full policy within seconds. Beck warns about the "re-soloing" of programming. Fair enough — but governance has to hold regardless of team size.

### Hermetic builds with proof integration

[rules_wasm_component](https://github.com/pulseengine/rules_wasm_component) (v1.0, 439+ merged PRs) builds WebAssembly components across Rust, Go, C++, and TypeScript in Bazel. Three Bazel rule sets — [rules_verus](https://github.com/pulseengine/rules_verus), [rules_rocq_rust](https://github.com/pulseengine/rules_rocq_rust), [rules_lean](https://github.com/pulseengine/rules_lean) — integrate formal proofs into the build. `bazel test //...` runs all proof tracks, all tests, all verification in one command. No local tool installation. Hermetic and reproducible.

## Where he is right

I do not disagree with Greenblatt. The data is compelling.

[kiln](https://github.com/pulseengine/kiln), our WebAssembly runtime, is a direct example of what he describes. Clear external spec: the WebAssembly test suite. Tight feedback loop: run the tests, count the failures, fix them. We went from hundreds of failures to 36 remaining. This is exactly the kind of task where AI is very good.

He is also right about taste. Architectural decisions — which components to fuse, which properties to verify, which standards to trace against — still require a person who understands the domain. The agents execute. The solvers check. But someone has to decide what "correct" means.

## What the framework does not cover

Three things that matter in my world.

**Test suites are not specifications.** When Greenblatt writes "you can get the AI to develop a test suite and then it can spend huge amounts of time optimizing against it," that works well for general software. In safety-critical systems, passing a test suite is evidence — necessary, but not the whole argument. The specification is the requirement. Formal proofs verify the specification across all inputs, not a sample. The distinction matters when an assessor asks what you have actually demonstrated.

**Provenance.** If agents produce person-years of code, the audit trail is not something you add later. Which agent produced this? Which model? What was the input? Which architecture decision drove the requirement that drove the code? In regulated domains, you cannot ship what you cannot trace — from architecture model through requirement through proof through signed binary. That is what rivet, spar, and sigil do together.

**Governance at velocity.** Fowler asks whether we get "more effective two-pizza teams" or "one-pizza teams because agents don't eat pizza." Good question. In safety-critical systems, team size does not change the governance requirements. ISO 26262 requires configuration management whether one person or fifty wrote the code. Without automation, governance drifts the moment AI velocity kicks in.

## Honestly

This stack is not complete. I want to be clear about that.

Formal proofs cover functional correctness. Timing behavior — latency, deadlines, scheduling — is a different problem. spar's AADL analysis captures timing properties at the architecture level, but end-to-end timing verification from model to running code is not solved yet. The Rust subset that all three proof systems accept simultaneously is restrictive — no trait objects, no closures in proof context. Specification completeness still needs human review. No assessor has evaluated this specific combination of proof systems in a certification audit.

Community adoption is early. These tools are used in one organization. Mine.

But the direction is clear. Greenblatt estimates ~30% probability of full AI R&D automation by end of 2028. Whether or not that timeline holds, the verification gap widens as velocity increases. Test suites alone will not close it.

The infrastructure has to exist before the velocity makes it impossible to retrofit.

---

*[PulseEngine](/) is a formally verified WebAssembly Component Model engine for safety-critical systems. Code at [github.com/pulseengine](https://github.com/pulseengine). All tools are open source under Apache-2.0 or MIT.*
