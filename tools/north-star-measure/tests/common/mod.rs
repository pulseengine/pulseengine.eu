//! Offline fixtures: a repository root with data/north-star.toml and a
//! `--offline` directory of releases, signed by tests/cosign-stub.sh's rules.
#![allow(dead_code)]

use north_star_measure::verify::sha256_hex;
use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};

static N: AtomicUsize = AtomicUsize::new(0);

pub fn stub_cosign() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests").join("cosign-stub.sh")
}

/// How a planted release signs (or fails to sign) its input.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Sign {
    /// SHA256SUMS lists the input; bundle by release.yml at the release tag.
    Good,
    /// The same, as .sig + .pem instead of a bundle.
    GoodSigCert,
    /// SHA256SUMS present, no signature at all.
    Unsigned,
    /// Signed by a branch run, not the tag.
    BranchRef,
    /// Signed at another tag of the same repository.
    OtherTag,
    /// Signed by another repository's release workflow.
    OtherRepo,
    /// The input was changed after SHA256SUMS was signed.
    Tampered,
    /// SHA256SUMS does not list the input.
    NotListed,
    /// No input asset attached.
    NoAsset,
    /// No SHA256SUMS at all.
    NoSums,
}

pub struct Fx {
    pub root: PathBuf,
    pub fixtures: PathBuf,
}

impl Drop for Fx {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.root);
    }
}

impl Fx {
    /// `products`: (name, pulls). `measured`: objective ids whose state is "measured".
    pub fn new(products: &[(&str, &[&str])], measured: &[&str]) -> Fx {
        let root = std::env::temp_dir().join(format!(
            "ns-measure-test-{}-{}",
            std::process::id(),
            N.fetch_add(1, Ordering::SeqCst)
        ));
        let _ = std::fs::remove_dir_all(&root);
        let fixtures = root.join("fixtures");
        std::fs::create_dir_all(root.join("data").join("north-star")).unwrap();
        std::fs::create_dir_all(&fixtures).unwrap();
        let mut t = String::from("north_star = \"test\"\n");
        for (name, pulls) in products {
            let p: Vec<String> = pulls.iter().map(|x| format!("{x:?}")).collect();
            t.push_str(&format!("\n[[products]]\nname = {name:?}\nnorth_star = \"x\"\npulls = [{}]\n", p.join(", ")));
        }
        for id in ["O1", "O2", "O3", "O4", "O5"] {
            let state = if measured.contains(&id) { "measured" } else { "unmeasured" };
            t.push_str(&format!("\n[[objectives]]\nid = {id:?}\nstate = {state:?}\n"));
        }
        std::fs::write(root.join("data").join("north-star.toml"), t).unwrap();
        Fx { root, fixtures }
    }

    /// Plant `product`'s latest release `tag` carrying `input` as
    /// `asset_name`, signed as `sign` says.
    pub fn publish_as(&self, product: &str, tag: &str, asset_name: &str, input: &Value, sign: Sign) {
        let dir = self.fixtures.join(product);
        let assets = dir.join("assets");
        std::fs::create_dir_all(&assets).unwrap();
        let mut names: Vec<String> = vec![format!("{product}-{tag}.tar.gz")];
        std::fs::write(assets.join(&names[0]), b"a binary").unwrap();
        let input_bytes = serde_json::to_vec_pretty(input).unwrap();
        let mut sums = format!("{}  ./{}\n", sha256_hex(b"a binary"), names[0]);
        if sign != Sign::NotListed {
            let listed = if sign == Sign::Tampered { b"the signed version".to_vec() } else { input_bytes.clone() };
            sums.push_str(&format!("{}  ./{asset_name}\n", sha256_hex(&listed)));
        }
        if sign != Sign::NoAsset {
            std::fs::write(assets.join(asset_name), &input_bytes).unwrap();
            names.push(asset_name.into());
        }
        if sign != Sign::NoSums {
            std::fs::write(assets.join("SHA256SUMS.txt"), &sums).unwrap();
            names.push("SHA256SUMS.txt".into());
        }
        let identity = match sign {
            Sign::BranchRef => format!("https://github.com/pulseengine/{product}/.github/workflows/release.yml@refs/heads/main"),
            Sign::OtherTag => format!("https://github.com/pulseengine/{product}/.github/workflows/release.yml@refs/tags/v9.9.9"),
            Sign::OtherRepo => format!("https://github.com/pulseengine/not-{product}/.github/workflows/release.yml@refs/tags/{tag}"),
            _ => format!("https://github.com/pulseengine/{product}/.github/workflows/release.yml@refs/tags/{tag}"),
        };
        let sig = format!("{identity}\n{}\n", sha256_hex(sums.as_bytes()));
        match sign {
            Sign::Unsigned | Sign::NoSums => {}
            Sign::GoodSigCert => {
                std::fs::write(assets.join("SHA256SUMS.txt.sig"), &sig).unwrap();
                std::fs::write(assets.join("SHA256SUMS.txt.pem"), b"cert").unwrap();
                names.push("SHA256SUMS.txt.sig".into());
                names.push("SHA256SUMS.txt.pem".into());
            }
            _ => {
                std::fs::write(assets.join("SHA256SUMS.txt.cosign.bundle"), &sig).unwrap();
                names.push("SHA256SUMS.txt.cosign.bundle".into());
            }
        }
        let rel = json!({"tag_name": tag, "assets": names.iter().map(|n| json!({"name": n})).collect::<Vec<_>>()});
        std::fs::write(dir.join("release.json"), serde_json::to_vec_pretty(&rel).unwrap()).unwrap();
    }

    pub fn publish(&self, product: &str, tag: &str, input: &Value, sign: Sign) {
        let o = input["objective"].as_str().unwrap_or("O1");
        self.publish_as(product, tag, &format!("north-star-input.{o}.json"), input, sign);
    }
}

pub fn fact(id: &str, ran: bool, pass: bool, control: Option<bool>, detail: Value) -> Value {
    let mut f = json!({"id": id, "ran": ran, "pass": pass});
    if let Some(c) = control {
        f["control_failed_as_expected"] = json!(c);
    }
    if !detail.is_null() {
        f["detail"] = detail;
    }
    f
}

pub fn input(objective: &str, product: &str, facts: Vec<Value>) -> Value {
    json!({
        "schema_version": 1,
        "objective": objective,
        "repo": format!("pulseengine/{product}"),
        "version": "0.8.0",
        "generated_at": "2026-11-20T06:00:00Z",
        "generator": {"tool": "fixture", "version": "1"},
        "facts": facts,
        "not_measured": ["fixture blind spot"]
    })
}
