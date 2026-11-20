// rivet: verifies REQ-NORTH-STAR-MEASURE
//! The binary: exit codes, what it writes (and when it writes nothing), and
//! that --help states the counting rules.

mod common;

use common::{fact, input, stub_cosign, Fx, Sign};
use north_star_measure::{Objective, COMMON_RULES};
use serde_json::{json, Value};
use std::process::{Command, Output};

fn bin(fx: &Fx, args: &[&str], cosign: Option<&std::path::Path>) -> Output {
    let mut c = Command::new(env!("CARGO_BIN_EXE_north-star-measure"));
    c.args(args).arg("--root").arg(&fx.root).arg("--offline").arg(&fx.fixtures);
    match cosign {
        Some(p) => c.env("COSIGN", p),
        // An empty PATH and a COSIGN that does not exist: no cosign anywhere.
        None => c.env("COSIGN", fx.root.join("no-cosign-here")).env("PATH", ""),
    };
    c.output().unwrap()
}

fn gates() -> Value {
    let d = json!({"signed": true, "kiln_runs": true, "wasmtime_equal": true, "equivalence_in_ci": true, "gap_switch": false});
    input("O5", "kiln", vec![fact("g1", true, true, Some(true), d.clone()), fact("g2", true, true, Some(true), d)])
}

fn out_file(fx: &Fx, id: &str) -> std::path::PathBuf {
    fx.root.join("data").join("north-star").join(format!("{id}.json"))
}

#[test]
fn cosign_absent_exits_2_and_writes_nothing() {
    let fx = Fx::new(&[("kiln", &["O5"])], &["O5"]);
    fx.publish("kiln", "v0.9.0", &gates(), Sign::Good);
    let o = bin(&fx, &["o5"], None);
    assert_eq!(o.status.code(), Some(2), "{}", String::from_utf8_lossy(&o.stderr));
    assert!(String::from_utf8_lossy(&o.stderr).contains("cosign not found"));
    assert!(!out_file(&fx, "O5").exists());
}

#[test]
fn no_input_exits_2_and_writes_nothing() {
    let fx = Fx::new(&[("kiln", &["O5"])], &[]);
    fx.publish("kiln", "v0.9.0", &gates(), Sign::NoAsset);
    let o = bin(&fx, &["o5"], Some(&stub_cosign()));
    assert_eq!(o.status.code(), Some(2));
    let err = String::from_utf8_lossy(&o.stderr);
    assert!(err.contains("no product publishes") && err.contains("stays unmeasured, never 0"), "{err}");
    assert!(!out_file(&fx, "O5").exists());
}

#[test]
fn no_product_pulling_exits_2() {
    let fx = Fx::new(&[("jess", &["O1"])], &[]);
    let o = bin(&fx, &["o5"], Some(&stub_cosign()));
    assert_eq!(o.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&o.stderr).contains("no product in data/north-star.toml pulls O5"));
}

#[test]
fn measured_and_state_measured_exits_0_with_the_o2_shape() {
    let fx = Fx::new(&[("kiln", &["O5"])], &["O5"]);
    fx.publish("kiln", "v0.9.0", &gates(), Sign::Good);
    let o = bin(&fx, &["O5"], Some(&stub_cosign()));
    assert_eq!(o.status.code(), Some(0), "{}", String::from_utf8_lossy(&o.stderr));
    let d: Value = serde_json::from_str(&std::fs::read_to_string(out_file(&fx, "O5")).unwrap()).unwrap();
    let keys: Vec<&str> = d.as_object().unwrap().keys().map(String::as_str).collect();
    for k in ["schema_version", "objective", "measured_at", "verifier", "as_of", "value", "of", "items", "blind_spot"] {
        assert!(keys.contains(&k), "missing {k}: {keys:?}");
    }
    assert_eq!((d["schema_version"].as_u64(), d["value"].as_u64(), d["of"].as_u64()), (Some(1), Some(2), Some(2)));
    assert_eq!(d["objective"], "O5");
    let bs = d["blind_spot"].as_str().unwrap();
    for r in COMMON_RULES {
        assert!(bs.contains(r), "blind_spot lacks the rule {r:?}");
    }
    assert!(bs.contains(Objective::O5.rule()));
    assert!(d["measured_at"].as_str().unwrap().ends_with('Z'));
}

#[test]
fn measured_while_toml_says_unmeasured_exits_1() {
    // Rule 7: a written O5.json with state "unmeasured" is inconsistent until
    // the same PR flips the state.
    let fx = Fx::new(&[("kiln", &["O5"])], &[]);
    fx.publish("kiln", "v0.9.0", &gates(), Sign::Good);
    let o = bin(&fx, &["o5"], Some(&stub_cosign()));
    assert_eq!(o.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&o.stderr).contains("rule 7"));
    assert!(out_file(&fx, "O5").exists());
}

#[test]
fn snapshot_matches_ignores_time_and_catches_a_changed_value() {
    let fx = Fx::new(&[("kiln", &["O5"])], &["O5"]);
    fx.publish("kiln", "v0.9.0", &gates(), Sign::Good);
    assert_eq!(bin(&fx, &["o5"], Some(&stub_cosign())).status.code(), Some(0));
    let live = out_file(&fx, "O5");
    let mut d: Value = serde_json::from_str(&std::fs::read_to_string(&live).unwrap()).unwrap();
    let cmp = |d: &Value| {
        let c = fx.root.join("committed.json");
        std::fs::write(&c, serde_json::to_vec(d).unwrap()).unwrap();
        Command::new(env!("CARGO_BIN_EXE_north-star-measure")).arg("snapshot-matches").arg(&c).arg(&live).output().unwrap().status.code()
    };
    d["measured_at"] = json!("2020-01-01T00:00Z");
    assert_eq!(cmp(&d), Some(0), "a different time is not staleness");
    d["value"] = json!(1);
    assert_eq!(cmp(&d), Some(1), "a different value is stale");
    d["value"] = json!(2);
    d["inputs"][0]["release"] = json!("v0.8.0");
    assert_eq!(cmp(&d), Some(1), "a different release is stale");
}

#[test]
fn help_states_every_counting_rule() {
    let o = Command::new(env!("CARGO_BIN_EXE_north-star-measure")).arg("--help").output().unwrap();
    assert_eq!(o.status.code(), Some(0));
    let h = String::from_utf8_lossy(&o.stdout);
    for r in COMMON_RULES {
        assert!(h.contains(r), "--help lacks {r:?}");
    }
    for ob in [Objective::O1, Objective::O3, Objective::O5] {
        assert!(h.contains(ob.rule()), "--help lacks the {} rule", ob.id());
    }
}

#[test]
fn usage_errors_exit_2() {
    let fx = Fx::new(&[], &[]);
    for args in [&["o2"][..], &[][..], &["o1", "--bogus"][..]] {
        let o = bin(&fx, args, Some(&stub_cosign()));
        assert_eq!(o.status.code(), Some(2), "{args:?}");
    }
}

/// The identity regexp against a real signed release, with the real cosign.
/// Needs the network and cosign, so it is not part of the default run:
/// `cargo test -- --ignored real_cosign`.
#[test]
#[ignore]
fn real_cosign_accepts_jess_v0_7_3_and_rejects_another_tag() {
    use north_star_measure::verify::{cosign_verify, find_cosign, identity_regexp, Signature};
    let cosign = find_cosign().expect("cosign on PATH");
    let fx = Fx::new(&[], &[]);
    let base = "https://github.com/pulseengine/jess/releases/download/v0.7.3";
    for n in ["SHA256SUMS.txt", "SHA256SUMS.txt.cosign.bundle"] {
        let st = Command::new("curl").args(["-fsSL", "-o"]).arg(fx.root.join(n)).arg(format!("{base}/{n}")).status().unwrap();
        assert!(st.success(), "download {n}");
    }
    let sums = fx.root.join("SHA256SUMS.txt");
    let sig = Signature::Bundle(fx.root.join("SHA256SUMS.txt.cosign.bundle"));
    cosign_verify(&cosign, &sums, &sig, &identity_regexp("pulseengine", "jess", "v0.7.3")).expect("real signature verifies");
    assert!(cosign_verify(&cosign, &sums, &sig, &identity_regexp("pulseengine", "jess", "v0.7.2")).is_err());
    assert!(cosign_verify(&cosign, &sums, &sig, &identity_regexp("pulseengine", "kiln", "v0.7.3")).is_err());
}
