//! Classification: which classes a change set selects. Fails open: any doubt
//! selects every class.

use crate::config::Config;
use crate::graph::{self, Graph};
use crate::repo::{basename, Repo};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone)]
pub struct Verdict {
    pub run_all: bool,
    pub reason: Option<String>,
    pub classes: BTreeMap<String, bool>,
    pub unknown_paths: Vec<String>,
    pub inputs_hash: Option<String>,
    /// Human-readable notes (unresolved classes); stderr only.
    pub notes: Vec<String>,
    /// Emit a GitHub `::warning::` (internal failures).
    pub warn: bool,
    /// class -> unresolved inputs as {code, input} (REQ-021); always in the JSON.
    pub unresolved: BTreeMap<String, Vec<serde_json::Value>>,
    /// class -> why it was selected: {path, claim, via} per changed path, or
    /// {unresolved} (REQ-020; printed with --explain).
    pub explain: BTreeMap<String, Vec<serde_json::Value>>,
}

impl Verdict {
    pub fn all(cfg: &Config, reason: impl Into<String>) -> Self {
        let reason = reason.into();
        Verdict {
            run_all: true,
            warn: reason.starts_with("internal:"),
            reason: Some(reason),
            classes: cfg.classes.iter().map(|c| (c.name.clone(), true)).collect(),
            unknown_paths: vec![],
            inputs_hash: None,
            notes: vec![],
            unresolved: BTreeMap::new(),
            explain: BTreeMap::new(),
        }
    }
}

pub fn is_run_all(cfg: &Config, p: &str) -> bool {
    let base = basename(p);
    cfg.run_all_prefixes
        .iter()
        .any(|x| p.starts_with(x.as_str()))
        || cfg.run_all_files.iter().any(|x| x == p)
        || cfg.run_all_basenames.iter().any(|x| x == base)
        || cfg.run_all_suffixes.iter().any(|x| p.ends_with(x.as_str()))
        || p.split('/')
            .rev()
            .skip(1)
            .any(|c| cfg.run_all_dirs.iter().any(|d| d == c))
}

pub fn is_inert(cfg: &Config, p: &str) -> bool {
    cfg.inert_prefixes.iter().any(|x| p.starts_with(x.as_str()))
        || cfg.inert_files.iter().any(|x| x == p)
}

fn docs_candidate(p: &str) -> bool {
    let b = basename(p);
    p.ends_with(".md") || b == "LICENSE" || b.starts_with("LICENSE-")
}

/// Which docs basenames some tracked non-markdown file names. One pass over
/// the tree for all candidates (the reference's per-file `git grep` took 50 s
/// for 1,200 .md files). A file that cannot be read counts as naming them all.
pub fn docs_named(
    repo: &Repo,
    cfg: &Config,
    candidates: &BTreeSet<String>,
) -> Result<BTreeSet<String>, String> {
    let mut named = BTreeSet::new();
    if candidates.is_empty() {
        return Ok(named);
    }
    let pats: Vec<&String> = candidates.iter().collect();
    let ac = aho_corasick::AhoCorasick::new(&pats).map_err(|e| format!("docs index: {e}"))?;
    for f in repo.tracked()? {
        if f.ends_with(".md") || f == cfg.path || cfg.docs_namer_exclude.contains(&f) {
            continue;
        }
        match std::fs::read(repo.path(&f)) {
            Ok(bytes) => {
                for m in ac.find_overlapping_iter(&bytes) {
                    named.insert(pats[m.pattern().as_usize()].clone());
                }
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {} // tracked but deleted in the worktree
            Err(_) => return Ok(candidates.clone()),
        }
        if named.len() == candidates.len() {
            break;
        }
    }
    Ok(named)
}

pub fn inputs_hash(cfg: &Config, g: &Graph) -> String {
    use sha2::{Digest, Sha256};
    let mut h = Sha256::new();
    h.update(cfg.digest.as_bytes());
    for (c, cg) in g {
        h.update(b"\0class\0");
        h.update(c.as_bytes());
        for (claim, src) in &cg.claims {
            h.update(b"\0");
            h.update(claim.as_bytes());
            h.update(b"=");
            h.update(src.as_bytes());
        }
        for u in &cg.unresolved {
            h.update(b"\0unresolved\0");
            h.update(u.to_string().as_bytes());
        }
    }
    format!("{:x}", h.finalize())
}

/// Classify an explicit change set against a derived graph.
pub fn classify(
    repo: &Repo,
    cfg: &Config,
    changed: &[String],
    g: &Graph,
) -> Result<Verdict, String> {
    let changed: Vec<String> = changed
        .iter()
        .map(|c| c.trim().to_string())
        .filter(|c| !c.is_empty())
        .collect();
    if changed.is_empty() {
        return Ok(Verdict::all(cfg, "no changed paths"));
    }
    let mut v = Verdict {
        run_all: false,
        reason: None,
        classes: cfg
            .classes
            .iter()
            .map(|c| (c.name.clone(), false))
            .collect(),
        unknown_paths: vec![],
        inputs_hash: Some(inputs_hash(cfg, g)),
        notes: vec![],
        warn: false,
        unresolved: BTreeMap::new(),
        explain: BTreeMap::new(),
    };
    for (c, cg) in g {
        if !cg.unresolved.is_empty() {
            v.unresolved
                .insert(c.clone(), cg.unresolved.iter().map(|u| u.json()).collect());
            v.explain.entry(c.clone()).or_default().extend(
                cg.unresolved
                    .iter()
                    .map(|u| serde_json::json!({"unresolved": u.json()})),
            );
        }
        if let Some(u) = cg.unresolved.first() {
            v.classes.insert(c.clone(), true);
            v.notes
                .push(format!("{c}: unresolved input ({u}); always runs"));
        }
    }
    let candidates: BTreeSet<String> = changed
        .iter()
        .filter(|p| docs_candidate(p))
        .map(|p| basename(p).to_string())
        .collect();
    let named = docs_named(repo, cfg, &candidates)?;
    let mut run_all: Option<String> = None;
    for p in &changed {
        // A control character could forge a workflow command in the log.
        let malformed = p.starts_with('/')
            || p.chars().any(char::is_control)
            || p.split('/').any(|c| c == ".." || c == "." || c.is_empty());
        if malformed {
            v.unknown_paths.push(p.clone());
            run_all.get_or_insert_with(|| {
                format!("run-all path: {p} is not a repository-relative path")
            });
            continue;
        }
        if is_run_all(cfg, p) {
            run_all.get_or_insert_with(|| {
                format!("run-all path: {p} is CI, toolchain, build-system or sieve config")
            });
            continue;
        }
        let hits: Vec<&String> = g
            .iter()
            .filter(|(_, cg)| cg.claims_path(p))
            .map(|(c, _)| c)
            .collect();
        // Docs only if no class claims it: a .md inside a claimed directory can
        // be read through include_dir!, a directory walk or a built name.
        if hits.is_empty() && docs_candidate(p) && !named.contains(basename(p)) {
            continue; // docs only
        }
        for c in &hits {
            if let Some((claim, via)) = g[*c].claim_of(p) {
                v.explain
                    .entry((*c).clone())
                    .or_default()
                    .push(serde_json::json!({"path": p, "claim": claim, "via": via}));
            }
            v.classes.insert((*c).clone(), true);
        }
        if is_inert(cfg, p) {
            if !hits.is_empty() {
                run_all.get_or_insert_with(|| {
                    format!("run-all path: {p} is inert AND an input of {hits:?}")
                });
            }
            continue;
        }
        if hits.is_empty() {
            v.unknown_paths.push(p.clone());
            run_all.get_or_insert_with(|| format!("run-all path: {p} is claimed by no class"));
        }
    }
    if let Some(r) = run_all {
        let unknown = std::mem::take(&mut v.unknown_paths);
        let notes = std::mem::take(&mut v.notes);
        let hash = v.inputs_hash.take();
        let unresolved = std::mem::take(&mut v.unresolved);
        let explain = std::mem::take(&mut v.explain);
        v = Verdict::all(cfg, r);
        v.unknown_paths = unknown;
        v.notes = notes;
        v.inputs_hash = hash;
        v.unresolved = unresolved;
        v.explain = explain;
    }
    Ok(v)
}

/// Derive the graph, then classify; a graph that cannot be derived selects all.
pub fn classify_paths(repo: &Repo, cfg: &Config, changed: &[String]) -> Verdict {
    if changed.iter().all(|c| c.trim().is_empty()) {
        return Verdict::all(cfg, "no changed paths");
    }
    match graph::derive(repo, cfg) {
        Ok(g) => classify(repo, cfg, changed, &g)
            .unwrap_or_else(|e| Verdict::all(cfg, format!("internal: {e}"))),
        Err(e) => Verdict::all(
            cfg,
            format!(
                "internal: build graph unreadable: {}: {}",
                e.code, e.message
            ),
        ),
    }
}

/// git mode: classify `base...head` for a pull_request event; anything else
/// (another event, no base, a failed or empty diff) selects everything.
pub fn git_mode(
    root: &std::path::Path,
    cfg: &Config,
    event: Option<&str>,
    base: Option<&str>,
    head: Option<&str>,
) -> Verdict {
    let repo = Repo {
        root: root.to_path_buf(),
        git: true,
    };
    let ev = event.unwrap_or("");
    if ev != "pull_request" {
        return Verdict::all(
            cfg,
            format!(
                "event {} is not pull_request",
                if ev.is_empty() { "<none>" } else { ev }
            ),
        );
    }
    let base = base.unwrap_or("").trim();
    if base.is_empty() {
        return Verdict::all(cfg, "no base sha");
    }
    let head = head.unwrap_or("HEAD");
    // A rename is a delete plus an add, and both are classified (gix, in-process).
    match crate::gitrepo::diff_names(root, base, head) {
        Err(e) => Verdict::all(cfg, format!("git diff failed against {base}: {e}")),
        Ok(paths) => {
            if paths.is_empty() {
                Verdict::all(cfg, "empty diff")
            } else {
                classify_paths(&repo, cfg, &paths)
            }
        }
    }
}
