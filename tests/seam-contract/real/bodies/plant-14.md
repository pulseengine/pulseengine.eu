The interface that relay, sigil, spar and other consumers bind to when they pin `plant guard` instead of their own copies of the fork-guard check (owner decision 2026-11-18, relayed by pulseengine.eu). It ships first in v0.2.0.

The promise: the command line `plant guard [DIR] [--config FILE] [--format text|json]`, the exit codes 0/1/2, the `plant-guard.toml` keys `fallback`, `labels` and `[[exempt]] workflow/reason`, and the JSON schema `plant.guard.v1` change only with a notice on this issue before the tag. A new rejection that narrows what passes is a fix, not a contract change, but it is announced here, because it can turn a consumer's CI red.

```seam
format: 1
seam: plant/guard
kind: consumption
status: proposed
provider:
  repo: pulseengine/plant
  promise: "plant guard's CLI, exit codes 0/1/2, plant-guard.toml keys (fallback as a string or a list, labels, exempt.workflow, exempt.reason) and JSON schema plant.guard.v1 change only with a notice on this issue before the tag"
  guard: tests/guard.rs
consumers:
  - repo: pulseengine/relay
    binding: "workflow-lint step switches from scripts/check-selfhosted-fork-guard.rs to a pinned plant guard release"
  - repo: pulseengine/sigil
    binding: "may replace verification/selfhosted-guard with a pinned plant guard"
  - repo: pulseengine/spar
    binding: "may replace tools/check-runner-guard with a pinned plant guard"
interface:
  - kind: file
    path: src/guard.rs
    symbols: ['pub const CONFIG_FILE: &str = "plant-guard.toml";', 'pub const DEFAULT_FALLBACK: &str = "ubuntu-24.04";', '    fallback: Option<Fallback>,', 'enum Fallback {', '    One(String),', '    Many(Vec<String>),', '    labels: Option<Vec<String>>,', '    exempt: Vec<Exempt>,', '    pub workflow: String,', '    pub reason: String,', '"schema": "plant.guard.v1",']
  - kind: file
    path: src/main.rs
    symbols: ['    Guard {']
open_questions:
  - {q: "which tag does each consumer pin, and do they pin through varve or the release URL?", owner: pulseengine/relay}
```

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01KEjmjZcSsvA9nXMcU5x24s

