//! The seven rules of scripts/check-north-star.py, statement for statement.
//! Keep the order of the checks: the output is compared line by line.

use crate::py::{Py, PyErr, str_repr, strip_nonempty};
use crate::pyjson::{self, J, int_cmp};
use crate::pyre;
use std::cmp::Ordering;
use std::path::Path;

const OBJECTIVE_FIELDS: [&str; 6] = ["id", "title", "summary", "indicator", "guard", "state"];
const STATES_SORTED: &str = "['measured', 'unmeasured']";
const KINDS_SORTED: &str = "['committed', 'stretch']";

/// `_measurement(oid, measure_dir)`: `None` when there is no file, an empty
/// object when the file is not valid UTF-8 JSON (Python's ValueError branch).
fn measurement(oid: &str, measure_dir: &Path) -> Option<J> {
    let p = measure_dir.join(format!("{}.json", oid));
    if !p.is_file() {
        return None;
    }
    let bytes = match std::fs::read(&p) {
        Ok(b) => b,
        Err(_) => return Some(J::Obj(Vec::new())),
    };
    let text = match String::from_utf8(bytes) {
        Ok(t) => crate::universal_newlines(&t),
        Err(_) => return Some(J::Obj(Vec::new())), // UnicodeDecodeError is a ValueError
    };
    match pyjson::parse(&text) {
        Ok(J::Null) => None, // json.loads("null") is None
        Ok(v) => Some(v),
        Err(()) => Some(J::Obj(Vec::new())),
    }
}

fn in_set(needle: &Py, set: &[Py]) -> Result<bool, PyErr> {
    needle.check_hashable()?;
    Ok(set.iter().any(|x| x.py_eq(needle)))
}

fn strings(node: &Py, out: &mut Vec<String>) {
    match node {
        Py::Str(s) => out.push(s.clone()),
        Py::Dict(d) => d.iter().for_each(|(_, v)| strings(v, out)),
        Py::List(l) => l.iter().for_each(|v| strings(v, out)),
        _ => {}
    }
}

fn valid_measurement(m: &J, oid: &str) -> Result<bool, PyErr> {
    if !matches!(m, J::Obj(_)) {
        return Err("AttributeError: object has no attribute 'get'".into());
    }
    if !matches!(m.get("objective"), Some(J::Str(Some(s))) if s == oid) {
        return Ok(false);
    }
    let Some(value) = m.get("value").and_then(J::as_int) else { return Ok(false) };
    let Some(of) = m.get("of").and_then(J::as_int) else { return Ok(false) };
    let zero = (false, "0".to_string());
    Ok(int_cmp(&of, &zero) == Ordering::Greater
        && int_cmp(&zero, &value) != Ordering::Greater
        && int_cmp(&value, &of) != Ordering::Greater)
}

pub fn check(doc: &Py, measure_dir: &Path) -> Result<Vec<String>, PyErr> {
    let mut errors = Vec::new();
    match doc.get("north_star")? {
        Some(Py::Str(s)) if strip_nonempty(s) => {
            if pyre::date_search(s) {
                errors.push("north_star carries a date; only commitments are dated".into());
            }
        }
        _ => errors.push("north_star is missing or empty".into()),
    }

    let objectives = Py::iter_or_empty(doc.get("objectives")?)?;
    if objectives.is_empty() {
        errors.push("no objectives".into());
    }
    let mut ids: Vec<Py> = Vec::new();
    for (i, o) in objectives.iter().enumerate() {
        let w = format!("objectives[{}]", i);
        for f in OBJECTIVE_FIELDS {
            match o.get(f)? {
                Some(Py::Str(v)) if strip_nonempty(v) => {}
                _ => errors.push(format!("{}: field {} is missing or empty", w, str_repr(f))),
            }
        }
        let oid = o.get("id")?.cloned().unwrap_or(Py::Str(String::new()));
        if oid.truthy() {
            let s = oid.as_str().ok_or_else(|| "TypeError: expected string or bytes-like object".to_string())?;
            if !pyre::id_match(s) {
                errors.push(format!("{}: id {} is not O<n>", w, oid.py_repr()));
            }
        }
        if in_set(&oid, &ids)? {
            errors.push(format!("{}: duplicate id {}", w, oid.py_repr()));
        }
        ids.push(oid.clone());
        let state = o.get("state")?.cloned().unwrap_or(Py::None);
        if state.truthy() {
            let states = [Py::Str("unmeasured".into()), Py::Str("measured".into())];
            if !in_set(&state, &states)? {
                errors.push(format!("{}: state {} is not one of {}", w, state.py_repr(), STATES_SORTED));
            }
        }
        // oid is a str here whenever it is truthy (the id check above raised otherwise).
        let m = match &oid {
            Py::Str(s) if !s.is_empty() => measurement(s, measure_dir),
            _ => None,
        };
        let oid_s = oid.py_str();
        if state.as_str() == Some("measured") {
            match &m {
                None => errors.push(format!(
                    "{}: state is measured but data/north-star/{}.json is missing",
                    w, oid_s
                )),
                Some(m) => {
                    if !valid_measurement(m, &oid_s)? {
                        errors.push(format!("{}: data/north-star/{}.json is not a valid measurement", w, oid_s));
                    }
                }
            }
        } else if m.is_some() {
            errors.push(format!(
                "{}: data/north-star/{}.json exists but state is {}",
                w,
                oid_s,
                state.py_repr()
            ));
        }
    }

    for (i, p) in Py::iter_or_empty(doc.get("periods")?)?.iter().enumerate() {
        let w = format!("periods[{}]", i);
        let layers = Py::iter_or_empty(p.get("layers")?)?;
        if layers.is_empty() {
            errors.push(format!("{}: no varve layers", w));
        }
        for layer in &layers {
            if !pyre::layer_match(&layer.py_str()) {
                errors.push(format!("{}: layer {} is not YYYY.MM", w, layer.py_repr()));
            }
        }
        for (j, c) in Py::iter_or_empty(p.get("commitments")?)?.iter().enumerate() {
            let cw = format!("{}.commitments[{}]", w, j);
            let objective = c.get("objective")?.cloned().unwrap_or(Py::None);
            if !in_set(&objective, &ids)? {
                errors.push(format!("{}: objective {} does not exist", cw, objective.py_repr()));
            }
            let kind = c.get("kind")?.cloned().unwrap_or(Py::None);
            let kinds = [Py::Str("committed".into()), Py::Str("stretch".into())];
            if !in_set(&kind, &kinds)? {
                errors.push(format!("{}: kind {} is not one of {}", cw, kind.py_repr(), KINDS_SORTED));
            }
            let target = c.get("target")?.cloned().unwrap_or(Py::Str(String::new()));
            if !strip_nonempty(&target.py_str()) {
                errors.push(format!("{}: target is empty", cw));
            }
        }
    }

    for (i, pr) in Py::iter_or_empty(doc.get("products")?)?.iter().enumerate() {
        for pid in Py::iter_or_empty(pr.get("pulls")?)? {
            if !in_set(&pid, &ids)? {
                let name = pr.get("name")?.cloned().unwrap_or(Py::None);
                errors.push(format!(
                    "products[{}] ({}): pulls unknown objective {}",
                    i,
                    name.py_str(),
                    pid.py_repr()
                ));
            }
        }
    }

    let mut all = Vec::new();
    strings(doc, &mut all);
    for s in all {
        if pyre::ipv4_search(&s) || pyre::host_search(&s) {
            let head: String = s.chars().take(60).collect();
            errors.push(format!("private infrastructure detail in text: {}", str_repr(&head)));
        }
    }
    Ok(errors)
}
