#!/usr/bin/env python3
"""Fail if any internal link in the built site points at a page that does not exist.

Why this exists rather than `zola check`: `zola check --skip-external-links`
validates Zola's own `@/path.md` internal-link syntax, but treats a raw
absolute href (`/docs/guide/compliance/`) as unchecked. Measured: with a
deliberately dead `/docs/guide/compliance/` link in content/docs/_index.md,
`zola check --skip-external-links` exits 0. Our content uses raw absolute
hrefs throughout, so that gate is vacuous here — it would report green over
exactly the links that rot.

Run AFTER `zola build`, against `public/`.

Note the parser detail that matters: Zola minifies output and emits
UNQUOTED attributes (`href=/docs/`), so a naive `href="([^"]+)"` pattern
matches nothing at all and reports a triumphant zero. Handle all three
quoting forms.
"""

from __future__ import annotations

import collections
import glob
import os
import re
import sys

ROOT = "public"
HREF = re.compile(r"""href=(?:"([^"]+)"|'([^']+)'|([^\s>"']+))""")


def main() -> int:
    if not os.path.isdir(ROOT):
        print(f"error: {ROOT}/ not found — run `zola build` first", file=sys.stderr)
        return 2

    pages = glob.glob(f"{ROOT}/**/*.html", recursive=True)
    dead: dict[str, list[str]] = collections.defaultdict(list)
    checked = 0

    for page in pages:
        html = open(page, encoding="utf-8", errors="replace").read()
        for m in HREF.finditer(html):
            url = (m.group(1) or m.group(2) or m.group(3)).split("#")[0].split("?")[0]
            # Site-internal only: absolute paths, not protocol-relative.
            if not url.startswith("/") or url.startswith("//"):
                continue
            checked += 1
            target = os.path.join(ROOT, url.lstrip("/"))
            if os.path.isfile(target) or os.path.isfile(os.path.join(target, "index.html")):
                continue
            dead[url].append(os.path.relpath(page, ROOT))

    print(f"{len(pages)} pages, {checked} internal links checked, {len(dead)} dead")

    # A run that checked nothing is a broken checker, not a clean site.
    if checked == 0:
        print("error: matched zero internal links — the checker is not working", file=sys.stderr)
        return 2

    if not dead:
        return 0

    print("\nDead internal links:", file=sys.stderr)
    for url, sources in sorted(dead.items()):
        srcs = sorted(set(sources))
        shown = ", ".join(srcs[:5]) + (f" (+{len(srcs) - 5} more)" if len(srcs) > 5 else "")
        print(f"  {url}\n      linked from: {shown}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
