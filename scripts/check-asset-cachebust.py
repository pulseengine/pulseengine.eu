#!/usr/bin/env python3
"""Fail if a template links a static asset without a cache-busting hash.

The deploy host sends no `Cache-Control` header — only `ETag` and
`Last-Modified`. With no explicit policy a browser caches heuristically, around
a tenth of the file's age, and does not revalidate inside that window. Asset
URLs are stable (`/main.css` never changes), so a returning visitor is served
whatever copy they already had.

That is not theoretical. After `/layers` shipped, a reader on Edge got the new
HTML and the new `layers.js` — both URLs the browser had never seen, so both
fetched — against a `main.css` from days earlier. Every rule the page needed was
missing while the markup and the script were current, so the layer cards
scattered across the page under their own inline transforms, the pills rendered
as a run of text, and the collapsing nav showed its button and all twelve links
at once. It looked like a browser bug and was a caching one.

`get_url(..., cachebust=true)` appends `?h=<content hash>`, so the URL changes
whenever the bytes do and the stale copy can never be reused. The real fix is a
`Cache-Control` header on the host; this gate is what we can enforce in the repo.

Checked here rather than in the built output so it needs no `zola build`, and so
the failure names the template line a reviewer has to edit.

Exit: 0 every asset is busted · 1 one is not · 2 could not run the check.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"

# get_url(path='main.css')  /  get_url(path="x.js", cachebust=true)
GET_URL = re.compile(r"get_url\(\s*path\s*=\s*['\"]([^'\"]+)['\"]([^)]*)\)")
# Only files the browser caches as a versioned asset. Pages (@/about.md),
# feeds and images are out of scope: a page must not carry a query string,
# and an image that changes is normally a new file.
ASSET = re.compile(r"\.(css|js|json)$", re.I)


def main() -> int:
    if not TEMPLATES.is_dir():
        print(f"error: expected {TEMPLATES}", file=sys.stderr)
        return 2

    checked = 0
    naked: list[tuple[str, int, str]] = []
    for f in sorted(TEMPLATES.rglob("*.html")):
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for path, rest in GET_URL.findall(line):
                if not ASSET.search(path):
                    continue
                checked += 1
                if "cachebust" not in rest:
                    naked.append((str(f.relative_to(ROOT)), n, path))

    print(f"{checked} static asset references, {len(naked)} without a cache-busting hash")
    if not checked:
        print("error: found no asset references — the check examined nothing",
              file=sys.stderr)
        return 2
    if not naked:
        return 0

    print("\nAssets linked at a stable URL, which a browser may serve from cache "
          "after a deploy:", file=sys.stderr)
    for where, n, path in naked:
        print(f"  {where}:{n}  {path}", file=sys.stderr)
    print("\nAdd `cachebust=true`:  "
          "{{ get_url(path='main.css', cachebust=true) }}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
