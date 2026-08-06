#!/usr/bin/env python3
"""Bundle a rendered talk into ONE self-contained HTML file.

A served deck depends on a working local server, on the browser not upgrading a
plain-HTTP LAN address to HTTPS, and on nothing between the laptop and the
screen. A presentation should not depend on any of that. This inlines the
stylesheet, the fonts and the terminal recordings so the result opens from disk,
offline, in any browser.

    python3 tools/bundle-talk.py publications/wasm-research-day-2026
"""
import base64, pathlib, re, sys

root = pathlib.Path(__file__).resolve().parent.parent
slug = sys.argv[1] if len(sys.argv) > 1 else "publications/wasm-research-day-2026"
html = (root / "public" / slug / "index.html").read_text()
# A stale slug points at an alias REDIRECT stub, not the deck -- the bundler then
# writes a ~500 B file and reports success. Fail loudly instead.
if "<section" not in html:
    raise SystemExit(
        f"ERROR: public/{slug}/index.html has no slides ({len(html)} B) -- "
        "wrong slug, or it is an alias redirect stub. Nothing written.")
# A BOM survives read_text() and, unlike a fetched stylesheet, is NOT stripped
# inside an inline <style>: "<style>\ufeff:root{...}" makes that first selector
# invalid and the browser DROPS the whole rule. That rule is the dark base
# palette, so the bundle rendered black-on-transparent in dark mode while light
# mode (whose overrides come later) looked fine.
css  = (root / "public" / "main.css").read_text().lstrip("\ufeff")

# Fonts -> data URIs, so there is nothing left to fetch.
def embed_font(m):
    name = m.group(1)
    f = root / "public" / "fonts" / name
    if not f.exists():
        return m.group(0)
    b64 = base64.b64encode(f.read_bytes()).decode()
    return f'url(data:font/woff2;base64,{b64}) format("woff2")'
css, n_fonts = re.subn(r"""url\(/fonts/([^)]+\.woff2)\)\s*format\((?:'|")woff2(?:'|")\)""", embed_font, css)

# Recordings -> a JS object, because fetch() is blocked on file://
casts = {}
for m in re.finditer(r'data-cast=([^\s">]+)', html):
    ref = m.group(1)
    f = root / "public" / ref.lstrip("/")
    if f.exists():
        casts[ref] = f.read_text()
cast_js = "window.__CASTS = {" + ",".join(
    "%s:%s" % (repr(k), repr(v)) for k, v in casts.items()) + "};"

html = re.sub(r'<link href=[^>]*main\.css[^>]*>', "<style>" + css + "</style>", html, count=1)
html = re.sub(r'<link[^>]*rel=icon[^>]*>', "", html, count=1)
html = html.replace("<script>", "<script>" + cast_js, 1)

out = root / "dist" / (slug.split("/")[-1] + ".html")
out.parent.mkdir(exist_ok=True)
out.write_text(html)
print(f"{out}  ({out.stat().st_size:,} bytes)  fonts inlined: {n_fonts}  recordings: {len(casts)}")
