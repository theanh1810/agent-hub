"""Tests for the auditor plugin's error_stats.py and run_auditor.py: fixture counts, an empty tree, an unreadable
yaml line, the PyYAML-absent fallback, and the --dry-run command. The shell parity check runs only where the
legacy error-stats.sh and zsh exist."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "agent-hub-auditor"
STATS = PLUGIN / "scripts" / "error_stats.py"
RUN = PLUGIN / "scripts" / "run_auditor.py"
BIN = PLUGIN / "bin" / "agent-hub-audit"
LEGACY = Path.home() / ".claude" / "scripts" / "error-stats.sh"


def py(script, *args, env=None, pre=""):
    e = dict(os.environ, NO_COLOR="1")
    e.update(env or {})
    code = pre + f"import sys,runpy;sys.argv={[str(script)] + list(args)!r};runpy.run_path({str(script)!r},run_name='__main__')"
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=e)


class Tree:
    def __init__(self, case):
        self.root = tempfile.mkdtemp(prefix="auditor-test-")
        case.addCleanup(shutil.rmtree, self.root, True)

    def write(self, rel, text):
        p = Path(self.root, rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def fixture(case):
    t = Tree(case)
    t.write("a/docs/changes/x1/errors.yaml",
            "errors:\n  - id: 1\n    pattern: p1\n    severity: high\n  - id: 2\n    source: s\n    task_id: t\n")
    t.write("a/docs/plan/y/errors.yaml", "errors:\n  - pattern: p1\n  - pattern: p2\n  - pattern: p1\n")
    t.write("b/docs/plan/z/errors.yaml", "bugs:\n  - pattern: p1\n    actual: x\n")
    t.write("b/node_modules/q/docs/changes/n/errors.yaml", "errors:\n  - pattern: skipped\n")
    return t


class StatsTests(unittest.TestCase):
    def test_fixture_counts(self):
        t = fixture(self)
        r = py(STATS, t.root, "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual((d["files_count"], d["projects_count"], d["total_errors"]), (3, 2, 6))
        self.assertEqual(d["top_patterns"][0], {"pattern": "p1", "count": 4})
        self.assertEqual([p["project"] for p in d["per_project"]], ["a", "b"])
        self.assertEqual(d["recurring_offenders"][0]["project"], "a")

    @unittest.skipUnless(LEGACY.is_file() and shutil.which("zsh"), "legacy shell version absent")
    def test_text_and_json_match_shell(self):
        t = fixture(self)
        for args in ([], ["--json"], ["--top", "1", "--recurring-threshold", "2"]):
            sh = subprocess.run(["zsh", str(LEGACY), t.root, *args], capture_output=True, text=True,
                                env=dict(os.environ, NO_COLOR="1")).stdout
            out = py(STATS, t.root, *args).stdout
            strip = lambda s: "\n".join(l for l in s.splitlines() if "scanned_at" not in l and "yaml_loader" not in l)
            self.assertEqual(strip(out), strip(sh))

    def test_empty_tree(self):
        t = Tree(self)
        r = py(STATS, t.root)
        self.assertEqual(r.returncode, 0)
        self.assertIn("No errors logged", r.stdout)
        self.assertEqual(json.loads(py(STATS, t.root, "--json").stdout)["total_errors"], 0)

    def test_unreadable_yaml_line_skipped(self):
        t = fixture(self)
        t.write("c/docs/changes/bad/errors.yaml", "errors:\n  - pattern: [unclosed\n  - pattern: p9\n")
        d = json.loads(py(STATS, t.root, "--json").stdout)
        self.assertEqual(d["files_count"], 4)
        self.assertTrue(any("c/docs/changes/bad" in w.replace(os.sep, "/") for w in d["parse_warnings"]))

    def test_fallback_when_pyyaml_absent(self):
        t = fixture(self)
        r = py(STATS, t.root, "--json", pre="import sys;sys.modules['yaml']=None;")
        d = json.loads(r.stdout)
        self.assertEqual(d["yaml_loader"], "fallback")
        self.assertEqual(d["total_errors"], 6)
        strict = py(STATS, t.root, "--strict", pre="import sys;sys.modules['yaml']=None;")
        self.assertEqual(strict.returncode, 2)

    def test_arg_errors(self):
        t = Tree(self)
        self.assertEqual(py(STATS, t.root, "--top").returncode, 3)
        self.assertEqual(py(STATS, t.root, "--top", "0").returncode, 3)
        self.assertEqual(py(STATS, t.root, "--nope").returncode, 3)
        self.assertEqual(py(STATS, os.path.join(t.root, "missing")).returncode, 1)


class RunTests(unittest.TestCase):
    def test_dry_run_prints_command(self):
        t = Tree(self)
        t.write("proj/docs/x.md", "x")
        t.write("empty/readme.txt", "x")
        cfg = Tree(self)
        r = py(RUN, "--dry-run", env={"CODE_ROOT": t.root, "CLAUDE_CONFIG_DIR": cfg.root, "CLAUDE_BIN": "claude-x"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("would run: claude-x --model sonnet --print --add-dir", r.stdout)
        self.assertIn("Skipped: empty", r.stdout)
        self.assertFalse(Path(cfg.root, "logs").exists())

    def test_least_privilege_command_and_cwd(self):
        import importlib.util
        from unittest import mock
        spec = importlib.util.spec_from_file_location("run_auditor", RUN)
        ra = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ra)
        t = Tree(self)
        t.write("proj/docs/x.md", "x")
        proj = Path(t.root) / "proj"
        cmd = ra.command("claude", proj, Path("/tmp/logs"))
        self.assertNotIn("acceptEdits", cmd)
        tools = cmd[cmd.index("--allowedTools") + 1].split(",")
        for bare in ("Bash", "Write", "Edit"):
            self.assertNotIn(bare, tools)
        self.assertIn("Bash(git log:*)", tools)
        self.assertIn("Edit(docs/audits/**)", tools)
        cfg = Tree(self)
        env = {"CODE_ROOT": t.root, "CLAUDE_CONFIG_DIR": cfg.root, "CLAUDE_BIN": "claude"}
        done = subprocess.CompletedProcess([], 0, "", "")
        with mock.patch.dict(os.environ, env), mock.patch.object(ra.subprocess, "run", return_value=done) as run:
            self.assertEqual(ra.main([]), 0)
        self.assertEqual(run.call_args.kwargs.get("cwd"), str(proj))

    def test_dispatcher(self):
        t = Tree(self)
        r = subprocess.run([sys.executable, str(BIN), "stats", t.root], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("No errors logged", r.stdout)
        self.assertEqual(subprocess.run([sys.executable, str(BIN), "nope"], capture_output=True, text=True).returncode, 3)


if __name__ == "__main__":
    unittest.main()
