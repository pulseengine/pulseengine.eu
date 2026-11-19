//! `plant guard`: no fork pull request reaches a self-hosted runner.
//!
//! Ported from pulseengine/relay's scripts/check-selfhosted-fork-guard.rs
//! (relay#695, f852816), itself a port of pulseengine/ordeal#322. The decision
//! rules and their 19 tests are relay's; plant adds the per-repo config
//! (`plant-guard.toml`): the hosted fallback image, the provisioned runner
//! labels, and exemptions for workflows a fork cannot trigger.
//!
//! Every line in .github/workflows/*.yml that names `self-hosted` must be one of:
//!
//!   1. a `runs-on:` in exactly the fail-closed same-repo form
//!      `${{ (github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository) && fromJSON('[..."self-hosted"...]') || '<fallback>' }}`
//!      so the self-hosted labels are chosen only for a non-PR event or a PR
//!      whose head repository is this one. A fork, or a deleted fork whose
//!      `head.repo` is null, falls to the hosted runner;
//!   2. a matrix `runner:` value inside a job whose `runs-on:` is exactly the
//!      matrix variant of that form, which also sends a self-hosted matrix leg
//!      to the hosted runner for a foreign head.
//!
//! Every `runs-on:` is allowlisted: a hosted image (ubuntu-*, macos-*,
//! windows-*), the fail-closed form, the matrix form, or a plain
//! `${{ matrix.<id> }}` whose every literal value is a hosted image. GitHub
//! matches labels, so `light` or `[linux, light]` reach the self-hosted pool
//! without the word self-hosted. A runner taken from needs.*.outputs, inputs,
//! vars or github.* is rejected, and so is a block-list or map runs-on.
//!
//! Any self-hosted job in a workflow with a trigger outside TRUSTED is
//! rejected: the form trusts every event that is not `pull_request`. A run
//! that finds no self-hosted selection fails: it compared nothing.
//!
//! Unlike relay's line-based original, each workflow is parsed as YAML
//! (yaml-rust2), so quoted keys, flow-style jobs, anchors and multi-line
//! trigger lists read as GitHub reads them. Review of the line parser found
//! 13 shapes that passed while routing a fork to self-hosted. The check
//! still fails closed: a file that does not parse, a merge key, a job with
//! neither runs-on nor a local `uses:`, a reusable workflow from another
//! repository, and a matrix that cannot be read statically are violations.

use std::collections::{BTreeMap, BTreeSet};
use std::fmt;
use std::fs;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use yaml_rust2::parser::{Event, EventReceiver, Parser};
use yaml_rust2::{Yaml, YamlLoader};

const GUARD: &str = "(github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository)";
const MATRIX_GUARD: &str = "(github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository || !contains(matrix.runner, 'self-hosted'))";
/// The hosted image a fork PR falls back to when the config names none.
pub const DEFAULT_FALLBACK: &str = "ubuntu-24.04";
/// `release` is plant's addition to relay's list: only a user with write
/// access can publish a release, so a fork cannot cause the event.
const TRUSTED: &[&str] = &[
    "push",
    "pull_request",
    "schedule",
    "workflow_dispatch",
    "merge_group",
    "release",
];
/// Triggers under which an exempt workflow may select self-hosted runners
/// without the fail-closed form: none of them can be caused by a fork.
const EXEMPTABLE: &[&str] = &["push", "schedule", "workflow_dispatch", "release"];
pub const CONFIG_FILE: &str = "plant-guard.toml";

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ConfigFile {
    fallback: Option<Fallback>,
    labels: Option<Vec<String>>,
    #[serde(default)]
    exempt: Vec<Exempt>,
}

/// `fallback = "ubuntu-24.04"` or `fallback = ["ubuntu-24.04", "ubuntu-latest"]`.
#[derive(Deserialize)]
#[serde(untagged)]
enum Fallback {
    One(String),
    Many(Vec<String>),
}

#[derive(Deserialize, Clone)]
#[serde(deny_unknown_fields)]
pub struct Exempt {
    pub workflow: String,
    pub reason: String,
}

pub struct Config {
    /// The first accepted fallback image (reported as `fallback`).
    pub fallback: String,
    /// Every hosted image the fail-closed forms may fall back to.
    pub fallbacks: Vec<String>,
    /// The provisioned runner labels; None when the config declares none.
    pub labels: Option<BTreeSet<String>>,
    pub exempt: Vec<Exempt>,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            fallback: DEFAULT_FALLBACK.into(),
            fallbacks: vec![DEFAULT_FALLBACK.into()],
            labels: None,
            exempt: vec![],
        }
    }
}

impl Config {
    pub fn parse(text: &str) -> Result<Config, String> {
        let f: ConfigFile = toml::from_str(text).map_err(|e| e.to_string())?;
        let fallbacks = match f.fallback {
            None => vec![DEFAULT_FALLBACK.to_string()],
            Some(Fallback::One(s)) => vec![s],
            Some(Fallback::Many(v)) => v,
        };
        if fallbacks.is_empty() {
            return Err("fallback is an empty list; omit it or name a hosted image".into());
        }
        for fb in &fallbacks {
            if !is_hosted(fb) || fb.contains('\'') {
                return Err(format!("fallback {fb:?} is not a GitHub-hosted image name"));
            }
        }
        let fallback = fallbacks[0].clone();
        let labels = match f.labels {
            None => None,
            Some(v) => {
                if v.is_empty() {
                    return Err("labels is empty; omit it or name the provisioned labels".into());
                }
                if let Some(bad) = v
                    .iter()
                    .find(|l| l.trim().is_empty() || l.trim() != l.as_str())
                {
                    return Err(format!(
                        "label {bad:?} is empty or has surrounding whitespace"
                    ));
                }
                Some(v.into_iter().collect())
            }
        };
        for e in &f.exempt {
            if e.workflow.is_empty() || e.workflow.contains('/') {
                return Err(format!(
                    "exempt workflow {:?} must be a file name in .github/workflows",
                    e.workflow
                ));
            }
            if e.reason.trim().is_empty() {
                return Err(format!("exempt workflow {:?} has no reason", e.workflow));
            }
        }
        Ok(Config {
            fallback,
            fallbacks,
            labels,
            exempt: f.exempt,
        })
    }

    /// True when `tail` ends the single-label form with an accepted fallback.
    fn is_form_tail(&self, tail: &str) -> bool {
        self.fallbacks
            .iter()
            .any(|fb| tail == format!("]') || '{fb}' }}}}"))
    }

    /// The matrix form with each accepted fallback.
    fn matrix_forms(&self) -> Vec<String> {
        self.fallbacks
            .iter()
            .map(|fb| format!("${{{{ {MATRIX_GUARD} && matrix.runner || '{fb}' }}}}"))
            .collect()
    }

    #[cfg(test)]
    fn matrix_form(&self) -> String {
        self.matrix_forms().remove(0)
    }
}

#[derive(Debug, PartialEq, Serialize)]
pub struct Violation {
    pub file: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub line: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub job: Option<String>,
    pub reason: String,
}

impl fmt::Display for Violation {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match (self.line, &self.job) {
            (Some(n), Some(j)) => write!(f, "{}:{n} ({j}): {}", self.file, self.reason),
            (Some(n), None) => write!(f, "{}:{n}: {}", self.file, self.reason),
            _ => write!(f, "{}: {}", self.file, self.reason),
        }
    }
}

#[derive(Debug, PartialEq)]
pub struct Report {
    pub seen: usize,
    pub bad: Vec<Violation>,
}

/// The labels of the fail-closed single-label form, or None when `v` is not
/// that form.
fn runs_on_form_labels(v: &str, cfg: &Config) -> Option<Vec<String>> {
    let rest = v
        .strip_prefix("${{ ")?
        .strip_prefix(GUARD)?
        .strip_prefix(" && fromJSON('[")?;
    let end = rest.find("]')")?;
    let labels = &rest[..end];
    if labels.contains('\'') || !cfg.is_form_tail(&rest[end..]) {
        return None;
    }
    let list: Vec<String> = serde_json::from_str(&format!("[{labels}]")).ok()?;
    list.iter().any(|l| l == "self-hosted").then_some(list)
}

/// The key of `${{ matrix.<ident> }}`, with any spaces or tabs inside the
/// braces (`${{matrix.os   }}` is the same reference), else None.
fn plain_matrix_key(v: &str) -> Option<&str> {
    v.strip_prefix("${{")
        .and_then(|r| r.strip_suffix("}}"))
        .map(|r| r.trim_matches([' ', '\t']))
        .and_then(|r| r.strip_prefix("matrix."))
        .filter(|id| {
            !id.is_empty()
                && id
                    .chars()
                    .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
        })
}

/// A GitHub-hosted image name: ubuntu-latest, ubuntu-24.04, ubuntu-24.04-arm,
/// ubuntu-slim, macos-latest, macos-15, macos-15-intel / -large / -xlarge,
/// windows-latest, windows-2022, windows-11-arm. A self-hosted label that
/// merely starts with ubuntu-, macos- or windows- is not one.
fn is_hosted(v: &str) -> bool {
    let parts: Vec<&str> = v.split('-').collect();
    let num = |s: &str, dotted: bool| {
        let mut it = s.split('.');
        let ok = |p: Option<&str>| {
            p.is_some_and(|p| !p.is_empty() && p.chars().all(|c| c.is_ascii_digit()))
        };
        match (it.next(), it.next(), it.next()) {
            (a, None, None) => !dotted && ok(a),
            (a, b, None) => dotted && ok(a) && ok(b),
            _ => false,
        }
    };
    match parts.as_slice() {
        ["ubuntu", "latest" | "slim"] | ["macos", "latest"] | ["windows", "latest"] => true,
        ["ubuntu", v] => num(v, true),
        ["ubuntu", v, "arm"] => num(v, true),
        ["macos", v] => num(v, false),
        ["macos", v, "intel" | "large" | "xlarge"] => num(v, false),
        ["windows", v] => num(v, false),
        ["windows", v, "arm"] => num(v, false),
        _ => false,
    }
}

/// A matrix value: a scalar or a list of scalars. Anything else is None.
#[derive(Debug)]
enum Val {
    One(String),
    List(Vec<String>),
}

fn scalar(y: &Yaml) -> Option<String> {
    match y {
        Yaml::String(s) | Yaml::Real(s) => Some(s.clone()),
        Yaml::Integer(i) => Some(i.to_string()),
        Yaml::Boolean(b) => Some(b.to_string()),
        _ => None,
    }
}

fn val(y: &Yaml) -> Option<Val> {
    match y {
        Yaml::Array(a) => a
            .iter()
            .map(scalar)
            .collect::<Option<Vec<_>>>()
            .map(Val::List),
        other => scalar(other).map(Val::One),
    }
}

/// The largest workflow plant guard reads, and the most it lets the document
/// expand to once aliases are resolved, in bytes (each node counts its scalar
/// length plus one). Larger inputs are violations: an alias bomb, of many
/// nodes or of one long scalar aliased many times, must not take the checker
/// down.
const MAX_BYTES: usize = 1 << 20;
const MAX_EXPANDED: u64 = 8 << 20;

/// Counts what a document expands to, without expanding aliases.
#[derive(Default)]
struct NodeBudget {
    frames: Vec<(usize, u64)>,
    anchors: BTreeMap<usize, u64>,
    total: u64,
}

impl NodeBudget {
    fn add(&mut self, n: u64) {
        match self.frames.last_mut() {
            Some(f) => f.1 = f.1.saturating_add(n),
            None => self.total = self.total.saturating_add(n),
        }
    }
}

impl EventReceiver for NodeBudget {
    fn on_event(&mut self, ev: Event) {
        match ev {
            Event::Scalar(v, _, anchor, _) => {
                let n = 1 + v.len() as u64;
                if anchor != 0 {
                    self.anchors.insert(anchor, n);
                }
                self.add(n);
            }
            Event::SequenceStart(anchor, _) | Event::MappingStart(anchor, _) => {
                self.frames.push((anchor, 1))
            }
            Event::SequenceEnd | Event::MappingEnd => {
                if let Some((anchor, n)) = self.frames.pop() {
                    if anchor != 0 {
                        self.anchors.insert(anchor, n);
                    }
                    self.add(n);
                }
            }
            Event::Alias(id) => {
                let n = self.anchors.get(&id).copied().unwrap_or(1);
                self.add(n);
            }
            _ => {}
        }
    }
}

/// The size the text expands to, or None when it does not parse.
fn expanded_nodes(text: &str) -> Option<u64> {
    let mut b = NodeBudget::default();
    Parser::new_from_str(text).load(&mut b, true).ok()?;
    Some(b.total)
}

/// True when a mapping anywhere in `y` has a `<<` merge key. yaml-rust2 does
/// not apply merge keys, so a merged value would be invisible here.
fn has_merge_key(y: &Yaml) -> bool {
    match y {
        Yaml::Hash(h) => h
            .iter()
            .any(|(k, v)| k.as_str() == Some("<<") || has_merge_key(v)),
        Yaml::Array(a) => a.iter().any(has_merge_key),
        _ => false,
    }
}

/// Keys that steer runner selection. GitHub may read workflow keys without
/// regard to case, so a key that differs from one of these only by case is a
/// violation rather than an unread key.
const KEYWORDS: &[&str] = &[
    "on", "jobs", "runs-on", "uses", "strategy", "matrix", "include", "exclude",
];

/// Keys of `h` that spell a KEYWORD in another case, or are not strings.
fn case_variants(h: &yaml_rust2::yaml::Hash) -> Vec<String> {
    h.keys()
        .filter_map(|k| match k.as_str() {
            Some(s) => KEYWORDS
                .iter()
                .any(|w| s != *w && s.eq_ignore_ascii_case(w))
                .then(|| s.to_string()),
            None => Some(format!("{k:?}")),
        })
        .collect()
}

fn key<'a>(h: &'a yaml_rust2::yaml::Hash, k: &str) -> Option<&'a Yaml> {
    h.get(&Yaml::String(k.to_string()))
}

/// Every value matrix key `k` can take in a job's `strategy.matrix`: the axis
/// itself and every `include` entry naming it. None when the matrix cannot be
/// read statically (an expression, a non-scalar value, an include entry that
/// is not a mapping), because then its legs are not knowable here.
fn matrix_values(job: &yaml_rust2::yaml::Hash, k: &str) -> Option<Vec<Val>> {
    let strategy = match key(job, "strategy") {
        Some(Yaml::Hash(h)) => h,
        _ => return None,
    };
    let matrix = match key(strategy, "matrix") {
        Some(Yaml::Hash(h)) => h,
        _ => return None,
    };
    if !case_variants(strategy).is_empty() || !case_variants(matrix).is_empty() {
        return None;
    }
    let mut out = Vec::new();
    match key(matrix, k) {
        None => {}
        Some(Yaml::Array(a)) => {
            for item in a {
                out.push(val(item)?);
            }
        }
        Some(_) => return None, // `os: ${{ ... }}` or a scalar axis
    }
    match key(matrix, "include") {
        None => {}
        Some(Yaml::Array(a)) => {
            for entry in a {
                let Yaml::Hash(e) = entry else { return None };
                if let Some(v) = key(e, k) {
                    out.push(val(v)?);
                }
            }
        }
        Some(_) => return None, // computed include legs
    }
    Some(out)
}

/// The workflow's trigger names: `on` as a scalar, a list or a mapping.
/// None when there is no `on` or it has another shape.
fn triggers(doc: &yaml_rust2::yaml::Hash) -> Option<Vec<String>> {
    match key(doc, "on")? {
        Yaml::String(s) => Some(vec![s.clone()]),
        Yaml::Array(a) => a.iter().map(|y| y.as_str().map(str::to_string)).collect(),
        Yaml::Hash(h) => h.keys().map(|y| y.as_str().map(str::to_string)).collect(),
        _ => None,
    }
}

/// The 1-based line of job `id`'s `runs-on` (else its header) in `text`, for
/// reporting only. The verdict never depends on it.
fn locate(text: &str, id: &str, what: &str) -> Option<usize> {
    let lines: Vec<&str> = text.lines().collect();
    let in_jobs = lines.iter().position(|l| l.trim_end() == "jobs:")?;
    let header = lines.iter().enumerate().skip(in_jobs + 1).find(|(_, l)| {
        let t = l.trim_start();
        let t = t
            .strip_prefix('"')
            .or_else(|| t.strip_prefix('\''))
            .unwrap_or(t);
        t.strip_prefix(id).is_some_and(|r| {
            let r = r.trim_start_matches(['"', '\'']).trim_start();
            r.starts_with(':')
        })
    })?;
    let ind = header.1.len() - header.1.trim_start().len();
    for (n, l) in lines.iter().enumerate().skip(header.0 + 1) {
        let t = l.trim();
        if !t.is_empty() && !t.starts_with('#') && l.len() - l.trim_start().len() <= ind {
            break;
        }
        if t.trim_start_matches(['"', '\'']).starts_with(what) {
            return Some(n + 1);
        }
    }
    Some(header.0 + 1)
}

/// Checks one workflow's text. `seen` counts self-hosted selections compared.
/// `exempt` is true when plant-guard.toml exempts this workflow.
pub fn check_workflow(name: &str, text: &str, cfg: &Config, exempt: bool) -> Report {
    let whole = |reason: String| Violation {
        file: name.to_string(),
        line: None,
        job: None,
        reason,
    };
    if text.len() > MAX_BYTES {
        return Report {
            seen: 0,
            bad: vec![whole(format!(
                "is larger than {MAX_BYTES} bytes; not checked, so not passed"
            ))],
        };
    }
    if expanded_nodes(text).is_some_and(|n| n > MAX_EXPANDED) {
        return Report { seen: 0, bad: vec![whole(format!("expands to more than {MAX_EXPANDED} bytes through aliases; not checked, so not passed"))] };
    }
    let docs = match YamlLoader::load_from_str(text) {
        Ok(d) => d,
        Err(e) => {
            return Report {
                seen: 0,
                bad: vec![whole(format!(
                    "cannot be read as YAML ({e}); not checked, so not passed"
                ))],
            }
        }
    };
    let doc = match docs.as_slice() {
        [Yaml::Hash(h)] => h,
        _ => {
            return Report {
                seen: 0,
                bad: vec![whole("is not a single YAML mapping".into())],
            }
        }
    };
    if has_merge_key(&docs[0]) {
        return Report {
            seen: 0,
            bad: vec![whole(
                "uses a YAML merge key (<<); merged values are not checked, so not passed".into(),
            )],
        };
    }
    let matrix_forms = cfg.matrix_forms();
    let mut bad = Vec::new();
    let mut seen = 0;
    let odd = case_variants(doc);
    if !odd.is_empty() {
        bad.push(whole(format!(
            "top-level key(s) {} differ from a workflow keyword only by case",
            odd.join(", ")
        )));
    }
    let jobs = match key(doc, "jobs") {
        None => None,
        Some(Yaml::Hash(h)) => Some(h),
        Some(_) => {
            bad.push(whole("`jobs` is not a mapping".into()));
            None
        }
    };
    for (id, job) in jobs.into_iter().flatten() {
        let Some(id) = id.as_str() else {
            bad.push(whole("a job id is not a string".into()));
            continue;
        };
        let at = |what: &str, reason: String| Violation {
            file: name.to_string(),
            line: locate(text, id, what),
            job: Some(id.to_string()),
            reason,
        };
        let Yaml::Hash(job) = job else {
            bad.push(at(":", "job is not a mapping".into()));
            continue;
        };
        let odd = case_variants(job);
        if !odd.is_empty() {
            bad.push(at(
                ":",
                format!(
                    "key(s) {} differ from a workflow keyword only by case",
                    odd.join(", ")
                ),
            ));
            continue;
        }
        let check_labels = |labels: &[String], bad: &mut Vec<Violation>| {
            if let Some(set) = &cfg.labels {
                for l in labels.iter().filter(|l| !set.contains(l.as_str())) {
                    bad.push(at(
                        "runs-on",
                        format!("runner label {l:?} is not in {CONFIG_FILE} labels"),
                    ));
                }
            }
        };
        let runs_on = key(job, "runs-on");
        if let Some(u) = key(job, "uses") {
            match u.as_str() {
                Some(p) if p.starts_with("./") && runs_on.is_none() => {} // checked as its own file
                _ => bad.push(at(
                    "uses",
                    "job calls a reusable workflow outside this repository; the runners it selects are not visible here".into(),
                )),
            }
            continue;
        }
        let Some(runs_on) = runs_on else {
            bad.push(at(":", "job has no runs-on and no local `uses:`".into()));
            continue;
        };
        // Matrix legs naming self-hosted: allowed only under the matrix form.
        let runner_vals = matrix_values(job, "runner");
        let self_hosted_legs = runner_vals
            .iter()
            .flatten()
            .filter(|v| {
                matches!(v, Val::List(l) if l.iter().any(|i| i == "self-hosted"))
                    || matches!(v, Val::One(s) if s.contains("self-hosted"))
            })
            .count();
        let ok = match runs_on {
            Yaml::String(v) => {
                if let Some(labels) = runs_on_form_labels(v, cfg) {
                    seen += 1;
                    check_labels(&labels, &mut bad);
                    true
                } else if matrix_forms.contains(v) {
                    seen += 1 + self_hosted_legs;
                    match &runner_vals {
                        Some(vals) if !vals.is_empty() => vals.iter().all(|x| match x {
                            Val::List(it) if it.iter().any(|i| i == "self-hosted") => {
                                check_labels(it, &mut bad);
                                true
                            }
                            Val::List(it) => !it.is_empty() && it.iter().all(|i| is_hosted(i)),
                            Val::One(s) => is_hosted(s),
                        }),
                        _ => false,
                    }
                } else if let Some(k) = plain_matrix_key(v) {
                    match matrix_values(job, k) {
                        Some(vals) if !vals.is_empty() => vals.iter().all(|x| match x {
                            Val::List(it) => !it.is_empty() && it.iter().all(|i| is_hosted(i)),
                            Val::One(s) => is_hosted(s),
                        }),
                        _ => false,
                    }
                } else if is_hosted(v) {
                    true
                } else if exempt && !v.contains("${{") {
                    seen += 1;
                    check_labels(std::slice::from_ref(v), &mut bad);
                    true
                } else {
                    false
                }
            }
            Yaml::Array(a) if exempt => match a
                .iter()
                .map(|y| {
                    y.as_str()
                        .filter(|s| !s.contains("${{"))
                        .map(str::to_string)
                })
                .collect::<Option<Vec<_>>>()
            {
                Some(l) if !l.is_empty() => {
                    seen += 1;
                    check_labels(&l, &mut bad);
                    true
                }
                _ => false,
            },
            _ => false,
        };
        if !ok {
            if matches!(runs_on, Yaml::String(s) if s.contains("self-hosted"))
                || matches!(runs_on, Yaml::Array(a) if a.iter().any(|y| y.as_str() == Some("self-hosted")))
            {
                seen += 1;
            }
            bad.push(at("runs-on", "runs-on is not a hosted image, the fail-closed form, or a matrix whose every runner is a hosted image".into()));
        }
        let is_matrix_form = matches!(runs_on, Yaml::String(v) if matrix_forms.contains(v));
        if self_hosted_legs > 0 && !is_matrix_form {
            seen += self_hosted_legs;
            bad.push(at("runner", "self-hosted matrix runner in a job whose runs-on is not the fail-closed matrix form".into()));
        }
    }
    if seen > 0 || exempt {
        match triggers(doc) {
            None => bad.push(whole(
                "has self-hosted jobs but no readable top-level `on:`".into(),
            )),
            Some(ev) => {
                let untrusted: Vec<_> = ev
                    .iter()
                    .filter(|e| !TRUSTED.contains(&e.as_str()))
                    .cloned()
                    .collect();
                if seen > 0 && !untrusted.is_empty() {
                    bad.push(whole(format!(
                        "self-hosted jobs under trigger(s) outside the allowlist: {}",
                        untrusted.join(", ")
                    )));
                }
                let reachable: Vec<_> = ev
                    .iter()
                    .filter(|e| !EXEMPTABLE.contains(&e.as_str()))
                    .cloned()
                    .collect();
                if exempt && !reachable.is_empty() {
                    bad.push(whole(format!(
                        "exempt in {CONFIG_FILE}, but trigger(s) {} can be caused by a pull request; an exemption holds only under push, schedule, workflow_dispatch and release",
                        reachable.join(", ")
                    )));
                }
            }
        }
    }
    Report { seen, bad }
}

pub struct GuardRun {
    pub workflows: usize,
    pub seen: usize,
    pub bad: Vec<Violation>,
    pub fallback: String,
    pub fallbacks: Vec<String>,
}

impl GuardRun {
    pub fn exit_code(&self) -> u8 {
        if self.seen == 0 || !self.bad.is_empty() {
            1
        } else {
            0
        }
    }
}

/// Reads the config: `explicit` when given (it must exist), else
/// DIR/plant-guard.toml when present, else the defaults.
pub fn load_config(dir: &Path, explicit: Option<&Path>) -> Result<Config, String> {
    let path: PathBuf = match explicit {
        Some(p) => p.to_path_buf(),
        None => {
            let p = dir.join(CONFIG_FILE);
            if !p.exists() {
                return Ok(Config::default());
            }
            p
        }
    };
    let text =
        fs::read_to_string(&path).map_err(|e| format!("could not read {}: {e}", path.display()))?;
    Config::parse(&text).map_err(|e| format!("{}: {e}", path.display()))
}

/// Checks every workflow under DIR/.github/workflows. Err means could not run.
pub fn run(dir: &Path, cfg: &Config) -> Result<GuardRun, String> {
    let wdir = dir.join(".github/workflows");
    let mut entries: Vec<PathBuf> = fs::read_dir(&wdir)
        .map_err(|e| format!("could not read {}: {e}", wdir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| matches!(p.extension().and_then(|x| x.to_str()), Some("yml" | "yaml")))
        .collect();
    entries.sort();
    let names: BTreeSet<String> = entries
        .iter()
        .map(|p| p.file_name().unwrap().to_string_lossy().into_owned())
        .collect();
    let exempt: BTreeSet<&str> = cfg.exempt.iter().map(|e| e.workflow.as_str()).collect();
    let (mut seen, mut bad) = (0, Vec::new());
    for e in &cfg.exempt {
        if !names.contains(&e.workflow) {
            bad.push(Violation {
                file: CONFIG_FILE.into(),
                line: None,
                job: None,
                reason: format!(
                    "exempts {:?}, which is not in .github/workflows",
                    e.workflow
                ),
            });
        }
    }
    for p in &entries {
        let text =
            fs::read_to_string(p).map_err(|e| format!("could not read {}: {e}", p.display()))?;
        let name = p.file_name().unwrap().to_string_lossy().into_owned();
        let r = check_workflow(&name, &text, cfg, exempt.contains(name.as_str()));
        seen += r.seen;
        bad.extend(r.bad);
    }
    if seen > 0 && cfg.labels.is_none() {
        bad.push(Violation {
            file: CONFIG_FILE.into(),
            line: None,
            job: None,
            reason:
                "workflows select self-hosted runners, but no provisioned `labels` are declared"
                    .into(),
        });
    }
    Ok(GuardRun {
        workflows: entries.len(),
        seen,
        bad,
        fallback: cfg.fallback.clone(),
        fallbacks: cfg.fallbacks.clone(),
    })
}

pub fn text(r: &GuardRun) -> String {
    let mut out = String::new();
    for b in &r.bad {
        out.push_str(&format!("FAIL  {b}\n"));
    }
    if r.seen == 0 {
        out.push_str(&format!(
            "FAIL  no self-hosted line found in {} workflow(s): this check compared nothing",
            r.workflows
        ));
    } else if !r.bad.is_empty() {
        out.push_str(&format!(
            "FAIL  {} violation(s) across {} self-hosted line(s)",
            r.bad.len(),
            r.seen
        ));
    } else {
        out.push_str(&format!(
            "self-hosted fork guard: OK ({} self-hosted line(s) in {} workflow(s), all fail-closed)",
            r.seen, r.workflows
        ));
    }
    out
}

pub fn json(r: &GuardRun) -> String {
    serde_json::json!({
        "schema": "plant.guard.v1",
        "ok": r.exit_code() == 0,
        "workflows": r.workflows,
        "self_hosted_lines": r.seen,
        "compared_nothing": r.seen == 0,
        "fallback": r.fallback,
        "fallbacks": r.fallbacks,
        "violations": r.bad,
    })
    .to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cfg() -> Config {
        Config {
            fallback: DEFAULT_FALLBACK.into(),
            fallbacks: vec![DEFAULT_FALLBACK.into()],
            labels: Some(
                ["self-hosted", "linux", "x64", "light", "rust-cpu"]
                    .iter()
                    .map(|s| s.to_string())
                    .collect(),
            ),
            exempt: vec![],
        }
    }
    fn check(name: &str, text: &str) -> Report {
        check_workflow(name, text, &cfg(), false)
    }
    fn good(label: &str) -> String {
        format!("${{{{ {GUARD} && fromJSON('[\"self-hosted\",\"linux\",\"x64\",\"{label}\"]') || '{DEFAULT_FALLBACK}' }}}}")
    }
    fn wf(on: &str, runs_on: &str) -> String {
        format!(
            "name: t\n{on}\njobs:\n  a:\n    runs-on: {runs_on}\n    steps:\n      - run: true\n"
        )
    }
    fn matrix_form() -> String {
        cfg().matrix_form()
    }

    // The 19 decision cases below are relay's (f852816), with `bad` counted.

    // rivet: verifies REQ-011
    #[test]
    fn accepts_the_fail_closed_form() {
        let r = check(
            "t.yml",
            &wf("on:\n  pull_request:\n  push:", &good("light")),
        );
        assert_eq!(
            r,
            Report {
                seen: 1,
                bad: vec![]
            }
        );
    }

    // rivet: verifies REQ-011
    #[test]
    fn rejects_the_fail_open_fork_form() {
        let v = "${{ github.event.pull_request.head.repo.fork && 'ubuntu-latest' || fromJSON('[\"self-hosted\",\"linux\"]') }}";
        let r = check("t.yml", &wf("on: [pull_request]", v));
        assert_eq!(r.bad.len(), 1, "{r:?}");
    }

    // rivet: verifies REQ-011
    #[test]
    fn rejects_an_unpinned_fallback() {
        let v = format!(
            "${{{{ {GUARD} && fromJSON('[\"self-hosted\",\"light\"]') || 'ubuntu-latest' }}}}"
        );
        let r = check("t.yml", &wf("on: [pull_request]", &v));
        assert_eq!(r.bad.len(), 1, "{r:?}");
        let m = matrix_form().replace(DEFAULT_FALLBACK, "ubuntu-latest");
        let t = format!("name: t\non: [pull_request]\njobs:\n  a:\n    strategy:\n      matrix:\n        include:\n          - runner: [self-hosted, light]\n    runs-on: {m}\n    steps:\n      - run: true\n");
        assert!(!check("t.yml", &t).bad.is_empty());
    }

    // rivet: verifies REQ-011
    #[test]
    fn rejects_a_plain_label_list() {
        let r = check(
            "t.yml",
            &wf("on:\n  schedule:", "[self-hosted, linux, x64, light]"),
        );
        assert_eq!(r.bad.len(), 1, "{r:?}");
    }

    // rivet: verifies REQ-011
    #[test]
    fn rejects_swapped_branches() {
        let v = format!("${{{{ {GUARD} && 'ubuntu-latest' || fromJSON('[\"self-hosted\"]') }}}}");
        let r = check("t.yml", &wf("on: [pull_request]", &v));
        assert_eq!(r.bad.len(), 1, "{r:?}");
    }

    // rivet: verifies REQ-011
    #[test]
    fn rejects_untrusted_triggers_even_with_the_form() {
        for on in [
            "on:\n  pull_request_target:",
            "on: [workflow_run]",
            "on:\n  issue_comment:\n    types: [created]",
        ] {
            let r = check("t.yml", &wf(on, &good("light")));
            assert_eq!(r.bad.len(), 1, "{on}: {r:?}");
        }
    }

    // rivet: verifies REQ-011
    #[test]
    fn trigger_parse_ignores_nested_keys() {
        let on = "on:\n  push:\n    branches: [main]\n  pull_request:\n    paths:\n      - 'x'";
        let r = check("t.yml", &wf(on, &good("light")));
        assert_eq!(
            r,
            Report {
                seen: 1,
                bad: vec![]
            }
        );
    }

    // rivet: verifies REQ-011
    #[test]
    fn matrix_runner_needs_the_matrix_form() {
        let body = |ro: &str| {
            format!(
                "on: [pull_request]\njobs:\n  test:\n    strategy:\n      matrix:\n        include:\n          - label: linux\n            runner: [self-hosted, linux, x64, rust-cpu]\n          - label: macos\n            runner: macos-14\n    runs-on: {ro}\n    steps:\n      - run: true\n"
            )
        };
        assert_eq!(check("t.yml", &body(&matrix_form())).bad, vec![]);
        let fail_open = "${{ github.event.pull_request.head.repo.fork && contains(matrix.runner, 'self-hosted') && 'ubuntu-latest' || matrix.runner }}";
        assert_eq!(check("t.yml", &body(fail_open)).bad.len(), 2);
    }

    // rivet: verifies REQ-011
    #[test]
    fn self_hosted_in_an_unknown_shape_fails_closed() {
        let t = "on: [pull_request]\njobs:\n  a:\n    runs-on:\n      - self-hosted\n    steps:\n      - run: true\n";
        assert!(!check("t.yml", t).bad.is_empty());
    }

    // rivet: verifies REQ-011
    #[test]
    fn comments_naming_self_hosted_are_ignored() {
        let t = format!(
            "# runs on self-hosted\n{}",
            wf("on: [push]", &good("rust-cpu"))
        );
        assert_eq!(
            check("t.yml", &t),
            Report {
                seen: 1,
                bad: vec![]
            }
        );
    }

    // rivet: verifies REQ-011
    #[test]
    fn shell_text_in_run_blocks_is_not_structure() {
        let t = format!(
            "on: [push]\njobs:\n  a:\n    runs-on: {}\n    steps:\n      - run: |\n          echo self-hosted fleet\n          kind=\"self-hosted\"\n      - name: x\n        run: true\n",
            good("light")
        );
        assert_eq!(
            check("t.yml", &t),
            Report {
                seen: 1,
                bad: vec![]
            }
        );
    }

    // rivet: verifies REQ-011
    #[test]
    fn a_runs_on_after_a_run_block_is_still_checked() {
        let t = "on: [push]\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: |\n          echo hi\n  b:\n    runs-on: [self-hosted, light]\n";
        assert_eq!(check("t.yml", t).bad.len(), 1);
    }

    // rivet: verifies REQ-011
    #[test]
    fn computed_runners_are_rejected() {
        for v in [
            "${{ needs.pick.outputs.runner }}",
            "${{ inputs.runner }}",
            "${{ vars.RUNNER }}",
            "${{ fromJSON(needs.pick.outputs.labels) }}",
            "${{ github.event.inputs.runner || 'ubuntu-latest' }}",
        ] {
            let r = check("t.yml", &wf("on: [workflow_dispatch]", v));
            assert_eq!(r.bad.len(), 1, "{v}: {r:?}");
        }
    }

    // rivet: verifies REQ-011
    #[test]
    fn plain_matrix_and_literal_hosted_runners_pass() {
        for v in ["ubuntu-latest", "macos-14", "windows-2022"] {
            let r = check("t.yml", &wf("on: [pull_request]", v));
            assert_eq!(
                r,
                Report {
                    seen: 0,
                    bad: vec![]
                },
                "{v}"
            );
        }
    }

    // rivet: verifies REQ-011
    #[test]
    fn block_and_map_runs_on_are_rejected() {
        let list = "on: [push]\njobs:\n  a:\n    runs-on:\n      - ${{ needs.x.outputs.r }}\n";
        let map = "on: [push]\njobs:\n  a:\n    runs-on: { group: fleet }\n";
        assert_eq!(check("t.yml", list).bad.len(), 1);
        assert_eq!(check("t.yml", map).bad.len(), 1);
    }

    // rivet: verifies REQ-011
    #[test]
    fn bare_and_listed_custom_labels_are_rejected() {
        for v in ["light", "[linux, light]", "[light]", "rust-cpu"] {
            let r = check("t.yml", &wf("on: [schedule]", v));
            assert_eq!(r.bad.len(), 1, "{v}: {r:?}");
        }
    }

    // rivet: verifies REQ-011
    #[test]
    fn plain_matrix_ref_needs_every_value_hosted() {
        let job = |axis: &str| {
            format!("on: [push]\njobs:\n  a:\n    strategy:\n      matrix:\n{axis}\n    runs-on: ${{{{ matrix.os }}}}\n")
        };
        assert!(
            check("t.yml", &job("        os: [ubuntu-latest, macos-14]"))
                .bad
                .is_empty()
        );
        assert!(check(
            "t.yml",
            &job("        os:\n          - ubuntu-24.04\n          - windows-2022")
        )
        .bad
        .is_empty());
        assert!(check(
            "t.yml",
            &job("        include:\n          - os: ubuntu-latest\n          - os: macos-14")
        )
        .bad
        .is_empty());
        assert_eq!(
            check("t.yml", &job("        os: [ubuntu-latest, light]"))
                .bad
                .len(),
            1
        );
        assert_eq!(
            check(
                "t.yml",
                &job("        include:\n          - os: ubuntu-latest\n          - os: light")
            )
            .bad
            .len(),
            1
        );
        assert_eq!(
            check("t.yml", &job("        os: ${{ fromJSON(vars.OSES) }}"))
                .bad
                .len(),
            1
        );
        assert_eq!(check("t.yml", &job("        arch: [x64]")).bad.len(), 1);
    }

    // rivet: verifies REQ-011
    #[test]
    fn matrix_form_rejects_a_custom_label_runner() {
        let job = "on: [pull_request]\njobs:\n  test:\n    strategy:\n      matrix:\n        include:\n          - runner: [linux, light]\n";
        let t = format!("{job}    runs-on: {}\n", matrix_form());
        assert_eq!(check("t.yml", &t).bad.len(), 1);
    }

    // rivet: verifies REQ-011
    #[test]
    fn a_workflow_without_self_hosted_is_not_counted() {
        let r = check("t.yml", &wf("on: [pull_request_target]", "ubuntu-latest"));
        assert_eq!(
            r,
            Report {
                seen: 0,
                bad: vec![]
            }
        );
    }

    // plant's additions: configured fallback, labels, exemptions.

    // rivet: verifies REQ-011
    #[test]
    fn the_fallback_is_a_per_repo_setting() {
        let c =
            Config::parse("fallback = \"ubuntu-22.04\"\nlabels = [\"self-hosted\", \"light\"]\n")
                .unwrap();
        let v = format!(
            "${{{{ {GUARD} && fromJSON('[\"self-hosted\",\"light\"]') || 'ubuntu-22.04' }}}}"
        );
        assert!(
            check_workflow("t.yml", &wf("on: [pull_request]", &v), &c, false)
                .bad
                .is_empty()
        );
        let pinned_elsewhere = check_workflow(
            "t.yml",
            &wf("on: [pull_request]", &good("light")),
            &c,
            false,
        );
        assert_eq!(pinned_elsewhere.bad.len(), 1, "{pinned_elsewhere:?}");
        assert!(Config::parse("fallback = \"light\"").is_err());
        assert!(Config::parse("fallback = \"ubuntu-latest' || 'light\"").is_err());
    }

    // rivet: verifies REQ-012
    #[test]
    fn a_label_outside_the_declared_set_is_rejected() {
        let r = check("t.yml", &wf("on: [pull_request]", &good("}.$l.q{")));
        assert_eq!(r.bad.len(), 1, "{r:?}");
        assert!(r.bad[0].reason.contains("\"}.$l.q{\""), "{r:?}");
        let r = check("t.yml", &wf("on: [pull_request]", &good("lihgt")));
        assert_eq!(r.bad.len(), 1, "{r:?}");
    }

    // rivet: verifies REQ-012
    #[test]
    fn a_matrix_runner_label_outside_the_set_is_rejected() {
        let t = format!(
            "on: [pull_request]\njobs:\n  test:\n    strategy:\n      matrix:\n        include:\n          - runner: [self-hosted, linux, gpu]\n    runs-on: {}\n",
            matrix_form()
        );
        let r = check("t.yml", &t);
        assert_eq!(r.bad.len(), 1, "{r:?}");
        assert!(r.bad[0].reason.contains("\"gpu\""));
    }

    // rivet: verifies REQ-012
    #[test]
    fn a_form_whose_label_list_is_not_json_is_rejected() {
        let v = format!(
            "${{{{ {GUARD} && fromJSON('[self-hosted, light]') || '{DEFAULT_FALLBACK}' }}}}"
        );
        assert_eq!(check("t.yml", &wf("on: [push]", &v)).bad.len(), 1);
    }

    // rivet: verifies REQ-012
    #[test]
    fn labels_are_not_checked_when_none_are_declared_but_the_run_fails() {
        let dir = tempdir_with("x.yml", &wf("on: [push]", &good("light")));
        let r = run(dir.path(), &Config::default()).unwrap();
        assert_eq!(r.bad.len(), 1, "{:?}", r.bad);
        assert!(r.bad[0].reason.contains("no provisioned `labels`"));
        assert_eq!(r.exit_code(), 1);
    }

    // rivet: verifies REQ-013
    #[test]
    fn an_exemption_holds_for_a_schedule_only_workflow() {
        let t = wf(
            "on:\n  schedule:\n    - cron: '0 3 * * *'\n  workflow_dispatch:",
            "[self-hosted, linux, light]",
        );
        let r = check_workflow("nightly.yml", &t, &cfg(), true);
        assert_eq!(
            r,
            Report {
                seen: 1,
                bad: vec![]
            }
        );
        let r = check_workflow("nightly.yml", &wf("on: [schedule]", "light"), &cfg(), true);
        assert_eq!(
            r,
            Report {
                seen: 1,
                bad: vec![]
            }
        );
        // Labels are still checked in an exempt workflow.
        let r = check_workflow(
            "nightly.yml",
            &wf("on: [schedule]", "[self-hosted, lihgt]"),
            &cfg(),
            true,
        );
        assert_eq!(r.bad.len(), 1, "{r:?}");
    }

    // rivet: verifies REQ-013
    #[test]
    fn an_exemption_on_a_pull_request_workflow_is_a_violation() {
        for on in [
            "on: [pull_request]",
            "on:\n  push:\n  pull_request:",
            "on: [merge_group]",
        ] {
            let r = check_workflow("x.yml", &wf(on, "[self-hosted, light]"), &cfg(), true);
            assert_eq!(r.bad.len(), 1, "{on}: {r:?}");
            assert!(r.bad[0].reason.contains("exempt"), "{r:?}");
        }
        // Even with no self-hosted job, the exemption itself is checked.
        let r = check_workflow(
            "x.yml",
            &wf("on: [pull_request]", "ubuntu-24.04"),
            &cfg(),
            true,
        );
        assert_eq!(r.bad.len(), 1, "{r:?}");
    }

    // rivet: verifies REQ-013
    #[test]
    fn an_exemption_does_not_admit_computed_runners() {
        let r = check_workflow(
            "n.yml",
            &wf("on: [schedule]", "${{ vars.RUNNER }}"),
            &cfg(),
            true,
        );
        assert_eq!(r.bad.len(), 1, "{r:?}");
    }

    // rivet: verifies REQ-013
    #[test]
    fn an_exemption_for_a_missing_workflow_is_a_violation() {
        let dir = tempdir_with("x.yml", &wf("on: [push]", &good("light")));
        let mut c = cfg();
        c.exempt = vec![Exempt {
            workflow: "gone.yml".into(),
            reason: "old".into(),
        }];
        let r = run(dir.path(), &c).unwrap();
        assert_eq!(r.bad.len(), 1, "{:?}", r.bad);
        assert!(r.bad[0].reason.contains("gone.yml"));
    }

    // rivet: verifies REQ-013
    #[test]
    fn config_is_strict() {
        assert!(Config::parse("lables = [\"x\"]").is_err());
        assert!(Config::parse("labels = []").is_err());
        assert!(Config::parse("[[exempt]]\nworkflow = \"a.yml\"\nreason = \" \"").is_err());
        assert!(Config::parse("[[exempt]]\nworkflow = \"../a.yml\"\nreason = \"x\"").is_err());
        let c = Config::parse("labels = [\"self-hosted\"]\n[[exempt]]\nworkflow = \"a.yml\"\nreason = \"schedule only\"").unwrap();
        assert_eq!(c.fallback, DEFAULT_FALLBACK);
        assert_eq!(c.exempt.len(), 1);
    }

    // rivet: verifies REQ-011
    #[test]
    fn a_tree_with_no_self_hosted_line_compared_nothing() {
        let dir = tempdir_with("x.yml", &wf("on: [push]", "ubuntu-24.04"));
        let r = run(dir.path(), &cfg()).unwrap();
        assert_eq!((r.seen, r.exit_code()), (0, 1));
        assert!(text(&r).contains("compared nothing"));
    }

    // rivet: verifies REQ-011
    #[test]
    fn a_name_naming_self_hosted_is_not_a_site() {
        let t = format!(
            "name: no fork PR reaches a self-hosted runner\non: [pull_request]\njobs:\n  a:\n    name: self-hosted guard\n    runs-on: {}\n    steps:\n      - name: No fork PR reaches a self-hosted runner\n        run: true\n",
            good("light")
        );
        assert_eq!(
            check("t.yml", &t),
            Report {
                seen: 1,
                bad: vec![]
            }
        );
        // A runs-on is still a site even in a job that has a name.
        let t = "on: [pull_request]\njobs:\n  a:\n    name: x\n    runs-on: [self-hosted, light]\n";
        assert_eq!(check("t.yml", t).bad.len(), 1);
    }

    // rivet: verifies REQ-011
    #[test]
    fn release_is_a_trusted_trigger() {
        let r = check(
            "t.yml",
            &wf(
                "on:\n  release:\n    types: [published]\n  push:",
                &good("light"),
            ),
        );
        assert_eq!(
            r,
            Report {
                seen: 1,
                bad: vec![]
            }
        );
    }

    // Bypasses found by review of the line-based parser (PR #10). Each must
    // be rejected; every one exited 0 before the structural parse.
    // rivet: verifies REQ-011
    #[test]
    fn review_bypasses_are_rejected() {
        let f = good("light");
        let m = matrix_form();
        let ok = format!("  ok:\n    runs-on: {f}\n");
        let cases: Vec<(&str, String)> = vec![
            ("quoted key", format!("on: [pull_request]\njobs:\n{ok}  evil:\n    \"runs-on\": light\n")),
            ("space before colon", format!("on: [pull_request]\njobs:\n{ok}  evil:\n    runs-on : light\n")),
            ("flow-style job", format!("on: [pull_request]\njobs:\n{ok}  evil: {{runs-on: light, steps: [{{run: id}}]}}\n")),
            ("flow trigger list over two lines", format!("on: [push,\n  pull_request_target]\njobs:\n{ok}")),
            ("block trigger list at indent 0", format!("on:\n- push\n- pull_request_target\njobs:\n{ok}")),
            ("include adds a label leg", format!("on: [pull_request]\njobs:\n{ok}  evil:\n    strategy:\n      matrix:\n        os: [ubuntu-latest]\n        include: [{{os: light}}]\n    runs-on: ${{{{ matrix.os }}}}\n")),
            ("computed include", format!("on: [pull_request]\njobs:\n{ok}  evil:\n    strategy:\n      matrix:\n        os: [ubuntu-latest]\n        include: ${{{{ fromJSON(needs.ok.outputs.extra) }}}}\n    runs-on: ${{{{ matrix.os }}}}\n")),
            ("computed matrix with a decoy", format!("on: [pull_request]\njobs:\n{ok}  evil:\n    env:\n      os: ubuntu-latest\n    strategy:\n      matrix: ${{{{ fromJSON(needs.ok.outputs.m) }}}}\n    runs-on: ${{{{ matrix.os }}}}\n")),
            ("flow-map include in the matrix form", format!("on: [pull_request]\njobs:\n  evil:\n    strategy:\n      matrix:\n        include:\n          - runner: [self-hosted, light]\n          - {{runner: [linux, light]}}\n    runs-on: {m}\n")),
            ("anchored job header", "on: [pull_request]\njobs:\n  ok: &e\n    strategy:\n      matrix:\n        os: [ubuntu-latest]\n    runs-on: ${{ matrix.os }}\n  evil:\n    strategy:\n      matrix:\n        os: [light]\n    runs-on: ${{ matrix.os }}\n".to_string()),
            ("remote reusable workflow", format!("on: [pull_request]\njobs:\n{ok}  evil:\n    uses: some-org/other/.github/workflows/sh.yml@main\n")),
            ("self-hosted label with a hosted prefix", format!("on: [pull_request]\njobs:\n{ok}  evil:\n    runs-on: ubuntu-gpu\n")),
            ("merge key", format!("on: [pull_request]\njobs:\n  base: &b\n    runs-on: {f}\n  evil:\n    <<: *b\n    runs-on: light\n")),
            ("job without runs-on", format!("on: [pull_request]\njobs:\n{ok}  evil:\n    steps: []\n")),
            ("case variant of runs-on", format!("on: [pull_request]\njobs:\n{ok}  evil:\n    Runs-On: light\n")),
            ("case variant of include", format!("on: [pull_request]\njobs:\n{ok}  evil:\n    strategy:\n      matrix:\n        os: [ubuntu-latest]\n        Include: [{{os: light}}]\n    runs-on: ${{{{ matrix.os }}}}\n")),
            ("case variant of on", format!("On: [pull_request_target]\njobs:\n{ok}")),
            ("merge key in an include entry", format!("on: [pull_request]\njobs:\n{ok}  evil:\n    strategy:\n      matrix:\n        os: [ubuntu-latest]\n        include:\n          - <<: {{os: light}}\n    runs-on: ${{{{ matrix.os }}}}\n")),
            ("merge key in strategy", format!("on: [pull_request]\njobs:\n{ok}  evil:\n    strategy: {{<<: {{matrix: {{os: [light]}}}}, matrix: {{os: [ubuntu-latest]}}}}\n    runs-on: ${{{{ matrix.os }}}}\n")),
            ("boolean top-level key", format!("true: [pull_request_target]\non: [push]\njobs:\n{ok}")),
            ("duplicate runs-on", "on: [pull_request]\njobs:\n  evil:\n    runs-on: ubuntu-24.04\n    runs-on: light\n".to_string()),
        ];
        for (what, t) in &cases {
            assert!(!check("t.yml", t).bad.is_empty(), "{what} passed:\n{t}");
        }
        for (what, on) in [
            ("two-line flow list", "on: [push,\n  pull_request]"),
            ("indent-0 list", "on:\n- push\n- pull_request"),
        ] {
            let t = format!("{on}\njobs:\n  a:\n    runs-on: [self-hosted, light]\n");
            assert!(
                !check_workflow("x.yml", &t, &cfg(), true).bad.is_empty(),
                "exempt {what} held"
            );
        }
    }

    // rivet: verifies REQ-011
    #[test]
    fn an_alias_bomb_is_a_violation_not_a_crash() {
        let mut t = String::from("on: [push]\na0: &a0 [x, x, x, x, x, x, x, x, x]\n");
        for i in 1..10 {
            let p = i - 1;
            t.push_str(&format!(
                "a{i}: &a{i} [*a{p}, *a{p}, *a{p}, *a{p}, *a{p}, *a{p}, *a{p}, *a{p}, *a{p}]\n"
            ));
        }
        t.push_str(&format!("jobs:\n  a:\n    runs-on: {}\n", good("light")));
        let r = check("t.yml", &t);
        assert_eq!(r.bad.len(), 1, "{r:?}");
        assert!(r.bad[0].reason.contains("expands to more than"), "{r:?}");
        // One long scalar aliased many times.
        let mut t = format!("on: [push]\ns: &s {}\nl: [", "x".repeat(100_000));
        t.push_str(&vec!["*s"; 100].join(", "));
        t.push_str(&format!("]\njobs:\n  a:\n    runs-on: {}\n", good("light")));
        let r = check("t.yml", &t);
        assert!(
            r.bad.len() == 1 && r.bad[0].reason.contains("expands to more than"),
            "{r:?}"
        );
        let big = format!("on: [push]\n#{}\n", "x".repeat(MAX_BYTES));
        assert!(check("t.yml", &big).bad[0].reason.contains("larger than"));
    }

    // rivet: verifies REQ-013
    #[test]
    fn review_false_positives_are_accepted() {
        let t = "on:\n  push:\n    branches: [main]\n  \"schedule\":\n    - cron: '0 3 * * *'\njobs:\n  a:\n    runs-on: [self-hosted, light]\n";
        assert_eq!(
            check_workflow("n.yml", t, &cfg(), true),
            Report {
                seen: 1,
                bad: vec![]
            }
        );
        let t = format!(
            "on: [pull_request]\njobs:\n  a:\n    strategy:\n      matrix:\n        include:\n          - runner:\n              - self-hosted\n              - light\n    runs-on: {}\n    steps:\n      - run: !!str |\n          echo self-hosted\n",
            matrix_form()
        );
        assert!(
            check("t.yml", &t).bad.is_empty(),
            "{:?}",
            check("t.yml", &t)
        );
    }

    // sigil's equivalence corpus, shape s19: spacing inside the braces is the
    // same matrix reference. Values are still checked.
    // rivet: verifies REQ-011
    #[test]
    fn a_matrix_ref_with_odd_spacing_is_still_a_matrix_ref() {
        let job = |ro: &str, os: &str| {
            format!("on: [push]\njobs:\n  a:\n    strategy:\n      matrix:\n        os: [{os}]\n    runs-on: {ro}\n")
        };
        for ro in ["${{matrix.os   }}", "${{  matrix.os}}", "${{\tmatrix.os }}"] {
            assert!(
                check("t.yml", &job(ro, "ubuntu-latest")).bad.is_empty(),
                "{ro}"
            );
            assert_eq!(
                check("t.yml", &job(ro, "light")).bad.len(),
                1,
                "{ro} with a label"
            );
        }
        assert_eq!(plain_matrix_key("${{ matrix.os || 'x' }}"), None);
        assert_eq!(plain_matrix_key("${{ matrix. }}"), None);
    }

    // sigil's corpus, cases t00 and t01: a repo may accept several fallbacks.
    // rivet: verifies REQ-011
    #[test]
    fn fallback_may_be_a_list() {
        let c = Config::parse(
            "fallback = [\"ubuntu-24.04\", \"ubuntu-latest\"]\nlabels = [\"self-hosted\", \"light\"]\n",
        )
        .unwrap();
        assert_eq!(c.fallback, "ubuntu-24.04");
        let form = |fb: &str| {
            format!("${{{{ {GUARD} && fromJSON('[\"self-hosted\",\"light\"]') || '{fb}' }}}}")
        };
        for fb in ["ubuntu-24.04", "ubuntu-latest"] {
            let r = check_workflow("t.yml", &wf("on: [pull_request]", &form(fb)), &c, false);
            assert!(r.bad.is_empty(), "{fb}: {r:?}");
            let m = c
                .matrix_forms()
                .into_iter()
                .find(|m| m.ends_with(&format!("'{fb}' }}}}")))
                .unwrap();
            let t = format!("on: [pull_request]\njobs:\n  a:\n    strategy:\n      matrix:\n        include:\n          - runner: [self-hosted, light]\n    runs-on: {m}\n");
            assert!(
                check_workflow("t.yml", &t, &c, false).bad.is_empty(),
                "matrix {fb}"
            );
        }
        // A fallback outside the list is still rejected.
        let r = check_workflow(
            "t.yml",
            &wf("on: [pull_request]", &form("ubuntu-22.04")),
            &c,
            false,
        );
        assert_eq!(r.bad.len(), 1, "{r:?}");
        assert!(Config::parse("fallback = []").is_err());
        assert!(Config::parse("fallback = [\"ubuntu-24.04\", \"light\"]").is_err());
    }

    // rivet: verifies REQ-012
    #[test]
    fn hosted_image_names_are_exact() {
        for h in [
            "ubuntu-latest",
            "ubuntu-24.04",
            "ubuntu-24.04-arm",
            "ubuntu-slim",
            "macos-15",
            "macos-15-intel",
            "macos-14-large",
            "windows-2022",
            "windows-11-arm",
            "windows-latest",
        ] {
            assert!(is_hosted(h), "{h}");
        }
        for h in [
            "ubuntu-gpu",
            "ubuntu-24",
            "macos-15.1",
            "windows-x",
            "ubuntu-24.04-gpu",
            "ubuntu-",
            "light",
        ] {
            assert!(!is_hosted(h), "{h}");
        }
    }

    struct TempDir(PathBuf);
    impl TempDir {
        fn path(&self) -> &Path {
            &self.0
        }
    }
    impl Drop for TempDir {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }
    fn tempdir_with(name: &str, text: &str) -> TempDir {
        use std::sync::atomic::{AtomicUsize, Ordering};
        static N: AtomicUsize = AtomicUsize::new(0);
        let d = std::env::temp_dir().join(format!(
            "plant-guard-{}-{}",
            std::process::id(),
            N.fetch_add(1, Ordering::SeqCst)
        ));
        fs::create_dir_all(d.join(".github/workflows")).unwrap();
        fs::write(d.join(".github/workflows").join(name), text).unwrap();
        TempDir(d)
    }
}
