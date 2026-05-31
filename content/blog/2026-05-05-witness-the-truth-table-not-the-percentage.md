+++
title = "witness ships the truth table, not the percentage"
description = "I just shipped witness v0.9.11. A fresh-eyes evaluator hit the first MC/DC truth table at 91 seconds and bookmarked the gap drill-down as the differentiator. This is the build-in-public note: what 91 seconds actually looks like, where the tool still has gaps, and why the truth table — not the coverage percentage — is the artifact I'd lead with externally."
date = 2026-05-05
draft = true
[taxonomies]
tags = ["verification", "wasm", "witness", "build-in-public"]
authors = ["Ralf Anton Beier"]
+++

{% insight() %}
witness v0.9.11 shipped on 2026-04-28. A fresh-eyes evaluator scaffolded a fixture, hit the first MC/DC truth table on stdout at 91 seconds, and bookmarked the gap drill-down as the screenshot a marketing team would actually use. The maintainer's version of that read: the version-stamped facts, the wow moment that survived the cold start, the gaps I'm staying honest about, and the framing I'd lead with externally rather than from inside the v0.9.x grind.
{% end %}

## What v0.9.11 actually is

The pitch hasn't moved since the [witness — MC/DC for the WebAssembly component model](/blog/witness-wasm-mcdc/) sketch: instrument a Wasm module, run a test harness, get back an MC/DC-style branch-coverage report keyed to source via DWARF. v0.9.10 added a `witness new <fixture>` scaffold so fresh users do not have to assemble the no_std + cdylib + wasm32-unknown-unknown + DWARF Cargo.toml by hand. v0.9.11 closed five tester items — three blockers — including the `verdict-evidence/` layout `witness viz` actually wants, the typed-args scaffold (no more `core::hint::black_box` poisoning DWARF to `hint.rs:491`), and a spec-compliant MCP `initialize` handshake so Claude Desktop and Cursor can connect at all.

Three commands from cold start to a running visualiser:

```sh
witness new my-fixture
cd my-fixture && ./run.sh
witness viz --reports-dir verdict-evidence
```

The scaffolded `run.sh` emits `verdict-evidence/<name>/{report.json, manifest.json}` so the viz wiring is automatic. The leap-year predicate is a real ISO rule — modular arithmetic blocks the rustc constant-fold-to-bitwise transformation that silently zero-decisions naive `(a && b) || c` over plain bools.

## The 91-second number

The fresh-eyes evaluator's stopwatch stopped at t=91s with this on stdout:

```
decisions: 1/1 full MC/DC; conditions: 2 proved, 0 gap, 0 dead

decision #0 lib.rs:40: FullMcdc
  truth table:
    row 0: {c0=T} -> T
    row 1: {c0=F, c1=T} -> T
    row 2: {c0=F, c1=F} -> F
  conditions:
    c0 (branch 0): proved via rows 0+2 (masking)
    c1 (branch 1): proved via rows 1+2 (unique-cause)
```

Twenty seconds of that 91 was a self-inflicted papercut — the first `./run.sh` hit `witness: command not found` because `WITNESS=...` was set in the script but the binary was not on PATH. v0.9.12 should write the resolved binary path into the generated `run.sh`; with PATH exported up front it would have been ~70s.

What I want to underline is the *artifact* at t=91. Not a percentage. A real DO-178C-vocabulary truth table with masking and unique-cause citations on each condition. That is the differentiator I keep underselling internally because I see it every day.

## The wow moment was the gap view, not the truth table

This was the part of the evaluation I did not predict. The truth table is what survives the cold start; the *gap drill-down view* in `witness viz` is what made the evaluator bookmark the project. Click a partial decision, click a gap row, land on a page that says *"To prove condition c2 independently affects the decision, you need a row where c2 = F. Required condition vector: c0 = T, c1 = T, c2 = F"* — and underneath, a literal `#[test]` stub ready to copy.

The same data is exposed over MCP at `/mcp`: three tools (`get_decision_truth_table`, `find_missing_witness`, `list_uncovered_conditions`), one surface for the reviewer and the agent. Every gap-closing test the agent proposes is verifiable by re-running witness and watching the row appear — same observation as in [Three patterns colliding](/blog/three-patterns-colliding/): the agent gets the same evidence the auditor sees, and the oracle either fires or it doesn't.

If I were positioning witness on the front page rather than in a v0.9.x changelog, this is the screenshot. Not the truth table. The gap view plus the suggested test stub. *The tool is doing the test-design step.* That is a different category of artifact from gcov, llvm-cov, or any HTML coverage report I have used.

## The verdict-suite scoreboard

The compliance bundle that ships with each release has 12 verdict fixtures now — `base64_decode` joined at v0.9.7, on top of the v0.8.0 frozen scoreboard:

```
TOTAL    716 branches   115 decisions   21/115 full MC/DC
         90 proved      91 gap          146 dead
```

Real Rust crates: httparse (67 decisions, 7 full MC/DC), nom_numbers (3/3), a TLS-handshake state machine (4/5), json_lite (2/29 — rich gap surface), and seven smaller compound-decision shapes. The "dead" bucket is what `cargo-llvm-cov` does not have the vocabulary to render: conditions that exist in the Wasm but cannot fire under the current test set. Reviewer's gold dust.

## What v0.9.11 still does not solve

The post would be marketing if I stopped here.

- **The signed predicate covers the branch report, not the MC/DC truth tables.** `witness predicate` builds a `witness-coverage/v1` in-toto Statement from the branch view; the MC/DC report is unsigned. The "signed evidence chain for MC/DC" pitch isn't fully delivered until v0.10.0 lands a `witness-mcdc/v1` predicate type.
- **Truth-table polarity is wasm-level, not source-level.** `c0=T` is the `br_if` value (taken / not taken), not the source condition value. v0.9.12 doc fix.
- **Release binaries are unsigned.** `SHA256SUMS.txt` ships unsigned; macOS arm64 trips Gatekeeper. For a tool whose pitch is signed evidence, that is a credibility gap. Sigstore-OIDC release signing is on v0.10.0.
- **No `witness merge`, no `witness diff`.** Per-PR coverage delta is a v0.10.x problem.
- **MC/DC on source is still aspirational.** The Ferrous / DLR mapping is the layer-5 story from the [variant-pruning post](/blog/variant-pruning-rust-mcdc/); witness measures one level below it. The two compose, but the source-level tool is not ours and is not shipping yet.

Every one of those is something an evaluator deserves written down before they bet on the v0.10 roadmap.

## Why I'd lead with the truth table

The Wasm angle is the load-bearing structural argument and it has not changed since the variant-pruning post: by the time the module exists, pattern matching has lowered to `br_if` and `br_table`, the `?` operator has desugared, type-state has resolved, cfg branches have been elided. Decisions visible in the Wasm are already MC/DC-shaped, against an instruction set with a machine-readable spec — the post-preprocessor C precedent DO-178C signed off on in 1992, restated for Wasm.

What I learned from the evaluation is that the structural pitch is not what closes a fresh user. The truth table on stdout closes them. The gap view with the suggested test stub keeps them. The MCP surface convinces them an agent can drive this. The scoreboard — 21 full-MC/DC decisions across 115 reconstructed decisions in real Rust — convinces them the tool isn't a toy.

v0.10 is where the signed-MC/DC predicate, the polarity docs, the release signing, and the merge / diff workflow have to land. Until then, install the v0.9.11 tarball, run `witness new`, click through the dashboard. Ninety seconds to the first truth table is the test, and right now the test is passing.

---

*This post is part of [PulseEngine](/) — a formally verified WebAssembly Component Model engine for safety-critical systems. Prior posts in the arc: [Spec-driven development is half the loop](/blog/spec-driven-development-is-half-the-loop/), [MC/DC for AI-authored Rust is tractable — the variant-pruning argument](/blog/variant-pruning-rust-mcdc/), [witness — MC/DC for the WebAssembly component model](/blog/witness-wasm-mcdc/), [Three patterns colliding](/blog/three-patterns-colliding/).*
