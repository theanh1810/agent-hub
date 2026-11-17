"""Tests for tools/package.py: builds go to a temp tree, never into plugins/. The release ships the seven agent files only."""
import importlib.util
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, REPO / "tools" / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


package = load("package_tool", "package.py")
AGENTS = ("brainstorm", "scout", "designer", "implement", "reviewer", "test", "devops")
VARIANT = re.compile(r"-(low|medium|high|xhigh|max)\.md$")


class PackageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wv7-package-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.out = self.tmp / "release"

    def test_release_agents_dir_holds_no_effort_variant(self):
        fake = self.tmp / "repo"
        agents = fake / "plugins" / "agent-hub" / "agents"
        agents.mkdir(parents=True)
        (fake / "plugins" / "agent-hub" / ".claude-plugin").mkdir()
        (fake / "plugins" / "agent-hub" / ".claude-plugin" / "plugin.json").write_text('{"version": "0.0.1"}\n')
        for a in AGENTS:
            (agents / f"{a}.md").write_text(f"---\nname: {a}\nmodel: sonnet\n---\nbody\n")
        (fake / ".claude-plugin").mkdir()
        (fake / ".claude-plugin" / "marketplace.json").write_text("{}\n")
        for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
            shutil.copy2(REPO / name, fake / name)
        code, msg = package.build(repo=str(fake), out=str(self.out), validate=False)
        self.assertEqual(code, 0, msg)
        built = sorted(p.name for p in (self.out / "plugins" / "agent-hub" / "agents").glob("*.md"))
        self.assertEqual(built, sorted(f"{a}.md" for a in AGENTS))
        self.assertEqual([n for n in built if VARIANT.search(n)], [])
        self.assertTrue((self.out / "VERSION").is_file())

    def test_every_plugin_carries_licence_and_notices(self):
        code, msg = package.build(out=str(self.out), validate=False)
        self.assertEqual(code, 0, msg)
        plugins = sorted(p for p in (self.out / "plugins").iterdir() if p.is_dir())
        self.assertGreaterEqual(len(plugins), 1)
        for plugin in plugins:
            for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
                self.assertEqual((plugin / name).read_bytes(), (REPO / name).read_bytes(), f"{plugin.name}/{name}")
        self.assertNotIn("no text, code or assets were copied", (REPO / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8"))

    def test_second_build_replaces_cleanly(self):
        package.build(out=str(self.out), validate=False)
        stray = self.out / "stray.txt"
        stray.write_text("x")
        code, _ = package.build(out=str(self.out), validate=False)
        self.assertEqual(code, 0)
        self.assertFalse(stray.exists())


class OutGuard(unittest.TestCase):
    """--out names a folder the tool deletes: it refuses what it did not build, and what holds the repo or the home."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="m7-package-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = self.tmp / "work" / "repo"
        (self.repo / "plugins" / "agent-hub" / ".claude-plugin").mkdir(parents=True)
        (self.repo / "plugins" / "agent-hub" / ".claude-plugin" / "plugin.json").write_text('{"version": "0.0.1"}\n')
        (self.repo / ".claude-plugin").mkdir()
        (self.repo / ".claude-plugin" / "marketplace.json").write_text("{}\n")
        for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
            shutil.copy2(REPO / name, self.repo / name)

    def build(self, out):
        return package.build(repo=str(self.repo), out=str(out), validate=False)

    def test_existing_non_empty_folder_without_the_marker_is_refused(self):
        out = self.tmp / "mine"
        out.mkdir()
        (out / "keep.txt").write_text("precious")
        code, msg = self.build(out)
        self.assertEqual(code, 2, msg)
        self.assertEqual((out / "keep.txt").read_text(), "precious")

    def test_empty_folder_and_a_folder_this_tool_built_are_replaced(self):
        out = self.tmp / "release"
        out.mkdir()
        self.assertEqual(self.build(out)[0], 0)
        (out / "stray.txt").write_text("x")
        self.assertEqual(self.build(out)[0], 0)
        self.assertFalse((out / "stray.txt").exists())

    def test_repo_root_its_ancestors_and_home_are_refused(self):
        home = self.tmp / "home"
        home.mkdir()
        (home / "keep.txt").write_text("precious")
        for out in (self.repo, self.repo.parent, self.tmp, home):
            marker = out / package.MARKER
            marker.write_text("x")   # even a marker never unlocks these
            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                code, msg = self.build(out)
            self.assertEqual(code, 2, (str(out), msg))
            self.assertTrue((self.repo / "plugins").is_dir(), str(out))
            marker.unlink()
        self.assertEqual((home / "keep.txt").read_text(), "precious")

    def test_missing_licence_leaves_an_existing_release_untouched(self):
        out = self.tmp / "release"
        self.assertEqual(self.build(out)[0], 0)
        (out / "VERSION").write_text("old\n")
        (self.repo / "LICENSE").unlink()
        code, msg = self.build(out)
        self.assertEqual(code, 2, msg)
        self.assertIn("LICENSE", msg)
        self.assertEqual((out / "VERSION").read_text(), "old\n")


if __name__ == "__main__":
    unittest.main()
