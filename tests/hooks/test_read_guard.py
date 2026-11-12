"""Tests for plugins/agent-hub/hooks/read_guard.py (runs under unittest and pytest)."""
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOKS = REPO / "plugins" / "agent-hub" / "hooks"
SCRIPT = HOOKS / "read_guard.py"
GIT_GUARD = HOOKS / "git_guard.py"
PLUGIN = REPO / "plugins" / "agent-hub"


def run(payload, args=(), env_extra=None, raw=None, script=SCRIPT):
    env = dict(os.environ)
    env.pop("CLAUDE_PLUGIN_OPTION_READ_GUARD", None)
    env.pop("CLAUDE_PLUGIN_OPTION_READ_GUARD_LINES", None)
    env.pop("CLAUDE_PLUGIN_OPTION_READ_GUARD_BYTES", None)
    env.update(env_extra or {})
    data = raw if raw is not None else json.dumps(payload)
    return subprocess.run([sys.executable, str(script), *args], input=data,
                          capture_output=True, text=True, env=env, timeout=30)


def read_payload(path, **extra):
    inp = {"file_path": str(path)}
    inp.update(extra)
    return {"tool_name": "Read", "tool_input": inp}


def bash_payload(cmd, cwd):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": str(cwd)}


def write_lines(path, count, width=10):
    Path(path).write_text("".join(("x" * width) + "\n" for _ in range(count)))


def reason_of(proc):
    out = json.loads(proc.stdout)
    spec = out["hookSpecificOutput"]
    assert spec["hookEventName"] == "PreToolUse"
    assert spec["permissionDecision"] == "deny"
    return spec["permissionDecisionReason"]


class GuardCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.big = self.tmp / "big.txt"
        write_lines(self.big, 1000)

    def assertSilent(self, proc):
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")


class TestDeny(GuardCase):
    def test_tc1_whole_file_over_lines(self):
        proc = run(read_payload(self.big))
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(len(proc.stdout.strip().splitlines()), 1)
        r = reason_of(proc)
        for word in ("offset", "limit", "200", "read_guard"):
            self.assertIn(word, r)

    def test_tc2_size_over_bytes(self):
        f = self.tmp / "wide.txt"
        write_lines(f, 100, 199)  # 100 lines, 20,000 bytes
        proc = run(read_payload(f))
        self.assertEqual(proc.returncode, 0)
        self.assertIn("16384", reason_of(proc))


class TestPass(GuardCase):
    def test_tc3_allowed_reads(self):
        exact = self.tmp / "exact.txt"
        write_lines(exact, 200)
        pdf = self.tmp / "x.pdf"
        write_lines(pdf, 5000)
        png = self.tmp / "x.png"
        write_lines(png, 5000)
        nb = self.tmp / "x.ipynb"
        write_lines(nb, 5000)
        payloads = [
            read_payload(self.big, offset=1, limit=200),
            read_payload(self.big, limit=50),
            read_payload(self.big, pages="1-3"),
            read_payload(exact), read_payload(pdf), read_payload(png), read_payload(nb),
            read_payload(self.tmp), read_payload(self.tmp / "missing.txt"),
        ]
        for p in payloads:
            self.assertSilent(run(p))

    def test_no_trailing_newline_counts(self):
        f = self.tmp / "nonl.txt"
        f.write_text("a\n" * 200 + "last")  # 201 lines
        self.assertIn("200", reason_of(run(read_payload(f))))

    def test_other_tool_passes(self):
        self.assertSilent(run({"tool_name": "Grep", "tool_input": {"file_path": str(self.big)}}))


class TestOptions(GuardCase):
    def test_tc4_switch_and_limits(self):
        self.assertSilent(run(read_payload(self.big), ["--switch", "off"]))
        self.assertSilent(run(read_payload(self.big), env_extra={"CLAUDE_PLUGIN_OPTION_READ_GUARD": "off"}))
        sixty = self.tmp / "sixty.txt"
        write_lines(sixty, 60)
        self.assertIn("50", reason_of(run(read_payload(sixty), ["--lines", "50"])))
        self.assertIn("50", reason_of(run(read_payload(sixty), env_extra={"CLAUDE_PLUGIN_OPTION_READ_GUARD_LINES": "50"})))
        hundred = self.tmp / "hundred.txt"
        write_lines(hundred, 50, width=10)
        self.assertSilent(run(read_payload(hundred), env_extra={"CLAUDE_PLUGIN_OPTION_READ_GUARD_BYTES": "1000"}))
        self.assertIn("100", reason_of(run(read_payload(hundred), env_extra={"CLAUDE_PLUGIN_OPTION_READ_GUARD_BYTES": "100"})))
        for args in (["--lines", "abc"], ["--lines", "0"], ["--bytes", "abc"],
                     ["--lines", "${user_config.read_guard_lines}"],
                     ["--bytes", "${user_config.read_guard_bytes}"],
                     ["--switch", "${user_config.read_guard}"]):
            proc = run(read_payload(self.big), args)
            self.assertEqual(proc.returncode, 0, args)
            reason_of(proc)
        # fallback to default 200 lines: a 150-line file still passes with a bad lines value
        small = self.tmp / "small.txt"
        write_lines(small, 150)
        self.assertSilent(run(read_payload(small), ["--lines", "abc"]))


class TestBroken(GuardCase):
    def test_tc5_broken_input_and_no_writes(self):
        for raw in ("", "not json", "[1, 2]", json.dumps(read_payload(self.big)).replace(str(self.big), "")):
            self.assertSilent(run(None, raw=raw))
        self.assertSilent(run({"tool_name": "Read", "tool_input": {"file_path": 42}}))
        self.assertSilent(run({"tool_name": "Read", "tool_input": "x"}))
        home = tempfile.TemporaryDirectory()
        self.addCleanup(home.cleanup)

        def snap():
            out = []
            for root in (self.tmp, Path(home.name)):
                for d, dirs, files in os.walk(root):
                    out.append((d, sorted(dirs), sorted((f, os.stat(os.path.join(d, f)).st_size) for f in files)))
            return out
        before = snap()
        proc = run(read_payload(self.big), env_extra={"HOME": home.name, "USERPROFILE": home.name})
        reason_of(proc)
        self.assertEqual(before, snap())

    def test_tc6_same_for_subagent(self):
        a = run(read_payload(self.big))
        payload = read_payload(self.big)
        payload.update(agent_id="a1", agent_type="agent-hub:implement")
        b = run(payload)
        self.assertEqual(a.stdout, b.stdout)
        reason_of(b)


class TestBashCat(GuardCase):
    def test_tc7_cat_forms(self):
        (self.tmp / "small.txt").write_text("hi\n")
        denied = [f"cat {self.big}", "cat big.txt", "cat ~/big.txt", "cat 'big.txt'"]
        for cmd in denied:
            proc = run(bash_payload(cmd, self.tmp), env_extra={"HOME": str(self.tmp), "USERPROFILE": str(self.tmp)})
            r = reason_of(proc)
            for word in ("Read", "offset", "limit"):
                self.assertIn(word, r, cmd)
        passes = ["cat small.txt", "cat big.txt | head", "cat -n big.txt", "cat big.txt small.txt",
                  "cat big.txt > out.txt", "cat $(echo big.txt)", "cat *.txt", "cat <<EOF\nhi\nEOF",
                  "cat <<'EOF'\nhi\nEOF", "ls -la", "cat", "cat missing.txt", "echo cat big.txt", "cat big.txt; ls"]
        for cmd in passes:
            self.assertSilent(run(bash_payload(cmd, self.tmp), env_extra={"HOME": str(self.tmp)}))
        self.assertFalse((self.tmp / "out.txt").exists())

    def test_cat_relative_without_cwd(self):
        proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=self.tmp, capture_output=True, text=True,
                              input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "cat big.txt"}}))
        reason_of(proc)


class TestLocal(unittest.TestCase):
    def test_tc8_latency(self):
        payload = {"tool_name": "Bash", "tool_input": {"command": "git status"}}

        def median(script):
            times = []
            for _ in range(20):
                t = time.perf_counter()
                run(payload, script=script)
                times.append((time.perf_counter() - t) * 1000)
            return statistics.median(times)
        rg, gg = median(SCRIPT), median(GIT_GUARD)
        print("median ms read_guard=%.1f git_guard=%.1f" % (rg, gg))
        self.assertLessEqual(rg, 1.5 * gg)

    def test_tc9_package_files(self):
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())
        pre = hooks["hooks"]["PreToolUse"]
        self.assertEqual(pre[0]["matcher"], "Bash")
        self.assertIn("git_guard.py", pre[0]["hooks"][0]["command"])
        self.assertEqual(pre[1]["matcher"], "Read|Bash")
        cmd = pre[1]["hooks"][0]["command"]
        self.assertEqual(cmd, 'python3 "${CLAUDE_PLUGIN_ROOT}/hooks/read_guard.py"')
        self.assertEqual(pre[1]["hooks"][0]["timeout"], 10)
        self.assertNotIn("statusMessage", pre[1]["hooks"][0])
        cfg = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())["userConfig"]
        self.assertEqual({k: cfg[k]["default"] for k in ("read_guard", "read_guard_lines", "read_guard_bytes")},
                         {"read_guard": "on", "read_guard_lines": "200", "read_guard_bytes": "16384"})
        self.assertEqual(cfg["read_guard"]["title"], "Read guard")
        self.assertEqual(cfg["read_guard_lines"]["title"], "Read guard line limit")
        self.assertEqual(cfg["read_guard_bytes"]["title"], "Read guard size limit")
        self.assertLessEqual(len((PLUGIN / "rules" / "core.md").read_text().splitlines()), 200)


if __name__ == "__main__":
    unittest.main()
