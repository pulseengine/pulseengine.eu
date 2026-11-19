#!/bin/sh
# A stand-in for `cosign verify-blob` in the offline tests: no network, no
# Fulcio. A fixture "signature" (bundle, or .sig) is two lines: the signer's
# certificate identity and the sha256 of the signed blob. It verifies only when
# the issuer is GitHub's OIDC issuer, the identity matches the regexp the tool
# passed (grep -E, the same ERE the real cosign gets as RE2), and the blob's
# sha256 is the one recorded, so a planted wrong signer, wrong tag, branch run
# or edited SHA256SUMS fails here as it would under cosign.
set -eu
[ "${1:-}" = "verify-blob" ] || { echo "stub: expected verify-blob" >&2; exit 9; }
shift
sig="" re="" iss=""
while [ $# -gt 1 ]; do
  case "$1" in
    --bundle|--signature) sig=$2; shift 2 ;;
    --certificate) shift 2 ;;
    --certificate-identity-regexp) re=$2; shift 2 ;;
    --certificate-oidc-issuer) iss=$2; shift 2 ;;
    *) echo "stub: unexpected argument $1" >&2; exit 9 ;;
  esac
done
blob=$1
[ -n "$sig" ] && [ -n "$re" ] || { echo "stub: missing --bundle/--signature or identity regexp" >&2; exit 9; }
[ "$iss" = "https://token.actions.githubusercontent.com" ] || { echo "Error: wrong issuer $iss" >&2; exit 1; }
id=$(sed -n 1p "$sig")
want=$(sed -n 2p "$sig")
printf '%s\n' "$id" | grep -Eq -- "$re" || { echo "Error: none of the expected identities matched: $id" >&2; exit 1; }
if command -v sha256sum >/dev/null 2>&1; then
  got=$(sha256sum "$blob" | cut -d' ' -f1)
else
  got=$(shasum -a 256 "$blob" | cut -d' ' -f1)
fi
[ "$got" = "$want" ] || { echo "Error: invalid signature when validating ASN.1 encoded signature" >&2; exit 1; }
echo "Verified OK" >&2
