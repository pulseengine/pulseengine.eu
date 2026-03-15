# Compliance Reports Integration — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate versioned rivet compliance report HTML exports from GitHub releases into the pulseengine.eu website, with automatic discovery, version switching, and cross-repo rebuild triggers.

**Architecture:** A TOML manifest declares which projects publish reports. A Rust CLI tool fetches release assets from GitHub, unpacks them into `static/reports/`, and generates `config.js` + `index.json`. The existing deploy workflow is extended with a `repository_dispatch` trigger so component releases rebuild the site.

**Tech Stack:** Rust (toml, serde, serde_json, ureq, flate2, tar, semver, glob-match), Zola templates (Tera), GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-03-15-compliance-reports-integration-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `reports.toml` | Create | Manifest declaring projects and exclude patterns |
| `tools/fetch-reports/Cargo.toml` | Create | Rust project for the build tool |
| `tools/fetch-reports/src/main.rs` | Create | Build tool: fetch, validate, unpack, generate config.js + index.json |
| `content/reports/_index.md` | Create | Reports index page content |
| `templates/reports.html` | Create | Zola template rendering project cards with version links |
| `templates/base.html` | Modify (line 33) | Add Reports nav link |
| `.github/workflows/deploy.yml` | Modify | Add repository_dispatch trigger + Rust toolchain + fetch-reports step |
| `docs/superpowers/plans/dispatch-step-for-components.md` | Create | Reference doc for component repo workflow changes |

---

## Chunk 1: Manifest and Rust Build Tool

### Task 1: Create `reports.toml` manifest

**Files:**
- Create: `reports.toml`

- [ ] **Step 1: Create the manifest file**

See spec section "Manifest: `reports.toml`" for the full TOML content. Two project entries (rivet, gale), each with `repo`, `asset_pattern`, and `exclude` fields.

- [ ] **Step 2: Commit**

```bash
git add reports.toml
git commit -m "feat: add reports.toml manifest for compliance report integration"
```

---

### Task 2: Scaffold `tools/fetch-reports/` Cargo project

**Files:**
- Create: `tools/fetch-reports/Cargo.toml`
- Create: `tools/fetch-reports/src/main.rs`

- [ ] **Step 1: Create Cargo.toml**

```toml
[package]
name = "fetch-reports"
version = "0.1.0"
edition = "2024"
publish = false

[dependencies]
flate2 = "1"
glob-match = "0.2"
semver = "1"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tar = "0.4"
toml = "0.8"
ureq = "3"
```

- [ ] **Step 2: Create minimal main.rs that parses the manifest**

A `main.rs` with:
- Manifest struct: `projects: HashMap<String, ProjectConfig>` where `ProjectConfig` has `repo`, `asset_pattern`, `exclude`
- Read and parse `reports.toml` from repo root (determined relative to the binary or via env)
- Print parsed projects and exit

- [ ] **Step 3: Verify it builds and parses**

Run: `cargo run --manifest-path tools/fetch-reports/Cargo.toml`
Expected: Prints the two project entries from reports.toml.

- [ ] **Step 4: Commit**

```bash
git add tools/fetch-reports/
git commit -m "feat: scaffold fetch-reports Rust tool with manifest parsing"
```

---

### Task 3: Implement GitHub API release fetching and filtering

**Files:**
- Modify: `tools/fetch-reports/src/main.rs`

- [ ] **Step 1: Add release fetching**

Add a function that calls `GET https://api.github.com/repos/{owner}/{repo}/releases?per_page=100` using `ureq`, reads `GITHUB_TOKEN` env var for auth, follows `Link` header pagination, and deserializes into a `Vec<Release>` struct (fields: `tag_name`, `assets: Vec<Asset>` where Asset has `name` and `browser_download_url`).

- [ ] **Step 2: Add filtering logic**

Filter releases:
- Skip tags matching any `exclude` pattern via `glob_match::glob_match`
- Find the asset matching `asset_pattern` with `{name}` and `{version}` substituted
- Parse version via `semver::Version`
- Sort descending by semver

Return `Vec<(Version, String)>` (version, download URL).

- [ ] **Step 3: Test against real repos (will find 0 compliance assets)**

Run: `GITHUB_TOKEN=$(gh auth token) cargo run --manifest-path tools/fetch-reports/Cargo.toml`
Expected: Fetches releases from pulseengine/rivet and pulseengine/gale, finds 0 matching compliance report assets, generates empty index.json.

- [ ] **Step 4: Commit**

```bash
git add tools/fetch-reports/src/main.rs
git commit -m "feat: add GitHub release fetching and filtering to fetch-reports"
```

---

### Task 4: Implement download, tarball safety, extraction, and config.js generation

**Files:**
- Modify: `tools/fetch-reports/src/main.rs`

- [ ] **Step 1: Add tarball download and safety validation**

Download asset via `ureq::get(url)` to a temp file. Open with `flate2::read::GzDecoder` + `tar::Archive`. Iterate entries and reject if any path:
- Is absolute
- Contains `..`
- Resolves outside the target directory

- [ ] **Step 2: Add extraction into `static/reports/<project>/<version>/`**

Extract validated tarball. Check cache first: skip if `compliance/index.html` already exists in the target.

- [ ] **Step 3: Add config.js generation**

Write `var RIVET_CONFIG = { ... }` into each `compliance/config.js` with:
- `homepage`, `projectName`, `versionLabel`
- `versions` array built from all discovered versions + "latest"
- All paths relative (`../0.1.0/compliance/`)

- [ ] **Step 4: Add latest directory copy**

Copy highest semver version's `compliance/` to `<project>/latest/compliance/` using `fs::copy` recursively. Remove existing latest dir first.

- [ ] **Step 5: Add index.json generation**

Write `static/reports/index.json` with `{ "projects": { "<name>": { "latest": "x.y.z", "versions": [...] } } }`.

- [ ] **Step 6: Test end-to-end (still 0 real assets, but full code path exercised)**

Run: `GITHUB_TOKEN=$(gh auth token) cargo run --manifest-path tools/fetch-reports/Cargo.toml`
Expected: Completes without error, generates empty `index.json`.

- [ ] **Step 7: Commit**

```bash
git add tools/fetch-reports/
git commit -m "feat: complete fetch-reports with download, extraction, config.js, and index.json"
```

---

## Chunk 2: Reports Index Page and Navigation

### Task 5: Create reports index page

**Files:**
- Create: `content/reports/_index.md`
- Create: `templates/reports.html`

- [ ] **Step 1: Create content file**

`content/reports/_index.md` with frontmatter: title "Compliance Reports", template "reports.html".

- [ ] **Step 2: Create template**

`templates/reports.html` extends `base.html`. Uses `load_data(path="static/reports/index.json")` to read the generated index. Renders glass-card per project with version badges linking to `/reports/<project>/<version>/compliance/`. Shows "No compliance reports available yet." if index.json missing or empty.

Use `get_file_hash` as existence check before `load_data`.

- [ ] **Step 3: Verify Zola builds**

Run: `zola build 2>&1 | tail -5`
Expected: Succeeds.

- [ ] **Step 4: Commit**

```bash
git add content/reports/_index.md templates/reports.html
git commit -m "feat: add compliance reports index page"
```

---

### Task 6: Add Reports nav link

**Files:**
- Modify: `templates/base.html:29-34`

- [ ] **Step 1: Add link after Projects, before GitHub**

```html
<a href="{{ get_url(path='@/reports/_index.md') }}"{% if current_path is starting_with("/reports") %} class="active"{% endif %}>Reports</a>
```

- [ ] **Step 2: Verify build and nav**

Run: `zola build && grep -c "Reports" public/index.html`
Expected: >= 1 match.

- [ ] **Step 3: Commit**

```bash
git add templates/base.html
git commit -m "feat: add Reports link to site navigation"
```

---

## Chunk 3: CI Workflow and Documentation

### Task 7: Modify deploy workflow

**Files:**
- Modify: `.github/workflows/deploy.yml`

- [ ] **Step 1: Add repository_dispatch trigger**

```yaml
on:
  push:
    branches: [main]
  repository_dispatch:
    types: [compliance-report-updated]
```

- [ ] **Step 2: Add Rust toolchain, cache, and fetch-reports steps**

Insert after "Inject git info" step, before "Inject build info" step:

```yaml
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

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "feat: add Rust fetch-reports and repository_dispatch to deploy workflow"
```

---

### Task 8: Document dispatch step for component repos

**Files:**
- Create: `docs/superpowers/plans/dispatch-step-for-components.md`

- [ ] **Step 1: Create reference document**

Document: the YAML snippet for component release workflows, the required secret (`PULSEENGINE_DISPATCH_TOKEN` — fine-grained PAT with `contents: write` on pulseengine.eu), and testing instructions.

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/plans/dispatch-step-for-components.md
git commit -m "docs: add reference for component release workflow dispatch step"
```

---

## Chunk 4: Smoke Test and PR

### Task 9: End-to-end smoke test with mock report

- [ ] **Step 1: Create mock compliance tarball**

Create `/tmp/compliance/` with minimal `index.html`, `coverage.html`, `matrix.html` (each with `<script src="./config.js"></script>`). Tar into `/tmp/compliance-report.tar.gz`.

- [ ] **Step 2: Unpack into static/reports/rivet/0.1.0/**

- [ ] **Step 3: Verify Zola copies through**

Run: `zola build && ls public/reports/rivet/0.1.0/compliance/index.html`

- [ ] **Step 4: Clean up** (do NOT commit test artifacts)

```bash
rm -rf static/reports/rivet
```

---

### Task 10: Create PR

- [ ] **Step 1: Create branch, push, open PR**

```bash
git checkout -b feat/compliance-reports-integration
git push -u origin feat/compliance-reports-integration
gh pr create --title "feat: compliance reports integration"
```

PR body: summary, prerequisites note (rivet export --html doesn't exist yet), test plan, link to spec.

- [ ] **Step 2: Monitor CI and merge when green**
