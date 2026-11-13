+++
title = "Green by default: required checks that could pass on bad input"
description = "On 13 November an agent checked the required and release CI checks of PulseEngine's repositories. In eight repositories a check could pass on bad input. A planted input showed it in five; in the other three it was read from the code, is latent or was seen in a release. Six shapes, with issues and fixes."
date = 2026-11-16
draft = true
[taxonomies]
tags = ["verification", "ci", "process", "ai-agents"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**A required check counts as evidence once a planted bad input has turned it red.**

In eight repositories a required or release check could pass on bad input. In
five (witness, gale, rules_rocq_rust, scry, ordeal) a planted input showed it.
In meld it was read from the code, in varve it is latent, and in spar one check
is latent and one skip was observed in a release. The findings fall into six
shapes, each listed below with the issue and the fix PR where one exists. As of
13 November every issue and PR from this sweep is open.
{% </insight> %}

## What this is about, from the outside

PulseEngine is an open-source, pre-1.0 project building a WebAssembly
Component Model engine meant for safety-critical systems, together with the
tools that check that work. Much of the code and many of the issues in these
repositories are written by agent sessions. A pull request merges only when the
repository's required checks report success. If a check can report success
without having checked anything, the merge rule is satisfied and nothing has
been verified.

The eight repositories were witness (measures test coverage of compiled
WebAssembly), spar (architecture models), meld (fuses components), gale (a Rust
port of Zephyr RTOS kernel primitives with machine-checked proofs on its
source), rules_rocq_rust (Bazel rules for Rocq proofs), scry (static analysis
for WebAssembly), ordeal (an SMT solver) and varve (signed toolchain layers).

GitHub's own documentation names one way this happens: a job skipped by a
conditional ["reports 'Success'"](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks).
That case was covered in [How the factory talks](/blog/how-the-factory-talks/);
this post covers other shapes. A 2025 study of 142,387 CI jobs across 81
industrial projects calls the general class silent failures, jobs ["marked as
successful but fail to complete all or part of their
tasks"](https://arxiv.org/abs/2509.14347); its analysis of 92 public issues
lists ignored exit codes among the most frequent causes. That study finds them afterwards, by looking at which
successful jobs get rerun. The method here works before the fact: plant an
input whose correct verdict is known to be "fail", and see what the check says.

## How the sweep worked

An agent read the CI workflows and checker scripts of the organization's
repositories. Where a check looked suspicious, it ran a planted input against
it and recorded the exit code. It changed nothing in any repository. Findings
were filed as issues. In three of the eight (meld, gale, spar) the issue
records a re-check by the session that owns the repository.

## Six ways a check could pass on bad input

### Zero work counts as a pass

witness's required verification gate returns success whenever nothing
failed. If every selected artifact is skipped because it has no runnable
step, the summary reads `passed: 0  failed: 0  skipped: 2` and the job exits
0. A test step whose filter matches no test prints `0 passed` and also counts
as a pass ([witness#372](https://github.com/pulseengine/witness/issues/372),
fix in [witness#373](https://github.com/pulseengine/witness/pull/373)).
spar's Miri (Rust's interpreter for detecting undefined behaviour) and
ignored-test steps run 30 and 5 tests today, but nothing asserts a floor, so a
renamed module would make them run none. That one is latent: the tests match
today ([spar#622](https://github.com/pulseengine/spar/issues/622)).

### An exit code that nobody reads

meld's loss-scenario gate (a loss-scenario is a hazard scenario from the safety
analysis, each with a regression test) runs `cargo test` for each scenario's
regression test and never checks cargo's return code. A compile error, a
deleted test and a renamed test all became "missing", and missing was advisory,
so the job passed. The sweep also found that only scenarios marked `approved`
were checked, so promoting one to `implemented` silently removed it from the
gate. The findings were read from the code, not run, and the meld session
confirmed them against the code ([meld#608](https://github.com/pulseengine/meld/issues/608)).
The issue's acceptance test is that deleting one regression test turns the
check red.

### A regex where a parser belongs

gale's data-overlap gate reads the text form of a WebAssembly module and
looks for data segments with a pattern. A segment written with a name,
`(data $a …)`, does not match, so a module with two overlapping named
segments printed "no data segments — nothing to check" and exited 0. The Rust
implementation of the same gate has the same gap
([gale#502](https://github.com/pulseengine/gale/issues/502)). gale has
collected further checks that match text where they should parse it, such as
its proof-completeness and vacuous-lemma checks, in
[gale#505](https://github.com/pulseengine/gale/issues/505).

The same shape appeared in a proof-hygiene check.
rules_rocq_rust's assumptions test is meant to fail when a Rocq file
contains axioms (assumptions taken without proof) or `Admitted` proofs (proofs
left unfinished). The original check matched six keywords with a regex and
returned 0 when it found none, without running the Rocq compiler. A file of
only `Example … Admitted.`, `Definition … Admitted.`, `Local` declarations and
`Axiom cheat : False.` passed
([rules_rocq_rust#57](https://github.com/pulseengine/rules_rocq_rust/issues/57)).
The first draft of the fix still matched names with a regex that accepted ASCII
only, and an automated review caught it with a Unicode-named `Admitted`
lemma. The fix in
[rules_rocq_rust#58](https://github.com/pulseengine/rules_rocq_rust/pull/58)
enumerates declarations from the compiled module, which covers both.

### A comparison that errors into success

scry's MC/DC gate reads values from a coverage report with `jq` and compares
two of them against floors, for example `[ "$PROVED" -lt 155 ]`, where 155 is
the floor for proved conditions. MC/DC is a structural coverage criterion from
avionics. When the report lacks those fields, `jq` prints `null` and the
comparison errors. The `if` that guards the failure branch reads the error as
false, so the script prints "MC/DC gate PASSED" ([scry#239](https://github.com/pulseengine/scry/issues/239), fix in
[scry#240](https://github.com/pulseengine/scry/pull/240)). Two more scry
checks failed open in the same pass: a round-trip step for the WIT file (the
component's interface definition), which re-prints it to check it parses, piped through `head -50 || true`, and
a claim check (a script that checks documented claims against evidence) that
accepted an empty claim list.

### Agreement without a verdict

ordeal checks that its native and WebAssembly builds give identical output on
21 invocations of its fixture corpus, so two broken sides agree. When both
sides were replaced by a stub that exits with an error, all 21 invocations
were scored as agreeing and the script exited 0. The proposed fix requires
each invocation to exit cleanly with the verdict its fixture is named for.
With it ([ordeal#319](https://github.com/pulseengine/ordeal/pull/319)), the
same stub produces 42 WRONG lines, one for each of an invocation's two
builds, and a failure.

### Release steps that skip quietly

spar's release confirmed that each binary reports the tagged version, but
skipped the two targets it could not run natively, so in v0.49.0 two of seven
binaries shipped with that check unrun. This one was observed in a release; no
input was planted. [spar#621](https://github.com/pulseengine/spar/pull/621)
(not yet run on a runner) proposes a job that runs them. varve's release signs
the checksum file with the varve root key, and when that key is missing it
skips the signing step with a warning and exits 0
([varve#366](https://github.com/pulseengine/varve/issues/366)).
varve checked its releases: v0.45.0 to v0.47.0 all carry the signature, so no
release shipped unsigned and this one is latent.

## Limits of the sweep

The sweep is not a clean bill for the repositories it did not flag. Coverage
was uneven, and not every script behind every required check was read. One
check the sweep read and found sound is spar's verification gate: a pull
request can name a filter, the gate only lets that filter widen what runs, and
a run that executes nothing fails. That last property came from an earlier
fix: [spar#403](https://github.com/pulseengine/spar/issues/403), an all-skipped
run counted as a pass, was fixed in v0.44.0.

DO-330 is the avionics tool-qualification standard. Rapita's summary of
[DO-330](https://rapitasystems.com/do-330) lists tools that could fail to
detect an error among its qualification criteria; verification tools typically
fall at TQL-5, the lowest of its five qualification levels. I did not read the standard itself. Our checks are not qualified
tools, and this sweep is not a qualification.

## The rule I apply now

I already had a skill for this, `gate-potency`, and earlier instances of the
same failure: a nightly fuzz job that ran no fuzzer in loom, the WebAssembly
optimizer ([loom#474](https://github.com/pulseengine/loom/issues/474)), and a
release step in sigil, the signing and attestation tool, where a cosign
signature check written `cosign verify … || echo` could never fail
([sigil#350](https://github.com/pulseengine/sigil/issues/350)). I now count a
required check as evidence only once a planted bad input has turned it red.
The fix PRs for witness, rules_rocq_rust, scry and ordeal show, in local runs,
their planted input turning the check red. For rules_rocq_rust, scry and ordeal
they also show real input staying green; witness's is shown against a stubbed
rivet. None is merged yet, and some have not run in CI.
