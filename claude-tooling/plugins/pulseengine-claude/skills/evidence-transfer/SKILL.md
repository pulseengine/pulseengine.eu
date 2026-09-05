---
name: evidence-transfer
description: This skill should be used whenever a green result is about to be filed as evidence for a claim about a DIFFERENT system than the one it ran on — "on-target", "on silicon", "in production", "end-to-end", "the released binary", "verified on hardware". Use it when wiring an emulator/simulator/staging run into a requirement's verification chain, when a self-test ships inside the artifact it tests, when reviewing an inherited "on-target" gate, and at the campaign self-verify interval. The failure class is NOT a vacuous gate — the check runs, can go red, and reports something TRUE. It is about the wrong machine, which is harder to see precisely because the result is correct. Composes with gate-potency (checks that cannot fail), verify-your-own-claims (a claim must not exceed its instrument — here the instrument is the substrate), oracle-gate-a-change (the oracle you author), clean-room-verification (review it cold) and traceability-audit (where the bad inference lands).
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# Evidence transfer — is this green result about the machine you ship?

[`gate-potency`] covers the check that **cannot go red**. This skill covers its harder sibling:
the check that **can** go red, **does** assert a real property, and reports something **true** —
but about a substrate that is not the one the claim is about.

> **The one principle.** A passing test licenses a claim about **the system it ran on**, and
> nothing else. Every step from *that* system to *the* system is an inference, and each one
> needs its own evidence.

This class is more dangerous than a vacuous gate for one reason: **the result is correct**. There
is nothing wrong to find in the output, the assertion, or the code. Reviewers read it, agree, and
move on. The defect lives in the word *on-target* — one adjective in a test title — not in
anything the test does.

## Why this is a real class

Field-observed, all with numbers:

- **The emulator was more generous than the part.** An "on-target execution rung" for an
  STM32F100 failsafe core ran in an emulator whose synthetic platform declared **256 KB of SRAM**.
  The real part has **8 KB**. The image's initial stack pointer was `0x20020000` — *outside
  physical RAM* — and its SRAM segment overflowed the real part by **57,344 bytes**. It had been
  green in CI for six weeks. The byte-exactness it asserted was genuine; the machine was not.
- **The self-test shipped inside the thing it tested.** A CLI's built-in `--self-test` reported
  **5/5 PASS** on a release binary that returned **exit 0 for commands it never ran**. The
  self-test only ever wrapped `sleep`, `true` and `kill -9` — none carrying a flag the tool also
  understood — so the entire bug class sat outside every path it walked.
- **The test measured the platform, not the property.** An assertion passed on macOS and failed
  on Linux because GNU `echo` interprets `--version` while BSD `echo` prints it. The tool was
  correct in both. The gate ran on one platform; the artifact shipped on both.
- **The negative control did not discriminate.** A deadlock-freedom test passed with the
  mechanism it was written to prove **removed**. Two independent mechanisms were present; the
  test saw only the other one.

Four different repos' worth of shape, one root: *a result was filed against a claim it did not
support.*

## The check

Run this before a result enters a verification chain, and when auditing one you inherited.

### 1. Name both substrates, out loud, in one line

Write: **"this ran on X; the claim is about Y."** If X and Y are the same string, stop — this
skill does not apply. If they differ by even one word (`cortex-m3` vs `STM32F100`,
`release build` vs `the published asset`, `staging` vs `prod`), continue. Most of the value is
here: the inference is usually invisible until it is written as a sentence.

### 2. Enumerate where the proxy is MORE PERMISSIVE

Not "where does the model differ" — differences that make the proxy *stricter* are safe. Only
generosity hides failures. Ask, per resource: could Y run out of something X had plenty of?

| axis | the question |
|---|---|
| memory | RAM/flash size, stack ceiling, alignment, MPU/MMU regions |
| time | timeouts, watchdogs, clock rate, real-time deadlines |
| privilege | privileged vs unprivileged, secure world, kernel driver bound |
| capacity | file descriptors, buffer sizes, queue depth, packet size |
| tolerance | does the proxy accept malformed input the target rejects — or vice versa |

An emulator, a staging environment and a developer laptop are all *usually* more generous than
production. That is what makes them pleasant to work in, and it is exactly the hazard.

### 3. MEASURE the target — do not read the datasheet, and do not trust the model

Read the number off the real thing. Silicon has ID registers; a service has a config endpoint; a
release has an actual asset you can download. In the STM32F100 case the decisive numbers came
from SWD reads of the part on the bench (`DBGMCU_IDCODE`, the flash-size register, and the
existing firmware's initial MSP), not from a datasheet and not from the `.repl`. A model is a
*hypothesis about* the target and cannot be evidence about it.

### 4. Assert the artifact against the MEASURED values, as a committed check

Turn the finding into a script that anyone can run, not a paragraph anyone must believe. It
should take the artifact and the measured geometry and exit non-zero when they disagree.

**A check that fails today is the correct output.** Commit it red rather than softening it — the
honest state is the deliverable, and a red mechanical check survives a handover in a way a caveat
in a PR description does not.

### 5. Negative-control the mechanism, not just the result

Remove the property you believe is doing the work and confirm the test goes red. If it still
passes, the test is measuring something else — find out what before you rely on it. *"I designed
P and the test passes"* is not evidence for P. This is the step that catches a proxy that agreed
with the target by luck.

### 6. Never let a self-check be the only witness of the thing it lives inside

An in-artifact `--self-test` is a **field acceptance check** — its job is running where there is
no source tree. It exercises only the paths it happens to walk, and it ships with exactly the
bug it failed to catch. It is not a substitute for a suite outside the artifact, and treating it
as one is how a broken binary gets released reporting 5/5.

## Output

State, per result:

```
ran on:        <substrate X, with the parameters that mattered>
claim is about:<substrate Y, MEASURED — with the register/endpoint the number came from>
generosity:    <every axis where X was more permissive than Y>
transfers:     yes | no | partially (say which part)
gate:          <path to the committed check that asserts it, and its current exit code>
```

If it does not transfer, **say what the result DOES support** rather than discarding it. In the
STM32F100 case the byte-exactness and the rotor-out zeros were genuine Cortex-M3 semantics and
kept their value as an ISA-level claim; only the word *on-target* had to go. Overturning the
adjective is the finding — overturning the whole result would be wrong.

## Cadence

- Whenever a result is first filed against a requirement (this is the cheapest moment).
- When a proxy's configuration changes — a new `.repl`, a staging resize, a runner image bump.
- When the real target becomes available for the first time. **Its first job is not new
  capability, it is falsifying what the proxy has been asserting.**
- At the campaign self-verify interval, alongside [`gate-potency`].

## Anti-patterns

- **Treating "class" as "part".** `STM32F100-class` is an honest label on a model and a dishonest
  one in a verification chain. The model is not lying; the inference is.
- **Reading the proxy's config as the target's spec.** The `.repl`, the container limits and the
  mock are all hypotheses. Only the target is evidence about the target.
- **Softening a red check into a caveat.** A note in a PR body is not a control; the next person
  inherits the green.
- **Discarding a true result because it does not transfer.** Re-file it against the claim it does
  support.
- **Diagnosing with an instrument that mutates the subject.** Detaching a driver to prove one
  tool could bind the device made it invisible to the tool actually under test — three rounds
  were then spent diagnosing a self-dug hole. If a diagnostic changes state, it is part of the
  system under test; undo it, or hold it constant and say so.
- **Filing upstream before reading the supplier's source.** An error message reading
  `invalid sub-command or arguments` was raised on an *empty device response* — the message named
  the wrong cause and nearly cost a supplier their attention on a wrong report.

## Where this composes

- [`gate-potency`] — the sibling class: a check that cannot go red at all. Run both; they miss
  different things.
- [`oracle-gate-a-change`] — when authoring the oracle, name the substrate at step one.
- [`clean-room-verification`] — a cold reviewer is far more likely to notice that *on-target* is
  doing unearned work.
- [`traceability-audit`] — where a non-transferring result actually does its damage: as a
  `verifies` link that closes a V which is not closed.
- [`verify-your-own-claims`] — its rule *a claim must not exceed its instrument* is this one
  stated for assertions you emit; here the instrument is the **substrate**, and the claim exceeds
  it by naming a machine the run never touched.
- [`report-tool-friction`] — when the proxy's generosity is itself the upstream defect.
