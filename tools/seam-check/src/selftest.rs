//! `--self-test`: the same fixtures, negative controls and loopback-stub HTTP
//! cases as seam-check.py's self_test(), printing the same lines.

use crate::cli;
use crate::pyval::{json_dumps, V};
use std::io::{Read, Write};
use std::net::TcpListener;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

pub const GOOD: &str = "format: 1
seam: provider-consumer/example
kind: consumption
status: decided
provider:
  repo: acme/provider
  promise: \"the WIT package and not changing it without telling the consumer\"
  guard: scripts/one-exporter.sh
consumers:
  - repo: acme/consumer
    binding: \"the host that calls it\"
    guard: tools/check-pin.sh
interface:
  - kind: wit
    path: wit/api.wit
    package: \"acme:api\"
    version: \"0.2.0\"
    interfaces: [controller]
  - kind: file
    path: src/wire.rs
    symbols: [\"pub const VERSION: u8 = 2;\"]
options:
  - id: step
    summary: \"synchronous step per tick\"
  - id: stream
    summary: \"a stream of samples\"
recommendation: step
decisions:
  - summary: \"step at the core boundary\"
    option: step
    decided_by: \"acme/consumer maintainer\"
    date: \"2026-10-20\"
open_questions:
  - q: \"where does battery-v live?\"
    owner: acme/consumer
";

pub const WIT: &str = "/// api\npackage acme:api@0.2.0;\n\ninterface controller {\n  step: func();\n}\n";
pub const WIRE: &str = "pub const VERSION: u8 = 2;\npub const LEN: usize = 81;\n";

/// `_sub`: replace the first occurrence; the old text must be present.
pub fn sub(old: &str, new: &str, text: &str) -> String {
    assert!(text.contains(old), "{}", old);
    text.replacen(old, new, 1)
}

fn g(old: &str, new: &str) -> String {
    sub(old, new, GOOD)
}

pub fn block(text: &str) -> String {
    format!("Contract below.\n\n```seam\n{}```\n", text)
}

fn s(x: &str) -> V {
    V::s(x)
}

fn d(items: Vec<(&str, V)>) -> V {
    V::Dict(items.into_iter().map(|(k, v)| (V::s(k), v)).collect())
}

/// The keyword arguments of `_world`.
#[derive(Clone, Default)]
pub struct World {
    pub body: String,
    pub comments: Vec<V>,
    pub labels: Option<Vec<String>>,
    pub files: Option<V>,
    pub fail: Vec<String>,
    pub extra_issues: Vec<V>,
}

/// `_world`: write api.wit, wire.rs and world.json into `dir`.
pub fn write_world(dir: &Path, w: &World) -> std::io::Result<PathBuf> {
    std::fs::create_dir_all(dir)?;
    std::fs::write(dir.join("api.wit"), WIT)?;
    std::fs::write(dir.join("wire.rs"), WIRE)?;
    let labels = w.labels.clone().unwrap_or_else(|| vec!["seam".into()]);
    let mut issues = vec![d(vec![
        ("repo", s("acme/consumer")),
        ("number", V::Int(1)),
        ("labels", V::List(labels.iter().map(|l| s(l)).collect())),
        ("body", s(&w.body)),
        ("comments", V::List(w.comments.clone())),
    ])];
    issues.extend(w.extra_issues.iter().cloned());
    let files = w.files.clone().unwrap_or_else(|| {
        d(vec![
            (
                "acme/provider",
                d(vec![
                    ("wit/api.wit", s("api.wit")),
                    ("src/wire.rs", s("wire.rs")),
                    ("scripts/one-exporter.sh", V::None),
                ]),
            ),
            ("acme/consumer", d(vec![("tools/check-pin.sh", V::None)])),
        ])
    });
    let world = d(vec![
        ("issues", V::List(issues)),
        ("files", files),
        ("fail", V::List(w.fail.iter().map(|f| s(f)).collect())),
    ]);
    std::fs::write(dir.join("world.json"), json_dumps(&world))?;
    Ok(dir.to_path_buf())
}

fn comment(at: &str, body: String) -> V {
    d(vec![("created_at", s(at)), ("body", V::Str(body))])
}

/// Every fixture case: (name, world, extra argv, expected exit).
pub fn cases() -> Vec<(String, World, Vec<String>, i32)> {
    let now: Vec<String> = ["--now", "2026-10-29", "--org", "acme"].iter().map(|x| x.to_string()).collect();
    let later = |strict: bool| -> Vec<String> {
        let mut v: Vec<String> = ["--now", "2027-03-01", "--org", "acme"].iter().map(|x| x.to_string()).collect();
        if strict {
            v.push("--strict".into());
        }
        v
    };
    let options = g("status: decided", "status: options");
    let mut_ = vec![
        ("parse: not YAML", g("kind: consumption", "kind: [consumption")),
        ("parse: not a mapping", "- just\n- a list\n".to_string()),
        ("parse: duplicate key", g("kind: consumption", "kind: consumption\nkind: wire")),
        ("required: unquoted float version", g("version: \"0.2.0\"", "version: 0.2")),
        ("required: missing interface", g("interface:\n  - kind: wit", "interfacex:\n  - kind: wit")),
        ("enum: bad kind", g("kind: consumption", "kind: api")),
        ("enum: bad status", g("status: decided", "status: agreed")),
        ("unknown-key", g("kind: consumption", "kind: consumption\nowner: someone")),
        ("owner: consumer without repo", g("  - repo: acme/consumer\n    binding", "  - binding")),
        ("owner: provider repo not OWNER/REPO", g("repo: acme/provider", "repo: provider")),
        ("owner: consumer is the provider", g("  - repo: acme/consumer\n", "  - repo: acme/provider\n")),
        (
            "owner: no consumers",
            g(
                "consumers:\n  - repo: acme/consumer\n    binding: \"the host that calls it\"\n    guard: tools/check-pin.sh\n",
                "consumers: []\n",
            ),
        ),
        ("question-owner: missing", g("    owner: acme/consumer\n", "")),
        ("question-owner: not a party", g("    owner: acme/consumer\n", "    owner: acme/elsewhere\n")),
        ("decision: decided without decisions", g("decisions:", "decisionz:")),
        ("decision: no date", g("    date: \"2026-10-20\"\n", "")),
        ("decision: date not ISO", g("date: \"2026-10-20\"", "date: \"20 Oct 2026\"")),
        ("decision: date in the future", g("date: \"2026-10-20\"", "date: \"2027-01-01\"")),
        ("decision: option not offered", g("    option: step", "    option: batch")),
        ("decision: no decided_by", g("    decided_by: \"acme/consumer maintainer\"\n", "")),
        ("options: one option only", options.replace("  - id: stream\n    summary: \"a stream of samples\"\n", "")),
        ("options: no recommendation", options.replace("recommendation: step\n", "")),
        ("options: recommendation not an option", options.replace("recommendation: step", "recommendation: batch")),
        ("implemented: no implemented_by", g("status: decided", "status: implemented")),
        ("broken", g("status: decided", "status: broken")),
        ("interface-missing", g("path: wit/api.wit", "path: wit/gone.wit")),
        ("interface-version: version drift", g("version: \"0.2.0\"", "version: \"0.1.0\"")),
        ("interface-version: package drift", g("package: \"acme:api\"", "package: \"acme:other\"")),
        ("interface-symbol: WIT interface gone", g("interfaces: [controller]", "interfaces: [pilot]")),
        ("interface-symbol: file symbol gone", g("VERSION: u8 = 2;", "VERSION: u8 = 3;")),
        ("required: wit without version", g("    version: \"0.2.0\"\n", "")),
        ("required: file without symbols", g("    symbols: [\"pub const VERSION: u8 = 2;\"]\n", "")),
        ("guard-missing", g("guard: tools/check-pin.sh", "guard: tools/gone.sh")),
        ("guard-missing: provider guard gone", g("guard: scripts/one-exporter.sh", "guard: scripts/gone.sh")),
        (
            "guard-missing: second guard in a list",
            g("guard: tools/check-pin.sh", "guard: [tools/check-pin.sh, tools/gone.sh]"),
        ),
        ("required: guard list with a non-string", g("guard: tools/check-pin.sh", "guard: [tools/check-pin.sh, 3]")),
    ];
    let w = |body: String| World { body, ..Default::default() };
    let mut out: Vec<(String, World, Vec<String>, i32)> =
        mut_.into_iter().map(|(n, t)| (n.to_string(), w(block(&t)), now.clone(), 1)).collect();
    let with = |extra: &[&str]| -> Vec<String> {
        let mut v = now.clone();
        v.extend(extra.iter().map(|x| x.to_string()));
        v
    };
    out.push(("positive: good block".into(), w(block(GOOD)), now.clone(), 0));
    out.push((
        "positive: a guard list".into(),
        w(block(&g("guard: tools/check-pin.sh", "guard: [tools/check-pin.sh]"))),
        now.clone(),
        0,
    ));
    out.push(("positive: --party keeps it".into(), w(block(GOOD)), with(&["--party", "acme/provider"]), 0));
    out.push(("no-seams: --party filters everything out".into(), w(block(GOOD)), with(&["--party", "acme/x"]), 1));
    out.push(("no-block: labelled, no block".into(), w("prose only".into()), now.clone(), 1));
    out.push((
        "no-seams: nothing labelled".into(),
        World { body: block(GOOD), labels: Some(vec![]), ..Default::default() },
        now.clone(),
        1,
    ));
    out.push((
        "duplicate-id: across issues".into(),
        World {
            body: block(GOOD),
            extra_issues: vec![d(vec![
                ("repo", s("acme/provider")),
                ("number", V::Int(7)),
                ("labels", V::List(vec![s("seam")])),
                ("body", V::Str(block(GOOD))),
            ])],
            ..Default::default()
        },
        now.clone(),
        1,
    ));
    out.push((
        "positive: body is canonical over a later broken comment".into(),
        World {
            body: block(GOOD),
            comments: vec![comment("2026-10-28T00:00:00Z", block(&g("kind: consumption", "kind: api")))],
            ..Default::default()
        },
        now.clone(),
        0,
    ));
    out.push((
        "positive: no body block, the latest comment counts".into(),
        World {
            body: "prose".into(),
            comments: vec![
                comment("2026-10-01T00:00:00Z", block(&g("kind: consumption", "kind: api"))),
                comment("2026-10-28T00:00:00Z", block(GOOD)),
            ],
            ..Default::default()
        },
        now.clone(),
        0,
    ));
    out.push((
        "enum: no body block, the latest comment is broken".into(),
        World {
            body: "prose".into(),
            comments: vec![
                comment("2026-10-01T00:00:00Z", block(GOOD)),
                comment("2026-10-28T00:00:00Z", block(&g("kind: consumption", "kind: api"))),
            ],
            ..Default::default()
        },
        now.clone(),
        1,
    ));
    out.push(("positive: stale is a warning only".into(), w(block(GOOD)), later(false), 0));
    out.push(("stale: --strict makes it fail".into(), w(block(GOOD)), later(true), 1));
    out.push((
        "positive: implemented is never stale".into(),
        w(block(&(g("status: decided", "status: implemented") + "implemented_by: \"acme/provider#9\"\n"))),
        later(true),
        0,
    ));
    out.push((
        "infra: search fails".into(),
        World { body: block(GOOD), fail: vec!["search".into()], ..Default::default() },
        now.clone(),
        2,
    ));
    out.push((
        "infra: provider repo unreadable".into(),
        World {
            body: block(GOOD),
            files: Some(d(vec![("acme/consumer", d(vec![("tools/check-pin.sh", V::None)]))])),
            ..Default::default()
        },
        now.clone(),
        2,
    ));
    out
}

/// A scratch directory, removed on drop.
pub struct Scratch(pub PathBuf);

impl Scratch {
    pub fn new(tag: &str) -> Scratch {
        let nanos = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0);
        let p = std::env::temp_dir().join(format!("seam-check-{}-{}-{}", tag, std::process::id(), nanos));
        let _ = std::fs::create_dir_all(&p);
        Scratch(p)
    }
}

impl Drop for Scratch {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

fn argv(v: &[&str]) -> Vec<String> {
    v.iter().map(|x| x.to_string()).collect()
}

fn run_quiet(args: Vec<String>, out: &mut String) -> i32 {
    cli::run(&args, out).unwrap_or(1)
}

fn fired(report_json: &str) -> Vec<String> {
    let mut rules: Vec<String> = vec![];
    if let Ok(r) = crate::json::loads(report_json) {
        if let Some(V::List(seams)) = r.get("seams") {
            for s in seams {
                for key in ["violations", "warnings"] {
                    if let Some(V::List(l)) = s.get(key) {
                        for f in l {
                            if let Some(V::Str(rule)) = f.get("rule") {
                                if !rules.contains(rule) {
                                    rules.push(rule.clone());
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    rules.sort();
    rules
}

fn line(out: &mut String, ok: bool, name: &str, rest: &str) {
    out.push_str(&format!("{}  {:<62} {}\n", if ok { "ok  " } else { "FAIL" }, name, rest));
}

// ── loopback GitHub stand-in ────────────────────────────────────────────────

/// A route body or header value; `{port}` is replaced by the stub's port.
pub type Route = (String, (u16, Vec<(String, String)>, String));

pub struct Stub {
    pub port: u16,
    stop: Arc<AtomicBool>,
    handle: Option<std::thread::JoinHandle<()>>,
}

impl Stub {
    pub fn start(routes: Vec<Route>) -> Stub {
        let listener = TcpListener::bind("127.0.0.1:0").expect("bind loopback");
        let port = listener.local_addr().map(|a| a.port()).unwrap_or(0);
        let stop = Arc::new(AtomicBool::new(false));
        let stop2 = stop.clone();
        let handle = std::thread::spawn(move || {
            for conn in listener.incoming() {
                if stop2.load(Ordering::SeqCst) {
                    break;
                }
                let Ok(mut c) = conn else { continue };
                let routes = routes.clone();
                std::thread::spawn(move || {
                    let mut buf = vec![];
                    let mut tmp = [0u8; 4096];
                    while !buf.windows(4).any(|w| w == b"\r\n\r\n") {
                        match c.read(&mut tmp) {
                            Ok(0) | Err(_) => break,
                            Ok(n) => buf.extend_from_slice(&tmp[..n]),
                        }
                    }
                    let head = String::from_utf8_lossy(&buf).to_string();
                    let path = head.split_whitespace().nth(1).unwrap_or("/").to_string();
                    let (code, headers, body) = routes
                        .iter()
                        .find(|(prefix, _)| path.starts_with(prefix.as_str()))
                        .map(|(_, r)| r.clone())
                        .unwrap_or((404, vec![], "{\"message\":\"Not Found\"}".into()));
                    let fill = |t: &str| t.replace("{port}", &port.to_string());
                    let body = fill(&body);
                    let mut resp = format!("HTTP/1.0 {} X\r\n", code);
                    for (k, v) in headers {
                        resp.push_str(&format!("{}: {}\r\n", k, fill(&v)));
                    }
                    resp.push_str(&format!("Content-Length: {}\r\n\r\n", body.len()));
                    let _ = c.write_all(resp.as_bytes());
                    let _ = c.write_all(body.as_bytes());
                });
            }
        });
        Stub { port, stop, handle: Some(handle) }
    }
}

impl Drop for Stub {
    fn drop(&mut self) {
        self.stop.store(true, Ordering::SeqCst);
        let _ = std::net::TcpStream::connect(("127.0.0.1", self.port));
        if let Some(h) = self.handle.take() {
            let _ = h.join();
        }
    }
}

fn r(prefix: &str, code: u16, headers: &[(&str, &str)], body: &str) -> Route {
    (
        prefix.to_string(),
        (code, headers.iter().map(|(k, v)| (k.to_string(), v.to_string())).collect(), body.to_string()),
    )
}

pub fn search_body(incomplete: bool) -> String {
    format!(
        "{{\"incomplete_results\": {}, \"items\": [{{\"number\": 1, \"title\": \"t\", \"html_url\": \"x\", \"labels\": [{{\"name\": \"seam\"}}], \"body\": \"prose\", \"repository_url\": \"http://127.0.0.1:{{port}}/repos/acme/consumer\"}}]}}",
        if incomplete { "true" } else { "false" }
    )
}

pub fn ok_routes() -> Vec<Route> {
    let page1 = "[{\"id\": 1, \"created_at\": \"2026-10-01T00:00:00Z\", \"body\": \"no block here\"}]";
    let page2 = json_dumps(&V::List(vec![d(vec![
        ("id", V::Int(2)),
        ("created_at", s("2026-10-28T00:00:00Z")),
        ("body", V::Str(block(GOOD))),
    ])]));
    vec![
        r("/search/issues", 200, &[], &search_body(false)),
        r("/repos/acme/consumer/issues/1/comments?per_page=100&page=2", 200, &[], &page2),
        r(
            "/repos/acme/consumer/issues/1/comments",
            200,
            &[("Link", "<http://127.0.0.1:{port}/repos/acme/consumer/issues/1/comments?per_page=100&page=2>; rel=\"next\"")],
            page1,
        ),
        r("/repos/acme/provider/contents/wit/api.wit", 200, &[], WIT),
        r("/repos/acme/provider/contents/src/wire.rs", 200, &[], WIRE),
        r("/repos/acme/consumer/contents/tools/check-pin.sh", 200, &[], "#!/bin/sh\n"),
        r("/repos/acme/provider/contents/scripts/one-exporter.sh", 200, &[], "#!/bin/sh\n"),
        r("/repos/acme/provider", 200, &[], "{\"default_branch\": \"main\"}"),
        r("/repos/acme/consumer", 200, &[], "{\"default_branch\": \"main\"}"),
    ]
}

/// `dict(ok_routes, **{prefix: route})`: replace in place, keeping the position.
fn replace(routes: &[Route], new: Route) -> Vec<Route> {
    routes.iter().map(|x| if x.0 == new.0 { new.clone() } else { x.clone() }).collect()
}

fn without(routes: &[Route], prefix: &str) -> Vec<Route> {
    routes.iter().filter(|x| x.0 != prefix).cloned().collect()
}

pub fn http_cases() -> Vec<(String, Vec<Route>, i32)> {
    let ok = ok_routes();
    vec![
        ("http: block on comment page 2 (pagination)".into(), ok.clone(), 0),
        ("http: search 500".into(), replace(&ok, r("/search/issues", 500, &[], "{}")), 2),
        (
            "http: rate limited".into(),
            replace(&ok, r("/search/issues", 403, &[("X-RateLimit-Remaining", "0"), ("X-RateLimit-Reset", "1")], "{}")),
            2,
        ),
        ("http: incomplete search results".into(), replace(&ok, r("/search/issues", 200, &[], &search_body(true))), 2),
        ("http: provider repo 404".into(), without(&ok, "/repos/acme/provider"), 2),
        ("http: interface file 404".into(), without(&ok, "/repos/acme/provider/contents/wit/api.wit"), 1),
        (
            "http: interface file 500".into(),
            replace(&ok, r("/repos/acme/provider/contents/wit/api.wit", 500, &[], "{}")),
            2,
        ),
    ]
}

pub fn self_test(stdout: &mut String) -> i32 {
    let mut out = String::new();
    let now = argv(&["--now", "2026-10-29", "--org", "acme"]);
    let mut failures = 0;
    let tmp = Scratch::new("selftest");
    for (n, (name, w, extra, want)) in cases().into_iter().enumerate() {
        let dir = match write_world(&tmp.0.join(format!("w{}", n)), &w) {
            Ok(d) => d,
            Err(_) => return 1,
        };
        let mut buf = String::new();
        let mut args = argv(&["--fixtures", &dir.to_string_lossy(), "--format", "json"]);
        args.extend(extra);
        let got = run_quiet(args, &mut buf);
        let mut ok = got == want;
        let rules = fired(&buf);
        let rule = name.split(':').next().unwrap_or("");
        if want == 1 && !name.starts_with("no-seams") {
            ok = ok && rules.iter().any(|x| x == rule);
        }
        if name.starts_with("no-seams") {
            ok = ok && buf.contains("no seam blocks found");
        }
        failures += !ok as i32;
        line(&mut out, ok, &name, &format!("exit {} (want {}) {}", got, want, rules.join(",")));
        if !ok {
            out.push_str(&buf);
            out.push('\n');
        }
    }

    // --block mode, offline: the drafted-block path.
    let dir = write_world(
        &tmp.0.join("blk"),
        &World { body: "prose".into(), labels: Some(vec![]), ..Default::default() },
    )
    .unwrap_or_default();
    let bf = tmp.0.join("draft.seam");
    for (name, text, want) in [
        ("positive: --block draft", GOOD.to_string(), 0),
        ("--block draft with version drift", g("\"0.2.0\"", "\"0.3.0\""), 1),
    ] {
        let _ = std::fs::write(&bf, text);
        let mut args = argv(&["--fixtures", &dir.to_string_lossy(), "--block", &bf.to_string_lossy()]);
        args.extend(now.clone());
        let got = run_quiet(args, &mut String::new());
        failures += (got != want) as i32;
        line(&mut out, got == want, name, &format!("exit {} (want {})", got, want));
    }

    // JSON output carries the schema and the exit code (warte reads it).
    let mut buf = String::new();
    let js = write_world(&tmp.0.join("js"), &World { body: block(GOOD), ..Default::default() }).unwrap_or_default();
    let mut args = argv(&["--fixtures", &js.to_string_lossy(), "--format", "json"]);
    args.extend(now.clone());
    run_quiet(args, &mut buf);
    let j = crate::json::loads(&buf).unwrap_or(V::None);
    let first_id = match j.get("seams") {
        Some(V::List(l)) => l.first().and_then(|x| x.get("id")).cloned(),
        _ => None,
    };
    let ok = j.get("schema").and_then(|x| x.as_str()) == Some(crate::check::SCHEMA)
        && j.get("exit") == Some(&V::Int(0))
        && first_id.as_ref().and_then(|x| x.as_str()) == Some("provider-consumer/example");
    failures += !ok as i32;
    out.push_str(&format!("{}  {:<62}\n", if ok { "ok  " } else { "FAIL" }, "json: schema, exit and id present"));
    drop(tmp);

    // The real HTTP path against a loopback stub: pagination, raw files, errors.
    let mut modes = vec!["urllib"];
    if crate::transport::which("curl").is_some() {
        modes.push("curl");
    }
    for mode in modes {
        for (name, routes, want) in http_cases() {
            let stub = Stub::start(routes);
            let api = format!("http://127.0.0.1:{}", stub.port);
            let mut args = argv(&["--api", &api, "--http", mode]);
            args.extend(now.clone());
            let got = run_quiet(args, &mut String::new());
            drop(stub);
            failures += (got != want) as i32;
            line(&mut out, got == want, &format!("{} [{}]", name, mode), &format!("exit {} (want {})", got, want));
        }
    }

    // The token never leaves for a non-GitHub host.
    let env = |k: &str| if k == "GITHUB_TOKEN" { Some("secret".to_string()) } else { None };
    let tok = crate::transport::resolve_token("http://127.0.0.1:1", &env);
    failures += tok.is_some() as i32;
    out.push_str(&format!(
        "{}  {:<62}\n",
        if tok.is_none() { "ok  " } else { "FAIL" },
        "token withheld from a non-GitHub API host"
    ));

    out.push_str(&format!(
        "seam-check self-test: {}\n",
        if failures == 0 { "PASS".to_string() } else { format!("{} FAILED", failures) }
    ));
    stdout.push_str(&out);
    if failures == 0 { 0 } else { 1 }
}
