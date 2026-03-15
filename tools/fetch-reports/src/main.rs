use serde::Deserialize;
use std::collections::HashMap;
use std::path::PathBuf;

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

fn main() {
    let manifest_path = repo_root().join("reports.toml");
    let content = std::fs::read_to_string(&manifest_path)
        .unwrap_or_else(|e| panic!("failed to read {}: {e}", manifest_path.display()));

    let manifest: Manifest =
        toml::from_str(&content).expect("failed to parse reports.toml");

    for name in manifest.projects.keys() {
        println!("{name}");
    }
}
