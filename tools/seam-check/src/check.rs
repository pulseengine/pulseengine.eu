//! The rules, the driver and the output of seam-check.py, ported line by line.
//! Function names follow the Python ones so the two can be read side by side.

use crate::pyval::{iter_or_empty, py_str, repr, Crash, V};
use crate::text::{self, is_repo, is_seam_id};
use crate::transport::Source;

pub const SCHEMA: &str = "seam-check.v1";
const BLOCK_FORMAT: i128 = 1;
const KINDS: [&str; 5] = ["hal", "consumption", "wire", "identity", "other"];
const STATUSES: [&str; 5] = ["proposed", "options", "decided", "implemented", "broken"];
const DECIDED: [&str; 2] = ["decided", "implemented"];
const IFACE_KINDS: [&str; 2] = ["wit", "file"];

#[derive(Clone, Copy, PartialEq)]
enum Ty {
    Str,
    Int,
    Map,
    List,
    MapOrList,
    StrOrList,
}

impl Ty {
    fn name(self) -> &'static str {
        match self {
            Ty::Str => "str",
            Ty::Int => "int",
            Ty::Map => "dict",
            Ty::List => "list",
            Ty::MapOrList => "map|list",
            Ty::StrOrList => "str|list",
        }
    }
}

type Spec = &'static [(&'static str, bool, Ty)];

const TOP: Spec = &[
    ("format", true, Ty::Int), ("seam", true, Ty::Str), ("kind", true, Ty::Str), ("status", true, Ty::Str),
    ("provider", true, Ty::Map), ("consumers", true, Ty::List), ("interface", true, Ty::MapOrList),
    ("options", false, Ty::List), ("recommendation", false, Ty::Str), ("decisions", false, Ty::List),
    ("implemented_by", false, Ty::Str), ("open_questions", false, Ty::List), ("notes", false, Ty::Str),
];
const PROVIDER: Spec = &[("repo", true, Ty::Str), ("promise", true, Ty::Str), ("guard", false, Ty::StrOrList)];
const CONSUMER: Spec = &[("repo", true, Ty::Str), ("binding", true, Ty::Str), ("guard", false, Ty::StrOrList)];
const IFACE: Spec = &[
    ("kind", true, Ty::Str), ("path", true, Ty::Str), ("repo", false, Ty::Str), ("ref", false, Ty::Str),
    ("package", false, Ty::Str), ("version", false, Ty::Str), ("interfaces", false, Ty::List),
    ("symbols", false, Ty::List),
];
const OPTION: Spec = &[("id", true, Ty::Str), ("summary", true, Ty::Str)];
const DECISION: Spec = &[
    ("summary", true, Ty::Str), ("option", false, Ty::Str), ("decided_by", true, Ty::Str),
    ("date", true, Ty::Str), ("ref", false, Ty::Str),
];
const QUESTION: Spec = &[("q", true, Ty::Str), ("owner", true, Ty::Str), ("ref", false, Ty::Str)];

/// Why a run could not finish the way a pass or fail does.
#[derive(Debug)]
pub enum Fail {
    /// The evidence could not be reached: exit 2, never a pass.
    Infra(String),
    /// Python would die with a traceback here.
    Crash(String),
}

impl From<Crash> for Fail {
    fn from(c: Crash) -> Fail {
        Fail::Crash(c.0)
    }
}

pub type Finding = (String, String);

fn f(rule: &str, msg: String) -> Finding {
    (rule.to_string(), msg)
}

// ── dates ───────────────────────────────────────────────────────────────────

/// A proleptic Gregorian date as a day number (datetime.date.toordinal - 1).
#[derive(Clone, Copy, PartialEq, PartialOrd, Debug)]
pub struct Date(pub i64);

fn days_from_civil(y: i64, m: i64, d: i64) -> i64 {
    let y = if m <= 2 { y - 1 } else { y };
    let era = y.div_euclid(400);
    let yoe = y - era * 400;
    let mp = (m + 9) % 12;
    let doy = (153 * mp + 2) / 5 + d - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146097 + doe - 719468
}

fn civil_from_days(z: i64) -> (i64, i64, i64) {
    let z = z + 719468;
    let era = z.div_euclid(146097);
    let doe = z - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    (if m <= 2 { y + 1 } else { y }, m, d)
}

impl Date {
    pub fn iso(self) -> String {
        let (y, m, d) = civil_from_days(self.0);
        format!("{:04}-{:02}-{:02}", y, m, d)
    }

    pub fn today_utc() -> Date {
        let secs = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs() as i64)
            .unwrap_or(0);
        Date(secs.div_euclid(86400))
    }
}

/// `_date`: DATE.match and date.fromisoformat, else None.
pub fn parse_date(s: &str) -> Option<Date> {
    let b = s.as_bytes();
    if b.len() != 10 || b[4] != b'-' || b[7] != b'-' {
        return None;
    }
    let num = |r: std::ops::Range<usize>| -> Option<i64> {
        let t = &s[r];
        if t.bytes().all(|c| c.is_ascii_digit()) {
            t.parse().ok()
        } else {
            None
        }
    };
    let (y, m, d) = (num(0..4)?, num(5..7)?, num(8..10)?);
    if !(1..=9999).contains(&y) || !(1..=12).contains(&m) || d < 1 {
        return None;
    }
    let leap = (y % 4 == 0 && y % 100 != 0) || y % 400 == 0;
    let dim = [31, if leap { 29 } else { 28 }, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][(m - 1) as usize];
    if d > dim {
        return None;
    }
    Some(Date(days_from_civil(y, m, d)))
}

fn date_of(v: &V) -> Option<Date> {
    v.as_str().and_then(parse_date)
}

// ── strict YAML ─────────────────────────────────────────────────────────────

fn from_yaml(v: rivet_yaml::Value) -> Result<V, String> {
    use rivet_yaml::Value as Y;
    Ok(match v {
        Y::Null => V::None,
        Y::Bool(b) => V::Bool(b),
        Y::Number(n) => {
            if let Some(u) = n.as_u64() {
                V::Int(u as i128)
            } else if let Some(i) = n.as_i64() {
                V::Int(i as i128)
            } else {
                V::Float(n.as_f64().unwrap_or(f64::NAN))
            }
        }
        Y::String(s) => V::Str(s),
        Y::Sequence(seq) => V::List(seq.into_iter().map(from_yaml).collect::<Result<_, _>>()?),
        Y::Mapping(m) => {
            let mut out = vec![];
            for (k, v) in m {
                out.push((from_yaml(k)?, from_yaml(v)?));
            }
            V::Dict(out)
        }
        Y::Tagged(_) => return Err("tags are not supported".into()),
    })
}

/// `parse_block`: (data, error); data is None when the block is not a mapping.
pub fn parse_block(text: &str) -> Result<V, String> {
    let parsed: Result<Option<rivet_yaml::Value>, _> = rivet_yaml::from_str(text);
    let v = match parsed {
        Ok(Some(v)) => from_yaml(v),
        Ok(None) => Ok(V::None),
        Err(e) => Err(e.to_string()),
    };
    match v {
        Err(e) => Err(format!("block is not valid YAML: {}", e.replace('\n', " "))),
        Ok(v @ V::Dict(_)) => Ok(v),
        Ok(_) => Err("block must be a YAML mapping".into()),
    }
}

// ── rules ───────────────────────────────────────────────────────────────────

/// `_shape`: required keys, types, unknown keys.
fn shape(obj: Option<&V>, spec: Spec, at: &str, out: &mut Vec<Finding>, missing: &[(&str, &str)]) -> bool {
    let Some(V::Dict(d)) = obj else {
        out.push(f("required", format!("{} must be a mapping", at)));
        return false;
    };
    for (k, _) in d {
        if !spec.iter().any(|(name, _, _)| k.as_str() == Some(name)) {
            out.push(f("unknown-key", format!("{}: unknown key {} (strict schema)", at, repr(k))));
        }
    }
    let obj = obj.unwrap_or(&V::None);
    let mut ok = true;
    for (k, req, ty) in spec {
        let v = obj.get(k);
        let absent = match v {
            None | Some(V::None) => true,
            Some(V::Str(s)) => s.is_empty(),
            _ => false,
        };
        if absent {
            if *req {
                let rule = missing.iter().find(|(m, _)| m == k).map(|(_, r)| *r).unwrap_or("required");
                out.push(f(rule, format!("{}: missing required field {}", at, repr(&V::s(k)))));
                ok = false;
            }
            continue;
        }
        let v = v.unwrap_or(&V::None);
        let good = match ty {
            Ty::Str => matches!(v, V::Str(_)),
            Ty::Int => matches!(v, V::Int(_)),
            Ty::Map => v.is_dict(),
            Ty::List => v.is_list(),
            Ty::MapOrList => v.is_dict() || v.is_list(),
            Ty::StrOrList => match v {
                V::Str(_) => true,
                V::List(l) => !l.is_empty() && l.iter().all(|x| matches!(x, V::Str(s) if !s.is_empty())),
                _ => false,
            },
        };
        if !good {
            let hint = if *ty == Ty::Str { " (quote it)" } else { "" };
            out.push(f("required", format!("{}.{} must be {}, got {}{}", at, k, ty.name(), v.type_name(), hint)));
            ok = false;
        }
    }
    ok
}

/// `ifaces if list else [ifaces] if ifaces else []`
fn iface_list(d: &V) -> Vec<V> {
    match d.get("interface") {
        Some(V::List(l)) => l.clone(),
        Some(v) if v.truthy() => vec![v.clone()],
        _ => vec![],
    }
}

fn str_in(v: &V, set: &[&str]) -> bool {
    v.as_str().is_some_and(|s| set.contains(&s))
}

/// `check_block`: (violations, warnings).
pub fn check_block(d: &V, now: Date, stale_days: i128) -> Result<(Vec<Finding>, Vec<Finding>), Crash> {
    let mut v: Vec<Finding> = vec![];
    let mut w: Vec<Finding> = vec![];
    shape(Some(d), TOP, "seam", &mut v, &[]);
    match d.get("format") {
        Some(V::Int(i)) if *i != BLOCK_FORMAT => {
            v.push(f("enum", format!("format must be {}, got {}", BLOCK_FORMAT, i)));
        }
        Some(V::Bool(false)) => v.push(f("enum", format!("format must be {}, got False", BLOCK_FORMAT))),
        _ => {}
    }
    if let Some(V::Str(sid)) = d.get("seam") {
        if !is_seam_id(sid) {
            v.push(f("required", format!("seam id {} must match {}", repr(&V::s(sid)), text::SEAM_ID_PATTERN)));
        }
    }
    if let Some(V::Str(k)) = d.get("kind") {
        if !KINDS.contains(&k.as_str()) {
            v.push(f("enum", format!("kind {} is not one of {}", repr(&V::s(k)), KINDS.join("/"))));
        }
    }
    let status = d.get("status").cloned().unwrap_or(V::None);
    if let V::Str(s) = &status {
        if !STATUSES.contains(&s.as_str()) {
            v.push(f("enum", format!("status {} is not one of {}", repr(&status), STATUSES.join("/"))));
        }
    }

    // Both sides name an owner repo.
    let mut parties: Vec<String> = vec![];
    let add_party = |p: &str, parties: &mut Vec<String>| {
        if !parties.iter().any(|x| x == p) {
            parties.push(p.to_string());
        }
    };
    let prov = d.get("provider");
    if shape(prov, PROVIDER, "provider", &mut v, &[("repo", "owner")]) {
        if let Some(V::Str(r)) = prov.and_then(|p| p.get("repo")) {
            if !is_repo(r) {
                v.push(f("owner", format!("provider.repo {} is not OWNER/REPO", repr(&V::s(r)))));
            }
            add_party(r, &mut parties);
        }
    }
    if let Some(V::List(cons)) = d.get("consumers") {
        if cons.is_empty() {
            v.push(f("owner", "consumers is empty: a seam needs at least one consumer".into()));
        }
        for (n, c) in cons.iter().enumerate() {
            let at = format!("consumers[{}]", n);
            if shape(Some(c), CONSUMER, &at, &mut v, &[("repo", "owner")]) {
                if let Some(V::Str(r)) = c.get("repo") {
                    if !is_repo(r) {
                        v.push(f("owner", format!("consumers[{}].repo {} is not OWNER/REPO", n, repr(&V::s(r)))));
                    }
                    if let Some(p @ V::Dict(_)) = prov {
                        if p.get("repo").is_some_and(|pr| pr.as_str() == Some(r)) {
                            v.push(f("owner", format!("consumers[{}].repo is the provider: a seam has two sides", n)));
                        }
                    }
                    add_party(r, &mut parties);
                }
            }
        }
    }

    // Interface entries: shape only here; resolution needs the transport.
    for (n, it) in iface_list(d).iter().enumerate() {
        let at = format!("interface[{}]", n);
        if !shape(Some(it), IFACE, &at, &mut v, &[]) {
            continue;
        }
        let k = it.get("kind").and_then(|k| k.as_str()).unwrap_or("");
        if !IFACE_KINDS.contains(&k) {
            v.push(f("enum", format!("{}.kind {} is not one of {}", at, repr(&V::s(k)), IFACE_KINDS.join("/"))));
        } else if k == "wit" && !(it.get_or("package").is_some() && it.get_or("version").is_some()) {
            v.push(f("required", format!("{}: a wit interface needs package and version", at)));
        } else if k == "file" && it.get_or("symbols").is_none() {
            v.push(f("required", format!("{}: a file interface needs symbols (literal text that must appear)", at)));
        }
        for key in ["interfaces", "symbols"] {
            if let Some(V::List(l)) = it.get(key) {
                if !l.iter().all(|s| matches!(s, V::Str(x) if !x.is_empty())) {
                    v.push(f("required", format!("{}.{} must be a list of non-empty strings", at, key)));
                }
            }
        }
    }

    // Every open question has an owner, and the owner is a side of this seam.
    for (n, q) in iter_or_empty(d.get("open_questions"))?.iter().enumerate() {
        let at = format!("open_questions[{}]", n);
        if shape(Some(q), QUESTION, &at, &mut v, &[]) {
            let owner = q.get("owner").and_then(|o| o.as_str()).unwrap_or("");
            if !parties.iter().any(|p| p == owner) {
                let mut sorted = parties.clone();
                sorted.sort();
                let list = if sorted.is_empty() { "none".to_string() } else { sorted.join(", ") };
                v.push(f(
                    "question-owner",
                    format!("open_questions[{}].owner {} is not a party to this seam ({})", n, repr(&V::s(owner)), list),
                ));
            }
        } else if q.is_dict() && q.get_or("owner").is_none() {
            v.push(f("question-owner", format!("open_questions[{}] has no owner", n)));
        }
    }

    let mut option_ids: Vec<String> = vec![];
    for (n, o) in iter_or_empty(d.get("options"))?.iter().enumerate() {
        if shape(Some(o), OPTION, &format!("options[{}]", n), &mut v, &[]) {
            option_ids.push(o.get("id").and_then(|x| x.as_str()).unwrap_or("").to_string());
        }
    }
    let is_option = |x: &V| x.as_str().is_some_and(|s| option_ids.iter().any(|o| o == s));
    if status.as_str() == Some("options") {
        if option_ids.len() < 2 {
            v.push(f("options", format!("status options needs at least two options, has {}", option_ids.len())));
        }
        match d.get_or("recommendation") {
            None => v.push(f("options", "status options needs a recommendation naming one option".into())),
            Some(rec) if !is_option(rec) => v.push(f(
                "options",
                format!("recommendation {} is not an option id ({})", repr(rec), option_ids.join(", ")),
            )),
            Some(_) => {}
        }
    }

    // Decided means a decision with who and when.
    let decisions_truthy = d.get_or("decisions").is_some();
    let mut latest: Option<Date> = None;
    for (n, dec) in iter_or_empty(d.get("decisions"))?.iter().enumerate() {
        let at = format!("decisions[{}]", n);
        if !shape(Some(dec), DECISION, &at, &mut v, &[("date", "decision"), ("decided_by", "decision")]) {
            continue;
        }
        let date = dec.get("date").cloned().unwrap_or(V::None);
        match date_of(&date) {
            None => v.push(f("decision", format!("decisions[{}].date {} is not YYYY-MM-DD", n, repr(&date)))),
            Some(day) if day > now => {
                v.push(f("decision", format!("decisions[{}].date {} is in the future", n, py_str(&date))))
            }
            Some(day) => {
                if latest.is_none_or(|l| day > l) {
                    latest = Some(day);
                }
            }
        }
        if let Some(opt) = dec.get_or("option") {
            if !option_ids.is_empty() && !is_option(opt) {
                v.push(f(
                    "decision",
                    format!("decisions[{}].option {} is not an option id ({})", n, repr(opt), option_ids.join(", ")),
                ));
            }
        }
    }
    if str_in(&status, &DECIDED) && !decisions_truthy {
        v.push(f("decision", format!("status {} needs at least one entry in decisions", py_str(&status))));
    }
    if status.as_str() == Some("implemented") && d.get_or("implemented_by").is_none() {
        v.push(f("implemented", "status implemented needs implemented_by (the PR or release that landed it)".into()));
    }
    if status.as_str() == Some("broken") {
        v.push(f("broken", "the seam is marked broken: the provider and consumers must settle it".into()));
    }
    if let (Some("decided"), Some(l)) = (status.as_str(), latest) {
        let days = (now.0 - l.0) as i128;
        if days > stale_days {
            w.push(f(
                "stale",
                format!("decided {}, {} days ago, and not implemented (threshold {} days)", l.iso(), days, stale_days),
            ));
        }
    }
    Ok((v, w))
}

/// `resolve`: interface and guard resolution against the repos.
pub fn resolve(d: &V, src: &mut dyn Source) -> Result<(Vec<Finding>, Vec<V>), Fail> {
    let mut v: Vec<Finding> = vec![];
    let mut resolved: Vec<V> = vec![];
    let prov = match d.get("provider") {
        Some(p @ V::Dict(_)) => p.get("repo").cloned().unwrap_or(V::None),
        _ => V::None,
    };
    for (n, it) in iface_list(d).iter().enumerate() {
        if !it.is_dict() || !it.get("kind").is_some_and(|k| str_in(k, &IFACE_KINDS)) {
            continue;
        }
        let Some(V::Str(path)) = it.get("path") else { continue };
        let repo = it.get_or("repo").cloned().unwrap_or_else(|| prov.clone());
        let repo = match repo {
            V::Str(r) if is_repo(&r) => r,
            _ => continue,
        };
        let refv = match it.get_or("ref") {
            Some(r) => r.clone(),
            None => src.default_branch(&repo)?,
        };
        let at = format!("interface[{}] {}:{}@{}", n, repo, path, py_str(&refv));
        let text = src.read_file(&repo, path, &refv)?;
        let mut rec = V::Dict(vec![
            (V::s("repo"), V::s(&repo)),
            (V::s("path"), V::s(path)),
            (V::s("ref"), refv.clone()),
            (V::s("found"), V::Bool(text.is_some())),
        ]);
        let Some(text) = text else {
            resolved.push(rec);
            v.push(f("interface-missing", format!("{} does not exist", at)));
            continue;
        };
        let kind = it.get("kind").and_then(|k| k.as_str()).unwrap_or("");
        if kind == "wit" && it.get_or("package").is_some() && it.get_or("version").is_some() {
            let package = it.get("package").cloned().unwrap_or(V::None);
            let version = it.get("version").cloned().unwrap_or(V::None);
            match text::wit_package(&text) {
                None => v.push(f("interface-version", format!("{} has no `package name@version;` line", at))),
                Some((pkg, ver)) => {
                    rec.set("found_package", V::s(&pkg));
                    rec.set("found_version", V::s(&ver));
                    if package.as_str() != Some(pkg.as_str()) {
                        v.push(f(
                            "interface-version",
                            format!("{} declares package {}, the block says {}", at, pkg, py_str(&package)),
                        ));
                    }
                    if ver != py_str(&version) {
                        v.push(f(
                            "interface-version",
                            format!(
                                "{} is at @{}, the block says @{}: update the block (or pin ref:) and tell the consumers",
                                at,
                                ver,
                                py_str(&version)
                            ),
                        ));
                    }
                }
            }
            for name in iter_or_empty(it.get("interfaces"))? {
                if let V::Str(name) = name {
                    if !text::declares_interface(&text, &name) {
                        v.push(f("interface-symbol", format!("{} declares no `interface {}`", at, name)));
                    }
                }
            }
        }
        resolved.push(rec);
        for sym in iter_or_empty(it.get("symbols"))? {
            if let V::Str(sym) = sym {
                if !sym.is_empty() && !text.contains(&sym) {
                    v.push(f("interface-symbol", format!("{} does not contain {}", at, repr(&V::s(&sym)))));
                }
            }
        }
    }
    let mut sides: Vec<(String, V)> = vec![("provider".into(), d.get("provider").cloned().unwrap_or(V::None))];
    for (n, c) in iter_or_empty(d.get("consumers"))?.into_iter().enumerate() {
        sides.push((format!("consumers[{}]", n), c));
    }
    for (at, side) in sides {
        let Some(V::Str(repo)) = side.get("repo") else { continue };
        if !side.is_dict() || !is_repo(repo) {
            continue;
        }
        let guards = match side.get("guard") {
            Some(g @ V::Str(_)) => vec![g.clone()],
            Some(V::List(l)) => l.clone(),
            _ => vec![],
        };
        for g in guards {
            let V::Str(g) = g else { continue };
            if g.is_empty() {
                continue;
            }
            let refv = src.default_branch(repo)?;
            if src.read_file(repo, &g, &refv)?.is_none() {
                v.push(f(
                    "guard-missing",
                    format!("{}.guard {}:{}@{} does not exist", at, repo, g, py_str(&refv)),
                ));
            }
        }
    }
    Ok((v, resolved))
}

// ── driver ──────────────────────────────────────────────────────────────────

fn body_text(v: Option<&V>) -> Result<String, Crash> {
    match v {
        None => Ok(String::new()),
        Some(x) if !x.truthy() => Ok(String::new()),
        Some(V::Str(s)) => Ok(s.clone()),
        Some(other) => Err(Crash(format!("TypeError: expected string, got {}", other.type_name()))),
    }
}

/// `collect`: blocks per issue (body canonical, else the newest comment with one).
pub fn collect(issues: &[V]) -> Result<(Vec<(String, V)>, Vec<V>), Crash> {
    let mut blocks = vec![];
    let mut empty = vec![];
    for i in issues {
        let repo = i.get("repo").cloned().unwrap_or(V::None);
        let number = i.get("number").cloned().unwrap_or(V::None);
        let url = i.get("url").cloned().unwrap_or(V::s(""));
        let mut src = V::Dict(vec![
            (V::s("repo"), repo.clone()),
            (V::s("issue"), number.clone()),
            (V::s("url"), url.clone()),
            (V::s("in"), V::s("body")),
        ]);
        let mut texts = text::blocks_in(&body_text(i.get("body"))?);
        if texts.is_empty() {
            let mut comments: Vec<V> = match i.get("comments") {
                Some(V::List(l)) => l.clone(),
                _ => vec![],
            };
            let key = |c: &V| {
                (
                    c.get("created_at").map(py_str).unwrap_or_default(),
                    c.get("id").map(py_str).unwrap_or_else(|| "None".into()),
                )
            };
            comments.sort_by(|a, b| key(b).cmp(&key(a)));
            for c in &comments {
                texts = text::blocks_in(&body_text(c.get("body"))?);
                if !texts.is_empty() {
                    src.set("in", V::s("comment"));
                    src.set("comment_id", c.get("id").cloned().unwrap_or(V::None));
                    let curl = c.get_or("url").cloned().unwrap_or_else(|| url.clone());
                    src.set("url", curl);
                    break;
                }
            }
        }
        if texts.is_empty() {
            empty.push(V::Dict(vec![
                (V::s("repo"), repo.clone()),
                (V::s("issue"), number.clone()),
                (V::s("url"), url.clone()),
            ]));
        }
        for t in texts {
            blocks.push((t, src.clone()));
        }
    }
    Ok((blocks, empty))
}

pub struct Args {
    pub org: String,
    pub label: String,
    pub issue: Vec<String>,
    pub block: Vec<String>,
    pub party: Vec<String>,
    pub fixtures: Option<String>,
    pub api: String,
    pub http: String,
    pub format: String,
    pub stale_days: i128,
    pub strict: bool,
    pub now: Option<String>,
}

fn finding(rule: &str, msg: &str) -> V {
    V::Dict(vec![(V::s("rule"), V::s(rule)), (V::s("message"), V::s(msg))])
}

fn push(list: &mut V, item: V) {
    if let V::List(l) = list {
        l.push(item);
    }
}

fn list_len(v: Option<&V>) -> usize {
    match v {
        Some(V::List(l)) => l.len(),
        _ => 0,
    }
}

/// Python's str(OSError) for a failed open: `[Errno 2] No such file or directory: 'path'`.
pub fn os_error(e: &std::io::Error, path: &str) -> String {
    match e.raw_os_error() {
        Some(code) => {
            let text = e.to_string();
            let text = match text.rfind(" (os error ") {
                Some(i) => text[..i].to_string(),
                None => text,
            };
            format!("[Errno {}] {}: {}", code, text, repr(&V::s(path)))
        }
        None => e.to_string(),
    }
}

/// The body of `run` after argument parsing: returns the report.
pub fn check(a: &Args, now: Date, report: &mut V, make_src: &mut dyn FnMut() -> Result<Box<dyn Source>, Fail>) -> Result<i32, Fail> {
    let mut src = make_src()?;
    report.set("source", V::s(&src.name()));
    let mut issues: Vec<V> = vec![];
    for spec in &a.issue {
        let Some((repo, num)) = text::issue_spec(spec) else {
            eprintln!("error: --issue wants OWNER/REPO#N, got {}", repr(&V::s(spec)));
            return Ok(-2);
        };
        issues.push(src.issue(&repo, num)?);
    }
    for path in &a.block {
        let raw = std::fs::read(path).map_err(|e| Fail::Infra(format!("cannot read block file {}: {}", path, os_error(&e, path))))?;
        let text = String::from_utf8(raw).map_err(|_| Crash("UnicodeDecodeError".into()))?;
        let body = if !text::blocks_in(&text).is_empty() {
            text
        } else if text.ends_with('\n') {
            format!("```seam\n{}```\n", text)
        } else {
            format!("```seam\n{}\n```\n", text)
        };
        issues.push(V::Dict(vec![
            (V::s("repo"), V::s("local")),
            (V::s("number"), V::Int(0)),
            (V::s("url"), V::s(path)),
            (V::s("labels"), V::List(vec![])),
            (V::s("body"), V::Str(body)),
            (V::s("comments"), V::List(vec![])),
        ]));
    }
    if a.issue.is_empty() && a.block.is_empty() {
        issues = src.discover(&a.org, &a.label)?;
    }
    let (blocks, empty) = collect(&issues)?;
    report.set("issues_without_block", V::List(empty.clone()));

    // seam id -> indices into report.seams
    let mut seen: Vec<(String, Vec<usize>)> = vec![];
    for (btext, bsrc) in blocks {
        let parsed = parse_block(&btext);
        let mut entry = V::Dict(vec![
            (V::s("id"), V::None),
            (V::s("source"), bsrc.clone()),
            (V::s("violations"), V::List(vec![])),
            (V::s("warnings"), V::List(vec![])),
        ]);
        let mut sid: Option<String> = None;
        match &parsed {
            Err(err) => push(entry.get_mut("violations").unwrap_or(&mut V::None), finding("parse", err)),
            Ok(data) => {
                if let Some(V::Str(s)) = data.get("seam") {
                    entry.set("id", V::s(s));
                }
                for key in ["kind", "status", "provider", "consumers", "interface", "open_questions", "decisions", "implemented_by"] {
                    if let Some(x) = data.get(key) {
                        entry.set(key, x.clone());
                    }
                }
                // {provider.get("repo") if provider is a dict else None} | {c.get("repo") ...}
                let mut parties: Vec<V> = vec![match data.get("provider") {
                    Some(p @ V::Dict(_)) => p.get("repo").cloned().unwrap_or(V::None),
                    _ => V::None,
                }];
                for c in iter_or_empty(data.get("consumers"))? {
                    if c.is_dict() {
                        parties.push(c.get("repo").cloned().unwrap_or(V::None));
                    }
                }
                if let Some(bad) = parties.iter().find(|p| !p.hashable()) {
                    return Err(Fail::Crash(format!("TypeError: unhashable type: '{}'", bad.type_name())));
                }
                if !a.party.is_empty() && !parties.iter().any(|p| p.as_str().is_some_and(|s| a.party.iter().any(|x| x == s))) {
                    continue;
                }
                let (vio, warn) = check_block(data, now, a.stale_days)?;
                let (rv, resolved) = resolve(data, &mut *src)?;
                entry.set("resolved", V::List(resolved));
                for (r, m) in vio.iter().chain(rv.iter()) {
                    push(entry.get_mut("violations").unwrap_or(&mut V::None), finding(r, m));
                }
                for (r, m) in &warn {
                    push(entry.get_mut("warnings").unwrap_or(&mut V::None), finding(r, m));
                }
                if let Some(V::Str(s)) = entry.get("id") {
                    if !s.is_empty() {
                        sid = Some(s.clone());
                    }
                }
            }
        }
        if !a.party.is_empty() && parsed.is_err() {
            let srepo = bsrc.get("repo").and_then(|r| r.as_str()).unwrap_or("");
            if !a.party.iter().any(|p| p == srepo) {
                continue;
            }
        }
        let idx = list_len(report.get("seams"));
        if let Some(seams) = report.get_mut("seams") {
            push(seams, entry);
        }
        if let Some(s) = sid {
            match seen.iter_mut().find(|(k, _)| *k == s) {
                Some((_, l)) => l.push(idx),
                None => seen.push((s, vec![idx])),
            }
        }
    }
    for (sid, idxs) in &seen {
        if idxs.len() < 2 {
            continue;
        }
        let seams = report.get("seams").cloned().unwrap_or(V::List(vec![]));
        let V::List(list) = seams else { continue };
        let at = idxs
            .iter()
            .map(|i| {
                let s = list[*i].get("source").cloned().unwrap_or(V::None);
                format!(
                    "{}#{}",
                    py_str(s.get("repo").unwrap_or(&V::None)),
                    py_str(s.get("issue").unwrap_or(&V::None))
                )
            })
            .collect::<Vec<_>>()
            .join(", ");
        let msg = format!("seam id {} appears {} times ({})", repr(&V::s(sid)), idxs.len(), at);
        if let Some(V::List(l)) = report.get_mut("seams") {
            for i in idxs {
                push(l[*i].get_mut("violations").unwrap_or(&mut V::None), finding("duplicate-id", &msg));
            }
        }
    }
    if a.party.is_empty() {
        for e in empty {
            let mut s = e.clone();
            s.set("in", V::s("issue"));
            let entry = V::Dict(vec![
                (V::s("id"), V::None),
                (V::s("source"), s),
                (V::s("warnings"), V::List(vec![])),
                (
                    V::s("violations"),
                    V::List(vec![finding("no-block", "issue carries no ```seam block in its body or comments")]),
                ),
            ]);
            push(report.get_mut("seams").unwrap_or(&mut V::None), entry);
        }
    }
    Ok(0)
}

/// `run` minus argument parsing: the report, the exit code, and the text or JSON.
pub fn run_args(a: &Args, out: &mut String, make_src: &mut dyn FnMut() -> Result<Box<dyn Source>, Fail>) -> Result<i32, Crash> {
    let now = match &a.now {
        Some(s) => match parse_date(s) {
            Some(d) => d,
            None => {
                eprintln!("error: --now must be YYYY-MM-DD");
                return Ok(2);
            }
        },
        None => Date::today_utc(),
    };
    let mut report = V::Dict(vec![
        (V::s("schema"), V::s(SCHEMA)),
        (V::s("now"), V::s(&now.iso())),
        (V::s("seams"), V::List(vec![])),
        (V::s("issues_without_block"), V::List(vec![])),
        (V::s("errors"), V::List(vec![])),
        (V::s("exit"), V::Int(2)),
    ]);
    match check(a, now, &mut report, make_src) {
        Ok(-2) => return Ok(2),
        Ok(_) => {}
        Err(Fail::Crash(c)) => return Err(Crash(c)),
        Err(Fail::Infra(e)) => {
            push(report.get_mut("errors").unwrap_or(&mut V::None), V::Str(e));
            report.set("exit", V::Int(2));
            emit(&report, &a.format, out);
            return Ok(2);
        }
    }
    let seams = match report.get("seams") {
        Some(V::List(l)) => l.clone(),
        _ => vec![],
    };
    if seams.is_empty() {
        push(
            report.get_mut("errors").unwrap_or(&mut V::None),
            V::s("no seam blocks found: nothing was checked, which is not a pass"),
        );
        report.set("exit", V::Int(1));
        emit(&report, &a.format, out);
        return Ok(1);
    }
    let failing = seams.iter().filter(|s| s.get_or("violations").is_some()).count();
    let warning = seams.iter().filter(|s| s.get_or("warnings").is_some()).count();
    let code = if failing > 0 || (a.strict && warning > 0) { 1 } else { 0 };
    report.set("exit", V::Int(code));
    report.set(
        "summary",
        V::Dict(vec![
            (V::s("seams"), V::Int(seams.len() as i128)),
            (V::s("failing"), V::Int(failing as i128)),
            (V::s("warning"), V::Int(warning as i128)),
        ]),
    );
    emit(&report, &a.format, out);
    Ok(code as i32)
}

/// `_emit`
pub fn emit(report: &V, fmt: &str, out: &mut String) {
    if fmt == "json" {
        out.push_str(&crate::pyval::json_dumps(report));
        out.push('\n');
        return;
    }
    let empty = vec![];
    let list = |v: Option<&V>| -> Vec<V> {
        match v {
            Some(V::List(l)) => l.clone(),
            _ => empty.clone(),
        }
    };
    for s in list(report.get("seams")) {
        let src = s.get("source").cloned().unwrap_or(V::None);
        let repo = src.get("repo").cloned().unwrap_or(V::None);
        let at = if repo.as_str() != Some("local") {
            format!("{}#{}", py_str(&repo), py_str(src.get("issue").unwrap_or(&V::None)))
        } else {
            py_str(src.get("url").unwrap_or(&V::None))
        };
        let vio = list(s.get("violations"));
        let warn = list(s.get("warnings"));
        let tag = if !vio.is_empty() { "FAIL" } else if !warn.is_empty() { "WARN" } else { "PASS" };
        let id = match s.get_or("id") {
            Some(x) => py_str(x),
            None => "<no id>".into(),
        };
        out.push_str(&format!("{}  {}  ({}, {})\n", tag, id, at, py_str(src.get("in").unwrap_or(&V::None))));
        for x in &vio {
            out.push_str(&format!(
                "      [{}] {}\n",
                py_str(x.get("rule").unwrap_or(&V::None)),
                py_str(x.get("message").unwrap_or(&V::None))
            ));
        }
        for x in &warn {
            out.push_str(&format!(
                "      warn [{}] {}\n",
                py_str(x.get("rule").unwrap_or(&V::None)),
                py_str(x.get("message").unwrap_or(&V::None))
            ));
        }
    }
    for e in list(report.get("errors")) {
        out.push_str(&format!("error: {}\n", py_str(&e)));
    }
    let exit = report.get("exit").map(py_str).unwrap_or_default();
    let source = report.get("source").map(py_str).unwrap_or_else(|| "?".into());
    out.push_str(&format!("seam-check: exit {} ({})\n", exit, source));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dates() {
        let d = parse_date("2026-10-29").unwrap();
        assert_eq!(d.iso(), "2026-10-29");
        assert_eq!(parse_date("2027-03-01").unwrap().0 - parse_date("2026-10-20").unwrap().0, 132);
        assert!(parse_date("2026-02-29").is_none() && parse_date("2024-02-29").is_some());
        assert!(parse_date("0000-01-01").is_none() && parse_date("20 Oct 2026").is_none());
    }
}
