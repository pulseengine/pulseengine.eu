#!/usr/bin/env python3
# rivet: verifies REQ-VIEW-STYLED
"""Fail if the layer view's JavaScript emits a class the stylesheet does not define.

The view builds its entire DOM in `static/layers.js`; nothing in the Tera
template carries the per-row classes. So a class name that exists in the script
and not in `sass/_layers.scss` produces an element that renders unstyled, and
nothing else notices: the page still builds, `zola check` still passes, and the
defect is a table cell in the wrong colour halfway down a tab nobody opened.

This is not hypothetical. Porting the prototype into the site renamed classes in
bulk and four went wrong in ways that all built cleanly:

  * `el('span', 'pill c', ...)`   kept the pre-port name, so the pill lost its
    background and its tint.
  * `c.style.display = 'lv__none'` — a CSS *value* caught by the rename. The
    assignment is silently ignored, so all nineteen layer cards rendered at once
    instead of the nearest nine.
  * the version cell emitted `lv__val`, the styling was on `lv__v`.
  * a freshness span emitted `class="txt"` against a `lv__txt` rule.

Two checks, because they fail differently:
  1. every class the script emits is defined in the stylesheet;
  2. no CSS *value* assignment (display/position/etc.) was caught by a rename,
     which is how the `lv__none` bug read.

Exit: 0 consistent · 1 a mismatch · 2 could not run the check.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
JS = ROOT / "static" / "layers.js"
SCSS = ROOT / "sass" / "_layers.scss"
TEMPLATE = ROOT / "templates" / "layers.html"
DATA = ROOT / "static" / "layers.json"

PREFIX = "lv__"
# el('div', 'lv__card is-x')  ·  classList.add('in')  ·  class="lv__txt"
EL_CALL = re.compile(r"el\(\s*'([a-z][a-z0-9_]*)'\s*,\s*'([^']+)'")
EL_TAG = re.compile(r"el\(\s*'([a-zA-Z][a-zA-Z0-9_-]*)'\s*,")
CLASS_ATTR = re.compile(r'class="([^"]+)"')
CLASS_LIST = re.compile(r"classList\.(?:add|toggle|remove)\('([^']+)'\)")
# a modifier built by concatenation: 'lv__pill is-' + (...)
CONCAT = re.compile(r"'(" + PREFIX + r"[a-z0-9-]+(?: is-)?)'\s*\+")
SCSS_CLASS = re.compile(r"\.(" + PREFIX + r"[a-z0-9-]+|is-[a-z0-9-]+)")
# style.display = 'lv__...' — a class name where a CSS keyword belongs
BAD_VALUE = re.compile(r"style\.([a-zA-Z]+)\s*=\s*'(" + PREFIX + r"[a-z0-9-]*)'")
HTML_TAGS = {"div", "span", "button", "b", "em", "i", "p", "a", "code", "table",
             "thead", "tbody", "tr", "td", "th", "details", "summary", "h1",
             "h2", "h3", "h4", "ul", "li", "strong"}


def main() -> int:
    for f in (JS, SCSS, TEMPLATE):
        if not f.is_file():
            print(f"error: expected {f.relative_to(ROOT)}", file=sys.stderr)
            return 2

    js = JS.read_text(encoding="utf-8")
    scss = SCSS.read_text(encoding="utf-8")
    template = TEMPLATE.read_text(encoding="utf-8")

    defined = set(SCSS_CLASS.findall(scss))
    if not defined:
        print("error: no lv__ classes found in the stylesheet — the check "
              "examined nothing", file=sys.stderr)
        return 2

    emitted: dict[str, str] = {}      # class -> where it came from
    bad_tags = [t for t in EL_TAG.findall(js) if t not in HTML_TAGS]
    for tag, classes in EL_CALL.findall(js):
        for c in classes.split():
            emitted.setdefault(c, f"el('{tag}', '{classes}')")
    for m in CLASS_ATTR.findall(js):
        for c in m.split():
            emitted.setdefault(c, 'class="..." in layers.js')
    # The template also uses the site's own classes (container, page-section);
    # those are not the view's to namespace, so they are checked for existence
    # only if they carry the prefix.
    template_classes = {c for m in CLASS_ATTR.findall(template) for c in m.split()}
    for c in CLASS_LIST.findall(js):
        emitted.setdefault(c, "classList")
    # concatenated modifiers contribute their stem only
    for stem in CONCAT.findall(js):
        emitted.setdefault(stem.split()[0], "concatenated modifier")

    # A token ending in `-` is a concatenation prefix ('lv__mk is-' + kind),
    # not a class in its own right; the modifier it builds is dynamic.
    for c in template_classes:
        if c.startswith(PREFIX):
            emitted.setdefault(c, 'class="..." in layers.html')
    checked = {c: w for c, w in emitted.items() if not c.endswith("-")}
    unprefixed = {c: w for c, w in checked.items()
                  if not (c.startswith(PREFIX) or c.startswith("is-"))}
    missing = {c: w for c, w in checked.items()
               if c not in defined and c not in unprefixed}
    bad_values = BAD_VALUE.findall(js)

    print(f"{len(checked)} classes emitted by layers.js, "
          f"{len(defined)} defined in _layers.scss, {len(missing)} unstyled")

    if not checked:
        print("error: the script emitted no lv__ classes — the check examined "
              "nothing", file=sys.stderr)
        return 2

    ok = True
    if missing:
        ok = False
        print("\nClasses the script emits that the stylesheet does not define:",
              file=sys.stderr)
        for c, where in sorted(missing.items()):
            print(f"  .{c}\n      from: {where}", file=sys.stderr)
    if unprefixed:
        ok = False
        print("\nThe view owns the `lv__` namespace. These classes carry no "
              "prefix, which is what a name left behind by a rename looks "
              "like:", file=sys.stderr)
        for c, where in sorted(unprefixed.items()):
            print(f"  .{c}\n      from: {where}", file=sys.stderr)
    if bad_values:
        ok = False
        print("\nA class name is being assigned where a CSS value belongs. The "
              "assignment is ignored and the element keeps its previous style:",
              file=sys.stderr)
        for prop, val in bad_values:
            print(f"  style.{prop} = '{val}'", file=sys.stderr)
    if bad_tags:
        ok = False
        print(f"\nel() called with something that is not an HTML tag: "
              f"{sorted(set(bad_tags))}", file=sys.stderr)

    # the committed snapshot must be loadable, since the template reads it at build
    if DATA.is_file():
        try:
            d = json.loads(DATA.read_text())
            realms = d.get("realms", {})
            total = sum(len(r.get("order", [])) for r in realms.values())
            for name, r in realms.items():
                for tag in r.get("order", []):
                    if tag not in r.get("layers", {}):
                        print(f"\nlayers.json: {name} lists {tag} in `order` but "
                              f"has no such layer", file=sys.stderr)
                        ok = False
            print(f"layers.json: {len(realms)} realms, {total} layers, "
                  f"fetched {d.get('generated_utc', '?')}")
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"\nlayers.json does not parse: {e}", file=sys.stderr)
            ok = False

    if not ok:
        print("\nEither add the rule to sass/_layers.scss or correct the name in "
              "static/layers.js.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
