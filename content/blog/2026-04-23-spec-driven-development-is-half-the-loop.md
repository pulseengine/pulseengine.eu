+++
title = "Spec-driven development is half the loop"
description = "Spec-driven development compresses the software lifecycle to spec → plan → implement, with a QA-lens agent at the end. That agent is a soft oracle. We replaced it twice — once for finding bugs in code, once for closing gaps in the audit graph — using the same oracle-gated parallel-agent scaffold that Anthropic's red team used for their Claude Mythos preview. Here is the pattern, our two applications, and why it is the half SDD does not ship."
date = 2026-04-23
[taxonomies]
tags = ["verification", "process", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
Spec-driven development sells the intent half of the loop — agents against structured specs. The verification half it ships with is an agent reading the spec back. That is a soft oracle; it cannot find what the spec did not mention, and it cannot resist the politeness drift of long LLM conversations. We replaced it twice in sigil this month, both times with the same pattern: minimal prompt + strong mechanical oracle + parallel agents + fresh-session validator. Anthropic's red team uses the same shape as the scaffold for their vulnerability research — most recently showcased with Claude Mythos, a new model, but the scaffold predates it. We apply it to bug hunting and to V-model traceability gaps. SDD plus an oracle-gated verification phase downstream is a loop. SDD alone is half of one.
{% end %}

## The pattern

The shape does not have a clean industry name. Descriptively: *oracle-gated parallel agents*. Anthropic's red team uses it as the scaffold for their vulnerability-finding research[^mythos-preview]. Their own phrasing is a *"simple agentic scaffold"* that runs across multiple of their publications — the model changes, the scaffold holds. The four ingredients:

1. **Minimal prompt.** The agent gets a narrow task and the artifact under investigation. Not instructions.
2. **Strong mechanical oracle.** A check the agent cannot hallucinate its way around — a failing PoC test, a fuzzer crash, a type error, a proof obligation, a `rivet validate` diagnostic. The oracle either fires or it does not.
3. **Parallel agents.** Many in parallel, each narrow, each independent. Diversity of candidate resolutions matters more than depth per agent.
4. **Fresh-session validator.** A separate agent with no stake in the proposal re-runs the oracle before any change lands.

The April 2026 Claude Mythos Preview used this scaffold to produce working exploits for a 27-year-old OpenBSD SACK vulnerability, a 16-year-old FFmpeg H.264 codec bug, CVE-2026-4747 in FreeBSD NFS, multiple Linux kernel privilege-escalation chains, and several browser-JIT heap-spray techniques — thousands of further findings still under responsible disclosure[^mythos-preview]. The model matters; independent reproductions with smaller open-weights models have landed similar findings on the same scaffold[^mythos-decoder], which is how you know the scaffold is doing much of the work.

The shape of one pipeline pass:

{% mermaid() %}
flowchart LR
    subgraph rank["rank.md"]
        r["score and<br/>prioritize candidates"]
    end
    subgraph discover["discover.md · parallel"]
        direction TB
        a1["agent 1"]
        a2["agent 2"]
        aN["agent N"]
    end
    oracle["mechanical oracle<br/>must fire<br/>(PoC · Kani · rivet validate<br/>fuzzer · sanitizer · CodeQL)"]
    subgraph validate["validate.md · fresh session"]
        v["re-run oracle<br/>independently"]
    end
    subgraph emit["emit.md"]
        e["draft artifact or<br/>link command"]
    end

    rank --> discover --> oracle --> validate --> emit

    classDef phase fill:#13161f,stroke:#3d4258,color:#8b90a0;
    classDef node fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef gate fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef good fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;

    class rank,discover,validate,emit phase;
    class r,a1,a2,aN,v node;
    class oracle gate;
    class e good;
{% end %}

The amber box is the hard part. Everything before it is hypothesis generation; the oracle is the first thing that has to say yes. SDD's QA-lens agent sits in the same position — but it is a second LLM with no mechanical check behind it, so the gate is soft. A soft oracle cannot find what the specification did not think to say, and bug classes are almost by definition what the specification did not think to say.

## Our two applications

We run two oracle-gated pipelines in [sigil](https://github.com/pulseengine/sigil), against two different oracle types. Both live in the repo as four-file prompt pipelines: `rank.md` → `discover.md` → `validate.md` → `emit.md`.

| Pipeline | Oracle | Finds | First real output |
|---|---|---|---|
| [`scripts/mythos/`](https://github.com/pulseengine/sigil/tree/main/scripts/mythos) | failing PoC test + Kani harness | bug classes in code | [PR #87](https://github.com/pulseengine/sigil/pull/87) — silently-swallowed `cert_count` parse error |
| [`scripts/vmodel/`](https://github.com/pulseengine/sigil/tree/main/scripts/vmodel) | `rivet validate` diagnostics | gaps in the audit graph | [PR #90](https://github.com/pulseengine/sigil/pull/90) — 9 of 12 sigil-local errors closed in one cycle |

**[`scripts/mythos/`](https://github.com/pulseengine/sigil/tree/main/scripts/mythos) — bug hunting against code.** The oracle is a failing PoC test plus, where tractable, a failing Kani harness. `rank.md` scores hypotheses across the codebase; `discover.md` runs one agent per hypothesis in parallel with a minimal prompt; `validate.md` re-runs the oracle in a fresh session with no context from the proposal; `emit.md` produces the draft artifact only if the oracle fires and the validator agrees. First real output: [PR #87](https://github.com/pulseengine/sigil/pull/87) — a malformed `cert_count` in a signature section's chain block was being silently swallowed into `None` by `if let Ok(...)`, masking bitstream corruption. The regression test is the oracle; it would now fail without the fix.

**[`scripts/vmodel/`](https://github.com/pulseengine/sigil/tree/main/scripts/vmodel) — traceability gap hunting against the audit graph.** The oracle is `rivet validate` — our own traceability validator that knows requirement ↔ design ↔ code ↔ test ↔ proof links by schema. Same four-file shape; different oracle. An agent cannot hallucinate a closure, because the validator either still reports the gap or it does not. First real output: [PR #90](https://github.com/pulseengine/sigil/pull/90) closed 9 of 12 sigil-local `rivet validate` errors — 75% in one cycle. The remaining three are a schema fix, not a gap.

The point of showing both is that the oracle is interchangeable. Any mechanical check your domain produces — tests, fuzzers, sanitizers, Semgrep, CodeQL, a model checker, `rivet validate`, a differential run — can be the oracle. The discipline is the same.

## Why this is the half SDD does not ship

SDD owns the intent axis: *what should be built.* Oracle-gated agent work owns the verification axis: *did it work, is it safe, is the audit trail complete.* They are orthogonal. You can run Spec Kit or Kiro on the front end — their structured intent document is a useful front-end — and put oracle-gated pipelines downstream of `/implement`. What you cannot do is let the QA-lens agent be the only verification and pretend you have the loop.

Clay Nelson put the compliance-grade version of this argument into one sentence at GitHub Shift: Automotive[^nelson-medium]:

> *"You cannot attest to what you did not observe."*

The mechanical oracle is the instrument that produces the observation. A QA-lens agent reading a spec is a second opinion, not an instrument. Auditors and attackers do not accept second opinions — and the security ecosystem has built most of the instruments you need already (OSS-Fuzz, cargo-fuzz, ASAN/TSAN/Miri, Semgrep, CodeQL, OSV, GHSA, Sigstore, SLSA[^sigstore-slsa]). What is missing is the *plumbing*: running them in parallel, under the oracle-gated discipline, with a fresh-session validator before anything lands.

There is a third half worth naming but not dwelling on — the iteration phase where a ticket turns into a real specification. Kent Beck keeps pointing at this[^beck-pragmatic]: *"you learn things during implementation that change what the spec should say."* SDD tools present that as done; it rarely is. Oracle-gated agent pipelines do not address this gap — they address the verification gap. Worth being explicit about what each pattern solves.

## The tools around it

**[rivet](https://github.com/pulseengine/rivet)** — our traceability graph validator. Ships with schemas for STPA-Sec, cybersecurity, IEC 61508, IEC 62304, DO-178C, EN 50128, ASPICE, EU AI Act. `rivet validate` is the oracle for the V-model pipeline. The `rivet query --sexpr` DSL lets agents enumerate gap candidates without LLM hallucination. Both exposed to agents through an MCP server so the trail stays current as they work. More in [rivet: because AI agents don't remember why](/blog/rivet-v0-1-0/). *(Adjacent prior art worth acknowledging on the requirements side: useblocks' [Sphinx-Needs](https://useblocks.com/products/sphinx-needs) and [ubCode](https://useblocks.com/products/ubcode) — battle-tested MCP-exposed structured requirements in automotive.)*

**[spar](https://github.com/pulseengine/spar)** — our AADL v2.3 architecture toolchain, shipping at v0.6.0. 27+ analysis passes (scheduling, latency, ARINC 653 partitioning, EMV2 fault trees, memory budgets), a deployment solver with ASIL decomposition and SIL/DAL integrity constraints, a declarative assertion engine, LSP support, and a WASM component build. In the pipe: `spar-codegen` emits Cargo.toml and BUILD.bazel directly from the AADL model (the moment the architecture stops being a parallel drawing and starts being what the build reads), a SysML v2 parser for the requirements side of the roundtrip, a JSON CLI adapter so rivet can consume spar analysis results, and an MCP server so agents call spar for architecture review the same way they call rivet for traceability.

**[sigil](https://github.com/pulseengine/sigil)** — in-module cryptographic signing. Sigstore keyless, SLSA L4 predicates, per-transformation attestations. This is what operationalizes Clay Nelson's *cannot attest to what you did not observe* end-to-end: each build transformation produces signed evidence or it does not.

**Spec Kit / Kiro / Tessl** — fine front-ends for `/specify`. The minimum we expect them to emit into our loop is a draft rivet requirement: title, description, acceptance criteria structured enough that rivet's schema can validate them, and a parent architecture or requirement link. Anything less is a prose ticket in a different file.

None of these alone closes the loop. Together — the MBSE layer (spar for architecture, rivet for requirements and traceability), oracle-gated agents against a mechanical check, sigil-signed build output — they are the shape of an AI-assisted loop that produces an audit trail a regulator or an attacker cannot dismiss.

## How do you make an AI follow the V-model?

Someone asked me this the first time I showed them rivet, and it is the right question. The answer is that the question misstates the problem. You do not make the agent follow the V-model through instructions. You make the tools *require* V-model shape, and the agent responds to the errors the tools produce. It is the difference between *"please follow the rules"* and *"the door is locked until you follow the rules."* Only the second works on LLMs.

The shape of the flow, assuming a GitHub issue or Jira ticket as the starting point — the same structure holds for either:

{% mermaid() %}
flowchart LR
    issue([issue · ticket])
    req["requirement<br/>rivet validate"]
    design["design<br/>rivet validate"]
    impl["implement<br/>scripts/mythos<br/>failing-test oracle"]
    unit["unit tests<br/>test pass"]
    integ["integration<br/>rivet validate<br/>verified-by links"]
    signed([sigil-signed<br/>attestation bundle])

    issue --> req --> design --> impl --> unit --> integ --> signed

    req -.verified-by.-> integ
    design -.verified-by.-> unit

    classDef start fill:#13161f,stroke:#4a5068,color:#e1e4ed;
    classDef node fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef gate fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef good fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;

    class issue start;
    class req,design,unit,integ node;
    class impl gate;
    class signed good;
{% end %}

The dotted lines are the V-model's symmetry made concrete: the requirement is *verified-by* the integration result; the design is *verified-by* the unit tests. `rivet validate` checks both directions. The six-step walk-through:

1. **The issue is already the spec.** Description, acceptance criteria, linked design doc if you have one. You do not re-type this into a Spec Kit markdown form; you use the issue as the input to step 2.

2. **Iterate into a rivet requirement.** An agent drafts the structured artifact from the issue text (status, description, safety goal, verification-method, parent architecture element). `rivet validate` runs and complains about missing fields. Each complaint is the next prompt. This is the iteration phase — not a separate ceremony, just a tight loop between the agent, the human reviewing the draft, and the schema. Beck's *"you learn things during implementation that change what the spec should say"* happens here, with the schema as the teacher.

3. **Descend the left side of the V.** `rivet validate` now reports: this requirement has no linked design, no linked test plan, no risk analysis, no allocated component. Each report is an ERROR. The [`scripts/vmodel/`](https://github.com/pulseengine/sigil/tree/main/scripts/vmodel) pipeline picks those up: `discover.md` proposes closures in parallel (one agent per gap), `validate.md` re-runs `rivet validate` in a fresh session, `emit.md` produces either a `rivet link` command (if the target artifact exists) or a draft artifact for human review (if it does not). No LLM narrative in the loop — just the validator's diagnostic and the agent's proposed closure.

4. **Implement with the test as oracle.** The tests that fell out of step 3 are now the mechanical oracle. [`scripts/mythos/`](https://github.com/pulseengine/sigil/tree/main/scripts/mythos) pattern: minimal prompt, the failing test, parallel agents for different sub-tasks, fresh-session validator that re-runs the test before anything merges. If you want stronger evidence, a Kani harness or a Verus contract on top of the test.

5. **Ascend the right side.** `rivet validate` gates again. Every requirement now needs a `verified-by` link to a passing test; every code change needs an `implements` link to the design; every test needs a `verifies` link back to a requirement. The agent either adds the link (because the artifact exists) or flags the gap (because it does not). The ascent is not a ritual; it is a graph-completion task with the validator as oracle.

6. **Sign and merge.** `sigil` attaches signed evidence to each transformation — source commit, Bazel build, test pass, `rivet validate` zero-errors, Kani harness result if present. The PR carries the attestation bundle. Clay Nelson's *"cannot attest to what you did not observe"* becomes "observed and signed at each step." Audit trail complete.

At no point does anyone tell the agent *"follow the V-model."* The agent responds to `rivet validate` errors. That is what *"the tools require V-model shape"* means in practice — and it is why the V-model survives AI velocity instead of being eroded by it.

If you prefer Spec Kit or Kiro as the front-end for step 1 or 2, that slots in cleanly: use `/specify` to produce the draft rivet requirement rather than writing one directly. The oracle-gated steps 3–6 do not change. Front-end choice is a matter of taste; the mechanical floor is what makes the agent's output attestable.

## MBSE, mandatory now

Model-Based Systems Engineering has a reputation. For two decades it was sold as the future — SysML, AADL, Capella, Papyrus, executable architecture, traceable models from requirements to deployment — and most of us said no. The tooling was heavy. The models drifted from code within weeks. The cost-benefit did not pencil for anything short of aerospace.

Two things shifted, both for the same reason: AI agents.

First, on the cost side, authoring the model stopped being the bottleneck. A structured requirement block that used to take half a day of an engineer's time to write, review, and link now takes a few agent-minutes plus a human review of the draft. The drift problem shrinks for the same reason — maintaining the model as a first-class artifact stops being free labor nobody signed up for and starts being another loop the agent closes against the schema oracle. This is the same economic shift I argued for formal verification in [Formal verification just became practical](/blog/formal-verification-ai-agents/); it lands on MBSE for the same reasons.

Second, and more load-bearing, in a world where the agent produces most of the code, *how do you prove what was produced*? The answer cannot be *"we trust the agent"* and cannot be *"our QA-lens agent reviewed the output."* Both are soft oracles. The answer has to be a model — a structured, machine-readable description of the intended system — against which the built system is mechanically checked. That is MBSE renamed for AI velocity.

And the model has to *drive* the build, not sit alongside it. Audit-only models drift and get skipped under pressure. Models that actually select cargo features, emit build files, or configure hardware cannot be skipped, because the build depends on them:

{% mermaid() %}
flowchart LR
    subgraph mbse["MBSE layer"]
        direction TB
        spar["spar<br/>AADL architecture"]
        rivet["rivet<br/>requirements · variants · links"]
    end

    codegen["spar-codegen<br/>Cargo.toml · BUILD.bazel<br/>#[aadl] attributes"]
    build[compiled binary]
    validate[rivet validate]
    attest([sigil attestation bundle])

    mbse -->|drives| codegen
    mbse -->|gates| validate
    codegen --> build
    build --> attest
    validate --> attest

    classDef phase fill:#13161f,stroke:#3d4258,color:#8b90a0;
    classDef model fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef step fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef good fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;

    class mbse phase;
    class spar,rivet model;
    class codegen,build,validate step;
    class attest good;
{% end %}

Two concrete beats from our own stack: [spar](https://github.com/pulseengine/spar) already ships deployment allocation with ASIL decomposition and ARINC 653 partitioning — the integrity-level constraints are first-class in the solver, not bolted-on checks. Next on the roadmap, `spar-codegen` emits Cargo.toml and BUILD.bazel directly from the AADL model, with `#[aadl(period = ...)]` attributes tying Rust functions to the architecture elements they implement. The moment that lands, you cannot produce a binary without the model, because the build files are the model's output. rivet's variant artifacts do the symmetric thing on the requirements side — selecting which requirement set applies at which integrity level, gated by `rivet validate`. `sigil` signs the bundle only when all three layers — architecture, requirements, build — agree. The model is no longer a parallel document. It is the source of truth the build depends on, and that dependency is what makes skipping it impossible rather than merely discouraged.

Where *"mandatory"* cuts: not every internal CRUD app needs MBSE. The line is systems with safety regulation, systems facing external auditors, and high-blast-radius infrastructure — cryptographic components, OS kernels, signing tools, language-model infrastructure with reach into hundreds of downstream systems. The common denominator is *"if this fails, the failure is not locally contained."* For those systems, the "too heavy" argument against MBSE stops holding; the alternative is shipping AI-authored code with no answer to how-do-you-prove.

In the past the argument was *"we can't do MBSE, it's too heavy for our pace."* For any system that needs to be proven, that argument is over. The new argument is the inverse: if you want an attestable trail from the agent's input to the agent's output, a model is how you get it. Otherwise — how do you prove?

## Limits, migration, and where to start

The post argues for a pattern; here is what would stop me from over-pitching it.

**The oracle has to exist.** The pattern works where the check is mechanical — tests, fuzzers, proof obligations, `rivet validate`, schema diagnostics, `sigil` verify. On domains with blurry correctness signals — performance regressions, UX quality, business-logic smells — there is no crisp oracle and this pattern does not close the loop. Performance has proxies (criterion benchmarks as the oracle for no-regression); UX and product sense do not. Admit it before anyone has to point it out.

**The oracle can be wrong.** If a Verus contract encodes an incorrect postcondition, or a rivet schema rule fires for the wrong reason, the pipeline confidently enforces the wrong behaviour. Three countermeasures, all already in our stack: (1) multiple independent oracles on the same property — Verus + Kani + property tests discharge the same claim by different techniques, and a bug in any one is revealed by disagreement with the other two; (2) mutation testing (cargo-mutants) catches tautological oracles — if mutating the code does not fail the test, the test was not a real oracle; (3) counter-examples force re-examination of the oracle, not just the code. When Kani reports a failing execution, the right move is to read the trace and ask *"is my property wrong?"* before asking *"is my code wrong?"*

**Signed is not the same as safe.** This is the attestation-illiteracy risk — management or auditors reading a `sigil` bundle and hearing *"safe."* The bundle claims only what was observed: *this commit's Verus proof discharged, these Kani harnesses ran to completion, `rivet validate` reported zero errors against these schema versions*. It does not claim the deployed binary is correct, that the proof obligations were the right ones, or that the schemas captured the right properties. The way to avoid the confusion is to name what the attestation *does not* cover inside the attestation itself — versions of each oracle, scope of the proof, schema revisions, explicitly excluded failure modes.

**Brownfield does not mean stop-the-world.** If you already have Jira or DOORS requirements, rivet reads those (or you script the import once) and starts producing diagnostics the next day — no new authoring required beyond filling the schema gaps rivet surfaces. spar is a bigger ask, so earn its place: introduce it where an AADL or SysML model already exists, or where the architecture analysis pays for itself (scheduling feasibility, ARINC 653 isolation, deployment allocation). sigil is additive — it layers onto whatever CI you have.

**If you can only start with one, start with rivet.** It is the oracle, it works standalone, and it produces diagnostics on day one against whatever requirement set you already have. spar earns its place when an architecture model exists or is worth building. sigil is the easiest to add late, because its output format is orthogonal to the rest of the pipeline.

## Take-away

- SDD is useful at the front. Put oracle-gated parallel agents downstream. The QA-lens agent is not the verification.
- The oracle is the part that matters. Any mechanical check your domain produces works — tests, fuzzers, proofs, `rivet validate`, Semgrep, CodeQL. Pick one, gate on it, fresh-session-validate before merging.
- Parallel is the trick. Diversity of candidate resolutions beats depth per agent.
- Make the model essential to the build, not parallel to it. If spar-codegen emits your Cargo.toml and rivet variants select your cargo features, nobody can skip the MBSE layer.
- The audit trail is the product. Ticket → iteration → model → oracle-gated build → signed artifact. MBSE is mandatory now for anything that has to be proven — not because the process team asked for it, but because that is the only way to answer "how do you prove?"

We published the four-prompt pipeline skeletons in `scripts/mythos/` and `scripts/vmodel/`. The `mythos` directory is a deliberate homage to the Anthropic preview that put this scaffold in the public eye — the pattern is what we ran, the name of the model is what made it newsworthy. Copy, adapt the oracle for your domain, run. The discipline transfers; the tooling transfers through open Skills primitives that Claude Code, Cursor, Codex CLI, and Copilot all consume.

---

## Sources

[^mythos-preview]: Anthropic — *Claude Mythos Preview.* Red-team research publication, April 2026. [red.anthropic.com/2026/mythos-preview](https://red.anthropic.com/2026/mythos-preview/). Primary (Anthropic publication). *Mythos* is a new general-purpose Claude model, not a methodology; the preview describes the "simple agentic scaffold" used across Anthropic's prior vulnerability-finding work and the specific bugs this model produced exploits for (OpenBSD SACK, FFmpeg H.264, FreeBSD NFS, Linux kernel privesc chains, browser JITs). The scaffold is what this post calls the pattern; the model is what made the 2026 results newsworthy.

[^mythos-decoder]: *The myth of Claude Mythos crumbles as small open models hunt the same cybersecurity bugs Anthropic showcased*. The Decoder, 2026. [the-decoder.com](https://the-decoder.com/the-myth-of-claude-mythos-crumbles-as-small-open-models-hunt-the-same-cybersecurity-bugs-anthropic-showcased/). Secondary (journalism; reports reproduction of Anthropic's scaffold results with smaller open-weights models).

[^nelson-medium]: Clay Nelson — *Automotive's AI problem isn't speed, it's proof.* Medium, April 2026. [medium.com/@claynelson](https://medium.com/@claynelson/automotives-ai-problem-isn-t-speed-it-s-proof-15a1d3cc9cee). Primary (author's own publication). Source of the *"you cannot attest to what you did not observe"* line delivered at GitHub Shift: Automotive in Frankfurt.

[^sigstore-slsa]: [Sigstore](https://www.sigstore.dev/) — keyless signing, Fulcio CA, Rekor transparency log. [SLSA](https://slsa.dev/) — Supply-chain Levels for Software Artifacts. Primary (specification project home pages). Both are the build-attestation and provenance machinery that makes Nelson's argument operationally concrete.

[^beck-pragmatic]: Kent Beck — *TDD, AI agents, and coding with Kent Beck.* The Pragmatic Engineer newsletter interview. [newsletter.pragmaticengineer.com](https://newsletter.pragmaticengineer.com/p/tdd-ai-agents-and-coding-with-kent). Secondary (interview).

---

*This post is part of [PulseEngine](/) — a formally verified WebAssembly Component Model engine for safety-critical systems. Prior posts in the arc: [Formal verification just became practical](/blog/formal-verification-ai-agents/), [What comes after test suites](/blog/what-comes-after-test-suites/), [rivet v0.1.0](/blog/rivet-v0-1-0/).*
