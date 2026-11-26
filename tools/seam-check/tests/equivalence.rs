// rivet: verifies REQ-SEAM-CHECK-RUST

//! Equivalence gate: seam-check.py (the reference, while it exists) and this
//! binary run on the same inputs and must print the same stdout and exit with
//! the same code. Inputs: `--self-test`, every self-test fixture case in text
//! and JSON, the --block drafts, the 2026-10-29 drone-seam pilot, six real
//! seam issues recorded 2026-11-19 (tests/seam-contract/real), CLI edge cases,
//! YAML edge cases, and the HTTP path against a loopback stub (urllib vs the
//! std client, curl vs curl).
//!
//! Two normalisations, and only these: the parser's own words after
//! "block is not valid YAML: " (PyYAML and rivet-yaml word a syntax error
//! differently), and the elapsed time curl prints in a connect error
//! ("after 0 ms" vs "after 3 ms" made one run flaky). The rule, the prefix,
//! the exit code and every other byte must match. The count of cases that
//! needed the parser normalisation is printed.
//!
//! Negative control: two planted mutants of the Python script (one rule, one
//! output format) must each make at least one case differ, so a harness that
//! compares nothing cannot pass.
//!
//! The reference needs python3 with PyYAML. Without it the test FAILS rather
//! than skips: SEAM_CHECK_PYTHON names another interpreter.

use seam_check::selftest::{self, block, sub, write_world, Route, Scratch, Stub, World, GOOD};
use std::path::{Path, PathBuf};
use std::process::Command;

const PARSE_PREFIX: &str = "block is not valid YAML: ";

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn script() -> PathBuf {
    root().join("claude-tooling/plugins/pulseengine-claude/skills/seam-contract/seam-check.py")
}

fn python() -> String {
    let py = std::env::var("SEAM_CHECK_PYTHON").unwrap_or_else(|_| "python3".into());
    let ok = Command::new(&py).args(["-c", "import yaml"]).output().map(|o| o.status.success()).unwrap_or(false);
    assert!(ok, "the reference needs {} with PyYAML (set SEAM_CHECK_PYTHON); refusing to pass without it", py);
    py
}

struct Case {
    name: String,
    args: Vec<String>,
    /// Run against a loopback stub; "{api}" in args becomes its URL.
    stub: Option<Vec<Route>>,
    /// Compare only the exit code and the first stdout line (argparse help
    /// wording differs across Python versions).
    first_line_only: bool,
}

fn case(name: &str, args: &[&str]) -> Case {
    Case { name: name.into(), args: args.iter().map(|x| x.to_string()).collect(), stub: None, first_line_only: false }
}

fn s(p: &Path) -> String {
    p.to_string_lossy().into_owned()
}

fn yaml_edges() -> Vec<(&'static str, String)> {
    let g = |old: &str, new: &str| sub(old, new, GOOD);
    vec![
        ("unquoted date stays a string", g("date: \"2026-10-20\"", "date: 2026-10-20")),
        ("int format 2", g("format: 1", "format: 2")),
        ("format false", g("format: 1", "format: false")),
        ("format true", g("format: 1", "format: true")),
        ("format float", g("format: 1", "format: 1.0")),
        ("format string", g("format: 1", "format: \"1\"")),
        ("null provider", g("provider:\n  repo: acme/provider\n  promise: \"the WIT package and not changing it without telling the consumer\"\n  guard: scripts/one-exporter.sh\n", "provider: ~\n")),
        ("empty kind", g("kind: consumption", "kind: \"\"")),
        ("int kind", g("kind: consumption", "kind: 7")),
        ("seam id with capitals", g("seam: provider-consumer/example", "seam: Provider/Example")),
        ("seam id as block scalar", g("seam: provider-consumer/example", "seam: |\n  provider-consumer/example")),
        ("unicode in a key", g("kind: consumption", "kind: consumption\nkïnd: x")),
        ("int key", g("kind: consumption", "kind: consumption\n7: x")),
        ("quote in a value", g("kind: consumption", "kind: \"it's\"")),
        ("tab and newline in a value", g("kind: consumption", "kind: \"a\\tb\\nc\"")),
        ("open_questions as a string", g("open_questions:\n  - q: \"where does battery-v live?\"\n    owner: acme/consumer\n", "open_questions: \"ab\"\n")),
        ("open_questions as a mapping", g("open_questions:\n  - q: \"where does battery-v live?\"\n    owner: acme/consumer\n", "open_questions: {a: 1}\n")),
        ("open_questions as a number", g("open_questions:\n  - q: \"where does battery-v live?\"\n    owner: acme/consumer\n", "open_questions: 5\n")),
        ("consumers as a number", g("consumers:\n  - repo: acme/consumer\n    binding: \"the host that calls it\"\n    guard: tools/check-pin.sh\n", "consumers: 5\n")),
        ("consumer repo a list", g("  - repo: acme/consumer\n", "  - repo: [acme/consumer]\n")),
        ("interface a mapping", g("interface:\n  - kind: wit\n    path: wit/api.wit\n    package: \"acme:api\"\n    version: \"0.2.0\"\n    interfaces: [controller]\n  - kind: file", "interface:\n  kind: file")),
        ("interface ref pinned", g("    path: src/wire.rs\n", "    path: src/wire.rs\n    ref: v1\n")),
        ("interface repo elsewhere", g("    path: src/wire.rs\n", "    path: src/wire.rs\n    repo: acme/consumer\n")),
        ("interfaces as a string", g("interfaces: [controller]", "interfaces: controller")),
        ("symbols with an empty string", g("symbols: [\"pub const VERSION: u8 = 2;\"]", "symbols: [\"pub const VERSION: u8 = 2;\", \"\"]")),
        ("guard an empty list", g("guard: tools/check-pin.sh", "guard: []")),
        ("decision date a number", g("date: \"2026-10-20\"", "date: 20261020")),
        ("decision date invalid day", g("date: \"2026-10-20\"", "date: \"2026-02-30\"")),
        ("recommendation a number", g("status: decided", "status: options").replace("recommendation: step", "recommendation: 3")),
        ("anchor and alias", g("kind: consumption", "kind: &k consumption\nnotes: *k")),
        ("block scalar notes", g("kind: consumption", "kind: consumption\nnotes: >\n  folded\n  text\n")),
        ("flow mapping options", g("options:\n  - id: step\n    summary: \"synchronous step per tick\"\n", "options:\n  - {id: step, summary: \"synchronous step per tick\"}\n")),
        ("version float 1.10", g("version: \"0.2.0\"", "version: 1.10")),
        ("version int", g("version: \"0.2.0\"", "version: 2")),
        ("empty block", String::new()),
        ("comment-only block", "# nothing\n".into()),
        ("scalar block", "just text\n".into()),
        ("tab indentation", "format: 1\nprovider:\n\trepo: x\n".into()),
        ("unclosed quote", g("kind: consumption", "kind: \"consumption")),
        ("multi-document", format!("{}---\na: 1\n", GOOD)),
        ("stale decided", GOOD.to_string()),
        ("non-ascii summary", g("summary: \"step at the core boundary\"", "summary: \"Schritt über die Grenze – ok\"")),
    ]
}

fn cases(tmp: &Path) -> Vec<Case> {
    let mut out = vec![case("--self-test", &["--self-test"])];

    // Every self-test fixture case, in both output formats.
    for (n, (name, w, extra, _)) in selftest::cases().into_iter().enumerate() {
        let d = write_world(&tmp.join(format!("w{}", n)), &w).expect("world");
        for fmt in ["text", "json"] {
            let mut args = vec!["--fixtures".to_string(), s(&d), "--format".into(), fmt.into()];
            args.extend(extra.iter().cloned());
            out.push(Case { name: format!("self-test case {} [{}]", name, fmt), args, stub: None, first_line_only: false });
        }
    }

    // The --block draft path, and YAML edge cases as drafts.
    let blk = write_world(&tmp.join("blk"), &World { body: "prose".into(), labels: Some(vec![]), ..Default::default() })
        .expect("world");
    let mut drafts: Vec<(String, String)> = vec![
        ("--block draft".into(), GOOD.to_string()),
        ("--block draft with version drift".into(), sub("\"0.2.0\"", "\"0.3.0\"", GOOD)),
        ("--block draft already fenced".into(), block(GOOD)),
        ("--block draft without final newline".into(), GOOD.trim_end().to_string()),
    ];
    drafts.extend(yaml_edges().into_iter().map(|(n, t)| (format!("yaml edge: {}", n), t)));
    for (n, (name, text)) in drafts.into_iter().enumerate() {
        let f = tmp.join(format!("draft{}.seam", n));
        std::fs::write(&f, text).expect("draft");
        for fmt in ["text", "json"] {
            out.push(Case {
                name: format!("{} [{}]", name, fmt),
                args: vec![
                    "--fixtures".into(), s(&blk), "--block".into(), s(&f), "--now".into(), "2026-10-29".into(),
                    "--org".into(), "acme".into(), "--format".into(), fmt.into(),
                ],
                stub: None,
                first_line_only: false,
            });
        }
    }

    // Recorded worlds: the drone-seam pilot and six real seam issues.
    let pilot = s(&root().join("tests/seam-contract/pilot"));
    let real = s(&root().join("tests/seam-contract/real"));
    let drift = tmp.join("drift.md");
    let pilot589 = std::fs::read_to_string(root().join("tests/seam-contract/pilot/blocks/relay-589.md")).expect("pilot");
    std::fs::write(&drift, pilot589.replace("version: \"0.12.0\"", "version: \"0.11.0\"")).expect("drift");
    let drift = s(&drift);
    let world_runs: Vec<(&str, Vec<&str>)> = vec![
        ("pilot", vec!["--fixtures", &pilot, "--now", "2026-10-29"]),
        ("pilot later, strict", vec!["--fixtures", &pilot, "--now", "2027-06-01", "--strict"]),
        ("pilot later, stale-days 0", vec!["--fixtures", &pilot, "--now", "2026-11-19", "--stale-days", "0"]),
        ("pilot --party relay", vec!["--fixtures", &pilot, "--now", "2026-10-29", "--party", "pulseengine/relay"]),
        ("pilot --party jess", vec!["--fixtures", &pilot, "--now", "2026-10-29", "--party", "pulseengine/jess"]),
        ("pilot drift block", vec!["--fixtures", &pilot, "--block", &drift, "--now", "2026-10-29"]),
        ("real", vec!["--fixtures", &real, "--now", "2026-11-19"]),
        ("real later, strict", vec!["--fixtures", &real, "--now", "2027-06-01", "--strict"]),
        ("real --party plant", vec!["--fixtures", &real, "--now", "2026-11-19", "--party", "pulseengine/plant"]),
        ("real --party warte", vec!["--fixtures", &real, "--now", "2026-11-19", "--party", "pulseengine/warte"]),
        ("real --party sieve + gale", vec!["--fixtures", &real, "--now", "2026-11-19", "--party", "pulseengine/sieve", "--party", "pulseengine/gale"]),
        ("real --party nobody", vec!["--fixtures", &real, "--now", "2026-11-19", "--party", "pulseengine/nobody"]),
        ("real other org", vec!["--fixtures", &real, "--now", "2026-11-19", "--org", "acme"]),
        ("real other label", vec!["--fixtures", &real, "--now", "2026-11-19", "--label", "bug"]),
        ("real --issue warte#185", vec!["--fixtures", &real, "--now", "2026-11-19", "--issue", "pulseengine/warte#185"]),
        ("real --issue plant#8 and sieve#3", vec!["--fixtures", &real, "--now", "2026-11-19", "--issue", "pulseengine/plant#8", "--issue", "pulseengine/sieve#3"]),
        ("real --issue missing", vec!["--fixtures", &real, "--now", "2026-11-19", "--issue", "pulseengine/warte#1"]),
        ("real --issue bad spec", vec!["--fixtures", &real, "--now", "2026-11-19", "--issue", "warte#185"]),
        ("missing fixture dir", vec!["--fixtures", "does/not/exist", "--now", "2026-11-19"]),
        ("bad --now", vec!["--fixtures", &real, "--now", "19.11.2026"]),
        ("--now=, --format=json", vec!["--fixtures", &real, "--now=2026-11-19", "--format=json"]),
        ("abbreviated options", vec!["--fix", &real, "--no", "2026-11-19", "--form", "json"]),
        ("ambiguous abbreviation", vec!["--fixtures", &real, "--s"]),
        ("unknown option", vec!["--fixtures", &real, "--bogus"]),
        ("positional argument", vec!["--fixtures", &real, "extra"]),
        ("bad --format", vec!["--fixtures", &real, "--format", "yaml"]),
        ("bad --http", vec!["--fixtures", &real, "--http", "wget"]),
        ("--stale-days negative", vec!["--fixtures", &real, "--now", "2026-11-19", "--stale-days", "-5"]),
        ("--stale-days not a number", vec!["--fixtures", &real, "--stale-days", "x"]),
        ("--issue without value", vec!["--fixtures", &real, "--issue"]),
        ("--strict=1", vec!["--fixtures", &real, "--strict=1"]),
    ];
    for (name, args) in world_runs {
        for fmt in ["text", "json"] {
            let mut a: Vec<String> = args.iter().map(|x| x.to_string()).collect();
            a.extend(["--format".to_string(), fmt.to_string()]);
            out.push(Case { name: format!("{} [{}]", name, fmt), args: a, stub: None, first_line_only: false });
        }
    }
    let mut help = case("--help", &["--help"]);
    help.first_line_only = true;
    out.push(help);

    // The HTTP path, against one loopback stub per case.
    for (name, routes, _) in selftest::http_cases() {
        for mode in ["urllib", "curl"] {
            for fmt in ["text", "json"] {
                out.push(Case {
                    name: format!("{} [{}, {}]", name, mode, fmt),
                    args: ["--api", "{api}", "--http", mode, "--now", "2026-10-29", "--org", "acme", "--format", fmt]
                        .iter()
                        .map(|x| x.to_string())
                        .collect(),
                    stub: Some(routes.clone()),
                    first_line_only: false,
                });
            }
        }
    }
    for mode in ["urllib", "curl"] {
        out.push(Case {
            name: format!("http: --issue answered by the wrong route [{}]", mode),
            args: ["--api", "{api}", "--http", mode, "--now", "2026-10-29", "--issue", "acme/consumer#1"]
                .iter()
                .map(|x| x.to_string())
                .collect(),
            stub: Some(selftest::ok_routes()),
            first_line_only: false,
        });
        out.push(Case {
            name: format!("http: nothing listening [{}]", mode),
            args: ["--api", "http://127.0.0.1:9", "--http", mode, "--now", "2026-10-29", "--org", "acme"]
                .iter()
                .map(|x| x.to_string())
                .collect(),
            stub: None,
            first_line_only: false,
        });
    }
    out
}

fn exec(prog: &str, pre: &[String], args: &[String]) -> (String, i32) {
    let o = Command::new(prog)
        .args(pre)
        .args(args)
        .env("COLUMNS", "80")
        .env("NO_COLOR", "1")
        .env_remove("GITHUB_TOKEN")
        .env_remove("GH_TOKEN")
        .env_remove("GITHUB_API_URL")
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .output()
        .expect("spawn");
    (String::from_utf8_lossy(&o.stdout).into_owned(), o.status.code().unwrap_or(-1))
}

/// Replace curl's elapsed time in "after N ms" with a fixed token. Only lines
/// carrying a curl error are touched, so no other number can be masked.
fn mask_curl_elapsed(l: &str) -> String {
    if !l.contains("curl: (") {
        return l.to_string();
    }
    let mut out = String::new();
    let mut rest = l;
    while let Some(i) = rest.find("after ") {
        out.push_str(&rest[..i + 6]);
        rest = &rest[i + 6..];
        let n = rest.bytes().take_while(u8::is_ascii_digit).count();
        if n > 0 && rest[n..].starts_with(" ms") {
            out.push_str("<n>");
            rest = &rest[n..];
        }
    }
    out.push_str(rest);
    out
}

/// Cut the parser's own words after the parse prefix, in text and JSON, and
/// mask curl's elapsed time.
fn normalize(out: &str) -> String {
    out.lines()
        .map(mask_curl_elapsed)
        .map(|l| match l.find(PARSE_PREFIX) {
            Some(i) => {
                let tail = if l.trim_end().ends_with('"') { "\"" } else { "" };
                format!("{}{}<parser detail>{}", &l[..i], PARSE_PREFIX, tail)
            }
            None => l,
        })
        .collect::<Vec<_>>()
        .join("\n")
}

#[test]
fn curl_elapsed_mask_is_narrow() {
    let a = "error: GET x failed: curl exit 7: curl: (7) Failed to connect to 127.0.0.1 port 9 after 0 ms: Couldn't connect";
    let b = a.replace("after 0 ms", "after 3 ms");
    assert_eq!(mask_curl_elapsed(a), mask_curl_elapsed(&b));
    // a different port still differs, and lines without a curl error are untouched
    assert_ne!(mask_curl_elapsed(a), mask_curl_elapsed(&a.replace("port 9", "port 8")));
    assert_eq!(mask_curl_elapsed("retry after 5 ms"), "retry after 5 ms");
}

struct Tally {
    total: usize,
    identical: usize,
    normalized: usize,
    diffs: Vec<String>,
}

fn compare(py: &str, script: &Path, tmp: &Path) -> Tally {
    let bin = env!("CARGO_BIN_EXE_seam-check");
    let mut t = Tally { total: 0, identical: 0, normalized: 0, diffs: vec![] };
    for c in cases(tmp) {
        let stub = c.stub.clone().map(Stub::start);
        let args: Vec<String> = match &stub {
            Some(st) => c.args.iter().map(|a| a.replace("{api}", &format!("http://127.0.0.1:{}", st.port))).collect(),
            None => c.args.clone(),
        };
        let (po, pc) = exec(py, &[s(script)], &args);
        let (ro, rc) = exec(bin, &[], &args);
        drop(stub);
        t.total += 1;
        let (pn, rn) = if c.first_line_only {
            (po.lines().next().unwrap_or("").to_string(), ro.lines().next().unwrap_or("").to_string())
        } else {
            (normalize(&po), normalize(&ro))
        };
        if pc == rc && pn == rn {
            t.identical += 1;
            if po != ro && !c.first_line_only {
                t.normalized += 1;
            }
        } else {
            t.diffs.push(format!(
                "--- {}\nargs: {:?}\npython exit {}:\n{}\nrust exit {}:\n{}",
                c.name, args, pc, po, rc, ro
            ));
        }
    }
    t
}

#[test]
fn rust_matches_python_on_every_case() {
    let py = python();
    let tmp = Scratch::new("equiv");
    let t = compare(&py, &script(), &tmp.0);
    for d in &t.diffs {
        eprintln!("{}", d);
    }
    println!(
        "equivalence: {}/{} cases identical (stdout and exit code); {} needed the parser-detail normalisation",
        t.identical, t.total, t.normalized
    );
    assert!(t.total >= 200, "the case list shrank to {}", t.total);
    assert_eq!(t.identical, t.total, "{} case(s) differ", t.diffs.len());
}

#[test]
fn planted_mutants_break_equivalence() {
    let py = python();
    let src = std::fs::read_to_string(script()).expect("script");
    let mutants = [
        ("rule: options needs one option, not two", "if len(option_ids) < 2:", "if len(option_ids) < 1:"),
        ("output: violation lines lose one space of indent", "\"      [%s] %s\\n\"", "\"     [%s] %s\\n\""),
    ];
    for (name, old, new) in mutants {
        assert!(src.contains(old), "mutant site gone: {}", old);
        let tmp = Scratch::new("mutant");
        let m = tmp.0.join("seam-check.py");
        std::fs::write(&m, src.replacen(old, new, 1)).expect("mutant");
        let t = compare(&py, &m, &tmp.0);
        println!("negative control [{}]: {}/{} cases differ", name, t.diffs.len(), t.total);
        assert!(!t.diffs.is_empty(), "mutant '{}' was not caught: the harness compares nothing", name);
    }
}

/// What is NOT equivalent, by design: PyYAML reads YAML 1.1, rivet-yaml reads
/// the YAML 1.2 core schema. Each input below must still DIFFER, so this list
/// stays the exact, current boundary: if rivet-yaml (or the port) starts to
/// agree on one, it moves into the gate above.
#[test]
fn documented_yaml_divergences_still_differ() {
    let py = python();
    let tmp = Scratch::new("diverge");
    let world = tmp.0.join("w");
    std::fs::create_dir_all(&world).expect("dir");
    std::fs::write(world.join("world.json"), "{\"issues\": [], \"files\": {}}").expect("world");
    let bin = env!("CARGO_BIN_EXE_seam-check");
    let known = [
        ("YAML 1.1 boolean yes (PyYAML: bool, rivet-yaml: str)", "notes: yes"),
        ("YAML 1.1 boolean off", "notes: off"),
        ("YAML 1.1 octal 012 (PyYAML: int 10, rivet-yaml: str)", "notes: 012"),
        ("YAML 1.1 underscore int 1_000", "notes: 1_000"),
        ("YAML 1.1 sexagesimal 1:30", "notes: 1:30"),
        ("exponent without a dot 1e3 (PyYAML: str, rivet-yaml: float)", "notes: 1e3"),
        ("YAML 1.2 octal 0o17 (PyYAML: str, rivet-yaml: int)", "notes: 0o17"),
        ("the YAML 1.1 value key = (PyYAML: refused)", "notes: ="),
        ("a tag !!str (rivet-yaml: refused)", "notes: !!str x"),
        ("an int beyond 64 bits (rivet-yaml: refused)", "notes: 99999999999999999999"),
        ("a C0 control character (PyYAML: refused)", "notes: a\u{1}b"),
    ];
    let mut same = vec![];
    for (n, (name, line)) in known.iter().enumerate() {
        let f = tmp.0.join(format!("k{}.seam", n));
        std::fs::write(&f, format!("format: 1\nseam: a/b\nkind: wire\nstatus: proposed\n{}\n", line)).expect("block");
        let args = vec!["--fixtures".to_string(), s(&world), "--block".into(), s(&f), "--now".into(), "2026-11-19".into()];
        let (po, pc) = exec(&py, &[s(&script())], &args);
        let (ro, rc) = exec(bin, &[], &args);
        if pc == rc && normalize(&po) == normalize(&ro) {
            same.push(*name);
        }
    }
    println!("documented divergences: {} listed, {} still differ", known.len(), known.len() - same.len());
    assert!(same.is_empty(), "now equivalent, move them into the gate: {:?}", same);
}
