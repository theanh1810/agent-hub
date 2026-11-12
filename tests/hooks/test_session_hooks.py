"""Unit tests for hooks/post_compact_pointer.py and hooks/clear_handoff.py (runs under unittest and pytest)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
HOOKS = REPO / "plugins" / "agent-hub" / "hooks"
sys.path.insert(0, str(HOOKS))
import clear_handoff as ch  # noqa: E402


def run(script, args, payload):
    return subprocess.run([sys.executable, str(HOOKS / script)] + args, input=json.dumps(payload),
                          capture_output=True, text=True)


def assistant(text):
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})


class TmpCase(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = Path(self._t.name)
        self.addCleanup(self._t.cleanup)

    def transcript(self, lines):
        p = self.d / "t.jsonl"
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return p


class PostCompact(TmpCase):
    def test_fixture_parity(self):
        plan = self.d / "docs" / "changes" / "x" / "plan.yaml"
        plan.parent.mkdir(parents=True)
        plan.write_text("a: 1\n")
        other = self.d / "src.py"
        other.write_text("x\n")
        tool = lambda n, p: json.dumps({"timestamp": "2026-01-01T00:00:00Z", "message": {"content": [
            {"type": "tool_use", "name": n, "input": {"file_path": str(p)}}]}})
        t = self.transcript([tool("Read", plan), tool("Read", other)])
        out = run("post_compact_pointer.py", [], {"source": "compact", "transcript_path": str(t), "cwd": str(self.d)})
        self.assertEqual(out.returncode, 0)
        self.assertEqual(out.stdout, "%s\n%s\n" % (
            "POST-COMPACT: the summary above is lossy. Re-read these files this session worked on before continuing:", plan))
        self.assertEqual(run("post_compact_pointer.py", [], {"source": "startup", "transcript_path": str(t)}).stdout, "")

    def test_unreadable_transcript(self):
        out = run("post_compact_pointer.py", [], {"source": "compact", "transcript_path": str(self.d / "nope")})
        self.assertEqual((out.returncode, out.stdout), (0, ""))

    def _entry(self, kind, content, ts, **extra):
        return json.dumps(dict({"type": kind, "timestamp": ts, "message": {"content": content}}, **extra), ensure_ascii=False)

    def _tool(self, name, path, ts, **inp):
        return self._entry("assistant", [{"type": "tool_use", "name": name, "input": dict({"file_path": str(path)}, **inp)}], ts)

    def _hook(self, t, **extra):
        return run("post_compact_pointer.py", [], dict({"source": "compact", "transcript_path": str(t), "cwd": str(self.d), "session_id": "s1"}, **extra))

    def test_edited_files_and_request(self):
        (self.d / "src").mkdir()
        a, b, c = (self.d / "src" / n for n in ("a.py", "b.py", "c.py"))
        for f in (a, b, c):
            f.write_text("x\n")
        t = self.transcript([self._entry("user", "fix the bug\nsecond line", "2026-01-01T00:00:01Z"),
                             self._tool("Edit", a, "2026-01-01T00:00:02Z"), self._tool("Write", b, "2026-01-01T00:00:04Z")])
        sub = self.d / "s1" / "subagents"
        sub.mkdir(parents=True)
        (sub / "agent-1.jsonl").write_text(self._tool("Edit", c, "2026-01-01T00:00:03Z") + "\n")
        out = self._hook(t)
        self.assertEqual(out.returncode, 0)
        self.assertEqual(out.stdout, "Files edited this session, newest first:\n%s\n%s\n%s\nLast request (first line): fix the bug\n" % (b, c, a))

    def test_noise_is_not_a_request(self):
        ts = "2026-01-01T00:00:0%dZ"
        t = self.transcript([
            self._entry("user", "real prompt", ts % 1),
            self._entry("user", [{"type": "tool_result", "content": "tool says"}], ts % 2),
            self._entry("user", "meta text", ts % 3, isMeta=True),
            self._entry("user", "<command-name>/x</command-name>", ts % 4),
            self._entry("user", "<system-reminder>hi</system-reminder>", ts % 5),
            self._entry("user", "This session is being continued", ts % 6, isCompactSummary=True)])
        self.assertEqual(self._hook(t).stdout, "Last request (first line): real prompt\n")

    def test_budget_holds(self):
        docs = []
        for i in range(3):
            f = self.d / "docs" / "changes" / ("x%d" % i) / "plan.yaml"
            f.parent.mkdir(parents=True)
            f.write_text("a: 1\n")
            docs.append(f)
        lines = [self._entry("user", "Cần sửa lỗi " * 420, "2026-01-01T00:00:01Z")]  # scrub-allow: fixture
        for i in range(40):
            f = self.d / "deep" / ("d" * 100) / ("f%02d.py" % i)
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("x\n")
            lines.append(self._tool("Edit", f, "2026-01-01T00:01:%02dZ" % i))
        for f in docs:
            lines.append(self._tool("Read", f, "2026-01-01T00:02:00Z"))
        out = self._hook(self.transcript(lines)).stdout
        self.assertLessEqual(len(out.encode("utf-8")), 2048)
        for f in docs:
            self.assertIn(str(f), out)
        req = [ln for ln in out.splitlines() if ln.startswith("Last request (first line): ")][0]
        self.assertLessEqual(len(req) - len("Last request (first line): "), 201)

    def test_no_disk_write_no_leak(self):
        home, cwd = self.d / "home", self.d / "cwd"
        home.mkdir()
        cwd.mkdir()
        f = cwd / "w.py"
        f.write_text("x\n")
        t = self.d / "t.jsonl"
        t.write_text("\n".join([
            self._entry("user", [{"type": "tool_result", "content": "SECRET-TOKEN-X"}], "2026-01-01T00:00:01Z"),
            self._tool("Write", f, "2026-01-01T00:00:02Z", content="BODY-Y")]) + "\n")
        snap = lambda: sorted((str(q.relative_to(self.d)), q.stat().st_size, q.stat().st_mtime_ns) for q in self.d.rglob("*"))
        before = snap()
        out = subprocess.run([sys.executable, str(HOOKS / "post_compact_pointer.py")], cwd=str(cwd), capture_output=True, text=True,
                             env=dict(os.environ, HOME=str(home), TMPDIR=str(home)),
                             input=json.dumps({"source": "compact", "transcript_path": str(t), "cwd": str(cwd)}))
        self.assertEqual(snap(), before)
        self.assertIn(str(f), out.stdout)
        self.assertNotIn("SECRET-TOKEN-X", out.stdout)
        self.assertNotIn("BODY-Y", out.stdout)

    def test_nothing_to_say(self):
        t = self.transcript([self._entry("user", "hi", "2026-01-01T00:00:01Z")])
        self.assertEqual((run("post_compact_pointer.py", [], {"source": "startup", "transcript_path": str(t)}).stdout), "")
        out = self._hook(self.transcript([""]))
        self.assertEqual((out.returncode, out.stdout), (0, ""))

    def test_revision_prefixed_docs_path_is_kept(self):
        p, q = (self.d / "docs" / "changes" / n / "plan.yaml" for n in ("p", "q"))
        for f in (p, q):
            f.parent.mkdir(parents=True)
            f.write_text("a: 1\n")
        bash = lambda cmd, ts: self._entry("assistant", [{"type": "tool_use", "name": "Bash", "input": {"command": cmd}}], ts)
        t = self.transcript([bash("git show HEAD:docs/changes/p/plan.yaml", "2026-01-01T00:00:01Z"),
                             bash("git show 0123abcd:docs/changes/q/plan.yaml", "2026-01-01T00:00:02Z")])
        out = self._hook(t)
        self.assertEqual(out.returncode, 0)
        self.assertEqual(out.stdout, "%s\n%s\n%s\n" % (
            "POST-COMPACT: the summary above is lossy. Re-read these files this session worked on before continuing:", q, p))


class ClearHandoff(TmpCase):
    END = {"reason": "clear", "session_id": "s1"}

    def end(self, t):
        return run("clear_handoff.py", ["end"], dict(self.END, transcript_path=str(t)))

    def test_first_section_any_language(self):
        t = self.transcript([assistant("## Resumen\nHecho el cambio.\n\n## Riesgo\nninguno")])
        out = self.end(t)
        self.assertEqual(out.returncode, 0)
        saved = (self.d / "last-task.md").read_text(encoding="utf-8")
        self.assertTrue(saved.startswith("source_session: s1\n"))
        self.assertIn("Hecho el cambio.", saved)
        self.assertNotIn("ninguno", saved)
        self.assertEqual(list(self.d.glob(".last-task.*")), [])

    def test_no_section_writes_nothing(self):
        t = self.transcript([assistant("plain reply, no headings")])
        self.assertEqual(self.end(t).returncode, 0)
        self.assertFalse((self.d / "last-task.md").exists())

    def test_unreadable_transcript(self):
        out = self.end(self.d / "missing.jsonl")
        self.assertEqual((out.returncode, out.stdout), (0, ""))
        self.assertEqual(list(self.d.iterdir()), [])

    def test_interrupted_write_leaves_no_partial(self):
        t = self.transcript([assistant("## S\nbody")])
        with mock.patch.object(ch.os, "replace", side_effect=OSError("boom")):
            with self.assertRaises(OSError):
                ch.do_end(dict(self.END, transcript_path=str(t)), str(self.d), str(self.d / "last-task.md"))
        self.assertFalse((self.d / "last-task.md").exists())
        self.assertEqual(list(self.d.glob(".last-task.*")), [])

    def test_start_emits_then_nothing(self):
        t = self.transcript([assistant("## Tóm tắt\nxong")])  # scrub-allow: fixture
        self.end(t)
        payload = {"source": "clear", "session_id": "s2", "transcript_path": str(t)}
        out = run("clear_handoff.py", ["start"], payload)
        self.assertEqual(out.returncode, 0)
        self.assertIn("xong", out.stdout)
        self.assertFalse((self.d / "last-task.md").exists())
        with mock.patch.object(ch, "WAIT_SECONDS", 0):
            out2 = run("clear_handoff.py", ["start"], payload)
        self.assertEqual((out2.returncode, out2.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
