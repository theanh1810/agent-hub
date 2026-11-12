"""Unit and security tests for plugins/agent-hub/hooks/git_guard.py (runs under unittest and pytest)."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins" / "agent-hub" / "hooks" / "git_guard.py"

GUARDED = {
    "git push --force origin main": "force push",
    "git push --force-with-lease origin main": "force push",
    "git push -f origin main": "force push",
    "git push origin +main": "force push",
    "git reset --hard HEAD~1": "reset --hard",
    "git clean -fd": "clean -f",
    "git clean --force": "clean -f",
    "git branch -D feature": "branch -D",
    "git branch --delete --force feature": "branch -D",
    "git checkout .": "checkout .",
    "git restore .": "restore .",
    "git restore --staged --worktree .": "restore .",
}

WRAPPED = [
    "sudo git reset --hard",
    "env FOO=1 git push -f",
    "FOO=1 git clean -f",
    "command git checkout .",
    "exec git reset --hard",
    "time git push --force",
    "nohup git branch -D x",
    "xargs git clean -f",
    "echo ok && git reset --hard",
    "echo ok; git push -f",
    "true | git checkout .",
    "echo $(git reset --hard)",
    "echo `git clean -f`",
    "bash -c 'git reset --hard'",
    "sh -c \"git push -f\"",
    "zsh -lc 'git checkout .'",
    "dash -c 'git clean -f'",
    "eval git reset --hard",
    "eval 'git push --force'",
    "bash -c 'echo $(git reset --hard)'",
    "echo $(echo $(echo $(git reset --hard)))",
    "git -C /tmp/repo reset --hard",
]

SAFE = [
    "git push origin main",
    "git push --set-upstream origin feat",
    "git reset --soft HEAD~1",
    "git reset HEAD file",
    "git restore --staged x",
    "git restore --staged .",
    "git restore file.txt",
    "git branch -d merged",
    "git branch feature",
    "git clean -n",
    "git checkout main",
    "git status",
    "ls -la",
]

QUOTED = [
    'git commit -m "do not run git reset --hard"',
    "echo 'git push --force'",
    "git commit -m 'avoid git clean -f'",
    "echo hi # git reset --hard",
    "cat <<EOF\ngit reset --hard\ngit push -f\nEOF",
    "cat <<'EOF' > notes.txt\ngit checkout .\nEOF\necho done",
    "git commit -F - <<EOF\nrun git clean -f later\nEOF",
]


def run(stdin):
    return subprocess.run([sys.executable, str(SCRIPT)], input=stdin, capture_output=True, text=True)


def bash(cmd):
    return run(json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}))


def decision(proc):
    return json.loads(proc.stdout)["hookSpecificOutput"]


class GuardedForms(unittest.TestCase):
    def test_each_guarded_form_asks(self):
        for cmd, key in GUARDED.items():
            with self.subTest(cmd=cmd):
                p = bash(cmd)
                self.assertEqual(p.returncode, 0)
                out = decision(p)
                self.assertEqual(out["hookEventName"], "PreToolUse")
                self.assertEqual(out["permissionDecision"], "ask")
                reason = out["permissionDecisionReason"]
                self.assertTrue(reason.startswith("agent-hub git guard: "), reason)
                self.assertTrue(reason.endswith(". Approve only if you meant to do this."), reason)
                self.assertIn(key, reason)

    def test_reason_texts_kept(self):
        self.assertIn("force push rewrites shared history", decision(bash("git push -f"))["permissionDecisionReason"])
        self.assertIn("reset --hard discards uncommitted work", decision(bash("git reset --hard"))["permissionDecisionReason"])
        self.assertIn("clean -f deletes untracked files for good", decision(bash("git clean -f"))["permissionDecisionReason"])
        self.assertIn("branch -D deletes a branch even when unmerged", decision(bash("git branch -D x"))["permissionDecisionReason"])
        self.assertIn("checkout . discards all working-tree changes", decision(bash("git checkout ."))["permissionDecisionReason"])
        self.assertIn("restore . discards all working-tree changes", decision(bash("git restore ."))["permissionDecisionReason"])


class WrappedAndNested(unittest.TestCase):
    def test_wrapped_and_nested_forms_ask(self):
        for cmd in WRAPPED:
            with self.subTest(cmd=cmd):
                p = bash(cmd)
                self.assertEqual(p.returncode, 0)
                self.assertEqual(decision(p)["permissionDecision"], "ask")


class SafeAndQuoted(unittest.TestCase):
    def test_safe_lookalikes_pass(self):
        for cmd in SAFE:
            with self.subTest(cmd=cmd):
                p = bash(cmd)
                self.assertEqual((p.returncode, p.stdout), (0, ""))

    def test_quoted_and_heredoc_mentions_pass(self):
        for cmd in QUOTED:
            with self.subTest(cmd=cmd):
                p = bash(cmd)
                self.assertEqual((p.returncode, p.stdout), (0, ""))


class Malformed(unittest.TestCase):
    def test_malformed_input_exits_zero_silently(self):
        for stdin in ["not json", "{", "", "[]", "null", json.dumps({"tool_input": None}),
                      json.dumps({"tool_input": {"command": 5}}), json.dumps({})]:
            with self.subTest(stdin=stdin):
                p = run(stdin)
                self.assertEqual((p.returncode, p.stdout), (0, ""))


class NonUtf8Locale(unittest.TestCase):
    def test_utf8_stdin_under_cp1252_still_asks(self):
        cmd = 'git commit -m "\u0110\u1ed5i" && git push --force'
        stdin = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}, ensure_ascii=False).encode("utf-8")
        env = dict(os.environ, PYTHONUTF8="0", PYTHONIOENCODING="cp1252")
        p = subprocess.run([sys.executable, str(SCRIPT)], input=stdin, capture_output=True, env=env)
        out = json.loads(p.stdout.decode("utf-8"))
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")


if __name__ == "__main__":
    unittest.main()
