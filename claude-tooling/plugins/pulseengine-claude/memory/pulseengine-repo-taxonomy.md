# PulseEngine repo taxonomy — which kind of work am I in?

PulseEngine work splits into two categories, and the methodology applies
differently to each. **Identify which one the current repo is before
choosing how to work** (the situational-awareness hook prints a best-effort
guess at session start; confirm it from the repo itself).

## 1. Toolchain development — building the tools

Repos whose product *is* a verification/build tool. The methodology turns
*inward*: the tool must prove its own correctness.

Examples: `rivet`, `spar`, `witness`, `sigil`, `meld`, `loom`, `synth`,
`kiln`, `gale`, `scry`, the Bazel rule sets (`rules_lean`,
`rules_rocq_rust`, `rules_verus`, `rules_wasm_component`, `rules_moonbit`),
plus infrastructure (`smithy` runners, `mcp` framework, `temper`).

Focus here:
- **Oracle-gate the tool's own behavior** — the mechanical oracle is the
  tool's own check/pass/proof (e.g. synth's transcode-equivalence, witness's
  truth-table, loom's optimization-preserves-semantics).
- **The release-artifact pipeline** is part of the product — signed
  `SHA256SUMS`, SBOM, SLSA, cosign (see [`release-artifact-pipeline`]).
- The tool **dogfoods** the chain on itself: rivet emits its own compliance
  report; witness runs MC/DC on its own Wasm; sigil signs its own releases.
- `pulseengine-feature-loop` applies to the *tool's* features, but the
  "architecture" step is often the tool's own design, not an AADL model.

## 2. Toolchain consumers — building verified products

Repos that *use* the toolchain to build a real, verified application. The
methodology turns *outward*: compose the tools end-to-end.

Examples: `wohl` (home supervision), `relay` (flight software),
`example-kvs`, and other applications (this list grows — classify by role,
not by memorising names).

Focus here:
- **`pulseengine-feature-loop` is the primary mode**: spar (AADL) → WIT →
  rivet typed traceability → oracle-gated code → witness MC/DC → sigil
  attestation → clean-room verify. The architecture step is a real model.
- The value is *composition* — proving the application correct *through*
  the tools, with traceability from requirement to shipped Wasm.
- The release gate is the V-model completeness check (see
  [`release-execution`]): every approved/implemented artifact traced + tested.

## Dual-role and edge cases

Some repos are both: `scry` is a tool **and** dogfoods witness MC/DC;
`rivet` is a tool **and** produces a consumer-style compliance report. When
a repo is dual, apply the inward lens to its own code and the outward lens
to what it produces. Repos like `automator`, `glsp-mcp`, `studio-mcp`,
`bazel-file-ops-component` are tooling/support — treat as category 1.

If a repo is **not** a PulseEngine repo at all (a fork, an upstream
dependency, a scratch repo), the methodology framing still informs *how* to
work, but don't force the toolchain onto it.

## Why this matters

Reaching for `pulseengine-feature-loop` in a tool-development repo (where
there's no AADL model to start from) wastes effort; skipping it in a
consumer repo (where composition *is* the point) drops the evidence chain.
Pick the lens that matches the repo's role.
