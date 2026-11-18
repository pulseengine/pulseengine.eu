#!/usr/bin/env python3
"""Measure North Star objective O4: not only one person.

Indicator (data/north-star.toml): merged pull requests per month by people other
than the maintainer. This script measures the last full calendar month across
the pulseengine organisation:

  value = merged PRs whose author is a human account other than the maintainers
  of    = all merged PRs in the month that were not opened by a bot

Agent-written PRs are opened under the maintainer's account, so they count in
`of` but never in `value`: the number says how much work arrives from other
people, not how much work is done.

Blind spots, written into the output: "time from ready to first pick-up" (the
second half of the indicator) is not measured yet, and neither is the guard
(reverted or reopened work from those PRs). GitHub's search API caps a query at
1,000 results; if the month's non-maintainer PRs exceed that, the script refuses
to measure rather than undercount.

Writes data/north-star/O4.json. Exit: 0 measured · 2 could not measure.
`--self-test` checks the classification and the month window.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "north-star" / "O4.json"
ORG = "pulseengine"
MAINTAINERS = ("avrabe",)
API = "https://api.github.com/search/issues"


class CannotMeasure(Exception):
    pass


def last_full_month(today: dt.date) -> tuple[str, str]:
    first_this = today.replace(day=1)
    last_prev = first_this - dt.timedelta(days=1)
    return last_prev.replace(day=1).isoformat(), last_prev.isoformat()


def search(query: str, page: int = 1) -> dict:
    url = API + "?" + urllib.parse.urlencode({"q": query, "per_page": 100, "page": page})
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "north-star-o4"})
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except Exception as e:  # noqa: BLE001 - any failure means no measurement
        raise CannotMeasure("search failed: %s" % e)


def classify(items: list) -> tuple[list, int]:
    """Split non-maintainer items into human PRs and a bot count."""
    humans, bots = [], 0
    for it in items:
        user = it.get("user") or {}
        login = user.get("login", "")
        if user.get("type") == "Bot" or login.endswith("[bot]"):
            bots += 1
        elif login not in MAINTAINERS:
            humans.append(it)
    return humans, bots


def measure(today: dt.date) -> dict:
    start, end = last_full_month(today)
    base = "org:%s is:pr is:merged merged:%s..%s" % (ORG, start, end)
    total = search(base).get("total_count", 0)
    q = base + "".join(" -author:%s" % m for m in MAINTAINERS)
    first = search(q)
    count = first.get("total_count", 0)
    if count > 1000:
        raise CannotMeasure("%d non-maintainer PRs exceed the search cap of 1,000" % count)
    items = list(first.get("items", []))
    page = 2
    while len(items) < count:
        more = search(q, page).get("items", [])
        if not more:
            break
        items += more
        page += 1
    if len(items) != count:
        raise CannotMeasure("search returned %d of %d items" % (len(items), count))
    humans, bots = classify(items)
    of = total - bots
    if of <= 0:
        raise CannotMeasure("no human-opened PRs merged in %s..%s" % (start, end))
    return {
        "objective": "O4",
        "measured_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "verifier": "GitHub search, merged PRs %s to %s" % (start, end),
        "period": "%s..%s" % (start, end),
        "value": len(humans),
        "of": of,
        "items": [{"pr": "%s#%d" % (h["repository_url"].rsplit("/", 1)[-1], h["number"]),
                   "url": h["html_url"]} for h in humans],
        "blind_spot": "time from ready to first pick-up and the guard (reverted or reopened work) "
                      "are not measured yet; agent PRs run under the maintainer's account",
    }


def self_test() -> int:
    ok = True
    if last_full_month(dt.date(2026, 11, 18)) != ("2026-10-01", "2026-10-31"):
        print("self-test: month window wrong"); ok = False
    if last_full_month(dt.date(2027, 1, 1)) != ("2026-12-01", "2026-12-31"):
        print("self-test: year boundary wrong"); ok = False
    items = [
        {"user": {"login": "dependabot[bot]", "type": "Bot"}},
        {"user": {"login": "pulseengine-actions-helper[bot]", "type": "Bot"}},
        {"user": {"login": "someone", "type": "User"}},
        {"user": {"login": MAINTAINERS[0], "type": "User"}},
    ]
    humans, bots = classify(items)
    if bots != 2 or [h["user"]["login"] for h in humans] != ["someone"]:
        print("self-test: classification wrong: %d bots, %r" % (bots, humans)); ok = False
    print("self-test: %s" % ("all cases hold" if ok else "FAILED"))
    return 0 if ok else 1


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return self_test()
    try:
        out = measure(dt.datetime.now(dt.timezone.utc).date())
    except CannotMeasure as e:
        print("north-star-o4: could not measure: %s" % e, file=sys.stderr)
        return 2
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("O4 (%s): %d of %d merged PRs came from people other than the maintainer"
          % (out["period"], out["value"], out["of"]))
    for i in out["items"]:
        print("  " + i["pr"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
