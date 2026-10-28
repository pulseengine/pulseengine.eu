#!/usr/bin/env bash
# Render static/og-image-generator.html to static/og-image.png (1200x630 social card).
#
# Usage: scripts/render-og-image.sh
#   CHROME=/path/to/chrome  override the browser binary
#
# Needs network access: the generator loads Atkinson Hyperlegible Next from
# Google Fonts. --virtual-time-budget keeps the page alive until the font
# request settles, so the capture is not taken with the fallback font.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$root/static/og-image-generator.html"
out="$root/static/og-image.png"

chrome="${CHROME:-}"
if [[ -z "$chrome" ]]; then
  for c in "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
           google-chrome google-chrome-stable chromium chromium-browser; do
    if [[ -x "$c" ]] || command -v "$c" >/dev/null 2>&1; then chrome="$c"; break; fi
  done
fi
[[ -n "$chrome" ]] || { echo "error: no Chrome/Chromium found; set CHROME=" >&2; exit 1; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

"$chrome" --headless=new --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=1 --window-size=1200,630 \
  --virtual-time-budget=10000 --user-data-dir="$tmp/profile" \
  --screenshot="$tmp/og.png" "file://$src" >"$tmp/chrome.log" 2>&1 || true

if [[ ! -s "$tmp/og.png" ]]; then
  echo "error: Chrome produced no screenshot; its log:" >&2
  cat "$tmp/chrome.log" >&2
  exit 1
fi

# Shrink if an optimizer is available; the card is flat colour, so this is cheap.
if command -v pngquant >/dev/null 2>&1; then
  pngquant --force --skip-if-larger --quality=80-95 --output "$tmp/og.png" -- "$tmp/og.png" || true
elif command -v oxipng >/dev/null 2>&1; then
  oxipng -q -o 4 --strip safe "$tmp/og.png"
fi

mv "$tmp/og.png" "$out"

if command -v sips >/dev/null 2>&1; then
  w="$(sips -g pixelWidth "$out" | awk '/pixelWidth/{print $2}')"
  h="$(sips -g pixelHeight "$out" | awk '/pixelHeight/{print $2}')"
  dims="${w}x${h}"
elif command -v magick >/dev/null 2>&1; then
  dims="$(magick identify -format '%wx%h' "$out")"
else
  dims="unknown"
fi
if [[ "$dims" != "1200x630" && "$dims" != "unknown" ]]; then
  echo "error: got ${dims}, want 1200x630" >&2
  exit 1
fi
echo "wrote $out ($dims, $(wc -c <"$out" | tr -d ' ') bytes)"
