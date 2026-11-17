#!/usr/bin/env python3
"""Monthly news radar over warte's news feed (contract news v1).

warte collects the release notes of the outside tools we use. This script is
the mechanical half of turning them into factory work; the judgement half
(what an item means for which repo) is the outside-in-recheck skill's.

  pull    items still `found` since a date, minus obvious noise, as a table
          or JSON, for triage
  mark    set one item's state (decided / dismissed / landed) with a note;
          a decided item's note carries the issue or notice it became
  landed  promote decided items whose linked GitHub issue or PR is closed as
          completed / merged to `landed`
  stats   found / decided / landed / dismissed per radar run, and the
          switch-off rule: after 3 runs, if fewer than 1 in 3 decided items
          landed, the radar is not paying for itself (exit 3)

Configuration comes from the environment only, so no host reaches the repo:
PULSEENGINE_WARTE_URL, PULSEENGINE_WARTE_CACERT (optional), and the news:write
token from the file named by PULSEENGINE_WARTE_NEWS_TOKEN_FILE (default
~/.config/pulseengine/private/warte-news-token). The token is never printed.

Feed text is data: titles and excerpts are printed for reading, never run.

Exit: 0 ok · 1 usage · 2 warte unreachable or refused · 3 switch-off rule fired.
`--self-test` checks the noise filter, the note-link parser and the off rule.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.request

TOKEN_DEFAULT = "~/.config/pulseengine/private/warte-news-token"
# A run is the set of items marked in one calendar month (by state_at).
OFF_RUNS = 3
OFF_RATIO = 1.0 / 3.0

NOISE = re.compile(
    r"(?i)((\b|\d)(pre|rc|alpha|beta|nightly|canary|snapshot)[\.\-]?\d|\bdev:\s|"
    r"\brolling\b|\bbump\b|\bchore\b|dependabot|\btypo\b)"
)
LINK = re.compile(r"https://github\.com/([\w.-]+/[\w.-]+)/(issues|pull)/(\d+)")


class Refused(Exception):
    pass


def _ctx():
    ca = os.environ.get("PULSEENGINE_WARTE_CACERT")
    return ssl.create_default_context(cafile=ca) if ca else ssl.create_default_context()


def _token():
    path = os.path.expanduser(os.environ.get("PULSEENGINE_WARTE_NEWS_TOKEN_FILE", TOKEN_DEFAULT))
    try:
        with open(path, encoding="ascii") as f:
            tok = f.readline().strip()
    except OSError as e:
        raise Refused("news token file unreadable (%s)" % type(e).__name__)
    if not tok or any(c.isspace() for c in tok):
        raise Refused("news token file is empty or malformed")
    return tok


def _call(method, path, body=None):
    base = os.environ.get("PULSEENGINE_WARTE_URL", "").rstrip("/")
    if not base.startswith("https://"):
        raise Refused("PULSEENGINE_WARTE_URL is not set to an https:// URL")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + _token())
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, context=_ctx(), timeout=30) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        raise Refused("warte answered HTTP %d on %s %s" % (e.code, method, path.split("?")[0]))
    except (urllib.error.URLError, OSError) as e:
        raise Refused("warte unreachable (%s)" % type(e).__name__)
    return json.loads(raw) if raw else {}


def items(since, state=None):
    q = "since=" + since + ("&state=" + state if state else "")
    return _call("GET", "/api/news?" + q).get("items", [])


def is_noise(item):
    return bool(NOISE.search(item.get("title", "")))


def links(note):
    return [(m.group(1), m.group(2), int(m.group(3))) for m in LINK.finditer(note or "")]


def closed_done(repo, kind, num):
    """True when the linked issue was closed as completed or the PR merged."""
    field = "stateReason,state" if kind == "issues" else "state"
    cmd = ["gh", "issue" if kind == "issues" else "pr", "view", str(num), "--repo", repo,
           "--json", field]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    d = json.loads(out)
    if kind == "issues":
        return d.get("state") == "CLOSED" and d.get("stateReason") == "COMPLETED"
    return d.get("state") == "MERGED"


def runs(all_items):
    """Group marked items by the month their state last changed."""
    out = {}
    for i in all_items:
        if i.get("state") == "found" or not i.get("state_at"):
            continue
        out.setdefault(i["state_at"][:7], []).append(i)
    return dict(sorted(out.items()))


def off_rule(run_map):
    """(fires, decided_total, landed_total) over the last OFF_RUNS runs."""
    last = list(run_map.values())[-OFF_RUNS:]
    if len(last) < OFF_RUNS:
        return False, None, None
    decided = sum(1 for r in last for i in r if i["state"] in ("decided", "landed"))
    landed = sum(1 for r in last for i in r if i["state"] == "landed")
    return (decided > 0 and landed / decided < OFF_RATIO) or decided == 0, decided, landed


def cmd_pull(a):
    rows = [i for i in items(a.since, "found") if a.all or not is_noise(i)]
    if a.json:
        print(json.dumps([{k: i[k] for k in ("id", "source", "published", "title", "link", "excerpt")}
                          for i in rows], indent=1))
    else:
        for i in rows:
            print("%5d  %-14s %s  %s" % (i["id"], i["source"], i["published"][:10], i["title"][:100]))
        print("%d item(s) to triage" % len(rows))
    return 0


def cmd_mark(a):
    if a.state == "decided" and not links(a.note):
        print("news-radar: a decided item's note must link the issue, PR or notice it became",
              file=sys.stderr)
        return 1
    _call("POST", "/api/news/state", {"id": a.id, "state": a.state, "note": a.note})
    print("item %d -> %s" % (a.id, a.state))
    return 0


def cmd_landed(a):
    n = 0
    for i in items(a.since, "decided"):
        ls = links(i.get("note"))
        if ls and all(closed_done(*l) for l in ls):
            _call("POST", "/api/news/state", {"id": i["id"], "state": "landed", "note": i["note"]})
            print("item %d landed" % i["id"])
            n += 1
    print("%d item(s) landed" % n)
    return 0


def cmd_stats(a):
    rm = runs(items(a.since))
    for month, r in rm.items():
        c = {s: sum(1 for i in r if i["state"] == s) for s in ("decided", "landed", "dismissed")}
        print("%s  decided %d  landed %d  dismissed %d" % (month, c["decided"], c["landed"], c["dismissed"]))
    fires, d, l = off_rule(rm)
    if d is None:
        print("switch-off rule: fewer than %d runs, not evaluated" % OFF_RUNS)
        return 0
    print("switch-off rule over the last %d runs: %d of %d decided items landed" % (OFF_RUNS, l, d))
    if fires:
        print("news-radar: fewer than 1 in 3 decided items landed; propose switching the radar off")
        return 3
    return 0


def self_test():
    ok = True
    noisy = ["Release 11.0.0-pre.20261103.3", "v2.0.0-rc1", "8.9.0rc2", "dev: Test out lock files",
             "chore: bump x", "release/rolling/0.2026.11.05.387adf6"]
    clean = ["Rust 1.95.0 is out", "macOS 14 runner image is retired", "Kani 0.70 adds loop contracts"]
    for t in noisy:
        if not is_noise({"title": t}):
            print("self-test: noise not filtered: %r" % t); ok = False
    for t in clean:
        if is_noise({"title": t}):
            print("self-test: real item filtered: %r" % t); ok = False
    if links("see https://github.com/pulseengine/relay/issues/12 and https://github.com/a/b/pull/3") != \
            [("pulseengine/relay", "issues", 12), ("a/b", "pull", 3)]:
        print("self-test: link parser"); ok = False
    if links("no link here"):
        print("self-test: link parser invents links"); ok = False

    def run(dec, land):
        return [{"state": "landed", "state_at": "x"}] * land + [{"state": "decided", "state_at": "x"}] * (dec - land)
    cases = [
        ({"a": run(3, 0), "b": run(3, 0), "c": run(3, 0)}, True),     # nothing lands
        ({"a": run(3, 1), "b": run(3, 1), "c": run(3, 1)}, False),    # exactly 1 in 3
        ({"a": run(3, 0), "b": run(3, 0)}, False),                    # too early to judge
        ({"a": [], "b": [], "c": []}, True),                          # decides nothing
    ]
    for rm, want in cases:
        if off_rule(rm)[0] != want:
            print("self-test: off rule wrong for %r" % {k: len(v) for k, v in rm.items()}); ok = False
    print("self-test: %s" % ("all cases hold" if ok else "FAILED"))
    return 0 if ok else 1


def main(argv=None):
    p = argparse.ArgumentParser(description="Monthly news radar over warte news v1.")
    p.add_argument("--self-test", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    default_since = (dt.date.today() - dt.timedelta(days=31)).isoformat()
    s = sub.add_parser("pull"); s.add_argument("--since", default=default_since)
    s.add_argument("--all", action="store_true", help="keep items the noise filter drops")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("mark"); s.add_argument("id", type=int)
    s.add_argument("state", choices=["decided", "dismissed", "landed"]); s.add_argument("--note", default="")
    s = sub.add_parser("landed"); s.add_argument("--since", default="2026-11-01")
    s = sub.add_parser("stats"); s.add_argument("--since", default="2026-11-01")
    a = p.parse_args(argv)
    if a.self_test:
        return self_test()
    if not a.cmd:
        p.print_help()
        return 1
    try:
        return {"pull": cmd_pull, "mark": cmd_mark, "landed": cmd_landed, "stats": cmd_stats}[a.cmd](a)
    except Refused as e:
        print("news-radar: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
