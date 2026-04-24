+++
title = "MC/DC for AI-authored Rust is tractable — the variant-pruning argument"
description = "The received wisdom is that Rust's pattern matching makes MC/DC harder than C. Under variant-managed AI-authored code, the opposite is true. Five layers of variant pruning, one oracle per layer, and a certification burden proportional to the single variant you ship — not the combinatorial product."
date = 2026-04-24
draft = true
[taxonomies]
tags = ["verification", "process", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
The received wisdom about MC/DC for Rust reads: *"pattern matching makes it harder than C."* That is only true if you look at the runtime-decision layer in isolation. Rust has at least five layers of variant-pruning machinery — requirements variants, cargo features, cfg attributes, the type system, and match arms. Each prunes what the next layer has to reason about. Composed end-to-end under rivet-style variant management, MC/DC-for-Rust is less burdensome at certification scale than MC/DC-for-C ever was. AI-velocity authorship tips the economics further in Rust's favour, not worse.
{% end %}

## The framing this post inverts

The Ferrous Systems ESA SW PA post[^ferrous-post] summarises the common framing in one paragraph:

> *"Rust has novel language features (such as pattern-matching) that don't map well to the existing MC/DC specifications, however a recent paper proposes a mapping that will allow the development of MC/DC tools for Rust in the future."*

The received reading is: MC/DC was designed for C's boolean decisions; Rust pattern matching does not decompose naturally into boolean decisions; Rust needs a new mapping before tools can even count coverage. Once the mapping lands, Rust's coverage burden will be "addressable" but presumably large.

The argument below is that the mapping is the least interesting part of the problem. Under multi-layer variant management — the kind a mature safety-critical product line already runs — the coverage *scope* at the decision layer shrinks multiplicatively with every layer above it. At scale, the burden becomes proportional to the single variant you ship, not to the combinatorial product across your feature matrix.

## Five layers of variant pruning

A Rust codebase has at least five distinct mechanisms for pruning the space of reachable decisions, stacked from design to execution:

| Layer | Mechanism | Prunes what | Timing |
|---|---|---|---|
| 1. Requirements | rivet variant artifact | Which requirement set applies to this build | Design |
| 2. Build | Cargo features (`[features]`) | Which crates and modules link | Configure |
| 3. Source | `#[cfg(feature = ...)]`, `#[cfg(target_os = ...)]`, `#[cfg(debug_assertions)]` | Which code is even parsed | Compile |
| 4. Type | Exhaustive match, `!` (never type), type-state, const generics, trait bounds | Which match arms and branches are reachable in principle | Type-check |
| 5. Runtime | Match arms, `if let`, `?` desugaring | Which decisions fire on a given input | Execute |

Each layer takes the variant space its predecessor produced and makes it smaller. Layer 1 selects a variant from the product family. Layer 2 translates that selection into feature toggles. Layer 3 elides entire blocks of source. Layer 4 closes gaps the source would otherwise leave open — Rust's exhaustive-match requirement and the never type remove whole classes of "unreachable but still counted" branches that C's MC/DC has to discharge by testing. Only what survives all four pruning steps ever reaches layer 5, where the Ferrous/DLR MC/DC mapping operates.

If the compilation target is WebAssembly — as it is for PulseEngine — layer 5 is even more tractable than the Ferrous/DLR framing makes it look. By the time the Wasm module exists, pattern matching has already lowered to `br_if` and `br_table`, the `?` operator has desugared, type-state has been resolved, and cfg branches have been elided from the emitted code. The decisions visible in the Wasm are already MC/DC-shaped — small, explicit, without the source-level syntax that makes pattern matching hard to map. An MC/DC tool at the Wasm level measures coverage against an instruction set with a machine-readable spec and a reference test suite, neither of which C or Rust has to the same degree; the tool-qualification argument moves in your favour. And the coverage report describes what actually ships, not a source-level abstraction that the compiler then rearranges.

## The multiplicative reduction

Call the fully-expanded MC/DC decision space of the union of all variants `N_max`. That is the number MC/DC-for-Rust would nominally have to discharge if you naively applied the Ferrous mapping to every possible cfg-expansion of every feature combination across every variant. It is large. It is also not what any single shipped artifact actually contains.

What the shipped artifact contains is a space of size:

> `N_shipped(V) = f_1(V) · f_2(V) · f_3(V) · f_4(V) · N_max`

where each `f_i(V) ∈ (0, 1]` represents the pruning fraction at layer `i` when variant `V` is selected. For a well-decomposed product line targeting, say, ASIL-D with a specific board and feature profile, every `f_i` is aggressive. The product is small.

**Certification is against the shipped artifact, not against the union.** You present the MC/DC report for variant V, not for every possible V. The combinatorial argument you sometimes hear — *"Rust MC/DC is impractical because the decision space is huge"* — is comparing `N_max` to what C MC/DC reports do per-configuration. That is not an apples-to-apples comparison.

Under variant management done properly, the apples-to-apples comparison is `N_shipped(V)` for Rust vs. the equivalent-configuration MC/DC space for C. On that comparison, Rust comes out ahead — because C's preprocessor-based cfg is structurally the same as Rust's, but C's type system does not provide layer-4 pruning.

## Why AI authorship makes this load-bearing

Variant-aware certification was historically hard for a practical reason: authoring the variant graph, the feature flags, the cfg discipline, and the per-variant test suite was expensive human work. Product-line engineering research has been on this problem for thirty years and the adoption story outside a few hold-out industries is mixed[^ple-lit].

AI-velocity authorship changes that calculus. The agent that writes the code also writes the variant graph, the cfg, the feature declarations, and the per-variant tests. What stops the output from being unattestable is the same thing that stops any AI output from being unattestable: a mechanical oracle at each layer. I made this argument for the pattern generally in [Spec-driven development is half the loop](/blog/spec-driven-development-is-half-the-loop/). Applied to the five-layer variant stack, the oracles are:

- **Layer 1** — `rivet validate` checks that each requirement has a variant, each variant has linked evidence, each evidence has a linked test. Today.
- **Layer 2** — `cargo metadata`, `cargo tree --edges features`, and per-variant CI matrices catch feature-combination rot. `cargo check --all-features` and its per-variant siblings run today.
- **Layer 3** — `rustc --cfg=... --emit=dep-info` resolves cfg-expansion at compile time. Tooling to report *which* cfg blocks were active in a build is simple to add if it is not already present.
- **Layer 4** — `rustc` itself is the oracle. `#![deny(warnings)]`, `clippy`, exhaustive-match enforcement, and type-state discipline are all mechanical and already run.
- **Layer 5** — the Ferrous/DLR MC/DC tooling will be the oracle once it lands. The mapping paper[^ferrous-paper] is the theoretical work; a qualified tool is the engineering work tracked in the 2026 Rust Project Goal[^rust-project-goal].

Each layer's failure is a diagnostic, not an opinion. Each diagnostic is something an agent can act on without human interpretation. The same oracle-gated scaffold discipline that works for bug hunting and for V-model gap closure works here.

## With our stack, concretely

- **rivet** — layer 1. Variant artifact, requirement-to-variant link, variant-to-feature-set link. Ships today; variant-schema refinements ongoing.
- **Cargo** — layer 2. Feature declarations, variant-to-feature mapping fed by rivet output. The `spar-codegen` → Cargo.toml plan extends this (see the MBSE section of the SDD post).
- **stable rustc + clippy + `#![deny(warnings)]`** — layers 3 and 4. Ships today. Under Ferrocene-qualified rustc, the oracle gains certification standing.
- **Ferrocene** — when qualified rustc ships against a given integrity target, layers 3 and 4 acquire certification weight. IEC 61508 SIL 2 already exists for the `core` subset; DO-178C qualification is the roadmap[^ferrocene-cert].
- **Ferrous/DLR MC/DC tool** — layer 5, when it ships.

None of these is complete as a composed stack today. The argument is that the composition, not any single piece, is what makes the economics work.

## The inversion

Pulling the threads together:

- C code under preprocessor-based cfg has roughly layers 1 (if you count project-level variant management), 2 (via build flags), 3 (`#ifdef`), and 5 (MC/DC at runtime-decision level). Layer 4 is absent — C's type system does not prune reachable branches.
- Rust code under rivet / cargo / cfg / type-discipline / match-arm-MC/DC has all five layers.
- Each layer that prunes at all makes the product strictly smaller. Adding a layer cannot make the product larger.

Therefore:

> **For a variant-managed product shipped at a specific configuration, MC/DC-for-Rust requires strictly less coverage effort than MC/DC-for-equivalent-C, once all layers are counted.**

This inverts the naive reading of the Ferrous paragraph. The novel language features do not make MC/DC harder in net; they provide an additional pruning layer C does not have. Ferrous's post is not wrong — layer 5 alone is harder for Rust than for C. The post is measuring at the wrong boundary.

## What this does not solve

Three honest caveats.

**Layer independence is an assumption.** The multiplicative argument assumes the pruning at each layer is orthogonal. In practice, cfg-guarded code can interact with type-system choices (a feature-gated generic bound, for instance), so the product `f_1 · f_2 · f_3 · f_4` can be loose. The argument degrades to *"strictly less or equal to C"* under pathological interaction, which is still a net win but less dramatic.

**Ferrocene MC/DC tooling is not yet shipping.** The layer-5 oracle is proposed in a paper, referenced in the Rust Project Goal for 2026, and worked on by the Safety-Critical Rust Consortium. Until the tool lands and is qualified, the argument is theoretical at layer 5. The other four layers are operational today, so partial value is already available.

**Proofs are still strictly stronger than coverage.** This post argues MC/DC-for-Rust is tractable, not sufficient. For ASIL-D and DAL-A, the full dossier wants both. The earlier posts in this arc — [Formal verification just became practical](/blog/formal-verification-ai-agents/), [What comes after test suites](/blog/what-comes-after-test-suites/) — make the proof-first case. MC/DC is what you add to the dossier *alongside* proofs, not instead of them.

## Academic prior art

Variability-aware analysis that prunes verification scope is a mature research line. Starting points:

- **Czarnecki & Eisenecker** — *Generative Programming: Methods, Tools, and Applications* (2000). The original MBE/PLE synthesis.
- **Classen, Heymans, Schobbens, Legay** — family-based model checking for software product lines (TSE 2013). Proves that SPL-wide verification can be done without enumerating all variants, which is the formal analogue of the MC/DC argument here.
- **Thüm et al.** — *A Classification and Survey of Analysis Strategies for Software Product Lines* (ACM Computing Surveys 2014). The reference survey.
- **Apel, Batory, Kästner, Saake** — *Feature-Oriented Software Product Lines* (2013). The textbook.

What this post contributes, as far as I can tell, is the Rust + AI-authorship angle. The academic literature is C-and-Ada-heavy; Rust's type-system pruning (layer 4) is qualitatively different from what PLE literature analyses. And AI-authorship as the economic ingredient that makes maintaining the variant graph cheap is not an angle the 2010–2014 literature was in a position to make.

## Take-away

- The coverage burden you have to discharge at ship is proportional to the single variant you ship, not to the product of your feature matrix. This is the variant-pruning principle.
- Rust provides four pruning layers above MC/DC itself — requirements variants, cargo features, cfg, and the type system. Three of the four ship today; the fifth (MC/DC tooling) is in development.
- AI-velocity authorship makes authoring all five layers cheap. That is what makes the economics work at scale.
- Under variant management, MC/DC-for-Rust at certification scale is *less* burdensome than MC/DC-for-C, not more. The received wisdom is measuring at layer 5 in isolation.

---

## Sources

[^ferrous-post]: Ferrous Systems — *Rust: Who, What and Why for ESA SW PA Workshop*, September 2025. [ferrous-systems.com/blog/rust-who-what-why](https://ferrous-systems.com/blog/rust-who-what-why/). Primary (author publication).

[^ferrous-paper]: *Toward Modified Condition/Decision Coverage of Rust*. German Aerospace Center (DLR) and Ferrous Systems. arXiv:2409.08708, 2024. [arxiv.org/abs/2409.08708](https://arxiv.org/abs/2409.08708). Primary (preprint).

[^rust-project-goal]: Rust Project — *What does it take to ship Rust in safety-critical?* 2026-01-14. [blog.rust-lang.org](https://blog.rust-lang.org/2026/01/14/what-does-it-take-to-ship-rust-in-safety-critical/). Primary (Rust Project publication; MC/DC listed as a 2026 goal).

[^ferrocene-cert]: Ferrous Systems — *IEC 61508 (SIL 2) Certification for Rust Core Library Subset*. [ferrous-systems.com/blog](https://ferrous-systems.com/blog/). Primary.

[^ple-lit]: Representative starting points: Czarnecki & Eisenecker (*Generative Programming*, 2000); the Classen / Heymans family-based model checking papers (2010–2013); Apel et al. (*Feature-Oriented Software Product Lines*, 2013); the Thüm et al. survey (ACM Computing Surveys 2014). Secondary — referenced collectively rather than quoted.

---

*This post is part of [PulseEngine](/) — a formally verified WebAssembly Component Model engine for safety-critical systems. Prior posts in the arc: [Formal verification just became practical](/blog/formal-verification-ai-agents/), [What comes after test suites](/blog/what-comes-after-test-suites/), [Spec-driven development is half the loop](/blog/spec-driven-development-is-half-the-loop/).*
