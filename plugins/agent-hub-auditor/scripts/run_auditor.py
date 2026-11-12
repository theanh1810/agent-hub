#!/usr/bin/env python3
"""run_auditor.py: daily auditor. Scans CODE_ROOT/*, one workspace root per subdir, one report per workspace.

Port of run-auditor.sh. Log: <config_dir>/logs/auditor/<date>.log. Exit 0 always (a scheduler never retries),
except a bad flag (3). --dry-run prints the claude command per workspace and runs nothing.
Env: CLAUDE_BIN (default claude), CODE_ROOT (default ~/Code), CLAUDE_CONFIG_DIR.
"""
import datetime
import glob
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

MANIFESTS = ("package.json", "go.mod", "pyproject.toml", "Cargo.toml")


def config_dir():
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(env).expanduser() if env else Path.home() / ".claude"


def is_workspace(proj):
    """Recognition only: a .git, docs/, a package manifest, or a sub-repo .git."""
    if (proj / ".git").is_dir() or (proj / "docs").is_dir() or any((proj / m).is_file() for m in MANIFESTS):
        return True
    return bool(glob.glob(str(proj / "*" / ".git")))


def build_prompt(proj, ts, log_dir, proj_name):
    return (f"You are the auditor agent. Effective cwd: {proj}. Window: the last 24 hours. "
            "Read docs/changes/ (archive included) and the legacy roots docs/plan/ and docs/specs/changes/ "
            "(archive included, the latter when docs/specs/README.md exists), docs/audits/, errors.yaml, "
            "mem0 (when the MCP is available; for every user correction found, search then add or update its "
            "lesson counter, never delete), and git log --since='24 hours ago'. Write the report using the "
            f"skeleton in the auditor agent file to docs/audits/{ts}.md when that directory exists, otherwise "
            f"{log_dir}/{proj_name}-{ts}.md. The report body is in the reply language. Read-only outside the "
            "audit file and the mem0 lesson counter. Close with a three-sentence summary.")


def allowed_tools(log_dir):
    """Read-only plus git log, writes only to the audit dirs and the auditor's memory; `//` marks an absolute path."""
    def absolute(path):
        return "Edit(//%s/**)" % str(path).lstrip("/")
    return ",".join(["Read", "Grep", "Glob", "Bash(git log:*)", "Edit(docs/audits/**)", absolute(log_dir),
                     absolute(config_dir() / "agent-memory" / "auditor"), "mcp__mcp_mem0__search_memories",
                     "mcp__mcp_mem0__add_memory", "mcp__mcp_mem0__update_memory"])


def command(claude_bin, proj, log_dir):
    return [claude_bin, "--model", "sonnet", "--print", "--add-dir", str(proj),
            "--allowedTools", allowed_tools(log_dir)]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    dry = False
    for a in argv:
        if a == "--dry-run":
            dry = True
        elif a in ("--help", "-h"):
            print(__doc__)
            return 0
        else:
            sys.stderr.write(f"Unknown argument: {a}\n")
            return 3
    claude_bin = os.environ.get("CLAUDE_BIN", "claude")
    code_root = Path(os.environ.get("CODE_ROOT") or Path.home() / "Code").expanduser()
    log_dir = config_dir() / "logs" / "auditor"
    now = datetime.datetime.now().astimezone()
    ts, ts_full = now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%dT%H:%M:%S%z")
    log_file = log_dir / f"{ts}.log"
    lines_out = []

    def emit(text=""):
        lines_out.append(text)
        print(text, flush=True)
        if not dry:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(text + "\n")

    if not dry:
        log_dir.mkdir(parents=True, exist_ok=True)
    emit(f"=== Auditor run {ts_full} ===")
    emit(f"Code root: {code_root}")
    emit()
    if not code_root.is_dir():
        emit("Code root not found, skip.")
        return 0
    for proj in sorted(p for p in code_root.iterdir() if p.is_dir()):
        if not is_workspace(proj):
            emit(f"--- Skipped: {proj.name} (no .git, no docs/, no sub-repo .git, no package manifest) ---")
            continue
        emit(f"--- Auditing: {proj.name} ---")
        cmd = command(claude_bin, proj, log_dir)
        if dry:
            emit("would run: " + " ".join(shlex.quote(c) for c in cmd) + "  (prompt on stdin)")
            continue
        prompt = build_prompt(proj, ts, log_dir, proj.name)
        try:
            res = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                 cwd=str(proj))
            for chunk in (res.stdout, res.stderr):
                if chunk:
                    emit(chunk.rstrip("\n"))
        except OSError as e:
            emit(f"error: could not run {claude_bin}: {e}")
        emit()
    emit(f"=== Done {ts_full} ===")
    if not dry:
        cutoff = time.time() - 30 * 86400
        for f in log_dir.glob("*.log"):
            try:
                if f.is_file() and f.stat().st_mtime < cutoff:
                    f.unlink()
            except OSError:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
