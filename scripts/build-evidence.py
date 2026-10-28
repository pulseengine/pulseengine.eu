#!/usr/bin/env python3
# rivet: verifies REQ-HERO-EVIDENCE
"""Measure the three figures in the landing-page evidence panel into data/evidence.json.

pulseengine.eu#201, option C. The panel is a claim that decays in public, so
every figure is re-measured here, at deploy time, from the instrument that owns
it. Nothing is typed into the template: templates/partials/evidence-panel.html
only renders what this file writes, and a claim in claims.yaml fails the build
if a digit appears in that partial.

  tile      instrument                                   source date
  claims    claim-check.py claims.yaml, run now          this run
  layer     static/layers.json (fetch-layers.py)         its generated_utc
  rivet     rivet coverage --format json, run now        this run

A fourth tile, gale's trusted-base size, waits on a machine-readable source:
the external_body count exists only as prose in gale's honesty ledger.

Rules, because they are the point of the issue:

* A source that is missing or unreadable yields `status: unavailable` and NO
  value. This script never reads its own previous output, so it cannot carry an
  old number forward.
* Each tile records `source_epoch` and `stale_after` (source + 7 days). The
  template compares `stale_after` with `now()` at `zola build` time, so an old
  evidence.json is still judged against the build clock, not its own.
* A sparkline is emitted only from a real series with at least two points:
  claims.yaml's git history (needs a full clone — the deploy checks out with
  fetch-depth 0; CI's shallow clone gets none) and the layer index. rivet has
  no recorded history, so it gets none. Nothing is interpolated: x is the real
  time of each point, and the line is drawn as steps, because each value holds
  until the next one replaces it.

Usage:  build-evidence.py [--require claims,rivet,...]   write data/evidence.json
        build-evidence.py --self-test                    decision table, offline
Exit:   0 written · 1 a --require'd tile came out unavailable · 2 self-test failed
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "evidence.json"
CLAIM_CHECK = ROOT / "claude-tooling/plugins/pulseengine-claude/skills/claim-verification/claim-check.py"
REPO_URL = "https://github.com/pulseengine/pulseengine.eu"
STALE_AFTER = dt.timedelta(days=7)
REALM = "pulseengine"


def _epoch(ts: str) -> int:
    return int(dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())


def _iso(epoch: int) -> str:
    return dt.datetime.fromtimestamp(epoch, dt.timezone.utc).strftime("%Y-%m-%d")


def _run(cmd: list[str], cwd: pathlib.Path) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return None


def sparkline(series: list[tuple[int, float]], label: str) -> dict | None:
    """Step polyline in a 100x24 box. x is proportional to real time, never index.

    Drawn step-after: a layer's payload count, or the claim ledger's size, holds
    from the moment it is issued until the next one replaces it, so the honest
    shape is a staircase, not a line sloping between two releases. Two points at
    the same timestamp would draw a vertical stroke that means nothing, so the
    later entry for a timestamp wins.

    A short-lived value is NOT smoothed away: layer 2026.09.18 shipped 44
    payloads where its neighbours shipped 54, and 2026.09.19 restored them two
    hours later. On a seven-week axis that is a narrow notch, and it stays one.
    """
    dedup: dict[int, float] = {}
    for t, v in sorted(series, key=lambda tv: tv[0]):
        dedup[t] = v
    series = sorted(dedup.items())
    if len(series) < 2:
        return None
    t0, t1 = series[0][0], series[-1][0]
    lo, hi = min(v for _, v in series), max(v for _, v in series)
    span_t, span_v = (t1 - t0) or 1, (hi - lo)

    def pt(t, v):
        x = (t - t0) / span_t * 100
        y = 12 if span_v == 0 else 22 - (v - lo) / span_v * 20
        return round(x, 2), round(y, 2)

    pts = []
    for i, (t, v) in enumerate(series):
        x, y = pt(t, v)
        if i:
            pts.append((x, pts[-1][1]))      # hold the previous value until now
        pts.append((x, y))
    fmt = lambda v: f"{v:g}" if isinstance(v, float) else str(v)
    low_t, low_v = min(series, key=lambda tv: (tv[1], -tv[0]))   # most recent low
    return {
        "viewbox": "0 0 100 24",
        "points": " ".join(f"{x},{y}" for x, y in pts),
        "label": (f"{label}: {len(series)} points, {fmt(series[0][1])} on {_iso(t0)} "
                  f"to {fmt(series[-1][1])} on {_iso(t1)}; lowest {fmt(low_v)} on "
                  f"{_iso(low_t)}"),
    }


def tile(key: str, label: str, href: str, source: str, **kw) -> dict:
    t = {"key": key, "label": label, "href": href, "source": source,
         "status": "unavailable", "value": None, "unit": None, "detail": None,
         "tone": "neutral", "source_epoch": None, "source_date": None,
         "stale_after": None, "spark": None}
    t.update(kw)
    t["external"] = t["href"].startswith("http")
    if t["source_epoch"] is not None:
        t["source_date"] = _iso(t["source_epoch"])
        t["stale_after"] = t["source_epoch"] + int(STALE_AFTER.total_seconds())
    return t


# ── tile 1: claims ────────────────────────────────────────────────────────────

HOLD = re.compile(r"^(\d+)/(\d+) claims hold\.$", re.M)


def claims_history(root: pathlib.Path) -> list[tuple[int, float]]:
    """Ledger size at each commit that touched claims.yaml. Empty on a shallow clone."""
    shallow = _run(["git", "rev-parse", "--is-shallow-repository"], root)
    if not shallow or shallow.returncode or shallow.stdout.strip() != "false":
        return []
    log = _run(["git", "log", "--format=%H %ct", "--", "claims.yaml"], root)
    if not log or log.returncode:
        return []
    out = []
    for line in log.stdout.split("\n"):
        if not line.strip():
            continue
        sha, ct = line.split()
        show = _run(["git", "show", f"{sha}:claims.yaml"], root)
        if show and not show.returncode:
            n = len(re.findall(r"^  - id: ", show.stdout, re.M))
            if n:
                out.append((int(ct), n))
    return out


def tile_claims(root: pathlib.Path, now: int, sha: str, run=None) -> dict:
    base = dict(key="claims", label="site claims holding",
                href=f"{REPO_URL}/blob/{sha}/claims.yaml",
                source="claim-check.py claims.yaml, run at this build")
    res = (run or _run)([sys.executable, str(CLAIM_CHECK), "claims.yaml"], root)
    m = HOLD.search(res.stdout) if res else None
    if not m:
        return tile(**base)
    held, total = int(m[1]), int(m[2])
    return tile(**base, status="ok", value=f"{held}/{total}", unit="claims hold",
                detail="each bound to evidence re-derived from the tree",
                tone="good" if held == total else "bad", source_epoch=now,
                spark=sparkline(claims_history(root), "claims declared in claims.yaml"))


# ── tile 2: current varve layer ───────────────────────────────────────────────

def tile_layer(root: pathlib.Path) -> dict:
    base = dict(key="layer", label="current varve layer", href="/layers/",
                source="static/layers.json, fetched from ghcr.io by fetch-layers.py")
    try:
        data = json.loads((root / "static" / "layers.json").read_text())
        realm = data["realms"][REALM]
        cur = realm["layers"][realm["order"][0]]
        gen = _epoch(data["generated_utc"])
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return tile(**base)
    digest = cur.get("digest")
    detail = (f"{digest[:19]}…" if digest else "digest not recorded in this snapshot")
    issued = cur.get("issued")
    series = [(_epoch(L["issued"]), L["payloads"]) for L in realm["layers"].values()
              if L.get("issued") and isinstance(L.get("payloads"), int)]
    return tile(**base, status="ok", value=cur["layer"],
                unit=f"issued {issued[:10]}" if issued else "issue date not recorded",
                detail=detail, digest=digest, source_epoch=gen,
                spark=sparkline(series, f"signed payloads per {REALM} layer, by issue date"))


# ── tile 3: rivet traceability of this repo ───────────────────────────────────

def tile_rivet(root: pathlib.Path, now: int, sha: str, run=None, which=shutil.which) -> dict:
    base = dict(key="rivet", label="requirements with a verifying test",
                href=f"{REPO_URL}/tree/{sha}/artifacts",
                source="rivet coverage over artifacts/, run at this build")
    if not which("rivet"):
        return tile(**base)
    res = (run or _run)(["rivet", "coverage", "--format", "json"], root)
    try:
        rules = {r["name"]: r for r in json.loads(res.stdout)["rules"]}
        ver, cov = rules["requirement-verification"], rules["requirement-coverage"]
        v, n, traced = int(ver["covered"]), int(ver["total"]), int(cov["covered"])
    except (AttributeError, ValueError, KeyError, TypeError):
        return tile(**base)
    if not n:            # an empty load is not "all verified"
        return tile(**base)
    version = (run or _run)(["rivet", "--version"], root)
    vtxt = version.stdout.split()[1] if version and version.stdout.split()[1:] else "?"
    return tile(**base, status="ok", value=f"{v}/{n}", unit="a verifies link in rivet",
                detail=f"{traced}/{n} traced to a feature · rivet {vtxt}",
                tone="good" if v == n else "neutral", source_epoch=now)


# ── assemble ──────────────────────────────────────────────────────────────────

def build(root: pathlib.Path, now: int | None = None) -> dict:
    now = now if now is not None else int(dt.datetime.now(dt.timezone.utc).timestamp())
    head = _run(["git", "rev-parse", "HEAD"], root)
    sha = head.stdout.strip() if head and not head.returncode else "main"
    return {"generated_epoch": now, "commit": sha[:7] if sha != "main" else None,
            "commit_url": f"{REPO_URL}/commit/{sha}" if sha != "main" else None,
            "stale_after_days": STALE_AFTER.days,
            "tiles": [_guarded("claims", lambda: tile_claims(root, now, sha)),
                      _guarded("layer", lambda: tile_layer(root)),
                      _guarded("rivet", lambda: tile_rivet(root, now, sha))]}


LABELS = {"claims": ("site claims holding", "claim-check.py claims.yaml"),
          "layer": ("current varve layer", "static/layers.json"),
          "rivet": ("requirements with a verifying test", "rivet coverage")}


def _guarded(key: str, fn) -> dict:
    """A source shaped in a way nobody anticipated must cost one tile, not the deploy."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 — deliberately total
        print(f"warning: {key} tile unavailable: {type(e).__name__}: {e}", file=sys.stderr)
        label, source = LABELS[key]
        return tile(key=key, label=label, href="/", source=source)


def self_test() -> int:
    fails = []

    def check(name, cond):
        print(("  ok   " if cond else "  FAIL ") + name)
        if not cond:
            fails.append(name)

    class R:  # stand-in CompletedProcess
        def __init__(self, out, rc=0):
            self.stdout, self.returncode = out, rc

    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        now = 1_800_000_000

        # missing sources -> unavailable, no value, no date
        t = tile_layer(root)
        check("layer: no layers.json -> unavailable", t["status"] == "unavailable" and t["value"] is None)
        t = tile_rivet(root, now, "x", which=lambda _: None)
        check("rivet: no binary -> unavailable", t["status"] == "unavailable" and t["source_epoch"] is None)
        t = tile_rivet(root, now, "x", run=lambda *a: R('{"rules": []}'), which=lambda _: "rivet")
        check("rivet: unexpected JSON shape -> unavailable", t["status"] == "unavailable")
        empty = json.dumps({"rules": [
            {"name": "requirement-verification", "covered": 0, "total": 0},
            {"name": "requirement-coverage", "covered": 0, "total": 0}]})
        t = tile_rivet(root, now, "x", run=lambda *a: R(empty), which=lambda _: "rivet")
        check("rivet: zero requirements loaded -> unavailable, not 0/0", t["status"] == "unavailable")
        t = tile_claims(root, now, "x", run=lambda *a: R("Traceback ...", 1))
        check("claims: unparsable checker output -> unavailable", t["status"] == "unavailable")
        t = tile_claims(root, now, "x", run=lambda *a: R("✗ A\n\n17/18 claims hold.\n", 1))
        check("claims: a failing claim is shown as failing", t["value"] == "17/18" and t["tone"] == "bad")

        # staleness boundary: source + 7 days, judged by the template against now()
        (root / "static").mkdir()
        old = now - 8 * 86400
        stamp = dt.datetime.fromtimestamp(old, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        (root / "static" / "layers.json").write_text(json.dumps({
            "generated_utc": stamp, "realms": {REALM: {"order": ["2026.01.1"], "layers": {
                "2026.01.1": {"layer": "2026.01.1", "issued": stamp, "payloads": 3}}}}}))
        t = tile_layer(root)
        check("layer: 8-day-old snapshot is dated by its fetch, stale_after < now",
              t["source_epoch"] == old and t["stale_after"] < now)
        check("layer: no digest in snapshot -> says so", "not recorded" in t["detail"])
        check("layer: one layer is not a series -> no sparkline", t["spark"] is None)
        t = tile_claims(root, now, "x", run=lambda *a: R("19/19 claims hold.\n"))
        check("claims: measured now is not stale", t["stale_after"] > now)
        check("claims: not a git checkout -> no history, no sparkline", t["spark"] is None)

        # a malformed source costs its tile, never the run
        (root / "static" / "layers.json").write_text(json.dumps({
            "generated_utc": stamp, "realms": {REALM: {"order": ["x"], "layers": {
                "x": {"issued": "not a date", "payloads": 1}}}}}))
        t = _guarded("layer", lambda: tile_layer(root))
        check("guard: malformed layer entry -> unavailable, no exception",
              t["status"] == "unavailable")

    s = sparkline([(0, 5), (10, 5)], "x")
    check("sparkline: flat series stays inside the box",
          s and s["points"] == "0.0,12 100.0,12 100.0,12")
    s = sparkline([(0, 1), (90, 2), (100, 3)], "x")
    check("sparkline: x follows real time, not index",
          s and s["points"].split()[1].startswith("90.0,"))
    s = sparkline([(0, 1), (50, 3)], "x")
    check("sparkline: steps — the old value holds until the new one",
          s and s["points"] == "0.0,22.0 100.0,22.0 100.0,2.0")
    s = sparkline([(0, 1), (50, 3), (50, 2), (100, 2)], "x")
    xs = [p.split(",")[0] for p in s["points"].split()] if s else []
    check("sparkline: a duplicate timestamp is one point, the later value wins",
          s and "4 points" not in s["label"] and "3 points" in s["label"]
          and s["points"].split()[2] == "50.0,2.0")
    check("sparkline: x never decreases", xs == sorted(xs, key=float))
    check("sparkline: duplicates collapsing to one point -> no sparkline",
          sparkline([(5, 1), (5, 2)], "x") is None)
    print(f"\n{'FAILED' if fails else 'passed'}: {len(fails)} failing case(s)")
    return 2 if fails else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    required = set()
    if "--require" in argv:
        required = set(argv[argv.index("--require") + 1].split(","))
    data = build(ROOT)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    bad = 0
    for t in data["tiles"]:
        mark = "ok  " if t["status"] == "ok" else "n/a "
        spark = "spark" if t["spark"] else "-"
        print(f"  {mark} {t['key']:7} {t['value'] or 'unavailable':12} "
              f"source {t['source_date'] or '-':10} {spark}")
        if t["key"] in required and t["status"] != "ok":
            print(f"error: {t['key']} is required and came out unavailable", file=sys.stderr)
            bad = 1
    print(f"-> {OUT.relative_to(ROOT)}")
    return bad


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
