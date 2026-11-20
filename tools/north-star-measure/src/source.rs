//! Where releases come from: the GitHub REST API over curl, or a fixture
//! directory (`--offline DIR`) laid out as
//!
//! ```text
//! DIR/<product>/release.json          the /releases/latest response (tag_name, assets[].name)
//! DIR/<product>/assets/<asset name>   the asset's bytes
//! ```
//!
//! A product without `release.json` has no release. Both sources answer the
//! same three ways: a release, no release (the product is not counted), or an
//! error (nothing is measured: a measurement that cannot reach its evidence
//! has measured nothing).

use serde_json::Value;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

pub const ORG: &str = "pulseengine";

#[derive(Debug, Clone)]
pub struct Release {
    pub tag: String,
    /// (name, download URL); the URL is empty for fixtures.
    pub assets: Vec<(String, String)>,
}

impl Release {
    pub fn has(&self, name: &str) -> bool {
        self.assets.iter().any(|(n, _)| n == name)
    }
}

#[derive(Debug, Clone)]
pub enum Source {
    Live,
    Offline(PathBuf),
}

fn token() -> Option<String> {
    ["GITHUB_TOKEN", "GH_TOKEN"].iter().find_map(|k| std::env::var(k).ok().filter(|v| !v.trim().is_empty()))
}

fn parse_release(v: &Value) -> Result<Release, String> {
    let tag = v.get("tag_name").and_then(Value::as_str).ok_or("release has no tag_name")?.to_string();
    let mut assets = Vec::new();
    for a in v.get("assets").and_then(Value::as_array).cloned().unwrap_or_default() {
        let name = a.get("name").and_then(Value::as_str).ok_or("asset without a name")?.to_string();
        let url = a.get("browser_download_url").and_then(Value::as_str).unwrap_or("").to_string();
        assets.push((name, url));
    }
    Ok(Release { tag, assets })
}

impl Source {
    /// `Ok(None)`: the product has no release.
    pub fn latest_release(&self, product: &str) -> Result<Option<Release>, String> {
        match self {
            Source::Offline(dir) => {
                let p = dir.join(product).join("release.json");
                if !p.exists() {
                    return Ok(None);
                }
                let text = std::fs::read_to_string(&p).map_err(|e| format!("read {}: {e}", p.display()))?;
                let v: Value = serde_json::from_str(&text).map_err(|e| format!("{}: {e}", p.display()))?;
                parse_release(&v).map(Some)
            }
            Source::Live => {
                let url = format!("https://api.github.com/repos/{ORG}/{product}/releases/latest");
                let (code, body) = curl_api(&url)?;
                match code {
                    200 => {
                        let v: Value = serde_json::from_slice(&body).map_err(|e| format!("{url}: {e}"))?;
                        parse_release(&v).map(Some)
                    }
                    404 => Ok(None),
                    c => Err(format!("{url}: HTTP {c}")),
                }
            }
        }
    }

    /// Download one asset of `release` to `dest`.
    pub fn fetch(&self, product: &str, release: &Release, name: &str, dest: &Path) -> Result<(), String> {
        match self {
            Source::Offline(dir) => {
                let p = dir.join(product).join("assets").join(name);
                std::fs::copy(&p, dest).map(|_| ()).map_err(|e| format!("fixture asset {}: {e}", p.display()))
            }
            Source::Live => {
                let url = release.assets.iter().find(|(n, _)| n == name).map(|(_, u)| u.as_str()).unwrap_or("");
                // Only this product's own release downloads, never a URL a
                // release body could point anywhere.
                let want = format!("https://github.com/{ORG}/{product}/releases/download/");
                if !url.starts_with(&want) {
                    return Err(format!("{product} {}: asset {name} has an unexpected download URL {url:?}", release.tag));
                }
                let st = Command::new("curl")
                    .args(["-fsSL", "--retry", "3", "--max-time", "300", "-A", "north-star-measure", "-o"])
                    .arg(dest)
                    .arg(url)
                    .status()
                    .map_err(|e| format!("curl: {e}"))?;
                if st.success() {
                    Ok(())
                } else {
                    Err(format!("download {url}: curl exit {:?}", st.code()))
                }
            }
        }
    }
}

/// GET a GitHub API URL; the token goes through curl's stdin config, never argv.
fn curl_api(url: &str) -> Result<(u16, Vec<u8>), String> {
    let mut cmd = Command::new("curl");
    cmd.args([
        "-sSL",
        "--retry",
        "3",
        "--max-time",
        "60",
        "-H",
        "Accept: application/vnd.github+json",
        "-A",
        "north-star-measure",
        "-w",
        "\n%{http_code}",
        "--config",
        "-",
        url,
    ])
    .stdin(Stdio::piped())
    .stdout(Stdio::piped())
    .stderr(Stdio::piped());
    let mut child = cmd.spawn().map_err(|e| format!("curl: {e}"))?;
    {
        let mut stdin = child.stdin.take().ok_or("curl: no stdin")?;
        if let Some(t) = token() {
            let _ = writeln!(stdin, "header = \"Authorization: Bearer {}\"", t.trim());
        }
    }
    let out = child.wait_with_output().map_err(|e| format!("curl: {e}"))?;
    if !out.status.success() {
        return Err(format!("{url}: curl exit {:?}: {}", out.status.code(), String::from_utf8_lossy(&out.stderr).trim()));
    }
    let body = out.stdout;
    let cut = body.iter().rposition(|b| *b == b'\n').ok_or_else(|| format!("{url}: no HTTP status from curl"))?;
    let code: u16 = std::str::from_utf8(&body[cut + 1..])
        .ok()
        .and_then(|s| s.trim().parse().ok())
        .ok_or_else(|| format!("{url}: unreadable HTTP status"))?;
    Ok((code, body[..cut].to_vec()))
}
