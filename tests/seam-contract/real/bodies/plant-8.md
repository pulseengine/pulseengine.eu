plant's first release (v0.1.0) publishes two surfaces that other repositories bind to: the `ci-controls.toml` format and the GitHub Action's inputs and outputs. The block below writes them down, so `seam-check` goes red if either moves without a notice here first.

The only prospective consumer today is sigil: plant's `examples/sigil` (#4) turns sigil's fork-guard self-test into plant controls. That example is offered to sigil and not adopted, so the status is `proposed`.

```seam
format: 1
seam: plant/manifest-and-action
kind: consumption
status: implemented
provider:
  repo: pulseengine/plant
  promise: "the ci-controls.toml keys, the exit codes 0/1/2 and the action inputs manifest/only/format change only with a notice on this issue before the tag"
  guard: tests/selftest.rs
consumers:
  - repo: pulseengine/sigil
    binding: "sigil's own ci-controls.toml, copied from plant examples/sigil at ff7c538 plus matrix-include-mapping, run in the guard job by plant v0.2.0 pinned by cosign identity release.yml@refs/tags/v0.2.0 and sha256 (owner decision 20261117/7ed73c, adopted in sigil#392, merged as 5c6505d)"
interface:
  - kind: file
    path: src/manifest.rs
    symbols: ["const KNOWN_KEYS: &[&str] = &[", '    "id",', '    "check",', '    "run",', '    "plant",', '    "expect",', '    "stderr_or_stdout_matches",', '    "timeout",', '    "baseline",', '    "env",']
  - kind: file
    path: action.yml
    symbols: ["  manifest:", "  only:", "  format:", "  report:"]
open_questions: []
```


🤖 Generated with [Claude Code](https://claude.com/claude-code)


