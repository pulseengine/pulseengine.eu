#!/usr/bin/env python3
# rivet: verifies REQ-HOOK-ZSH-SHELL-OPTIONS
"""Check the SessionStart hook that writes zsh options into $CLAUDE_ENV_FILE.

Claude Code runs the contents of $CLAUDE_ENV_FILE before every Bash command, in
the same shell. hooks/persist-shell-options.sh appends one guarded line,
`if [ -n "$ZSH_VERSION" ]; then setopt no_nomatch no_equals; fi`, so that zsh's NOMATCH and
EQUALS defaults stop failing agent commands.

This runs the real hook against a temp file and then the real shells:

  control   in `zsh -f` WITHOUT the file, `echo ===` and an unmatched
            `--include=*.nomatchext` both FAIL — otherwise this zsh never had
            the problem and every check below would pass vacuously;
  fixed     in `zsh -f` after sourcing the file, both SUCCEED and print the
            words literally;
  once      three SessionStart runs (startup, resume, compact) leave exactly
            one copy of the line;
  append    a line another hook wrote, without a trailing newline, survives
            byte for byte and stays a working export;
  bash      `bash --norc` sourcing the file is a no-op: nothing printed, the
            file's own status is 0 (so `. file && cmd` still runs cmd, also
            under `set -e`), and bash's own globbing unchanged;
  no file   with CLAUDE_ENV_FILE unset the hook exits 0 and writes nothing.

zsh is required. Without it this exits 2, never 0: a skipped check is a green
that examined nothing.

Exit: 0 all hold · 1 a check failed · 2 cannot check (no zsh, no bash, no hook).
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOK = ROOT / "claude-tooling" / "plugins" / "pulseengine-claude" / "hooks" / "persist-shell-options.sh"
LINE = 'if [ -n "$ZSH_VERSION" ]; then setopt no_nomatch no_equals; fi'

# Each probe runs in its own shell from an empty directory, so one aborted
# command line cannot hide another and no real file can satisfy the glob.
PROBES = {
    "equals": ("echo ===", "==="),
    "nomatch": ("echo x --include=*.nomatchext", "x --include=*.nomatchext"),
}

failures: list[str] = []


def check(ok: bool, what: str) -> None:
    print(("ok    " if ok else "FAIL  ") + what)
    if not ok:
        failures.append(what)


def run_hook(env_file: str | None, source: str, cwd: str) -> subprocess.CompletedProcess:
    # cwd is a temp dir, so a hook that writes somewhere relative when the
    # variable is unset is seen by the "no file" check, not left in the repo.
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_ENV_FILE"}
    if env_file is not None:
        env["CLAUDE_ENV_FILE"] = env_file
    return subprocess.run(["bash", str(HOOK)], env=env, cwd=cwd, capture_output=True, text=True,
                          input='{"hook_event_name":"SessionStart","source":"%s"}' % source)


def shell(argv: list[str], script: str, cwd: str) -> subprocess.CompletedProcess:
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": cwd}
    return subprocess.run(argv + ["-c", script], cwd=cwd, env=env,
                          capture_output=True, text=True)


def main() -> int:
    zsh, bash = shutil.which("zsh"), shutil.which("bash")
    if not zsh or not bash:
        print(f"error: need zsh and bash on PATH (zsh={zsh}, bash={bash})", file=sys.stderr)
        return 2
    if not HOOK.is_file():
        print(f"error: hook not found: {HOOK.relative_to(ROOT)}", file=sys.stderr)
        return 2
    ver = subprocess.run([zsh, "--version"], capture_output=True, text=True).stdout.strip()
    print(f"using {ver} ({zsh}) and {bash}")

    with tempfile.TemporaryDirectory() as tmp:
        empty = os.path.join(tmp, "cwd")
        os.mkdir(empty)
        hookcwd = os.path.join(tmp, "hookcwd")
        os.mkdir(hookcwd)
        envf = os.path.join(tmp, "claude-env.sh")

        # control: plain zsh has the failure this hook exists to remove
        for name, (cmd, _) in PROBES.items():
            r = shell([zsh, "-f"], cmd, empty)
            check(r.returncode != 0, f"control: plain zsh fails `{cmd}` (rc={r.returncode})")

        # once: startup, resume, compact
        for src in ("startup", "resume", "compact"):
            r = run_hook(envf, src, hookcwd)
            check(r.returncode == 0 and r.stdout == "", f"hook exits 0 silently on {src} (rc={r.returncode})")
        text = pathlib.Path(envf).read_text() if os.path.exists(envf) else ""
        n = text.splitlines().count(LINE)
        check(n == 1, f"once: line present exactly once after 3 runs (found {n})")

        # fixed: source the file, then the probe
        for name, (cmd, want) in PROBES.items():
            r = shell([zsh, "-f"], f'. "{envf}"\n{cmd}', empty)
            check(r.returncode == 0 and r.stdout.strip() == want,
                  f"fixed: zsh after sourcing runs `{cmd}` (rc={r.returncode}, out={r.stdout.strip()!r})")

        # bash: sourcing is a no-op
        r = shell([bash, "--norc", "--noprofile"], f'set -e; . "{envf}" && echo ok; echo x --include=*.nomatchext', empty)
        check(r.returncode == 0 and r.stdout == "ok\nx --include=*.nomatchext\n" and r.stderr == "",
              f"bash: sourcing is a no-op (rc={r.returncode}, out={r.stdout!r}, err={r.stderr!r})")

        # append: another hook's unterminated line survives
        other = os.path.join(tmp, "other-env.sh")
        prior = "export PE_PRIOR_HOOK=kept"
        pathlib.Path(other).write_text(prior)  # no trailing newline
        run_hook(other, "startup", hookcwd)
        run_hook(other, "compact", hookcwd)
        got = pathlib.Path(other).read_text()
        check(got == prior + "\n" + LINE + "\n",
              f"append: prior unterminated line kept, ours on its own line once (got {got!r})")
        r = shell([zsh, "-f"], f'. "{other}"\necho "$PE_PRIOR_HOOK" ===', empty)
        check(r.returncode == 0 and r.stdout.strip() == "kept ===",
              f"append: prior export still works alongside ours (rc={r.returncode}, out={r.stdout.strip()!r})")

        # no file: unset CLAUDE_ENV_FILE
        before = set(os.listdir(tmp))
        r = run_hook(None, "startup", hookcwd)
        check(r.returncode == 0 and set(os.listdir(tmp)) == before and not os.listdir(hookcwd),
              f"no file: hook exits 0 and writes nothing without CLAUDE_ENV_FILE (rc={r.returncode})")

    if failures:
        print(f"\n{len(failures)} check(s) failed", file=sys.stderr)
        return 1
    print("\nall checks hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
