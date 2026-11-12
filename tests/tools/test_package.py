"""Tests for tools/package.py and tools/effort-variants.py: builds go to a temp tree, never into plugins/."""
import importlib.util
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, REPO / "tools" / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


package = load("package_tool", "package.py")
variants = load("effort_variants", "effort-variants.py")


def frontmatter(text):
    return text[len("---\n"):].partition("\n---\n")[0].split("\n")


class PackageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wv7-package-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.out = self.tmp / "release"

    def test_build_makes_16_variants(self):
        code, msg = package.build(out=str(self.out), validate=False)
        self.assertEqual(code, 0, msg)
        agents = self.out / "plugins" / "agent-hub" / "agents"
        names = sorted(p.stem for p in agents.glob("*.md") if re.search(r"-(low|medium|high|xhigh|max)$", p.stem))
        self.assertEqual(names, sorted(variants.VARIANTS))
        self.assertEqual(len(names), 16)
        self.assertFalse(any(n.startswith("analyst") for n in names))
        for v in names:
            role = v.rsplit("-", 1)[0]
            base = frontmatter((agents / f"{role}.md").read_text(encoding="utf-8"))
            var = frontmatter((agents / f"{v}.md").read_text(encoding="utf-8"))
            self.assertEqual(len(base), len(var))
            diff = {b.split(":")[0] for b, x in zip(base, var) if b != x}
            self.assertLessEqual(diff, {"name", "description", "effort", "maxTurns"}, v)
            self.assertIn("name", diff)
            self.assertTrue((agents / f"{v}.md").read_text(encoding="utf-8").endswith(
                (agents / f"{role}.md").read_text(encoding="utf-8").partition("\n---\n")[2]))
        self.assertTrue((self.out / "VERSION").is_file())
        # the repo itself holds no variant file
        repo_agents = REPO / "plugins" / "agent-hub" / "agents"
        self.assertEqual([p.name for p in repo_agents.glob("*.md") if p.stem in variants.VARIANTS], [])

    def test_second_build_replaces_cleanly(self):
        package.build(out=str(self.out), validate=False)
        stray = self.out / "stray.txt"
        stray.write_text("x")
        code, _ = package.build(out=str(self.out), validate=False)
        self.assertEqual(code, 0)
        self.assertFalse(stray.exists())

    def test_missing_base_exits_2_naming_it(self):
        fake = self.tmp / "repo"
        shutil.copytree(REPO / "plugins" / "agent-hub", fake / "plugins" / "agent-hub", ignore=shutil.ignore_patterns("lib"))
        shutil.copytree(REPO / ".claude-plugin", fake / ".claude-plugin")
        os.remove(fake / "plugins" / "agent-hub" / "agents" / "planner.md")
        out = self.tmp / "o"
        code = variants.main(["--plugin", str(fake / "plugins" / "agent-hub"), "--out", str(out)])
        self.assertEqual(code, 2)
        with self.assertRaises(FileNotFoundError) as cm:
            variants.build(str(fake / "plugins" / "agent-hub"), str(out))
        self.assertIn("planner.md", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
