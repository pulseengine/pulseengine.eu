#!/usr/bin/env bash
# SessionStart hook (pulseengine-claude): in a rivet project, inject the state
# the agent would otherwise re-derive by grepping artifact YAML — loaded schemas,
# typed artifact counts, the validate verdict, and the coverage rules that are
# not yet closed — plus the command surface to use instead of text munging.
#
# Read-only by construction. `rivet context` would produce a richer document but
# always writes .rivet/agent-context.md, which is untracked in most repos (only
# rivet itself gitignores it), and a SessionStart hook must not dirty a working
# tree. So this uses the read-only commands and points at `rivet context` for the
# agent to run deliberately.
#
# No network. Fails open: any error yields no injected context.

emit() {
  if command -v jq >/dev/null 2>&1; then
    jq -Rs '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: .}}'
  fi
}

command -v rivet >/dev/null 2>&1 || exit 0

# rivet resolves its project from the working directory; only speak up if there
# is one here or at the repo root.
root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -f rivet.yaml ] || { [ -n "$root" ] && [ -f "$root/rivet.yaml" ] && cd "$root"; } || exit 0
[ -f rivet.yaml ] || exit 0

validate_out="$(rivet validate 2>/dev/null || true)"
verdict="$(printf '%s' "$validate_out" | grep -m1 '^Result:' || true)"
schemas="$(printf '%s' "$validate_out" | grep -m1 '^Schemas:' | sed 's/^Schemas: //' || true)"
[ -n "$verdict" ] || exit 0   # not a resolvable project — stay quiet

counts="$(rivet stats 2>/dev/null | awk 'NF==2 && $2 ~ /^[0-9]+$/ {printf "%s %s, ", $1, $2}' | sed 's/, $//')"

# Only the rules that still have something to close — a wall of 100.0% is noise.
gaps="$(rivet coverage 2>/dev/null | awk '
  $3 ~ /^[0-9]+$/ && $4 ~ /^[0-9]+$/ && $4 > 0 && $3 < $4 {printf "  - %s: %s/%s\n", $1, $3, $4}')"

{
  echo "## rivet project (injected at session start)"
  echo
  echo "- **Validate:** ${verdict#Result: }"
  [ -n "$schemas" ] && echo "- **Schemas:** ${schemas}"
  [ -n "$counts" ] && echo "- **Artifacts:** ${counts}"
  if [ -n "$gaps" ]; then
    echo "- **Coverage rules not yet closed:**"
    printf '%s\n' "$gaps"
  fi
  echo
  echo "**Use rivet's own commands — do not grep/jq/sed the artifact YAML.** The tool answers these"
  echo "directly, and its built-in docs are versioned with the binary while a skill is not:"
  echo
  echo '    rivet docs [topic]    authoritative reference; `rivet docs cli` lists every command'
  echo '    rivet get <ID>        one artifact resolved, with links and fields'
  echo "    rivet query '(and (= type \"requirement\") (!= status \"verified\"))'"
  echo '    rivet list | stats | coverage | trace <ID> | impact <ID> | bundle <ID>'
  echo '    rivet add | link | modify | remove | next-id     mutate; never hand-edit YAML'
  echo
  echo "\`rivet context\` writes a fuller \`.rivet/agent-context.md\` (schema, link types, rules) —"
  echo "run it deliberately when doing traceability work; note it creates an untracked file."
} | emit
