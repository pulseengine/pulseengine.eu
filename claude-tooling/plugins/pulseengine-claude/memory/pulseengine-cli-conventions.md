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

**4. `verify` is the shared verb** for "check this artifact against its evidence." Already true of
six of nine tools; keep it. Domain-specific verbs (`analyze`, `inspect`, `fuse`) stay
domain-specific — the convention governs the shell of the CLI, not its vocabulary.

**5. Enforce 1–2 mechanically at release.** A release job that runs the freshly built binary and
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
