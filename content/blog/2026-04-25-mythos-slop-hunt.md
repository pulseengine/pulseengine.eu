+++
title = "Mythos slop-hunt: oracle-gated audits in practice"
description = "The Anthropic red-team Mythos scaffold runs four prompts — rank → discover → validate → emit — gated by a mechanical oracle that either fires or it doesn't. We pointed it at our own codebase to hunt slop: typed-but-unwired code, orphan modules, aspirational scaffolding. Here is the v2.2 oracle pair we settled on, the three pitfalls the audit surfaced, and three concrete findings that produced ~370 lines of orphan deletion plus three approved-but-unrealized requirements wired to live tested implementations."
date = 2026-04-25
draft = false
[taxonomies]
tags = ["verification", "process", "deep-dive"]
authors = ["Ralf Anton Beier"]
+++

{% note(kind="tip") %}
**Reading order for this stack** — if you arrived here cold, [*Three patterns colliding*](/blog/three-patterns-colliding/) is the synthesis: why this method belongs alongside Karpathy's LLM Wiki and typed compliance. This post is the method itself. The [v0.1.0 announcement](/blog/rivet-v0.1.0/) covers what rivet is and how to install it.
{% end %}

{% insight() %}
The Anthropic red team's Mythos scaffold is four prompts and one rule: a mechanical oracle either fires or it doesn't, and a fresh-session validator reproves anything before it ships as an artifact. We adapted it to hunt *slop* — typed-but-unwired code, orphan modules, aspirational scaffolding — by pairing two oracles instead of one: excision (primary, ground-truth reachability) and symbol-scoped trace (interpretive, classifies the kind of slop). Round one exposed three bugs in our own oracle design. Round two, with the v2.2 fixes, produced three confirmed findings — DD-064, DD-065, DD-066 — and three approved-but-unrealized requirements newly wired and tested. ~370 LOC of orphan code deleted, traceability coverage 36.9% → 39.5% on a single branch. The audit was the kind of session-length depth that the same scaffold would have produced quarters of work in a manual review.
{% end %}

## The four prompts

`scripts/mythos/` in [rivet](https://github.com/pulseengine/rivet/tree/feat/agent-pipelines-foundation/scripts/mythos) ships the pipeline. The shape is the same as the [SDD post](/blog/spec-driven-development-is-half-the-loop/) described in the abstract; this is the concrete oracle-and-prompt pair tuned for slop.

{% tree(root="scripts/mythos/") %}
HOWTO.md | pipeline overview + oracle design
rank.md | score every source file 1-5 by slop likelihood
discover.md | minimal prompt + oracle requirement; one agent per file
validate.md | fresh-session validator; reruns the oracle
emit.md | confirmed finding → draft design-decision artifact
{% end %}

The flow:

{% mermaid() %}
flowchart TB
    rank["<b>rank.md</b> · 1 agent · read-only<br/><i>score each file 1-5</i>"]
    subgraph discover_block["<b>discover.md</b> — N agents in parallel · isolated worktrees"]
        direction LR
        d1["agent · file A"]
        d2["agent · file B"]
        dn["agent · file N"]
    end
    excision["<b>excision oracle</b> · primary<br/>stub symbol · cargo build/test/clippy + rivet validate + commits<br/><i>baseline-match required</i>"]
    trace["<b>symbol trace</b> · interpretive<br/>git log -L · rivet artifacts · inline annotations<br/><i>classifies orphan vs aspirational</i>"]
    validate["<b>validate.md</b> · fresh session · no discovery context<br/><i>re-runs both oracles</i>"]
    emit["<b>emit.md</b><br/><i>draft design-decision artifact · verbatim oracle output in rationale</i>"]

    rank --> discover_block
    discover_block --> excision
    excision --> trace
    trace --> validate
    validate --> emit

    classDef phase fill:#13161f,stroke:#3d4258,color:#8b90a0;
    classDef agent fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef gate fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef interp fill:#1a1d27,stroke:#c084fc,color:#e1e4ed;
    classDef good fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;

    class discover_block phase;
    class rank,d1,d2,dn,validate agent;
    class excision gate;
    class trace interp;
    class emit good;
{% end %}

Run order: ranker classifies the corpus → for each rank-5 file, one parallel discover agent in an isolated git worktree → excision must pass before trace runs → validator in a *separate* fresh session re-runs both oracles → emit produces the audit-trail artifact. One agent per file is load-bearing — parallel coverage of independent files finds diverse bugs; one agent across the whole codebase converges on surface issues.

The agent topology is *one supervisor, many workers*. The supervisor holds the plan, dispatches workers, collects their structured outputs; the workers run in fresh contexts with narrow tasks and no awareness of each other. This is what keeps the discipline — a worker that hallucinates a finding cannot influence its peers, and the validator that re-runs the oracle has no exposure to the discovery agent's reasoning.

{% mermaid() %}
flowchart TB
    human["human curator<br/><i>scopes the run · approves emit drafts</i>"]
    rank_out["rank.md output<br/><i>file scores 1-5</i>"]
    sup["<b>supervisor agent</b><br/>holds plan · dispatches workers · collects results"]

    subgraph discoverers["discover workers · parallel · isolated git worktrees"]
        direction LR
        d1["worker A<br/>file rivet-core/foo.rs"]
        d2["worker B<br/>file rivet-core/bar.rs"]
        dn["worker N<br/>file rivet-cli/baz.rs"]
    end

    subgraph validators["validator workers · fresh sessions · no discovery context"]
        direction LR
        v1["validator A<br/>finding from worker A"]
        vn["validator N<br/>finding from worker N"]
    end

    artifact["<b>audit artifact</b><br/>design-decision · status: draft<br/>rationale carries verbatim oracle output"]

    human -->|"intent · what to audit"| sup
    rank_out --> sup
    sup -->|"spawn 1-per-file"| discoverers
    discoverers -->|"structured findings"| sup
    sup -->|"spawn fresh-session validators"| validators
    validators -->|"verdicts"| sup
    sup -->|"emit confirmed only"| artifact
    artifact -->|"review · promote draft → approved"| human

    classDef human fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed,stroke-width:1.5px;
    classDef sup fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed,stroke-width:2px;
    classDef worker fill:#0f1117,stroke:#4a5068,color:#8b90a0;
    classDef artifact fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
    classDef grp fill:#13161f,stroke:#3d4258,color:#8b90a0;

    class human human;
    class sup sup;
    class d1,d2,dn,v1,vn worker;
    class artifact artifact;
    class discoverers,validators grp;
{% end %}

The supervisor is the only agent with full plan visibility. Discoverers have one file each; validators have one finding each. The "fresh session" property is structural — validators can't see what the discoverer hypothesised, only the patch and the claim, so they verify the claim mechanically rather than rationalising it.

## The two oracles

The original Mythos paper uses one oracle (failing PoC test). Slop hunting needs two because the bug class — *unexercised typed-but-unwired code* — has two distinguishable signatures:

**Excision (primary, ground-truth reachability).** The agent submits a patch that stubs the target symbol with `unimplemented!("slop-hunt excision: {{file}}::{{symbol}}")` or — for whole-module excision — annotates the `mod` declaration with `#[cfg(not(all()))]` (not `#[cfg(never)]`; that one trips `unexpected_cfgs` under `-D warnings` and fabricates a non-baseline lint error, see *pitfalls* below). Then run, on the excised tree:

```
cargo build --workspace --all-targets
cargo test  --workspace --no-fail-fast
cargo clippy --workspace --all-targets -- -D warnings
cargo run --bin rivet --quiet -- validate
cargo run --bin rivet --quiet -- commits
```

`build` and `test` must exit 0. `clippy`, `validate`, `commits` must match a *baseline* recorded on a pristine checkout — pristine main is often non-zero on these for unrelated reasons (pre-existing lint noise, schema drift). Any *new* error after excision means the symbol is exercised; the finding is rejected. If the matrix passes, the symbol is unreachable.

**Symbol-scoped trace (interpretive, classifies kind).** Trace does not gate the finding — it tells us what kind of slop we have:

```
git log -L ':SYMBOL:path/to/file.rs' --format="%H" |
  grep -oE "[0-9a-f]{40}" | sort -u | while read sha; do
    git log -1 --format="%B" "$sha" |
      grep -qE "^(Implements|Refs|Fixes|Verifies): " && echo "$sha traced"
  done

rg -n "// rivet: (verifies|implements|refs|fixes) [A-Z]+-[0-9]+" path/to/file.rs

rivet list --format json | jq -r --arg p path/to/file.rs --arg s SYMBOL '
  .[] | select(
    (.description // "" | (contains($p) and contains($s))) or
    (.fields["source-ref"] // "" | (contains($p) and contains($s)))
  ) | .id'
```

Three queries. All empty → **orphan-slop** — nobody specced it, nobody calls it, propose `delete`. Any non-empty → **aspirational-slop** — somebody specced it, nobody wired it up, propose `add-test` or `document-as-non-goal`. The classification matters because the right disposition is different for each: orphans get cut; aspirations get either built or formally rescinded.

{% mermaid() %}
flowchart TB
    excise["excision oracle<br/>tests still pass with symbol stubbed?"]
    excise -- "no — symbol is exercised" --> reject["<b>finding rejected</b><br/><i>not slop</i>"]
    excise -- "yes — symbol is unreachable" --> trace
    trace["any of:<br/>git log -L trailers<br/>artifact source-ref<br/>inline // verifies REQ-N"]
    trace -- "all three empty" --> orphan["<b>orphan-slop</b><br/><i>delete</i>"]
    trace -- "any non-empty" --> aspir["<b>aspirational-slop</b><br/><i>add-test or document-as-non-goal</i>"]

    classDef gate fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;
    classDef interp fill:#1a1d27,stroke:#c084fc,color:#e1e4ed;
    classDef bad fill:#1a1d27,stroke:#f87171,color:#e1e4ed;
    classDef good fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
    classDef warn fill:#1a1d27,stroke:#fbbf24,color:#e1e4ed;

    class excise gate;
    class trace interp;
    class reject bad;
    class orphan good;
    class aspir warn;
{% end %}

## Three pitfalls v2.2 caught

Round one had a working oracle but three bugs the second round exposed. Each is small individually; collectively they're the difference between a method that flatters the practitioner and one that catches what the practitioner missed.

**Trailer passthrough.** v1's trace was *file-level*: any commit touching the file with `Implements:` / `Refs:` / `Fixes:` / `Verifies:` counted. That gave file-wide credit to unrelated refactor commits. The `wasm_runtime.rs` file passed v1 trace because a Phase-6-rowan refactor touched it for trailerless reasons; the four genuinely unwired methods (`call_id`, `call_name`, `call_supported_types`, `call_analyze`) hid behind that. Fix: switch to `git log -L :SYMBOL:file` so only commits that modified the *specific symbol* count.

**`#[cfg(never)]` fabricates lint errors.** Module-level excision needs an always-false cfg. `#[cfg(never)]` works on stable Rust but trips `unexpected_cfgs` under `-D warnings` (post-Rust 1.80), generating a clippy error that looks like the code is exercised when it is not. Use `#[cfg(not(all()))]` — recognised, always false, no lint noise.

**Inline-annotation blindness.** Tests in rivet carry `// rivet: verifies REQ-N` comments that tie tests to requirements. The artifact corpus does not expose these via `rivet list`; the v1 trace query missed them entirely. v2 greps the source for the inline form too. The `providers.rs` audit illustrates the difference: ten tests inline-tagged `verifies REQ-027`, REQ-027 status `approved`, no artifact `source-ref` mentioned the file. Strict v1 oracle classified it orphan; v2 classified it aspirational and we wired it up instead of deleting.

## Three case studies

### DD-064 — orphan-slop, four `WasmAdapter` methods

Excision target: `call_id`, `call_name`, `call_supported_types`, `call_analyze` in `rivet-core/src/wasm_runtime.rs`. Each `#[allow(dead_code)]` or `pub fn` with no caller in the workspace.

Excision diff: each method body replaced with `unimplemented!("slop-hunt excision: wasm_runtime.rs::METHOD_NAME")`, `_root` / `_aadl_dir` prefixed for unused parameters. Build, test, clippy, validate, commits all baseline-match.

Trace per symbol: introducing commits `50c5107` and `3b04f01` are both trailer-less; `git log -L` returns those single SHAs and they fail the trailer regex. No artifact references any of the four symbol names. Inline-annotation grep: empty. **Three queries empty → orphan-slop → delete.**

Result: 155 lines removed in [`75f3916`](https://github.com/pulseengine/rivet/pull/205/commits/75f3916). The `Adapter` trait impl at L590-619 had a `// TODO: call self.call_id() and cache` comment with no surrounding work — that comment was the smoking gun. Cleaned up alongside the deletion.

### DD-065 — orphan-slop, four narrow symbols across four files

| File | Symbol | Reason orphan |
|---|---|---|
| `rivet-core/src/sexpr.rs` | `line_starts`, `offset_to_line_col`, `SyntaxToken` alias | Duplicates of `yaml_cst::*` with no caller. LSP and db diagnostics use the `yaml_cst` versions. |
| `rivet-core/src/commits.rs` | `CommitClass::Exempt` variant + its match arm | `classify_commit_refs` has three return sites (`Linked`, `BrokenRef`, `Orphan`); none yields `Exempt`. The match arm was the author's `// for completeness` confession. |
| `rivet-core/src/reqif.rs` | `build_reqif` shorthand | Backward-compat wrapper for `build_reqif_with_schema(_, None)`. Zero callers. Every test goes through `ReqIfAdapter::export` to the schema-aware path. |
| `rivet-core/src/formats/needs_json.rs` | `import_needs_json_directory` | Adapter dispatch arm `AdapterSource::Directory` unreached at runtime; nothing in the corpus declares `format: needs-json` as a directory source. |

All four passed excision oracle with baseline match across build/test/clippy/validate/commits. All four trace-empty across the three queries. 75 lines removed in [`8c17daa`](https://github.com/pulseengine/rivet/pull/205/commits/8c17daa). The discovery agent on `formats/generic.rs` proposed a fifth fictional symbol `build_reqif_with_schema_unused`; grep refuted it before action — a reminder that bonus-finding hallucinations happen in agent NOTES even when the main finding is sound. Always grep-verify before deletion.

### DD-066 — orphan-slop, the entire `NeedsJsonAdapter` chain

Whole-block excision target: `pub struct NeedsJsonAdapter`, its `Default`/`Adapter` impls, the `adapter_config_to_needs_config` helper, the helper-only round-trip test, *plus* the `"needs-json" =>` arm in `rivet-core/src/lib.rs::load_artifacts` (the dispatch arm is also dead because no source declares `format: needs-json`). 129 LOC across two files.

Excision used `#[cfg(not(all()))]` on the relevant items. Live path preserved: the CLI command `cmd_import_results_needs_json` and the fuzz target both call `import_needs_json` directly, bypassing the adapter. Trace queries: empty for both `NeedsJsonAdapter` and `adapter_config_to_needs_config`. Inline-annotation grep: one hit on the helper-only test (which gets deleted with the helper). 12 retained tests on the live path still verify `REQ-025`. Removed in [`48ff990`](https://github.com/pulseengine/rivet/pull/205/commits/48ff990).

## What this also closed

Three approved-but-unrealized requirements where the audit found existing implementations had no live caller:

- **`REQ-027`** ("Build-system-aware cross-repo discovery") — `providers.rs` had the implementation, no CLI command exposed it. Wired up via `rivet externals discover` with three integration tests; commit [`aa257cd`](https://github.com/pulseengine/rivet/pull/205/commits/aa257cd).
- **`REQ-006`** ("OSLC-based tool synchronization") + **`FEAT-011`** ("OSLC client for bidirectional sync") — `OslcSyncAdapter::push` was a fire-and-forget POST loop; the doc comment admitted it was incomplete. Implemented diff-then-POST-or-PUT semantics with five wiremock integration tests; commit [`cc735f2`](https://github.com/pulseengine/rivet/pull/205/commits/cc735f2). Both promoted from `draft` to `approved`.

These are aspirational-slop cases where the right disposition was add-wire-up, not delete. The v2 oracle made the call correctly because the inline-annotation query surfaced `verifies REQ-027` on the providers tests and lifted the classification from orphan to aspirational.

## What's reusable

The oracle is interchangeable. Anything mechanical your domain produces — failing PoC test, fuzzer crash, type error, proof obligation, `rivet validate` diagnostic, sanitizer fault — can be the oracle. The Mythos paper's failing-PoC oracle for vulnerability research, the SDD post's `rivet validate` oracle for traceability gap closure, and this post's excision-plus-trace oracle for slop hunting are three instantiations of the same scaffold against three oracle types. The four prompts and the parallel-agent-plus-fresh-validator discipline transfer; the oracle is the parameter.

The discipline transfers to any codebase that has typed validators and audit-grade artifacts — not just rivet. A C++/CMake project with `clang-tidy` plus a configuration-validator has both halves; the same pipeline shape works there.

## Numbers from PR #205

`scripts/mythos/` shipped, then ran against rivet's own codebase:

- ~370 lines of orphan code deleted across DD-064/065/066
- 3 approved-but-unrealized requirements wired and tested
- 8 new integration tests (3 externals discover, 5 OSLC push)
- Traceability coverage 87/236 (36.9%) → 94/238 (39.5%)
- 12 typed audit artifacts produced; every one carries the verbatim oracle output in its `rationale` field

The session that produced these took roughly six hours of wall time, almost entirely waiting on cargo builds in parallel worktrees. The bookkeeping the LLM agents did would have taken weeks of human review at the same depth — and a human reviewer would have produced prose, not typed audit artifacts.

`scripts/mythos/` is the file. `rivet validate` is the oracle. `git log -L :symbol:file` is the trace. Everything else is discipline.
