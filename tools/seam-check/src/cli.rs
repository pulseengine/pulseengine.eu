//! The argparse surface of seam-check.py: the same long options, `--opt=value`,
//! unique-prefix abbreviations, repeatable `--issue/--block/--party`, choices,
//! and exit 2 with a usage line on stderr for anything argparse refuses.

use crate::check::{run_args, Args, Fail};
use crate::pyval::Crash;
use crate::transport::{resolve_token, Fixtures, GitHub, Source, GITHUB_API};

pub const USAGE: &str = "usage: seam-check.py [-h] [--org ORG] [--label LABEL] [--issue OWNER/REPO#N]
                     [--block FILE] [--party OWNER/REPO] [--fixtures DIR]
                     [--api API] [--http {auto,curl,urllib}]
                     [--format {text,json}] [--stale-days STALE_DAYS]
                     [--strict] [--now NOW] [--self-test]
";

/// argparse's help at 80 columns (Python 3.14).
pub const HELP: &str = "usage: seam-check.py [-h] [--org ORG] [--label LABEL] [--issue OWNER/REPO#N]
                     [--block FILE] [--party OWNER/REPO] [--fixtures DIR]
                     [--api API] [--http {auto,curl,urllib}]
                     [--format {text,json}] [--stale-days STALE_DAYS]
                     [--strict] [--now NOW] [--self-test]

Check seam contract blocks.

options:
  -h, --help            show this help message and exit
  --org ORG
  --label LABEL
  --issue OWNER/REPO#N
  --block FILE
  --party OWNER/REPO
  --fixtures DIR
  --api API
  --http {auto,curl,urllib}
  --format {text,json}
  --stale-days STALE_DAYS
  --strict              warnings fail too
  --now NOW             YYYY-MM-DD (default: today, UTC)
  --self-test
";

const VALUED: [&str; 11] = [
    "--org", "--label", "--issue", "--block", "--party", "--fixtures", "--api", "--http", "--format", "--stale-days", "--now",
];
const FLAGS: [&str; 3] = ["--strict", "--self-test", "--help"];

pub enum Parsed {
    Run(Args, bool),
    Help,
    Error(String),
}

/// Python's int() on a command-line string: whitespace, a sign, digits and
/// single underscores between digits.
fn py_int(s: &str) -> Option<i128> {
    let t = s.trim_matches(crate::text::py_space);
    let (neg, digits) = match t.strip_prefix('-') {
        Some(r) => (true, r),
        None => (false, t.strip_prefix('+').unwrap_or(t)),
    };
    if digits.is_empty() || digits.starts_with('_') || digits.ends_with('_') || digits.contains("__") {
        return None;
    }
    let clean: String = digits.chars().filter(|c| *c != '_').collect();
    if !clean.chars().all(|c| c.is_ascii_digit()) {
        return None;
    }
    let v: i128 = clean.parse().ok()?;
    Some(if neg { -v } else { v })
}

fn negative_number(s: &str) -> bool {
    // argparse: '^-\d+$|^-\d*\.\d+$'
    let Some(r) = s.strip_prefix('-') else { return false };
    let r = r.strip_suffix('\n').unwrap_or(r);
    if !r.is_empty() && r.chars().all(|c| c.is_ascii_digit()) {
        return true;
    }
    match r.split_once('.') {
        Some((a, b)) => a.chars().all(|c| c.is_ascii_digit()) && !b.is_empty() && b.chars().all(|c| c.is_ascii_digit()),
        None => false,
    }
}

fn all_options() -> Vec<&'static str> {
    VALUED.iter().chain(FLAGS.iter()).copied().collect()
}

/// argparse `_parse_optional`: Some(option, explicit value) when `arg` is an
/// option, Ok(None) when it is a plain value, Err for an ambiguous prefix.
#[allow(clippy::type_complexity)]
fn classify(arg: &str) -> Result<Option<(Option<&'static str>, Option<String>)>, String> {
    if arg.is_empty() || !arg.starts_with('-') {
        return Ok(None);
    }
    let opts = all_options();
    if arg == "-h" {
        return Ok(Some((Some("--help"), None)));
    }
    if let Some(o) = opts.iter().find(|o| **o == arg) {
        return Ok(Some((Some(o), None)));
    }
    if arg.len() == 1 {
        return Ok(None);
    }
    if let Some((name, value)) = arg.split_once('=') {
        if let Some(o) = opts.iter().find(|o| **o == name) {
            return Ok(Some((Some(o), Some(value.to_string()))));
        }
    }
    // Unique-prefix abbreviations of long options.
    if arg.starts_with("--") {
        let (name, value) = match arg.split_once('=') {
            Some((n, v)) => (n, Some(v.to_string())),
            None => (arg, None),
        };
        let hits: Vec<&'static str> = opts.iter().filter(|o| o.starts_with(name)).copied().collect();
        if hits.len() > 1 {
            return Err(format!("ambiguous option: {} could match {}", name, hits.join(", ")));
        }
        if hits.len() == 1 {
            return Ok(Some((Some(hits[0]), value)));
        }
    } else if arg.starts_with('-') && !arg.starts_with("--") {
        // single-dash: only -h exists; '-hX' style is -h with an explicit arg.
        if arg.starts_with("-h") && arg.len() > 2 {
            return Err(format!("argument -h/--help: ignored explicit argument {}", &arg[2..]));
        }
    }
    if negative_number(arg) {
        return Ok(None);
    }
    if arg.contains(' ') {
        return Ok(None);
    }
    Ok(Some((None, None)))
}

pub fn parse(argv: &[String]) -> Parsed {
    let mut a = Args {
        org: "pulseengine".into(),
        label: "seam".into(),
        issue: vec![],
        block: vec![],
        party: vec![],
        fixtures: None,
        api: std::env::var("GITHUB_API_URL").unwrap_or_else(|_| GITHUB_API.to_string()),
        http: "auto".into(),
        format: "text".into(),
        stale_days: 30,
        strict: false,
        now: None,
    };
    let mut self_test = false;
    let mut unknown: Vec<String> = vec![];
    let mut i = 0;
    let mut only_positional = false;
    while i < argv.len() {
        let arg = &argv[i];
        i += 1;
        if only_positional {
            unknown.push(arg.clone());
            continue;
        }
        if arg == "--" {
            only_positional = true;
            continue;
        }
        let (opt, explicit) = match classify(arg) {
            Err(e) => return Parsed::Error(e),
            Ok(None) => {
                unknown.push(arg.clone());
                continue;
            }
            Ok(Some((None, _))) => {
                unknown.push(arg.clone());
                continue;
            }
            Ok(Some((Some(o), v))) => (o, v),
        };
        if FLAGS.contains(&opt) {
            if explicit.is_some() {
                return Parsed::Error(format!("argument {}: ignored explicit argument", opt));
            }
            match opt {
                "--help" => return Parsed::Help,
                "--strict" => a.strict = true,
                _ => self_test = true,
            }
            continue;
        }
        let value = match explicit {
            Some(v) => v,
            None => {
                let Some(next) = argv.get(i) else {
                    return Parsed::Error(format!("argument {}: expected one argument", opt));
                };
                match classify(next) {
                    Ok(None) => {}
                    _ if next == "--" => return Parsed::Error(format!("argument {}: expected one argument", opt)),
                    _ => return Parsed::Error(format!("argument {}: expected one argument", opt)),
                }
                i += 1;
                next.clone()
            }
        };
        match opt {
            "--org" => a.org = value,
            "--label" => a.label = value,
            "--issue" => a.issue.push(value),
            "--block" => a.block.push(value),
            "--party" => a.party.push(value),
            "--fixtures" => a.fixtures = Some(value),
            "--api" => a.api = value,
            "--http" => {
                if !["auto", "curl", "urllib"].contains(&value.as_str()) {
                    return Parsed::Error(format!("argument --http: invalid choice: '{}'", value));
                }
                a.http = value
            }
            "--format" => {
                if !["text", "json"].contains(&value.as_str()) {
                    return Parsed::Error(format!("argument --format: invalid choice: '{}'", value));
                }
                a.format = value
            }
            "--stale-days" => match py_int(&value) {
                Some(n) => a.stale_days = n,
                None => return Parsed::Error(format!("argument --stale-days: invalid int value: '{}'", value)),
            },
            _ => a.now = Some(value),
        }
    }
    if !unknown.is_empty() {
        return Parsed::Error(format!("unrecognized arguments: {}", unknown.join(" ")));
    }
    Parsed::Run(a, self_test)
}

/// `run(argv)`: Ok(exit code) with the stdout text in `out`, Err on a crash.
pub fn run(argv: &[String], out: &mut String) -> Result<i32, Crash> {
    match parse(argv) {
        Parsed::Help => {
            out.push_str(HELP);
            Ok(0)
        }
        Parsed::Error(e) => {
            eprint!("{}", USAGE);
            eprintln!("seam-check.py: error: {}", e);
            Ok(2)
        }
        Parsed::Run(_, true) => Ok(crate::selftest::self_test(out)),
        Parsed::Run(a, false) => {
            let fixtures = a.fixtures.clone();
            let (api, http) = (a.api.clone(), a.http.clone());
            let mut make = move || -> Result<Box<dyn Source>, Fail> {
                match &fixtures {
                    Some(d) => Ok(Box::new(Fixtures::new(d)?)),
                    None => {
                        let env = |k: &str| std::env::var(k).ok();
                        Ok(Box::new(GitHub::new(&api, resolve_token(&api, &env), &http)))
                    }
                }
            };
            run_args(&a, out, &mut make)
        }
    }
}
