---
name: report-tool-friction
description: This skill should be used whenever a PulseEngine tool (rivet, spar, witness, sigil, meld, loom, synth, kiln, gale, scry, ordeal, varve, smithy, temper — the roster lives in the pulseengine-toolchain memory) produces friction during real work — it errors, crashes, produces wrong or surprising output, is missing a capability you needed, has confusing/undocumented behavior, or forced you into a workaround. ALWAYS use this skill the moment you notice yourself working *around* a tool instead of *with* it, or saying "this should just work but doesn't." The friction is the signal; capturing it as an issue in the tool's own repo is the action. Fires inside [`pulseengine-feature-loop`] and [`release-execution`] and any standalone tool use.
metadata:
  author: pulseengine.eu
  version: "0.5.0"
---

# Report tool friction

## When this fires

You are using a PulseEngine tool to *get real work done* — not testing the tool, just using it — and it gets in your way. Concretely, any of:

- It errors, panics, or crashes on input that should be valid.
- It produces wrong, surprising, or unexplained output.
- It's missing a capability the task needed, so you reached for something else.
- Its behavior was confusing or undocumented enough that you had to guess.
- You wrote a workaround — a manual step, a shim, a `|| true`, a hand-edit of generated output, a "do it outside the tool for now."

The moment you notice the workaround is the trigger. **A workaround you don't report is friction the next person re-hits.** Dogfooding only improves the tools if the friction becomes a tracked, fixable artifact.

This is a standing practice woven through all tool use, not a phase. It fires *as you work*, not at a checkpoint.

## Procedure

### 1. Identify the right repo
File in the **tool's own repo** (`pulseengine/<tool>`), not in the consuming project. If rivet misbehaves while you're shipping spar, the issue goes to `pulseengine/rivet`. If you can't tell which tool owns the friction, file in the one you invoked and cross-link.

### 2. Search for a duplicate first
`gh issue list --repo pulseengine/<tool> --search "<key phrase>" --state all`. If an open issue already covers it, add a comment with your fresh repro instead of opening a new one. Label-search for the friction label too.

### 2b. Check you are not reporting a gap that is already fixed

**A missing *capability* is the one friction class that expires.** Before filing
"tool X cannot do Y", confirm you are on a current version — record both numbers
in the issue:

```sh
<tool> --version
gh release list -R pulseengine/<tool> --limit 1
```

Embedded schemas and rule sets ship *inside* the binary, so a stale install
reports a stale capability. Three measured instances of this exact waste:

- a "the schema has no verification type" issue filed **13 days after** that type
  shipped — the reporter's binary was one release behind, and the fix had
  already landed;
- an agent session pinned to the **oldest** installed plugin version, silently
  hiding eight skills, so their absence looked like a capability gap;
- a machine running rivet **0.28.0 against a v0.32.0 release** — four minor
  versions of shipped fixes invisible to everything running there.

**Under a varve pin, name the layer as well as the version.** `varve which <tool>`
prints the binary, the layer and the manifest digest — so a capability gap filed from a
pinned project is reported against a *specific, reproducible* toolchain rather than
whatever happened to be on PATH:

```sh
varve which <tool>     # layer + digest — include this in the issue
<tool> --version
gh release list -R pulseengine/<tool> --limit 1
```

A pin makes staleness deliberate rather than accidental, but it does **not** make it
impossible: a project frozen on an old layer is exactly the case that produced the
13-days-late report above. If the pinned layer predates the fix, the finding is "our pin
is stale", not "the tool cannot do Y".

`varve status` is the intended home for this check — it carries the support window, known
problems and yank state for a line. As of **v0.14.0 it does not yet answer for a registry
install**: `varve install` auto-caches line-status only when the installed oci-layout
carries one, so an `oci://` install still exits 1 with `no line-status document cached for
line …`. Distribution over the registry is tracked as `REQ-STATUS-DIST-001`. Until that
lands, compare the pinned layer against the tool's releases by hand, as above.

A bug or a crash is worth filing immediately regardless. A *missing feature* is
worth thirty seconds of version-checking first, because the cost of getting it
wrong is a maintainer re-deriving a fix they already shipped.

### 3. File it automatically, then mention it
Open the issue without pausing the work, then note it in your response to the user (link + one line). Don't batch, don't wait for permission — friction is cheap to capture and expensive to forget. The body, kept short:

```
**What I was trying to do:** <the real task, one or two sentences>
**Tool + version:** <tool> <version / commit / "source @ <sha>">
**What happened:** <the error / wrong output / missing capability>
**Repro:** <the exact command(s) or input, minimal>
**Workaround used (if any):** <what I did instead, so the next person isn't blocked>
**Impact:** <blocked / slowed / cosmetic — be honest>
```

Use a consistent label so these are filterable and reviewable as a batch later:

```sh
gh issue create --repo pulseengine/<tool> \
  --title "friction: <short description>" \
  --label tool-friction \
  --body-file <body>
# create the label once per repo if missing:
gh label create tool-friction --color fbbf24 --description "Friction hit while using the tool for real work (dogfooding signal)" --force
```

### 4. Keep moving
Filing the issue is not a stop point. Note the workaround in the issue, apply it, and continue the task. The issue is the durable record; the work doesn't wait on the fix.

## What makes a good friction issue

- **The real task is in it.** "rivet check failed" is noise; "rivet check rejected a valid `verifies` link between a test and a sec-constraint while shipping spar v0.9" is signal — it tells the maintainer what use-case broke.
- **Minimal repro.** The smallest command/input that reproduces. If you can't minimize quickly, paste what you have and say so.
- **Honest impact.** Cosmetic friction and blocking friction need different triage. Don't inflate; don't omit.
- **The workaround is recorded.** Even a bad workaround is information — it shows what the tool failed to make easy.

## Anti-patterns

- **Silent workarounds.** The single failure mode this skill exists to kill. If you worked around a tool and didn't file, the friction is now invisible.
- **Batching everything to the end of the session.** You forget the specifics; repros decay. File when you hit it.
- **Filing in the consuming repo instead of the tool repo.** The fix lives where the tool lives.
- **Filing without searching for a dupe.** Noise erodes the signal of the `tool-friction` label.
- **A CLI that breaks [`pulseengine-cli-conventions`] is friction, not taste.** `--version` that
  errors or prints no version, an unknown flag exiting 1 instead of 2, structured output missing
  or spelled differently — these are filable defects with a named baseline behind them, and they
  block evidence recording. Do not soften them into preferences.
- **A mirror you were forced to create is friction, not test hygiene.** If you hardcoded a
  value in a test because the tool would not tell you what the value is, the finding is
  *"the tool cannot report its own constants"* — file it. Fixing it in the test only moves
  the debt. (synth: 38 harnesses mirror a compiler layout constant because the compiler
  cannot print it.)
- **Turning every preference into friction.** Friction is "the tool failed at what it's for," not "I'd have designed it differently." Disagreements about design are a different conversation.
- **Pausing the real work to perfect the issue.** Capture, link, continue. A terse-but-real issue beats a polished one you never filed.

## Where this composes

- [`pulseengine-feature-loop`] — friction surfaces at every step (spar passes, rivet validate, witness gaps, `wsc verify`); report it inline as you go.
- [`release-execution`] — the release-tail is where deferred friction tends to accumulate; the traceability completeness gate often surfaces tool gaps. File them rather than carrying them in your head.
- [`oracle-gate-a-change`] — when the oracle itself is the tool that's broken (the check won't run, or runs wrong), that's friction in the verifier — report it; a broken oracle is worse than a missing one.
