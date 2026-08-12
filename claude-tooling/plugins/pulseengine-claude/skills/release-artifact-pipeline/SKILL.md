---
name: release-artifact-pipeline
description: This skill should be used when setting up, standardizing, auditing, or modifying a release artifact pipeline on a PulseEngine project — including "standardize release artifacts", "set up release workflow", "fix the release pipeline", "add cosign signing", "add SLSA attestation", "add SBOM", "switch to signed SHA256SUMS", "sign the wasm with sigil", "add a witness/scry gate to the release", "publish to crates.io / npm", "add a Pages verification dashboard", "audit release artifacts", "migrate off per-file .sha256 sidecars", or any GitHub Actions release.yml setup/refactor. ALWAYS use this skill when proposing or reviewing changes to a release.yml workflow, when adopting the PulseEngine release-artifact standard for a new repo, or before claiming a release pipeline is "compliant" or "signed". Covers all five tracks — native binaries, distribution channels (crates.io + npm), wasm signing (sigil + cosign) and wasm verification gates (witness MC/DC + scry), the Pages verification dashboard, and rivet verification extraction.
metadata:
  author: pulseengine.eu
  version: "0.3.0"
---

# Release artifact pipeline

## When this fires

Anytime you touch the *release workflow itself* on a PulseEngine project — setting it up for the first time, standardizing assets, adding cosign signing, adding SLSA attestation, adding SBOMs, migrating off per-file `.sha256` sidecars, or auditing whether the pipeline meets the project's verifiability bar.

This is distinct from `release-execution`, which fires when you're *cutting* a release on top of an already-working pipeline. Pipeline setup is the rarer, deeper task.

## The standard — match it for *every artifact type the repo ships*

A repo's release is compliant only when **each kind of artifact it produces** meets
its track below. The recurring org-wide defect (2026-06 sweep): the *native binary*
gets the full supply chain everywhere, while the *wasm* it ships gets weaker signing
and no verification gate. Hold wasm to the **same bar** as the binary.

- **Track A — native binaries** → the cosign+SBOM+SLSA bundle (canonical: synth).
- **Track B — distribution channels** → crates.io for everything Rust; npm for CLIs/tools;
  **varve layers** for the toolchain as a pinned, signed set.
- **Track C — wasm artifacts** → sigil + cosign signature, **and** a witness MC/DC
  gate **and** a scry abstract-interpretation gate. No wasm ships unverified.
- **Track D — Pages verification dashboard** → witness-viz / scry-viz (canonical:
  witness, scry).

A repo skips a track only if it produces none of that artifact type — and "we emit
wasm but only Track A is wired" is the exact drift this skill exists to close.

## Track A — native binaries

The canonical implementation lives at **`pulseengine/synth/.github/workflows/release.yml`** — Phase 6 onward. **Copy that block verbatim** into the target repo's release workflow, then adapt the SBOM step's manifest path to point at the target repo's main crate.

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

## Track B — distribution channels

Distribution is currently incoherent (rivet npm-only, sigil/synth/scry crates.io-only,
mcp a stale unsigned manual script). The rule:

- **crates.io for everything written in Rust** — canonical, published from CI via
  OIDC trusted publishing, never a hand-run `cargo publish` from a laptop. Keep it
  in a dedicated `publish-to-crates-io.yml` on the `v*` tag (canonical: sigil,
  synth, scry) so the artifact-release and the registry-publish don't race.
  **mcp's manual `scripts/publish.sh` is the anti-pattern — it ships unsigned, out
  of CI, with stale pinned versions; move it into CI.**
- **npm for CLIs and tools** — the platform-package wrapper pattern (canonical:
  rivet's `release-npm.yml`: per-target `@pulseengine/<tool>-<platform>` packages
  wired to a root launcher via `optionalDependencies`), triggered `workflow_run`
  after the GitHub Release so the binaries exist. This is **not** rivet-only —
  every user-facing CLI (rivet, spar, …) should ship it.
- **varve layers — the canonical org-internal channel, and now shipping.** A tool's
  signed release becomes an entry in a dated OCI layer via `varve deposit`
  (`ghcr.io/pulseengine/varve/layers`); consumers pin *one layer* rather than N
  independently-drifting tool versions. crates.io and npm remain the public channels —
  the layer is how the toolchain is consumed as a set. `varve export-bazel` compiles a
  Bazel checksum registry from the verified layer, so every hash Bazel enforces is a
  transcription from the signed manifest **instead of TOFU**.
- **Editor marketplaces are in scope later** — rivet/spar's VS Code Marketplace is the
  precedent; not required now.

A Rust tool is compliant on Track B only when it is on crates.io **and** (if it's a
CLI) on npm. crates.io-but-no-npm and npm-but-no-crates.io are both drift.

### The deposit workflow is an org release-standard enforcer

This is the part worth internalising: `deposit-layer.yml` verifies each tool's release
against **that tool's own repo cosign identity**, and a tool whose release lacks
cosign-signed `SHA256SUMS.txt` is **excluded from the layer** with a notice rather than
deposited unverified. Exclusion is visible and dated — the workflow's own comments record
`ordeal is EXCLUDED until its releases carry cosign-signed sums`, then
`ordeal rejoined at v0.18.0 — its first cosign-signed release`.

So Track A compliance stopped being advisory the day layers shipped: an unsigned release
no longer merely *fails an audit*, it **drops the tool out of the toolchain everyone
installs**. Treat a tool's absence from the current layer as a release-pipeline defect in
that tool's repo, and file it there per [`report-tool-friction`].

## Track C — wasm artifacts (same bar as the binary)

Any repo that **ships or emits wasm** (component or module) must sign and verify it
to the binary's standard. The sweep found this is where every repo cuts corners.

### Signing — sigil + cosign
- **sigil signature** (dogfood the attestation tool) **and** cosign over the sums.
  Canonical signer: sigil's own `wsc sign --keyless` (see sigil `release.yml` /
  `wasm-signing.yml`).
- **Prerequisite — fix sigil first.** sigil cannot yet parse its own `wasm32-wasip2`
  output, so it ships unsigned-on-failure. **Do not mandate the sigil step on a repo
  until that parser blocker is fixed** (tracked upstream in `pulseengine/sigil`); add
  cosign now, add the sigil signature as the blocker clears. Mandating a broken step
  just reintroduces `continue-on-error` theatre.
- SLSA `subject-path` must cover the **`.wasm`**, not only the `.o`/`.tar.gz`
  (gale's provenance currently covers the `.o` objects but not the wasm — fix).

### Verification gates — witness AND scry (both required)
Every wasm-emitting repo runs, as a **CI/release gate** (not a manual side-script):
- **witness** — MC/DC truth-table on the wasm; the gate asserts zero unresolved gap
  rows for new decisions (canonical: witness `ci.yml` dogfood + `verdict-suite`;
  scry's `mcdc-gate.sh` is the consume-as-library exemplar). Where the bundled
  witness can't parse component-format exports (relay #145), that's a witness bug to
  file via [`report-tool-friction`] — not a reason to leave the gate manual.
- **scry** — sound abstract interpretation over the fused Wasm core (consume scry as
  a crates.io library, v1.15+; canonical: scry's self-analysis dogfood).

"We emit wasm and run neither" is the headline gap (loom — a wasm *optimizer* — runs
no wasm verification; meld, gale, spar likewise). Manual witness runs (relay, wohl)
count as **not a gate** until they're in CI.

## Track D — Pages verification dashboard

Publish the verification evidence as a browsable dashboard on every repo that runs
witness/scry. Canonical: witness's and scry's `publish-pages` job (witness-viz /
scry-viz MC/DC truth-table + self-analysis, `actions/upload-pages-artifact` +
`deploy-pages`). **One-time setup gotcha to document in the PR** (it bit both repos):
Pages *Source* must be "GitHub Actions", and the `github-pages` environment needs a
`v*` **tag** deployment-branch policy or tag deploys are rejected —
`gh api -X POST repos/<org>/<repo>/environments/github-pages/deployment-branch-policies -f name='v*' -f type=tag`.
(gale's `pages.yml` deploys only the gust demo, not a verification dashboard — that's
the gap, not coverage.)

## Track E — the verification IS extracted into rivet (gate, not prose)

A signed, dashboarded wasm is still non-compliant if the requirement→test mapping
isn't in the rivet graph. The right side of the V must be *driven*, not narrated.
The in-house exemplars already exist — **copy them, don't reinvent**:
- **relay** — test/target-level `verifies` links (e.g. a specific bazel coverage
  target → `SWREQ-…`), all 174 verification artifacts linked, + a `verification-gate.yml`
  that *executes* the steps (`run-falcon-verification.py`). The model for "name the
  actual test, not the crate."
- **gale** (642 links, ~complete coverage) and **synth** (141) for volume.
- The rivet-driven PR gate (`tools/run_verification.py` over `type: test-case`
  artifacts) is canonical in witness/loom/spar — adopt it where missing.

Laggards as of the sweep: scry (0 links despite 111 tests + 12 Rocq proofs + a live
MC/DC gate), witness (2/55), loom, meld, mcp. The procedure for closing this lives in
[`traceability-audit`]; this track just makes it a release-pipeline requirement.

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
2. **Identify the target repo's deltas** — Track A is broadly done org-wide; the
   live gaps from the 2026-06 sweep are Tracks B–E:
   - **Track A (binaries):** mostly compliant. Exceptions: sigil lacks the CycloneDX
     SBOM; kiln/mcp have no real release at all.
   - **Track B (distribution):** rivet is npm-only (no crates.io); sigil/synth/scry
     crates.io-only (no npm CLI wrapper); **mcp publishes via a stale unsigned manual
     script — move it into CI.**
   - **Track C (wasm):** the big one. loom/meld/gale/spar emit/handle wasm and run
     **neither** witness nor scry; relay/wohl run witness **manually** (not a gate);
     gale has an open `TODO(sigil)` and SLSA that misses the `.wasm`. (sigil-sign step
     is blocked on the wasip2-parser fix — add cosign now.)
   - **Track D (Pages):** only witness + scry deploy a verification dashboard — roll
     it to every repo running witness/scry.
   - **Track E (rivet extraction):** scry (0 links), witness (2/55), loom, meld, mcp
     are the laggards; copy relay's test-level pattern.
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
