+++
title = "Green by default: required checks that passed on planted bad input"
description = "On 13 November we fed known-bad input to the required CI checks of 19 PulseEngine repositories and watched for the ones that stayed green. Most were sound. The rest failed open in a handful of repeatable ways: zero tests counted as a pass, an ignored exit code, a regex where a parser belonged, a shell comparison that errors into success. This post lists the shapes, the planted inputs that exposed them, and the rule we now apply: a gate counts once a planted input has turned it red."
date = 2026-11-16
draft = true
[taxonomies]
tags = ["verification", "ci", "process", "ai-agents"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**A required check is evidence only after someone has watched it fail on purpose.**

On 13 November two read-only agent passes looked at the required CI checks of
19 PulseEngine repositories. Where a check looked suspicious, the agent fed it
an input that should fail and recorded the exit code. Most required checks
held. The ones that did not are listed below, each with the planted input,
the issue and, where it exists, the fix PR. Most of those issues are still
open on the day this is written, so this post reports what was found, not
what is fixed.
{% </insight> %}

## What this is about, from the outside

PulseEngine is an open-source, pre-1.0 project building a WebAssembly
Component Model engine meant for safety-critical systems, together with the
tools that check that work. Most of the code, tests and issues in these
repositories are written by Claude agent sessions, one per repository, and a
pull request merges only when the repository's required checks report
success. That makes the required checks the thing everything else leans on.
If a check can report success without having checked anything, the merge
rule is satisfied and nothing has been verified.

GitHub's own documentation names one way this happens: a job skipped by a
conditional ["will report its status as
'Success'"](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks).
A 2025 study of 142,387 CI jobs across 81 industrial projects calls the
general class silent failures, jobs ["marked as successful but fail to
complete all or part of their tasks"](https://arxiv.org/abs/2509.14347), and
lists ignored exit codes among the most frequent causes. That study finds
them afterwards, by looking at which successful jobs get rerun. The method
here works before the fact: plant an input whose correct verdict is known to
be "fail", and see what the check says.

## How the sweep worked

The first pass read the workflow files and checker scripts of 18 repositories
and ran nine negative controls. The second pass went deeper on eight
repositories that the first had only pattern-searched. It read the deciding
step behind 85 of their 87 required contexts and ran its own controls. Every
control ran the repository's own script, or the workflow's `run:` block
verbatim, against a planted input: an empty list, a report with a missing
field, a module whose segments overlap, a test filter that matches nothing.
External tools were stubbed where the check shells out. Nothing was changed
in any repository by the sweep. Findings went to the session that owns each
repository, which reproduced them on its own main before filing.

## The shapes

The failures fell into a small number of repeatable shapes. Each one below
names the planted input and the result.

### Zero work counts as a pass

witness's required verification gate returns success whenever nothing
failed. If every selected artifact is skipped because it has no runnable
step, the summary reads `passed: 0  failed: 0  skipped: 2` and the job exits
0. A test step whose filter matches no test prints `0 passed` and also counts
as a pass ([witness#372](https://github.com/pulseengine/witness/issues/372),
fix in [witness#373](https://github.com/pulseengine/witness/pull/373)).
spar's Miri and ignored-test steps run 30 and 5 tests today, but nothing
asserts a floor, so a renamed module would make them run none
([spar#622](https://github.com/pulseengine/spar/issues/622)). This shape is
the one the agents' own work is most likely to trigger, because renaming a
test is an ordinary refactor.

### An exit code that nobody reads

meld's loss-scenario gate runs `cargo test` for each scenario's regression
test and never checks cargo's return code. A compile error, a deleted test
and a renamed test all became "missing", and missing was advisory, so the job
passed. The meld session also found that only scenarios marked `approved`
were checked, so promoting one to `implemented` silently removed it from the
gate ([meld#608](https://github.com/pulseengine/meld/issues/608)). With the
fix, renaming one scenario's only test exits 1 and names the scenario.

### A regex where a parser belongs

gale's data-overlap gate reads the text form of a WebAssembly module and
looks for data segments with a pattern. A segment written with a name,
`(data $a …)`, does not match, so a module with two overlapping named
segments printed "no data segments, nothing to check" and exited 0. A newer
implementation of the same gate had the same gap, so a step requiring both
implementations to agree passed as well
([gale#502](https://github.com/pulseengine/gale/issues/502)). gale has
collected ten more checks of this shape in
[gale#505](https://github.com/pulseengine/gale/issues/505).

The same shape appeared in a proof-hygiene check.
rules_rocq_rust's assumptions test is meant to fail when a Rocq file
contains axioms or `Admitted` proofs. It found declarations with a regex over
six keywords, and when the regex found none it returned 0 without running the
Rocq compiler. A file containing only `Example … Admitted.` and
`Axiom cheat : False.` passed
([rules_rocq_rust#57](https://github.com/pulseengine/rules_rocq_rust/issues/57)).
The fix enumerates declarations from the compiled module instead. While it
was in review, a second gap turned up: the replacement name pattern accepted
ASCII only, so `Lemma α_bad : False. Admitted.` went unchecked. Both are
closed in [rules_rocq_rust#58](https://github.com/pulseengine/rules_rocq_rust/pull/58).

### A comparison that errors into success

scry's MC/DC gate reads three numbers from a coverage report with `jq` and
compares them with `[ "$x" -lt 155 ]`. When the report lacks those fields,
`jq` prints `null`, the comparison errors, the `if` treats the error as
false, and the script prints "MC/DC gate PASSED"
([scry#239](https://github.com/pulseengine/scry/issues/239), fix in
[scry#240](https://github.com/pulseengine/scry/pull/240)). Two more scry
checks failed open in the same pass: a WIT round-trip step piped through
`head -50 || true`, and a claim check that accepted an empty claim list.

### Agreement without a verdict

ordeal checks that its native and WebAssembly builds give identical output on
21 fixtures. When both sides were replaced by a stub that exits with an
error, all 21 invocations were scored as agreeing and the script exited 0.
The fix requires each invocation to exit cleanly with the verdict its fixture
is named for; the same stub now produces 42 wrong results and a failure
([ordeal#319](https://github.com/pulseengine/ordeal/pull/319)). Any
differential check has this risk: two broken sides agree.

### Release steps that skip quietly

Two release paths skipped a check without failing. spar's release confirmed
that each binary reports the tagged version, but skipped the two targets it
could not run natively, so in v0.49.0 two of seven binaries shipped with that
check unrun ([spar#621](https://github.com/pulseengine/spar/pull/621) adds a
job that runs them). varve's release signs the checksum file with an
additional key and, when the key is missing, warns and exits 0
([varve#366](https://github.com/pulseengine/varve/issues/366)). varve checked
its releases: v0.45.0 to v0.47.0 all carry the signature, so this one is
latent.

## What the planted inputs did not find

The sweep is not a clean bill for the repositories it did not flag. The
first pass only pattern-searched several repositories, and the second pass
did not read about 50 sub-scripts in one claim-check job, about 20 guardrail
scripts in another repository, or the Rust internals behind
`rivet validate`. What it did read and found sound includes rivet's single
required gate, all 19 of spar's, and the Kani and Gazebo checks in relay.
spar's verification gate is the model the others are moving towards: an
override in a pull request can only widen what runs, never narrow it, and a
run that executes nothing exits 1.

A follow-up looked back through merged pull requests for cases where one of
these holes let something through. It found none in the retained logs. It
did find the larger exposure next to them: in one repository, 99 pull
requests had merged while a verification gate that was not required was red.
A separate fault had turned that gate red on every run, so its real failures
were hidden among the false ones. The gate is clean on main today, and making
it required is the next step.

## The rule

We already had a skill for this, `gate-potency`, and earlier instances of the
same failure: a nightly fuzz job that ran no fuzzer
([loom#474](https://github.com/pulseengine/loom/issues/474)) and a release
step `cosign verify … || echo` that could never fail
([sigil#350](https://github.com/pulseengine/sigil/issues/350)). What changed
on 13 November is that the controls were run across every required check at
once, and each fix now ships with its control as the acceptance test: the
planted input turns the check red, and the real input stays green.

For a reader with a safety-standards background this is familiar ground.
A tool that ["could fail to detect an
error"](https://rapitasystems.com/do-330) is a verification tool in DO-330's
terms, and its qualification asks the same question. Our checks are not
qualified tools, and this sweep is not a qualification. It is the cheap first
step: before trusting a check's green, watch it go red once.
