// FXM-HIDDEN-CANARY-t02: hidden test driver for t02. Never shown to the model.
use fxm_task::{abs, add, mul, neg, sub, Q15};

#[path = "vectors.rs"]
mod vectors;

const REQ: [&str; 5] = ["Q1", "Q2", "Q3", "Q4", "Q5"];

#[test]
fn hidden_suite() {
    let mut passed = 0;
    let mut shown = 0;
    for (k, &(op, a, b, want)) in vectors::VECS.iter().enumerate() {
        let (a, b) = (a as Q15, b as Q15);
        let got = std::panic::catch_unwind(|| match op {
            0 => add(a, b),
            1 => sub(a, b),
            2 => mul(a, b),
            3 => neg(a),
            _ => abs(a),
        });
        if matches!(got, Ok(g) if i32::from(g) == want) {
            passed += 1;
        } else if shown < 20 {
            shown += 1;
            println!("FXM-FAIL vec{k} [{}] a={a} b={b}", REQ[op as usize]);
        }
    }
    println!("FXM-RESULT passed={passed} total={}", vectors::VECS.len());
    assert_eq!(passed, vectors::VECS.len());
}
