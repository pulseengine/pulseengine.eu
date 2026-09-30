#!/usr/bin/env python3
"""Fetch every published varve layer's signed metadata from ghcr.io into static/layers.json.

This is the answer to pulseengine.eu#205's third question. A varve layer is an OCI
artifact whose signed metadata sits in its own blobs, each tagged by an
`eu.pulseengine.varve.role` annotation (`envelope`, `payload`, `line-status`). GHCR
issues an anonymous pull token for a public package, so none of this needs varve
itself, a varve.toml, or a pinned layer — which is what made a deploy-time fetch
look blocked.

Output shape: {generated_utc, realms:{<realm>:{registry, order:[tag], layers:{tag:{...}}}}}
A composition layer carries no payloads of its own; its `includes` are resolved
against the other realms here, so the page can show an EFFECTIVE support horizon
(the minimum over the closure) rather than repeating the composition's own claim.
See varve#226.

Exit: 0 wrote the file · 1 a realm answered but held no usable layer · 2 cannot reach ghcr.
"""

from __future__ import annotations

import base64
import datetime
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "static" / "layers.json"

REALMS = {
    "pulseengine": "layers",
    "pulseengine-wasm": "wasm-layers",
    "covalent": "covalent-layers",
}
MANIFEST_ACCEPT = "application/vnd.oci.image.manifest.v1+json"
LAYER_TAG = re.compile(r"^\d{4}\.\d{2}\.\d+$")   # YYYY.MM.P — skips realm-bootstrap
TIMEOUT = 20


def _token(repo: str) -> str:
    url = (f"https://ghcr.io/token?scope=repository:pulseengine/{repo}:pull"
           f"&service=ghcr.io")
    with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
        return json.load(r)["token"]


def _get(repo: str, path: str, accept: str | None = None):
    req = urllib.request.Request(
        f"https://ghcr.io/v2/pulseengine/{repo}/{path}",
        headers={"Authorization": f"Bearer {_token(repo)}",
                 **({"Accept": accept} if accept else {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r)


def _dsse(repo: str, digest: str) -> dict:
    """A DSSE envelope's payload is base64 of the JSON it signs."""
    return json.loads(base64.b64decode(_get(repo, f"blobs/{digest}")["payload"]))


def _sort_key(tag: str) -> tuple[int, ...]:
    return tuple(int(p) for p in tag.split("."))


def fetch_realm(realm: str, repo: str) -> dict:
    tags = [t for t in _get(repo, "tags/list")["tags"] if LAYER_TAG.match(t)]
    tags.sort(key=_sort_key)
    layers = {}
    for tag in tags:
        manifest = _get(repo, f"manifests/{tag}", MANIFEST_ACCEPT)
        roles = {l.get("annotations", {}).get("eu.pulseengine.varve.role"): l["digest"]
                 for l in manifest["layers"]}
        env = _dsse(repo, roles["envelope"])
        status = _dsse(repo, roles["line-status"]) if "line-status" in roles else {}
        ann = env["annotations"]

        tools, includes = {}, []
        for entry in env["manifests"]:
            a = entry["annotations"]
            if a.get("eu.pulseengine.varve.kind") == "layer":
                includes.append({"realm": a.get("eu.pulseengine.varve.include.realm"),
                                 "layer": a.get("eu.pulseengine.varve.include.layer"),
                                 "digest": entry["digest"]})
                continue
            name = a.get("eu.pulseengine.tool")
            if not name:
                continue
            t = tools.setdefault(name, {
                "name": name,
                "version": a.get("eu.pulseengine.tool.version"),
                "kind": a.get("eu.pulseengine.varve.kind") or "tool",
                "proof": a.get("eu.pulseengine.source.proof"),
                "asserts": a.get("eu.pulseengine.source.proof-asserts"),
                "repo": a.get("eu.pulseengine.source.repo"),
                "release": a.get("eu.pulseengine.source.release"),
                "platforms": []})
            if a.get("eu.pulseengine.platform"):
                t["platforms"].append(a["eu.pulseengine.platform"])

        layers[tag] = {
            "layer": ann.get("eu.pulseengine.varve.layer", tag),
            "counter": int(ann.get("eu.pulseengine.varve.counter", 0)),
            "channel": ann.get("eu.pulseengine.varve.channel"),
            "line": ann.get("eu.pulseengine.varve.line"),
            "created": ann.get("org.opencontainers.image.created"),
            "issued": status.get("issued-at"),
            "support_until": status.get("support-until"),
            "payloads": len(env["manifests"]),
            "tools": tools,
            "includes": includes,
        }
    return {"registry": f"oci://ghcr.io/pulseengine/{repo}",
            "order": tags[::-1], "layers": layers}


def add_diffs(realm: dict) -> None:
    """Diff each layer against its predecessor at two levels: version and platform.

    The platform level is not redundant. Layer 2026.09.18 shipped ten fewer
    platform payloads than 2026.09.17 while its only version change was a patch
    bump, so a version-only history calls that layer routine.
    """
    tags = sorted(realm["layers"], key=_sort_key)
    for i, tag in enumerate(tags):
        cur = realm["layers"][tag]
        diff = {"versions": [], "added": [], "removed": [], "platforms": []}
        cur["prev"] = tags[i - 1] if i else None
        if i:
            prev = realm["layers"][tags[i - 1]]["tools"]
            now = cur["tools"]
            for name in sorted(now):
                if name in prev:
                    if prev[name]["version"] != now[name]["version"]:
                        diff["versions"].append({"tool": name,
                                                 "from": prev[name]["version"],
                                                 "to": now[name]["version"]})
                    was, is_ = set(prev[name]["platforms"]), set(now[name]["platforms"])
                    if was != is_:
                        diff["platforms"].append({"tool": name,
                                                  "lost": sorted(was - is_),
                                                  "gained": sorted(is_ - was)})
            diff["added"] = [{"tool": n, "version": now[n]["version"]}
                             for n in sorted(now) if n not in prev]
            diff["removed"] = [n for n in sorted(prev) if n not in now]
        cur["diff"] = diff


def resolve_compositions(realms: dict) -> None:
    """Resolve a composition's includes, and derive the horizon it does not state.

    A composition carries no payloads, so `support-horizon` computes its window
    from when the PAIRING was asserted. Because a composition is cut after the
    layers it composes, its own window routinely closes last — covalent states
    2026-10-30 while both its includes end 2026-10-24. varve#226.
    """
    for realm in realms.values():
        for layer in realm["layers"].values():
            if not layer["includes"]:
                continue
            windows = [layer["support_until"]] if layer["support_until"] else []
            tools = unverified = 0
            for inc in layer["includes"]:
                src = realms.get(inc["realm"], {}).get("layers", {}).get(inc["layer"])
                if not src:
                    inc["resolved"] = False
                    continue
                inc["resolved"] = True
                inc["support_until"] = src["support_until"]
                inc["tools"] = len(src["tools"])
                inc["unverified"] = sum(1 for t in src["tools"].values()
                                        if t["proof"] == "unverified")
                inc["issued"] = src["issued"]
                # Is the pinned layer still the newest in its realm?
                newest = realms[inc["realm"]]["order"][0]
                inc["newest_in_realm"] = newest
                inc["behind"] = (sorted(realms[inc["realm"]]["layers"],
                                        key=_sort_key).index(newest)
                                 - sorted(realms[inc["realm"]]["layers"],
                                          key=_sort_key).index(inc["layer"]))
                tools += inc["tools"]
                unverified += inc["unverified"]
                if src["support_until"]:
                    windows.append(src["support_until"])
            layer["effective"] = {
                "support_until": min(windows) if windows else None,
                "constrained_by": [i["realm"] + " " + i["layer"] for i in layer["includes"]
                                   if i.get("support_until") == min(windows)] if windows else [],
                "overstated_days": ((datetime.date.fromisoformat(layer["support_until"])
                                     - datetime.date.fromisoformat(min(windows))).days
                                    if windows and layer["support_until"] else 0),
                "tools": tools, "unverified": unverified,
            }


def main() -> int:
    realms = {}
    try:
        for realm, repo in REALMS.items():
            realms[realm] = fetch_realm(realm, repo)
            add_diffs(realms[realm])
            print(f"  {realm:18} {len(realms[realm]['order']):>3} layers  "
                  f"newest {realms[realm]['order'][0] if realms[realm]['order'] else '-'}")
    except (urllib.error.URLError, TimeoutError, KeyError) as e:
        # A registry hiccup must not fail the deploy. The committed snapshot
        # stays in place and the page reports how old it is, which is the
        # behaviour pulseengine.eu#201 asked for: a stale panel that says so.
        print(f"warning: cannot read ghcr.io ({e}); keeping {OUT.name} as committed",
              file=sys.stderr)
        return 0 if OUT.is_file() else 2

    empty = [r for r, v in realms.items() if not v["order"]]
    if empty:
        print(f"error: realms answered but hold no layer: {empty}", file=sys.stderr)
        return 1

    resolve_compositions(realms)
    out = {"generated_utc": datetime.datetime.now(datetime.timezone.utc)
           .strftime("%Y-%m-%dT%H:%M:%SZ"), "realms": realms}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    total = sum(len(v["order"]) for v in realms.values())
    print(f"{total} layers across {len(realms)} realms -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
