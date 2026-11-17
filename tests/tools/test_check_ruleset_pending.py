"""The PENDING rule of tools/check-ruleset.sh, run on a throwaway repo: WP_DONE unset means ALL; PENDING only for an explicit subset.

The script is copied into a temp repo whose manifest names one package (Q) that has not landed, so no real tree is
read. Check `test_modes_in_description` declares package H as a need and fails on an empty plugin."""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools" / "check-ruleset.sh"
CHECK = "test_modes_in_description"


def run(root, done=None):
    env = {k: v for k, v in os.environ.items() if k != "WP_DONE"}
    if done is not None:
        env["WP_DONE"] = done
    p = subprocess.run(["bash", str(root / "tools" / "check-ruleset.sh")], env=env, cwd=root,
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout


def line_of(out, name):
    return next(l for l in out.splitlines() if re.match(r"^(PASS|FAIL|PENDING)\b.*?\b%s\b" % name, l))


class PendingRule(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="wd-pend-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "tools").mkdir()
        shutil.copy(SCRIPT, self.root / "tools" / "check-ruleset.sh")
        (self.root / "plugins" / "agent-hub" / "rules").mkdir(parents=True)
        (self.root / "tools" / "v2-manifest.tsv").write_text(
            "plugins/agent-hub/agents/implement.md\tNEW\tx\tH\n"
            "plugins/agent-hub/agents/test.md\tNEW\tx\tH\n", encoding="utf-8")

    def test_explicit_subset_keeps_the_pending_path_and_still_exits_nonzero(self):
        code, out = run(self.root, "Q")
        self.assertRegex(line_of(out, CHECK), r"^PENDING H\b")
        self.assertNotIn("FATAL", out)
        self.assertEqual(code, 1)

    def test_wp_done_unset_means_all(self):
        code, out = run(self.root)
        self.assertRegex(line_of(out, CHECK), r"^FAIL\b")
        self.assertNotIn("PENDING", out)
        self.assertEqual(code, 1)

    def test_wp_done_all_makes_the_same_failure_fail(self):
        code, out = run(self.root, "ALL")
        self.assertRegex(line_of(out, CHECK), r"^FAIL\b")
        self.assertEqual(code, 1)
        self.assertNotIn("PENDING", out)
        n = len(re.findall(r"^(?:PASS|FAIL)\b", out, re.M))
        self.assertRegex(out.strip().splitlines()[-1], r"^\d+/%d checks passed$" % n)

    def test_listed_package_is_landed(self):
        code, out = run(self.root, "H")
        self.assertRegex(line_of(out, CHECK), r"^FAIL\b")


class DeletedFile(unittest.TestCase):
    def test_deleting_a_manifest_file_exits_nonzero_with_wp_done_unset(self):
        tmp = Path(tempfile.mkdtemp(prefix="wd-del-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        shutil.copytree(REPO, tmp, ignore=shutil.ignore_patterns("__pycache__", ".git"), dirs_exist_ok=True)
        (tmp / "plugins" / "agent-hub" / "refs" / "gates.md").unlink()
        code, out = run(tmp)
        self.assertNotEqual(code, 0)
        self.assertNotIn("PENDING", out)
        line = line_of(out, "tree_matches_manifest")
        self.assertRegex(line, r"^FAIL\b")
        self.assertIn("missing: plugins/agent-hub/refs/gates.md", out)


if __name__ == "__main__":
    unittest.main()
