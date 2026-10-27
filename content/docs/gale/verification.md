+++
title = "Verification Status"
template = "docs.html"
description = "What is proven, what is not, and what remains open"
weight = 2
+++

# Verification Honesty Assessment

**Date:** 2026-03-22

> The 2026-03-22 assessment below is kept as written. Its statements that the formal tools do not run in CI are out of date: see [Current status](#current-status) at the end of this page, which follows gale's own [claims ledger](https://github.com/pulseengine/gale/blob/main/docs/safety/verification-honesty.md).

## What Runs on Every Commit (CI-Enforced)

| Check | Tool | What It Proves |
|-------|------|---------------|
| Runtime tests | `cargo test` | Functions produce expected outputs, no panics (~995 tests) |
| Lint | `cargo clippy` | No common Rust pitfalls (pedantic + safety-critical lints) |
| Strip gate | `verus-strip gate` | plain/src/ is in sync with src/ (no stale stripped code) |
| Zephyr integration | west + QEMU | 36 upstream test suites pass with Gale replacing C code |
| Multi-arch | Renode | Semaphore tests pass on M4F, M33, R5 hardware emulation |
| Coverage | cargo-llvm-cov + gcov | Line coverage metrics uploaded to Codecov |

**These are functional tests, not formal proofs.**

## What Exists But Does NOT Run in CI

| Tool | What It Proves | How to Run | Last Verified |
|------|---------------|------------|---------------|
| Verus (Z3) | SMT verification of requires/ensures contracts | `bazel test //:verus_test` | Local only, no CI record |
| Rocq | Theorem proofs about abstract invariants | `bazel test //proofs:*` | Local only, no CI record |
| Lean 4 | Mathematical scheduling theory proofs | `bazel test //proofs/lean:*` | Local only, no CI record |
| Kani BMC | Bounded model checking (185 harnesses) | `bazel test //:kani_test` | Local only, no CI record |
| Miri | Undefined behavior detection | `bazel test //:miri_test` | Local only, no CI record |

**All formal verification requires Bazel + Nix toolchains.**

## The Gap

A commit could break any formal proof and CI would not catch it. The README claims "39/39 Verus verified" but this is based on local runs, not CI-enforced regression testing.

## What "Formally Verified" Actually Means for Gale Today

1. The Verus annotations EXIST in every src/*.rs file
2. They WERE verified to pass at some point (locally)
3. They are NOT regression-tested on every commit
4. The Verus-stripped code (plain/src/) IS tested functionally on every commit
5. The Zephyr integration IS tested on every commit

This is closer to "well-specified and comprehensively tested with local formal verification" than "continuously formally verified."

## Path to Real Formal Verification CI

Option A: Add Bazel CI workflow with Nix (complex setup, but runs everything)
Option B: Add a nightly/weekly cron job for formal verification (less frequent but catches drift)
Option C: Add individual verification tools to GitHub Actions without Bazel (simpler but more workflows)

The seL4 team spent a decade on their proofs. This is honest about where we are.

## Current status

gale's claims ledger supersedes the "does not run in CI" statements above. `.github/workflows/formal-verification.yml` in gale runs Verus (`bazel test //:verus_test`), Kani (185 harnesses), Rocq and Lean on pull requests that touch proof-relevant paths, on pushes, and on a weekly cron. Miri is not part of that workflow.

A green run of that workflow certifies less than "all proven", and the ledger names each gap:

| Tool | What a green run means | What it does not mean |
|------|------------------------|-----------------------|
| Verus | The bodies Verus checked satisfy their requires/ensures contracts | That every line is checked: 133 `external_body` functions and 2 `assume_specification` calls are trusted, and CI does not pass `--no-cheating` |
| Rocq | Every file elaborates; 10 modules are fully proven with `Qed` | That `poll`, `sched` and `thread_lifecycle` are proven: their 74 theorems are `Admitted` stubs, which Rocq accepts. All Rocq proofs are over hand-written models, not the Rust |
| Lean | The scheduling-theory theorems check | Anything about the implementation |
| Kani | The harnesses hold within their bounds | That kernel properties hold for all inputs: most kernel harnesses assume a bound such as `count <= 20`. The uart-thin and gpio-thin driver decision cores are the exception, checked over the full input type; dma-own is bounded to a four-slot ring |

Every proof above is about the Rust or wasm **source**. For the wasm line, the shipped artifact is native code produced by meld, loom and synth. That code is differentially tested against a reference wasm semantics over sampled or finite input ranges. It is not proven equivalent to the source, and no end-to-end verified pipeline is claimed.
