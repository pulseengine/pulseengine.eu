#!/usr/bin/env python3
"""Inline SVG figures for "Agents don't tidy up", from the label and SZZ files.

    tidy-charts.py refactor  > refactor.svg   # refactor share per project, Wilson 95%
    tidy-charts.py fixonfix  > fixonfix.svg   # fix-on-fix share against its null

Reads cls/<name>-full-labels.json (commit-classify.py) and szz/<name>.json plus
szz/introducer-labels.json (szz.py, then the same classifier on introducers).
Colours are site tokens with fallbacks, as in the first post's figures."""
import json, math, subprocess, sys

HUMAN = [("hubris", "Hubris"), ("cranelift", "Cranelift"), ("px4", "PX4")]
AGENT = [("ccc", "C compiler"), ("beads", "beads"), ("gastown", "gastown"),
         ("openclaw", "OpenClaw"), ("rivet", "rivet"), ("spar", "spar")]
FONT = "font-family:'Atkinson Hyperlegible Next',system-ui,sans-serif"


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return 100 * max(0, c - h), 100 * min(1, c + h)


def refactor():
    rows = HUMAN + AGENT
    W, top, rh = 760, 56, 30
    H = top + rh * len(rows) + 52
    x0, x1 = 150, 720
    sx = lambda v: x0 + (x1 - x0) * v / 50
    o = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-labelledby="rf-title rf-desc" style="max-width:{W}px;height:auto;{FONT}">',
         '<title id="rf-title">Share of commits that refactor, per project</title>']
    desc, body = [], []
    for k, (name, label) in enumerate(rows):
        lab = json.load(open(f"cls/{name}-full-labels.json")).values()
        n = len(lab)
        r = sum(v["primary"] == "refactor" for v in lab)
        lo, hi = wilson(r, n)
        y = top + rh * k + rh / 2
        col = "var(--green,#4ade80)" if (name, label) in HUMAN else "var(--accent,#6c8cff)"
        body.append(f'<text x="{x0 - 10}" y="{y + 4}" font-size="12" text-anchor="end" fill="var(--text,#e1e4ed)">{label}</text>')
        body.append(f'<line x1="{sx(lo):.1f}" y1="{y}" x2="{sx(hi):.1f}" y2="{y}" stroke="{col}" stroke-width="2" opacity="0.55"/>')
        body.append(f'<circle cx="{sx(100 * r / n):.1f}" cy="{y}" r="5" fill="{col}"/>')
        body.append(f'<text x="{sx(hi) + 8:.1f}" y="{y + 4}" font-size="10.5" fill="var(--text-dim,#8b90a0)">{100 * r / n:.0f}%  (n={n})</text>')
        desc.append(f"{label} {100 * r / n:.0f}% ({lo:.0f} to {hi:.0f}, n={n})")
    o.append('<desc id="rf-desc">Refactor share of classified commits with 95% Wilson intervals. ' + "; ".join(desc) + ".</desc>")
    o.append(f'<text x="12" y="22" font-size="13" font-weight="700" fill="var(--text,#e1e4ed)">Refactor share of commits</text>')
    o.append(f'<text x="12" y="40" font-size="10.5" fill="var(--text-dim,#8b90a0)"><tspan fill="var(--green,#4ade80)">●</tspan> written by people   <tspan fill="var(--accent,#6c8cff)">●</tspan> written mostly by agents</text>')
    for t in range(0, 51, 10):
        o.append(f'<line x1="{sx(t):.1f}" y1="{top - 4}" x2="{sx(t):.1f}" y2="{top + rh * len(rows)}" stroke="var(--border-subtle,#3d4258)" stroke-width="0.6"/>')
        o.append(f'<text x="{sx(t):.1f}" y="{top + rh * len(rows) + 16}" font-size="10" text-anchor="middle" fill="var(--text-faint,#808698)">{t}%</text>')
    sep = top + rh * len(HUMAN)
    o.append(f'<line x1="20" y1="{sep}" x2="{W - 20}" y2="{sep}" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="3 4"/>')
    o += body
    o.append(f'<text x="12" y="{H - 10}" font-size="9.5" fill="var(--text-faint,#808698)">Bars: 95% Wilson interval. Full commit messages, prefixes stripped, labelled by Haiku; 15 commits per 250-commit bucket. Source: commit-classify.py, 22 October 2026.</text>')
    o.append("</svg>")
    return "\n".join(o)


def fixonfix():
    rows = [r for r in HUMAN + AGENT if r[0] not in ("px4", "openclaw")]
    intro = json.load(open("szz/introducer-labels.json"))
    W, top, rh = 760, 56, 30
    H = top + rh * len(rows) + 52
    x0, x1 = 150, 720
    sx = lambda v: x0 + (x1 - x0) * v / 50
    o = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-labelledby="ff-title ff-desc" style="max-width:{W}px;height:auto;{FONT}">',
         '<title id="ff-title">Fixes that repair an earlier fix, against the share of code fixes write</title>']
    desc, body = [], []
    for k, (name, label) in enumerate(rows):
        R = [r for r in json.load(open(f"szz/{name}.json")) if r["introducers"]]
        kinds = [intro[f"{name}:{r['introducers'][0]['sha']}"]["primary"] for r in R]
        n, f = len(kinds), sum(x == "fix" for x in kinds)
        lo, hi = wilson(f, n)
        null = json.load(open(f"szz/{name}-null.json"))["fix_share_of_added_lines"]
        y = top + rh * k + rh / 2
        col = "var(--green,#4ade80)" if (name, label) in HUMAN else "var(--accent,#6c8cff)"
        body.append(f'<text x="{x0 - 10}" y="{y + 4}" font-size="12" text-anchor="end" fill="var(--text,#e1e4ed)">{label}</text>')
        body.append(f'<line x1="{sx(lo):.1f}" y1="{y}" x2="{sx(hi):.1f}" y2="{y}" stroke="{col}" stroke-width="2" opacity="0.55"/>')
        body.append(f'<rect x="{sx(null) - 1.5:.1f}" y="{y - 8}" width="3" height="16" fill="var(--amber,#fbbf24)"/>')
        body.append(f'<circle cx="{sx(100 * f / n):.1f}" cy="{y}" r="5" fill="{col}"/>')
        body.append(f'<text x="{max(sx(hi), sx(null)) + 8:.1f}" y="{y + 4}" font-size="10.5" fill="var(--text-dim,#8b90a0)">{f}/{n}</text>')
        desc.append(f"{label} {f} of {n} ({100 * f / n:.0f}%, interval {lo:.0f} to {hi:.0f}) against {null:.0f}%")
    o.append('<desc id="ff-desc">Share of traced fixes whose main introducing commit was itself a fix, with 95% Wilson intervals, and as a marker the share of added source lines written by fix commits. ' + "; ".join(desc) + ".</desc>")
    o.append(f'<text x="12" y="22" font-size="13" font-weight="700" fill="var(--text,#e1e4ed)">Bugs introduced by an earlier fix</text>')
    o.append(f'<text x="12" y="40" font-size="10.5" fill="var(--text-dim,#8b90a0)"><tspan fill="var(--amber,#fbbf24)">▮</tspan> expected if fixes broke things at the rate they write code</text>')
    for t in range(0, 51, 10):
        o.append(f'<line x1="{sx(t):.1f}" y1="{top - 4}" x2="{sx(t):.1f}" y2="{top + rh * len(rows)}" stroke="var(--border-subtle,#3d4258)" stroke-width="0.6"/>')
        o.append(f'<text x="{sx(t):.1f}" y="{top + rh * len(rows) + 16}" font-size="10" text-anchor="middle" fill="var(--text-faint,#808698)">{t}%</text>')
    sep = top + rh * 2
    o.append(f'<line x1="20" y1="{sep}" x2="{W - 20}" y2="{sep}" stroke="var(--border-subtle,#3d4258)" stroke-dasharray="3 4"/>')
    o += body
    o.append(f'<text x="12" y="{H - 10}" font-size="9.5" fill="var(--text-faint,#808698)">B-SZZ on the sampled fixes; the introducer is the commit owning most blamed lines. Source: szz.py, 22 October 2026.</text>')
    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    print({"refactor": refactor, "fixonfix": fixonfix}[sys.argv[1]]())
