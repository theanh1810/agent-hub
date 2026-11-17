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


def core_text():
    return (PLUGIN / "rules" / "core.md").read_text(encoding="utf-8")


def main_view():
    return ri.render(core_text(), PLUGIN.as_posix(), "en", "main")


def sub_view():
    return ri.render(core_text(), PLUGIN.as_posix(), "en", "subagent")


RETIRED = re.compile(r"orchestrator|planner|next_spawns|plan\.yaml|plan-verify|devops-low|effort variant", re.I)


class RealCore(unittest.TestCase):
    def test_main_view_size_and_chunk_count(self):
        view = main_view()
        self.assertLessEqual(len(view), 12000)
        chunks = ri.build_chunks(core_text(), PLUGIN.as_posix(), "en", "main")
        self.assertLessEqual(len(chunks), 2)
        for c in chunks:
            self.assertLessEqual(len(c), 9500)
        self.assertEqual("".join(chunks), view)
        heads = [l for l in view.splitlines() if l.startswith("#")]
        self.assertEqual(heads, [l for l in core_text().splitlines() if l.startswith("#")])
        for c in chunks[1:]:
            self.assertTrue(c.startswith("#"), "a section was split across chunks")

    def test_subagent_view_size_and_single_chunk(self):
        view = sub_view()
        self.assertLessEqual(len(view), 6000)
        chunks = ri.build_chunks(core_text(), PLUGIN.as_posix(), "en", "subagent")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], view)

    def test_views_fit_with_a_long_install_root(self):
        root = "/" + "r" * 69  # the installed cache path is about 60 characters
        self.assertLessEqual(len(ri.render(core_text(), root, "en", "subagent")), 6000)
        self.assertLessEqual(len(ri.render(core_text(), root, "en", "main")), 12000)
        self.assertEqual(len(ri.build_chunks(core_text(), root, "en", "subagent")), 1)
        self.assertLessEqual(len(ri.build_chunks(core_text(), root, "en", "main")), 2)

    def test_main_only_rows_absent_from_subagent_view(self):
        main, sub = main_view(), sub_view()
        for text in (main, sub):
            self.assertNotIn("main-only", text)
        self.assertLess(len(sub), len(main))
        for marker in ("## Routing", "| L2 small |", "refs/lanes.md", "approval stamp, the rulings ledger", "thinking-partner", "refs/vendored/teach.md", "Main thread calls `AskUserQuestion`"):
            self.assertIn(marker, main, marker)
            self.assertNotIn(marker, sub, marker)
        self.assertIn("## Ask, never guess", sub)
        self.assertIn("**How to ask**", sub)

    def test_core_shape_rulings(self):
        core = core_text()
        self.assertIsNone(re.search(r"(?m)^#{1,6} \d", core))
        self.assertEqual(len(re.findall(r"(?m)^# ", core)), 1)
        self.assertIn("| Lane | When | Spawn order | Stops at |", core)
        self.assertNotIn("| Agent | Model |", core)
        self.assertEqual(core.count("[<agent> \u00b7 model: <haiku|sonnet|opus>]"), 1)
        self.assertEqual(len(re.findall(r"(?m)^<!-- main-only:begin -->$", core)) + len(re.findall(r"(?m)^<!-- main-only:end -->$", core)), 2 * len(re.findall(r"(?m)^<!-- main-only:begin -->$", core)))

    def test_four_principles_first_section_of_both_views(self):
        for view in (main_view(), sub_view()):
            heads = [l for l in view.splitlines() if l.startswith("## ")]
            self.assertEqual(heads[0], "## Four principles (HARD)")
        self.assertNotIn("## Coding principles", core_text())

    def test_both_views_fit_a_92_char_root(self):
        root = "/" + "r" * 91
        self.assertEqual(len(root), 92)
        self.assertLessEqual(len(ri.render(core_text(), root, "en", "subagent")), 6000)
        self.assertLessEqual(len(ri.render(core_text(), root, "en", "main")), 12000)

    def test_subagent_view_fits_a_90_char_root(self):
        root = "/" + "r" * 89
        self.assertLessEqual(len(ri.render(core_text(), root, "en", "subagent")), 6000)

    def test_no_memory_tool_name_in_core(self):
        self.assertNotIn("mem0", core_text())

    def test_main_only_fences_balanced_in_real_core(self):
        core = core_text()
        self.assertEqual(core.count("<!-- main-only:begin -->"), core.count("<!-- main-only:end -->"))
        self.assertGreaterEqual(core.count("<!-- main-only:begin -->"), 3)

    def test_store_match_start_line_in_both_views(self):
        for view in (main_view(), sub_view()):
            self.assertIn("agent-hub store match --files <files to edit>", view)
            self.assertIn("at most two printed entries", view)

    def test_start_block_within_budget(self):
        m = re.search(r"(?ms)^## Start\n.*?(?=^#)", core_text())
        self.assertIsNotNone(m)
        self.assertLessEqual(len(m.group(0)), 1200)

    def test_no_retired_names_in_core_or_hook(self):
        self.assertIsNone(RETIRED.search(core_text()))
        self.assertIsNone(RETIRED.search(SCRIPT.read_text(encoding="utf-8")))

    def test_ruling_line_and_five_kinds_present(self):
        sub = sub_view()
        self.assertIn("Ruling: <what you decided> \u2014 <why> \u2014 <what it costs if wrong>", sub)
        self.assertIn("**May rule, and log**", sub)

    def test_emitted_chunks_within_limit_and_counts(self):
        for n in (1, 2):
            p = run(["SessionStart", str(n)])
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertLessEqual(len(ctx(p)), 10000)
        p = run(["SubagentStart", "1"], stdin='{"agent_type":"agent-hub:implement"}')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertLessEqual(len(ctx(p)), 10000)
        for ev, n in (("SessionStart", "3"), ("SubagentStart", "2")):
            p = run([ev, n], stdin='{"agent_type":"agent-hub:implement"}')
            self.assertEqual((p.returncode, p.stdout), (0, ""))

    def test_no_placeholder_left(self):
        for n in (1, 2):
            self.assertNotIn("{{", ctx(run(["SessionStart", str(n)])))
        self.assertIn(PLUGIN.as_posix(), ctx(run(["SessionStart", "1"])))

    def test_session_start_is_main_view_and_subagent_is_not(self):
        s1 = ctx(run(["SessionStart", "1"]))
        self.assertIn("## Routing", s1)
        self.assertIn("| L-cfg no-plan |", s1)
        a1 = ctx(run(["SubagentStart", "1"], stdin='{"agent_type":"agent-hub:implement"}'))
        self.assertNotIn("## Routing", a1)
        self.assertNotIn("| L-cfg no-plan |", a1)
        self.assertIn("## Ask, never guess", a1)

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
        self.assertEqual(set(scripts), {"rules_inject", "clear_handoff", "post_compact_pointer", "git_guard", "read_guard", "worktree_create", "worktree_remove", "format_on_edit"})
        for ev in ("SessionStart", "SubagentStart", "PreToolUse", "PostToolUse", "SessionEnd", "WorktreeCreate", "WorktreeRemove"):
            self.assertIn(ev, data["hooks"])
        post = [h["command"] for g in data["hooks"]["PostToolUse"] for h in g["hooks"]]
        self.assertEqual(len(post), 1)
        self.assertIn("format_on_edit.py", post[0])
        rj = [c for c in cmds if "rules_inject" in c]
        self.assertEqual(sorted(rj), sorted([
            'python3 "${CLAUDE_PLUGIN_ROOT}/hooks/rules_inject.py" SessionStart 1',
            'python3 "${CLAUDE_PLUGIN_ROOT}/hooks/rules_inject.py" SessionStart 2',
            'python3 "${CLAUDE_PLUGIN_ROOT}/hooks/rules_inject.py" SubagentStart 1']))
        for c in rj:
            self.assertNotIn("--lang", c)
        sa = data["hooks"]["SubagentStart"]
        self.assertEqual(len(sa), 1)
        self.assertTrue(all(g["matcher"] == "^agent-hub:" for g in sa))
        self.assertTrue(all(g["matcher"] == "startup|clear|compact" for g in data["hooks"]["SessionStart"][1:3]))

    def test_no_user_config_in_shell_form_command(self):
        files = sorted((REPO / "plugins").glob("*/hooks/hooks.json"))
        self.assertTrue(files)
        for f in files:
            for groups in json.loads(f.read_text())["hooks"].values():
                for g in groups:
                    for h in g["hooks"]:
                        self.assertNotIn("${user_config", h.get("command", ""), f.as_posix())


class Synthetic(unittest.TestCase):
    def test_three_main_chunks_warn_on_chunk_one_only(self):
        secs = ["# S%d\n%s\n" % (i, "x" * 7000) for i in range(3)]
        with tempfile.TemporaryDirectory() as tmp:
            root = synthetic_root(secs, tmp)
            self.assertEqual(len(ri.build_chunks("".join(secs), root.as_posix(), "en", "main")), 3)
            p1 = run(["SessionStart", "1"], root=root)
            out = json.loads(p1.stdout)
            self.assertEqual(out["systemMessage"], "agent-hub: rules exceed 2 hook chunks; some rules were not loaded")
            p2 = run(["SessionStart", "2"], root=root)
            self.assertNotIn("systemMessage", json.loads(p2.stdout))
            self.assertIn("# S1", ctx(p2))

    def test_two_subagent_chunks_warn(self):
        secs = ["# S%d\n%s\n" % (i, "x" * 7000) for i in range(2)]
        with tempfile.TemporaryDirectory() as tmp:
            root = synthetic_root(secs, tmp)
            p1 = run(["SubagentStart", "1"], stdin='{"agent_type":"agent-hub:test"}', root=root)
            self.assertEqual(json.loads(p1.stdout)["systemMessage"], "agent-hub: rules exceed 1 hook chunks; some rules were not loaded")

    def test_main_only_fences_line_and_inline(self):
        text = "# A\nkeep\n<!-- main-only:begin -->\n# B\nsecret\n<!-- main-only:end -->\n# C\ntail <!-- main-only:begin -->inline<!-- main-only:end -->end\n"
        self.assertEqual(ri.render(text, "/r", "en", "subagent"), "# A\nkeep\n# C\ntail end\n")
        self.assertEqual(ri.render(text, "/r", "en", "main"), "# A\nkeep\n# B\nsecret\n# C\ntail inlineend\n")

    def test_direct_mode_directive_first_and_no_routing_directive(self):
        self.assertFalse(hasattr(ri, "ROUTING_DIRECTIVE"))
        with tempfile.TemporaryDirectory() as tmp:
            root = synthetic_root(["# A\nbody\n"], tmp)
            d = ctx(run(["SessionStart", "1"], env_extra={"AGENT_HUB_DIRECT": "1"}, root=root))
            self.assertTrue(d.startswith(ri.DIRECT_DIRECTIVE))
            r = ctx(run(["SessionStart", "1"], root=root))
            self.assertEqual(r, "# A\nbody\n")

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
        marker = "| The reply to the user and the text of `user_questions[]` | %s |"
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
    def test_scout_and_implement_get_subagent_view(self):
        p = run(["SubagentStart", "1"], stdin='{"agent_type":"agent-hub:scout"}')
        self.assertEqual(ctx(p), ri.render(core_text(), PLUGIN.as_posix(), "en", "subagent"))
        p = run(["SubagentStart", "1"], stdin='{"agent_type":"agent-hub:implement"}')
        c = ctx(p)
        self.assertEqual(json.loads(p.stdout)["hookSpecificOutput"]["hookEventName"], "SubagentStart")
        self.assertNotIn("SESSION DIRECTIVE", c)
        self.assertTrue(c.startswith("# Global Agent Rules"))
        self.assertEqual(c, ri.render(core_text(), PLUGIN.as_posix(), "en", "subagent"))


class NonUtf8Locale(unittest.TestCase):
    def test_cp1252_stdio_still_emits_utf8_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = synthetic_root(["# A\n\u2192 arrow\n"], tmp)
            env = dict(os.environ, PYTHONUTF8="0", PYTHONIOENCODING="cp1252", CLAUDE_PLUGIN_ROOT=str(root))
            p = subprocess.run([sys.executable, str(SCRIPT), "SessionStart", "1"], input=b"", capture_output=True, env=env)
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout.decode("utf-8"))["hookSpecificOutput"]["additionalContext"]
            self.assertIn("\u2192", out)


if __name__ == "__main__":
    unittest.main()
