#!/bin/bash
# check-no-third-party.sh <dir>: fail if the built site in <dir> loads anything
# from a host other than pulseengine.eu. Covers <script src>, <link> with a
# loading rel (stylesheet, preconnect, preload, modulepreload, dns-prefetch,
# icon), ES module `import ... from '<url>'` and CSS `url(...)`/`@import`.
# Plain <a href> links are navigation, not loads, and are not checked.
#
# This is the static half of tests/playwright/no-third-party-loads.spec.js,
# which no CI job runs. The browser test sees runtime loads too, but needs
# a browser download; this one runs in the build job in a second.
set -u
dir="${1:-public}"
[ -d "$dir" ] || { echo "no such directory: $dir"; exit 2; }

ext='https?://(www\.)?[a-z0-9.-]+'
first_party='https?://(www\.)?pulseengine\.eu([/:"'"'"')]|$)'

hits=$(
  {
    grep -rEoh --include='*.html' "<script[^>]*src=[\"']${ext}[^\"']*" "$dir"
    grep -rEoh --include='*.html' "<link[^>]*rel=[\"']?(stylesheet|preconnect|preload|modulepreload|dns-prefetch|icon)[^>]*" "$dir" \
      | grep -Eo "href=[\"']${ext}[^\"']*"
    grep -rEoh --include='*.html' --include='*.js' --include='*.mjs' "(import|from)[[:space:]]*\(?[\"']${ext}[^\"']*" "$dir"
    grep -rEoh --include='*.html' --include='*.css' "(url\(|@import[[:space:]]+)[\"']?${ext}[^\"')]*" "$dir"
  } 2>/dev/null | grep -Ev "$first_party" | sort -u
)

if [ -n "$hits" ]; then
  echo "third-party loads found in $dir (self-host them under static/, pinned):"
  printf '%s\n' "$hits"
  exit 1
fi
echo "no third-party loads in $dir"
