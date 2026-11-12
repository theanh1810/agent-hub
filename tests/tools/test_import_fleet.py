"""Tests for tools/import_fleet.py on temp source trees (plus a static check of the real manifest).
Run: python3 -m unittest tests.tools.test_import_fleet  (also collected by pytest)."""
import contextlib
import io
import re
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import import_fleet  # noqa: E402


class Case(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        root = Path(self._td.name)
        self.src, self.repo = root / "src", root / "repo"
        self.src.mkdir()
        self.repo.mkdir()
        self.manifest = root / "manifest.yaml"
        self.lock = root / "import-lock.yaml"

    def write(self, rel, text="x\n"):
        p = self.src / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def manifest_rows(self, rows, forbidden=()):
        self.manifest.write_text(yaml.safe_dump({"forbidden": list(forbidden), "rows": rows}))

    def run_tool(self, *extra):
        out, err = io.StringIO(), io.StringIO()
        argv = ["--src", str(self.src), "--repo", str(self.repo), "--manifest", str(self.manifest),
                "--lock", str(self.lock), *extra]
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = import_fleet.main(argv)
        return code, out.getvalue(), err.getvalue()

    def repo_files(self):
        return sorted(p.relative_to(self.repo).as_posix() for p in self.repo.rglob("*") if p.is_file())


class ImportTests(Case):
    def test_mapped_rows_copied_dropped_rows_absent(self):
        self.write("a/keep.md")
        self.write("a/sub/deep.md")
        self.write("a/__pycache__/x.pyc")
        self.write("a/.DS_Store")
        self.write("agents/analyst.md")
        self.write("agents/analyst-high.md")
        self.write("agents/brainstorm.md")
        self.write("one.md")
        self.manifest_rows([
            {"src": "a", "dst": "plugins/p/a"},
            {"src": "one.md", "dst": "plugins/p/rules/core.md"},
            {"src": "agents/brainstorm.md", "dst": "plugins/p/agents/brainstorm.md"},
            {"src": "agents/analyst*.md", "drop": "Q31"},  # scrub-allow: test fixture
        ])
        code, out, _ = self.run_tool()
        self.assertEqual(code, 0)
        self.assertEqual(self.repo_files(), ["plugins/p/a/keep.md", "plugins/p/a/sub/deep.md",
                                             "plugins/p/agents/brainstorm.md", "plugins/p/rules/core.md"])
        self.assertIn("rows expanded: 4; copied: 4", out)
        lock = yaml.safe_load(self.lock.read_text())["files"]
        self.assertEqual(len(lock), 4)
        self.assertTrue(all(len(e["sha256"]) == 64 for e in lock))

    def test_more_specific_row_wins_and_drop_beats_copy(self):
        self.write("refs/a.md")
        self.write("refs/local.md")
        self.write("refs/gone.md")
        self.manifest_rows([
            {"src": "refs", "dst": "plugins/p/refs"},
            {"src": "refs/local.md", "dst": "plugins/q/refs/local.md"},
            {"src": "refs/gone.md", "drop": "Q1"},  # scrub-allow: test fixture
        ])
        self.assertEqual(self.run_tool()[0], 0)
        self.assertEqual(self.repo_files(), ["plugins/p/refs/a.md", "plugins/q/refs/local.md"])

    def test_empty_folder_row_copies_nothing(self):
        (self.src / "empty").mkdir()
        self.manifest_rows([{"src": "empty", "dst": "plugins/p/empty"}])
        code, out, _ = self.run_tool()
        self.assertEqual(code, 0)
        self.assertIn("rows expanded: 0; copied: 0", out)
        self.assertEqual(self.repo_files(), [])

    def test_forbidden_prefix_exits_2_and_copies_nothing(self):
        self.write("ok.md")
        self.write("memory/secret.md")
        for bad in ("memory/secret.md", "memory", "settings.json", "history.jsonl", "docs/adr/1.md",  # scrub-allow: test fixture
                    "../.claude.json"):
            self.manifest_rows([{"src": "ok.md", "dst": "plugins/p/ok.md"}, {"src": bad, "dst": "plugins/p/x"}])
            code, _, err = self.run_tool()
            self.assertEqual(code, 2, bad)
            self.assertIn("manifest error", err)
            self.assertEqual(self.repo_files(), [], bad)
            self.assertFalse(self.lock.exists())

    def test_expanded_file_under_forbidden_glob_is_refused(self):
        self.write("tpl/settings.json")
        self.manifest_rows([{"src": "tpl", "dst": "plugins/p/tpl"}])
        self.assertEqual(self.run_tool()[0], 2)
        self.assertEqual(self.repo_files(), [])

    def test_templates_memory_is_not_the_forbidden_root_memory(self):
        self.write("templates/memory/PROJECT-MEM.md")
        self.manifest_rows([{"src": "templates", "dst": "plugins/p/templates"}])
        self.assertEqual(self.run_tool()[0], 0)

    def test_missing_source_stops_reports_row_and_leaves_no_lock(self):
        self.write("a.md")
        self.manifest_rows([{"src": "a.md", "dst": "plugins/p/a.md"}, {"src": "nope.md", "dst": "plugins/p/n.md"}])
        code, _, err = self.run_tool()
        self.assertEqual(code, 1)
        self.assertIn("nope.md", err)
        self.assertFalse(self.lock.exists())
        self.assertEqual(self.repo_files(), [])

    def test_check_no_drift_then_lists_edited_and_missing_source(self):
        self.write("a.md", "one\n")
        self.write("b.md", "two\n")
        self.manifest_rows([{"src": "a.md", "dst": "plugins/p/a.md"}, {"src": "b.md", "dst": "plugins/p/b.md"}])
        self.assertEqual(self.run_tool()[0], 0)
        code, out, _ = self.run_tool("--check")
        self.assertEqual(code, 0)
        self.assertIn("drifted: 0", out)
        self.write("a.md", "changed\n")
        (self.src / "b.md").unlink()
        code, out, _ = self.run_tool("--check")
        self.assertEqual(code, 1)
        self.assertIn("drift: a.md (changed)", out)
        self.assertIn("drift: b.md (missing)", out)

    def test_two_sources_to_one_destination_is_refused(self):
        self.write("a.md")
        self.write("b.md")
        self.manifest_rows([{"src": "a.md", "dst": "plugins/p/x.md"}, {"src": "b.md", "dst": "plugins/p/x.md"}])
        self.assertEqual(self.run_tool()[0], 2)


@unittest.skipUnless((REPO / "tools" / "manifest.yaml").is_file(),
                     "tools/manifest.yaml is git-ignored and exists only on the maintainer machine")
class RealManifestTests(unittest.TestCase):
    """Static checks on tools/manifest.yaml, no source tree needed."""

    def setUp(self):
        self.forbidden, self.rows = import_fleet.load_manifest(REPO / "tools" / "manifest.yaml")

    def test_manifest_loads_and_has_forbidden_list(self):
        self.assertIn("settings*.json", self.forbidden)
        self.assertTrue(self.rows)

    def test_no_dst_puts_md_in_a_subfolder_of_agents_or_commands(self):
        bad = re.compile(r"^plugins/[^/]+/(agents|commands)/[^/]+/")
        for row in self.rows:
            if "dst" in row:
                self.assertIsNone(bad.match(row["dst"]), row)

    def test_agent_refs_land_under_refs_roles(self):
        dsts = {str(r["src"]): str(r["dst"]) for r in self.rows if "dst" in r}
        self.assertEqual(dsts["agents/refs"], "plugins/agent-hub/refs/roles")
        self.assertEqual(dsts["agents/refs/auditor"], "plugins/agent-hub-auditor/refs/roles/auditor")
        self.assertEqual(dsts["commands/refs"], "plugins/agent-hub/refs/commands")


if __name__ == "__main__":
    unittest.main()
