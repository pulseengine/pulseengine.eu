//! Strict parsing of ci-controls.toml. Any problem here is exit 2.

use std::collections::BTreeMap;
use std::path::Path;

use regex::Regex;
use toml::{Table, Value};

pub const DEFAULT_TIMEOUT: f64 = 300.0;

const KNOWN_KEYS: &[&str] = &[
    "id",
    "check",
    "run",
    "plant",
    "expect",
    "stderr_or_stdout_matches",
    "timeout",
    "baseline",
    "env",
];

#[derive(Debug)]
pub struct Control {
    pub id: String,
    pub check: String,
    pub run: String,
    pub plant: String,
    pub regex: Option<Regex>,
    pub timeout: f64,
    pub baseline: bool,
    pub env: BTreeMap<String, String>,
}

pub fn load(path: &Path) -> Result<Vec<Control>, String> {
    let text = std::fs::read_to_string(path)
        .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
    parse(&text).map_err(|e| format!("{}: {e}", path.display()))
}

pub fn parse(text: &str) -> Result<Vec<Control>, String> {
    let doc: Table = text.parse().map_err(|e| format!("cannot parse: {e}"))?;
    if let Some(k) = doc.keys().find(|k| *k != "control") {
        return Err(format!(
            "unknown top-level key `{k}` (only [[control]] tables are allowed)"
        ));
    }
    let items = match doc.get("control") {
        None => return Ok(Vec::new()),
        Some(Value::Array(a)) => a,
        Some(_) => return Err("`control` must be an array of tables ([[control]])".into()),
    };
    let mut out: Vec<Control> = Vec::new();
    for (i, item) in items.iter().enumerate() {
        let t = item
            .as_table()
            .ok_or_else(|| format!("control #{} is not a table", i + 1))?;
        let c = control(t, i)?;
        if out.iter().any(|o| o.id == c.id) {
            return Err(format!("control {:?}: duplicate id", c.id));
        }
        out.push(c);
    }
    Ok(out)
}

fn control(t: &Table, i: usize) -> Result<Control, String> {
    let where_ = match t.get("id") {
        Some(Value::String(s)) => format!("control {s:?}"),
        _ => format!("control #{}", i + 1),
    };
    let req = |k: &str| -> Result<String, String> {
        match t.get(k) {
            Some(Value::String(s)) if !s.trim().is_empty() => Ok(s.clone()),
            _ => Err(format!(
                "{where_}: `{k}` is missing or not a non-empty string"
            )),
        }
    };
    let id = req("id")?;
    let check = req("check")?;
    let run = req("run")?;
    let plant = req("plant")?;

    let mut unknown: Vec<&str> = t
        .keys()
        .map(String::as_str)
        .filter(|k| !KNOWN_KEYS.contains(k))
        .collect();
    unknown.sort_unstable();
    if !unknown.is_empty() {
        return Err(format!("{where_}: unknown key(s) {}", unknown.join(", ")));
    }

    match t.get("expect") {
        None => {}
        Some(Value::String(s)) if s == "fail" => {}
        Some(_) => {
            return Err(format!(
                "{where_}: `expect` must be \"fail\" (the only verdict)"
            ))
        }
    }

    let regex = match t.get("stderr_or_stdout_matches") {
        None => None,
        Some(Value::String(s)) if !s.is_empty() => {
            Some(Regex::new(s).map_err(|e| format!("{where_}: bad regex: {e}"))?)
        }
        Some(_) => {
            return Err(format!(
                "{where_}: `stderr_or_stdout_matches` must be a non-empty string"
            ))
        }
    };

    let timeout = match t.get("timeout") {
        None => DEFAULT_TIMEOUT,
        Some(Value::Integer(n)) if *n > 0 => *n as f64,
        Some(Value::Float(f)) if *f > 0.0 && std::time::Duration::try_from_secs_f64(*f).is_ok() => {
            *f
        }
        Some(_) => {
            return Err(format!(
                "{where_}: `timeout` must be a positive number of seconds"
            ))
        }
    };

    let baseline = match t.get("baseline") {
        None => true,
        Some(Value::Boolean(b)) => *b,
        Some(_) => return Err(format!("{where_}: `baseline` must be true or false")),
    };

    let mut env = BTreeMap::new();
    match t.get("env") {
        None => {}
        Some(Value::Table(e)) => {
            for (k, v) in e {
                match v {
                    Value::String(s) => {
                        env.insert(k.clone(), s.clone());
                    }
                    _ => return Err(format!("{where_}: `env` must be a table of strings")),
                }
            }
        }
        Some(_) => return Err(format!("{where_}: `env` must be a table of strings")),
    }

    Ok(Control {
        id,
        check,
        run,
        plant,
        regex,
        timeout,
        baseline,
        env,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    const MIN: &str = "[[control]]\nid = \"a\"\ncheck = \"c\"\nrun = \"true\"\nplant = \"p\"\n";

    // rivet: verifies REQ-003
    #[test]
    fn minimal_control_gets_defaults() {
        let c = &parse(MIN).unwrap()[0];
        assert_eq!(c.timeout, DEFAULT_TIMEOUT);
        assert!(c.baseline);
        assert!(c.regex.is_none());
    }

    // rivet: verifies REQ-003
    #[test]
    fn rejects_bad_manifests() {
        let cases = [
            (format!("{MIN}color = 1\n"), "unknown key"),
            (format!("{MIN}expect = \"pass\"\n"), "expect"),
            (format!("{MIN}timeout = 0\n"), "timeout"),
            (format!("{MIN}timeout = \"5\"\n"), "timeout"),
            (format!("{MIN}timeout = 1e300\n"), "timeout"),
            (format!("{MIN}timeout = nan\n"), "timeout"),
            (format!("{MIN}baseline = \"no\"\n"), "baseline"),
            (
                format!("{MIN}stderr_or_stdout_matches = \"(\"\n"),
                "bad regex",
            ),
            (format!("{MIN}[control.env]\nX = 1\n"), "env"),
            (format!("{MIN}{MIN}"), "duplicate id"),
            ("[[control]]\nid = \"a\"\n".to_string(), "`check`"),
            ("stray = 1\n".to_string(), "top-level"),
            ("control = 3\n".to_string(), "array of tables"),
        ];
        for (text, needle) in cases {
            let err = parse(&text).unwrap_err();
            assert!(err.contains(needle), "{needle:?} not in {err:?}");
        }
    }

    // rivet: verifies REQ-003
    #[test]
    fn accepts_full_control() {
        let text = format!(
            "{MIN}expect = \"fail\"\nstderr_or_stdout_matches = \"R7\"\n\
             timeout = 1.5\nbaseline = false\n[control.env]\nK = \"v\"\n"
        );
        let c = &parse(&text).unwrap()[0];
        assert_eq!(c.timeout, 1.5);
        assert!(!c.baseline);
        assert_eq!(c.env.get("K").map(String::as_str), Some("v"));
    }

    // rivet: verifies REQ-003
    #[test]
    fn empty_manifest_has_no_controls() {
        assert!(parse("# nothing\n").unwrap().is_empty());
    }
}
