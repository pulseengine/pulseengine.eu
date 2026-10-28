#!/usr/bin/env python3
# rivet: verifies REQ-HERO-EVIDENCE
"""Measure the four figures in the landing-page evidence panel into data/evidence.json.

pulseengine.eu#201, option C. The panel is a claim that decays in public, so
every figure is re-measured here, at deploy time, from the instrument that owns
it. Nothing is typed into the template: templates/partials/evidence-panel.html
only renders what this file writes, and a claim in claims.yaml fails the build
if a digit appears in that partial.

  tile      instrument                                   source date
  claims    claim-check.py claims.yaml, run now          this run
  layer     static/layers.json (fetch-layers.py)         its generated_utc
  rivet     rivet coverage --format json, run now        this run
  mcdc      witness verdict-suite report.json files      the suite's own timestamp
            under static/reports/witness/ (fetch-reports)

Rules, because they are the point of the issue:

* A source that is missing or unreadable yields `status: unavailable` and NO
  value. This script never reads its own previous output, so it cannot carry an
  old number forward.
* Each tile records `source_epoch` and `stale_after` (source + 7 days). The
  template compares `stale_after` with `now()` at `zola build` time, so an old
  evidence.json is still judged against the build clock, not its own.
* A sparkline is emitted only from a real series with at least two points:
  claims.yaml's git history (needs a full clone — the deploy checks out with
  fetch-depth 0; CI's shallow clone gets none), the layer index, and witness
  versions on disk. rivet has no recorded history, so it gets none. Nothing is
  interpolated: x is the real time of each point.

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
    """Polyline in a 100x24 box. x is proportional to real time, never index."""
    if len(series) < 2:
        return None
    series = sorted(series)
    t0, t1 = series[0][0], series[-1][0]
    lo, hi = min(v for _, v in series), max(v for _, v in series)
    span_t, span_v = (t1 - t0) or 1, (hi - lo)

    def pt(t, v):
        x = (t - t0) / span_t * 100
        y = 12 if span_v == 0 else 22 - (v - lo) / span_v * 20
        return round(x, 2), round(y, 2)

    pts = [pt(t, v) for t, v in series]
    fmt = lambda v: f"{v:g}" if isinstance(v, float) else str(v)
    return {
        "viewbox": "0 0 100 24",
        "points": " ".join(f"{x},{y}" for x, y in pts),
        "label": (f"{label}: {len(series)} points, {fmt(series[0][1])} on {_iso(t0)} "
                  f"to {fmt(series[-1][1])} on {_iso(t1)}"),
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


# ── tile 4: MC/DC (substitute for the gale trusted-base count) ────────────────

SUITE_TS = re.compile(r"^witness verdict suite — (\S+)", re.M)


def _semver(s: str) -> tuple[int, ...]:
    return tuple(int(p) for p in re.findall(r"\d+", s)[:3])


def _suite(vdir: pathlib.Path) -> tuple[int, int, int, str] | None:
    """(timestamp, conditions proved, conditions total, schema) for one witness version.

    Conditions, not decisions: in witness 0.45.0 the per-report decision totals
    sum to 128 while SUMMARY.txt's TOTAL row says 151, so the decision figure
    depends on which of witness's own outputs is read. The condition sums agree
    with SUMMARY.txt (146 proved of 839) and are the self-consistent metric.
    """
    ev = vdir / "mcdc" / "verdict-evidence"
    try:
        ts = _epoch(SUITE_TS.search((ev / "SUMMARY.txt").read_text())[1])
        proved = total = 0
        schemas = set()
        reports = sorted(ev.glob("*/report.json"))
        for p in reports:
            r = json.loads(p.read_text())
            o = r["overall"]
            proved += int(o["conditions_proved"])
            total += int(o["conditions_total"])
            schemas.add(r.get("schema"))
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if not reports or not total or len(schemas) != 1:
        return None
    return ts, proved, total, schemas.pop()


def tile_mcdc(root: pathlib.Path) -> dict:
    base = dict(key="mcdc", label="MC/DC conditions proved", href="/reports/",
                source="witness verdict-suite report.json, fetched by fetch-reports")
    wdir = root / "static" / "reports" / "witness"
    versions = sorted((d for d in wdir.glob("*") if d.is_dir() and d.name != "latest"
                       and re.fullmatch(r"\d+\.\d+\.\d+", d.name)),
                      key=lambda d: _semver(d.name)) if wdir.is_dir() else []
    # The value comes from the NEWEST version only. If that one does not parse,
    # the tile is unavailable — falling back to an older release would be the
    # remembered number this panel exists to refuse.
    latest = _suite(versions[-1]) if versions else None
    if not latest:
        return tile(**base)
    ts, proved, total, schema = latest
    # History: only versions on the same report schema, so the series measures
    # coverage rather than a change of envelope.
    series = [(s[0], round(s[1] / s[2] * 100, 1)) for d in versions
              if (s := _suite(d)) and s[3] == schema]
    return tile(**base, status="ok", value=f"{proved}/{total}", unit="conditions",
                detail=(f"witness {versions[-1].name} on its own verdict suite of sample "
                        "programs — not a measurement of PulseEngine code"),
                source_epoch=ts,
                spark=sparkline(series, "percent of conditions proved, per witness release"))


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
                      _guarded("rivet", lambda: tile_rivet(root, now, sha)),
                      _guarded("mcdc", lambda: tile_mcdc(root))]}


LABELS = {"claims": ("site claims holding", "claim-check.py claims.yaml"),
          "layer": ("current varve layer", "static/layers.json"),
          "rivet": ("requirements with a verifying test", "rivet coverage"),
          "mcdc": ("MC/DC conditions proved", "witness verdict-suite report.json")}


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
        t = tile_mcdc(root)
        check("mcdc: no witness reports -> unavailable", t["status"] == "unavailable" and t["value"] is None)
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

        # witness: one version -> value, no sparkline; two -> sparkline
        def suite(ver, ts, proved, total):
            ev = root / "static/reports/witness" / ver / "mcdc/verdict-evidence"
            (ev / "a").mkdir(parents=True)
            (ev / "SUMMARY.txt").write_text(f"witness verdict suite — {ts}\n")
            (ev / "a/report.json").write_text(json.dumps({"overall": {
                "conditions_proved": proved, "conditions_total": total}}))
        suite("0.9.0", "2026-01-01T00:00:00Z", 1, 10)
        t = tile_mcdc(root)
        check("mcdc: single version -> value, no sparkline", t["value"] == "1/10" and t["spark"] is None)
        suite("0.10.0", "2026-02-01T00:00:00Z", 3, 10)
        t = tile_mcdc(root)
        check("mcdc: latest by semver, not by string", t["value"] == "3/10")
        check("mcdc: two versions -> sparkline", t["spark"] is not None)
        bad = root / "static/reports/witness/0.11.0/mcdc/verdict-evidence"
        bad.mkdir(parents=True)
        (bad / "SUMMARY.txt").write_text("a header witness changed\n")
        t = tile_mcdc(root)
        check("mcdc: newest unparseable -> unavailable, not an older release's figure",
              t["status"] == "unavailable" and t["value"] is None)

        # a malformed source costs its tile, never the run
        (root / "static" / "layers.json").write_text(json.dumps({
            "generated_utc": stamp, "realms": {REALM: {"order": ["x"], "layers": {
                "x": {"issued": "not a date", "payloads": 1}}}}}))
        t = _guarded("layer", lambda: tile_layer(root))
        check("guard: malformed layer entry -> unavailable, no exception",
              t["status"] == "unavailable")

    s = sparkline([(0, 5), (10, 5)], "x")
    check("sparkline: flat series stays inside the box", s and s["points"] == "0.0,12 100.0,12")
    s = sparkline([(0, 1), (90, 2), (100, 3)], "x")
    check("sparkline: x follows real time, not index", s and s["points"].split()[1].startswith("90.0,"))
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
