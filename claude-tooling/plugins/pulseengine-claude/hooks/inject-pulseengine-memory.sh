#!/usr/bin/env bash
# SessionStart hook shipped with the pulseengine-claude plugin.
# Injects the core contract (core/pulseengine-core.md) whole, plus an index of
# the full memory files by absolute path, to be read on demand.
#
# Until 0.51.0 this concatenated every memory file (~48 KB). Claude Code cut
# that to a ~2.3 KB preview, so the operating contract never reached the model
# (2026-10-30 tuition study). The core is written to stay under the 9,500-char
# cap that scripts/check-hook-context-size.py enforces; emit_context cuts and
# points at a spill file if it ever does not.
ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
CORE="$ROOT/core/pulseengine-core.md"
MEM_DIR="$ROOT/memory"
[ -f "$CORE" ] || exit 0
# shellcheck source=lib-emit.sh
. "$(dirname "$0")/lib-emit.sh"

{
  echo "## PulseEngine core contract (injected by pulseengine-claude)"
  echo
  cat "$CORE"
  echo
  echo "## Full reference, read on demand"
  echo
  echo "The core above is the always-on part. The full files stay on disk; Read the one that fits before relying on what it covers:"
  for f in "$MEM_DIR"/*.md; do
    [ -e "$f" ] || continue
    case $(basename "$f") in
      pulseengine-operating-contract.md) what="the full operating contract, with the incidents behind each rule" ;;
      pulseengine-toolchain.md) what="every tool, what it is for, and the binary you actually type" ;;
      pulseengine-philosophy.md) what="falsification, defense-in-depth, MBSE, the three pillars" ;;
      pulseengine-repo-taxonomy.md) what="toolchain vs consumer repos, and which lens each takes" ;;
      pulseengine-cli-conventions.md) what="the CLI baseline every tool must meet" ;;
      pulseengine-prose-conventions.md) what="writing rules for commits, PRs, issues, posts, with measurements" ;;
      pulseengine-generated-media.md) what="what generated video or images may publish, and the EU AI Act line" ;;
      *) what="" ;;
    esac
    echo "- \`$f\`${what:+ — $what}"
  done
} | emit_context pulseengine-memory
exit 0
