"""Tests for tools/scrub_check.py. Samples are joined at run time so this file holds no trace itself,
and private patterns come from planted temp files, never the owner's real one.
Run: python3 -m unittest tests.tools.test_scrub_check  (also collected by pytest)."""
import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import scrub_check  # noqa: E402

HOME = "/Us" + "ers/" + "jdoe"
FLEET = "~/." + "claude/" + "agents/x.md"
CITE_USER = "user 2026" + "-10-22"
CITE_Q = "Q" + "31"
CITE_ADR = "docs/" + "adr/003.md"
VI = "ti\u1ebfng vi\u1ec7t"
SAMPLES = {  # class -> (flagged, passes)
    "abs_home": (f"see {HOME}/work", "see /Users/<name>/work and /usr/local/bin"),
    "fleet_path": (f"read {FLEET}", "read ~/." + "claude/" + "memory/x.md"),
    "decision_cite": (f"rule ({CITE_Q})", "rule (see the spec) at 2026-10-22"),
    "language": (f"note: {VI}", "plain English only"),
}


class Case(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.tmp = Path(self._td.name)
        self.tree = self.tmp / "tree"
        self.tree.mkdir()
        self.private = self.tmp / "private.txt"

    def put(self, rel, text, base=None, mode="w"):
        p = (base or self.tree) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if mode == "wb":
            p.write_bytes(text)
        else:
            p.write_text(text, encoding="utf-8")
        return p

    def planted(self, *lines, draft=False):
        head = ["# agent-hub scrub-private DRAFT: remove this line after review"] if draft else ["# confirmed"]
        self.private.write_text("\n".join(head + list(lines)) + "\n")

    def run_tool(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = scrub_check.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def root_scan(self, *extra):
        return self.run_tool("--root", str(self.tree), "--private", str(self.private), *extra)


class ClassTests(Case):
    def test_each_class_flags_its_sample_and_passes_its_clean_one(self):
        self.planted("zed-corp")
        samples = dict(SAMPLES)
        samples["private"] = ("works at Zed-Corp now", "works at nobody now")
        for cls, (bad, good) in samples.items():
            with self.subTest(cls=cls):
                self.put("f.txt", bad + "\n")
                code, out, _ = self.root_scan()
                self.assertEqual(code, 1)
                self.assertIn(f"f.txt:1 {cls} ", out)
                self.put("f.txt", good + "\n")
                code, out, _ = self.root_scan()
                self.assertEqual(code, 0, out)

    def test_other_decision_forms_and_windows_home(self):
        for bad in (CITE_USER, CITE_ADR, "ADR-" + "007", "(FP-" + "3)", "C:\\Us" + "ers\\jdoe\\x"):
            self.put("f.txt", f"a {bad} b\n")
            self.assertEqual(self.root_scan()[0], 1, bad)

    def test_regex_private_line(self):
        self.planted("re:host-\\d+\\.internal")
        self.put("f.txt", "ssh host-12.internal\n")
        self.assertIn("private", self.root_scan()[1])

    def test_allowlisted_user_data_path_and_marker_line_not_reported(self):
        self.planted("zed-corp")
        self.put("f.txt", "kept in ~/." + "claude/" + "memory/notes and ~/." + "claude/" + "settings.json\n"
                 f"{HOME}/x zed-corp {VI} scrub-allow: demo text\n")
        code, out, _ = self.root_scan()
        self.assertEqual(code, 0, out)

    def test_findings_sorted_with_counts_line(self):
        self.planted("zed-corp")
        self.put("b.txt", f"{HOME}\n")
        self.put("a.txt", f"x\n{HOME}\nzed-corp\n")
        code, out, _ = self.root_scan()
        lines = out.splitlines()
        self.assertEqual(code, 1)
        self.assertEqual([l.split()[0] for l in lines[:3]], ["a.txt:2", "a.txt:3", "b.txt:1"])
        self.assertIn("findings: 3 in 2 files", out)
        self.assertIn("classes: abs_home=2 private=1", out)


class FileTests(Case):
    def test_empty_file_skipped_and_binary_reported_unless_allowlisted(self):
        self.planted("zed-corp")
        self.put("empty.txt", "")
        self.put("img.bin", b"\x89PNG\0\0data", mode="wb")
        code, out, _ = self.root_scan()
        self.assertEqual(code, 1)
        self.assertIn("img.bin:1 binary_unscanned", out)
        self.assertNotIn("empty.txt", out)
        pats = self.tmp / "patterns.yaml"
        pats.write_text("classes: {}\nallow_binary_paths: ['img.bin']\n")
        code, out, _ = self.root_scan("--patterns", str(pats))
        self.assertEqual(code, 0, out)

    def test_root_scans_only_that_dir_and_skips_dot_git(self):
        self.planted("zed-corp")
        self.put("in.txt", f"{HOME}\n")
        self.put(".git/hooks/x", f"{HOME}\n")
        self.put("outside.txt", f"{HOME}\n", base=self.tmp)
        code, out, _ = self.root_scan()
        self.assertEqual(code, 1)
        self.assertIn("in.txt:1", out)
        self.assertNotIn("outside.txt", out)
        self.assertNotIn(".git", out)
        self.assertIn("scanned: 1", out)

    def test_plan_id_in_a_code_comment_only(self):
        self.planted("zed-corp")
        tid = "W1-" + "T1"
        self.put("tests/x.py", "def test_a(self):  # TC-" + "W" + "2-T2-1\n" + f"t = 'tasks/W1/{tid}.yaml'\n")
        self.put("docs/a.md", f"see {tid}\n")
        code, out, _ = self.root_scan()
        self.assertEqual(code, 1)
        self.assertEqual([l.split(" ")[:2] for l in out.splitlines() if l.startswith(("tests/", "docs/"))],
                         [["tests/x.py:1", "plan_id"]])

    def test_patterns_file_is_skipped_by_default_allowlist(self):
        self.planted("zed-corp")
        self.put("tools/scrub_patterns.yaml", f"{HOME}\n")
        self.assertEqual(self.root_scan()[0], 0)


class PrivateFileTests(Case):
    def test_missing_private_file_warns_once_and_scan_continues(self):
        self.put("f.txt", f"{HOME}\n")
        code, out, err = self.root_scan()
        self.assertEqual(code, 1)
        self.assertEqual(err.count("warning"), 1)
        self.assertIn(str(self.private), err)
        self.assertIn("abs_home", out)

    def test_require_private_exits_2_naming_file_and_reason(self):
        self.put("f.txt", f"{HOME}\n")
        code, out, err = self.root_scan("--require-private")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("missing", err)
        self.assertIn(str(self.private), err)
        self.private.write_text("# only a comment\n\n")
        code, out, err = self.root_scan("--require-private")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("no pattern line", err)
        self.planted("zed-corp", draft=True)
        code, out, err = self.root_scan("--require-private")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("DRAFT", err)
        self.assertIn(str(self.private), err)
        self.planted("zed-corp")
        self.assertEqual(self.root_scan("--require-private")[0], 1)

    def test_invalid_private_regex_is_exit_2(self):
        self.planted("re:(")
        self.put("f.txt", "x\n")
        code, _, err = self.root_scan()
        self.assertEqual(code, 2)
        self.assertIn(":2:", err)
        self.planted("re:zed-sec(")
        code, _, err = self.root_scan()
        self.assertEqual(code, 2)
        self.assertNotIn("zed-sec", err)

    def test_allow_literal_suppresses_only_that_private_value(self):
        self.planted("zed-owner", "zed-corp")
        self.put("f.txt", f"zed-owner zed-corp {HOME}\n")
        code, out, err = self.root_scan("--allow-literal", "Zed-Owner")
        self.assertEqual(code, 1)
        self.assertIn("abs_home=1 private=1", out)
        self.assertNotIn("zed-", (out + err).lower())
        code, out, err = self.root_scan()
        self.assertIn("private=2", out)
        self.assertNotIn("zed-", (out + err).lower())

    def test_private_value_never_printed(self):
        self.planted("zed-corp", "re:jd[o]e")
        self.put("f.txt", f"Zed-Corp here\n{HOME}/x\n")
        code, out, err = self.root_scan()
        self.assertEqual(code, 1)
        self.assertIn("f.txt:1 private [redacted]", out)
        line2 = next(l for l in out.splitlines() if l.startswith("f.txt:2 abs_home "))
        self.assertIn("[redacted]", line2)
        for s in (out, err):
            self.assertNotIn("zed-corp", s.lower())
            self.assertNotIn("jdoe", s)


class RepoModeTests(Case):
    def test_repo_mode_equals_git_ls_files_co_exclude_standard(self):
        self.planted("zed-corp")
        repo = self.tmp / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        trace = f"{HOME}\n"
        self.put("CLAUDE.md", trace, base=repo)
        self.put(".github/workflows/ci.yml", trace, base=repo)
        self.put("notes/untracked.txt", trace, base=repo)
        self.put("ignored/secret.txt", trace, base=repo)
        self.put(".gitignore", "ignored/\n", base=repo)
        self.put("clean.txt", "fine\n", base=repo)
        code, out, _ = self.run_tool("--repo", str(repo), "--private", str(self.private))
        self.assertEqual(code, 1)
        hit = {l.split(":")[0] for l in out.splitlines() if " abs_home " in l}
        self.assertEqual(hit, {"CLAUDE.md", ".github/workflows/ci.yml", "notes/untracked.txt"})
        self.assertIn("scanned: 5", out)

    def test_not_a_git_repo_is_exit_2(self):
        self.planted("zed-corp")
        code, _, err = self.run_tool("--repo", str(self.tree), "--private", str(self.private))
        self.assertEqual(code, 2)
        self.assertIn("git ls-files", err)


if __name__ == "__main__":
    unittest.main()
