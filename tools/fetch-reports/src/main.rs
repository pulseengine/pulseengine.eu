use flate2::read::GzDecoder;
use glob_match::glob_match;
use semver::Version;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use tar::Archive;

// ── Manifest types ──────────────────────────────────────────────────────

#[derive(Debug, Deserialize)]
struct Manifest {
    projects: HashMap<String, ProjectConfig>,
}

#[derive(Debug, Deserialize)]
struct ProjectConfig {
    repo: String,
    asset_pattern: String,
    exclude: Vec<String>,
    /// Report kind: "compliance" (rivet HTML bundle, the default) or "mcdc"
    /// (witness MC/DC evidence bundle). Controls the extract subdirectory and
    /// the entry-point HTML file the website links to.
    #[serde(default = "default_kind")]
    kind: String,
}

fn default_kind() -> String {
    "compliance".to_string()
}

/// Map a report kind to its (extract subdirectory, entry-point HTML filename).
fn kind_layout(kind: &str) -> (&'static str, &'static str) {
    match kind {
        // The witness evidence bundle nests its viewer under verdict-evidence/.
        "mcdc" => ("mcdc", "verdict-evidence/suite-index.html"),
        _ => ("compliance", "index.html"),
    }
}

// ── GitHub API types ────────────────────────────────────────────────────

#[derive(Debug, Deserialize)]
struct Release {
    tag_name: String,
    assets: Vec<Asset>,
}

#[derive(Debug, Deserialize)]
struct Asset {
    name: String,
    browser_download_url: String,
    /// Asset size in bytes (from the GitHub API). Used to skip pathologically
    /// large report bundles that would bloat `site.tar.gz` until the deploy hangs.
    #[serde(default)]
    size: u64,
}

/// A compliance/MC-DC report is HTML + YAML + a few SVGs — single-digit MB in a
/// healthy release (witness ships 169 of them for ~52 MB total). A multi-hundred-MB
/// asset is a packaging bug (e.g. `target/` bundled in); fetching it balloons
/// `static/reports/` until the scp deploy stalls. Skip anything over this cap.
const MAX_REPORT_BYTES: u64 = 50 * 1024 * 1024;

// ── Resolved version ────────────────────────────────────────────────────

#[derive(Debug)]
struct ResolvedVersion {
    version: Version,
    _tag: String,
    download_url: String,
}

// ── Generic-yaml (artifacts.yaml) types ──────────────────────────────────
//
// The compliance bundle includes `artifacts.yaml` (rivet's generic-yaml
// export) whenever the producer runs the compliance action with
// `include-data-formats: true`. We parse the subset of fields the website
// needs and ignore the rest (fields, fields-per-variant, provenance) — so
// no `deny_unknown_fields` here.

#[derive(Debug, Deserialize)]
struct GenericFile {
    artifacts: Vec<GenericArtifact>,
}

#[derive(Debug, Deserialize)]
struct GenericArtifact {
    id: String,
    #[serde(rename = "type")]
    artifact_type: String,
    #[serde(default)]
    title: String,
    #[serde(default)]
    description: Option<String>,
    #[serde(default)]
    status: Option<String>,
    #[serde(default)]
    tags: Vec<String>,
    #[serde(default)]
    links: Vec<Link>,
}

#[derive(Debug, Deserialize, Serialize)]
struct Link {
    target: String,
    #[serde(rename = "type")]
    link_type: String,
}

// ── data/{project}/ output types ─────────────────────────────────────────
//
// Shapes match what the `compliance_stats` / `compliance_artifact`
// shortcodes load via `load_data(path="data/{project}/...")`.

#[derive(Debug, Serialize)]
struct StatsJson {
    total: usize,
    /// Counts keyed by artifact type. BTreeMap → deterministic, sorted keys.
    by_type: std::collections::BTreeMap<String, usize>,
    /// Counts keyed by status; a missing status is bucketed as "unset"
    /// (matching rivet-core's `snapshot.rs` aggregation).
    by_status: std::collections::BTreeMap<String, usize>,
}

#[derive(Debug, Serialize)]
struct ArtifactsJson {
    artifacts: Vec<OutArtifact>,
}

#[derive(Debug, Serialize)]
struct OutArtifact {
    id: String,
    #[serde(rename = "type")]
    artifact_type: String,
    title: String,
    description: String,
    status: String,
    tags: Vec<String>,
    links: Vec<Link>,
}

// ── index.json types ────────────────────────────────────────────────────

#[derive(Debug, Serialize)]
struct IndexJson {
    projects: HashMap<String, ProjectIndex>,
}

#[derive(Debug, Serialize)]
struct ProjectIndex {
    /// "compliance" or "mcdc" — lets the reports page group the two kinds.
    kind: String,
    latest: String,
    /// All versions, sorted descending by semver.
    versions: Vec<String>,
    /// Latest patch per minor version (e.g., 0.1.2, 0.2.5, 0.3.0, 1.0.0).
    /// Used by the reports page to show a compact version list.
    display_versions: Vec<String>,
}

// ── Helpers ─────────────────────────────────────────────────────────────

fn repo_root() -> PathBuf {
    // The Cargo manifest lives at tools/fetch-reports/Cargo.toml,
    // so the repo root is two directories up.
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest_dir
        .parent()
        .expect("missing tools/")
        .parent()
        .expect("missing repo root")
        .to_path_buf()
}

/// Strip the leading `v` (or `V`) from a tag name if present.
fn strip_v_prefix(tag: &str) -> &str {
    tag.strip_prefix('v')
        .or_else(|| tag.strip_prefix('V'))
        .unwrap_or(tag)
}

/// Build the expected asset filename by substituting placeholders.
fn expected_asset_name(pattern: &str, project_name: &str, version_str: &str) -> String {
    pattern
        .replace("{name}", project_name)
        .replace("{version}", version_str)
}

/// Capitalize the first letter of a string.
fn capitalize_first(s: &str) -> String {
    let mut chars = s.chars();
    match chars.next() {
        None => String::new(),
        Some(c) => c.to_uppercase().to_string() + chars.as_str(),
    }
}

/// Parse the `Link` header to find the URL for `rel="next"`.
fn parse_link_next(link_header: &str) -> Option<String> {
    for part in link_header.split(',') {
        let part = part.trim();
        // Each part looks like: <https://...>; rel="next"
        if part.contains("rel=\"next\"") {
            if let (Some(start), Some(end)) = (part.find('<'), part.find('>')) {
                return Some(part[start + 1..end].to_string());
            }
        }
    }
    None
}

/// Recursively copy a directory tree.
fn copy_dir_recursive(src: &Path, dst: &Path) -> io::Result<()> {
    fs::create_dir_all(dst)?;
    for entry in fs::read_dir(src)? {
        let entry = entry?;
        let file_type = entry.file_type()?;
        let src_path = entry.path();
        let dst_path = dst.join(entry.file_name());
        if file_type.is_dir() {
            copy_dir_recursive(&src_path, &dst_path)?;
        } else {
            fs::copy(&src_path, &dst_path)?;
        }
    }
    Ok(())
}

/// Remove a directory if it exists (ignoring "not found" errors).
fn remove_dir_if_exists(path: &Path) -> io::Result<()> {
    match fs::remove_dir_all(path) {
        Ok(()) => Ok(()),
        Err(e) if e.kind() == io::ErrorKind::NotFound => Ok(()),
        Err(e) => Err(e),
    }
}

// ── GitHub API ──────────────────────────────────────────────────────────

fn fetch_releases(agent: &ureq::Agent, repo: &str, token: &Option<String>) -> Vec<Release> {
    let mut all_releases: Vec<Release> = Vec::new();
    let mut url = format!(
        "https://api.github.com/repos/{repo}/releases?per_page=100"
    );

    loop {
        let mut req = agent.get(&url).header("User-Agent", "fetch-reports/0.1.0");

        if let Some(tok) = token {
            req = req.header("Authorization", &format!("Bearer {tok}"));
        }

        let response = match req.call() {
            Ok(resp) => resp,
            Err(e) => {
                eprintln!("  Warning: GitHub API request failed for {repo}: {e}");
                return all_releases;
            }
        };

        // Grab the Link header before consuming the body.
        let link_header = response
            .headers()
            .get("link")
            .and_then(|v| v.to_str().ok())
            .map(|s| s.to_string());

        let mut response = response; // rebind for body_mut
        let body_str = match response.body_mut().read_to_string() {
            Ok(s) => s,
            Err(e) => {
                eprintln!("  Warning: failed to read response body for {repo}: {e}");
                return all_releases;
            }
        };
        let page: Vec<Release> = match serde_json::from_str(&body_str) {
            Ok(v) => v,
            Err(e) => {
                eprintln!("  Warning: failed to parse releases JSON for {repo}: {e}");
                return all_releases;
            }
        };

        all_releases.extend(page);

        // Follow pagination via Link header.
        match link_header.and_then(|h| parse_link_next(&h)) {
            Some(next_url) => url = next_url,
            None => break,
        }
    }

    all_releases
}

// ── Filtering ───────────────────────────────────────────────────────────

fn filter_releases(
    releases: Vec<Release>,
    project_name: &str,
    config: &ProjectConfig,
) -> Vec<ResolvedVersion> {
    let mut resolved: Vec<ResolvedVersion> = Vec::new();

    for release in releases {
        // Skip tags matching any exclude pattern.
        let excluded = config
            .exclude
            .iter()
            .any(|pat| glob_match(pat, &release.tag_name));
        if excluded {
            continue;
        }

        let version_str = strip_v_prefix(&release.tag_name);
        let version = match Version::parse(version_str) {
            Ok(v) => v,
            Err(_) => continue, // skip non-semver tags
        };

        let expected = expected_asset_name(&config.asset_pattern, project_name, version_str);

        // Find the matching asset.
        let asset = release.assets.iter().find(|a| a.name == expected);
        let asset = match asset {
            Some(a) => a,
            None => continue,
        };

        // Skip pathologically large report assets — a packaging bug (e.g. rivet
        // v0.4.x/v0.7–0.9 shipped ~800 MB bundles) that would bloat site.tar.gz
        // until the deploy scp hangs. Warn loudly rather than silently ship it.
        if asset.size > MAX_REPORT_BYTES {
            eprintln!(
                "[{project_name}] {}: SKIPPING oversized report ({} MB > {} MB cap) — likely a packaging bug in the report producer",
                release.tag_name,
                asset.size / (1024 * 1024),
                MAX_REPORT_BYTES / (1024 * 1024),
            );
            continue;
        }

        resolved.push(ResolvedVersion {
            version,
            _tag: release.tag_name.clone(),
            download_url: asset.browser_download_url.clone(),
        });
    }

    // Sort descending by semver.
    resolved.sort_by(|a, b| b.version.cmp(&a.version));
    resolved
}

// ── Tarball safety ──────────────────────────────────────────────────────

fn validate_tarball(path: &Path) -> Result<(), String> {
    let file =
        fs::File::open(path).map_err(|e| format!("failed to open tarball: {e}"))?;
    let decoder = GzDecoder::new(file);
    let mut archive = Archive::new(decoder);

    for entry in archive
        .entries()
        .map_err(|e| format!("failed to read tarball entries: {e}"))?
    {
        let entry = entry.map_err(|e| format!("failed to read tarball entry: {e}"))?;
        let entry_path = entry
            .path()
            .map_err(|e| format!("invalid path in tarball: {e}"))?;
        let entry_str = entry_path.to_string_lossy();

        // Reject absolute paths.
        if entry_str.starts_with('/') {
            return Err(format!("absolute path in tarball: {entry_str}"));
        }

        // Reject path traversal.
        for component in entry_path.components() {
            if let std::path::Component::ParentDir = component {
                return Err(format!("path traversal in tarball: {entry_str}"));
            }
        }

        // Entries must not escape the extraction directory.
        // Flat files (no compliance/ prefix) are fine — we extract into
        // a compliance/ subdirectory ourselves.
    }

    Ok(())
}

// ── Download & extract ──────────────────────────────────────────────────

fn download_and_extract(
    agent: &ureq::Agent,
    token: &Option<String>,
    url: &str,
    dest_dir: &Path,
    subdir: &str,
) -> Result<(), String> {
    // Download to a temporary file.
    let tmp_path = dest_dir.join("_download.tar.gz");
    fs::create_dir_all(dest_dir)
        .map_err(|e| format!("failed to create directory {}: {e}", dest_dir.display()))?;

    let mut req = agent.get(url).header("User-Agent", "fetch-reports/0.1.0");
    if let Some(tok) = token {
        req = req.header("Authorization", &format!("Bearer {tok}"));
    }

    let mut response = req
        .call()
        .map_err(|e| format!("download failed: {e}"))?;

    {
        let mut file = fs::File::create(&tmp_path)
            .map_err(|e| format!("failed to create temp file: {e}"))?;
        let mut reader = response.body_mut().as_reader();
        io::copy(&mut reader, &mut file)
            .map_err(|e| format!("failed to write download: {e}"))?;
    }

    // Validate tarball safety.
    validate_tarball(&tmp_path)?;

    // Extract into the kind's subdirectory (the tarballs have flat files).
    let out_dir = dest_dir.join(subdir);
    fs::create_dir_all(&out_dir)
        .map_err(|e| format!("failed to create {subdir} dir: {e}"))?;
    let file = fs::File::open(&tmp_path)
        .map_err(|e| format!("failed to open tarball for extraction: {e}"))?;
    let decoder = GzDecoder::new(file);
    let mut archive = Archive::new(decoder);
    archive
        .unpack(&out_dir)
        .map_err(|e| format!("failed to extract tarball: {e}"))?;

    // Clean up temp file.
    let _ = fs::remove_file(&tmp_path);

    Ok(())
}

// ── config.js generation ────────────────────────────────────────────────

fn write_config_js(
    project_name: &str,
    all_versions: &[&Version],
    version_dir: &Path,
) -> io::Result<()> {
    let config_path = version_dir.join("compliance").join("config.js");

    let pretty_name = capitalize_first(project_name);
    let version_label = format!("v{version_dir}", version_dir = version_dir
        .file_name()
        .unwrap()
        .to_string_lossy());

    // Build the versions array entries.
    let mut version_entries = String::new();
    for (i, v) in all_versions.iter().enumerate() {
        let comma = if i + 1 < all_versions.len() + 1 { "," } else { "" }; // +1 for latest
        version_entries.push_str(&format!(
            "    {{ label: \"v{v}\", path: \"../../{v}/compliance/\" }}{comma}\n"
        ));
    }
    // Add "latest" entry (always last, no trailing comma).
    // Paths go up twice: out of compliance/, out of <version>/, into <target>/.
    version_entries.push_str("    { label: \"latest\", path: \"../../latest/compliance/\" }\n");

    let content = format!(
        "var RIVET_EXPORT = {{\n  \
         homepage: \"https://pulseengine.eu/projects/\",\n  \
         projectName: \"{pretty_name}\",\n  \
         versionLabel: \"{version_label}\",\n  \
         versions: [\n{version_entries}  ]\n\
         }};\n"
    );

    if let Some(parent) = config_path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&config_path, content)?;
    Ok(())
}

// ── data/{project}/ generation ────────────────────────────────────────────

/// Parse `artifacts.yaml` from an extracted bundle and (re)write
/// `data/{project}/stats.json` + `data/{project}/artifacts.json`.
///
/// Aggregation mirrors rivet-core's `snapshot.rs`: `by_type` groups on the
/// artifact type, `by_status` maps a missing status to "unset", `total` is
/// the artifact count. Returns the artifact count on success.
fn generate_data_files(
    project_name: &str,
    yaml_path: &Path,
    root: &Path,
) -> Result<usize, String> {
    let content = fs::read_to_string(yaml_path)
        .map_err(|e| format!("failed to read {}: {e}", yaml_path.display()))?;
    let file: GenericFile = serde_yaml::from_str(&content)
        .map_err(|e| format!("failed to parse artifacts.yaml: {e}"))?;

    let mut by_type = std::collections::BTreeMap::new();
    let mut by_status = std::collections::BTreeMap::new();
    let mut artifacts = Vec::with_capacity(file.artifacts.len());

    for a in file.artifacts {
        *by_type.entry(a.artifact_type.clone()).or_insert(0usize) += 1;
        let status = a.status.unwrap_or_else(|| "unset".to_string());
        *by_status.entry(status.clone()).or_insert(0usize) += 1;
        artifacts.push(OutArtifact {
            id: a.id,
            artifact_type: a.artifact_type,
            title: a.title,
            description: a.description.unwrap_or_default(),
            status,
            tags: a.tags,
            links: a.links,
        });
    }

    let total = artifacts.len();
    let data_dir = root.join("data").join(project_name);
    fs::create_dir_all(&data_dir)
        .map_err(|e| format!("failed to create {}: {e}", data_dir.display()))?;

    let stats = StatsJson {
        total,
        by_type,
        by_status,
    };
    let stats_json = serde_json::to_string_pretty(&stats)
        .map_err(|e| format!("failed to serialize stats.json: {e}"))?;
    fs::write(data_dir.join("stats.json"), stats_json + "\n")
        .map_err(|e| format!("failed to write stats.json: {e}"))?;

    let arts = ArtifactsJson { artifacts };
    let arts_json = serde_json::to_string_pretty(&arts)
        .map_err(|e| format!("failed to serialize artifacts.json: {e}"))?;
    fs::write(data_dir.join("artifacts.json"), arts_json + "\n")
        .map_err(|e| format!("failed to write artifacts.json: {e}"))?;

    Ok(total)
}

// ── main ────────────────────────────────────────────────────────────────

fn main() {
    let root = repo_root();
    let manifest_path = root.join("reports.toml");

    // Graceful exit if manifest doesn't exist.
    if !manifest_path.exists() {
        println!("reports.toml not found — nothing to fetch.");
        return;
    }

    let content = match fs::read_to_string(&manifest_path) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("Warning: failed to read {}: {e}", manifest_path.display());
            return;
        }
    };

    let manifest: Manifest = match toml::from_str(&content) {
        Ok(m) => m,
        Err(e) => {
            eprintln!("Error: failed to parse reports.toml: {e}");
            std::process::exit(1);
        }
    };

    let token = std::env::var("GITHUB_TOKEN").ok();
    let agent = ureq::Agent::new_with_config(
        ureq::Agent::config_builder()
            .http_status_as_error(true)
            .build(),
    );

    let reports_dir = root.join("static").join("reports");
    fs::create_dir_all(&reports_dir).expect("failed to create static/reports/");

    // Collect results for index.json.
    let mut index = IndexJson {
        projects: HashMap::new(),
    };

    // Sort project names for deterministic output.
    let mut project_names: Vec<&String> = manifest.projects.keys().collect();
    project_names.sort();

    for project_name in project_names {
        let config = &manifest.projects[project_name];
        println!("[{project_name}] Fetching releases...");

        let releases = fetch_releases(&agent, &config.repo, &token);
        println!(
            "[{project_name}] Found {} release(s)",
            releases.len()
        );

        let resolved = filter_releases(releases, project_name, config);
        if resolved.is_empty() {
            println!("[{project_name}] No matching compliance report assets found.");
            continue;
        }

        println!(
            "[{project_name}] {} version(s) with matching assets",
            resolved.len()
        );

        let (subdir, entry) = kind_layout(&config.kind);
        let project_dir = reports_dir.join(project_name);
        let mut successful_versions: Vec<Version> = Vec::new();

        for rv in &resolved {
            let version_str = rv.version.to_string();
            let version_dir = project_dir.join(&version_str);
            let entry_html = version_dir.join(subdir).join(entry);

            if entry_html.exists() {
                println!("[{project_name}] v{version_str}: cached, skipping");
                successful_versions.push(rv.version.clone());
                continue;
            }

            println!("[{project_name}] v{version_str}: downloading...");
            match download_and_extract(&agent, &token, &rv.download_url, &version_dir, subdir) {
                Ok(()) => {
                    println!("[{project_name}] v{version_str}: extracted");
                    successful_versions.push(rv.version.clone());
                }
                Err(e) => {
                    eprintln!("[{project_name}] v{version_str}: failed — {e}");
                    // Clean up partial extraction.
                    let _ = remove_dir_if_exists(&version_dir);
                }
            }
        }

        if successful_versions.is_empty() {
            continue;
        }

        // Versions are already sorted descending from filter_releases.
        let version_refs: Vec<&Version> = successful_versions.iter().collect();
        let is_compliance = config.kind == "compliance";

        // config.js (the rivet HTML report's version switcher) is compliance-
        // specific; the witness MC/DC bundle ships its own self-contained viewer.
        if is_compliance {
            for v in &successful_versions {
                let version_dir = project_dir.join(v.to_string());
                if let Err(e) = write_config_js(project_name, &version_refs, &version_dir) {
                    eprintln!(
                        "[{project_name}] Warning: failed to write config.js for v{v}: {e}"
                    );
                }
            }
        }

        // Copy latest version to {project}/latest/.
        let latest_version = &successful_versions[0]; // highest semver (sorted desc)
        let latest_src = project_dir.join(latest_version.to_string()).join(subdir);
        let latest_dst = project_dir.join("latest").join(subdir);

        // Remove existing latest directory.
        let _ = remove_dir_if_exists(&project_dir.join("latest"));

        if latest_src.exists() {
            if let Err(e) = copy_dir_recursive(&latest_src, &latest_dst) {
                eprintln!("[{project_name}] Warning: failed to copy latest: {e}");
            } else {
                if is_compliance {
                    // Also write config.js for the latest directory.
                    let latest_dir = project_dir.join("latest");
                    if let Err(e) = write_config_js(project_name, &version_refs, &latest_dir) {
                        eprintln!(
                            "[{project_name}] Warning: failed to write config.js for latest: {e}"
                        );
                    }
                }
                println!("[{project_name}] latest -> v{latest_version}");
            }
        }

        // Regenerate data/{project}/ summary files from the latest compliance
        // bundle's generic-yaml export, if present (rivet emits it when its
        // compliance action runs with `include-data-formats: true`). Only the
        // compliance kind carries artifacts.yaml; the MC/DC bundle does not.
        if is_compliance {
            let artifacts_yaml = latest_src.join("artifacts.yaml");
            if artifacts_yaml.exists() {
                match generate_data_files(project_name, &artifacts_yaml, &root) {
                    Ok(n) => println!(
                        "[{project_name}] data/: wrote stats.json + artifacts.json ({n} artifacts)"
                    ),
                    Err(e) => {
                        eprintln!("[{project_name}] Warning: failed to generate data/: {e}")
                    }
                }
            } else {
                println!(
                    "[{project_name}] no artifacts.yaml in bundle \
                     (set `include-data-formats: true` on the compliance action to \
                     auto-generate data/); leaving data/{project_name}/ as-is"
                );
            }
        }

        // Compute display versions: latest patch per minor version.
        // Versions are already sorted descending, so first seen per (major, minor) wins.
        let display_versions = {
            let mut seen: Vec<(u64, u64)> = Vec::new();
            let mut display: Vec<String> = Vec::new();
            for v in &successful_versions {
                let key = (v.major, v.minor);
                if !seen.contains(&key) {
                    seen.push(key);
                    display.push(v.to_string());
                }
            }
            display
        };

        // Record in index.
        index.projects.insert(
            project_name.clone(),
            ProjectIndex {
                kind: config.kind.clone(),
                latest: latest_version.to_string(),
                versions: successful_versions.iter().map(|v| v.to_string()).collect(),
                display_versions,
            },
        );
    }

    // Write index.json.
    let index_path = reports_dir.join("index.json");
    let index_json =
        serde_json::to_string_pretty(&index).expect("failed to serialize index.json");
    fs::write(&index_path, index_json + "\n").expect("failed to write index.json");
    println!("Wrote {}", index_path.display());
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn generate_data_files_aggregates_like_snapshot() {
        // Sample matching rivet's generic-yaml export shape, exercising:
        // a present status, a duplicate type, and a missing status (-> "unset").
        let yaml = r#"
artifacts:
  - id: FEAT-001
    type: feature
    title: First feature
    description: A feature.
    status: approved
    tags: [phase-1]
    links:
      - target: REQ-001
        type: satisfies
  - id: FEAT-002
    type: feature
    title: Second feature
    status: draft
  - id: UCA-1
    type: uca
    title: An unsafe control action
"#;
        // Dedicated temp dir for this test (cleaned at the start of each run).
        let root = std::env::temp_dir().join("fetch-reports-gen-data-test");
        let _ = fs::remove_dir_all(&root);
        let bundle = root.join("bundle");
        fs::create_dir_all(&bundle).unwrap();
        let yaml_path = bundle.join("artifacts.yaml");
        fs::write(&yaml_path, yaml).unwrap();

        let total = generate_data_files("rivet", &yaml_path, &root).unwrap();
        assert_eq!(total, 3);

        let stats: serde_json::Value =
            serde_json::from_str(&fs::read_to_string(root.join("data/rivet/stats.json")).unwrap())
                .unwrap();
        assert_eq!(stats["total"], 3);
        assert_eq!(stats["by_type"]["feature"], 2);
        assert_eq!(stats["by_type"]["uca"], 1);
        assert_eq!(stats["by_status"]["approved"], 1);
        assert_eq!(stats["by_status"]["draft"], 1);
        assert_eq!(stats["by_status"]["unset"], 1); // missing status bucketed

        let arts: serde_json::Value = serde_json::from_str(
            &fs::read_to_string(root.join("data/rivet/artifacts.json")).unwrap(),
        )
        .unwrap();
        assert_eq!(arts["artifacts"].as_array().unwrap().len(), 3);
        // Field projection: renamed `type`, "unset" status, links round-trip.
        assert_eq!(arts["artifacts"][2]["type"], "uca");
        assert_eq!(arts["artifacts"][2]["status"], "unset");
        assert_eq!(arts["artifacts"][0]["links"][0]["type"], "satisfies");
    }
}
