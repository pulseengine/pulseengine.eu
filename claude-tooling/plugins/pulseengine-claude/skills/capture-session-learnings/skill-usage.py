#!/usr/bin/env python3
"""Count how often agent skills are really used, from local Claude Code transcripts.

Reads ~/.claude/projects/*/*.jsonl and ~/.claude/projects/*/*/subagents/*.jsonl
and prints AGGREGATES ONLY: per skill, invocations split model / user-slash /
subagent, the number of sessions using it, top repos (a repo is the last path
component of the session's working directory, or the directory above a
`.claude/worktrees/` checkout), direct SKILL.md reads, then the sessions
using any skill and the date window.

PRIVACY: it NEVER prints transcript content, prompts, skill arguments, tool
output or file paths. The only strings that leave the reader are skill names,
plugin names and repo names, each checked against [a-z0-9._:-]{1,64}; anything
else is dropped, not echoed. Counting a "model" invocation reads only the tool
name and the `skill` field of a Skill call; the `args` field is never read.

What is counted (transcript types user and assistant only; a repeated uuid in
one file counts once):
  model       an assistant Skill tool call; in a subagents/ file it is
              "subagent" instead
  user_slash  a user message `<command-name>/skill</command-name>` whose name
              is an installed skill or a skill seen in a Skill call (so /login
              and /plugin are not counted)
  skill_md_reads  an assistant Read of a path ending skills/<name>/SKILL.md

Use (monthly, see skills/capture-session-learnings/SKILL.md):
  skill-usage.py --since 2026-10-06
  skill-usage.py --format json --source my-box --out report.json
  skill-usage.py --format json --source my-box --post     (to warte)

--format json prints the `skill-usage.v1` report (schema in pulseengine/warte
#125), self-validated before it is printed; a violation exits 2. --source
LABEL is required for json and is never derived from the hostname. --post
sends that report to $PULSEENGINE_WARTE_URL/api/skill-usage with a Bearer
token from PULSEENGINE_WARTE_TOKEN or the first line of the file named by
PULSEENGINE_WARTE_TOKEN_FILE (never in argv). No URL: says so, exit 0. HTTP
404 (warte lacks the endpoint): says so, exit 0.

--self-test runs the reader over fixtures/skill-usage/ and a stub warte.
Exit: 0 ok, 1 usage or post failure, 2 report failed its own schema or a
self-test check failed. Python 3.9+, stdlib only.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import glob
import http.server
import io
import json
import os
import re
import sys
import tempfile
import threading
import urllib.error
import urllib.request

SCHEMA = "skill-usage.v1"
NAME_RE = re.compile(r"^[a-z0-9._:-]{1,64}$")
SOURCE_RE = re.compile(r"^[a-z0-9-]{1,32}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SLASH_RE = re.compile(r"<command-name>\s*/?([^<\s]{1,100})\s*</command-name>")
SKILL_MD_RE = re.compile(r"(?:^|/)skills/([^/]+)/SKILL\.md$")
LOCAL_PLUGIN = "local"
MAX_REPOS = 10
HERE = os.path.dirname(os.path.abspath(__file__))


def split_name(raw):
    """(plugin, skill) from 'plugin:skill' or 'skill'; None when either is not a safe name."""
    if not isinstance(raw, str):
        return None
    raw = raw.strip().lstrip("/").lower()
    plugin, _, skill = raw.rpartition(":")
    plugin = plugin or LOCAL_PLUGIN
    if NAME_RE.match(plugin) and NAME_RE.match(skill) and ":" not in skill:
        return plugin, skill
    return None


def repo_of(cwd):
    if not isinstance(cwd, str) or not cwd:
        return None
    parts = [p for p in cwd.replace("\\", "/").split("/") if p]
    if ".claude" in parts and "worktrees" in parts:
        parts = parts[:parts.index(".claude")]
    if not parts:
        return None
    r = parts[-1].lower()
    return r if NAME_RE.match(r) else None


def installed_skills(plugins_dir):
    """Skill directory names of the newest version of each installed plugin."""
    out = set()
    for vdirs in glob.glob(os.path.join(plugins_dir, "*", "*")):
        versions = [d for d in glob.glob(os.path.join(vdirs, "*")) if os.path.isdir(d)]

        def key(d):
            return [int(x) if x.isdigit() else 0 for x in re.split(r"[.\-+]", os.path.basename(d))]
        if not versions:
            continue
        latest = sorted(versions, key=key)[-1]
        for s in glob.glob(os.path.join(latest, "skills", "*")):
            n = os.path.basename(s)
            if os.path.isdir(s) and NAME_RE.match(n):
                out.add(n)
    return sorted(out)


def transcript_files(projects_dir):
    for f in sorted(glob.glob(os.path.join(projects_dir, "*", "*.jsonl"))):
        yield f, False
    for f in sorted(glob.glob(os.path.join(projects_dir, "*", "*", "subagents", "*.jsonl"))):
        yield f, True


def collect(projects_dir, installed, since=None):
    """Aggregate counts. Returns a dict of counters; holds no transcript text."""
    sessions, with_skill = set(), set()
    calls = []          # (plugin, skill, kind, session, repo)
    slashes = []        # (plugin, skill, session, repo) candidates
    reads = []          # (skill, session)
    first = last = None
    for path, is_sub in transcript_files(projects_dir):
        seen = set()
        fallback = os.path.basename(path)[:-6]
        if is_sub:
            fallback = os.path.basename(os.path.dirname(os.path.dirname(path)))
        try:
            fh = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                if '"user"' not in line and '"assistant"' not in line:
                    continue
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(o, dict) or o.get("type") not in ("user", "assistant"):
                    continue
                uid = o.get("uuid")
                if isinstance(uid, str):
                    if uid in seen:
                        continue
                    seen.add(uid)
                ts = o.get("timestamp")
                day = ts[:10] if isinstance(ts, str) and DATE_RE.match(ts[:10]) else None
                if since and (day is None or day < since):
                    continue
                if day:
                    first = day if first is None or day < first else first
                    last = day if last is None or day > last else last
                sid = o.get("sessionId") if isinstance(o.get("sessionId"), str) else fallback
                sessions.add(sid)
                repo = repo_of(o.get("cwd"))
                content = (o.get("message") or {}).get("content") if isinstance(o.get("message"), dict) else None
                if o["type"] == "user" and isinstance(content, str):
                    m = SLASH_RE.search(content)
                    if m:
                        n = split_name(m.group(1))
                        if n:
                            slashes.append((n[0], n[1], sid, repo))
                elif o["type"] == "assistant" and isinstance(content, list):
                    for b in content:
                        if not isinstance(b, dict) or b.get("type") != "tool_use":
                            continue
                        inp = b.get("input") if isinstance(b.get("input"), dict) else {}
                        if b.get("name") == "Skill":
                            n = split_name(inp.get("skill"))
                            if n:
                                calls.append((n[0], n[1], "subagent" if is_sub else "model", sid, repo))
                        elif b.get("name") == "Read" and isinstance(inp.get("file_path"), str):
                            m = SKILL_MD_RE.search(inp["file_path"].replace("\\", "/"))
                            if m and NAME_RE.match(m.group(1).lower()):
                                reads.append((m.group(1).lower(), sid))
    known = {s for _, s, _, _, _ in calls} | set(installed)
    stats = {}

    def row(plugin, skill):
        r = stats.setdefault(skill, {"plugin": plugin, "inv": collections.Counter(),
                                     "sessions": set(), "reads": 0,
                                     "repos": collections.Counter()})
        if r["plugin"] == LOCAL_PLUGIN and plugin != LOCAL_PLUGIN:
            r["plugin"] = plugin
        return r
    for plugin, skill, kind, sid, repo in calls:
        r = row(plugin, skill)
        r["inv"][kind] += 1
        r["sessions"].add(sid)
        with_skill.add(sid)
        if repo:
            r["repos"][repo] += 1
    for plugin, skill, sid, repo in slashes:
        if skill not in known:
            continue
        r = row(plugin, skill)
        r["inv"]["user_slash"] += 1
        r["sessions"].add(sid)
        with_skill.add(sid)
        if repo:
            r["repos"][repo] += 1
    for skill, sid in reads:
        row(LOCAL_PLUGIN, skill)["reads"] += 1
    return {"sessions_total": len(sessions), "sessions_with_skill": len(with_skill),
            "stats": stats, "from": first, "to": last}


def build_report(agg, installed, source, since, now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    today = now.strftime("%Y-%m-%d")
    skills = []
    for name in sorted(agg["stats"]):
        r = agg["stats"][name]
        skills.append({
            "name": name, "plugin": r["plugin"],
            "invocations": {"model": r["inv"]["model"], "user_slash": r["inv"]["user_slash"],
                            "subagent": r["inv"]["subagent"]},
            "sessions": len(r["sessions"]), "skill_md_reads": r["reads"],
            "repos": [{"repo": k, "invocations": v}
                      for k, v in sorted(r["repos"].items(), key=lambda kv: (-kv[1], kv[0]))[:MAX_REPOS]],
        })
    skills.sort(key=lambda s: (-sum(s["invocations"].values()), s["name"]))
    return {"schema": SCHEMA, "source": source,
            "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "window": {"from": since or agg["from"] or today, "to": agg["to"] or today},
            "sessions_total": agg["sessions_total"],
            "sessions_with_skill": agg["sessions_with_skill"],
            "installed": list(installed), "skills": skills}


def validate(rep):
    """Problems with a report against skill-usage.v1; empty when valid. Never quotes values."""
    bad = []

    def keys(o, want, where):
        if not isinstance(o, dict):
            bad.append(where + " is not an object")
            return False
        if set(o) != set(want):
            bad.append(where + " has unknown or missing fields")
            return False
        return True

    def count(v, where):
        if not (isinstance(v, int) and not isinstance(v, bool) and v >= 0):
            bad.append(where + " is not a non-negative integer")

    def name(v, where):
        if not (isinstance(v, str) and NAME_RE.match(v)):
            bad.append(where + " does not match the name class")
    if not keys(rep, ["schema", "source", "generated_at", "window", "sessions_total",
                      "sessions_with_skill", "installed", "skills"], "report"):
        return bad
    if rep["schema"] != SCHEMA:
        bad.append("schema is not " + SCHEMA)
    if not (isinstance(rep["source"], str) and SOURCE_RE.match(rep["source"])):
        bad.append("source does not match [a-z0-9-]{1,32}")
    if not (isinstance(rep["generated_at"], str) and STAMP_RE.match(rep["generated_at"])):
        bad.append("generated_at is not an ISO UTC timestamp")
    if keys(rep["window"], ["from", "to"], "window"):
        for k in ("from", "to"):
            v = rep["window"][k]
            try:
                datetime.date.fromisoformat(v)
                ok = bool(DATE_RE.match(v))
            except (TypeError, ValueError):
                ok = False
            if not ok:
                bad.append("window." + k + " is not an ISO date")
    count(rep["sessions_total"], "sessions_total")
    count(rep["sessions_with_skill"], "sessions_with_skill")
    if not isinstance(rep["installed"], list):
        bad.append("installed is not a list")
    else:
        for n in rep["installed"]:
            name(n, "installed entry")
    if not isinstance(rep["skills"], list):
        bad.append("skills is not a list")
        return bad
    for s in rep["skills"]:
        if not keys(s, ["name", "plugin", "invocations", "sessions", "skill_md_reads", "repos"], "skill"):
            continue
        name(s["name"], "skill name")
        name(s["plugin"], "skill plugin")
        if keys(s["invocations"], ["model", "user_slash", "subagent"], "invocations"):
            for k in ("model", "user_slash", "subagent"):
                count(s["invocations"][k], "invocations." + k)
        count(s["sessions"], "skill sessions")
        count(s["skill_md_reads"], "skill_md_reads")
        if not isinstance(s["repos"], list):
            bad.append("repos is not a list")
            continue
        for r in s["repos"]:
            if keys(r, ["repo", "invocations"], "repo entry"):
                name(r["repo"], "repo name")
                count(r["invocations"], "repo invocations")
    return bad


def render_text(rep):
    w = rep["window"]
    pct = (100.0 * rep["sessions_with_skill"] / rep["sessions_total"]) if rep["sessions_total"] else 0.0
    out = ["Skill usage %s to %s (aggregates only: no prompts, no paths)" % (w["from"], w["to"]),
           "sessions: %d, using any skill: %d (%.1f%%)" % (
               rep["sessions_total"], rep["sessions_with_skill"], pct), "",
           "%-34s %5s %5s %5s %5s %5s  %s" % ("skill", "model", "slash", "sub", "sess", "reads", "top repos")]
    for s in rep["skills"]:
        i = s["invocations"]
        out.append("%-34s %5d %5d %5d %5d %5d  %s" % (
            s["plugin"] + ":" + s["name"], i["model"], i["user_slash"], i["subagent"], s["sessions"],
            s["skill_md_reads"], ", ".join("%s=%d" % (r["repo"], r["invocations"]) for r in s["repos"][:3])))
    used = {s["name"] for s in rep["skills"] if sum(s["invocations"].values())}
    never = [n for n in rep["installed"] if n not in used]
    out += ["", "installed, never invoked (%d of %d): %s" % (
        len(never), len(rep["installed"]), ", ".join(never) or "none")]
    return "\n".join(out)


def load_token(env=None):
    """(token, why-not). Same rules as factory-notice/notice.py load_token."""
    env = os.environ if env is None else env
    tok = (env.get("PULSEENGINE_WARTE_TOKEN") or "").strip()
    if not tok and env.get("PULSEENGINE_WARTE_TOKEN_FILE"):
        try:
            with open(env["PULSEENGINE_WARTE_TOKEN_FILE"], "r", encoding="ascii") as f:
                tok = f.readline().strip()
        except (OSError, UnicodeDecodeError) as e:
            return None, "PULSEENGINE_WARTE_TOKEN_FILE could not be read (%s)" % type(e).__name__
    if tok and not (tok.isascii() and tok.isprintable() and not any(c.isspace() for c in tok)):
        return None, "the warte token has whitespace or control characters; ignoring it"
    return (tok or None), None


def post(rep, env=None, err=None):
    """POST the report. Exit code: 0 sent / no URL / 404, 1 failed."""
    env = os.environ if env is None else env
    err = err or sys.stderr
    base = (env.get("PULSEENGINE_WARTE_URL") or "").strip().rstrip("/")
    if not base:
        print("PULSEENGINE_WARTE_URL is not set; nothing posted", file=err)
        return 0
    tok, why = load_token(env)
    if why:
        print(why, file=err)
    headers = {"Content-Type": "application/json", "User-Agent": "pulseengine-skill-usage"}
    if tok:
        headers["Authorization"] = "Bearer " + tok   # header only, never argv
    else:
        print("no warte token (PULSEENGINE_WARTE_TOKEN or PULSEENGINE_WARTE_TOKEN_FILE); "
              "the write will probably be refused", file=err)
    req = urllib.request.Request(base + "/api/skill-usage", data=json.dumps(rep).encode("utf-8"),
                                 headers=headers, method="POST")
    ctx = None
    if env.get("PULSEENGINE_WARTE_CACERT"):
        import ssl
        ctx = ssl.create_default_context(cafile=env["PULSEENGINE_WARTE_CACERT"])
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            print("posted skill-usage report (HTTP %d)" % resp.status, file=err)
            return 0
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("warte has no /api/skill-usage endpoint yet (HTTP 404); nothing posted", file=err)
            return 0
        print("warte refused the report (HTTP %d)" % e.code, file=err)
        return 1
    except (urllib.error.URLError, OSError) as e:
        print("warte is not reachable (%s)" % type(e).__name__, file=err)
        return 1


def parse_since(v):
    try:
        datetime.date.fromisoformat(v)
        if DATE_RE.match(v):
            return v
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("--since wants YYYY-MM-DD")


def make_parser():
    ap = argparse.ArgumentParser(
        description=(__doc__ or "").split("\n\n")[0] + "\n\nPRIVACY: prints aggregates only. It NEVER prints "
        "transcript content, prompts, skill arguments or file paths; only skill, plugin and repo names.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", type=parse_since, metavar="YYYY-MM-DD", help="only events on or after this date")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--source", metavar="LABEL", help="report label [a-z0-9-]{1,32}; required for json; never the hostname")
    ap.add_argument("--out", metavar="FILE", help="also write the json report to FILE")
    ap.add_argument("--post", action="store_true", help="POST the json report to $PULSEENGINE_WARTE_URL/api/skill-usage")
    ap.add_argument("--projects-dir", default=os.path.join("~", ".claude", "projects"))
    ap.add_argument("--plugins-dir", default=os.path.join("~", ".claude", "plugins", "cache"))
    ap.add_argument("--self-test", action="store_true")
    return ap


def run(args, out=None, err=None):
    out, err = out or sys.stdout, err or sys.stderr
    want_json = args.format == "json" or args.post or args.out
    if want_json and not (args.source and SOURCE_RE.match(args.source)):
        print("--source LABEL ([a-z0-9-]{1,32}) is required for json, --out and --post", file=err)
        return 1
    installed = installed_skills(os.path.expanduser(args.plugins_dir))
    agg = collect(os.path.expanduser(args.projects_dir), installed, args.since)
    rep = build_report(agg, installed, args.source or "local", args.since)
    if want_json:
        problems = validate(rep)
        if problems:
            print("report violates %s: %s" % (SCHEMA, "; ".join(problems[:5])), file=err)
            return 2
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2)
            f.write("\n")
    if args.format == "json":
        out.write(json.dumps(rep, indent=2) + "\n")
    else:
        out.write(render_text(rep) + "\n")
    if args.post:
        return post(rep, err=err)
    return 0


# ── self-test ────────────────────────────────────────────────────────────────

CANARY = ("zebrafish-canary", "SECRET PROMPT", "/work/private", "file.rs")


def self_test():
    fails = []

    def check(label, ok):
        print(("ok   " if ok else "FAIL ") + label)
        if not ok:
            fails.append(label)
    fx = os.path.join(HERE, "fixtures", "skill-usage", "projects")
    with tempfile.TemporaryDirectory() as td:
        for plug, ver, names in (("demo", "1.0.0", ["old"]), ("demo", "1.2.0", ["alpha", "beta", "gamma", "delta"])):
            for n in names:
                os.makedirs(os.path.join(td, "cache", "mkt", plug, ver, "skills", n))
        plugins = os.path.join(td, "cache")
        inst = installed_skills(plugins)
        check("installed: newest version only", inst == ["alpha", "beta", "delta", "gamma"])
        agg = collect(fx, inst)
        rep = build_report(agg, inst, "test-box", None,
                           now=datetime.datetime(2026, 11, 5, 12, 0, 0, tzinfo=datetime.timezone.utc))
        check("report validates", validate(rep) == [])
        by = {s["name"]: s for s in rep["skills"]}
        a = by.get("alpha", {})
        check("alpha split model 2 / slash 1 / subagent 1 (dup uuid, blob type, /plugin ignored)",
              a.get("invocations") == {"model": 2, "user_slash": 1, "subagent": 1})
        check("alpha plugin and sessions", a.get("plugin") == "demo" and a.get("sessions") == 2)
        check("alpha repos synth 3, loom 1",
              a.get("repos") == [{"repo": "synth", "invocations": 3}, {"repo": "loom", "invocations": 1}])
        check("bare skill gets the local plugin", by.get("beta", {}).get("plugin") == LOCAL_PLUGIN)
        check("direct SKILL.md read counted", by.get("gamma", {}).get("skill_md_reads") == 1)
        check("unsafe skill name dropped", set(by) == {"alpha", "beta", "gamma"})
        check("sessions 3, with skill 2", (rep["sessions_total"], rep["sessions_with_skill"]) == (3, 2))
        check("window", rep["window"] == {"from": "2026-09-01", "to": "2026-10-20"})
        s = collect(fx, inst, "2026-10-01")
        check("--since drops the September session", (s["sessions_total"], s["sessions_with_skill"]) == (2, 1))
        check("--since window starts at the date",
              build_report(s, inst, "x", "2026-10-01")["window"]["from"] == "2026-10-01")
        text = render_text(rep)
        js = json.dumps(rep)
        check("never-invoked line lists delta and the read-only gamma",
              "never invoked (2 of 4): delta, gamma" in text)
        check("no transcript content in text or json",
              not any(c in text or c in js for c in CANARY))
        # negative controls: the validator and the leak check can fail
        for label, mut in (
            ("unknown field", lambda r: r.update(extra=1)),
            ("bad source", lambda r: r.update(source="Host_Name")),
            ("prompt-like name", lambda r: r["skills"][0].update(name="ignore previous instructions")),
            ("negative count", lambda r: r["skills"][0]["invocations"].update(model=-1)),
            ("bool count", lambda r: r.update(sessions_total=True)),
            ("bad date", lambda r: r["window"].update(to="2026-13-40")),
        ):
            bad = json.loads(js)
            mut(bad)
            probs = validate(bad)
            check("validator rejects " + label, bool(probs))
            check("rejection of %s does not quote input" % label,
                  not any("ignore previous" in p or "Host_Name" in p for p in probs))
        check("leak check fires on a leaking string", any(c in text + "\nzebrafish-canary" for c in CANARY))
        # CLI: json needs --source
        e = io.StringIO()
        ns = make_parser().parse_args(["--format", "json", "--projects-dir", fx, "--plugins-dir", plugins])
        check("json without --source exits 1", run(ns, io.StringIO(), e) == 1)
        o = io.StringIO()
        outf = os.path.join(td, "r.json")
        ns = make_parser().parse_args(["--format", "json", "--source", "test-box", "--out", outf,
                                       "--projects-dir", fx, "--plugins-dir", plugins])
        check("json run exits 0", run(ns, o, io.StringIO()) == 0)
        check("--out file equals stdout", open(outf, encoding="utf-8").read() == o.getvalue())
        check("--help states the privacy rule", "NEVER prints" in make_parser().format_help())
        # stub warte
        seen = []

        class H(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                seen.append((self.path, self.headers.get("Authorization"), body))
                self.send_response(self.server.reply)
                self.end_headers()

            def log_message(self, *a):
                pass
        srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        srv.reply = 200
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        env = {"PULSEENGINE_WARTE_URL": "http://127.0.0.1:%d" % srv.server_port,
               "PULSEENGINE_WARTE_TOKEN": "tok.abc.123"}
        e = io.StringIO()
        check("post 200 exits 0", post(rep, env, e) == 0)
        check("post path, bearer and body",
              len(seen) == 1 and seen[0][0] == "/api/skill-usage" and seen[0][1] == "Bearer tok.abc.123"
              and json.loads(seen[0][2]) == rep)
        check("token never printed", "tok.abc.123" not in e.getvalue())
        tf = os.path.join(td, "tok")
        with open(tf, "w") as f:
            f.write("file.tok.9\nsecond line\n")
        post(rep, {"PULSEENGINE_WARTE_URL": env["PULSEENGINE_WARTE_URL"], "PULSEENGINE_WARTE_TOKEN_FILE": tf}, io.StringIO())
        check("token read from file's first line", seen[-1][1] == "Bearer file.tok.9")
        check("token with whitespace is refused", load_token({"PULSEENGINE_WARTE_TOKEN": "a b"})[0] is None)
        srv.reply = 404
        e = io.StringIO()
        check("post 404 says so and exits 0", post(rep, env, e) == 0 and "no /api/skill-usage endpoint" in e.getvalue())
        srv.reply = 403
        check("post 403 exits 1 (negative control)", post(rep, env, io.StringIO()) == 1)
        e = io.StringIO()
        check("no URL: says so, exits 0", post(rep, {}, e) == 0 and "not set" in e.getvalue())
        srv.shutdown()
    print("%d failure(s)" % len(fails))
    return 2 if fails else 0


def main(argv=None):
    ap = make_parser()
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
