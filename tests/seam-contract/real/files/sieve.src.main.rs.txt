//! sieve: the shared CI path classifier. Which heavy CI jobs does a change
//! touch? When unsure, everything runs.

mod check;
mod classify;
mod config;
mod equivalence;
mod gitrepo;
mod graph;
mod lex;
mod observe;
mod repo;
mod workflows;

use classify::Verdict;
use config::Config;
use repo::Repo;
use serde_json::json;
use std::io::Write;
use std::path::PathBuf;
use std::process::ExitCode;

pub const CLASSIFY_SCHEMA: &str = "sieve.classify.v1";
pub const GRAPH_SCHEMA: &str = "sieve.graph.v1";
pub const CHECK_SCHEMA: &str = "sieve.check.v1";
pub const WORKFLOWS_SCHEMA: &str = "sieve.workflows.v1";
pub const CONFIG_SCHEMA: &str = "sieve.config.v1";
pub const EQUIVALENCE_SCHEMA: &str = "sieve.equivalence.v1";
pub const OBSERVE_SCHEMA: &str = "sieve.observe.v1";

const USAGE: &str = "\
sieve: which heavy CI jobs does a change touch? When unsure, everything runs.

USAGE:
  sieve classify --config <sieve.toml> [--root <dir>]
                 (--base <sha> [--head <sha>] | --paths-file <file> | --paths <p>...)
                 [--event <name>] [--format json|github-output] [--explain]
  sieve graph --config <sieve.toml> [--root <dir>] [--format json]
  sieve check-graph --config <sieve.toml> [--root <dir>] [--control <name>]...
                    [--depinfo <class>=<file.d>]... [--format json|text]
  sieve check-workflows --config <sieve.toml> [--root <dir>] [--workflows <dir>]
                        [--required <file>] [--format json|text]
  sieve equivalence --config <sieve.toml> --old <detector> [--old-arg <a>]...
                    [--ref <rev> (origin/main)] [--commits <n> (400)]
                    [--map <old-output>=<class>]... [--accept-narrowing <class>]...
                    [--format json|text]
  sieve observe --config <sieve.toml> --verdict <classify.json> --results <jobs.json>
                [--format json|text]
  sieve --version | --help

classify: exit 0 with a verdict (run_all included); exit 2 on a usage or
config error. Every failure selects everything; nothing selects nothing.
  git mode (--base): event must be pull_request, else everything runs.
  --paths / --paths-file: classified as a pull_request, no git call made.
  GATE_PROBE_FILES=<file>: the changed paths, replacing event and diff.
  --explain: per class, the changed path that selected it, the claim it
  matched and the edge it came from (cargo, include, literal, bazel, ...),
  or its unresolved input; on stderr, and as `explain` in the JSON.
  --format github-output appends <class>=true|false and run_all=... to
  $GITHUB_OUTPUT (stdout if unset). Wire jobs with
    !cancelled() && (needs.C.result != 'success' || needs.C.outputs.<o> != 'false')
check-graph: exit 0 pass, 1 a control failed, 2 usage, 3 refused.
  controls: graph-inputs, cargo-metadata, true-inputs, no-job, inert-overlap,
            fail-open, bazel-srcs, bazel-snapshot, depinfo
check-workflows: exit 0 pass, 1 a gate failed, 2 usage, 3 refused (an input is
missing). For every required context (default .github/required-contexts.txt, or
[workflows] required_contexts): (a) its workflow triggers on pull_request with no
paths/paths-ignore key, no branch or types restriction, and on merge_group; (b)
its job is skipped only through the classifier (a step running `sieve classify
... --format github-output`), reading only the outputs the HAND-MAINTAINED
[workflows.job_outputs] map gives it; (c) the classifier fails open.
equivalence: the switch-over gate. For each of the last N first-parent
  commits of --ref, runs the old detector with GATE_PROBE_FILES=<its diff>
  and GITHUB_OUTPUT=<file>, classifies the same paths with sieve, and
  compares class by class. Exit 0 none narrower and no error, 1 a narrowing
  or an uncompared commit, 2 usage, 3 refused (nothing compared).
  --map may repeat an old output to map it to several classes.
  --accept-narrowing <class> declares that class's narrowing intended: it is
  listed (ACCEPTED-NARROWER) but does not fail the gate.
observe: the observed-miss counter. Given sieve's verdict for a commit and the
  job conclusions of a run where every job ran ([{name, conclusion}] or the
  API's {jobs: [...]}), lists each job that failed while all its classes
  ([workflows.job_outputs]) were false. Exit 0 none, 1 a miss, 2 usage,
  3 refused (unreadable input or no gated job).
";

struct Args {
    cmd: String,
    config: Option<String>,
    root: Option<String>,
    base: Option<String>,
    head: Option<String>,
    paths_file: Option<String>,
    paths: Vec<String>,
    event: Option<String>,
    format: Option<String>,
    controls: Vec<String>,
    depinfo: Vec<String>,
    workflows: Option<String>,
    required: Option<String>,
    explain: bool,
    old: Option<String>,
    old_args: Vec<String>,
    refspec: Option<String>,
    commits: Option<String>,
    map: Vec<String>,
    accept_narrowing: Vec<String>,
    verdict: Option<String>,
    results: Option<String>,
}

fn parse_args(argv: &[String]) -> Result<Args, String> {
    let mut it = argv.iter().peekable();
    let cmd = it.next().ok_or("no command")?.clone();
    let mut a = Args {
        cmd,
        config: None,
        root: None,
        base: None,
        head: None,
        paths_file: None,
        paths: vec![],
        event: None,
        format: None,
        controls: vec![],
        depinfo: vec![],
        workflows: None,
        required: None,
        explain: false,
        old: None,
        old_args: vec![],
        refspec: None,
        commits: None,
        map: vec![],
        accept_narrowing: vec![],
        verdict: None,
        results: None,
    };
    while let Some(flag) = it.next() {
        let mut val = |name: &str| it.next().cloned().ok_or(format!("{name} needs a value"));
        match flag.as_str() {
            "--config" => a.config = Some(val("--config")?),
            "--root" => a.root = Some(val("--root")?),
            "--base" => a.base = Some(val("--base")?),
            "--head" => a.head = Some(val("--head")?),
            "--paths-file" => a.paths_file = Some(val("--paths-file")?),
            "--event" => a.event = Some(val("--event")?),
            "--format" => a.format = Some(val("--format")?),
            "--control" => a.controls.push(val("--control")?),
            "--depinfo" => a.depinfo.push(val("--depinfo")?),
            "--explain" => a.explain = true,
            "--old" => a.old = Some(val("--old")?),
            "--old-arg" => a.old_args.push(val("--old-arg")?),
            "--ref" => a.refspec = Some(val("--ref")?),
            "--commits" => a.commits = Some(val("--commits")?),
            "--map" => a.map.push(val("--map")?),
            "--accept-narrowing" => a.accept_narrowing.push(val("--accept-narrowing")?),
            "--verdict" => a.verdict = Some(val("--verdict")?),
            "--results" => a.results = Some(val("--results")?),
            "--workflows" => a.workflows = Some(val("--workflows")?),
            "--required" => a.required = Some(val("--required")?),
            "--paths" => {
                while let Some(p) = it.peek() {
                    if p.starts_with("--") {
                        break;
                    }
                    a.paths.push(it.next().unwrap().clone());
                }
            }
            other => return Err(format!("unknown argument `{other}`")),
        }
    }
    Ok(a)
}

fn version() -> String {
    format!(
        "sieve {}\nschemas: {CLASSIFY_SCHEMA} {GRAPH_SCHEMA} {CHECK_SCHEMA} {WORKFLOWS_SCHEMA} {EQUIVALENCE_SCHEMA} {OBSERVE_SCHEMA} {CONFIG_SCHEMA}",
        env!("CARGO_PKG_VERSION")
    )
}

fn usage_error(msg: &str) -> ExitCode {
    eprintln!("sieve: {msg}\n\n{USAGE}");
    ExitCode::from(2)
}

fn main() -> ExitCode {
    let argv: Vec<String> = std::env::args().skip(1).collect();
    match argv.first().map(String::as_str) {
        None | Some("--help") | Some("-h") | Some("help") => {
            print!("{USAGE}");
            return if argv.is_empty() {
                ExitCode::from(2)
            } else {
                ExitCode::SUCCESS
            };
        }
        Some("--version") | Some("-V") => {
            println!("{}", version());
            return ExitCode::SUCCESS;
        }
        _ => {}
    }
    if ![
        "classify",
        "graph",
        "check-graph",
        "check-workflows",
        "equivalence",
        "observe",
    ]
    .contains(&argv[0].as_str())
    {
        return usage_error(&format!("unknown command `{}`", argv[0]));
    }
    let a = match parse_args(&argv) {
        Ok(a) => a,
        Err(e) => return usage_error(&e),
    };
    let root = PathBuf::from(a.root.clone().unwrap_or_else(|| ".".into()));
    let Some(cfg_arg) = a.config.clone() else {
        return usage_error("--config is required");
    };
    let cfg_path = if PathBuf::from(&cfg_arg).is_absolute() {
        PathBuf::from(&cfg_arg)
    } else {
        root.join(&cfg_arg)
    };
    let cfg_text = match std::fs::read_to_string(&cfg_path) {
        Ok(t) => t,
        Err(e) => return usage_error(&format!("{}: {e}", cfg_path.display())),
    };
    let rel_cfg = cfg_path
        .canonicalize()
        .ok()
        .zip(root.canonicalize().ok())
        .and_then(|(c, r)| {
            c.strip_prefix(&r)
                .ok()
                .map(|p| p.to_string_lossy().replace('\\', "/"))
        })
        .unwrap_or(cfg_arg.clone());
    let cfg = match config::parse(&cfg_text, &rel_cfg) {
        Ok(c) => c,
        Err(e) => return usage_error(&format!("invalid config: {e}")),
    };
    match a.cmd.as_str() {
        "classify" => cmd_classify(&a, root, &cfg),
        "graph" => cmd_graph(&a, root, &cfg),
        "check-graph" => {
            check::cmd_check_graph(&a.controls, &a.depinfo, a.format.as_deref(), root, &cfg)
        }
        "check-workflows" => workflows::cmd_check_workflows(
            a.workflows.as_deref(),
            a.required.as_deref(),
            a.format.as_deref(),
            root,
            &cfg,
        ),
        "equivalence" => {
            let Some(old) = a.old.clone() else {
                return usage_error("equivalence needs --old <detector>");
            };
            let commits = match a.commits.as_deref().unwrap_or("400").parse::<usize>() {
                Ok(n) if n > 0 => n,
                _ => return usage_error("--commits takes a positive number"),
            };
            // one old output may stand for several classes: --map code=a --map code=b
            let mut map: std::collections::BTreeMap<String, Vec<String>> = Default::default();
            for m in &a.map {
                let Some((o, n)) = m.split_once('=') else {
                    return usage_error("--map takes <old-output>=<class>");
                };
                if !cfg.classes.iter().any(|c| c.name == n) {
                    return usage_error(&format!("--map {m}: no class `{n}` in the config"));
                }
                let v = map.entry(o.to_string()).or_default();
                if !v.iter().any(|x| x == n) {
                    v.push(n.to_string());
                }
            }
            let mut accept_narrowing = std::collections::BTreeSet::new();
            for c in &a.accept_narrowing {
                if !cfg.classes.iter().any(|x| &x.name == c) {
                    return usage_error(&format!(
                        "--accept-narrowing: no class `{c}` in the config"
                    ));
                }
                accept_narrowing.insert(c.clone());
            }
            let format = a.format.clone().unwrap_or_else(|| "text".into());
            if !["json", "text"].contains(&format.as_str()) {
                return usage_error(&format!("unknown --format `{format}`"));
            }
            let opts = equivalence::Opts {
                old,
                old_args: a.old_args.clone(),
                refspec: a.refspec.clone().unwrap_or_else(|| "origin/main".into()),
                commits,
                map,
                accept_narrowing,
                format,
            };
            equivalence::cmd(&opts, root, &cfg)
        }
        "observe" => observe::cmd(
            a.verdict.as_deref(),
            a.results.as_deref(),
            a.format.as_deref(),
            &cfg,
        ),
        other => usage_error(&format!("unknown command `{other}`")),
    }
}

fn read_lines(path: &str) -> std::io::Result<Vec<String>> {
    Ok(std::fs::read_to_string(path)?
        .lines()
        .map(str::trim)
        .filter(|l| !l.is_empty())
        .map(str::to_string)
        .collect())
}

fn cmd_classify(a: &Args, root: PathBuf, cfg: &Config) -> ExitCode {
    let format = a.format.as_deref().unwrap_or("json");
    if !["json", "github-output"].contains(&format) {
        return usage_error(&format!("unknown --format `{format}`"));
    }
    let probe = std::env::var("GATE_PROBE_FILES")
        .ok()
        .filter(|s| !s.is_empty());
    let explicit = a.paths_file.is_some() || !a.paths.is_empty();
    let modes = [
        a.base.is_some(),
        a.paths_file.is_some(),
        !a.paths.is_empty(),
    ]
    .iter()
    .filter(|x| **x)
    .count();
    if modes > 1 {
        return usage_error("give one of --base, --paths-file, --paths");
    }
    if probe.is_some() && explicit {
        return usage_error("GATE_PROBE_FILES and --paths/--paths-file are exclusive");
    }
    if a.head.is_some() && a.base.is_none() {
        return usage_error("--head needs --base");
    }
    let paths_from_file = match &a.paths_file {
        Some(f) => match read_lines(f) {
            Ok(p) => Some(p),
            Err(e) => return usage_error(&format!("--paths-file {f}: {e}")),
        },
        None => None,
    };

    // Everything below fails open: a panic anywhere becomes run_all.
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        if let Some(pf) = &probe {
            let repo = Repo {
                root: root.clone(),
                git: false,
            };
            return match read_lines(pf) {
                Ok(p) => classify::classify_paths(&repo, cfg, &p),
                Err(e) => Verdict::all(cfg, format!("GATE_PROBE_FILES {pf} unreadable: {e}")),
            };
        }
        if explicit {
            let repo = Repo {
                root: root.clone(),
                git: false,
            };
            let ev = a.event.as_deref().unwrap_or("pull_request");
            if ev != "pull_request" {
                return Verdict::all(cfg, format!("event {ev} is not pull_request"));
            }
            let paths = paths_from_file.clone().unwrap_or_else(|| a.paths.clone());
            return classify::classify_paths(&repo, cfg, &paths);
        }
        classify::git_mode(
            &root,
            cfg,
            a.event.as_deref(),
            a.base.as_deref(),
            a.head.as_deref(),
        )
    }));
    let v = match result {
        Ok(v) => v,
        Err(p) => {
            let msg = p
                .downcast_ref::<String>()
                .cloned()
                .or_else(|| p.downcast_ref::<&str>().map(|s| s.to_string()))
                .unwrap_or_else(|| "panic".into());
            Verdict::all(cfg, format!("internal: classifier crashed: {msg}"))
        }
    };
    emit(&v, format, a.explain)
}

/// Escape a string for a log line, so a path cannot start or end a GitHub
/// workflow command (the runner's own escaping for command data).
fn esc(s: &str) -> String {
    s.replace('%', "%25")
        .replace('\r', "%0D")
        .replace('\n', "%0A")
}

fn emit(v: &Verdict, format: &str, explain: bool) -> ExitCode {
    let reason = esc(v.reason.as_deref().unwrap_or_default());
    eprintln!(
        "sieve: {}",
        if v.run_all {
            format!("run_all ({reason})")
        } else {
            "classified".into()
        }
    );
    for n in &v.notes {
        eprintln!("  -> {}", esc(n));
    }
    for u in &v.unknown_paths {
        eprintln!("  unknown: {}", esc(u));
    }
    if explain {
        for (class, why) in &v.explain {
            for w in why {
                let line = match (w.get("path"), w.get("unresolved")) {
                    (Some(p), _) => format!(
                        "{} via {} (claim {})",
                        p.as_str().unwrap_or(""),
                        w["via"].as_str().unwrap_or(""),
                        w["claim"].as_str().unwrap_or("")
                    ),
                    (_, Some(u)) => format!(
                        "unresolved {}: {}",
                        u["code"].as_str().unwrap_or(""),
                        u["input"].as_str().unwrap_or("")
                    ),
                    _ => continue,
                };
                eprintln!("  explain {class}: {}", esc(&line));
            }
        }
    }
    let warning = v.warn.then(|| {
        format!(
            "::warning title=sieve::{} -- every class selected",
            reason.replace('\n', " ")
        )
    });
    if format == "github-output" {
        let mut lines = vec![format!("run_all={}", v.run_all)];
        lines.extend(v.classes.iter().map(|(c, b)| format!("{c}={b}")));
        let body = lines.join("\n") + "\n";
        if let Some(w) = &warning {
            println!("{w}");
        }
        match std::env::var("GITHUB_OUTPUT")
            .ok()
            .filter(|s| !s.is_empty())
        {
            Some(f) => {
                let r = std::fs::OpenOptions::new()
                    .append(true)
                    .create(true)
                    .open(&f)
                    .and_then(|mut fh| fh.write_all(body.as_bytes()));
                if let Err(e) = r {
                    // No outputs written: the consumer's `!= 'false'` runs everything. Go red too.
                    eprintln!("sieve: cannot write GITHUB_OUTPUT {f}: {e}");
                    return ExitCode::from(2);
                }
                for l in &lines {
                    eprintln!("  {l}");
                }
            }
            None => print!("{body}"),
        }
    } else {
        if let Some(w) = &warning {
            eprintln!("{w}");
        }
        let mut out = json!({
            "schema": CLASSIFY_SCHEMA,
            "run_all": v.run_all,
            "reason": v.reason,
            "classes": v.classes,
            "unknown_paths": v.unknown_paths,
            "inputs_hash": v.inputs_hash,
            "unresolved": v.unresolved,
        });
        if explain {
            out["explain"] = json!(v.explain);
        }
        println!("{}", serde_json::to_string_pretty(&out).unwrap());
    }
    ExitCode::SUCCESS
}

fn cmd_graph(a: &Args, root: PathBuf, cfg: &Config) -> ExitCode {
    if let Some(f) = a.format.as_deref() {
        if f != "json" {
            return usage_error(&format!("unknown --format `{f}`"));
        }
    }
    let repo = Repo { root, git: false };
    match graph::derive(&repo, cfg) {
        Ok(g) => {
            let classes: serde_json::Map<String, serde_json::Value> = g
                .iter()
                .map(|(c, cg)| {
                    (
                        c.clone(),
                        json!({
                            "files": cg.claims.keys().collect::<Vec<_>>(),
                            "sources": cg.claims,
                            "unresolved": cg.unresolved.iter().map(|u| u.json()).collect::<Vec<_>>(),
                        }),
                    )
                })
                .collect();
            let mut run_all: Vec<String> = cfg.run_all_files.clone();
            run_all.extend(cfg.run_all_prefixes.iter().cloned());
            run_all.extend(cfg.run_all_basenames.iter().map(|b| format!("**/{b}")));
            run_all.extend(cfg.run_all_suffixes.iter().map(|s| format!("**/*{s}")));
            run_all.extend(cfg.run_all_dirs.iter().map(|d| format!("**/{d}/")));
            let mut inert = cfg.inert_files.clone();
            inert.extend(cfg.inert_prefixes.iter().cloned());
            let out = json!({
                "schema": GRAPH_SCHEMA,
                "classes": classes,
                "run_all_paths": run_all,
                "inert_paths": inert,
                "inputs_hash": classify::inputs_hash(cfg, &g),
            });
            println!("{}", serde_json::to_string_pretty(&out).unwrap());
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("sieve graph: {}: {}", e.code, e.message);
            ExitCode::from(3)
        }
    }
}
