//! Hand-written validation against data/north-star/input.schema.json,
//! schema_version 1. The schema is fixed per version (a change is a new
//! schema_version, announced on pulseengine.eu#393), so no general JSON-Schema
//! engine is needed. Two places are stricter than a default validator:
//! `generated_at` must be an RFC 3339 date-time (`format` is only an
//! annotation in JSON Schema 2020-12), and fact ids must be unique.

use serde_json::{Map, Value};

/// One fact of an input, after validation.
#[derive(Debug, Clone)]
pub struct Fact {
    pub id: String,
    pub ran: bool,
    pub pass: bool,
    pub control: Option<bool>,
    pub detail: Map<String, Value>,
    pub evidence: Option<String>,
}

/// A validated `north-star-input.<Ox>.json`.
#[derive(Debug, Clone)]
pub struct Input {
    pub objective: String,
    pub repo: String,
    pub version: String,
    pub facts: Vec<Fact>,
    pub not_measured: Vec<String>,
}

const TOP_REQUIRED: [&str; 8] = [
    "schema_version",
    "objective",
    "repo",
    "version",
    "generated_at",
    "generator",
    "facts",
    "not_measured",
];
const FACT_KEYS: [&str; 6] = ["id", "ran", "pass", "control_failed_as_expected", "detail", "evidence"];
const OBJECTIVES: [&str; 5] = ["O1", "O2", "O3", "O4", "O5"];

fn keys_exact(m: &Map<String, Value>, required: &[&str], allowed: &[&str], at: &str) -> Result<(), String> {
    for k in m.keys() {
        if !allowed.contains(&k.as_str()) {
            return Err(format!("{at}: property {k:?} is not allowed (additionalProperties: false)"));
        }
    }
    for k in required {
        if !m.contains_key(*k) {
            return Err(format!("{at}: required property {k:?} is missing"));
        }
    }
    Ok(())
}

fn string<'a>(m: &'a Map<String, Value>, k: &str, at: &str) -> Result<&'a str, String> {
    m.get(k).and_then(Value::as_str).ok_or_else(|| format!("{at}.{k}: must be a string"))
}

fn boolean(m: &Map<String, Value>, k: &str, at: &str) -> Result<bool, String> {
    m.get(k).and_then(Value::as_bool).ok_or_else(|| format!("{at}.{k}: must be a boolean"))
}

/// `^pulseengine/[A-Za-z0-9._-]+$`
pub fn repo_ok(s: &str) -> bool {
    match s.strip_prefix("pulseengine/") {
        Some(rest) => !rest.is_empty() && rest.chars().all(|c| c.is_ascii_alphanumeric() || "._-".contains(c)),
        None => false,
    }
}

/// `^v?[0-9]+\.[0-9]+\.[0-9]+([-+][0-9A-Za-z.-]+)?$`
pub fn version_ok(s: &str) -> bool {
    let s = s.strip_prefix('v').unwrap_or(s);
    let b = s.as_bytes();
    let mut i = 0;
    for part in 0..3 {
        let start = i;
        while i < b.len() && b[i].is_ascii_digit() {
            i += 1;
        }
        if i == start {
            return false;
        }
        if part < 2 {
            if i >= b.len() || b[i] != b'.' {
                return false;
            }
            i += 1;
        }
    }
    if i == b.len() {
        return true;
    }
    if b[i] != b'-' && b[i] != b'+' {
        return false;
    }
    let rest = &b[i + 1..];
    !rest.is_empty() && rest.iter().all(|c| c.is_ascii_alphanumeric() || *c == b'.' || *c == b'-')
}

/// RFC 3339 date-time: `YYYY-MM-DDTHH:MM:SS[.frac](Z|+HH:MM|-HH:MM)`.
pub fn date_time_ok(s: &str) -> bool {
    let b = s.as_bytes();
    let digits = |r: std::ops::Range<usize>| b.len() >= r.end && b[r.clone()].iter().all(u8::is_ascii_digit);
    let num = |r: std::ops::Range<usize>| -> u32 { std::str::from_utf8(&b[r]).ok().and_then(|x| x.parse().ok()).unwrap_or(999) };
    if b.len() < 20 || !digits(0..4) || b[4] != b'-' || !digits(5..7) || b[7] != b'-' || !digits(8..10) {
        return false;
    }
    if !matches!(b[10], b'T' | b't') || !digits(11..13) || b[13] != b':' || !digits(14..16) || b[16] != b':' || !digits(17..19) {
        return false;
    }
    let (mo, d, h, mi, se) = (num(5..7), num(8..10), num(11..13), num(14..16), num(17..19));
    if !(1..=12).contains(&mo) || !(1..=31).contains(&d) || h > 23 || mi > 59 || se > 60 {
        return false;
    }
    let mut i = 19;
    if b[i] == b'.' {
        let start = i + 1;
        i = start;
        while i < b.len() && b[i].is_ascii_digit() {
            i += 1;
        }
        if i == start {
            return false;
        }
    }
    match &b[i..] {
        [b'Z'] | [b'z'] => true,
        [sign, ..] if (*sign == b'+' || *sign == b'-') && b.len() == i + 6 => {
            digits(i + 1..i + 3) && b[i + 3] == b':' && digits(i + 4..i + 6) && num(i + 1..i + 3) <= 23 && num(i + 4..i + 6) <= 59
        }
        _ => false,
    }
}

/// Validate one input file against schema_version 1.
pub fn validate(text: &str) -> Result<Input, String> {
    let v: Value = serde_json::from_str(text).map_err(|e| format!("not JSON: {e}"))?;
    let top = v.as_object().ok_or("top level must be an object")?;
    let at = "$";
    keys_exact(top, &TOP_REQUIRED, &TOP_REQUIRED, at)?;
    if top["schema_version"].as_f64() != Some(1.0) {
        return Err("$.schema_version: must be 1".into());
    }
    let objective = string(top, "objective", at)?;
    if !OBJECTIVES.contains(&objective) {
        return Err(format!("$.objective: {objective:?} is not one of {OBJECTIVES:?}"));
    }
    let repo = string(top, "repo", at)?;
    if !repo_ok(repo) {
        return Err(format!("$.repo: {repo:?} does not match ^pulseengine/[A-Za-z0-9._-]+$"));
    }
    let version = string(top, "version", at)?;
    if !version_ok(version) {
        return Err(format!("$.version: {version:?} is not a version"));
    }
    let generated_at = string(top, "generated_at", at)?;
    if !date_time_ok(generated_at) {
        return Err(format!("$.generated_at: {generated_at:?} is not an RFC 3339 date-time"));
    }
    let gen = top["generator"].as_object().ok_or("$.generator: must be an object")?;
    keys_exact(gen, &["tool", "version"], &["tool", "version"], "$.generator")?;
    string(gen, "tool", "$.generator")?;
    string(gen, "version", "$.generator")?;

    let raw_facts = top["facts"].as_array().ok_or("$.facts: must be an array")?;
    let mut facts = Vec::with_capacity(raw_facts.len());
    for (i, f) in raw_facts.iter().enumerate() {
        let at = format!("$.facts[{i}]");
        let m = f.as_object().ok_or_else(|| format!("{at}: must be an object"))?;
        keys_exact(m, &["id", "ran", "pass"], &FACT_KEYS, &at)?;
        let id = string(m, "id", &at)?.to_string();
        if facts.iter().any(|x: &Fact| x.id == id) {
            return Err(format!("{at}.id: duplicate fact id {id:?}"));
        }
        let control = match m.get("control_failed_as_expected") {
            None => None,
            Some(Value::Bool(b)) => Some(*b),
            Some(_) => return Err(format!("{at}.control_failed_as_expected: must be a boolean")),
        };
        let detail = match m.get("detail") {
            None => Map::new(),
            Some(Value::Object(d)) => d.clone(),
            Some(_) => return Err(format!("{at}.detail: must be an object")),
        };
        let evidence = match m.get("evidence") {
            None => None,
            Some(Value::String(s)) => Some(s.clone()),
            Some(_) => return Err(format!("{at}.evidence: must be a string")),
        };
        facts.push(Fact { id, ran: boolean(m, "ran", &at)?, pass: boolean(m, "pass", &at)?, control, detail, evidence });
    }
    let nm = top["not_measured"].as_array().ok_or("$.not_measured: must be an array")?;
    let mut not_measured = Vec::new();
    for (i, s) in nm.iter().enumerate() {
        not_measured.push(s.as_str().ok_or_else(|| format!("$.not_measured[{i}]: must be a string"))?.to_string());
    }
    Ok(Input { objective: objective.into(), repo: repo.into(), version: version.into(), facts, not_measured })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn patterns() {
        assert!(version_ok("v0.7.3") && version_ok("1.2.3-rc.1") && version_ok("1.2.3+b.7"));
        assert!(!version_ok("1.2") && !version_ok("falcon-v1.2.3") && !version_ok("1.2.3-") && !version_ok("1.2.3 "));
        assert!(repo_ok("pulseengine/jess") && !repo_ok("pulseengine/") && !repo_ok("evil/jess") && !repo_ok("pulseengine/a/b"));
        assert!(date_time_ok("2026-11-20T06:37:00Z") && date_time_ok("2026-11-20T06:37:00.5+01:00"));
        assert!(!date_time_ok("2026-11-20") && !date_time_ok("2026-13-20T06:37:00Z") && !date_time_ok("2026-11-20T06:37:00"));
    }
}
