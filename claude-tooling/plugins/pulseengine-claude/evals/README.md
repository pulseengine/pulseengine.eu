# Plugin evals

Behaviour tests for the pulseengine-claude plugin, run with Claude Code's
`claude plugin eval` (https://code.claude.com/docs/en/plugin-evals.md). Each case runs
with and without the plugin; the score delta is what the plugin adds. Graders are
exact wherever possible (`tool_used` on the Bash command or Agent input, `regex` on
the answer or a file); `llm` (Haiku judge) only where the outcome is a judgement.

Run before a plugin release, from this plugin's root:

    PATH="$(echo "$PATH" | tr ':' '\n' | grep -v cryptexd | paste -sd: -)" \
      claude plugin eval . --scaffold --allow-tools Bash Agent --trust-plugin

macOS puts three unreadable cryptexd folders on the default PATH; the eval's Bash sandbox
refuses to start while any PATH folder cannot be examined, so drop them for the run.

Cases cover skills (ci-status, refactor-decision, publication-review,
delegate-by-cost, factory-notice), our tools (rivet commands over grepping YAML,
with-device for heavy disk work, the CI status API before gh) and the hooks'
lines (disk-pressure, loop-guard). Two runs per case; about 36 agent runs a pass.

## Baseline 2026-11-08 (plugin 0.57.1, 2 runs per arm, $5.62, 291 s)

| case | with | without |
|---|---|---|
| publication-review-before-ready | 1.0 | 0.0 |
| ci-status-before-polling | 1.0 | 0.5 |
| delegate-mechanical-to-haiku | 1.0 | 0.5 |
| disk-pressure-own-first | 1.0 | 0.5 |
| refactor-refused-in-rivet | 1.0 | 0.5 |
| loop-guard-changes-approach | 1.0 | 1.0 |
| rivet-asked-not-grepped | 1.0 | 1.0 |
| factory-notice-instead-of-waiting | 0.5 | 0.0 |
| mutants-through-with-device | 0.0 | 0.0 |

Open gaps: with-device for heavy disk work is not applied; the unattended-fork path
fires in 1 of 2 runs.
