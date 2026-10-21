#!/usr/bin/env python3
"""Render the small-multiples figure for "The machine arrived before the factory".

    factory-charts.py rivet=rivet.json spar=spar.json > figure.svg

Input is the --json output of factory-metrics.py. Each argument is `label=path`.
The label is what the row is called in the figure. A bare path still works and
falls back to the filename stem, but then the rendered figure depends on what
the file happened to be called: an independent re-run that wrote `v-rivet.json`
labelled its row "v-rivet" and stopped matching the published figure. Output is an inline SVG that
reads the site's theme tokens (var(--text) etc.), so it follows light and dark
mode like the other inline figures. No numbers are typed by hand here.
"""
import json
import sys

W, H = 760, 420
COLS = [
    ("Files per change, 90th percentile", "p90"),
    ("Share of changes: feat vs fix", "mix"),
    ("Open issues (bots excluded)", "open"),
]
PANEL_W, PANEL_H = 210, 120
LEFT, TOP, GAP_X, GAP_Y = 52, 64, 30, 70
MON = dict(zip(["01","02","03","04","05","06","07","08","09","10","11","12"],
           "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()))


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")


def polyline(points, colour, dash=None, thin=()):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
    d = f' stroke-dasharray="{dash}"' if dash else ""
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.8" fill="var(--surface,#1a1d27)" '
        f'stroke="{colour}" stroke-width="1.4"/>' if i in thin else
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.4" fill="{colour}"/>'
        for x, y, i in points)
    return (f'<polyline points="{pts}" fill="none" stroke="{colour}" '
            f'stroke-width="1.8"{d}/>{dots}')


def panel(x0, y0, months, series, ymax, unit, labels, thin=()):
    out = [f'<rect x="{x0}" y="{y0}" width="{PANEL_W}" height="{PANEL_H}" rx="6" '
           'fill="var(--surface,#1a1d27)" stroke="var(--border-subtle,#3d4258)"/>']
    for frac in (0.5, 1.0):
        y = y0 + PANEL_H - frac * PANEL_H * 0.82 - 8
        out.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0 + PANEL_W}" y2="{y:.1f}" '
                   'stroke="var(--border-subtle,#3d4258)" stroke-dasharray="2 3"/>')
        out.append(f'<text x="{x0 - 6}" y="{y + 3:.1f}" font-size="9" text-anchor="end" '
                   f'fill="var(--text-faint,#808698)">{ymax * frac:g}{unit}</text>')
    n = len(months)
    xs = [x0 + 14 + i * (PANEL_W - 28) / max(1, n - 1) for i in range(n)]
    for i, m in enumerate(months):
        if i in (0, n - 1) or m.endswith("-06"):
            out.append(f'<text x="{xs[i]:.1f}" y="{y0 + PANEL_H + 13}" font-size="9" '
                       f'text-anchor="middle" fill="var(--text-faint,#808698)">'
                       f'{MON[m[5:7]]}</text>')
    for (values, colour, dash), _ in zip(series, labels):
        pts = [(xs[i], y0 + PANEL_H - 8 - (v / ymax) * PANEL_H * 0.82, i)
               for i, v in enumerate(values) if v is not None]
        out.append(polyline(pts, colour, dash, thin))
    return "".join(out)


def main():
    repos = []
    for arg in sys.argv[1:3]:
        label, sep, path = arg.partition("=")
        if not sep:
            label, path = arg.rsplit("/", 1)[-1].removesuffix(".json"), arg
        with open(path) as fh:
            repos.append((label, json.load(fh)))

    parts = [
        f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-labelledby="fm-title fm-desc" '
        "style=\"max-width:760px;height:auto;font-family:'Atkinson Hyperlegible Next',system-ui,sans-serif\">",
        '<title id="fm-title">Seven months of rivet and spar, by month</title>',
        '<desc id="fm-desc">Small multiples for two repositories, March to October 2026: '
        "the 90th percentile of source files per change falls in both; the feature share "
        "falls and the fix share rises in both; the number of open issues rises in both "
        "from single digits to 33 and 37. Generated from factory-metrics.py output.</desc>",
    ]
    for c, (title, _) in enumerate(COLS):
        x = LEFT + c * (PANEL_W + GAP_X)
        parts.append(f'<text x="{x}" y="26" font-size="12" font-weight="700" '
                     f'fill="var(--text,#e1e4ed)">{esc(title)}</text>')
    parts.append(f'<text x="{LEFT + PANEL_W + GAP_X}" y="42" font-size="10" '
                 'fill="var(--accent,#6c8cff)">feat</text>')
    parts.append(f'<text x="{LEFT + PANEL_W + GAP_X + 30}" y="42" font-size="10" '
                 'fill="var(--amber,#fbbf24)">fix</text>')

    for r, (name, data) in enumerate(repos):
        y = TOP + r * (PANEL_H + GAP_Y)
        parts.append(f'<text x="8" y="{y - 8}" font-size="12" font-weight="700" '
                     f'fill="var(--text,#e1e4ed)">{name}</text>')
        months = [m["month"] for m in data["months"]]
        p90 = [m["p90_files"] for m in data["months"]]
        parts.append(panel(LEFT, y, months, [(p90, "var(--accent,#6c8cff)", None)],
                           max(30, max(p90)), "", [0]))
        feat = [m["feat_pct"] for m in data["months"]]
        fix = [m["fix_pct"] for m in data["months"]]
        parts.append(panel(LEFT + PANEL_W + GAP_X, y, months,
                           [(feat, "var(--accent,#6c8cff)", None),
                            (fix, "var(--amber,#fbbf24)", None)], 60, "%", [0, 1],
                           thin={i for i, m in enumerate(data["months"])
                                 if m["changes"] < 10}))
        imonths = [m["month"] for m in data["issues"]]
        opn = [m["open"] for m in data["issues"]]
        parts.append(panel(LEFT + 2 * (PANEL_W + GAP_X), y, imonths,
                           [(opn, "var(--red,#f87171)", None)], 40, "", [0]))
    parts.append(f'<text x="{LEFT}" y="{H - 8}" font-size="9.5" '
                 'fill="var(--text-faint,#808698)">Hollow points: fewer than 10 changes '
                 'that month. Source: factory-metrics.py over first-parent history and '
                 'the GitHub issue API, read 21 October 2026.</text>')
    parts.append("</svg>")
    print("\n".join(parts))


if __name__ == "__main__":
    main()
