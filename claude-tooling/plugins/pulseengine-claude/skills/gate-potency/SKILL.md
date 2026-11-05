---
name: gate-potency
description: This skill should be used to verify that checks and evidence can fail and are about the right system, such as "audit our gates", "can our CI actually fail", a vacuous or skipped required check, or a green emulator, staging or self-test result filed as "on-target", "on silicon" or "in production" evidence. Use before a release resting on green CI.
metadata:
  author: pulseengine.eu
  version: "1.0.0"
---

# Gate potency: can this check fail, and is it about the right system?

**When to use:** to verify the checks and evidence behind a claim, not the claim. Two failure classes, one question (can this green result be wrong?):

| The failure | Go to |
|---|---|
| a required CI check runs, reports green and **cannot go red** (the vacuous-gate class): "audit our gates", "can our CI actually fail", "is this check real", "why did that slip through a green board", inheriting a repo, before a release whose evidence rests on CI being green | Part A, the potency audit |
| a green result is about to be filed as evidence for a **different system** than the one it ran on ("on-target", "on silicon", "in production", "end-to-end", "the released binary", "verified on hardware"); wiring an emulator, simulator or staging run into a requirement's chain; a self-test that ships inside the artifact it tests | Part B, evidence transfer |

Part A's check runs and cannot fail. Part B's check can fail, runs, and reports something TRUE, but about the wrong machine, which is harder to see precisely because the result is correct. Run both; they miss different things. Whether the *claim* is true and worded to match its evidence is [`claim-verification`].

## Part A: the potency audit (the gate you inherited)

[`oracle-gate-a-change`] covers the oracle you are *authoring*: write it, wire it, watch it flip
red→green. This skill covers the gate you **inherited** — green since before you arrived, trusted
forever, never re-proved.

> **The one principle.** A green dashboard over a non-empty required-checks list is not evidence.
> **Presence is not potency.** The question is never "does a required check exist" — it is
> "**can this listed, running, currently-green check still go red today?**"

Nothing re-validates a standing gate on its own. The failure modes are mundane, invisible to
reading, and produce *confident, documented, auditable green over unverified code* — the
highest-severity failure a verification methodology can have.

### Why this is a real class, not a hypothetical

Two sibling repos sharing no code independently grew the same four bugs. Field-observed in one
sweep: a mutation gate reading a path the tool never writes (**4 months of vacuous green; 210
survivors reported as 0**) — and the same bug again in a second repo on a **hard** gate, whose own
artifact recorded 5 survivors while CI printed 0; a format check covering 1 of 4 workspaces; a
changed-paths classifier failing open two ways, skipping 11 of 18 required contexts; a "fail on
sorry" gate where all 12 `sorry`s carried the self-exempting comment; 7 verification artifacts
citing tests that never existed; a crashed tool run scored as a good one.

Once the artifact under test is well covered, the residual defects **migrate into the instruments**,
where they are structurally hard to see — the instrument's entire job is to report "fine".

### The audit

Run over **every required status check** on the protected branch. For each one:

#### 1. Negative control — the only real proof
Inject a deliberate violation and confirm the check goes **red**: an unformatted file, a surviving
mutant, a broken trace link, a `sorry` without the exemption, a deleted assertion. Restore
afterwards. Everything below is a cheap proxy; this is the actual evidence. Do it on a scratch
branch and record the run URL — that link *is* the potency evidence.

**Worked example — a supply-chain check, audited in minutes.** To establish that varve's digest
verification actually bites rather than merely existing, append one byte to a tool inside the
content-addressed core and re-run `varve verify`:

```
error: tool 'rivet' does not match its signed digest sha256:53af23a… — the binary was altered
```

Restore, and it is green again. That is potency evidence; *reading* the verification code is not.

**Pair the negative control with a positive one.** A control that goes red proves something fired —
not that the *mechanism you think* fired. Show it biting in one configuration and correctly inert in
another. Same audit: pointing `VARVE_TRUST_ROOT` at a bogus key makes `varve verify` exit 1 when the
pin names no realm, and is *ignored* (exit 0) when it names one — which is exactly the claim that a
realm's trust root cannot be substituted by the ambient environment. Either result alone proves
little; the pair isolates the mechanism. Without the red case the test may be vacuous; without the
green case you have not shown the red came from the property rather than the environment.

#### 2. Reads what it writes
Assert the gate parses a path the tool actually produces. Compare the parsed path against the real
output/artifact layout, not against the docs. Version bumps silently relocate results files.

#### 3. Scope covers the repo
Derive the target set mechanically — every `[workspace]` manifest, every `include_str!` input, every
crate — rather than trusting a hand-typed glob or a list that was correct when written.

#### 4. Defined ⇒ enforced
A check that exists in the tool but appears in no workflow is not a gate. Grep the workflows for an
actual invocation. Registry entries, scripts and harnesses are inert until something runs them.

#### 5. `skipped` ≠ `passed`
On GitHub a **skipped** required context satisfies the merge button. Therefore **any paths-filter is
a gate-disabler**, and its permissive branch is usually its *error* path (an errored `git diff`
skipping the matrix). Classifier error paths must fail **closed**. Treat every skipped required
context as unverified.

#### 6. Missing evidence ⇒ red
An absent results file must fail the gate, never default to a clean count (`MISSED=0`). Likewise a
crashed or timed-out tool run is **not** a pass — check the exit code, not just the summary line.

### Output

A per-check verdict: **potent** (negative control went red — with the run link), **inert** (proved
it cannot fail — file it), or **unproven** (not yet negative-controlled). Report the counts up
front. `unproven` is an honest state; `potent` without a negative control is not.

For every inert gate, file the defect in the repo it belongs to, and record whether any released
claim rested on it — a vacuous gate usually means published evidence needs re-checking, not just a
CI fix.

### Cadence

Fire at the **self-verify interval** the feature loop already mandates, when **inheriting a repo**,
and **before a release** whose evidence rests on green CI. Pairs naturally with [`repo-hygiene`]
as a release-tail sweep. Negative controls are cheap enough for that cadence; if a repo's checks are
numerous, rotate — audit the checks guarding this release's claims first.

### Anti-patterns

- **Trusting a non-empty `required_status_checks.contexts`.** It proves a list exists. Three of its
  contexts can be vacuous and the invariant still passes.
- **Reading the workflow instead of breaking it.** Vacuous gates look correct in review — that is
  precisely why they survive. Only the negative control settles it.
- **Auditing the check you just wrote and calling the standing ones fine.** The inherited gates are
  the risk; they have had longer to rot and nobody has ever seen them red.
- **Accepting a green summary line.** Check the exit code and the artifact; a crashed run prints a
  clean-looking tail.
- **Fixing the gate and closing the issue.** If the gate was inert, ask what shipped behind it.

## Part B: evidence transfer (is this green result about the machine you ship?)

Part A covers the check that **cannot go red**. This skill covers its harder sibling:
the check that **can** go red, **does** assert a real property, and reports something **true** —
but about a substrate that is not the one the claim is about.

> **The one principle.** A passing test licenses a claim about **the system it ran on**, and
> nothing else. Every step from *that* system to *the* system is an inference, and each one
> needs its own evidence.

This class is more dangerous than a vacuous gate for one reason: **the result is correct**. There
is nothing wrong to find in the output, the assertion, or the code. Reviewers read it, agree, and
move on. The defect lives in the word *on-target* — one adjective in a test title — not in
anything the test does.

### Why this is a real class

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

### The check

Run this before a result enters a verification chain, and when auditing one you inherited.

#### 1. Name both substrates, out loud, in one line

Write: **"this ran on X; the claim is about Y."** If X and Y are the same string, stop — this
skill does not apply. If they differ by even one word (`cortex-m3` vs `STM32F100`,
`release build` vs `the published asset`, `staging` vs `prod`), continue. Most of the value is
here: the inference is usually invisible until it is written as a sentence.

#### 2. Enumerate where the proxy is MORE PERMISSIVE

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

#### 3. MEASURE the target — do not read the datasheet, and do not trust the model

Read the number off the real thing. Silicon has ID registers; a service has a config endpoint; a
release has an actual asset you can download. In the STM32F100 case the decisive numbers came
from SWD reads of the part on the bench (`DBGMCU_IDCODE`, the flash-size register, and the
existing firmware's initial MSP), not from a datasheet and not from the `.repl`. A model is a
*hypothesis about* the target and cannot be evidence about it.

#### 4. Assert the artifact against the MEASURED values, as a committed check

Turn the finding into a script that anyone can run, not a paragraph anyone must believe. It
should take the artifact and the measured geometry and exit non-zero when they disagree.

**A check that fails today is the correct output.** Commit it red rather than softening it — the
honest state is the deliverable, and a red mechanical check survives a handover in a way a caveat
in a PR description does not.

#### 5. Negative-control the mechanism, not just the result

Remove the property you believe is doing the work and confirm the test goes red. If it still
passes, the test is measuring something else — find out what before you rely on it. *"I designed
P and the test passes"* is not evidence for P. This is the step that catches a proxy that agreed
with the target by luck.

#### 6. Never let a self-check be the only witness of the thing it lives inside

An in-artifact `--self-test` is a **field acceptance check** — its job is running where there is
no source tree. It exercises only the paths it happens to walk, and it ships with exactly the
bug it failed to catch. It is not a substitute for a suite outside the artifact, and treating it
as one is how a broken binary gets released reporting 5/5.

### Output

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

### Cadence

- Whenever a result is first filed against a requirement (this is the cheapest moment).
- When a proxy's configuration changes — a new `.repl`, a staging resize, a runner image bump.
- When the real target becomes available for the first time. **Its first job is not new
  capability, it is falsifying what the proxy has been asserting.**
- At the campaign self-verify interval, alongside Part A.

### Anti-patterns

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

### The media case

The same error travels in video. A generated depiction of a real run — a board
booting, a drone flying under verified control — is a result claimed on a
substrate that never existed, and a viewer cannot re-run it to find out. It is
evidence transfer with better production values.

EU AI Act Article 50(4) asks a narrower question (could the audience be deceived
about how it was made) and fully generated explainers sit outside it. Our
standard is the harder one: a rendering must never stand in for a measurement.
See [[pulseengine-generated-media]].

## Where this composes

- [`oracle-gate-a-change`]: authoring-time twin of Part A. Wire the oracle and prove it fails *in CI*; Part A is the
  standing-gate counterpart. When authoring the oracle, name the substrate at step one (Part B).
- [`claim-verification`]: a claim bound to a vacuous gate is an unbacked claim, and potency is what makes the
  evidence real. Its Part 1 rule *a claim must not exceed its instrument* is Part B stated for assertions you
  emit; here the instrument is the **substrate**, and the claim exceeds it by naming a machine the run never
  touched. A cold reviewer (its Part 2) is far more likely to notice that *on-target* is doing unearned work.
- [`traceability-audit`]: where a non-transferring result actually does its damage, as a `verifies` link that
  closes a V which is not closed.
- [`release-execution`]: run Part A before tagging; a release whose gate was inert needs its claims re-checked,
  not just its CI repaired.
- [`report-tool-friction`]: an inert gate in a PulseEngine tool is friction; file it in that tool's own repo. So
  is a proxy whose generosity is itself the upstream defect.
