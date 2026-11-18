// rivet: verifies REQ-NORTH-STAR-COMPONENT
//! north-star-cases: run the North Star check's cases through every
//! implementation; all must agree.
//!
//! The implementations are scripts/check-north-star.py (the reference while
//! the component replaces it) and the north-star-check WebAssembly component
//! under one or more runtimes. Each case is a directory laid out like the
//! repository (data/north-star.toml, data/north-star/<id>.json) and every
//! runner checks the same directories, so the comparison is about the
//! checkers, not about how each one was fed.
//!
//! The cases:
//!   - "committed": the repository's own data, which must pass (exit 0);
//!   - the 15 planted violations of check-north-star.py --self-test, ported
//!     as a table; each must make EVERY implementation exit 1;
//!   - --fuzz N seeded random mutations (wrong types, odd strings, TOML
//!     datetimes, malformed or edge-case measurement JSON); for these only
//!     agreement is required: same stdout, same exit code.
//!
//! Agreement is on stdout and the exit code. stderr is only required to start
//! with "check-north-star:" when the exit code is 2: exception and parser
//! texts differ between Python and Rust.
//!
//!   north-star-cases --repo REPO --runner python \
//!       --runner 'wasmtime=wasmtime run --dir {dir}::/case {wasm} --root /case' \
//!       --wasm north-star-check.wasm [--fuzz 200] [--seed N] [--expect-cannot-run NAME]
//!
//! A runner is NAME=COMMAND, split on whitespace (no quoting); {dir} is the
//! case directory and {wasm} the --wasm path. "python" alone means
//! `python3 -I REPO/scripts/check-north-star.py --root {dir}`.
//! --expect-cannot-run NAME marks a runtime known not to run the component
//! yet (a recorded gap): its failure to start is reported and tolerated, but
//! if it starts running the component the harness fails, so the expectation
//! is removed and the runtime is compared like the others.
//!
//! Exit: 0 all agree · 1 a disagreement, or a planted case not caught ·
//! 2 could not run.

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use toml::Value;
use toml::value::{Date, Datetime, Offset, Table, Time};

// --- a TOML writer: inline values only, which keeps document order --------

fn tstr(s: &str) -> String {
    let mut out = String::from("\"");
    for ch in s.chars() {
        let o = ch as u32;
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            _ if o < 0x20 || o == 0x7f => out.push_str(&format!("\\u{:04X}", o)),
            _ => out.push(ch),
        }
    }
    out.push('"');
    out
}

fn tval(v: &Value) -> String {
    match v {
        Value::Boolean(b) => b.to_string(),
        Value::Integer(i) => i.to_string(),
        Value::Float(f) if f.is_nan() => "nan".into(),
        Value::Float(f) if f.is_infinite() => if *f > 0.0 { "inf".into() } else { "-inf".into() },
        // Debug keeps a ".0" or an exponent, both valid TOML floats.
        Value::Float(f) => format!("{:?}", f),
        Value::String(s) => tstr(s),
        Value::Datetime(d) => d.to_string(),
        Value::Array(a) => format!("[{}]", a.iter().map(tval).collect::<Vec<_>>().join(", ")),
        Value::Table(t) => format!(
            "{{{}}}",
            t.iter().map(|(k, x)| format!("{} = {}", tstr(k), tval(x))).collect::<Vec<_>>().join(", ")
        ),
    }
}

fn to_toml(doc: &Table) -> Result<String, String> {
    let text: String = doc.iter().map(|(k, v)| format!("{} = {}\n", tstr(k), tval(v))).collect();
    let back: Table = text.parse().map_err(|e| format!("written TOML does not parse: {e}\n{text}"))?;
    // Debug, because NaN != NaN.
    if format!("{:?}", back) != format!("{:?}", doc) {
        return Err(format!("TOML writer does not round-trip:\n{:?}\n{:?}", doc, back));
    }
    Ok(text)
}

// --- the cases ---------------------------------------------------------------

type Files = BTreeMap<String, Vec<u8>>;

struct Case {
    name: String,
    doc: Table,
    files: Files,
}

fn committed_measurements(repo: &Path) -> Result<Files, String> {
    let dir = repo.join("data").join("north-star");
    let mut out = Files::new();
    let rd = fs::read_dir(&dir).map_err(|e| format!("{}: {e}", dir.display()))?;
    for e in rd.flatten() {
        let name = e.file_name().to_string_lossy().into_owned();
        if name.ends_with(".json") {
            out.insert(name, fs::read(e.path()).map_err(|e| e.to_string())?);
        }
    }
    Ok(out)
}

fn obj(d: &mut Table, i: usize) -> &mut Table {
    d.get_mut("objectives").unwrap().as_array_mut().unwrap()[i].as_table_mut().unwrap()
}

fn commitment(d: &mut Table) -> &mut Table {
    d.get_mut("periods").unwrap().as_array_mut().unwrap()[0]
        .get_mut("commitments")
        .unwrap()
        .as_array_mut()
        .unwrap()[0]
        .as_table_mut()
        .unwrap()
}

fn s(x: &str) -> Value {
    Value::String(x.into())
}

/// check-north-star.py --self-test's planted violations, as data.
fn planted(base: &Table, meas: &Files) -> Vec<Case> {
    let m = |name: &str, f: &dyn Fn(&mut Table), files: Files| {
        let mut d = base.clone();
        f(&mut d);
        Case { name: name.into(), doc: d, files }
    };
    let first = base["objectives"][0]["id"].as_str().unwrap().to_string();
    let first_id = first.clone();
    let mut cases = vec![
        m("missing guard", &|d| {
            obj(d, 0).remove("guard");
        }, meas.clone()),
        m("bad id", &|d| {
            obj(d, 0).insert("id".into(), s("X1"));
        }, meas.clone()),
        m("duplicate id", &|d| {
            obj(d, 1).insert("id".into(), s(&first_id));
        }, meas.clone()),
        m("made-up zero", &|d| {
            obj(d, 0).insert("state".into(), s("0%"));
        }, meas.clone()),
        m("unknown commitment objective", &|d| {
            commitment(d).insert("objective".into(), s("O99"));
        }, meas.clone()),
        m("bad kind", &|d| {
            commitment(d).insert("kind".into(), s("maybe"));
        }, meas.clone()),
        m("bad layer", &|d| {
            d.get_mut("periods").unwrap().as_array_mut().unwrap()[0]
                .get_mut("layers").unwrap().as_array_mut().unwrap().push(s("2026-11"));
        }, meas.clone()),
        m("unknown pull", &|d| {
            d.get_mut("products").unwrap().as_array_mut().unwrap()[0]
                .get_mut("pulls").unwrap().as_array_mut().unwrap().push(s("O99"));
        }, meas.clone()),
        m("dated north star", &|d| {
            let star = format!("{} By 2027.", d["north_star"].as_str().unwrap());
            d.insert("north_star".into(), s(&star));
        }, meas.clone()),
        m("ipv4", &|d| {
            obj(d, 0).insert("summary".into(), s("runs on 10.0.0.5"));
        }, meas.clone()),
        m("local host", &|d| {
            obj(d, 0).insert("summary".into(), s("measured on box.lan"));
        }, meas.clone()),
    ];
    // Rule 7: the self-test's planted measurement directories. Every other
    // objective is unmeasured and the directory holds only the planted file.
    let r7 = |name: &str, state: &str, payload: Option<String>| {
        let mut files = Files::new();
        if let Some(p) = payload {
            files.insert(format!("{first}.json"), p.into_bytes());
        }
        m(name, &|d| {
            obj(d, 0).insert("state".into(), s(state));
            let n = d["objectives"].as_array().unwrap().len();
            for i in 1..n {
                obj(d, i).insert("state".into(), s("unmeasured"));
            }
        }, files)
    };
    let f = |oid: &str, v: i64| Some(format!("{{\"objective\": \"{oid}\", \"value\": {v}, \"of\": 2}}"));
    cases.push(r7("measured without a file", "measured", None));
    cases.push(r7("file without measured", "unmeasured", f(&first, 1)));
    cases.push(r7("value above denominator", "measured", f(&first, 3)));
    cases.push(r7("file for another objective", "measured", f("O99", 1)));
    cases
}

fn dt(date: Option<(u16, u8, u8)>, time: Option<(u8, u8, u8, u32)>, offset: Option<Offset>) -> Value {
    Value::Datetime(Datetime {
        date: date.map(|(year, month, day)| Date { year, month, day }),
        time: time.map(|(hour, minute, second, nanosecond)| Time { hour, minute, second, nanosecond }),
        offset,
    })
}

fn odd_values() -> Vec<Value> {
    let mut v: Vec<Value> = [
        "", " ", "\u{a0}", "\u{1c}", "O1", "O1\n", "O0", "O01", "o1", "X1", "measured", "unmeasured",
        "committed", "stretch", "2026.11", "2026.11\n", "2026.1", "2026-11", "Q3", "Q34", "by 2027",
        "x2027", "1.2.3.4", "1.2.3.4567", "999.1.1.1", "box.lan", "BOX.LOCAL", "a-b.internal",
        "x.lane", "\u{130}nternal.k", "x.\u{131}ntranet", "_a.home", "it's", "say \"hi\"", "tab\tnl\n",
        "\u{2028}", "\u{1f600}", "\u{e9}t\u{e9}", "\u{7f}", "line\r",
    ]
    .iter()
    .map(|x| s(x))
    .collect();
    v.extend([0i64, 1, -7, 1 << 40].map(Value::Integer));
    v.extend([0.0, -0.0, 1.0, 2026.11, 1e16, 1e-05, f64::INFINITY, f64::NAN].map(Value::Float));
    v.extend([Value::Boolean(true), Value::Boolean(false)]);
    v.push(Value::Array(vec![]));
    v.push(Value::Array(vec![s("O1")]));
    v.push(Value::Array(vec![s("O1"), Value::Integer(2)]));
    v.push(Value::Table(Table::new()));
    let mut t = Table::new();
    t.insert("a".into(), Value::Integer(1));
    v.push(Value::Table(t));
    let mut t = Table::new();
    t.insert("objective".into(), s("O1"));
    v.push(Value::Table(t));
    v.push(dt(Some((2026, 11, 17)), None, None));
    v.push(dt(None, Some((10, 0, 0, 0)), None));
    v.push(dt(None, Some((10, 0, 5, 123_000_000)), None));
    v.push(dt(Some((2026, 11, 17)), Some((10, 0, 0, 0)), None));
    v.push(dt(Some((2026, 11, 17)), Some((10, 0, 7, 0)), Some(Offset::Z)));
    v.push(dt(Some((2026, 11, 17)), Some((10, 0, 0, 0)), Some(Offset::Custom { minutes: -330 })));
    v
}

/// Measurement file bodies; "%s" is replaced with the objective id. `None`
/// writes no file.
fn odd_json() -> Vec<Option<Vec<u8>>> {
    let mut v: Vec<Option<Vec<u8>>> = vec![None];
    for t in [
        r#"{"objective": "%s", "value": 1, "of": 2}"#,
        r#"{"objective": "%s", "value": 0, "of": 1}"#,
        r#"{"objective": "%s", "value": true, "of": 2}"#,
        r#"{"objective": "%s", "value": 1.0, "of": 2}"#,
        r#"{"objective": "%s", "value": 1, "of": 0}"#,
        r#"{"objective": "%s", "value": -1, "of": 2}"#,
        r#"{"objective": "%s", "value": 1, "of": 99999999999999999999999}"#,
        r#"{"objective": "%s", "value": 1, "of": 2, "x": NaN}"#,
        r#"{"objective": "%s", "value": 1, "value": 9, "of": 2}"#,
        r#"{"objective": "%s\ud800", "value": 1, "of": 2}"#,
        r#"{"objective": "%s", "value": 1, "of": 2} x"#,
        "null",
        "[]",
        "[1]",
        r#""O1""#,
        "3",
        "",
        "{",
        "\u{feff}{}",
        r#"{"objective": "%s", "value": 1e0, "of": 2}"#,
        r#"{"objective": "%s", "value": -0, "of": 2}"#,
    ] {
        v.push(Some(t.as_bytes().to_vec()));
    }
    v.push(Some(vec![0xff, 0xfe]));
    v
}

#[derive(Clone, Copy)]
enum K {
    S(&'static str),
    I(usize),
}

fn paths() -> Vec<Vec<K>> {
    use K::*;
    vec![
        vec![S("north_star")], vec![S("updated")], vec![S("objectives")], vec![S("periods")], vec![S("products")],
        vec![S("objectives"), I(0), S("id")], vec![S("objectives"), I(1), S("id")],
        vec![S("objectives"), I(0), S("state")], vec![S("objectives"), I(1), S("state")],
        vec![S("objectives"), I(2), S("title")], vec![S("objectives"), I(0), S("summary")],
        vec![S("objectives"), I(3), S("guard")], vec![S("objectives"), I(0)],
        vec![S("periods"), I(0), S("layers")], vec![S("periods"), I(1), S("layers"), I(0)],
        vec![S("periods"), I(0), S("commitments")], vec![S("periods"), I(0), S("commitments"), I(0), S("objective")],
        vec![S("periods"), I(1), S("commitments"), I(0), S("kind")],
        vec![S("periods"), I(0), S("commitments"), I(0), S("target")], vec![S("periods"), I(1)],
        vec![S("products"), I(0), S("pulls")], vec![S("products"), I(1), S("pulls"), I(0)],
        vec![S("products"), I(2), S("name")], vec![S("products"), I(0)],
    ]
}

/// Set or delete at `path`; does nothing when an earlier mutation changed a
/// parent's type or removed it.
fn set(doc: &mut Table, path: &[K], value: Value, delete: bool) {
    let mut root = Value::Table(std::mem::take(doc));
    set_in(&mut root, path, value, delete);
    if let Value::Table(t) = root {
        *doc = t;
    }
}

fn set_in(node: &mut Value, path: &[K], value: Value, delete: bool) {
    if path.len() > 1 {
        let next = match (path[0], node) {
            (K::S(key), Value::Table(t)) => t.get_mut(key),
            (K::I(i), Value::Array(a)) => a.get_mut(i),
            _ => None,
        };
        if let Some(n) = next {
            set_in(n, &path[1..], value, delete);
        }
        return;
    }
    match (path[0], node) {
        (K::S(key), Value::Table(t)) => {
            if delete {
                t.remove(key);
            } else {
                t.insert(key.into(), value);
            }
        }
        (K::I(i), Value::Array(a)) if i < a.len() => {
            if delete {
                a.remove(i);
            } else {
                a[i] = value;
            }
        }
        _ => {}
    }
}

/// splitmix64: seeded and dependency-free.
struct Rng(u64);

impl Rng {
    fn next(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9e37_79b9_7f4a_7c15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
        z ^ (z >> 31)
    }
    fn below(&mut self, n: usize) -> usize {
        (self.next() % n as u64) as usize
    }
    fn chance(&mut self, pct: u64) -> bool {
        self.next() % 100 < pct
    }
}

fn fuzz(base: &Table, n: usize, seed: u64) -> Vec<Case> {
    let mut rng = Rng(seed);
    let values = odd_values();
    let jsons = odd_json();
    let paths = paths();
    let mut ids: Vec<String> = base["objectives"]
        .as_array()
        .unwrap()
        .iter()
        .map(|o| o["id"].as_str().unwrap().to_string())
        .collect();
    ids.extend(["X1".to_string(), "O01".to_string()]);
    (0..n)
        .map(|k| {
            let mut d = base.clone();
            for _ in 0..1 + rng.below(3) {
                let p = &paths[rng.below(paths.len())];
                let v = values[rng.below(values.len())].clone();
                let del = rng.chance(15);
                set(&mut d, p, v, del);
            }
            let mut files = Files::new();
            let mut pool = ids.clone();
            for _ in 0..rng.below(3) {
                let oid = pool.remove(rng.below(pool.len()));
                if let Some(body) = &jsons[rng.below(jsons.len())] {
                    let body = match std::str::from_utf8(body) {
                        Ok(t) => t.replace("%s", &oid).into_bytes(),
                        Err(_) => body.clone(),
                    };
                    files.insert(format!("{oid}.json"), body);
                }
            }
            Case { name: format!("fuzz {k:03}"), doc: d, files }
        })
        .collect()
}

fn write_case(base_dir: &Path, c: &Case) -> Result<PathBuf, String> {
    let d = base_dir.join(c.name.replace(' ', "-"));
    let md = d.join("data").join("north-star");
    fs::create_dir_all(&md).map_err(|e| e.to_string())?;
    fs::write(d.join("data").join("north-star.toml"), to_toml(&c.doc)?).map_err(|e| e.to_string())?;
    for (name, body) in &c.files {
        fs::write(md.join(name), body).map_err(|e| e.to_string())?;
    }
    Ok(d)
}

// --- running -----------------------------------------------------------------

struct Run {
    code: Option<i32>,
    out: String,
    err: String,
}

fn run(argv: &[String]) -> Run {
    match Command::new(&argv[0]).args(&argv[1..]).output() {
        Ok(o) => Run {
            code: o.status.code(),
            out: String::from_utf8_lossy(&o.stdout).into_owned(),
            err: String::from_utf8_lossy(&o.stderr).into_owned(),
        },
        Err(e) => Run { code: None, out: String::new(), err: format!("{}: {e}", argv[0]) },
    }
}

fn runner_argv(spec: &str, repo: &Path, wasm: &str, dir: &Path) -> Vec<String> {
    if spec == "python" {
        let script = repo.join("scripts").join("check-north-star.py");
        return vec![
            "python3".into(),
            "-I".into(),
            script.display().to_string(),
            "--root".into(),
            dir.display().to_string(),
        ];
    }
    let d = dir.display().to_string();
    spec.split_whitespace().map(|a| a.replace("{dir}", &d).replace("{wasm}", wasm)).collect()
}

fn code_str(c: Option<i32>) -> String {
    c.map_or("none (signal or not started)".into(), |c| c.to_string())
}

fn last_lines(s: &str, n: usize) -> String {
    let l: Vec<&str> = s.trim().lines().collect();
    l[l.len().saturating_sub(n)..].join(" | ")
}

struct Args {
    repo: PathBuf,
    runners: Vec<(String, String)>,
    wasm: String,
    fuzz: usize,
    seed: u64,
    expect_gap: Vec<String>,
}

fn parse_args() -> Result<Args, String> {
    let mut a = Args { repo: PathBuf::from("."), runners: vec![], wasm: String::new(), fuzz: 0, seed: 20261118, expect_gap: vec![] };
    let mut it = std::env::args().skip(1);
    while let Some(k) = it.next() {
        let mut val = || it.next().ok_or_else(|| format!("{k} needs a value"));
        match k.as_str() {
            "--repo" => a.repo = PathBuf::from(val()?),
            "--runner" => {
                let r = val()?;
                let (name, cmd) = r.split_once('=').unwrap_or((r.as_str(), r.as_str()));
                a.runners.push((name.to_string(), cmd.to_string()));
            }
            "--wasm" => a.wasm = val()?,
            "--fuzz" => a.fuzz = val()?.parse().map_err(|e| format!("--fuzz: {e}"))?,
            "--seed" => a.seed = val()?.parse().map_err(|e| format!("--seed: {e}"))?,
            "--expect-cannot-run" => a.expect_gap.push(val()?),
            other => return Err(format!("unknown argument {other}")),
        }
    }
    if a.runners.len() < 2 {
        return Err("give at least two runners to compare".into());
    }
    Ok(a)
}

fn real_main() -> Result<bool, String> {
    let a = parse_args()?;
    let toml_path = a.repo.join("data").join("north-star.toml");
    let text = fs::read_to_string(&toml_path).map_err(|e| format!("{}: {e}", toml_path.display()))?;
    let base: Table = text.parse().map_err(|e| format!("{}: {e}", toml_path.display()))?;
    let meas = committed_measurements(&a.repo)?;

    let mut cases = vec![Case { name: "committed".into(), doc: base.clone(), files: meas.clone() }];
    cases.extend(planted(&base, &meas));
    let n_planted = cases.len() - 1;
    cases.extend(fuzz(&base, a.fuzz, a.seed));

    let tmp = std::env::temp_dir().join(format!("north-star-cases-{}", std::process::id()));
    let _ = fs::remove_dir_all(&tmp);
    fs::create_dir_all(&tmp).map_err(|e| e.to_string())?;

    let mut failures = 0usize;
    let mut exits: BTreeMap<String, usize> = BTreeMap::new();
    let mut gap_seen: BTreeMap<String, Option<String>> = a.expect_gap.iter().map(|n| (n.clone(), None)).collect();
    let mut fail = |msg: String| {
        println!("{msg}");
        failures += 1;
    };
    for (idx, c) in cases.iter().enumerate() {
        let dir = write_case(&tmp, c)?;
        let mut results: Vec<(&str, Run)> = Vec::new();
        for (rname, spec) in &a.runners {
            let r = run(&runner_argv(spec, &a.repo, &a.wasm, &dir));
            if let Some(seen) = gap_seen.get_mut(rname) {
                // A known gap: tolerated only while the runtime cannot run it.
                if !matches!(r.code, Some(0 | 1)) || !r.out.starts_with("north-star:") {
                    if seen.is_none() {
                        let tail = if r.err.trim().is_empty() { &r.out } else { &r.err };
                        *seen = Some(format!("exit {}: {}", code_str(r.code), last_lines(tail, 3)));
                    }
                } else {
                    fail(format!(
                        "FAIL {}: {rname} now runs the component (exit {}); remove --expect-cannot-run {rname}",
                        c.name,
                        code_str(r.code)
                    ));
                }
                continue;
            }
            results.push((rname, r));
        }
        let Some((ref_name, reference)) = results.first() else { continue };
        *exits.entry(code_str(reference.code)).or_default() += 1;
        for (rname, r) in &results {
            if (r.code, &r.out) != (reference.code, &reference.out) {
                let mut m = format!("FAIL {}: {ref_name} and {rname} disagree", c.name);
                for (nm, x) in [(ref_name, reference), (rname, r)] {
                    let out = if x.out.trim().is_empty() { "(no stdout)".to_string() } else { x.out.trim_end().replace('\n', "\n    ") };
                    m.push_str(&format!("\n  {nm} exit {}\n    {out}", code_str(x.code)));
                    if !x.err.trim().is_empty() {
                        m.push_str(&format!("\n    stderr: {}", last_lines(&x.err, 1)));
                    }
                }
                fail(m);
            }
            if r.code == Some(2) && !r.err.starts_with("check-north-star:") {
                fail(format!("FAIL {}: {rname} exit 2 without a check-north-star message: {}", c.name, last_lines(&r.err, 2)));
            }
            if !matches!(r.code, Some(0..=2)) {
                fail(format!("FAIL {}: {rname} exit {} (crash?)", c.name, code_str(r.code)));
            }
        }
        if c.name == "committed" && reference.code != Some(0) {
            fail(format!("FAIL committed: the repository's own data must pass, got exit {}", code_str(reference.code)));
        }
        if (1..=n_planted).contains(&idx) {
            for (rname, r) in &results {
                if r.code != Some(1) {
                    fail(format!("FAIL planted '{}': {rname} exit {}, expected 1", c.name, code_str(r.code)));
                }
            }
        }
    }
    let _ = fs::remove_dir_all(&tmp);

    for (rname, seen) in &gap_seen {
        if let Some(why) = seen {
            println!("KNOWN GAP {rname}: cannot run the component ({why})");
        }
    }
    // A comparison where every case exits 2 compares nothing about the rules.
    let mix: Vec<String> = exits.iter().map(|(c, n)| format!("{n} x {c}")).collect();
    println!("exit codes of {}: {}", a.runners[0].0, mix.join(", "));
    let names: Vec<&str> = a.runners.iter().map(|(n, _)| n.as_str()).filter(|n| !gap_seen.contains_key(*n)).collect();
    println!(
        "cases: {} (1 committed, {n_planted} planted, {} fuzz); compared: {}; {}",
        cases.len(),
        a.fuzz,
        names.join(", "),
        if failures == 0 { "all agree".to_string() } else { format!("{failures} failure(s)") }
    );
    Ok(failures == 0)
}

fn main() {
    let code = match real_main() {
        Ok(true) => 0,
        Ok(false) => 1,
        Err(e) => {
            eprintln!("north-star-cases: {e}");
            2
        }
    };
    std::process::exit(code)
}
