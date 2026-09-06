# PulseEngine CLI conventions — the baseline every tool must meet

Applies to every binary shipped in the varve layer (currently `kilnd`, `loom`, `meld`, `ordeal`,
`rivet`, `spar`, `synth`, `witness`, `wsc`) and to any new tool joining it. **When building or
changing a tool's CLI, conform to this; when auditing one, check it.**

These are not style preferences. Each rule exists because its absence broke something measurable.

## The baseline

**1. `--version` and `-V` print `<binary-name> <semver>` and exit 0.**
The reported name is the **installed binary's** name — `witness`, not `witness-mcdc`; `wsc`, not
`wsc-cli`. Build metadata after the semver is welcome; rivet's
`rivet 0.32.0 (ec436b89 HEAD 2026-08-05)` is the model. A tool that cannot state its own version
cannot appear in evidence.

**2. `--help` exits 0. An unknown flag or command exits 2, with usage on stderr.**
One failure, one exit code. Callers cannot branch on a condition that returns 1 from one tool and 2
from another.

**3. Structured output is `--format json`, spelled the same everywhere.**
Any tool that emits results a gate might parse offers it, and advertises it in **top-level**
`--help` — not only on a subcommand, where nobody looks first. Grep-scraping human output is how
gates go vacuous.

**4. Subcommand vocabulary is shared — and a name means one thing across the toolchain.**
Where a concept already has a name, reuse it rather than inventing a synonym; where you need a new
concept, do not reuse a name that means something else somewhere. Already established by use:

| verb | tools | meaning |
|---|---|---|
| `verify` | loom, rivet, spar, synth, witness, wsc | check an artifact against its evidence |
| `keygen` | witness, wsc | generate a signing keypair |
| `attest` | witness, wsc | produce a signed statement about an artifact |
| `diff` | rivet, spar, witness | compare two versions and report the delta |
| `lsp` / `mcp` | rivet, spar | expose the tool to editors / agents |

**Live collision to fix, not to copy:** `bundle` means *"an artifact plus its link-graph closure"*
in rivet and *"a trust bundle for air-gapped verification"* in wsc. Same word, unrelated concepts,
in one toolchain a user drives in one session. Domain-specific verbs (`fuse`, `instrument`,
`allocate`, `disasm`) need no permission — the rule is about **collisions and synonyms**, not about
flattening vocabulary.

**5. Embedded docs are `<tool> docs`, with `docs <topic>` for a topic.**
Shipping documentation inside the binary is one of the best things this toolchain does — it works on
a fresh machine with no repo — but it is spelled three ways today: rivet has `docs` *and*
`quickstart`, witness has only `quickstart`, wsc has only `docs`. Converge on **`docs`** as the
command and topics beneath it; a bare `quickstart` alias for `docs quickstart` is fine (rivet's
shape). Agents and users should not have to guess which tool spells it which way.

**6. `--help` is user-facing, not a changelog or a traceability surface.**
Command descriptions say **what the command does**, in a first sentence that stands alone. They do
not carry requirement IDs, issue numbers, version tags, or repo-relative doc paths — that
provenance belongs in rivet artifacts, the CHANGELOG, and `docs`, all of which already hold it
properly. Measured leakage today: rivet's help carries **6 `REQ-*` ids and 7 issue refs**; witness
opens descriptions with their release provenance, e.g.

    cross-check   v0.36 (REQ-058) — cross-check two run JSON files from different backends

The reader wants the verb, not the ticket. Keep the traceability — move it to where it is queryable
(`rivet get REQ-058` answers this better than help text ever will).

**7. Help lines wrap at 100 columns; a command's description is one sentence.**
Detail belongs in `<tool> <cmd> --help` and `docs`, not in the top-level list. Measured: witness has
a single line of **497 characters** and 16 lines over 100 columns; rivet peaks at **405** with 11
over. kilnd, loom, meld, ordeal and wsc are all under 80 with none over — so this is achievable and
already achieved by five of nine.

**8a. The rule is now checkable — run it, don't remember it.**
`scripts/check-cli-conventions.py` (pulseengine.eu) takes a directory with a
`varve.toml` pin and checks every tool the layer carries. It uses `varve inspect`
as the oracle, so rule 1 is checked in its strong form: not *"prints something
semver-shaped"* but **"agrees with the version its own signed layer records."**
It exits `2` when it cannot check at all (no pin — every shim refuses, which is
varve working correctly) and `1` only for real violations, so a missing pin can
never be mistaken for a conformance failure.

Measured on layer `2026.08.2`, 2026-09-06: **9 checked, 5 violating** — `kilnd`,
`ordeal`, `spar` (no `--version`), `witness` (`witness-mcdc`), `wsc` (`wsc-cli`).
`spar` and `kilnd` also break rule 2 (unknown flag exits 1, not 2). The four
conforming tools all match their layer-recorded version, so there is no
provenance mismatch — only missing and mis-named identity. Tracked as
pulseengine.eu#183.

**8. Enforce 1–2 mechanically at release.** A release job that runs the freshly built binary and
asserts `--version` equals the tag being released. This is the fix varve adopted after shipping a
v0.14.0 binary that reported `0.13.1` (pulseengine/varve#38) — a `version-guard` job plus the
artifact-level assert. Without it, rule 1 is a request; with it, it cannot regress.

## Why — the measured state that produced these rules

Surveyed across one verified core, layer `2026.08.2` (`9 tool(s) match their signed digests`):

| behaviour | tools |
|---|---|
| `--version` → `name semver`, exit 0 | loom, meld, synth, rivet |
| reports a name that is **not** the binary | witness (`witness-mcdc`), wsc (`wsc-cli`) |
| prints **no version**, exit 1 | kilnd |
| **errors** on `--version`, `-V` and `version` | ordeal (exit 2), spar (exit 1) |

`spar` and `kilnd` expose a version **nowhere**; `ordeal`'s exists only as the first line of
`--help`. Structured output is advertised by two of nine (`rivet --format`, `spar --format/-o`).

**The cost is not cosmetic.** `rivet validate` on one unchanged tree returns FAIL/exit 1 under 0.19.0
and PASS/exit 0 under 0.32.0 — so evidence must carry the tool version — and that rule is
unexecutable for three of nine tools. For a toolchain whose product is qualification evidence,
"which binary produced this result" is an assessor question, and three tools cannot answer it.

Tracking: pulseengine.eu#167.

## Until a tool conforms

`varve which <tool>` reports the layer name and manifest digest, and works for **every** tool
regardless of its `--version` support. Under a pin, prefer it — it identifies the exact artifact
rather than a self-reported string. See [[pulseengine-toolchain]].
