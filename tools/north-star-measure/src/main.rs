use north_star_measure::{count::Rules, find_root, help, run, snapshot_matches, source::Source, verify::find_cosign, Objective};
use std::path::{Path, PathBuf};

fn main() {
    std::process::exit(real_main());
}

fn real_main() -> i32 {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|a| a == "-h" || a == "--help") {
        print!("{}", help());
        return 0;
    }
    if args.first().map(String::as_str) == Some("snapshot-matches") {
        if args.len() != 3 {
            eprintln!("usage: north-star-measure snapshot-matches COMMITTED.json LIVE.json");
            return 2;
        }
        return snapshot_matches(Path::new(&args[1]), Path::new(&args[2]));
    }
    let (mut objective, mut offline, mut root) = (None, None, None);
    let mut it = args.into_iter();
    while let Some(a) = it.next() {
        match a.as_str() {
            "--offline" | "--root" => {
                let Some(v) = it.next() else {
                    eprintln!("north-star-measure: {a} needs a directory");
                    return 2;
                };
                if a == "--offline" {
                    offline = Some(PathBuf::from(v));
                } else {
                    root = Some(PathBuf::from(v));
                }
            }
            s if objective.is_none() && Objective::parse(s).is_some() => objective = Objective::parse(s),
            s => {
                eprintln!("north-star-measure: unexpected argument {s:?}\n\n{}", help());
                return 2;
            }
        }
    }
    let Some(o) = objective else {
        eprintln!("north-star-measure: name an objective: o1, o3 or o5\n\n{}", help());
        return 2;
    };
    let root = match root {
        Some(r) => r,
        None => match std::env::current_dir().ok().and_then(|d| find_root(&d)) {
            Some(r) => r,
            None => {
                eprintln!("north-star-measure: no data/north-star.toml here or above; use --root");
                return 2;
            }
        },
    };
    let source = match offline {
        Some(d) if !d.is_dir() => {
            eprintln!("north-star-measure: --offline {} is not a directory", d.display());
            return 2;
        }
        Some(d) => Source::Offline(d),
        None => Source::Live,
    };
    run(o, &root, source, find_cosign(), Rules::REAL)
}
