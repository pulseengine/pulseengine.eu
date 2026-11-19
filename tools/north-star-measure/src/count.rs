//! The counting rules for O1, O3 and O5. Inputs reaching this module are
//! already signed, listed in SHA256SUMS and valid against schema v1; a product
//! whose input is not is in `not_counted` and never reaches a counter.

use crate::schema::{Fact, Input};
use serde_json::{json, Map, Value};

/// Which counting rules are honoured. Production code uses [`Rules::REAL`];
/// the other settings exist only so the test suite can show that it fails
/// against a counter that drops a rule (negative control).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Rules {
    /// A fact with ran=false is a fail.
    pub honour_ran: bool,
    /// A fact with control_failed_as_expected=false is a fail.
    pub honour_control: bool,
}

impl Rules {
    pub const REAL: Rules = Rules { honour_ran: true, honour_control: true };
}

/// The O1 rungs that count toward the value (jess's ladder).
pub const NAMED_RUNGS: [&str; 3] = ["hil", "real-drone", "flight"];
/// synth's per-target numbers, reported in items and never summed.
pub const SYNTH_FIELDS: [&str; 3] = ["execution_match", "reach", "wcet"];
/// The three O3 facts a proof-carrying product must pass.
pub const O3_FACTS: [&str; 3] = ["proof_check_required", "axiom_audit", "ledger"];
/// The O5 gate fields: (name, required value).
pub const O5_FIELDS: [(&str, bool); 5] = [
    ("signed", true),
    ("kiln_runs", true),
    ("wasmtime_equal", true),
    ("equivalence_in_ci", true),
    ("gap_switch", false),
];

/// A product whose input passed every check.
#[derive(Debug, Clone)]
pub struct Counted {
    pub product: String,
    pub release: String,
    pub input: Input,
}

#[derive(Debug, Clone)]
pub struct Tally {
    pub value: u64,
    pub of: u64,
    pub items: Vec<Value>,
}

/// The rules every fact obeys. `control_required`: an absent
/// control_failed_as_expected is a fail too (O3, where the seam requires a
/// planted control for each fact).
pub fn fact_verdict(f: &Fact, rules: Rules, control_required: bool) -> Result<(), String> {
    if rules.honour_ran && !f.ran {
        return Err("ran=false: not run this release counts as a fail".into());
    }
    if !f.pass {
        return Err("pass=false".into());
    }
    match f.control {
        Some(false) if rules.honour_control => {
            Err("control_failed_as_expected=false: the planted control did not turn it red, so the check could not fail".into())
        }
        None if control_required => Err("no control_failed_as_expected: no planted control shows the check can fail".into()),
        _ => Ok(()),
    }
}

/// O1 structure beyond the schema: every fact id is `<target>/<rung>`, and
/// detail.target / detail.rung, when present, agree with it.
pub fn o1_split(f: &Fact) -> Result<(String, String), String> {
    let (t, r) = f.id.rsplit_once('/').ok_or_else(|| format!("fact {:?}: O1 ids are \"<target>/<rung>\"", f.id))?;
    if t.is_empty() || r.is_empty() {
        return Err(format!("fact {:?}: O1 ids are \"<target>/<rung>\"", f.id));
    }
    for (k, want) in [("target", t), ("rung", r)] {
        match f.detail.get(k) {
            None => {}
            Some(Value::String(s)) if s == want => {}
            Some(other) => return Err(format!("fact {:?}: detail.{k} {other} disagrees with the id", f.id)),
        }
    }
    Ok((t.to_string(), r.to_string()))
}

/// Objective-specific structure an input must have to be counted at all.
pub fn structure(objective: &str, input: &Input) -> Result<(), String> {
    if objective == "O1" {
        for f in &input.facts {
            o1_split(f)?;
        }
    }
    Ok(())
}

fn verdict_str(r: &Result<(), String>) -> String {
    match r {
        Ok(()) => "pass".into(),
        Err(e) => format!("fail: {e}"),
    }
}

fn with_url(mut item: Map<String, Value>, f: Option<&Fact>) -> Value {
    if let Some(u) = f.and_then(|f| f.evidence.clone()) {
        item.insert("url".into(), Value::String(u));
    }
    Value::Object(item)
}

/// O1: value = (target, named rung) facts passing; of = named rungs per target
/// reported. A named rung a target does not report is a fail. Other rungs (r0)
/// and synth's fields are items marked `in_value: false`.
pub fn o1(inputs: &[Counted], rules: Rules) -> Tally {
    let (mut value, mut of, mut items) = (0u64, 0u64, Vec::new());
    for c in inputs {
        let mut targets: Vec<String> = Vec::new();
        for f in &c.input.facts {
            let (t, _) = o1_split(f).expect("checked by structure()");
            if !targets.contains(&t) {
                targets.push(t);
            }
        }
        for t in &targets {
            for rung in NAMED_RUNGS {
                of += 1;
                let fact = c.input.facts.iter().find(|f| o1_split(f).map(|(ft, fr)| &ft == t && fr == rung).unwrap_or(false));
                let v = match fact {
                    Some(f) => fact_verdict(f, rules, false),
                    None => Err("not reported: a skipped rung counts as a fail".into()),
                };
                if v.is_ok() {
                    value += 1;
                }
                let mut m = Map::new();
                m.insert("label".into(), json!(format!("{} {}: {t}/{rung}", c.product, c.release)));
                m.insert("product".into(), json!(c.product));
                m.insert("release".into(), json!(c.release));
                m.insert("target".into(), json!(t));
                m.insert("rung".into(), json!(rung));
                m.insert("in_value".into(), json!(true));
                m.insert("counts".into(), json!(v.is_ok()));
                m.insert("verdict".into(), json!(verdict_str(&v)));
                items.push(with_url(m, fact));
            }
        }
        for f in &c.input.facts {
            let (t, r) = o1_split(f).expect("checked by structure()");
            if NAMED_RUNGS.contains(&r.as_str()) {
                continue;
            }
            let mut m = Map::new();
            m.insert("label".into(), json!(format!("{} {}: {t}/{r} (reported separately)", c.product, c.release)));
            m.insert("product".into(), json!(c.product));
            m.insert("release".into(), json!(c.release));
            m.insert("target".into(), json!(t));
            m.insert("rung".into(), json!(r));
            m.insert("in_value".into(), json!(false));
            m.insert("ran".into(), json!(f.ran));
            m.insert("pass".into(), json!(f.pass));
            if let Some(ctl) = f.control {
                m.insert("control_failed_as_expected".into(), json!(ctl));
            }
            for k in SYNTH_FIELDS {
                if let Some(x) = f.detail.get(k) {
                    m.insert(k.into(), x.clone());
                }
            }
            items.push(with_url(m, Some(f)));
        }
    }
    Tally { value, of, items }
}

/// O3: a product counts only if proof_check_required, axiom_audit and ledger
/// all pass, each with its planted control. of = products pulling O3.
pub fn o3(inputs: &[Counted], pulling: u64, rules: Rules) -> Tally {
    let (mut value, mut items) = (0u64, Vec::new());
    for c in inputs {
        let mut facts = Map::new();
        let mut all = true;
        for id in O3_FACTS {
            let v = match c.input.facts.iter().find(|f| f.id == id) {
                Some(f) => fact_verdict(f, rules, true),
                None => Err("not reported".into()),
            };
            all &= v.is_ok();
            facts.insert(id.into(), json!(verdict_str(&v)));
        }
        if all {
            value += 1;
        }
        let mut m = Map::new();
        m.insert("label".into(), json!(format!("{} {}", c.product, c.release)));
        m.insert("product".into(), json!(c.product));
        m.insert("release".into(), json!(c.release));
        m.insert("counts".into(), json!(all));
        m.insert("facts".into(), Value::Object(facts));
        items.push(Value::Object(m));
    }
    Tally { value, of: pulling, items }
}

/// The O5 verdict for one gate fact.
pub fn o5_gate(f: &Fact, rules: Rules) -> Result<(), String> {
    fact_verdict(f, rules, false)?;
    for (k, want) in O5_FIELDS {
        match f.detail.get(k).and_then(Value::as_bool) {
            Some(b) if b == want => {}
            Some(b) => return Err(format!("detail.{k}={b}")),
            None => return Err(format!("detail.{k} is missing or not a boolean")),
        }
    }
    Ok(())
}

/// O5: a gate counts only with signed, kiln_runs, wasmtime_equal and
/// equivalence_in_ci true and gap_switch false. of = the gates reported.
pub fn o5(inputs: &[Counted], rules: Rules) -> Tally {
    let (mut value, mut of, mut items) = (0u64, 0u64, Vec::new());
    for c in inputs {
        for f in &c.input.facts {
            of += 1;
            let v = o5_gate(f, rules);
            if v.is_ok() {
                value += 1;
            }
            let mut m = Map::new();
            m.insert("label".into(), json!(format!("{} {}: {}", c.product, c.release, f.id)));
            m.insert("product".into(), json!(c.product));
            m.insert("release".into(), json!(c.release));
            m.insert("gate".into(), json!(f.id));
            m.insert("counts".into(), json!(v.is_ok()));
            m.insert("verdict".into(), json!(verdict_str(&v)));
            items.push(with_url(m, Some(f)));
        }
    }
    Tally { value, of, items }
}
