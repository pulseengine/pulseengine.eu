---
name: port-with-equivalence
description: Use when existing Python (or another runtime-bound script) must move to Rust, because the no-new-Python rule says changed scripts port, a gate breaks on an interpreter or package update, or a tool should run as a WASI component on our own chain. It ports with the old script as the equivalence oracle.
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# Port with equivalence: the old script is the oracle

A port is a rewrite that must not change behaviour. The only cheap, honest proof
of that is the old implementation itself: run both on the same inputs and
compare. This skill is that procedure, written from three ports done on
2026-11-18/19: the North Star checker (pulseengine.eu#384, 3,016 of 3,016 cases
identical, as a WASI component), sigil's runner-guard checker (sigil#388), and
seam-check (pulseengine.eu#391, 290 of 290 identical, YAML via `rivet-yaml`).

**When:** the core rule says new tools are Rust, and existing Python moves to
Rust when it is changed anyway (a one-line fix during other work queues a port
instead). A port is also due when a gate breaks on the runtime rather than on
its logic: on 2026-11-19 a Homebrew update left `python3` 3.15 without PyYAML,
and seam-check exited "cannot check" on every tag.

## Steps

1. **Read the whole old script first**, including its self-test, every flag,
   exit codes and output lines. The port keeps all of them: same CLI, same
   stdout, same exit codes. Behaviour changes come in a separate change, before
   or after the port, never in it: without a fixed reference there is no oracle.
   If a change is needed, change the script first, then port with the changed
   script as the oracle (sigil's Required aggregator, decision 74b21d).
2. **Pick the parser and dependencies the fleet already uses.** YAML goes
   through `rivet-yaml`, pinned at an exact rev, then a tag. Prefer std plus
   what the old script used; shell out to `curl` where it did. A WASI component
   build (`wasm32-wasip2`) is the goal wherever the tool needs no host-only
   features, so it can run on our own chain (meld, loom, sigil, kiln) and count
   toward O5.
3. **Build the equivalence harness before trusting a line of the port.** It
   runs both implementations on the same inputs and asserts identical stdout
   and exit code. Inputs: every self-test case, recorded real fixtures (fetch
   them now and commit them; scrub private names and hosts), and seeded random
   cases where the input space allows it. Print the denominator ("290 of 290").
4. **Plant a mutant in the old script; the harness must fail.** One planted
   change that alters behaviour must break equivalence (the seam-check port used
   two: 3 and 81 cases differed). A harness that cannot fail proves nothing. If
   the reference cannot run (interpreter or package missing), the harness
   fails; it never skips.
5. **Name every allowed difference and pin it with a test.** Normalisations
   (e.g. a parser's error wording) are listed and counted. Known semantic
   differences are not hidden: YAML 1.1 versus 1.2 types 11 unquoted values
   differently; a test asserts those 11 still differ, and the docs tell users to
   quote them.
6. **Wire CI.** One job builds the tool and runs the harness, on the light
   self-hosted runner behind the fail-closed fork guard. Use a fresh target
   directory per tree and print a source fingerprint from inside the test
   binary: a shared `CARGO_TARGET_DIR` once made a comparison link the wrong
   build (the loom validator re-check, 2026-11-18).
7. **Keep the old script until the owner says otherwise.** It is the oracle
   while the port beds in. Removing it, and with it its entry in
   `scripts/python-frozen.txt`, is a separate change after the harness has been
   green on main.
8. **Ship it like any tool.** A signed release (cosign over `SHA256SUMS` from
   the tag workflow) so varve can carry it in the layer; a WASI component build
   as a separate asset when it exists.

## Report

The PR body states: cases compared and identical (N of N), normalisations and
known differences with their counts, the mutant results, the CI job name, the
`cargo test` exit code, and what the harness does not cover (stderr wording,
`--help` beyond line one, network paths, platform differences).

## Anti-patterns

- **Porting and changing behaviour in one change.** The oracle disappears.
- **A harness that skips when the reference is missing.** It reports green
  while comparing nothing.
- **Trusting a printed summary.** Check exit codes; `tail` once supplied the
  "exit 0" in a report (loom, 2026-11-19).
- **Deleting the old script in the porting PR.**
- **A new parser per tool.** The fleet shares `rivet-yaml`, so a YAML fix lands
  once.

## Where this composes

- [`oracle-gate-a-change`]: the old script is the oracle; the harness is the gate.
- [`gate-potency`]: the planted mutant is the negative control.
- [`release-artifact-pipeline`]: how the ported tool ships signed.
- [`claim-verification`]: the equivalence numbers in the PR body are claims.
