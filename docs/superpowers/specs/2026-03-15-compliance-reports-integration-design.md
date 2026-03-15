# Compliance Reports Integration

Integrate versioned rivet compliance report exports into pulseengine.eu so that each PulseEngine component's release automatically appears on the website with coverage, traceability, and verification data.

## Prerequisites

This design depends on capabilities that do not yet exist:

1. **`rivet export --html`** — rivet currently supports `reqif` and `generic-yaml` export formats. A static HTML export must be implemented in rivet first. The live dashboard (axum + HTMX) needs to be adapted to produce self-contained static pages with relative links. This is rivet's concern but is a hard blocker for this integration.
2. **Compliance report release assets** — component release workflows (rivet, gale, etc.) must be updated to run `rivet export --html`, package the output, and attach it as a release asset. No component currently produces this asset.

This spec defines the **website integration layer** and the **contract** that rivet's export must satisfy. The rivet export implementation and release workflow updates are separate work items.

## Context

Once `rivet export --html` exists, each PulseEngine component that uses rivet (e.g., gale, rivet itself) will publish a static HTML compliance report as a GitHub release asset alongside platform binaries and test evidence.

The pulseengine.eu website needs to:

1. Know which projects publish compliance reports
2. Automatically discover new releases (excluding pre-releases, RCs, etc.)
3. Download the HTML exports from GitHub releases
4. Serve them under versioned paths with a version switcher
5. Rebuild whenever any component publishes a new release

## Architecture

Three moving parts: a manifest, a build script, and a cross-repo trigger.

```
Component repo (e.g., gale)         pulseengine.eu
┌──────────────────────────┐        ┌────────────────────────────────┐
│ git tag v0.1.0           │        │ reports.toml (manifest)        │
│   ↓                      │        │   ↓                            │
│ CI: build + test         │        │ tools/fetch-reports       │
│   ↓                      │        │   ↓                            │
│ gh release create        │        │ static/reports/<proj>/<ver>/   │
│   assets:                │        │   compliance/                  │
│     ...-compliance-      │──(1)──→│     index.html, coverage.html  │
│       report.tar.gz      │        │     config.js (generated)      │
│   ↓                      │        │   ↓                            │
│ gh api dispatches ───(2)─┼───────→│ repository_dispatch            │
│   compliance-report-     │        │   → fetch-reports → zola build │
│   updated                │        │   → deploy                     │
└──────────────────────────┘        └────────────────────────────────┘
```

(1) Build script fetches assets from GH releases at build time.
(2) Component release workflow triggers pulseengine.eu rebuild.

## Manifest: `reports.toml`

Lives in the pulseengine.eu repo root. Declares which projects publish compliance reports and what release tags to skip. Uses TOML since Python 3.11+ has `tomllib` in stdlib — no external dependencies needed.

```toml
# reports.toml — projects that publish rivet compliance reports

[projects.rivet]
repo = "pulseengine/rivet"
asset_pattern = "{name}-v{version}-compliance-report.tar.gz"
exclude = ["*-rc*", "*-alpha*"]

[projects.gale]
repo = "pulseengine/gale"
asset_pattern = "{name}-v{version}-compliance-report.tar.gz"
exclude = ["*-rc*", "*-alpha*"]
```

### Fields

- **repo**: GitHub owner/repo.
- **asset_pattern**: Naming convention for the compliance report asset in each release. `{name}` is substituted from the project key, `{version}` from the tag (stripped of the `v` prefix).
- **exclude**: Glob patterns matched against the release tag name. Any matching tag is skipped.

### Adding a project

Add an entry to `reports.toml`. The next build picks it up automatically.

### Excluding a version

Add a pattern or exact version to `exclude`. The next build drops it.

## Build Tool: `tools/fetch-reports/`

A Rust CLI binary that runs during CI before `zola build`. Lives in `tools/fetch-reports/` within the pulseengine.eu repo as a standalone Cargo project.

### Dependencies

- `toml` — parse `reports.toml`
- `serde` + `serde_json` — deserialize GitHub API responses, serialize index.json
- `glob-match` — fnmatch-style pattern matching for exclude filters
- `flate2` + `tar` — tarball extraction with path validation
- `ureq` — HTTP client for GitHub API (minimal, blocking)
- `semver` — version parsing and sorting

### Steps

1. **Parse** `reports.toml` using `toml` crate.
2. **For each project**:
   a. Call GitHub REST API `GET /repos/{owner}/{repo}/releases` with pagination (follow `Link` headers).
   b. Filter out tags matching any `exclude` pattern (using glob matching).
   c. Filter out releases that have no matching compliance report asset.
   d. Sort remaining versions by semver (descending).
   e. For each version:
      - Skip if `static/reports/<project>/<version>/compliance/index.html` already exists (cache hit).
      - Download the compliance report tarball via the asset's `browser_download_url`.
      - Validate tarball contents: all paths must be within the `compliance/` prefix (path traversal protection).
      - Unpack into `static/reports/<project>/<version>/compliance/`.
      - Generate `config.js` (see below).
   f. Copy the highest semver version's compliance directory to `static/reports/<project>/latest/compliance/` (directory copy, not symlink — Zola and tar do not reliably preserve symlinks).
3. **Generate** `static/reports/index.json` — a machine-readable index of all projects and their available versions, consumed by a Zola template to render the reports index page.

### Caching

The tool checks for an existing `index.html` before downloading each version. Already-fetched versions are skipped. This means incremental builds only download new releases. For CI, the `static/reports/` directory can be cached between runs using `actions/cache`.

### Tarball Safety

Before extracting, the tool iterates all tarball entries and rejects the archive if any entry:
- Has an absolute path
- Contains `..` path components
- Extracts outside the target directory

### Generated `config.js`

The build tool writes a `config.js` into each version's compliance directory:

```js
var RIVET_EXPORT = {
  homepage: "https://pulseengine.eu/projects/",
  projectName: "Gale",
  versionLabel: "v0.1.0",
  versions: [
    { label: "v0.2.0", path: "../0.2.0/compliance/" },
    { label: "v0.1.0", path: "../0.1.0/compliance/" },
    { label: "latest", path: "../latest/compliance/" }
  ]
};
```

This is generated — not hand-written. The version list is computed from the discovered releases for that project. The `homepage` and `projectName` come from the manifest + conventions.

### Pagination

The tool follows `Link` response headers from the GitHub API, fetching all pages. In practice, PulseEngine projects are young and pagination is unlikely to be needed soon.

### Semver Sorting

Version tags are parsed using the `semver` crate and sorted numerically.

### Stale Version Cleanup

If a release is deleted or a version is added to `exclude` after it was previously fetched, the cached directory persists. This is acceptable — deleted releases are rare. A `--clean` flag can be added later to wipe `static/reports/` and re-fetch everything if needed.

### CI Usage

In CI, the tool is built from source (`cargo run --release --manifest-path tools/fetch-reports/Cargo.toml`). For faster CI, a pre-built binary could be cached or published as a release asset itself, but building from source is fine for now (~5s compile on a warm cache).

## Cross-Repo Trigger

### Component side (sender)

Each component's release workflow adds a final step after publishing the GH release:

```yaml
- name: Trigger website rebuild
  if: success()
  env:
    GH_TOKEN: ${{ secrets.PULSEENGINE_DISPATCH_TOKEN }}
  run: |
    gh api repos/pulseengine/pulseengine.eu/dispatches \
      --field event_type=compliance-report-updated \
      --field "client_payload[project]=${{ github.event.repository.name }}" \
      --field "client_payload[version]=${{ github.ref_name }}"
```

Requires a fine-grained PAT with `contents: write` scope on pulseengine.eu only (not full `repo` scope), stored as `PULSEENGINE_DISPATCH_TOKEN` in the component repo's secrets. A GitHub App installation token scoped to pulseengine.eu is preferred if available.

### Website side (receiver)

The existing `deploy.yml` workflow is **modified** (not replaced) to add two things:

1. A `repository_dispatch` trigger alongside the existing `push` trigger
2. A fetch-reports step before `zola build`

Changes to `.github/workflows/deploy.yml`:

```yaml
# Add to the existing 'on:' block:
on:
  push:
    branches: [main]
  repository_dispatch:
    types: [compliance-report-updated]

# Add these steps before the existing 'zola build' step:
- name: Install Rust toolchain
  uses: dtolnay/rust-toolchain@stable

- name: Cache fetch-reports build
  uses: actions/cache@v4
  with:
    path: tools/fetch-reports/target
    key: fetch-reports-${{ hashFiles('tools/fetch-reports/Cargo.lock') }}

- name: Fetch compliance reports
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: cargo run --release --manifest-path tools/fetch-reports/Cargo.toml
```

All existing steps (checkout with `fetch-depth: 0`, `inject-git-info.py`, Zola 0.22.1 install, SSH setup, deploy via `scp`/`ssh` with proper secrets) remain unchanged.

## Directory Structure

After the build tool runs, before `zola build`:

```
pulseengine.eu/
  reports.toml
  tools/
    fetch-reports/
      Cargo.toml
      Cargo.lock
      src/
        main.rs
  static/
    reports/
      index.json                          ← generated, consumed by Zola template
      rivet/
        0.1.0/
          compliance/
            index.html                    ← from rivet export
            coverage.html
            matrix.html
            verification.html
            artifacts.html
            ...
            config.js                     ← generated by fetch-reports
        latest/
          compliance/                     ← copy of highest semver version
            ...
      gale/
        0.1.0/
          compliance/
            ...
            config.js
        latest/
          compliance/
            ...
  content/
    reports/
      _index.md                           ← reports index page
```

## Reports Index Page

A Zola template-driven page at `/reports/` that reads `static/reports/index.json` via `load_data` and renders a list of projects with their available versions.

`index.json` structure:

```json
{
  "projects": {
    "rivet": {
      "latest": "0.1.0",
      "versions": ["0.1.0"]
    },
    "gale": {
      "latest": "0.1.0",
      "versions": ["0.1.0", "0.2.0"]
    }
  }
}
```

The template renders project cards (reusing the existing `glass-card` design system) with version links pointing to `/reports/<project>/<version>/compliance/`.

If `index.json` does not exist (e.g., fresh checkout without running the build script), the template shows an empty state: "No compliance reports available yet."

## Rivet Export Contract

The build script expects each compliance report tarball to contain a flat directory of HTML files:

```
compliance/
  index.html          ← dashboard overview / entry point
  coverage.html
  matrix.html
  verification.html
  artifacts.html
  ...                 ← any other views rivet exports
```

Requirements on the exported HTML:

- All inter-page links are **relative** (`./coverage.html`, `#art-REQ-001`).
- Each page includes `<script src="./config.js"></script>`.
- Pages work standalone without `config.js` (graceful degradation — the version switcher and homepage link simply don't appear).
- No external CDN dependencies baked in (HTMX, Mermaid, fonts should be bundled or optional).
- CSS is self-contained (embedded or a local stylesheet).

## Future: Baselines

Not in scope for this design, but the architecture supports it. A baseline would be a named set of component versions:

```toml
[baselines."2026-Q1"]
gale = "0.1.0"
rivet = "0.1.0"
sigil = "0.5.1"
```

This could live in `reports.toml` or a separate file. The reports index page would show baselines as curated sets linking to the specific version reports. The build script already fetches all versions — baselines are just a presentation concern.

## What This Design Does NOT Cover

- **Rivet export implementation** — that's rivet's domain. We only define the contract (tarball structure, relative links, config.js script tag). See Prerequisites.
- **Test evidence integration** — the `*-test-evidence.tar.gz` asset is a separate concern. Could follow the same pattern later.
- **CSS theming** — rivet's exported HTML has its own embedded CSS. If we want it to match pulseengine.eu's dark theme, that's a rivet export flag (`--theme dark`), not a website concern.

## Implementation Order

0. **Rivet `export --html`** — prerequisite, implemented in the rivet repo (not this spec's scope but blocks everything).
1. **`reports.toml`** + **`tools/fetch-reports/`** (Rust CLI) — the core integration in pulseengine.eu.
2. **Reports index page** — Zola template at `/reports/`.
3. **CI workflow update** — modify existing `deploy.yml` to add fetch-reports step and repository_dispatch trigger.
4. **Component release workflows** — add compliance report asset creation and dispatch step to rivet (and later gale, sigil, etc.).
5. **Navigation** — add "Reports" link to pulseengine.eu header nav.

Steps 1-3 and 5 are in the pulseengine.eu repo. Step 4 is per component repo.
