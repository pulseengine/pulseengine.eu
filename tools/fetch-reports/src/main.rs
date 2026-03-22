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
}

// ── Resolved version ────────────────────────────────────────────────────

#[derive(Debug)]
struct ResolvedVersion {
    version: Version,
    _tag: String,
    download_url: String,
}

// ── index.json types ────────────────────────────────────────────────────

#[derive(Debug, Serialize)]
struct IndexJson {
    projects: HashMap<String, ProjectIndex>,
}

#[derive(Debug, Serialize)]
struct ProjectIndex {
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

    // Extract into compliance/ subdirectory (rivet tarballs have flat files).
    let compliance_dir = dest_dir.join("compliance");
    fs::create_dir_all(&compliance_dir)
        .map_err(|e| format!("failed to create compliance dir: {e}"))?;
    let file = fs::File::open(&tmp_path)
        .map_err(|e| format!("failed to open tarball for extraction: {e}"))?;
    let decoder = GzDecoder::new(file);
    let mut archive = Archive::new(decoder);
    archive
        .unpack(&compliance_dir)
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

        let project_dir = reports_dir.join(project_name);
        let mut successful_versions: Vec<Version> = Vec::new();

        for rv in &resolved {
            let version_str = rv.version.to_string();
            let version_dir = project_dir.join(&version_str);
            let index_html = version_dir.join("compliance").join("index.html");

            if index_html.exists() {
                println!("[{project_name}] v{version_str}: cached, skipping");
                successful_versions.push(rv.version.clone());
                continue;
            }

            println!("[{project_name}] v{version_str}: downloading...");
            match download_and_extract(&agent, &token, &rv.download_url, &version_dir) {
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

        // Write config.js for each version directory.
        for v in &successful_versions {
            let version_dir = project_dir.join(v.to_string());
            if let Err(e) = write_config_js(project_name, &version_refs, &version_dir) {
                eprintln!(
                    "[{project_name}] Warning: failed to write config.js for v{v}: {e}"
                );
            }
        }

        // Copy latest version to {project}/latest/.
        let latest_version = &successful_versions[0]; // highest semver (sorted desc)
        let latest_src = project_dir
            .join(latest_version.to_string())
            .join("compliance");
        let latest_dst = project_dir.join("latest").join("compliance");

        // Remove existing latest directory.
        let _ = remove_dir_if_exists(&project_dir.join("latest"));

        if latest_src.exists() {
            if let Err(e) = copy_dir_recursive(&latest_src, &latest_dst) {
                eprintln!("[{project_name}] Warning: failed to copy latest: {e}");
            } else {
                // Also write config.js for the latest directory.
                let latest_dir = project_dir.join("latest");
                if let Err(e) = write_config_js(project_name, &version_refs, &latest_dir) {
                    eprintln!(
                        "[{project_name}] Warning: failed to write config.js for latest: {e}"
                    );
                }
                println!("[{project_name}] latest -> v{latest_version}");
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
