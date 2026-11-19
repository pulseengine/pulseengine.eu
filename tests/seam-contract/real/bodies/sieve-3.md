The CLI and JSON interface sieve provides to the fleet's CI and to plant's independent false-skip controls. Drafted in gale's handover and agreed with plant (2026-11-18): `--paths-file` and `graph` work without .git, internal failures carry the `internal:` reason prefix, and `sieve --version` names the schema versions.

```seam
format: 1
seam: sieve/classify-interface
kind: wire
status: implemented
provider:
  repo: pulseengine/sieve
  promise: "sieve.classify.v1 and sieve.graph.v1 keep their fields and meanings; a change bumps the schema name; every failure selects everything (run_all true), internal failures with the reason prefix internal:"
consumers:
  - repo: pulseengine/plant
    binding: "false-skip controls (plant#17) match the reason wording 'run-all path: <p> is CI, toolchain, build-system or sieve config' and 'run-all path: <p> is claimed by no class' (in the JSON reason and the stderr line), and parse `sieve classify --paths-file F --format json` (schema, run_all, reason, classes) without .git, and read `sieve --version` line 2 for the schema names"
  - repo: pulseengine/gale
    binding: "workflows read `sieve classify --format github-output` outputs <class>=true|false through the gated `!cancelled() && (needs.C.result != 'success' || needs.C.outputs.o != 'false')` form"
interface:
  - kind: file
    path: src/main.rs
    symbols:
      - 'pub const CLASSIFY_SCHEMA: &str = "sieve.classify.v1";'
      - 'pub const GRAPH_SCHEMA: &str = "sieve.graph.v1";'
      - '"schema": CLASSIFY_SCHEMA,'
      - '"run_all": v.run_all,'
      - '"unknown_paths": v.unknown_paths,'
      - '"inputs_hash": v.inputs_hash,'
      - '"unresolved": v.unresolved,'
      - 'pub const EQUIVALENCE_SCHEMA: &str = "sieve.equivalence.v1";'
      - 'pub const OBSERVE_SCHEMA: &str = "sieve.observe.v1";'
  - kind: file
    path: src/classify.rs
    symbols:
      - '"internal: build graph unreadable: {}: {}",'
      - 'format!("run-all path: {p} is CI, toolchain, build-system or sieve config")'
      - 'format!("run-all path: {p} is claimed by no class")'
decisions:
  - summary: "classify/graph CLI and JSON as drafted in gale's handover; plant's three requests (no .git for --paths-file and graph, internal: prefix, schema versions in --version)"
    decided_by: "owner (fleet adoption of sieve, relayed by gale and plant)"
    date: "2026-11-18"
    ref: "pulseengine/sieve#2"
  - summary: "v0.2.0, additive within sieve.classify.v1: `unresolved` (class to [{code, input}]) always, `explain` with --explain; `--version` line 2 also names sieve.equivalence.v1 and sieve.observe.v1. No field removed or renamed."
    decided_by: "owner (v0.2.0 scope, option dialogue)"
    date: "2026-11-19"
    ref: "pulseengine/sieve#6"
implemented_by: "pulseengine/sieve#2 (v0.1.0), #6 and #7 (on main; tag v0.2.0 pending)"
```


