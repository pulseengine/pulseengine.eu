#!/usr/bin/env python3
# rivet: verifies REQ-CONFIDENTIAL-TERMS-GUARD
"""Check rule 8 of the commit-merge-guard hook: the private confidential-terms ask.

Runs the real wrapper, hooks/commit-merge-guard.sh, with a temp HOME holding a
fixture terms file at .config/pulseengine/confidential-terms.txt. The fixture
holds one harmless word (zebrafish-canary); no real term is, or may be, in this
repo. Cases:

  ask      a gh pr create/edit/comment, gh issue create/comment and gh release
           create whose --body, --title, heredoc body or --body-file carries the
           word (any letter case) asks, and the reason names the term file's
           LINE NUMBER and never the word, the matched text or the file path;
           a git push asks when the added lines or a commit message of the
           unpushed commits carry it, against an upstream and against
           origin/main when there is none;
  allow    the same commands with non-matching text are silent; a term only in
           a # comment line does not match; an invalid regex line is skipped;
           a git push with nothing unpushed, or a clean diff, is silent;
  missing  with no terms file the matching commands are silent, with no git or
           file reads needed;
  shape    every run exits 0 with empty stderr, and a decision is "ask", never
           "allow" or "deny";
  control  the leak check is shown to fire on a string that contains the word.

Exit: 0 all hold, 1 a check failed, 2 cannot check.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
WRAPPER = ROOT / "claude-tooling" / "plugins" / "pulseengine-claude" / "hooks" / "commit-merge-guard.sh"
WORD = "zebrafish-canary"
TERMS = "# fixture terms for the test, not real\n\nharmless-unrelated\n%s\n([unclosed\n# secondary-canary\n" % WORD
# line numbers in TERMS: 1 comment, 2 blank, 3 harmless, 4 WORD, 5 invalid regex, 6 comment
FAILS = []


def fail(msg):
    FAILS.append(msg)
    print("FAIL " + msg)


def leaks(*texts):
    return any(WORD in t.lower() or "terms.txt" in t for t in texts)


def main():
    tools = {t: shutil.which(t) for t in ("git", "bash", "cat", "dirname")}
    tools["python3"] = sys.executable
    if not all(tools.values()) or not WRAPPER.exists():
        print("cannot check: missing tools or hook")
        return 2
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        bins = tmp / "bin"
        bins.mkdir()
        for n, p in tools.items():
            (bins / n).symlink_to(p)
        gitcfg = tmp / "gitconfig"
        gitcfg.write_text("[user]\n\tname = T\n\temail = t@example.com\n[commit]\n\tgpgsign = false\n"
                          "[init]\n\tdefaultBranch = main\n")

        def env(home):
            e = {k: v for k, v in os.environ.items()
                 if not k.startswith(("GIT_", "GH_", "GITHUB_", "CLAUDE_", "PULSEENGINE_"))
                 and k not in ("HOME", "PATH", "XDG_CONFIG_HOME", "TMPDIR")}
            e.update({"HOME": str(home), "PATH": str(bins), "GIT_CONFIG_GLOBAL": str(gitcfg),
                      "GIT_CONFIG_NOSYSTEM": "1", "CLAUDE_PLUGIN_DATA": str(tmp / "data"),
                      "TMPDIR": str(tmp)})
            return e

        def git(cwd, *a):
            subprocess.run(["git"] + list(a), cwd=cwd, env=env(tmp / "home-with"), check=True,
                           capture_output=True)

        home_with = tmp / "home-with"
        (home_with / ".config" / "pulseengine").mkdir(parents=True)
        (home_with / ".config" / "pulseengine" / "confidential-terms.txt").write_text(TERMS)
        home_without = tmp / "home-without"
        home_without.mkdir()

        # a repo with an upstream, and one with only origin/main
        bare = tmp / "bare.git"
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], env=env(home_with), check=True)
        work = tmp / "work"
        subprocess.run(["git", "clone", "-q", str(bare), str(work)], env=env(home_with),
                       check=True, capture_output=True)
        (work / "a.txt").write_text("base\n")
        git(work, "add", "a.txt")
        git(work, "commit", "-q", "-m", "base")
        git(work, "push", "-q", "-u", "origin", "main")

        def push_case(name, content, msg, upstream=True):
            d = tmp / name
            subprocess.run(["git", "clone", "-q", str(bare), str(d)], env=env(home_with),
                           check=True, capture_output=True)
            if not upstream:
                git(d, "branch", "--unset-upstream")
                git(d, "checkout", "-q", "-b", "side")
            if content is not None:
                (d / "new.txt").write_text(content)
                git(d, "add", "new.txt")
                git(d, "commit", "-q", "-m", msg)
            return d

        def run(command, cwd, home):
            ev = {"session_id": "s", "hook_event_name": "PreToolUse", "tool_name": "Bash",
                  "tool_input": {"command": command}, "cwd": str(cwd), "tool_use_id": "t"}
            r = subprocess.run(["bash", str(WRAPPER)], input=json.dumps(ev), capture_output=True,
                               text=True, env=env(home), timeout=30)
            if r.returncode != 0 or r.stderr:
                fail("%s: exit %d stderr %r" % (command[:40], r.returncode, r.stderr[:80]))
            decision, reason = None, ""
            if r.stdout.strip():
                o = json.loads(r.stdout)["hookSpecificOutput"]
                decision, reason = o.get("permissionDecision"), o.get("permissionDecisionReason", "")
            return decision, reason, r.stdout

        def expect_ask(name, command, cwd=work, home=home_with):
            d, reason, out = run(command, cwd, home)
            if d != "ask":
                fail("%s: want ask, got %r" % (name, d))
            elif "line(s) 4" not in reason:
                fail("%s: reason does not name line 4: %r" % (name, reason[:120]))
            elif leaks(out) or "line(s) 4," in reason or "line(s) 1" in reason:
                fail("%s: reason leaks or names a comment/invalid line" % name)
            else:
                print("ok   ask: " + name)

        def expect_quiet(name, command, cwd=work, home=home_with):
            d, reason, out = run(command, cwd, home)
            if "line(s)" in reason or d == "deny" or (d == "ask" and "confidential" in reason):
                fail("%s: want no terms ask, got %r %r" % (name, d, reason[:100]))
            else:
                print("ok   quiet: " + name)

        bf = tmp / "body.md"
        bf.write_text("notes mention ZebraFish-Canary here\n")
        clean = tmp / "clean.md"
        clean.write_text("nothing to see\n")
        expect_ask("pr create --body", 'gh pr create --title t --body "mentions ZEBRAFISH-canary x"')
        expect_ask("pr create --title", 'gh pr create --title "the zebrafish-canary fix" --body ok')
        expect_ask("pr create heredoc",
                   "gh pr create --title t --body \"$(cat <<'EOF'\nline one\nzebrafish-canary two\nEOF\n)\"")
        expect_ask("pr create --body-file", "gh pr create --title t --body-file %s" % bf, cwd=tmp)
        expect_ask("pr edit", 'gh pr edit 3 --body "zebrafish-canary"')
        expect_ask("pr comment", 'gh pr comment 3 --body "zebrafish-canary"')
        expect_ask("issue create", 'gh issue create --title t --body "zebrafish-canary"')
        expect_ask("issue comment", 'gh issue comment 3 --body "zebrafish-canary"')
        expect_ask("release create", 'gh release create v9.9.9 --notes "zebrafish-canary"')
        expect_ask("pr create after cd, chained", 'cd /x && gh pr comment 3 -b "zebrafish-canary" && echo done')
        expect_quiet("pr create clean", 'gh pr create --title t --body "all fine"')
        expect_quiet("pr create clean --body-file", "gh pr create --title t --body-file %s" % clean, cwd=tmp)
        expect_quiet("only a comment line's word", 'gh pr comment 3 --body "secondary-canary"')
        expect_quiet("issue comment clean", 'gh issue comment 3 --body "fine"')
        expect_quiet("pr view", "gh pr view 3")
        for name, cmd in (("pr create", 'gh pr create --title t --body "zebrafish-canary"'),
                          ("issue comment", 'gh issue comment 3 --body "zebrafish-canary"'),
                          ("pr create --body-file", "gh pr create --body-file %s" % bf)):
            expect_quiet("missing file: " + name, cmd, cwd=tmp, home=home_without)

        d_ask = push_case("p_add", "has zebrafish-canary in it\n", "add file")
        expect_ask("git push, added line, upstream", "git push", cwd=d_ask)
        d_msg = push_case("p_msg", "plain\n", "mentions Zebrafish-Canary in the message")
        expect_ask("git push, commit message", "git push origin main", cwd=d_msg)
        d_noup = push_case("p_noup", "zebrafish-canary\n", "x", upstream=False)
        git(d_noup, "update-ref", "refs/remotes/origin/main", "origin/main")
        expect_ask("git push, no upstream (origin/main)", "git push origin side", cwd=d_noup)
        d_clean = push_case("p_clean", "plain text\n", "add plain")
        expect_quiet("git push, clean diff", "git push", cwd=d_clean)
        d_none = push_case("p_none", None, "")
        expect_quiet("git push, nothing unpushed", "git push", cwd=d_none)
        expect_quiet("git push --dry-run", "git push --dry-run", cwd=d_ask)
        expect_quiet("missing file: git push", "git push", cwd=d_ask, home=home_without)

        # the leak check can fail
        if not leaks("reason mentioning " + WORD):
            fail("control: the leak check did not fire on a string with the word")
        else:
            print("ok   control: the leak check fires on a leaking string")
    print("%d failure(s)" % len(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
