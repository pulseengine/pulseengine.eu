// FXM-HIDDEN-CANARY-t01: hidden test driver for t01. Never shown to the model.
use fxm_task::{RingBuffer, CAPACITY};

#[path = "vectors.rs"]
mod vectors;

fn run_case(start: usize, len: usize) -> bool {
    let mut rb = RingBuffer::new();
    let mut ok = true;
    for &(op, arg, want_ok, want_val) in &vectors::STEPS[start..start + len] {
        let (got_ok, got_val) = match op {
            0 => {
                rb = RingBuffer::new();
                (1, 0)
            }
            1 => (u8::from(rb.push(arg)), 0),
            2 => rb.pop().map_or((0, 0), |v| (1, usize::from(v))),
            3 => rb.peek().map_or((0, 0), |v| (1, usize::from(v))),
            _ => {
                ok &= rb.is_empty() == (rb.len() == 0);
                (1, rb.len())
            }
        };
        ok &= got_ok == want_ok && got_val == usize::from(want_val);
    }
    ok
}

#[test]
fn hidden_suite() {
    assert_eq!(CAPACITY, 16);
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
