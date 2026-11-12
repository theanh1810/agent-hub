"""Tests for tools/port_paths.py. Samples are joined at run time so this file holds no personal or
decision trace itself (the scrub gate scans tests/ too).
Run: python3 -m unittest tests.tools.test_port_paths  (also collected by pytest)."""
import contextlib
import io
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import port_paths  # noqa: E402

RULES = port_paths.load_rules(REPO / "tools" / "port_rules.yaml")
H = "~/." + "claude/"          # the fleet home prefix
ROOT = "${CLAUDE_PLUGIN_ROOT}/"
BODY, REF = "body", "reference"


def port(text, kind=REF):
    return port_paths.apply_rules(text, kind, RULES)


class RuleCase(unittest.TestCase):
    def check(self, text, kind, expected, rule_id=None):
        out, counts = port(text, kind)
        self.assertEqual(out, expected)
        if rule_id:
            self.assertIn(rule_id, counts)
        again, again_counts = port(out, kind)
        self.assertEqual(again, out, "second pass must change nothing")
        self.assertEqual(again_counts, {})

    def untouched(self, text, kind=REF):
        out, counts = port(text, kind)
        self.assertEqual(out, text)
        self.assertEqual(counts, {})


class ScriptRules(RuleCase):
    def test_each_script_maps_to_its_subcommand(self):
        pairs = {"plan-verify": "agent-hub check plan", "plan-locate": "agent-hub locate",
                 "change-map": "agent-hub change-map", "review-packet": "agent-hub review-packet",
                 "secret-scan": "agent-hub secret-scan", "worktree-sweep": "agent-hub worktree-sweep",
                 "docs-migrate": "agent-hub docs-migrate"}
        for name, sub in pairs.items():
            with self.subTest(name):
                self.check(f"run `python3 {H}scripts/{name}.py PLAN`", REF, f"run `{sub} PLAN`", "script-" + name)
                self.check(f"run scripts/{name}.py", REF, f"run {sub}")
                self.check(f"{name}.py checks it", REF, f"{sub} checks it")

    def test_check_ruleset(self):
        self.check(f"bash {H}scripts/check-ruleset.sh", REF, "tools/check ruleset (package repo only)", "script-check-ruleset")

    def test_near_miss_other_script_and_path_suffix(self):
        self.untouched(f"{H}scripts/run-auditor.sh")
        self.untouched("see ${CLAUDE_PLUGIN_ROOT}/scripts/plan-verify.py")
        self.untouched("my-plan-verify.pyc and plan-verifier.py")


class PathRules(RuleCase):
    def test_fleet_path_kinds(self):
        self.check(f"read {H}SDD.md", BODY, f"read {ROOT}rules/SDD.md", "path-rule-file")
        self.check(f"read {H}SDD.md", REF, "read rules/SDD.md")
        self.check(f"read {H}CLAUDE.md", REF, "read rules/core.md", "path-core")
        self.check(f"read {H}code-style/README.md", BODY, f"read {ROOT}rules/code-style/README.md", "path-code-style")
        self.check(f"read {H}rules/code-style/python.md", REF, "read rules/code-style/python.md")
        self.check(f"see {H}templates/spec/x.md", REF, "see templates/spec/x.md", "path-fleet-dir")
        self.check(f"see {H}refs/closeout.md", BODY, f"see {ROOT}refs/closeout.md")
        self.check(f"see {H}agents/planner.md", REF, "see agents/planner.md")

    def test_home_variant(self):
        self.check("read $HOME/." + "claude/UI_RULES.md", REF, "read rules/UI_RULES.md")

    def test_prefix_maps_carry_over(self):
        self.check(f"read {H}agents/refs/planner/x.md", BODY, f"read {ROOT}refs/roles/planner/x.md", "path-role-refs")
        self.check(f"read {H}agents/refs/planner/x.md", REF, "read refs/roles/planner/x.md")
        self.check(f"read {H}commands/refs/a.md", BODY, f"read {ROOT}refs/commands/a.md", "path-command-refs")
        self.check("see agents/refs/brainstorm/modes.md", BODY, "see refs/roles/brainstorm/modes.md", "bare-role-refs")
        self.check("see agents/refs/brainstorm/modes.md", REF, "see refs/roles/brainstorm/modes.md")
        self.check("see commands/refs/spec.md", REF, "see refs/commands/spec.md", "bare-command-refs")

    def test_near_miss_prefix_maps(self):
        self.untouched("see agents/planner.md")           # top-level agent file stays
        self.untouched("see refs/closeout.md")            # a bare top-level refs/ is never rewritten
        self.untouched("see x-agents/refs/y.md and my.commands/refs/z.md")

    def test_user_data_paths_untouched(self):
        for tail in ("memory/MEMORY.md", "agent-memory/x", "projects/p", "plugins/cache", "settings.json"):
            with self.subTest(tail):
                self.untouched(f"read {H}{tail}")
                self.untouched(f"read {H}{tail}", BODY)


class SpawnRules(RuleCase):
    def test_spawn_targets(self):
        self.check('Agent(subagent_type="scout")', REF, 'Agent(subagent_type="agent-hub:scout")', "spawn-subagent-type")
        self.check("subagent_type: implement-medium", REF, "subagent_type: agent-hub:implement")
        self.check('subagent_type="auditor"', REF, 'subagent_type="agent-hub-auditor:auditor"', "spawn-subagent-type-auditor")
        self.check("main spawns `reviewer` after", REF, "main spawns `agent-hub:reviewer` after", "spawn-verb")
        self.check("re-spawn the `test` worker", REF, "re-spawn the `agent-hub:test` worker")
        self.check("Spawn `auditor`", REF, "Spawn `agent-hub-auditor:auditor`", "spawn-verb-auditor")

    def test_near_miss_not_a_spawn_target(self):
        self.untouched("the `implement` agent edits code")
        self.untouched("mode=`scout` is a scan")
        self.untouched("subagent_type: agent-hub:scout")
        self.untouched("subagent_type: scouting")

    def test_frontmatter_name_untouched(self):
        text = "---\nname: scout\ndescription: spawn `scout` often\n---\nsubagent_type: scout\n"
        out, _ = port(text, BODY)
        self.assertEqual(out.splitlines()[1], "name: scout")
        self.assertIn("agent-hub:scout", out.splitlines()[2])
        self.assertIn("agent-hub:scout", out.splitlines()[4])


class AnalystAndPlanRules(RuleCase):
    def test_analyst(self):
        self.check("(`agents/analyst.md` § Gates)", REF, "(`agents/brainstorm.md` § Gates)", "analyst-file")
        self.check("see agents/analyst-high.md", REF, "see agents/brainstorm.md")
        self.check("the analyst role", REF, "the brainstorm role", "analyst-word")
        self.check("Analyst owns it", REF, "Brainstorm owns it", "analyst-word-cap")

    def test_analyst_spawn_value_is_renamed_then_qualified(self):
        self.check('Agent(subagent_type="analyst")', REF, 'Agent(subagent_type="agent-hub:brainstorm")')

    def test_analyst_near_miss(self):
        self.untouched("keys analyst_handoff and analyst-high")
        self.untouched("docs/adr/009-scout-replaces-analyst-scan.md")  # scrub-allow: test fixture
        self.untouched("refs/roles/analyst/x.md")

    def test_plan_lang(self):
        self.check("write plan.vi.md", REF, "write plan.<lang>.md", "plan-lang-mirror")
        self.check("templates/plan/plan.vi-template.md", REF, "templates/plan/plan.lang-template.md", "plan-lang-template")
        self.check("plan.vi-lite-template.md", REF, "plan.lang-lite-template.md", "plan-lang-lite-template")

    def test_plan_lang_near_miss(self):
        self.untouched("plan.yaml and plan.md and plan.vi.mdx2")


class CitationRule(RuleCase):
    USER = "user 2026" + "-10-22"
    Q = "Q" + "31"
    ADR_FILE = "docs/" + "adr/003-x.md"
    ANALYSIS = "docs/" + "analysis/x.yaml"
    ADR_ID = "ADR" + "-018"

    def test_pure_citations_stripped(self):
        for cite in (self.USER, f"{self.USER}, {self.Q}", self.Q, f"{self.Q}, {self.Q}", self.ADR_FILE,
                     f"`{self.ADR_FILE}`", self.ANALYSIS, self.ADR_ID):
            with self.subTest(cite):
                self.check(f"Rule one ({cite}) applies.", REF, "Rule one applies.", "strip-citation")

    def test_mixed_parenthetical_left(self):
        for mixed in (f"({self.USER}: \"quoted words\")", f"({self.Q} and the reason)", f"(see {self.ADR_FILE})",
                      f"(user decision 1 of 2026-10-26, {self.Q})"):
            with self.subTest(mixed):
                self.untouched(f"Rule {mixed} applies.")

    def test_ordinary_parentheses_untouched(self):
        self.untouched("a (small) note (Q&A) and (2026-10-22)")


class MarkerAndKinds(unittest.TestCase):
    def test_marked_line_untouched(self):
        text = f"keep {H}SDD.md scrub-allow: fixture\nchange {H}SDD.md\n"
        out, counts = port(text)
        self.assertEqual(out.splitlines()[0], f"keep {H}SDD.md scrub-allow: fixture")
        self.assertEqual(out.splitlines()[1], "change rules/SDD.md")
        self.assertEqual(counts, {"path-rule-file": 1})

    def test_classify(self):
        for rel, kind in (("plugins/agent-hub/agents/scout.md", BODY),
                          ("plugins/agent-hub/skills/gitnexus-flow/SKILL.md", BODY),
                          ("plugins/agent-hub/commands/spec.md", BODY),
                          ("agents/scout.md", BODY),
                          ("plugins/agent-hub/refs/roles/scout/x.md", REF),
                          ("plugins/agent-hub/skills/gitnexus-flow/notes.md", REF),
                          ("plugins/agent-hub/templates/plan/t.yaml", REF),
                          ("tools/x.py", REF),
                          ("plugins/agent-hub/.claude-plugin/plugin.json", None),
                          ("plugins/x/scripts/mcp/figma.sh", None)):
            with self.subTest(rel):
                self.assertEqual(port_paths.classify(rel), kind)


class Cli(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.tmp = Path(self._td.name)

    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = port_paths.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def tree(self):
        self.walk = self.tmp / "walk"
        agents = self.walk / "agents"
        agents.mkdir(parents=True)
        body = agents / "x.md"
        body.write_text(f"---\nname: x\n---\nread {H}SDD.md and plan.vi.md\n", encoding="utf-8")
        ref = self.walk / "notes.md"
        ref.write_text(f"read {H}SDD.md\n", encoding="utf-8")
        return body, ref

    def test_unknown_kind_exits_2_naming_the_file(self):
        bad = self.tmp / "data.json"
        bad.write_text("{}", encoding="utf-8")
        code, out, err = self.run_main(str(bad))
        self.assertEqual(code, 2)
        self.assertIn(str(bad), err)
        self.assertIn("unknown file kind", err)

    def test_missing_path_exits_2(self):
        code, _, err = self.run_main(str(self.tmp / "nope.md"))
        self.assertEqual(code, 2)
        self.assertIn("nope.md", err)

    def test_dry_run_writes_nothing_and_second_run_is_zero(self):
        body, ref = self.tree()
        before = (body.read_text(), ref.read_text())
        code, out, _ = self.run_main("--dry-run", str(self.walk))
        self.assertEqual(code, 0)
        self.assertEqual((body.read_text(), ref.read_text()), before)
        self.assertRegex(out, r"\s+2\s+path-rule-file")
        code, out, _ = self.run_main(str(self.walk))
        self.assertEqual(code, 0)
        self.assertIn(ROOT + "rules/SDD.md", body.read_text())
        self.assertIn("name: x\n", body.read_text())
        self.assertIn("read rules/SDD.md", ref.read_text())
        code, out, _ = self.run_main(str(self.walk))
        self.assertIn("total hits: 0;", out)
        self.assertIn("changed 0 of", out)
        self.assertFalse([ln for ln in out.splitlines() if re.match(r"\s*[1-9]\d*\s+\S", ln)])

    def test_directory_walk_skips_unknown_kinds_and_skip_globs(self):
        self.tree()
        (self.walk / "data.json").write_text(f"{H}SDD.md", encoding="utf-8")
        rules = self.tmp / "rules.yaml"
        rules.write_text("skip:\n  - '*/notes.md'\nrules:\n  - {id: r, pattern: 'SDD', replace: 'X'}\n", encoding="utf-8")
        code, out, _ = self.run_main("--rules", str(rules), str(self.walk))
        self.assertEqual(code, 0)
        self.assertIn("changed 1 of 2 files", out)  # json not collected, notes.md skipped, x.md changed
        self.assertEqual((self.walk / "data.json").read_text(), f"{H}SDD.md")

    def test_file_mode_is_kept(self):
        body, _ = self.tree()
        body.chmod(0o640)
        self.run_main(str(body))
        self.assertEqual(body.stat().st_mode & 0o777, 0o666 if os.name == 'nt' else 0o640)


if __name__ == "__main__":
    unittest.main()
