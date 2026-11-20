//! The outer chain: the input's sha256 is listed in the release's SHA256SUMS,
//! and SHA256SUMS is cosign-signed by a workflow of the same repository at the
//! release's own tag (keyless, GitHub OIDC). Both must hold or the input is
//! not counted.

use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};
use std::process::Command;

pub const OIDC_ISSUER: &str = "https://token.actions.githubusercontent.com";

/// The sums file names producers use today (jess and kiln: SHA256SUMS.txt,
/// relay: SHA256SUMS), in the order they are tried.
pub const SUMS_NAMES: [&str; 2] = ["SHA256SUMS.txt", "SHA256SUMS"];

pub fn sha256_hex(bytes: &[u8]) -> String {
    let d = Sha256::digest(bytes);
    d.iter().map(|b| format!("{b:02x}")).collect()
}

/// The sha256 SHA256SUMS lists for `name` (`<hex>  name`, `<hex> *name`,
/// `./name` all accepted). `Err` when the name is listed twice.
pub fn sums_lookup(sums: &str, name: &str) -> Result<Option<String>, String> {
    let mut found = None;
    for line in sums.lines() {
        let mut parts = line.split_whitespace();
        let (Some(hex), Some(file), None) = (parts.next(), parts.next(), parts.next()) else { continue };
        let file = file.trim_start_matches('*');
        let file = file.strip_prefix("./").unwrap_or(file);
        if file == name {
            if found.is_some() {
                return Err(format!("SHA256SUMS lists {name} more than once"));
            }
            found = Some(hex.to_ascii_lowercase());
        }
    }
    Ok(found)
}

fn regex_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len() * 2);
    for c in s.chars() {
        if "\\.^$|?*+()[]{}".contains(c) {
            out.push('\\');
        }
        out.push(c);
    }
    out
}

/// `^https://github\.com/pulseengine/<repo>/\.github/workflows/[^/@]+@refs/tags/<tag>$`:
/// any workflow file of that repository, run on exactly that tag. A branch run,
/// another tag or another repository does not match.
pub fn identity_regexp(org: &str, repo: &str, tag: &str) -> String {
    format!(
        "^https://github\\.com/{}/{}/\\.github/workflows/[^/@]+@refs/tags/{}$",
        regex_escape(org),
        regex_escape(repo),
        regex_escape(tag)
    )
}

/// How SHA256SUMS is signed: a sigstore bundle, or a detached signature plus
/// its Fulcio certificate.
#[derive(Debug, Clone)]
pub enum Signature {
    Bundle(PathBuf),
    SigCert(PathBuf, PathBuf),
}

/// Find `cosign`: `$COSIGN` if set (it must exist), else the PATH.
pub fn find_cosign() -> Option<PathBuf> {
    if let Ok(p) = std::env::var("COSIGN") {
        let p = PathBuf::from(p);
        return p.is_file().then_some(p);
    }
    let path = std::env::var_os("PATH")?;
    std::env::split_paths(&path).map(|d| d.join("cosign")).find(|p| p.is_file())
}

/// Run `cosign verify-blob`. `Err` carries cosign's last line.
pub fn cosign_verify(cosign: &Path, sums: &Path, sig: &Signature, identity_re: &str) -> Result<(), String> {
    let mut cmd = Command::new(cosign);
    cmd.arg("verify-blob");
    match sig {
        Signature::Bundle(b) => {
            cmd.arg("--bundle").arg(b);
        }
        Signature::SigCert(s, c) => {
            cmd.arg("--signature").arg(s).arg("--certificate").arg(c);
        }
    }
    cmd.args(["--certificate-identity-regexp", identity_re, "--certificate-oidc-issuer", OIDC_ISSUER]).arg(sums);
    let out = cmd.output().map_err(|e| format!("could not run {}: {e}", cosign.display()))?;
    if out.status.success() {
        return Ok(());
    }
    let text = format!("{}{}", String::from_utf8_lossy(&out.stdout), String::from_utf8_lossy(&out.stderr));
    let last = text.lines().rev().find(|l| !l.trim().is_empty()).unwrap_or("").trim().to_string();
    Err(format!("cosign verify-blob failed (exit {:?}): {last}", out.status.code()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sums_lines() {
        let s = "aa  ./a.json\nBB *b.json\ncc  c.json\n\njunk\n";
        assert_eq!(sums_lookup(s, "a.json").unwrap().as_deref(), Some("aa"));
        assert_eq!(sums_lookup(s, "b.json").unwrap().as_deref(), Some("bb"));
        assert_eq!(sums_lookup(s, "c.json").unwrap().as_deref(), Some("cc"));
        assert_eq!(sums_lookup(s, "d.json").unwrap(), None);
        assert!(sums_lookup("aa  x\nbb  ./x\n", "x").is_err());
    }

    #[test]
    fn identity() {
        assert_eq!(
            identity_regexp("pulseengine", "jess", "v0.7.3"),
            "^https://github\\.com/pulseengine/jess/\\.github/workflows/[^/@]+@refs/tags/v0\\.7\\.3$"
        );
    }
}
