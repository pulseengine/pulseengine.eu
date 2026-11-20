#!/usr/bin/env bash
# The North Star schema fragment must allow exactly the objective ids.
#
# schemas/north-star.yaml gives rivet the allowed values of a feature's
# `serves:` field; data/north-star.toml is where the objectives are defined.
# If the two drift, a repository either rejects a feature serving a real
# objective or accepts one serving an objective that no longer exists. This
# fails unless the allowed-values list equals the `id`s of [[objectives]], in
# the same order.
#
# Usage: scripts/check-north-star-serves.sh [NORTH_STAR_TOML [SCHEMA_YAML]]
# Exit: 0 equal, 1 drift, 2 a file could not be read or parsed (no ids, or not
# exactly one allowed-values line), so an empty or malformed input never
# passes as "equal".
#
# bash 3.2 and BSD/GNU tools only: it runs on the macOS floor and in CI.
# rivet: verifies REQ-NORTH-STAR-SERVES
set -euo pipefail

TOML=${1:-data/north-star.toml}
SCHEMA=${2:-schemas/north-star.yaml}

for f in "$TOML" "$SCHEMA"; do
  if [ ! -r "$f" ]; then
    echo "check-north-star-serves: cannot read $f" >&2
    exit 2
  fi
done

# ids of [[objectives]] tables, in file order. Any other table header ends the
# objective, so a period's or product's `id` is never taken.
objectives=$(awk '
  /^[[:space:]]*\[/ {
    h = $0
    gsub(/[[:space:]]/, "", h)
    inobj = (h == "[[objectives]]")
    next
  }
  inobj && /^[[:space:]]*id[[:space:]]*=/ {
    v = $0
    sub(/^[^=]*=[[:space:]]*"/, "", v)
    sub(/".*$/, "", v)
    print v
  }
' "$TOML")

# The one allowed-values line, as one value per line.
n=$(grep -c '^[[:space:]]*allowed-values:' "$SCHEMA" || true)
if [ "$n" != "1" ]; then
  echo "check-north-star-serves: $SCHEMA has $n allowed-values lines, expected exactly 1 (keep the list on one line)" >&2
  exit 2
fi
allowed=$(grep '^[[:space:]]*allowed-values:' "$SCHEMA" \
  | sed -e 's/^[^[]*\[//' -e 's/\].*$//' \
  | tr ',' '\n' \
  | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/" \
  | grep -v '^$' || true)

if [ -z "$objectives" ]; then
  echo "check-north-star-serves: no [[objectives]] ids found in $TOML" >&2
  exit 2
fi
if [ -z "$allowed" ]; then
  echo "check-north-star-serves: empty allowed-values in $SCHEMA" >&2
  exit 2
fi

if [ "$objectives" != "$allowed" ]; then
  echo "check-north-star-serves: DRIFT between $TOML and $SCHEMA" >&2
  echo "  objective ids:  $(echo "$objectives" | tr '\n' ' ')" >&2
  echo "  allowed-values: $(echo "$allowed" | tr '\n' ' ')" >&2
  exit 1
fi

echo "check-north-star-serves: OK, allowed-values = objective ids ($(echo "$objectives" | tr '\n' ' ' | sed 's/ $//'))"
