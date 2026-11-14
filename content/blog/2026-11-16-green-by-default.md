+++
title = "Green by default: required checks that could pass on bad input"
description = "A CI check is a claim: if the change were wrong, I would turn red. That claim is only evidence once someone has tested it by feeding the check an input it must reject. This post explains the idea, shows six ways a check stays green on bad input, and lists what a sweep of PulseEngine's own checks found."
date = 2026-11-16
draft = true
[taxonomies]
tags = ["verification", "ci", "process", "ai-agents"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**A required check counts as evidence once a planted bad input has turned it red.**

A green check says "nothing I looked at was wrong". It does not say whether it
looked. The only way to find out is to give it something it must reject and
watch what it does. This post explains that idea first, with pictures, and then
shows what happened when we applied it to our own repositories.
{% </insight> %}

## A check is a claim about itself

Every required check in a CI pipeline makes two statements. The one everybody
reads is about the change: "this pull request is fine". The one nobody reads is
about the check: "if this pull request were not fine, I would have said so".
The first statement is only as good as the second.

Philosophers of science call the missing property falsifiability: a claim that
no observation could ever contradict tells you nothing, because it would look the same whether it were true or
false. A check that would report success no matter what it was given is the
same kind of claim. Its green is not evidence; it is the default.

The four possible outcomes of a check make the problem visible:

{% <mermaid> %}
quadrantChart
    title What a check can report
    x-axis Input is good --> Input is bad
    y-axis Check is red --> Check is green
    quadrant-1 Fail-open - this post
    quadrant-2 Correct pass
    quadrant-3 False alarm
    quadrant-4 Correct catch
{% </mermaid> %}

False alarms get noticed, because a red check blocks work and somebody
investigates. A check stuck in the top-right corner, green on bad input, gets
noticed by nobody. Every day it stays green looks exactly like a good day.

## Testing the check, not the change

The remedy is old and simple: occasionally give the check an input whose right
answer is known to be "fail", and see what it says. Laboratories call this a
negative control. Mutation testing does the same thing to a test suite by
planting small bugs in the code and asking whether any test notices. Here the
thing under test is the CI check itself.

{% <mermaid> %}
graph LR
    A[Known-bad input planted on purpose] --> B[The check]
    B --> C{Verdict}
    C -->|red| D[The check can fail - its green means something]
    C -->|green| E[The check is fail-open - its green means nothing yet]
{% </mermaid> %}

A planted input is cheap. It can be an empty list, a report with a missing
field, a file that should fail a parser, a test that was deleted. It only has
to be something the check must reject.

There is an outside reference point for why this matters. GitHub's own
documentation says a job skipped by a conditional ["reports
'Success'"](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks),
which [How the factory talks](/blog/how-the-factory-talks/) covered. A 2025
study of 142,387 CI jobs across 81 industrial projects calls the general class
silent failures, jobs ["marked as successful but fail to complete all or part
of their tasks"](https://arxiv.org/abs/2509.14347); its analysis of 92 public
issues lists ignored exit codes among the most frequent causes. That study
finds them afterwards, by looking at which successful jobs get rerun. A planted
input finds them before anything ships.

## Six ways a check stays green on bad input

The failures we found fall into six shapes. Each is shown first as a toy
version, so the shape is clear before any of our code appears.

**1. Zero work counts as a pass.** The check counts failures and passes when
the count is zero. If it ran nothing, the count is also zero.

```text
selected tests: 0     failed: 0     ->  exit 0  (green)
```

**2. An exit code nobody reads.** The check runs a tool and looks only at the
tool's printed summary. If the tool crashes before printing one, there is no
failure line to find.

```sh
cargo test my_test | grep -q "FAILED" && exit 1   # a compile error prints no FAILED
exit 0
```

**3. A regex where a parser belongs.** The check looks for a pattern in text.
Anything written in a form the pattern does not expect is invisible, and
"found nothing" turns into "nothing wrong".

```text
pattern:  (data (i32.const N) ...)
input:    (data $a (i32.const 0) ...)    -> no match -> "nothing to check"
```

**4. A comparison that errors into success.** In shell, a comparison that
cannot run is false, and false often means "don't fail".

```sh
x=$(jq '.coverage' report.json)          # field missing -> x="null"
if [ "$x" -lt 155 ]; then exit 1; fi     # error, treated as false -> no exit
echo "gate PASSED"
```

**5. Agreement without a verdict.** A differential check compares two
implementations and passes when they agree. Two broken implementations agree
too.

```text
native build:  crash (exit 3)
wasm build:    crash (exit 3)     -> identical -> "AGREE" -> green
```

**6. A step that skips quietly.** A release step that cannot do its job warns
and carries on, and the release ships without that step's guarantee.

```text
signing key missing -> "warning: skipping signature" -> exit 0
```

None of these is exotic. Each is an ordinary, readable piece of script that
does the right thing on the inputs its author had in mind.

## What we are working towards

PulseEngine is an open-source, pre-1.0 WebAssembly Component Model engine meant
for safety-critical systems, together with the tools that check that work.
Much of the code in these repositories is written by agent sessions, and a pull
request merges only when its repository's required checks report success. That
makes the required checks the place where trust is decided, so they are the
first thing that has to be trustworthy.

The rule I now apply is the one in the box at the top: a required check counts
as evidence once a planted bad input has turned it red. In practice that means
every fix to a check ships with its planted input as the acceptance test. The
planted input turns the check red, and the real input stays green.

For readers from avionics, this is a small, informal step in the direction of
tool qualification. DO-330 is the avionics tool-qualification standard.
Rapita's summary of [DO-330](https://rapitasystems.com/do-330) lists tools that
could fail to detect an error among its qualification criteria; verification
tools typically fall at TQL-5, the lowest of its five qualification levels. I
did not read the standard itself. Our checks are not qualified tools, and this
sweep is not a qualification.

## What the sweep of our own checks found

On 13 November an agent read the CI workflows and checker scripts of
PulseEngine's repositories, ran a planted input wherever a check looked
suspicious, and changed nothing. Findings were filed as issues in the
repositories concerned. In eight repositories a required or release check could
pass on bad input. A planted input showed it in five of them; in the other
three it was read from the code, is latent, or was observed in a release.

| Shape | Repository and check | How it was found | State on 14 November |
|---|---|---|---|
| 1 | witness (test coverage of compiled WebAssembly): verification gate passed an all-skipped run and a test step that ran 0 tests ([#372](https://github.com/pulseengine/witness/issues/372)) | planted input | fixed in [#373](https://github.com/pulseengine/witness/pull/373) |
| 1 | spar (architecture models): Miri and ignored-test steps assert no minimum test count ([#622](https://github.com/pulseengine/spar/issues/622)) | latent, the tests run today | open |
| 2 | meld (component fusion): loss-scenario gate ignored cargo's exit code and checked only `approved` scenarios ([#608](https://github.com/pulseengine/meld/issues/608)) | read from the code | fixed in [#610](https://github.com/pulseengine/meld/pull/610) |
| 3 | gale (Rust port of Zephyr kernel primitives with machine-checked proofs): data-overlap gate did not see named data segments ([#502](https://github.com/pulseengine/gale/issues/502), more checks of this shape in [#505](https://github.com/pulseengine/gale/issues/505)) | planted input | open |
| 3 | rules_rocq_rust (Bazel rules for Rocq proofs): the axiom and `Admitted` check passed when its regex found no theorems ([#57](https://github.com/pulseengine/rules_rocq_rust/issues/57)) | planted input | fixed in [#58](https://github.com/pulseengine/rules_rocq_rust/pull/58) |
| 4 | scry (static analysis for WebAssembly): the MC/DC gate printed PASSED when the report lacked its fields; two more scry checks failed open ([#239](https://github.com/pulseengine/scry/issues/239)) | planted input | fixed in [#240](https://github.com/pulseengine/scry/pull/240) |
| 5 | ordeal (an SMT solver): the native-vs-WebAssembly comparison scored two crashing builds as agreeing | planted input | fixed in [#319](https://github.com/pulseengine/ordeal/pull/319) |
| 6 | spar: in v0.49.0 the release skipped its version check on two of seven binaries | observed in a release | fixed in [#621](https://github.com/pulseengine/spar/pull/621) |
| 6 | varve (signed toolchain layers): signing step warns and exits 0 when its key is missing ([#366](https://github.com/pulseengine/varve/issues/366)) | latent, no release shipped unsigned | open |

The same failure had shown up before the sweep, one case at a time: a nightly
fuzz job in loom, the WebAssembly optimizer, that ran no fuzzer
([loom#474](https://github.com/pulseengine/loom/issues/474)), and a release
step in sigil, the signing and attestation tool, where a signature check
written `cosign verify … || echo` could never fail
([sigil#350](https://github.com/pulseengine/sigil/issues/350)). What changed on
13 November is that planted inputs were tried across the organization's checks
in one pass instead of one incident at a time.

## Limits

The sweep is not a clean bill for the repositories it did not flag. Coverage
was uneven, and not every script behind every required check was read. A
check the sweep read and found sound is spar's verification gate: a pull
request can name a filter, the gate only lets that filter widen what runs, and
a run that executes nothing fails. That last property came from an earlier
fix, [spar#403](https://github.com/pulseengine/spar/issues/403).

A planted input also only proves what it plants. A check that turns red on an
empty report may still pass a report with plausible but wrong numbers. The
rule makes a check's green mean "this check can fail on at least this kind of
mistake", which is far more than "the job finished", and far less than "the
change is correct".
