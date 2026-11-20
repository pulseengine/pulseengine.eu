//! North Star consumer for O1, O3 and O5 (seam pulseengine.eu#393).
//!
//! For every product in data/north-star.toml whose `pulls` include the
//! objective: take its latest release, find `north-star-input.<Ox>.json`,
//! check that the release's SHA256SUMS lists it with the right sha256 and that
//! SHA256SUMS is cosign-signed by a workflow of that repository at the release
//! tag, validate it against data/north-star/input.schema.json (v1), then count.
//! Writes data/north-star/<Ox>.json in the shape of O2.json / O4.json plus
//! `schema_version: 1`.

pub mod count;
pub mod schema;
pub mod source;
pub mod verify;

use count::{Counted, Rules, Tally};
use serde_json::{json, Map, Value};
use source::{Source, ORG};
use std::path::{Path, PathBuf};
use verify::Signature;

pub const VERSION: &str = env!("CARGO_PKG_VERSION");

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Objective {
    O1,
    O3,
    O5,
}

impl Objective {
    pub fn parse(s: &str) -> Option<Objective> {
        match s.to_ascii_lowercase().as_str() {
            "o1" => Some(Objective::O1),
            "o3" => Some(Objective::O3),
            "o5" => Some(Objective::O5),
            _ => None,
        }
    }
    pub fn id(self) -> &'static str {
        match self {
            Objective::O1 => "O1",
            Objective::O3 => "O3",
            Objective::O5 => "O5",
        }
    }
    pub fn asset(self) -> String {
        format!("north-star-input.{}.json", self.id())
    }
    /// The objective-specific counting rule, as stated in --help and blind_spot.
    pub fn rule(self) -> &'static str {
        match self {
            Objective::O1 => "O1: the value counts (target, named rung) facts that pass, named rungs being hil, real-drone and flight (jess's ladder); of = 3 named rungs per target the input reports, so a named rung not reported is a fail; r0 and synth's execution_match, reach and wcet are listed in items with in_value=false and never enter the value; an absent control_failed_as_expected is not penalised",
            Objective::O3 => "O3: a product or tool repository counts only if its facts proof_check_required, axiom_audit and ledger all pass, each with control_failed_as_expected=true (absent counts as a fail, the seam requires a planted control per fact); of = products plus tool repositories pulling O3 in data/north-star.toml, so a product or tool repository that is not counted stays in the denominator",
            Objective::O5 => "O5: a gate counts only if detail.signed, kiln_runs, wasmtime_equal and equivalence_in_ci are true and gap_switch is false; of = the gates the counted inputs report, not all our tools and gates (a better denominator is an open question); an absent control_failed_as_expected is not penalised",
        }
    }
}

/// The rules every objective shares, as stated in --help and blind_spot.
pub const COMMON_RULES: [&str; 4] = [
    "missing, unsigned or invalid input is not counted, never zero-filled: the product is listed under not_counted with the reason",
    "signed means SHA256SUMS lists the input with its sha256 and cosign verifies SHA256SUMS as signed by a workflow of the product's own repository at the release tag (GitHub OIDC); without cosign nothing is measured",
    "a fact with ran=false is a fail",
    "a fact with control_failed_as_expected=false is a fail: the check could not fail",
];

/// What this consumer does not check.
pub const NOT_CHECKED: &str = "facts are signed claims from the producer's release workflow and are not re-run here; the producers' own blind spots are under producer_not_measured; a cosign failure for any reason, a network outage included, makes an input unsigned (not counted), never measured; duplicate JSON keys in an input are not detected";

pub fn help() -> String {
    let mut s = String::from(
        "north-star-measure: measure North Star objective O1, O3 or O5 from signed release inputs\n\n\
         usage: north-star-measure o1|o3|o5 [--offline FIXTURE_DIR] [--root DIR]\n       \
         north-star-measure snapshot-matches COMMITTED.json LIVE.json\n\n\
         For every product and tool repository ([[products]] and [[tool_repos]]) in DIR/data/north-star.toml whose pulls include the objective, reads its\n\
         latest release, finds north-star-input.<Ox>.json, checks its sha256 in the release's SHA256SUMS\n\
         (or SHA256SUMS.txt), runs cosign verify-blob on SHA256SUMS against\n\
         ^https://github.com/pulseengine/<repo>/.github/workflows/<file>@refs/tags/<tag>$ with the GitHub\n\
         OIDC issuer, validates the input against schema_version 1 (file name and objective must agree,\n\
         repo must be pulseengine/<product>), counts, and writes DIR/data/north-star/<Ox>.json.\n\n\
         Counting rules:\n",
    );
    for r in COMMON_RULES {
        s.push_str(&format!("  - {r}\n"));
    }
    for o in [Objective::O1, Objective::O3, Objective::O5] {
        s.push_str(&format!("  - {}\n", o.rule()));
    }
    s.push_str(&format!(
        "\nNot checked: {NOT_CHECKED}.\n\n\
         If no product's input can be counted, nothing is written: the objective stays unmeasured, never 0.\n\n\
         Options:\n  --offline DIR  read DIR/<product>/release.json and DIR/<product>/assets/<name> instead of GitHub\n  \
         --root DIR     repository root (default: the nearest parent with data/north-star.toml)\n\n\
         Environment: GITHUB_TOKEN or GH_TOKEN (API reads), COSIGN (path to cosign; default: PATH).\n\n\
         Exit: 0 measured; 1 a rule broke (data/north-star.toml's state disagrees with the written\n\
         measurement, rule 7, or value exceeds of); 2 could not measure (no cosign, no product pulls the\n\
         objective, no input counted, or a release could not be read).\n"
    ));
    s
}

pub fn blind_spot(o: Objective) -> String {
    format!("counting rules: {}; {}. Not checked: {NOT_CHECKED}", COMMON_RULES.join("; "), o.rule())
}

/// Products and tool repositories in north-star.toml that pull `objective`, in file order, and the
/// objective's `state`.
pub fn products_pulling(toml_text: &str, objective: &str) -> Result<(Vec<String>, Option<String>), String> {
    let doc: toml::Table = toml_text.parse().map_err(|e| format!("data/north-star.toml: {e}"))?;
    let mut out = Vec::new();
    let entries = ["products", "tool_repos"]
        .iter()
        .flat_map(|k| doc.get(*k).and_then(|v| v.as_array()).cloned().unwrap_or_default());
    for p in entries {
        let name = p.get("name").and_then(|v| v.as_str()).unwrap_or("");
        let pulls = p.get("pulls").and_then(|v| v.as_array()).cloned().unwrap_or_default();
        if !name.is_empty() && pulls.iter().any(|x| x.as_str() == Some(objective)) {
            if !schema::repo_ok(&format!("{ORG}/{name}")) {
                return Err(format!("product or tool repository name {name:?} is not a repository name"));
            }
            out.push(name.to_string());
        }
    }
    let state = doc
        .get("objectives")
        .and_then(|v| v.as_array())
        .and_then(|a| a.iter().find(|o| o.get("id").and_then(|v| v.as_str()) == Some(objective)))
        .and_then(|o| o.get("state"))
        .and_then(|v| v.as_str())
        .map(String::from);
    Ok((out, state))
}

pub struct Env {
    pub root: PathBuf,
    pub source: Source,
    pub cosign: PathBuf,
    pub rules: Rules,
}

#[derive(Debug)]
pub enum Outcome {
    /// The document to write.
    Measured(Value),
    /// Nothing to write (exit 2): why, and the products not counted.
    Unmeasured(String, Vec<Value>),
}

fn not_counted(product: &str, release: Option<&str>, reason: impl Into<String>) -> Value {
    json!({"product": product, "release": release, "reason": reason.into()})
}

struct Work(PathBuf);
impl Drop for Work {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

fn work_dir() -> Result<Work, String> {
    static SEQ: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let nanos = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0);
    let seq = SEQ.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
    let p = std::env::temp_dir().join(format!("ns-measure-{}-{nanos}-{seq}", std::process::id()));
    // create_dir, not create_dir_all: an existing directory is someone else's.
    std::fs::create_dir(&p).map_err(|e| format!("temp dir {}: {e}", p.display()))?;
    Ok(Work(p))
}

/// One product. `Ok(Ok)` counted, `Ok(Err)` not counted (with the reason),
/// `Err` could not measure.
fn intake(o: Objective, product: &str, env: &Env, work: &Path) -> Result<Result<(Counted, Value), Value>, String> {
    let Some(rel) = env.source.latest_release(product)? else {
        return Ok(Err(not_counted(product, None, "no release")));
    };
    let tag = rel.tag.as_str();
    let nc = |r: String| Ok(Err(not_counted(product, Some(tag), r)));
    let asset = o.asset();
    if !rel.has(&asset) {
        return nc(format!("no {asset} asset in {tag}"));
    }
    let Some(sums_name) = verify::SUMS_NAMES.iter().find(|n| rel.has(n)) else {
        return nc(format!("{asset} is not listed in a signed SHA256SUMS: {tag} has no SHA256SUMS or SHA256SUMS.txt"));
    };
    let bundle = format!("{sums_name}.cosign.bundle");
    let (sig_s, cert_s) = (format!("{sums_name}.sig"), format!("{sums_name}.pem"));
    let dir = work.join(product);
    std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let sig = if rel.has(&bundle) {
        env.source.fetch(product, &rel, &bundle, &dir.join(&bundle))?;
        Signature::Bundle(dir.join(&bundle))
    } else if rel.has(&sig_s) && rel.has(&cert_s) {
        env.source.fetch(product, &rel, &sig_s, &dir.join(&sig_s))?;
        env.source.fetch(product, &rel, &cert_s, &dir.join(&cert_s))?;
        Signature::SigCert(dir.join(&sig_s), dir.join(&cert_s))
    } else {
        return nc(format!("unsigned: {tag} carries {sums_name} without {bundle} or {sig_s} + {cert_s}"));
    };
    let sums_path = dir.join(sums_name);
    env.source.fetch(product, &rel, sums_name, &sums_path)?;
    let identity = verify::identity_regexp(ORG, product, tag);
    if let Err(e) = verify::cosign_verify(&env.cosign, &sums_path, &sig, &identity) {
        return nc(format!("unsigned: {sums_name} does not verify as signed by {identity}: {e}"));
    }
    let input_path = dir.join(&asset);
    env.source.fetch(product, &rel, &asset, &input_path)?;
    let bytes = std::fs::read(&input_path).map_err(|e| e.to_string())?;
    let sums_text = std::fs::read_to_string(&sums_path).map_err(|e| format!("{sums_name}: {e}"))?;
    let got = verify::sha256_hex(&bytes);
    match verify::sums_lookup(&sums_text, &asset) {
        Err(e) => return nc(e),
        Ok(None) => return nc(format!("{sums_name} does not list {asset}")),
        Ok(Some(want)) if want != got => return nc(format!("{asset} sha256 {got} does not match {sums_name} ({want})")),
        Ok(Some(_)) => {}
    }
    let text = match String::from_utf8(bytes) {
        Ok(t) => t,
        Err(_) => return nc(format!("invalid: {asset} is not UTF-8")),
    };
    let input = match schema::validate(&text) {
        Ok(i) => i,
        Err(e) => return nc(format!("invalid: {asset}: {e}")),
    };
    if input.objective != o.id() {
        return nc(format!("invalid: file name says {} but objective is {:?}", o.id(), input.objective));
    }
    if input.repo != format!("{ORG}/{product}") {
        return nc(format!("invalid: repo is {:?}, the release is {ORG}/{product}", input.repo));
    }
    if let Err(e) = count::structure(o.id(), &input) {
        return nc(format!("invalid: {e}"));
    }
    let meta = json!({"product": product, "release": tag, "asset": asset, "sha256": got,
                      "signer": identity, "input_version": input.version});
    Ok(Ok((Counted { product: product.into(), release: tag.into(), input }, meta)))
}

/// UTC now as `YYYY-MM-DDTHH:MMZ` (the O2.json / O4.json format).
pub fn now_utc() -> (String, String) {
    let secs = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0) as i64;
    let (days, rem) = (secs.div_euclid(86_400), secs.rem_euclid(86_400));
    // Howard Hinnant's civil_from_days.
    let z = days + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = yoe + era * 400 + i64::from(m <= 2);
    let date = format!("{y:04}-{m:02}-{d:02}");
    (format!("{date}T{:02}:{:02}Z", rem / 3600, rem % 3600 / 60), date)
}

/// Measure `o`. `Err`: could not measure (exit 2).
pub fn measure(o: Objective, env: &Env) -> Result<Outcome, String> {
    let toml_path = env.root.join("data").join("north-star.toml");
    let text = std::fs::read_to_string(&toml_path).map_err(|e| format!("{}: {e}", toml_path.display()))?;
    let (products, _) = products_pulling(&text, o.id())?;
    if products.is_empty() {
        return Ok(Outcome::Unmeasured(format!("no product in data/north-star.toml pulls {}", o.id()), vec![]));
    }
    let work = work_dir()?;
    let (mut counted, mut metas, mut skipped) = (Vec::new(), Vec::new(), Vec::new());
    for p in &products {
        match intake(o, p, env, &work.0)? {
            Ok((c, m)) => {
                counted.push(c);
                metas.push(m);
            }
            Err(nc) => skipped.push(nc),
        }
    }
    if counted.is_empty() {
        return Ok(Outcome::Unmeasured(
            format!("no product publishes a countable {} yet ({} pulling: {})", o.asset(), products.len(), products.join(", ")),
            skipped,
        ));
    }
    let Tally { value, of, items } = match o {
        Objective::O1 => count::o1(&counted, env.rules),
        Objective::O3 => count::o3(&counted, products.len() as u64, env.rules),
        Objective::O5 => count::o5(&counted, env.rules),
    };
    if of == 0 {
        return Ok(Outcome::Unmeasured(format!("the counted inputs report nothing to count for {} (of = 0)", o.id()), skipped));
    }
    let (measured_at, date) = now_utc();
    let mut producer_nm = Map::new();
    for c in &counted {
        producer_nm.insert(c.product.clone(), json!(c.input.not_measured));
    }
    let doc = json!({
        "schema_version": 1,
        "objective": o.id(),
        "measured_at": measured_at,
        "verifier": format!("north-star-measure {VERSION}: cosign verify-blob on SHA256SUMS, input schema v1"),
        "as_of": format!("latest releases on {date}"),
        "value": value,
        "of": of,
        "items": items,
        "not_counted": skipped,
        "inputs": metas,
        "producer_not_measured": producer_nm,
        "blind_spot": blind_spot(o),
    });
    Ok(Outcome::Measured(doc))
}

/// What must stay equal between the committed snapshot and a live run: the
/// objective, value, of, and which releases were counted and not counted.
/// Times and cosign wording may differ.
pub fn snapshot_key(d: &Value) -> Value {
    let pairs = |k: &str| -> Vec<Value> {
        d[k].as_array().into_iter().flatten().map(|x| json!([x["product"], x["release"]])).collect()
    };
    json!({"objective": d["objective"], "value": d["value"], "of": d["of"],
           "inputs": pairs("inputs"), "not_counted": pairs("not_counted")})
}

/// `snapshot-matches COMMITTED LIVE`: 0 equal, 1 stale, 2 unreadable.
pub fn snapshot_matches(committed: &Path, live: &Path) -> i32 {
    let read = |p: &Path| -> Result<Value, String> {
        let t = std::fs::read_to_string(p).map_err(|e| format!("{}: {e}", p.display()))?;
        serde_json::from_str(&t).map_err(|e| format!("{}: {e}", p.display()))
    };
    let (a, b) = match (read(committed), read(live)) {
        (Ok(a), Ok(b)) => (snapshot_key(&a), snapshot_key(&b)),
        (Err(e), _) | (_, Err(e)) => {
            eprintln!("north-star-measure: could not compare snapshots: {e}");
            return 2;
        }
    };
    if a == b {
        println!("snapshot matches: {b}");
        0
    } else {
        eprintln!("north-star-measure: snapshot is stale: committed {a}, live {b}. Commit the uploaded artifact.");
        1
    }
}

/// The nearest directory at or above `start` holding data/north-star.toml.
pub fn find_root(start: &Path) -> Option<PathBuf> {
    start.ancestors().find(|d| d.join("data").join("north-star.toml").is_file()).map(Path::to_path_buf)
}

/// The whole command: measure, write, check rule 7. Returns the exit code.
pub fn run(o: Objective, root: &Path, source: Source, cosign: Option<PathBuf>, rules: Rules) -> i32 {
    let tag = format!("north-star-measure {}", o.id());
    let Some(cosign) = cosign else {
        eprintln!("{tag}: could not measure: cosign not found (set COSIGN or put it on PATH); signatures are never skipped");
        return 2;
    };
    let env = Env { root: root.to_path_buf(), source, cosign, rules };
    let doc = match measure(o, &env) {
        Err(e) => {
            eprintln!("{tag}: could not measure: {e}");
            return 2;
        }
        Ok(Outcome::Unmeasured(why, skipped)) => {
            for s in &skipped {
                eprintln!("  not counted: {} {}: {}", s["product"].as_str().unwrap_or(""), s["release"].as_str().unwrap_or("-"), s["reason"].as_str().unwrap_or(""));
            }
            eprintln!("{tag}: could not measure: {why}. Nothing written; {} stays unmeasured, never 0.", o.id());
            return 2;
        }
        Ok(Outcome::Measured(doc)) => doc,
    };
    let out = root.join("data").join("north-star").join(format!("{}.json", o.id()));
    let text = serde_json::to_string_pretty(&doc).expect("serialisable") + "\n";
    if let Err(e) = std::fs::create_dir_all(out.parent().expect("has parent")).and_then(|_| std::fs::write(&out, text)) {
        eprintln!("{tag}: could not write {}: {e}", out.display());
        return 2;
    }
    let (value, of) = (doc["value"].as_u64().unwrap_or(0), doc["of"].as_u64().unwrap_or(0));
    for i in doc["items"].as_array().into_iter().flatten() {
        let v = i.get("verdict").or_else(|| i.get("counts")).map(|v| v.to_string()).unwrap_or_default();
        println!("  {}  {}", i["label"].as_str().unwrap_or(""), v);
    }
    for s in doc["not_counted"].as_array().into_iter().flatten() {
        println!("  not counted: {} {}: {}", s["product"].as_str().unwrap_or(""), s["release"].as_str().unwrap_or("-"), s["reason"].as_str().unwrap_or(""));
    }
    println!("{}: {value} of {of}", o.id());
    if value > of {
        eprintln!("{tag}: rule broke: value {value} exceeds of {of}");
        return 1;
    }
    let state = std::fs::read_to_string(root.join("data").join("north-star.toml"))
        .ok()
        .and_then(|t| products_pulling(&t, o.id()).ok())
        .and_then(|(_, s)| s);
    if state.as_deref() != Some("measured") {
        eprintln!(
            "{tag}: rule 7 broke: wrote data/north-star/{}.json but data/north-star.toml has state {:?}; set state = \"measured\" in the same PR",
            o.id(),
            state.unwrap_or_default()
        );
        return 1;
    }
    0
}
