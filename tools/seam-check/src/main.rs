//! seam-check: see `seam-check --help` and the seam-contract SKILL.md.

use std::io::Write;

fn main() {
    let argv: Vec<String> = std::env::args().skip(1).collect();
    let mut out = String::new();
    let code = match seam_check::cli::run(&argv, &mut out) {
        Ok(code) => code,
        Err(crash) => {
            // Where seam-check.py dies with a traceback: nothing on stdout, exit 1.
            eprintln!("seam-check: internal error: {}", crash.0);
            out.clear();
            1
        }
    };
    let mut so = std::io::stdout().lock();
    let _ = so.write_all(out.as_bytes());
    let _ = so.flush();
    std::process::exit(code);
}
