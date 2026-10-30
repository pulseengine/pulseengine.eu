#!/usr/bin/env python3
# rivet: verifies REQ-CORE-CONTRACT-WHOLE
"""Fail if any plugin hook can hand Claude Code a context string it will not deliver.

Claude Code turns an additionalContext string over ~10k characters into a ~2.3 KB
preview plus a file path, and the model reads the preview. The 2026-10-30 tuition
study found the methodology block (~48 KB) cut that way on every session from June
to October: the operating contract never arrived, and nothing noticed.

This runs EVERY command hook that hooks/hooks.json registers (the list comes from
the file, so a new hook is covered the day it is wired) under worst-case inputs:
a fixture git repo with a 20 KB working-context checkpoint, a rivet.yaml and a
stub `rivet` that reports 2,000 open coverage gaps, PreToolUse events built to
make each guard say as much as it can, and the plugin's real memory and core.
It decodes the hook's JSON and measures each string the model would see
(additionalContext, permissionDecisionReason, systemMessage, reason).

  cap      every string is <= 9,500 characters;
  whole    the core contract block is delivered uncut: no "this block was cut"
           marker in the memory hook's output, and the core file's text is in it;
  covered  every hooks.json command was run at least once, and each one exited 0;
  clamp    factory-notice's clamp_context keeps a 30,000-char text under the cap
           and names the spill file.

Prints each hook's largest string (the per-session injected size). Exit: 0 all
hold, 1 a hook can exceed the cap or the core arrives cut, 2 cannot check.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "claude-tooling" / "plugins" / "pulseengine-claude"
HOOKS_JSON = PLUGIN / "hooks" / "hooks.json"
CORE = PLUGIN / "core" / "pulseengine-core.md"
CAP = 9500
CUT = "this block was cut at"
FIELDS = ("additionalContext", "permissionDecisionReason", "systemMessage", "reason")

STUB_RIVET = r'''#!/bin/sh
case "$1" in
  validate) echo "Result: PASS (0 warnings)"; echo "Schemas: common@0.3.0, dev@0.4.0" ;;
  stats) i=0; while [ $i -lt 400 ]; do echo "type-$i 7"; i=$((i+1)); done ;;
  coverage) i=0; while [ $i -lt 2000 ]; do echo "rule-number-$i  x  3 9  33.3%"; i=$((i+1)); done ;;
esac
exit 0
'''
STUB_GH = "#!/bin/sh\nexit 1\n"

FAILS = []


def fail(msg):
    FAILS.append(msg)
    print("FAIL " + msg)


def strings(stdout):
    """Every model-visible string in a hook's JSON output, by field name."""
    if not stdout.strip():
        return []
    try:
        out = json.loads(stdout)
    except ValueError:
        return [("(raw stdout)", stdout)]
    found = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in FIELDS and isinstance(v, str):
                    found.append((k, v))
                else:
                    walk(v)
    walk(out)
    return found


def events(cwd, matcher, event):
    """Worst-case inputs for a hook registered under (event, matcher)."""
    base = {"session_id": "size-check", "cwd": str(cwd), "hook_event_name": event,
            "transcript_path": str(cwd / "t.jsonl")}
    if event == "SessionStart":
        return [dict(base, source=s) for s in ("startup", "compact")]
    if event != "PreToolUse":
        return [dict(base, trigger="auto", reason="other")]
    m = matcher or ""
    out = []
    if "Bash" in m.split("|"):
        long_body = " ".join("host%d.local 10.0.%d.%d" % (i, i % 250, i % 250) for i in range(600))
        for cmd in ("gh pr merge 5 --admin", "git commit --no-gpg-sign -m x",
                    "git commit -m '%s'" % long_body, "gh pr create --title t --body '%s'" % long_body,
                    "gh pr merge 1 --auto -R acme/x && gh pr update-branch 2 -R acme/y && "
                    "gh pr merge 3 -R acme/z && git tag v1.0.0 && cargo publish"):
            out.append(dict(base, tool_name="Bash", tool_input={"command": cmd, "description": "x"}))
    if "Agent" in m.split("|") or "Task" in m.split("|"):
        out.append(dict(base, tool_name="Agent", tool_input={"prompt": "x" * 50000, "description": "d"}))
    for tool in ("Edit", "Write", "MultiEdit"):
        if tool in m.split("|"):
            body = "\n".join("ssh host%d.lan 192.168.%d.%d /Volumes/D%d" % (i, i % 250, i % 250, i)
                             for i in range(2000))
            ti = {"file_path": str(cwd / "big.txt")}
            if tool == "Write":
                ti["content"] = body
            elif tool == "Edit":
                ti.update(old_string="x", new_string=body)
            else:
                ti["edits"] = [{"old_string": "x", "new_string": body}]
            out.append(dict(base, tool_name=tool, tool_input=ti))
    return out


def main():
    for t in ("bash", "git", "jq"):
        if not shutil.which(t):
            print("cannot check: %s not on PATH" % t)
            return 2
    try:
        hooks = json.loads(HOOKS_JSON.read_text())["hooks"]
    except (OSError, ValueError, KeyError) as e:
        print("cannot check: hooks.json unreadable (%s)" % e)
        return 2
    if not CORE.is_file():
        fail("core contract %s is missing" % CORE.relative_to(ROOT))
        return 1

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(os.path.realpath(td))
        home, data, bindir = tmp / "home", tmp / "data", tmp / "bin"
        for d in (home, data, bindir):
            d.mkdir()
        # The repo sits outside every temp root, or the guards that skip temp
        # dirs (signing, host text, Edit/Write) would say nothing worth measuring.
        nt = pathlib.Path(tempfile.mkdtemp(prefix=".hookfix-", dir=str(ROOT)))
        repo = nt / "repo"
        repo.mkdir()
        (bindir / "rivet").write_text(STUB_RIVET)
        (bindir / "gh").write_text(STUB_GH)
        for f in ("rivet", "gh"):
            (bindir / f).chmod(0o755)
        gitcfg = home / ".gitconfig"
        gitcfg.write_text("[user]\n\tname = Size Check\n\temail = size@example.com\n")
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("GIT_", "GH_", "GITHUB_", "CLAUDE_", "PULSEENGINE_"))}
        env.update({"HOME": str(home), "CLAUDE_PLUGIN_ROOT": str(PLUGIN), "CLAUDE_PLUGIN_DATA": str(data),
                    "CLAUDE_ENV_FILE": str(tmp / "env"), "GIT_CONFIG_GLOBAL": str(gitcfg),
                    "GIT_CONFIG_NOSYSTEM": "1", "TMPDIR": str(tmp),
                    "PATH": str(bindir) + os.pathsep + env.get("PATH", ""),
                    "PULSEENGINE_GITHUB_API": "http://127.0.0.1:9",
                    "GIT_CEILING_DIRECTORIES": str(nt)})
        try:
            return run_all(hooks, repo, env, data)
        finally:
            shutil.rmtree(str(nt), ignore_errors=True)


def run_all(hooks, repo, env, data):
    subprocess.run(["git", "init", "-q"], cwd=repo, env=env, check=True)
    subprocess.run(["git", "commit", "-q", "--allow-empty", "--no-gpg-sign", "-m", "x"],
                   cwd=repo, env=env, check=True)
    (repo / "rivet.yaml").write_text("project: size-check\n")
    wc = repo / ".claude" / "pulseengine"
    wc.mkdir(parents=True)
    (wc / "working-context.md").write_text(("- a long working-context line, " * 4 + "\n") * 170)

    sizes = {}
    ran = 0
    for event, groups in hooks.items():
        for g in groups:
            for h in g.get("hooks", []):
                if h.get("type") != "command":
                    continue
                cmd = h["command"].replace("${CLAUDE_PLUGIN_ROOT}", str(PLUGIN))
                evs = events(repo, g.get("matcher"), event)
                if not evs:
                    fail("no fixture event for %s %r: %s" % (event, g.get("matcher"), h["command"]))
                    continue
                for e in evs:
                    r = subprocess.run(["bash", "-c", cmd], input=json.dumps(e), capture_output=True,
                                       text=True, cwd=str(repo), env=env, timeout=120)
                    ran += 1
                    if r.returncode != 0:
                        fail("%s exited %d" % (h["command"], r.returncode))
                    for field, s in strings(r.stdout):
                        key = "%s %s" % (event, h["command"].split("/hooks/")[-1])
                        sizes[key] = max(sizes.get(key, 0), len(s))
                        if len(s) > CAP:
                            fail("%s: %s is %d chars (> %d), Claude Code would deliver a preview"
                                 % (key, field, len(s), CAP))
                        if "inject-pulseengine-memory" in key:
                            if CUT in s:
                                fail("the core contract arrived cut: %d chars" % len(s))
                            core = CORE.read_text().strip()
                            if core not in s:
                                fail("the memory hook's output does not carry the core file whole")
    for k in sorted(sizes):
        print("     %-60s %6d chars" % (k, sizes[k]))
    if not any("inject-pulseengine-memory" in k for k in sizes):
        fail("the memory hook produced no context")
    print("ran %d hook invocation(s)" % ran)

    # factory-notice builds its text in python; check its clamp directly.
    spec = importlib.util.spec_from_file_location(
        "notice", str(PLUGIN / "skills" / "factory-notice" / "notice.py"))
    mod = importlib.util.module_from_spec(spec)
    old = dict(os.environ)
    try:
        os.environ["CLAUDE_PLUGIN_DATA"] = str(data)
        sys.dont_write_bytecode = True
        spec.loader.exec_module(mod)
        out = mod.clamp_context(("waiting answer line\n" * 1600), "size-check")
    finally:
        os.environ.clear()
        os.environ.update(old)
    if len(out) > CAP or "size-check.md" not in out:
        fail("factory-notice clamp_context: %d chars, spill named: %s" % (len(out), "size-check.md" in out))
    else:
        print("ok   factory-notice clamp: 32,000 chars -> %d, spill file named" % len(out))

    print("%d failure(s)" % len(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
