//! scripts/check-north-star.py as a WASI Preview 2 command component.
//!
//! Same seven rules, same messages on stdout, same exit codes:
//! 0 consistent · 1 a rule is broken · 2 could not run the check.
//!
//! Usage: north-star-check [--root DIR]
//! DIR is the repository (default "."); under a WASI runtime, preopen it,
//! e.g. `wasmtime run -S cli-exit-with-code=y --dir REPO::/repo
//! north-star-check.wasm --root /repo` (the -S flag carries exit code 2;
//! stable WASI 0.2 exit has only ok/err, see Cargo.toml).
//!
//! The Python script's `--self-test` is not repeated here: its planted
//! violations live in tools/north-star-check/cases.py, which runs every case
//! through both implementations and requires them to agree.

mod check;
mod py;
mod pyjson;
mod pyre;

use std::path::PathBuf;
use std::io::Write;

/// Python's text mode (`read_text`) turns "\r\n" and a lone "\r" into "\n".
pub fn universal_newlines(s: &str) -> String {
    s.replace("\r\n", "\n").replace('\r', "\n")
}

fn run() -> u8 {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut root = PathBuf::from(".");
    let mut k = 0;
    while k < args.len() {
        if args[k] == "--root" && k + 1 < args.len() {
            root = PathBuf::from(&args[k + 1]);
            k += 1;
        } else if args[k] == "--self-test" {
            eprintln!("check-north-star: --self-test lives in tools/north-star-check/cases.py for the component");
            return 2;
        }
        k += 1;
    }
    let data = root.join("data").join("north-star.toml");
    let measure_dir = root.join("data").join("north-star");
    if !data.is_file() {
        eprintln!("check-north-star: {} not found", data.display());
        return 2;
    }
    let text = match std::fs::read(&data).map(String::from_utf8) {
        Ok(Ok(t)) => universal_newlines(&t),
        Ok(Err(e)) => {
            eprintln!("check-north-star: cannot parse: {}", e);
            return 2;
        }
        Err(e) => {
            eprintln!("check-north-star: cannot parse: {}", e);
            return 2;
        }
    };
    // tomllib rejects a byte-order mark; the toml crate skips it.
    if text.starts_with('\u{feff}') {
        eprintln!("check-north-star: cannot parse: byte-order mark at the start");
        return 2;
    }
    let doc = match text.parse::<toml::Table>() {
        Ok(t) => py::from_toml(&toml::Value::Table(t)),
        Err(e) => {
            eprintln!("check-north-star: cannot parse: {}", e.message());
            return 2;
        }
    };
    let errors = match check::check(&doc, &measure_dir) {
        Ok(e) => e,
        Err(e) => {
            eprintln!("check-north-star: cannot check: {}", e);
            return 2;
        }
    };
    for e in &errors {
        println!("north-star: {}", e);
    }
    if errors.is_empty() {
        let len = |k: &str| match doc.get(k) {
            Ok(Some(py::Py::List(l))) => l.len(),
            _ => 0,
        };
        println!(
            "north-star: {} objectives, {} periods, {} products: consistent",
            len("objectives"),
            len("periods"),
            len("products")
        );
    }
    if errors.is_empty() { 0 } else { 1 }
}

fn main() {
    let code = run();
    let _ = std::io::stdout().flush();
    let _ = std::io::stderr().flush();
    // See Cargo.toml: std::process::exit(2) would reach the host as 1.
    #[cfg(all(target_os = "wasi", target_env = "p2"))]
    wasip2::cli::exit::exit_with_code(code);
    std::process::exit(code as i32)
}
