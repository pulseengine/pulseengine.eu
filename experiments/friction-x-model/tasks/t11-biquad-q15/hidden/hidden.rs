// FXM-HIDDEN-CANARY-t11: hidden test driver for t11. Never shown to the model.
use fxm_task::{Biquad, Coeffs, MAX_DECIMATION};

#[path = "vectors.rs"]
mod vectors;

fn coeffs(k: i32) -> Coeffs {
    let [b0, b1, b2, a1, a2] = vectors::COEFFS[k as usize];
    Coeffs { b0, b1, b2, a1, a2 }
}

fn run_case(start: usize, len: usize) -> bool {
    let mut f: Option<Biquad> = None;
    let mut ok = true;
    for &(op, a, b, c, want, want2) in &vectors::STEPS[start..start + len] {
        let (got, got2): (i64, i64) = match op {
            0 => match Biquad::new(coeffs(a), b as u8) {
                Some(g) => {
                    f = Some(g);
                    (1, 0)
                }
                None => (0, 0),
            },
            1 => (f.as_mut().unwrap().step(a as i16).map_or(i64::from(vectors::NONE), i64::from), 0),
            2 | 3 => {
                let (s, n, cap) = (a as usize, b as usize, c as usize);
                let input = &vectors::BLK_IN[s..s + n];
                // in place (C only) becomes a copy here: the output starts as the input
                let mut out: Vec<i16> =
                    if op == 3 { input[..cap].to_vec() } else { vec![vectors::SENTINEL; cap] };
                let (taken, made) = f.as_mut().unwrap().process(input, &mut out);
                for (k, &v) in out.iter().enumerate() {
                    let w = if k < n { vectors::BLK_OUT[s + k] } else { vectors::SENTINEL };
                    ok &= v == w;
                }
                (taken as i64, made as i64)
            }
            4 => {
                f.as_mut().unwrap().reset();
                (i64::from(want), 0)
            }
            5 => (i64::from(f.as_ref().unwrap().sat_count()), 0),
            _ => {
                let (mut emitted, mut last) = (0, 0);
                for _ in 0..b {
                    if let Some(y) = f.as_mut().unwrap().step(a as i16) {
                        emitted += 1;
                        last = i64::from(y);
                    }
                }
                (emitted, last)
            }
        };
        ok &= got == i64::from(want) && (!matches!(op, 2 | 3 | 6) || got2 == i64::from(want2));
    }
    ok
}

#[test]
fn hidden_suite() {
    assert_eq!(MAX_DECIMATION, 8);
    let mut passed = 0;
    for &(name, req, start, len) in vectors::CASES {
        if std::panic::catch_unwind(|| run_case(start, len)).unwrap_or(false) {
            passed += 1;
        } else {
            println!("FXM-FAIL {name} [{req}]");
        }
    }
    println!("FXM-RESULT passed={passed} total={}", vectors::CASES.len());
    assert_eq!(passed, vectors::CASES.len());
}
