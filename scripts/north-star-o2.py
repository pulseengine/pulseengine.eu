#!/usr/bin/env python3
"""Measure North Star objective O2: one-command evidence bundle.

Indicator (data/north-star.toml): consumer repositories whose latest release
carries the full bundle and passes the verify command.
Guard: the verify command must fail when evidence is removed or altered.

The denominator is not hand-picked: it is every product in data/north-star.toml
whose `pulls` includes O2. For each, the script:

  1. reads the latest release over the GitHub REST API;
  2. finds the `*-evidence-bundle.tar.gz` asset (absent = not counted);
  3. unpacks it, refusing absolute paths, `..` and links;
  4. runs the bundle's own `verify.sh` with sigil's latest released `wsc`
     binary, whose sha256 is checked against sigil's SHA256SUMS.txt;
  5. runs two negative controls on copies, each of which must fail:
     a deleted evidence file, and a flipped byte in the signed component with
     the manifest re-hashed, so only the signature check can catch it.

A repo counts only when the real bundle passes AND both controls fail. A bundle
whose verify.sh passes a control is reported as `vacuous`, never as passing.

Blind spot: this checks the bundle's inner consistency. The outer chain
(SHA256SUMS.txt cosign-signed by the release workflow, SLSA provenance) is not
checked here.

Running verify.sh executes code from a PulseEngine release. Only repositories
named in data/north-star.toml are fetched, so this never runs third-party code.

Writes data/north-star/O2.json. Exit: 0 measured (any value) · 2 could not
measure (API, download or wsc failure; a measurement that cannot reach its
evidence has measured nothing).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover - the macOS floor is 3.9
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        print("north-star-o2: needs Python 3.11+ or the tomli package", file=sys.stderr)
        sys.exit(2)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "north-star.toml"
OUT = ROOT / "data" / "north-star" / "O2.json"
API = "https://api.github.com/repos/pulseengine/{repo}/releases/latest"
BUNDLE_SUFFIX = "-evidence-bundle.tar.gz"


class CannotMeasure(Exception):
    pass


def _get(url: str, accept: str = "application/vnd.github+json") -> bytes:
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "north-star-o2"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
    except Exception as e:  # noqa: BLE001 - any fetch failure means no measurement
        raise CannotMeasure("fetch %s: %s" % (url, e))


def latest_release(repo: str) -> dict:
    return json.loads(_get(API.format(repo=repo)))


def asset(rel: dict, name_pred) -> dict | None:
    for a in rel.get("assets", []):
        if name_pred(a["name"]):
            return a
    return None


def wsc_asset_name() -> str:
    sysname = platform.system()
    mach = platform.machine().lower()
    arch = "aarch64" if mach in ("arm64", "aarch64") else "x86_64"
    if sysname == "Darwin":
        return "wsc-macos-" + arch
    if sysname == "Linux":
        return "wsc-linux-" + arch
    raise CannotMeasure("no wsc release binary for %s/%s" % (sysname, mach))


def fetch_wsc(work: pathlib.Path) -> tuple[pathlib.Path, str]:
    rel = latest_release("sigil")
    name = wsc_asset_name()
    bin_a = asset(rel, lambda n: n == name)
    sums_a = asset(rel, lambda n: n == "SHA256SUMS.txt")
    if not bin_a or not sums_a:
        raise CannotMeasure("sigil %s lacks %s or SHA256SUMS.txt" % (rel.get("tag_name"), name))
    data = _get(bin_a["browser_download_url"], "application/octet-stream")
    sums = _get(sums_a["browser_download_url"], "application/octet-stream").decode()
    want = None
    for line in sums.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*").lstrip("./") == name:
            want = parts[0]
    got = hashlib.sha256(data).hexdigest()
    if want != got:
        raise CannotMeasure("wsc %s sha256 %s does not match SHA256SUMS.txt (%s)" % (name, got, want))
    path = work / name
    path.write_bytes(data)
    path.chmod(0o755)
    return path, rel["tag_name"]


def safe_extract(tgz: pathlib.Path, dest: pathlib.Path) -> pathlib.Path:
    with tarfile.open(tgz, "r:gz") as tf:
        for m in tf.getmembers():
            p = pathlib.PurePosixPath(m.name)
            if p.is_absolute() or ".." in p.parts or not (m.isfile() or m.isdir()):
                raise CannotMeasure("unsafe member in bundle: %s" % m.name)
        tf.extractall(dest)  # members checked above
    tops = [d for d in dest.iterdir() if d.is_dir()]
    if len(tops) != 1 or not (tops[0] / "verify.sh").is_file():
        return None  # type: ignore[return-value]
    return tops[0]


def run_verify(bundle: pathlib.Path, wsc: pathlib.Path) -> tuple[int, str]:
    env = dict(os.environ, SIGIL=str(wsc))
    r = subprocess.run(["bash", str(bundle / "verify.sh")], env=env,
                       capture_output=True, text=True, timeout=600)
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()[-1:][0] if (r.stdout + r.stderr).strip() else ""


def control_delete(src: pathlib.Path, dst: pathlib.Path) -> pathlib.Path:
    shutil.copytree(src, dst)
    victims = sorted(p for p in dst.rglob("*") if p.is_file() and p.name not in ("verify.sh", "MANIFEST.sha256"))
    if not victims:
        raise CannotMeasure("bundle has no evidence files to remove")
    victims[0].unlink()
    return dst


def control_flip_signed(src: pathlib.Path, dst: pathlib.Path) -> pathlib.Path | None:
    shutil.copytree(src, dst)
    signed = sorted(dst.rglob("*.signed.wasm"))
    if not signed:
        return None
    p = signed[0]
    b = bytearray(p.read_bytes())
    b[len(b) // 2] ^= 1
    p.write_bytes(bytes(b))
    man = dst / "MANIFEST.sha256"
    if man.is_file():
        rel = p.relative_to(dst).as_posix()
        lines = []
        for line in man.read_text().splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2 and parts[1].lstrip("*").lstrip("./") == rel:
                line = "%s  %s" % (hashlib.sha256(b).hexdigest(), parts[1])
            lines.append(line)
        man.write_text("\n".join(lines) + "\n")
    return dst


def measure_repo(repo: str, wsc: pathlib.Path, work: pathlib.Path) -> dict:
    rel = latest_release(repo)
    row = {"repo": repo, "release": rel.get("tag_name"), "bundle": None,
           "verify": "absent", "controls": None, "counts": False}
    a = asset(rel, lambda n: n.endswith(BUNDLE_SUFFIX))
    if not a:
        return row
    row["bundle"] = a["name"]
    d = work / repo
    d.mkdir()
    tgz = d / a["name"]
    tgz.write_bytes(_get(a["browser_download_url"], "application/octet-stream"))
    bundle = safe_extract(tgz, d / "x")
    if bundle is None:
        row["verify"] = "no verify.sh"
        return row
    code, last = run_verify(bundle, wsc)
    row["verify"] = "pass" if code == 0 else "fail"
    row["verify_last_line"] = last
    if code != 0:
        return row
    controls = {}
    c1 = control_delete(bundle, d / "ctl-delete")
    controls["deleted evidence file"] = "red" if run_verify(c1, wsc)[0] != 0 else "GREEN"
    c2 = control_flip_signed(bundle, d / "ctl-flip")
    if c2 is None:
        controls["altered signed component"] = "no signed component"
    else:
        controls["altered signed component"] = "red" if run_verify(c2, wsc)[0] != 0 else "GREEN"
    row["controls"] = controls
    if all(v == "red" for v in controls.values()):
        row["counts"] = True
    else:
        row["verify"] = "vacuous"
    return row


def main() -> int:
    ns = tomllib.loads(DATA.read_text())
    repos = sorted(p["name"] for p in ns.get("products", []) if "O2" in p.get("pulls", []))
    if not repos:
        print("north-star-o2: no product pulls O2", file=sys.stderr)
        return 2
    try:
        with tempfile.TemporaryDirectory(prefix="ns-o2-") as tmp:
            work = pathlib.Path(tmp)
            wsc, wsc_tag = fetch_wsc(work)
            rows = [measure_repo(r, wsc, work) for r in repos]
    except CannotMeasure as e:
        print("north-star-o2: could not measure: %s" % e, file=sys.stderr)
        return 2
    n = sum(1 for r in rows if r["counts"])
    out = {
        "schema_version": 1,
        "objective": "O2",
        "measured_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "verifier": "sigil wsc " + wsc_tag,
        "value": n,
        "of": len(rows),
        "repos": rows,
        "blind_spot": "inner bundle consistency only; the cosign/SLSA outer chain is not checked",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    for r in rows:
        print("%-8s %-22s verify=%-8s controls=%s" % (r["repo"], r["release"], r["verify"], r["controls"]))
    print("O2: %d of %d" % (n, len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
