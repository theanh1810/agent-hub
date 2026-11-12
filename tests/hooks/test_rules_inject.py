"""Unit tests for plugins/agent-hub/hooks/rules_inject.py and hooks.json (runs under unittest and pytest)."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PLUGIN = REPO / "plugins" / "agent-hub"
HOOKS = PLUGIN / "hooks"
sys.path.insert(0, str(HOOKS))
import _common  # noqa: E402
import rules_inject as ri  # noqa: E402

SCRIPT = HOOKS / "rules_inject.py"


def run(args, stdin="{}", env_extra=None, root=PLUGIN, unset=()):
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_PLUGIN_OPTION_") and k != "AGENT_HUB_DIRECT" and k not in unset}
    env["CLAUDE_PLUGIN_ROOT"] = str(root)
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(SCRIPT)] + args, input=stdin, capture_output=True, text=True, env=env)


def ctx(proc):
    return json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]


def synthetic_root(sections, tmp):
    (Path(tmp) / "rules").mkdir()
    (Path(tmp) / "rules" / "core.md").write_text("".join(sections), encoding="utf-8")
    return Path(tmp)


class RealCore(unittest.TestCase):
    def test_real_core_chunks_within_limits_and_in_order(self):
        core = (PLUGIN / "rules" / "core.md").read_text(encoding="utf-8")
        chunks = ri.build_chunks(core, PLUGIN.as_posix(), "en")
        self.assertLessEqual(len(chunks), 3)
        for c in chunks:
            self.assertLessEqual(len(c), 9500)
        joined = "".join(chunks)
        self.assertEqual(joined, ri.fill(core, PLUGIN.as_posix(), "en"))
        heads = [l for l in joined.splitlines() if l.startswith("# ")]
        self.assertEqual(heads, [l for l in core.splitlines() if l.startswith("# ")])
        for c in chunks[1:]:
            self.assertTrue(c.startswith("# "), "a section was split across chunks")

    def test_emitted_chunks_with_directive_within_limit(self):
        for ev in ("SessionStart", "SubagentStart"):
            for n in (1, 2):
                p = run([ev, str(n)], stdin='{"agent_type":"agent-hub:planner"}')
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertLessEqual(len(ctx(p)), 9500)

    def test_no_placeholder_left(self):
        for n in (1, 2):
            c = ctx(run(["SessionStart", str(n)]))
            self.assertNotIn("{{", c)
        self.assertIn(PLUGIN.as_posix(), ctx(run(["SessionStart", "1"])))

    def test_hooks_json_names_only_hooks_scripts_by_root_token(self):
        data = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))
        cmds = [h["command"] for groups in data["hooks"].values() for g in groups for h in g["hooks"]]
        scripts = []
        for c in cmds:
            if c.startswith("python3 -c "):
                self.assertIn("Python 3.11+ not found as python3; hooks and scripts are off. Install Python 3.11+ and restart.", c)
                continue
            m = re.match(r'python3 "\$\{CLAUDE_PLUGIN_ROOT\}/hooks/([a-z_]+)\.py"( .*)?$', c)
            self.assertIsNotNone(m, c)
            scripts.append(m.group(1))
        self.assertEqual(set(scripts), {"rules_inject", "clear_handoff", "post_compact_pointer", "git_guard", "read_guard", "worktree_create", "worktree_remove"})
        for ev in ("SessionStart", "SubagentStart", "PreToolUse", "SessionEnd", "WorktreeCreate", "WorktreeRemove"):
            self.assertIn(ev, data["hooks"])
        rj = [c for c in cmds if "rules_inject" in c]
        self.assertEqual(len(rj), 6)
        for c in rj:
            self.assertNotIn("--lang", c)
        sa = data["hooks"]["SubagentStart"]
        self.assertTrue(all(g["matcher"] == "^agent-hub:" for g in sa))
        self.assertTrue(all(g["matcher"] == "startup|clear|compact" for g in data["hooks"]["SessionStart"][1:4]))

    def test_no_user_config_in_shell_form_command(self):
        files = sorted((REPO / "plugins").glob("*/hooks/hooks.json"))
        self.assertTrue(files)
        for f in files:
            for groups in json.loads(f.read_text())["hooks"].values():
                for g in groups:
                    for h in g["hooks"]:
                        self.assertNotIn("${user_config", h.get("command", ""), f.as_posix())


class Synthetic(unittest.TestCase):
    def test_four_chunks_warn_on_chunk_one_only(self):
        secs = ["# S%d\n%s\n" % (i, "x" * 7000) for i in range(4)]
        with tempfile.TemporaryDirectory() as tmp:
            root = synthetic_root(secs, tmp)
            self.assertEqual(len(ri.build_chunks("".join(secs), root.as_posix(), "en")), 4)
            p1 = run(["SessionStart", "1"], root=root)
            out = json.loads(p1.stdout)
            self.assertEqual(out["systemMessage"], "agent-hub: rules exceed 3 hook chunks; some rules were not loaded")
            p2 = run(["SessionStart", "2"], root=root)
            self.assertNotIn("systemMessage", json.loads(p2.stdout))
            self.assertIn("# S1", ctx(p2))

    def test_direct_mode_directive_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = synthetic_root(["# A\nbody\n"], tmp)
            d = ctx(run(["SessionStart", "1"], env_extra={"AGENT_HUB_DIRECT": "1"}, root=root))
            self.assertTrue(d.startswith(ri.DIRECT_DIRECTIVE))
            r = ctx(run(["SessionStart", "1"], root=root))
            self.assertTrue(r.startswith(ri.ROUTING_DIRECTIVE))
            self.assertNotIn(ri.DIRECT_DIRECTIVE, r)

    def test_n_beyond_chunk_count_prints_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = synthetic_root(["# A\nbody\n"], tmp)
            for n in ("2", "3"):
                p = run(["SessionStart", n], root=root)
                self.assertEqual((p.returncode, p.stdout), (0, ""))

    def test_unreadable_core_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = run(["SessionStart", "1"], root=Path(tmp))
            self.assertEqual((p.returncode, p.stdout), (0, ""))
            self.assertIn("cannot read core.md", p.stderr)


class Stdin(unittest.TestCase):
    def test_malformed_stdin_exits_zero_with_stderr(self):
        p = run(["SubagentStart", "1"], stdin="{not json")
        self.assertEqual(p.returncode, 0)
        self.assertIn("malformed stdin JSON", p.stderr)
        self.assertEqual(len(p.stderr.strip().splitlines()), 1)

    def test_python_below_311_is_silent(self):
        src = SCRIPT.read_text(encoding="utf-8")
        self.assertLess(src.index("sys.version_info < (3, 11)"), src.index("import _common"))


class Language(unittest.TestCase):
    def lang_of(self, args, env):
        c = ctx(run(["SessionStart", "1"] + args, env_extra=env))
        core = (PLUGIN / "rules" / "core.md").read_text(encoding="utf-8")
        return c, core.count("{{REPLY_LANGUAGE}}")

    def test_reply_language_rows(self):
        marker = "| %s; the mirror is skipped"
        c, n = self.lang_of(["--lang", "vi"], {})
        self.assertIn(marker % "vi", c)
        self.assertNotIn(marker % "en", c)
        c, _ = self.lang_of(["--lang", "${user_config.reply_language}"], {"CLAUDE_PLUGIN_OPTION_REPLY_LANGUAGE": "vi"})
        self.assertIn(marker % "vi", c)
        c, _ = self.lang_of(["--lang", "${user_config.reply_language}"], {})
        self.assertIn(marker % "en", c)
        c, _ = self.lang_of([], {})
        self.assertIn(marker % "en", c)

    def test_every_placeholder_filled(self):
        core = (PLUGIN / "rules" / "core.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(core.count("{{REPLY_LANGUAGE}}"), 1)
        out = ri.fill(core, "/r", "vi")
        self.assertEqual(out.count("{{REPLY_LANGUAGE}}"), 0)
        self.assertEqual(len(re.findall(r"\bvi\b", out)) - len(re.findall(r"\bvi\b", core)), core.count("{{REPLY_LANGUAGE}}"))

    def test_reply_language_validation(self):
        for bad in ("${user_config.reply_language}", "", "EN", "english", "vi;rm"):
            self.assertEqual(_common.reply_language(bad) if bad else _common.reply_language(None), "en")
        self.assertEqual(_common.reply_language("pt-BR"), "pt-BR")


class Subagent(unittest.TestCase):
    def test_scout_gets_nothing_planner_gets_chunk(self):
        p = run(["SubagentStart", "1"], stdin='{"agent_type":"agent-hub:scout"}')
        self.assertEqual((p.returncode, p.stdout), (0, ""))
        p = run(["SubagentStart", "1"], stdin='{"agent_type":"agent-hub:planner"}')
        c = ctx(p)
        self.assertEqual(json.loads(p.stdout)["hookSpecificOutput"]["hookEventName"], "SubagentStart")
        self.assertNotIn("SESSION DIRECTIVE", c)
        self.assertTrue(c.startswith("# Global Agent Rules"))
        p2 = run(["SubagentStart", "2"], stdin='{"agent_type":"agent-hub:planner"}')
        self.assertTrue(ctx(p2).startswith("# "))


class NonUtf8Locale(unittest.TestCase):
    def test_cp1252_stdio_still_emits_utf8_json(self):
        env = dict(os.environ, PYTHONUTF8="0", PYTHONIOENCODING="cp1252")
        p = subprocess.run([sys.executable, str(SCRIPT), "SessionStart", "1"], input=b"", capture_output=True, env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        ctx = json.loads(p.stdout.decode("utf-8"))["hookSpecificOutput"]["additionalContext"]
        self.assertIn("\u2192", ctx)


if __name__ == "__main__":
    unittest.main()
