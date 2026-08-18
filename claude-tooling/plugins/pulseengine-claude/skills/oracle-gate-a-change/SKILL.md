---
name: oracle-gate-a-change
description: This skill should be used whenever proposing, designing, landing, or evaluating a consequential change on a PulseEngine project (rivet, spar, witness, sigil, meld, loom, synth, wohl) — including "propose a change", "add a feature", "fix a bug", "is this safe to land", "what verifies this", "what's the gate", "how do we know this is correct", "before merging this", or whenever a code change needs a mechanical check to back it. ALWAYS use this skill before claiming a property holds and before recommending a change be merged.
metadata:
  author: pulseengine.eu
  version: "0.5.0"
---

# Oracle-gate a change

## When this fires

Before any consequential change lands on a PulseEngine project. The gate is **mechanical** — a check that fires or doesn't, not an LLM reading the spec back. The skill picks the right oracle for the kind of claim, writes it first if it doesn't exist, and refuses to call the change "done" until red flips to green.

This is distinct from [`clean-room-verification`], which validates *findings* before reporting. Oracle-gating runs at the *system* layer: it's how an agent's "I changed X" earns the right to be merged.

## Procedure

### 1. Name the kind of claim the change makes

Before anything else: what is this change asserting? Pick the right oracle for the claim type:

| Claim type | Mechanical oracle (PulseEngine toolchain) |
|---|---|
| Type / schema / traceability claim | `rivet validate`, `rivet check`, `rivet coverage` |
| Architecture / scheduling / WIT generation claim | spar analysis pass (one of 27+: EMV2 fault trees, ARINC 653 partitioning, ASIL decomposition, modal-filtered scheduling, piecewise-affine TSN arrival curves) |
| Branch / decision / MC/DC coverage on a Wasm artifact | `witness` truth-table gap report — **the gap view, not a coverage percentage**. The percentage is the wrong artifact. |
| Build-stage integrity / attestation | `sigil` verification chain |
| Memory-safety / UB / overflow / dedup-logic | Kani BMC (used in wohl + synth), Verus (used in wohl/AlertDispatcher) |
| Property-based / state-explosion search | fuzz harness (cargo-fuzz / synth's gale fuzzer), z3-backed verifier in synth-verify |
| Symbol-elimination claim (e.g. cross-language LTO) | `nm <artifact.elf> | grep <symbol>` returning zero. From the gale → zephyr LTO work. |
| Coverage gap | `rivet coverage` against the schema-defined trace topology |

If the claim doesn't fit any of these, the change is making a fuzzy claim that can't be mechanically backed. **Sharpen the claim or escalate** — fuzzy claims should not gate merges.

### 2. If no oracle exists for the claim, write the oracle first

This is the most-skipped step and the highest leverage one. If the change claims a new property and no test / `rivet check` / proof obligation / fuzz harness / `nm` invocation currently fires red-or-green for that property:

- **Write the oracle first.** Add the test that would currently fail. Add the `rivet check` rule. Write the Kani harness. Add the fuzz target.
- **Land the oracle separately if possible** so its red state is visible before the change that's supposed to flip it green. This makes the gate's behavior observable.

If you cannot write the oracle (the property isn't checkable with current tooling), **surface the gap clearly** in the PR description. Do not paper over it with prose review. Either the property is checkable or the change can't claim it.

### 2b. Wire it — an oracle CI does not run is not a gate

Writing a correct oracle and landing it is **not** gating. An oracle that nothing executes satisfies every other step in this skill and gates nothing. Landing an oracle means landing **its invocation** in the same change.

This is the one step where doing it wrong feels identical to doing it right: you run the oracle locally, it works, red→green happens on your machine, and it feels finished. The failure surfaces months later as a green board over a dead gate.

- **Wire it into a job that runs on PRs**, and **prove it fails there** — not merely locally. *"It passes locally"* and *"the gate passed"* are different claims.
- **Prove the wiring by mutation at the point of wiring.** Break the property, watch the *wired* job go red, restore. Anything less proves the oracle exists, not that it is enforced.
- **Prefer an already-required context.** A brand-new job is not a required check and can sit red for weeks — the same failure mode one level up. Putting the new check inside a job that is already required makes it bite on day one.
- **Declared ⇒ invoked.** If the repo keeps a registry of checks/repro scripts, adding an entry is not wiring; something must run it. Track undeclared/unwired scripts as a countable number that can only shrink.

Field cases this rule comes from: an oracle behind two headline size claims existed for two releases and was never CI-wired; the next release shipped its central differential oracle referenced by nothing, with a fully green PR board; a later audit found ~70 of ~150 repro scripts undeclared or unwired.

### 2c. Confirm the oracle is RED — before implementing

Writing the oracle and wiring it still leaves the question the whole method rests on unanswered:
**does it fail when the property is false?** Run it *before* the implementing change and read the
result. **An oracle that passes before the change is not an oracle** — it is measuring something
other than the property, and it will ship as evidence.

The two commonest causes, both of which look correct in review:

- **The predicate is satisfied by the initial or default state.** Zero-initialised values, empty
  collections, absent files, a fresh entry point. The assertion is true before the feature exists.
  Fix by making it position- or state-specific, not merely existential.
- **It is an upper bound where a presence check was needed.** Field case, in this plugin's own gate:
  `claim-check`'s `count-max` fails only when `n > max`, so a pattern matching **0** times stays
  green — the code's own comment now reads *"greens a 0-match, since 0 > max is false"*. A claim
  binding a doc's version string to `count-max` therefore went green precisely when the version
  drifted and the string vanished. The `count-min` predicate exists to catch that drift-to-absent
  case; pick the polarity that matches what you are asserting.

**A fixture chosen after the property is written is suspect.** If you picked the input *because* the
test passed, you may have selected around the failing case. Ask what the property claims in general
and whether your fixture is the easy instance.

This applies to **gates as much as tests**. A CI check whose predicate can silently match nothing is
the same failure with a longer blast radius, because a green check is read as evidence by everyone
downstream. Step 2b proves the gate *runs*; this step proves it can *fail*. Both are required —
see [`gate-potency`] for auditing checks that are already live.

### 3. Attach a kill-criterion to the claim

Per PulseEngine methodology, every claim should carry a falsifiable kill-criterion: "this claim would be wrong if X is observed." This is required for the philosophy to compose — without kill-criteria the falsification stance is empty.

**The prompt that generates the good ones:** *name the thing that would still be false if every
check you can run passes.* That question is what produces criteria worth having, and it is the step
most often skipped — a criterion derived from the checks you already have can only restate them.

Where the answer is a check **someone else** must run, say so in the requirement and treat it as
blocking: see [`traceability-audit`] on externally-owned criteria.

Examples:
- "AlertDispatcher dedup is correct" → kill-criterion: "if Verus flags a duplicate-acceptance path."
- "Cross-language LTO eliminated gale symbols" → kill-criterion: "if `nm zephyr.elf | grep gale_` returns non-zero."
- "PR doesn't drop trace coverage" → kill-criterion: "if `rivet coverage` reports a new uncovered predicate."

### 4. Gate the diff

Only the diff that flips the oracle from red to green counts. Specifically:
- If the oracle was already green before the change: the change must add a new oracle that goes red→green on this diff, or this change isn't actually verified.
- If the oracle was red: the change should flip it green. If green wasn't reached, the change isn't ready.
- If the oracle's behavior was unchanged: the change is doing something the oracle doesn't measure. Either expand the oracle or shrink the claim.

### 4b. Record *which* oracle — a version-less claim is unfalsifiable

The skill has always said to run the oracle. It never said **which build of it**. Citing a tool
result as evidence without its version is the same error as citing a benchmark without hardware.

- **Record the tool version alongside the result**, and state explicitly whether it matches what CI
  runs. `<tool> --version`; under a pin, `varve which <tool>` gives the layer and manifest digest.
- **`--version` is not universal in this toolchain — prefer the layer identity.** Measured across
  layer `2026.08.2`: `--version` works on 6 of 9 tools, **errors** on `ordeal` (exit 2) and `spar`
  (exit 1), and prints no version at all on `kilnd`. `ordeal`'s version appears only as the first
  line of `--help`; `spar` and `kilnd` expose none anywhere. So a rule built on `--version` alone is
  unexecutable for a third of the toolchain — `varve which <tool>` (layer + manifest digest) is the
  identity that exists for **all** of them, and is more precise anyway. The baseline every tool
  must meet is [`pulseengine-cli-conventions`]; tracked as pulseengine.eu#167.
- **A local pass on a different version is `suspected`, not `verified`.** This is the same
  distinction this skill already draws between *"the oracle passed"* and *"the gate passed"* — it
  just extends to *which* oracle.

**Measured, not hypothetical.** Three rivet versions over one identical tree (varve @ `a640673`,
158 artifacts):

| rivet | result | exit |
|---|---|---|
| 0.19.0 | **FAIL** — 60 errors, 62 warnings | 1 |
| 0.28.0 | **FAIL** — 60 errors, 72 warnings | 1 |
| 0.32.0 | **PASS** — 72 warnings | 0 |

The verdict *flips*, not just the counts — so "I ran the oracle and it passed" can be false in
either direction:

- **An old binary's FAIL can be an artifact of its own schema, not a finding.** Here the errors are
  `unknown artifact type 'verification'` — 0.19 rejects a type the newer schema ships. Chasing that
  as a defect burns a cycle on a tool gap.
- **An old binary's PASS can miss rules it never implemented.** The silent direction, and the
  dangerous one, because it ships as evidence.

Both are the schema-capability question [`traceability-audit`] step 0 already asks — the same check,
one layer down: *does this binary implement the rules I am claiming it enforced?*

**Watch the pin direction.** When CI pins old and developers run new, the required gate becomes the
**laxest** check in the system — a local run catches strictly more than the thing that can block a
merge, inverting what pinning is for. Field case: relay's `verification-gate.yml` and `release.yml`
pin rivet **v0.19.0** while the current layer ships **0.32.0**.

### 5. Verify before reporting "done"

Apply [`clean-room-verification`] to the claim "this change passed its oracle." An agent saying "I ran the test and it passed" is itself an unverified claim — actually re-run the oracle in a clean environment and read the output.

## The rules baked in

- **A "done" without a flipped mechanical oracle is unverified.** No exceptions for "small" changes.
- **Soft oracles (LLM reading the spec back) don't count.** They cannot find what the spec didn't anticipate. From the `mythos-slop-hunt` and `spec-driven-development-is-half-the-loop` blog posts.
- **Write the oracle first if it's missing.** If the property is worth claiming it's worth checking.
- **Specification completeness is the bottleneck.** Per `formal-verification-ai-agents`, agent-written proofs are cheap now — the limiting factor is whether the spec covers what the change is actually doing.
- **Kill-criteria are mandatory.** A claim without a falsifier is not a claim, it's a hope. And necessary is not sufficient: **a kill-criterion nobody evaluates is not a gate** — see step 2b.
- **The instruments rot last, and invisibly.** Once the artifact under test is well covered, residual defects migrate into the *checkers*, where they are structurally hard to see because the instrument's whole job is to report "fine". Two sibling repos sharing no code independently grew the same four instrument bugs. Common footguns, all field-observed:
  - a gate parsing a results path the tool never writes (4 months of vacuous green; 210 survivors reported as 0),
  - a formatter/linter scoped to 1 of N workspaces,
  - a checker built in the tool and wired into no workflow,
  - a self-exemption escape hatch that every violation happens to use (all 12 `sorry`s carried the exempting comment),
  - `cargo test -- <filter matching nothing>` exiting 0,
  - a crashed tool run scored as a clean one,
  - a paths-filter whose error path fails **open**, skipping required contexts — on GitHub a *skipped* required context satisfies the merge button, so a filter is a gate-disabler.
- **Missing evidence is red, never green.** An absent results file must fail the gate, not default to a clean count.
- **A documented gap with an "unreachable" judgment is a standing obligation, not a closed item.** Re-verify the reachability claim whenever a new code path lands near the gap. Field case: an independently-mechanized model bridge documented a semantics divergence as "unreachable via input masking" — a later code path made it reachable, and the divergence let a vacuous proof certify hardware-wrong code for weeks.
- **Byte-changing fixes re-pin goldens only AFTER the full differential suite passes on the new bytes.** They move together; a re-pin before the differentials is a frozen lie. Keep a printable re-pin aid inside the gate itself (an env-gated branch that emits the new golden tuples instead of asserting) so the ritual is mechanical, not hand-copied.

## Exit-code discipline

A gate's verdict is an **exit code**, so the ways a step silently exits 0 are the ways a gate goes
inert. Each of these has cost real time in this org:

- **`set -o pipefail` without `-e`** — the step's status is its *last* command's, so a failing
  oracle followed by a passing `grep` is **green**. Use `set -euo pipefail`.
- **`cmd | tail && echo OK`** — the `&&` binds to `tail`, which always succeeds.
- **`cargo test -- <filter>` matching nothing** — prints `0 passed` and **exits 0**. Assert the test
  count, or assert the filter matches.
- **`cargo build` does not compile `#[cfg(test)]` code** — signature breaks in test helpers stay
  invisible until `cargo test`.
- **A mutation/patch that no longer applies** silently stops mutating, and the mutation test then
  passes *for the wrong reason*. Make a non-applying patch **fatal**, never a skip.
- **A gate reading a JSON summary must check the run completed** — a crashed or timed-out tool run
  is not a pass. Check the exit code and a completion marker, not the summary line.
- **Comment-demotion in YAML** — YAML strips `#` only in a *single-line plain scalar*; inside
  `run: |` the `#` survives. So a grep-for-reference gate can be satisfied by a **commented-out**
  step. Field case: a wiring gate was itself defeated this way.

## Anti-patterns

- **"The oracle exists" as the deliverable.** The deliverable is the oracle **running in CI and
  demonstrably able to fail there**.
- **Asserting a gate is non-vacuous by *reading* it rather than by *mutating* it.** Vacuous gates
  look correct in review — that is exactly why they survive. Break the property and watch for red.
- **Running the oracle for the first time *after* the implementation.** A green result then is
  ambiguous — it cannot distinguish "the change works" from "this never measured anything." The
  red observation is not a formality; it is the only evidence the oracle discriminates at all.
- "Review looks good" as the gate. Review is input; oracle is the gate.
- "Tests pass" without saying *which* test exercises the new property. If you can't name it, it doesn't exist.
- Skipping the oracle write because "we already have lots of tests." The relevant question is whether *this property* is checked, not whether *anything* is.
- Treating `rivet validate` green as proof the change is correct. `rivet validate` is one oracle of many; pick the one matching the claim type.

## Where this composes

`pulseengine-feature-loop` runs this skill per change inside the feature loop. `release-execution` expects every PR in the queue to have passed through this gate before merge. Verification of the oracle-passed claim flows to [`clean-room-verification`].
