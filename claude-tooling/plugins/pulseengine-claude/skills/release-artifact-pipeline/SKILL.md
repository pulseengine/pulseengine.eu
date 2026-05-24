---
name: release-artifact-pipeline
description: This skill should be used when setting up, standardizing, auditing, or modifying a release artifact pipeline on a PulseEngine project — including "standardize release artifacts", "set up release workflow", "fix the release pipeline", "add cosign signing", "add SLSA attestation", "add SBOM", "switch to signed SHA256SUMS", "audit release artifacts", "migrate off per-file .sha256 sidecars", or any GitHub Actions release.yml setup/refactor. ALWAYS use this skill when proposing or reviewing changes to a release.yml workflow, when adopting the PulseEngine release-artifact standard for a new repo, or before claiming a release pipeline is "compliant" or "signed".
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# Release artifact pipeline

## When this fires

Anytime you touch the *release workflow itself* on a PulseEngine project — setting it up for the first time, standardizing assets, adding cosign signing, adding SLSA attestation, adding SBOMs, migrating off per-file `.sha256` sidecars, or auditing whether the pipeline meets the project's verifiability bar.

This is distinct from `release-execution`, which fires when you're *cutting* a release on top of an already-working pipeline. Pipeline setup is the rarer, deeper task.

## The standard

Every PulseEngine repo that ships binaries shares one release-artifact convention. The canonical implementation lives at **`pulseengine/synth/.github/workflows/release.yml`** — Phase 6 onward. **Copy that block verbatim** into the target repo's release workflow, then adapt the SBOM step's manifest path to point at the target repo's main crate.

### Required release assets (and no others for checksums/attestation)

```
<tool>-vX.Y.Z-<triple>.{tar.gz|zip}    # binary archives
<tool>-X.Y.Z.cdx.json                  # CycloneDX SBOM
SHA256SUMS.txt                         # checksums over the archives + SBOM
SHA256SUMS.txt.sig                     # cosign signature (keyless OIDC)
SHA256SUMS.txt.pem                     # cosign certificate
SHA256SUMS.txt.cosign.bundle           # cosign bundle for verify-blob
build-env.txt                          # rustc / cargo / cosign / runner versions
```

### Required workflow steps, in this order

1. **Build binary archives** → `release-assets/`.
2. **Generate SBOM** — `cargo cyclonedx --manifest-path <main-crate>/Cargo.toml --format json --spec-version 1.5`, then copy result to `release-assets/<tool>-${BARE}.cdx.json`. **Must run before step 3** so its digest enters the sums.
3. **Generate checksums** — `cd release-assets && sha256sum ./* > SHA256SUMS.txt`.
4. **SLSA provenance** — `actions/attest-build-provenance@v2` with `subject-path: "release-assets/*.tar.gz"` (SLSA v1 provenance, GitHub-native).
5. **Install cosign** — `sigstore/cosign-installer@v3`.
6. **Sign the sums file** — `cosign sign-blob --yes --bundle SHA256SUMS.txt.cosign.bundle --output-signature SHA256SUMS.txt.sig --output-certificate SHA256SUMS.txt.pem SHA256SUMS.txt` (keyless OIDC).
7. **Record build environment** — write `build-env.txt` (rustc/cargo/cosign/runner versions).
8. **Upload everything** — `gh release upload` over everything in `release-assets/`.

### Required workflow permissions

```yaml
permissions:
  contents: write
  id-token: write
  attestations: write
```

### What to delete from any existing release flow

- **All per-file `<asset>.sha256` sidecars.** The single signed `SHA256SUMS.txt` replaces them.
- **Exception**: witness keeps its per-asset `.cert` / `.sig` files because they're consumed as certification evidence. For witness, the signed sums file is *added*, not replacing.

## Verification — the oracle for this skill

Per [`oracle-gate-a-change`], the release pipeline is itself a mechanical oracle. The diff that flips it red→green is one where the verification one-liner below runs cleanly against the published release. **Paste this verification block into the release notes of every release that uses this pipeline**, so consumers can re-run the check:

```sh
cosign verify-blob \
  --certificate-identity-regexp 'https://github.com/pulseengine/<tool>/.github/workflows/release.yml@.*' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  --bundle SHA256SUMS.txt.cosign.bundle SHA256SUMS.txt

gh attestation verify <tool>-vX.Y.Z-<triple>.tar.gz --repo pulseengine/<tool>
```

If either of these fails on the published release, the pipeline did not actually do what was claimed. That's a refute under [`clean-room-verification`].

## How to apply to a target repo

1. **Read the canonical**: open `pulseengine/synth/.github/workflows/release.yml`. Find Phase 6 onward (the artifact-generation block).
2. **Identify the target repo's deltas**:
   - Does it already have binary archives? (loom: no — missing upload step entirely. Fix that first; the sums/signing flow is moot until artifacts exist.)
   - Does it have per-file `.sha256` sidecars? (sigil/wsc: yes — must be replaced.)
   - Does it have a SBOM? (most repos: no — add it.)
   - Does it have cosign signing? (spar: no — add it.)
   - Does it have SLSA attestation? (most repos: no — add it.)
3. **Copy the Phase 6+ block from synth verbatim**, adapt only:
   - The main crate manifest path for the SBOM step.
   - The `<tool>` name in the verification one-liner.
   - The asset name pattern.
4. **Run [`oracle-gate-a-change`]** to verify the new workflow flips a check that didn't previously exist. The check is "the verification one-liner runs green against a test release."
5. **Run [`clean-room-verification`]** on the claim "the pipeline produces signed, attestable, SBOM-bearing artifacts." Have the verifier actually re-run `cosign verify-blob` and `gh attestation verify` against a real published release, not infer from the workflow YAML.

## Anti-patterns

- **Trusting the workflow YAML as proof.** A green Actions run doesn't prove the artifacts are signed correctly — the verification one-liner against the *published* release does. The YAML is intent; the verifier is evidence.
- **Pinning specific tool versions in this skill body.** `actions/attest-build-provenance@v2`, `sigstore/cosign-installer@v3`, `cosign v2.4.1`, `--spec-version 1.5` — these all decay. The canonical version is whatever synth's `release.yml` currently ships. If versions drift, sync to synth, don't update this skill.
- **Keeping per-file `.sha256` sidecars "for backwards compat".** They're not in the standard. Drop them. (Witness's `.cert`/`.sig` are a different artifact serving certification evidence, not checksums — keep those.)
- **Adding the cosign step without `id-token: write` permission.** Cosign keyless OIDC requires it. Missing this is the most common pipeline-broken-silently failure mode.
- **Generating the SBOM after the sums file.** Order matters: SBOM must enter the sums.

## Cross-links

- [`oracle-gate-a-change`] — pipeline setup is itself an oracle-flip; this skill names the oracle.
- [`release-execution`] — what cuts a release atop a green pipeline.
- [`clean-room-verification`] — verifies the pipeline actually does what it claims (re-run the verification one-liner against the published release).
- [`pulseengine-feature-loop`] — sigil is the attestation step of the feature loop; the pipeline standard makes that step actually verifiable downstream.

## Notes on the canonical (synth)

synth's `release.yml` is the reference. If patterns there look synth-specific (e.g. transcoder-output naming, Rocq-proof handling), generalize them when adapting. Generalization is fine — divergence from the 8-step skeleton is not. If you find yourself wanting to skip a step, that's a [`oracle-gate-a-change`] decision, not a casual one.
