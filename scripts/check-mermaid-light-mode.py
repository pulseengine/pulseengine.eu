#!/usr/bin/env python3
"""Fail if a mermaid diagram uses a surface colour the light-mode patcher cannot map.

Mermaid compiles each `classDef` into CSS inside the rendered SVG's own <style>
tag, scoped by a dynamic id and marked !important, so outer CSS cannot override
it. The site therefore patches those stylesheets at runtime, rewriting dark hex
values to their cream equivalents (see templates/partials/content-scripts.html).

The failure mode this guards is asymmetric and easy to miss: the patcher knew
`#e1e4ed` (text) but not `#242836` (fill), so light mode rewrote the text to
deep navy and left the fill dark navy. Dark on dark. It did not look broken, it
looked washed out, which is why it survived.

Semantic accent colours are deliberately NOT mapped — green means good, amber
means warning, and they read on either background. They are allowlisted here so
the check does not flag them.

Exit: 0 every surface colour is mappable · 1 unmapped colours · 2 cannot check.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
SCRIPTS = ROOT / "templates" / "partials" / "content-scripts.html"

MERMAID_BLOCK = re.compile(r"\{%\s*mermaid\(\)\s*%\}(.*?)\{%\s*end\s*%\}", re.S)
HEX = re.compile(r"#[0-9a-fA-F]{6}")
# The left-hand column of the patcher's `replacements` array.
MAPPED = re.compile(r"\[\s*'(#[0-9a-fA-F]{6})'\s*,\s*'#[0-9a-fA-F]{6}'\s*\]")

# Semantic accents: meaningful, legible on both grounds, intentionally unmapped.
ACCENTS = {
    "#6c8cff",  # accent blue
    "#4ade80",  # green  — good / gate
    "#fbbf24",  # amber  — spine / warning
    "#22d3ee",  # cyan
    "#c084fc",  # purple — agent
    "#f87171",  # red
}


def main() -> int:
    if not SCRIPTS.is_file() or not CONTENT.is_dir():
        print(f"error: expected {SCRIPTS} and {CONTENT}", file=sys.stderr)
        return 2

    mapped = {m.lower() for m in MAPPED.findall(SCRIPTS.read_text())}
    if not mapped:
        print("error: found no replacement pairs in the light-mode patcher — "
              "the check examined nothing", file=sys.stderr)
        return 2

    unmapped: dict[str, set[str]] = {}
    blocks = 0
    for f in sorted(CONTENT.rglob("*.md")):
        text = f.read_text(encoding="utf-8", errors="replace")
        for block in MERMAID_BLOCK.findall(text):
            blocks += 1
            for hex_ in HEX.findall(block):
                h = hex_.lower()
                if h in mapped or h in ACCENTS:
                    continue
                unmapped.setdefault(h, set()).add(str(f.relative_to(ROOT)))

    print(f"{blocks} mermaid blocks, {len(mapped)} mapped colours, "
          f"{len(ACCENTS)} allowlisted accents, {len(unmapped)} unmapped")
    if not blocks:
        print("error: no mermaid blocks found — the check examined nothing",
              file=sys.stderr)
        return 2
    if not unmapped:
        return 0

    print("\nColours used in diagrams that light mode cannot remap:", file=sys.stderr)
    for h, files in sorted(unmapped.items()):
        print(f"  {h}\n      in: {', '.join(sorted(files))}", file=sys.stderr)
    print("\nAdd it to `replacements` in templates/partials/content-scripts.html, "
          "or to ACCENTS here if it is a semantic colour that reads on both "
          "backgrounds.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
