#!/usr/bin/env python3
"""Count gale's Verus trusted base from a gale checkout.

Usage:
    python3 -I scripts/count-gale-trusted-base.py <gale-checkout> [--json]

The site quotes gale's trusted-base size (templates/about.html and
content/docs/gale/). This script re-derives it from source so the figure can
be re-checked against any gale commit. Claim SITE-GALE-TRUSTED-BASE-COUNT in
claims.yaml pins the numbers and the commit the site cites.

Count rule (the reported figure)
--------------------------------
gale's ledger (docs/safety/verification-honesty.md) defines the inventory as
"`#[verifier::external_body]` instances and `assume_specification` calls across
the verified surface". The script counts exactly that:

* Scope: every ``*.rs`` file under ``src/`` (the Verus crate; gale's
  BUILD.bazel ``VERUS_SRCS`` lists only ``src/`` files). ``plain/`` is the
  Verus-stripped copy and ``tests/``, ``benches/``, ``tools/`` are not verified,
  so they are reported for information only.
* Comments (``//``, ``///``, ``//!``, nested ``/* */``) and string/char
  literals are removed first, so a doc comment that *mentions* the attribute is
  not counted as an instance of it.
* ``external_body``: the attribute ``#[verifier::external_body]`` or the older
  spelling ``#[verifier(external_body)]``.
* ``external_fn_specification``: ``#[verifier::external_fn_specification]`` /
  ``#[verifier(external_fn_specification)]`` (older Verus form of an assumed
  external spec; counted separately).
* ``assume_specification``: each ``assume_specification`` item.

Comparison rules (printed so other quoted figures can be reproduced)
--------------------------------------------------------------------
* ``line-fixed-string``: lines in ``src/*.rs`` containing the literal text
  ``#[verifier::external_body]``, comments included (``grep -F -c``).
* ``line-substring-ledger-modules``: lines containing ``external_body`` in the
  nine modules listed in the ledger's per-module table, comments included.

Standard library only.
"""

import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

EXTERNAL_BODY = re.compile(r"#\s*\[\s*verifier\s*(?:::\s*external_body|\(\s*external_body\s*\))\s*\]")
EXTERNAL_FN_SPEC = re.compile(
    r"#\s*\[\s*verifier\s*(?:::\s*external_fn_specification|\(\s*external_fn_specification\s*\))\s*\]"
)
ASSUME_SPEC = re.compile(r"\bassume_specification\b")

LEDGER_MODULES = [
    "net_buf", "pm", "ipc", "mmu", "usage",
    "thread_lifecycle", "sched", "poll", "mpu",
]
INFO_DIRS = ["plain", "tests", "benches", "tools", "ffi", "crates", "fuzz"]


def strip_rust(text):
    """Return text with comments and string/char literals blanked out.

    Newlines are kept so line structure survives. Lifetimes ('a) are left as
    code; a quote is treated as a char literal only when it closes within the
    usual char-literal width.
    """
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            j = text.find("\n", i)
            i = n if j == -1 else j
            continue
        if c == "/" and nxt == "*":
            depth, i = 1, i + 2
            while i < n and depth:
                if text.startswith("/*", i):
                    depth, i = depth + 1, i + 2
                elif text.startswith("*/", i):
                    depth, i = depth - 1, i + 2
                else:
                    if text[i] == "\n":
                        out.append("\n")
                    i += 1
            continue
        m = re.match(r'b?r(#*)"', text[i:i + 300]) if c in "rb" and (i == 0 or not (text[i - 1].isalnum() or text[i - 1] == "_")) else None
        if m:
            close = '"' + m.group(1)
            j = text.find(close, i + m.end())
            j = n if j == -1 else j + len(close)
            out.append("\n" * text.count("\n", i, j))
            i = j
            continue
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            j = min(j + 1, n)
            out.append("\n" * text.count("\n", i, j))
            i = j
            continue
        if c == "'":
            m = re.match(r"'(?:\\(?:x[0-9a-fA-F]{2}|u\{[0-9a-fA-F]{1,6}\}|.)|[^\\'\n])'", text[i:i + 14])
            if m:
                i += m.end()
                continue
        out.append(c)
        i += 1
    return "".join(out)


def count_file(path):
    code = strip_rust(path.read_text(encoding="utf-8", errors="replace"))
    return {
        "external_body": len(EXTERNAL_BODY.findall(code)),
        "external_fn_specification": len(EXTERNAL_FN_SPEC.findall(code)),
        "assume_specification": len(ASSUME_SPEC.findall(code)),
    }


def tally(root, files):
    totals, by_file = Counter(), {}
    for f in files:
        c = count_file(f)
        if any(c.values()):
            by_file[f.relative_to(root).as_posix()] = c
        totals.update(c)
    for k in ("external_body", "external_fn_specification", "assume_specification"):
        totals.setdefault(k, 0)
    return dict(totals), by_file


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        sys.exit(__doc__.strip().splitlines()[3].strip())
    root = Path(args[0]).resolve()
    src = root / "src"
    if not src.is_dir():
        sys.exit(f"{root}: no src/ directory; is this a gale checkout?")
    try:
        sha = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        sha = "unknown"

    totals, by_file = tally(root, sorted(src.rglob("*.rs")))
    info = {}
    for d in INFO_DIRS:
        if (root / d).is_dir():
            t, _ = tally(root, sorted((root / d).rglob("*.rs")))
            info[d] = t

    def lines_with(path, needle):
        text = path.read_text(encoding="utf-8", errors="replace")
        return sum(needle in line for line in text.splitlines())

    fixed = sum(lines_with(f, "#[verifier::external_body]") for f in sorted(src.glob("*.rs")))
    substring = sum(lines_with(src / f"{m}.rs", "external_body")
                    for m in LEDGER_MODULES if (src / f"{m}.rs").is_file())

    result = {
        "schema": 1,
        "commit": sha,
        "counted_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rule": "comment- and string-stripped attribute instances in src/**/*.rs",
        "totals": totals,
        "by_file": by_file,
        "outside_src_for_information": info,
        "comparison_rules": {
            "line-fixed-string": fixed,
            "line-substring-ledger-modules": substring,
        },
    }
    if "--json" in argv:
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    print(f"gale commit: {sha} (short {sha[:7]})")
    print(f"rule: {result['rule']}")
    for k, v in totals.items():
        print(f"  {k:28s} {v}")
    print("by file (src/):")
    for f, c in sorted(by_file.items()):
        print(f"  {f:34s} " + "  ".join(f"{k}={v}" for k, v in c.items() if v))
    print("outside src/ (not in the Verus crate; information only):")
    for d, t in info.items():
        print(f"  {d + '/':10s} " + "  ".join(f"{k}={v}" for k, v in t.items()))
    print("comparison rules (comments included):")
    for k, v in result["comparison_rules"].items():
        print(f"  {k:32s} {v}")


if __name__ == "__main__":
    main(sys.argv[1:])
