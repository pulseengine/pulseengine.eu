// rivet: verifies REQ-NORTH-STAR-MEASURE
//! One offline case per counting rule. Each case plants exactly one defect
//! next to an otherwise countable fixture and requires the result to move
//! exactly as the rule says. The cases take the counter's rules as a
//! parameter, so `negative_control_*` can run the whole suite against a
//! counter that drops a rule and require the suite to fail.

mod common;

use common::{fact, input, stub_cosign, Fx, Sign};
use north_star_measure::count::Rules;
use north_star_measure::source::Source;
use north_star_measure::{measure, Env, Objective, Outcome};
use serde_json::{json, Value};

type Case = fn(Rules) -> Result<(), String>;

macro_rules! ensure {
    ($c:expr, $($m:tt)*) => {
        if !$c {
            return Err(format!($($m)*));
        }
    };
}

fn outcome(fx: &Fx, o: Objective, rules: Rules) -> Result<Outcome, String> {
    let env = Env { root: fx.root.clone(), source: Source::Offline(fx.fixtures.clone()), cosign: stub_cosign(), rules };
    measure(o, &env)
}

fn doc(fx: &Fx, o: Objective, rules: Rules) -> Result<Value, String> {
    match outcome(fx, o, rules)? {
        Outcome::Measured(d) => Ok(d),
        Outcome::Unmeasured(why, _) => Err(format!("expected a measurement, got unmeasured: {why}")),
    }
}

fn vo(d: &Value) -> (u64, u64) {
    (d["value"].as_u64().unwrap(), d["of"].as_u64().unwrap())
}

fn reasons(d: &Value) -> Vec<String> {
    d["not_counted"]
        .as_array()
        .unwrap()
        .iter()
        .map(|n| format!("{}: {}", n["product"].as_str().unwrap(), n["reason"].as_str().unwrap()))
        .collect()
}

fn item<'a>(d: &'a Value, label_part: &str) -> Option<&'a Value> {
    d["items"].as_array().unwrap().iter().find(|i| i["label"].as_str().unwrap_or("").contains(label_part))
}

fn edit(facts: &mut [Value], id: &str, f: impl Fn(&mut Value)) {
    let x = facts.iter_mut().find(|x| x["id"] == id).unwrap_or_else(|| panic!("no fact {id}"));
    f(x);
}

// ---------------------------------------------------------------- O1

fn rung(t: &str, r: &str) -> Value {
    fact(&format!("{t}/{r}"), true, true, Some(true), json!({"target": t, "rung": r, "oracle": "relay simulation"}))
}

fn o1_facts(t: &str) -> Vec<Value> {
    vec![
        rung(t, "hil"),
        rung(t, "real-drone"),
        rung(t, "flight"),
        fact(&format!("{t}/r0"), true, true, None, json!({"target": t, "rung": "r0"})),
        fact(
            &format!("{t}/synth"),
            true,
            false,
            None,
            json!({"target": t, "rung": "synth", "execution_match": 0.97, "reach": 0.81, "wcet": 1200}),
        ),
    ]
}

fn o1_single(facts: Vec<Value>, rules: Rules) -> Result<Value, String> {
    let fx = Fx::new(&[("jess", &["O1"])], &[]);
    fx.publish("jess", "v0.8.0", &input("O1", "jess", facts), Sign::Good);
    doc(&fx, Objective::O1, rules)
}

fn o1_baseline(rules: Rules) -> Result<(), String> {
    let d = o1_single(o1_facts("rt1176"), rules)?;
    ensure!(vo(&d) == (3, 3), "baseline: want 3 of 3, got {:?}", vo(&d));
    ensure!(d["schema_version"] == 1, "schema_version missing");
    let synth = item(&d, "rt1176/synth").ok_or("synth fields not reported")?;
    ensure!(synth["in_value"] == false && synth["execution_match"] == 0.97 && synth["reach"] == 0.81 && synth["wcet"] == 1200, "synth item wrong: {synth}");
    ensure!(item(&d, "rt1176/r0").map(|i| i["in_value"] == false).unwrap_or(false), "r0 not reported separately");
    Ok(())
}

fn o1_ran_false_is_fail(rules: Rules) -> Result<(), String> {
    let mut f = o1_facts("rt1176");
    // A producer claiming pass for a rung it did not run.
    edit(&mut f, "rt1176/flight", |x| x["ran"] = json!(false));
    let d = o1_single(f, rules)?;
    ensure!(vo(&d) == (2, 3), "ran=false: want 2 of 3, got {:?}", vo(&d));
    let v = item(&d, "rt1176/flight").unwrap()["verdict"].as_str().unwrap().to_string();
    ensure!(v.contains("ran=false"), "verdict does not name ran=false: {v}");
    Ok(())
}

fn o1_control_false_is_fail(rules: Rules) -> Result<(), String> {
    let mut f = o1_facts("rt1176");
    edit(&mut f, "rt1176/hil", |x| x["control_failed_as_expected"] = json!(false));
    let d = o1_single(f, rules)?;
    ensure!(vo(&d) == (2, 3), "control=false: want 2 of 3, got {:?}", vo(&d));
    Ok(())
}

fn o1_missing_rung_is_fail(rules: Rules) -> Result<(), String> {
    let f: Vec<Value> = o1_facts("rt1176").into_iter().filter(|x| x["id"] != "rt1176/flight").collect();
    let d = o1_single(f, rules)?;
    ensure!(vo(&d) == (2, 3), "missing rung: want 2 of 3, got {:?}", vo(&d));
    ensure!(item(&d, "rt1176/flight").unwrap()["verdict"].as_str().unwrap().contains("not reported"), "missing rung not named");
    Ok(())
}

fn o1_r0_and_synth_stay_out_of_value(rules: Rules) -> Result<(), String> {
    let mut f = o1_facts("rt1176");
    edit(&mut f, "rt1176/r0", |x| x["pass"] = json!(false));
    edit(&mut f, "rt1176/synth", |x| x["pass"] = json!(true));
    let d = o1_single(f.clone(), rules)?;
    ensure!(vo(&d) == (3, 3), "r0/synth changed the value: {:?}", vo(&d));
    // A target that reports only r0 adds three named rungs to `of`, none passing.
    f.push(fact("esp32c3/r0", true, true, None, json!({})));
    let d = o1_single(f, rules)?;
    ensure!(vo(&d) == (3, 6), "r0-only target: want 3 of 6, got {:?}", vo(&d));
    Ok(())
}

/// jess (countable) plus falcon, whose input is planted per case.
fn o1_two(sign: Sign, asset: &str, change: impl Fn(&mut Value), rules: Rules) -> Result<Value, String> {
    let fx = Fx::new(&[("jess", &["O1"]), ("falcon", &["O1"])], &[]);
    fx.publish("jess", "v0.8.0", &input("O1", "jess", o1_facts("rt1176")), Sign::Good);
    let mut inp = input("O1", "falcon", o1_facts("stm32h7"));
    change(&mut inp);
    fx.publish_as("falcon", "v1.0.0", asset, &inp, sign);
    doc(&fx, Objective::O1, rules)
}

const O1_ASSET: &str = "north-star-input.O1.json";

/// The planted product is dropped (3 of 3 from jess alone), it is listed under
/// not_counted with `reason`, and the same product unplanted counts (6 of 6).
fn o1_not_counted(sign: Sign, asset: &str, change: fn(&mut Value), reason: &str, rules: Rules) -> Result<(), String> {
    let good = o1_two(Sign::Good, O1_ASSET, |_| {}, rules)?;
    ensure!(vo(&good) == (6, 6), "control fixture: want 6 of 6, got {:?}", vo(&good));
    let d = o1_two(sign, asset, change, rules)?;
    ensure!(vo(&d) == (3, 3), "{sign:?}: want 3 of 3 (falcon not counted, never zero-filled), got {:?}", vo(&d));
    let r = reasons(&d);
    ensure!(r.len() == 1 && r[0].starts_with("falcon: ") && r[0].contains(reason), "{sign:?}: not_counted {r:?} lacks {reason:?}");
    ensure!(item(&d, "falcon").is_none(), "a not-counted product left items");
    Ok(())
}

fn o1_unsigned_not_counted(rules: Rules) -> Result<(), String> {
    o1_not_counted(Sign::Unsigned, O1_ASSET, |_| {}, "unsigned", rules)
}
fn o1_branch_signer_not_counted(rules: Rules) -> Result<(), String> {
    o1_not_counted(Sign::BranchRef, O1_ASSET, |_| {}, "does not verify", rules)
}
fn o1_other_tag_signer_not_counted(rules: Rules) -> Result<(), String> {
    o1_not_counted(Sign::OtherTag, O1_ASSET, |_| {}, "does not verify", rules)
}
fn o1_other_repo_signer_not_counted(rules: Rules) -> Result<(), String> {
    o1_not_counted(Sign::OtherRepo, O1_ASSET, |_| {}, "does not verify", rules)
}
fn o1_tampered_input_not_counted(rules: Rules) -> Result<(), String> {
    o1_not_counted(Sign::Tampered, O1_ASSET, |_| {}, "does not match", rules)
}
fn o1_unlisted_input_not_counted(rules: Rules) -> Result<(), String> {
    o1_not_counted(Sign::NotListed, O1_ASSET, |_| {}, "does not list", rules)
}
fn o1_no_sums_not_counted(rules: Rules) -> Result<(), String> {
    o1_not_counted(Sign::NoSums, O1_ASSET, |_| {}, "no SHA256SUMS", rules)
}
fn o1_missing_asset_not_counted(rules: Rules) -> Result<(), String> {
    o1_not_counted(Sign::NoAsset, O1_ASSET, |_| {}, "no north-star-input.O1.json asset", rules)
}
fn o1_name_objective_mismatch_not_counted(rules: Rules) -> Result<(), String> {
    o1_not_counted(Sign::Good, O1_ASSET, |v| v["objective"] = json!("O5"), "file name says O1 but objective is \"O5\"", rules)
}
fn o1_wrong_name_is_missing(rules: Rules) -> Result<(), String> {
    // The seam's earlier single-file name is not read for O1.
    o1_not_counted(Sign::Good, "north-star-input.json", |_| {}, "no north-star-input.O1.json asset", rules)
}
fn o1_schema_violation_not_counted(rules: Rules) -> Result<(), String> {
    o1_not_counted(Sign::Good, O1_ASSET, |v| v["extra"] = json!(1), "additionalProperties", rules)
}
fn o1_ran_not_boolean_not_counted(rules: Rules) -> Result<(), String> {
    o1_not_counted(Sign::Good, O1_ASSET, |v| v["facts"][0]["ran"] = json!("yes"), "ran: must be a boolean", rules)
}
fn o1_repo_mismatch_not_counted(rules: Rules) -> Result<(), String> {
    o1_not_counted(Sign::Good, O1_ASSET, |v| v["repo"] = json!("pulseengine/jess"), "repo is", rules)
}
fn o1_bad_fact_id_not_counted(rules: Rules) -> Result<(), String> {
    o1_not_counted(Sign::Good, O1_ASSET, |v| v["facts"][0]["id"] = json!("hil"), "<target>/<rung>", rules)
}
fn o1_detail_disagrees_with_id_not_counted(rules: Rules) -> Result<(), String> {
    o1_not_counted(Sign::Good, O1_ASSET, |v| v["facts"][0]["detail"]["rung"] = json!("flight"), "disagrees with the id", rules)
}
fn o1_signed_sig_cert_counts(rules: Rules) -> Result<(), String> {
    let d = o1_two(Sign::GoodSigCert, O1_ASSET, |_| {}, rules)?;
    ensure!(vo(&d) == (6, 6), ".sig + .pem: want 6 of 6, got {:?}", vo(&d));
    Ok(())
}

fn o1_no_input_anywhere_is_unmeasured(rules: Rules) -> Result<(), String> {
    let fx = Fx::new(&[("jess", &["O1"]), ("falcon", &["O1"])], &[]);
    fx.publish("jess", "v0.8.0", &input("O1", "jess", o1_facts("rt1176")), Sign::NoAsset);
    // falcon has no release at all
    match outcome(&fx, Objective::O1, rules)? {
        Outcome::Unmeasured(why, nc) => {
            ensure!(why.contains("no product publishes"), "wrong reason: {why}");
            ensure!(nc.len() == 2, "both products must be listed as not counted: {nc:?}");
            Ok(())
        }
        Outcome::Measured(d) => Err(format!("measured {:?} with no input: a made-up number", vo(&d))),
    }
}

// ---------------------------------------------------------------- O3

fn o3_facts() -> Vec<Value> {
    ["proof_check_required", "axiom_audit", "ledger"].iter().map(|id| fact(id, true, true, Some(true), json!({}))).collect()
}

fn o3_run(plant: Option<Vec<Value>>, rules: Rules) -> Result<Value, String> {
    let fx = Fx::new(&[("relay", &["O2", "O3"]), ("plant", &["O3"])], &[]);
    fx.publish("relay", "falcon-v1.143.0", &input("O3", "relay", o3_facts()), Sign::Good);
    match plant {
        Some(f) => fx.publish("plant", "v0.3.0", &input("O3", "plant", f), Sign::Good),
        None => fx.publish("plant", "v0.3.0", &input("O3", "plant", o3_facts()), Sign::NoAsset),
    }
    doc(&fx, Objective::O3, rules)
}

fn o3_case(change: impl Fn(&mut Vec<Value>), want_fact: &str, rules: Rules) -> Result<(), String> {
    let base = o3_run(Some(o3_facts()), rules)?;
    ensure!(vo(&base) == (2, 2), "O3 baseline: want 2 of 2, got {:?}", vo(&base));
    let mut f = o3_facts();
    change(&mut f);
    let d = o3_run(Some(f), rules)?;
    ensure!(vo(&d) == (1, 2), "want 1 of 2, got {:?}", vo(&d));
    let plant = item(&d, "plant").ok_or("plant item missing")?;
    ensure!(plant["counts"] == false, "plant counted");
    ensure!(plant["facts"][want_fact].as_str().unwrap_or("").starts_with("fail"), "{want_fact} not failed: {plant}");
    Ok(())
}

fn o3_baseline(rules: Rules) -> Result<(), String> {
    let d = o3_run(Some(o3_facts()), rules)?;
    ensure!(vo(&d) == (2, 2), "want 2 of 2, got {:?}", vo(&d));
    Ok(())
}
fn o3_ran_false_is_fail(rules: Rules) -> Result<(), String> {
    o3_case(|f| edit(f, "ledger", |x| x["ran"] = json!(false)), "ledger", rules)
}
fn o3_control_false_is_fail(rules: Rules) -> Result<(), String> {
    o3_case(|f| edit(f, "axiom_audit", |x| x["control_failed_as_expected"] = json!(false)), "axiom_audit", rules)
}
fn o3_control_absent_is_fail(rules: Rules) -> Result<(), String> {
    o3_case(
        |f| edit(f, "proof_check_required", |x| {
            x.as_object_mut().unwrap().remove("control_failed_as_expected");
        }),
        "proof_check_required",
        rules,
    )
}
fn o3_pass_false_is_fail(rules: Rules) -> Result<(), String> {
    o3_case(|f| edit(f, "ledger", |x| x["pass"] = json!(false)), "ledger", rules)
}
fn o3_missing_fact_is_fail(rules: Rules) -> Result<(), String> {
    o3_case(|f| f.retain(|x| x["id"] != "axiom_audit"), "axiom_audit", rules)
}
fn o3_missing_input_stays_in_denominator(rules: Rules) -> Result<(), String> {
    let d = o3_run(None, rules)?;
    ensure!(vo(&d) == (1, 2), "want 1 of 2 (of = products pulling O3), got {:?}", vo(&d));
    let r = reasons(&d);
    ensure!(r.len() == 1 && r[0].starts_with("plant: no north-star-input.O3.json"), "not_counted: {r:?}");
    Ok(())
}

// ---------------------------------------------------------------- O5

fn gate(id: &str) -> Value {
    fact(
        id,
        true,
        true,
        Some(true),
        json!({"signed": true, "kiln_runs": true, "wasmtime_equal": true, "equivalence_in_ci": true, "gap_switch": false}),
    )
}

fn o5_run(g2: Value, rules: Rules) -> Result<Value, String> {
    let fx = Fx::new(&[("kiln", &["O3", "O5"])], &[]);
    fx.publish("kiln", "v0.9.0", &input("O5", "kiln", vec![gate("north-star-check"), g2]), Sign::Good);
    doc(&fx, Objective::O5, rules)
}

fn o5_case(change: impl Fn(&mut Value), want: &str, rules: Rules) -> Result<(), String> {
    let base = o5_run(gate("seam-check"), rules)?;
    ensure!(vo(&base) == (2, 2), "O5 baseline: want 2 of 2, got {:?}", vo(&base));
    let mut g = gate("seam-check");
    change(&mut g);
    let d = o5_run(g, rules)?;
    ensure!(vo(&d) == (1, 2), "want 1 of 2, got {:?}", vo(&d));
    let v = item(&d, "seam-check").unwrap()["verdict"].as_str().unwrap().to_string();
    ensure!(v.contains(want), "verdict {v:?} lacks {want:?}");
    Ok(())
}

fn o5_baseline(rules: Rules) -> Result<(), String> {
    let d = o5_run(gate("seam-check"), rules)?;
    ensure!(vo(&d) == (2, 2), "want 2 of 2, got {:?}", vo(&d));
    Ok(())
}
fn o5_gap_switch_is_fail(rules: Rules) -> Result<(), String> {
    o5_case(|g| g["detail"]["gap_switch"] = json!(true), "gap_switch=true", rules)
}
fn o5_equivalence_not_in_ci_is_fail(rules: Rules) -> Result<(), String> {
    o5_case(|g| g["detail"]["equivalence_in_ci"] = json!(false), "equivalence_in_ci=false", rules)
}
fn o5_kiln_not_running_is_fail(rules: Rules) -> Result<(), String> {
    o5_case(|g| g["detail"]["kiln_runs"] = json!(false), "kiln_runs=false", rules)
}
fn o5_unsigned_component_is_fail(rules: Rules) -> Result<(), String> {
    o5_case(|g| g["detail"]["signed"] = json!(false), "signed=false", rules)
}
fn o5_wasmtime_differs_is_fail(rules: Rules) -> Result<(), String> {
    o5_case(|g| g["detail"]["wasmtime_equal"] = json!(false), "wasmtime_equal=false", rules)
}
fn o5_missing_detail_is_fail(rules: Rules) -> Result<(), String> {
    o5_case(|g| {
        g["detail"].as_object_mut().unwrap().remove("gap_switch");
    }, "gap_switch is missing", rules)
}
fn o5_ran_false_is_fail(rules: Rules) -> Result<(), String> {
    o5_case(|g| g["ran"] = json!(false), "ran=false", rules)
}
fn o5_control_false_is_fail(rules: Rules) -> Result<(), String> {
    o5_case(|g| g["control_failed_as_expected"] = json!(false), "could not fail", rules)
}

// ---------------------------------------------------------------- the suite

const CASES: &[(&str, Case)] = &[
    ("o1_baseline", o1_baseline),
    ("o1_ran_false_is_fail", o1_ran_false_is_fail),
    ("o1_control_false_is_fail", o1_control_false_is_fail),
    ("o1_missing_rung_is_fail", o1_missing_rung_is_fail),
    ("o1_r0_and_synth_stay_out_of_value", o1_r0_and_synth_stay_out_of_value),
    ("o1_unsigned_not_counted", o1_unsigned_not_counted),
    ("o1_branch_signer_not_counted", o1_branch_signer_not_counted),
    ("o1_other_tag_signer_not_counted", o1_other_tag_signer_not_counted),
    ("o1_other_repo_signer_not_counted", o1_other_repo_signer_not_counted),
    ("o1_tampered_input_not_counted", o1_tampered_input_not_counted),
    ("o1_unlisted_input_not_counted", o1_unlisted_input_not_counted),
    ("o1_no_sums_not_counted", o1_no_sums_not_counted),
    ("o1_missing_asset_not_counted", o1_missing_asset_not_counted),
    ("o1_name_objective_mismatch_not_counted", o1_name_objective_mismatch_not_counted),
    ("o1_wrong_name_is_missing", o1_wrong_name_is_missing),
    ("o1_schema_violation_not_counted", o1_schema_violation_not_counted),
    ("o1_ran_not_boolean_not_counted", o1_ran_not_boolean_not_counted),
    ("o1_repo_mismatch_not_counted", o1_repo_mismatch_not_counted),
    ("o1_bad_fact_id_not_counted", o1_bad_fact_id_not_counted),
    ("o1_detail_disagrees_with_id_not_counted", o1_detail_disagrees_with_id_not_counted),
    ("o1_signed_sig_cert_counts", o1_signed_sig_cert_counts),
    ("o1_no_input_anywhere_is_unmeasured", o1_no_input_anywhere_is_unmeasured),
    ("o3_baseline", o3_baseline),
    ("o3_ran_false_is_fail", o3_ran_false_is_fail),
    ("o3_control_false_is_fail", o3_control_false_is_fail),
    ("o3_control_absent_is_fail", o3_control_absent_is_fail),
    ("o3_pass_false_is_fail", o3_pass_false_is_fail),
    ("o3_missing_fact_is_fail", o3_missing_fact_is_fail),
    ("o3_missing_input_stays_in_denominator", o3_missing_input_stays_in_denominator),
    ("o5_baseline", o5_baseline),
    ("o5_gap_switch_is_fail", o5_gap_switch_is_fail),
    ("o5_equivalence_not_in_ci_is_fail", o5_equivalence_not_in_ci_is_fail),
    ("o5_kiln_not_running_is_fail", o5_kiln_not_running_is_fail),
    ("o5_unsigned_component_is_fail", o5_unsigned_component_is_fail),
    ("o5_wasmtime_differs_is_fail", o5_wasmtime_differs_is_fail),
    ("o5_missing_detail_is_fail", o5_missing_detail_is_fail),
    ("o5_ran_false_is_fail", o5_ran_false_is_fail),
    ("o5_control_false_is_fail", o5_control_false_is_fail),
];

fn failures(rules: Rules) -> Vec<(String, String)> {
    CASES.iter().filter_map(|(n, c)| c(rules).err().map(|e| (n.to_string(), e))).collect()
}

/// Every case holds against the real counter.
#[test]
fn suite_holds_with_the_real_rules() {
    let f = failures(Rules::REAL);
    assert!(f.is_empty(), "{} of {} cases failed: {f:#?}", f.len(), CASES.len());
    println!("{} of {} cases hold", CASES.len(), CASES.len());
}

/// Negative control: a counter that ignores ran=false must fail the suite,
/// and exactly at the ran=false cases.
#[test]
fn negative_control_a_counter_ignoring_ran_false_fails_the_suite() {
    let f = failures(Rules { honour_ran: false, honour_control: true });
    let names: Vec<&str> = f.iter().map(|(n, _)| n.as_str()).collect();
    println!("mutant (ignores ran=false): {} of {} cases fail: {names:?}", f.len(), CASES.len());
    assert_eq!(names, ["o1_ran_false_is_fail", "o3_ran_false_is_fail", "o5_ran_false_is_fail"]);
}

/// Negative control: a counter that ignores control_failed_as_expected=false
/// must fail the suite, exactly at the control=false cases.
#[test]
fn negative_control_a_counter_ignoring_failed_controls_fails_the_suite() {
    let f = failures(Rules { honour_ran: true, honour_control: false });
    let names: Vec<&str> = f.iter().map(|(n, _)| n.as_str()).collect();
    println!("mutant (ignores control=false): {} of {} cases fail: {names:?}", f.len(), CASES.len());
    assert_eq!(names, ["o1_control_false_is_fail", "o3_control_false_is_fail", "o5_control_false_is_fail"]);
}

// One #[test] per case too, so `cargo test` names the rule that broke.
macro_rules! each {
    ($($name:ident),* $(,)?) => {
        $(
            #[test]
            fn $name() {
                if let Err(e) = super::$name(Rules::REAL) {
                    panic!("{e}");
                }
            }
        )*
    };
}

mod case {
    use super::Rules;
    each!(
        o1_baseline,
        o1_ran_false_is_fail,
        o1_control_false_is_fail,
        o1_missing_rung_is_fail,
        o1_r0_and_synth_stay_out_of_value,
        o1_unsigned_not_counted,
        o1_branch_signer_not_counted,
        o1_other_tag_signer_not_counted,
        o1_other_repo_signer_not_counted,
        o1_tampered_input_not_counted,
        o1_unlisted_input_not_counted,
        o1_no_sums_not_counted,
        o1_missing_asset_not_counted,
        o1_name_objective_mismatch_not_counted,
        o1_wrong_name_is_missing,
        o1_schema_violation_not_counted,
        o1_ran_not_boolean_not_counted,
        o1_repo_mismatch_not_counted,
        o1_bad_fact_id_not_counted,
        o1_detail_disagrees_with_id_not_counted,
        o1_signed_sig_cert_counts,
        o1_no_input_anywhere_is_unmeasured,
        o3_baseline,
        o3_ran_false_is_fail,
        o3_control_false_is_fail,
        o3_control_absent_is_fail,
        o3_pass_false_is_fail,
        o3_missing_fact_is_fail,
        o3_missing_input_stays_in_denominator,
        o5_baseline,
        o5_gap_switch_is_fail,
        o5_equivalence_not_in_ci_is_fail,
        o5_kiln_not_running_is_fail,
        o5_unsigned_component_is_fail,
        o5_wasmtime_differs_is_fail,
        o5_missing_detail_is_fail,
        o5_ran_false_is_fail,
        o5_control_false_is_fail,
    );
}

/// Every case in CASES has its own #[test] (and the other way round is a
/// compile error, since each! names a function that must exist).
#[test]
fn every_case_has_its_own_test() {
    let src = include_str!("rules.rs");
    let block = src.split("mod case {").nth(1).unwrap();
    for (n, _) in CASES {
        assert!(block.contains(&format!("        {n},")), "{n} has no #[test] in mod case");
    }
}
