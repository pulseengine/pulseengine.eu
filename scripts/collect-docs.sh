#!/usr/bin/env bash
# collect-docs.sh — Pull documentation from tool repos into Zola content.
#
# Docs live in each tool repo (e.g., rivet/docs/*.md). This script copies
# them into content/docs/{tool}/{version}/ with Zola frontmatter prepended.
#
# Usage:
#   ./scripts/collect-docs.sh rivet /path/to/rivet 0.3.0
#   ./scripts/collect-docs.sh spar  /path/to/spar  0.5.0
#
# On CI (release workflow), the tool repo calls this after checkout:
#   gh repo clone pulseengine/pulseengine.eu website
#   cd website && ./scripts/collect-docs.sh rivet ../rivet "$TAG"
#
# The script also:
#   - Copies raw markdown to static/docs/{tool}/{version}/ for AI agents
#   - Updates the docs index (static/docs/docs-index.json)
#   - Generates a _index.md for the tool if it doesn't exist

set -euo pipefail

TOOL="${1:?Usage: collect-docs.sh <tool> <repo-path> <version>}"
REPO="${2:?Usage: collect-docs.sh <tool> <repo-path> <version>}"
VERSION="${3:?Usage: collect-docs.sh <tool> <repo-path> <version>}"

SITE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONTENT_DIR="${SITE_ROOT}/content/docs/${TOOL}/${VERSION}"
STATIC_DIR="${SITE_ROOT}/static/docs/${TOOL}/${VERSION}"
DOCS_SRC="${REPO}/docs"

if [ ! -d "$DOCS_SRC" ]; then
  echo "Error: ${DOCS_SRC} does not exist"
  exit 1
fi

echo "Collecting docs: ${TOOL} v${VERSION} from ${DOCS_SRC}"

# ── Create target directories ──────────────────────────────────────────
mkdir -p "$CONTENT_DIR"
mkdir -p "$STATIC_DIR"

# ── Copy raw markdown for AI agents ────────────────────────────────────
cp "$DOCS_SRC"/*.md "$STATIC_DIR/" 2>/dev/null || true
echo "  → Raw markdown: ${STATIC_DIR}/"

# ── Generate Zola content pages ────────────────────────────────────────
for src in "$DOCS_SRC"/*.md; do
  [ -f "$src" ] || continue
  filename="$(basename "$src")"
  slug="${filename%.md}"

  # Skip if it's a _index
  [ "$slug" = "_index" ] && continue

  # Derive title from first H1, or from filename
  title="$(head -5 "$src" | grep '^# ' | head -1 | sed 's/^# //')"
  [ -z "$title" ] && title="$(echo "$slug" | sed 's/-/ /g; s/\b\(.\)/\u\1/g')"

  dest="${CONTENT_DIR}/${slug}.md"

  # Prepend Zola frontmatter, then the original content (skip the H1 line)
  cat > "$dest" << FRONTMATTER
+++
title = "${title}"
description = "${TOOL} v${VERSION} — ${title}"
template = "page.html"
+++

FRONTMATTER

  # Append content, skipping the first H1 line (Zola renders title from frontmatter)
  sed '0,/^# /{//d}' "$src" >> "$dest"

  echo "  → ${slug}.md"
done

# ── Create version _index.md ──────────────────────────────────────────
cat > "${CONTENT_DIR}/_index.md" << EOF
+++
title = "${TOOL} v${VERSION}"
description = "Documentation for ${TOOL} v${VERSION}"
template = "section.html"
sort_by = "weight"
+++

Documentation for **${TOOL} v${VERSION}**.

EOF

# List all pages
for src in "$DOCS_SRC"/*.md; do
  [ -f "$src" ] || continue
  filename="$(basename "$src")"
  slug="${filename%.md}"
  [ "$slug" = "_index" ] && continue
  title="$(head -5 "$src" | grep '^# ' | head -1 | sed 's/^# //')"
  [ -z "$title" ] && title="$(echo "$slug" | sed 's/-/ /g')"
  echo "- [${title}](/docs/${TOOL}/${VERSION}/${slug}/)" >> "${CONTENT_DIR}/_index.md"
done

echo "  → _index.md"

# ── Create tool-level _index.md (redirect to latest) ─────────────────
TOOL_INDEX="${SITE_ROOT}/content/docs/${TOOL}/_index.md"
cat > "$TOOL_INDEX" << EOF
+++
title = "${TOOL}"
description = "Documentation for ${TOOL}"
template = "section.html"
redirect_to = "/docs/${TOOL}/${VERSION}/"
+++
EOF
echo "  → tool index (redirect → v${VERSION})"

# ── Ensure top-level docs _index.md exists ────────────────────────────
DOCS_INDEX="${SITE_ROOT}/content/docs/_index.md"
if [ ! -f "$DOCS_INDEX" ]; then
  cat > "$DOCS_INDEX" << EOF
+++
title = "Documentation"
description = "PulseEngine tool documentation — versioned, per-tool, AI-accessible"
template = "section.html"
+++
EOF
  echo "  → created docs section index"
fi

echo "Done: ${TOOL} v${VERSION} → ${CONTENT_DIR}/"
