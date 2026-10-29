// FXM-HIDDEN-CANARY-t12: hidden test driver for t12. Never shown to the model.
use fxm_task::{crc16, encode, Counts, Event, Receiver, BROADCAST, ESC, FLAG, MAX_PAYLOAD};

#[path = "vectors.rs"]
mod vectors;

const SENTINEL: u8 = 0xA5;

fn event_code(e: Event) -> u32 {
    match e {
        Event::Nothing => 0,
        Event::Frame => 1,
        Event::Runt => 2,
        Event::BadCrc => 3,
        Event::Filtered => 4,
        Event::Abort => 5,
        Event::Overrun => 6,
    }
}

fn counts_are(c: Counts, row: u32) -> bool {
    let w = vectors::COUNTS[row as usize];
    [c.frames, c.runts, c.crc_errors, c.filtered, c.aborts, c.overruns] == w
}

fn run_case(start: usize, len: usize) -> bool {
    let mut rx = Receiver::new(0);
    let mut ok = true;
    for &(op, a, b, c, d, want, want2) in &vectors::STEPS[start..start + len] {
        let (a, b, c) = (a as usize, b as usize, c as usize);
        match op {
            0 => rx = Receiver::new(a as u8),
            1 => ok &= event_code(rx.push(a as u8)) == want,
            2 => ok &= rx.frame() == &vectors::OUTS[want as usize..want as usize + want2 as usize],
            3 => ok &= counts_are(rx.counts(), want),
            4 => {
                for _ in 0..c {
                    for &byte in &vectors::BLK[a..a + b] {
                        let _ = rx.push(byte);
                    }
                }
                ok &= counts_are(rx.counts(), want);
            }
            5 => ok &= u32::from(crc16(&vectors::BLK[a..a + b])) == want,
            _ => {
                let mut out = vec![SENTINEL; c];
                let n = encode(d as u8, &vectors::BLK[a..a + b], &mut out);
                ok &= n == want as usize;
                for (k, &v) in out.iter().enumerate() {
                    let w = if k < n { vectors::OUTS[want2 as usize + k] } else { SENTINEL };
                    ok &= v == w;
                }
            }
        }
    }
    ok
}

#[test]
fn hidden_suite() {
    assert_eq!((FLAG, ESC, BROADCAST, MAX_PAYLOAD), (0x7E, 0x7D, 0xFF, 32));
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
