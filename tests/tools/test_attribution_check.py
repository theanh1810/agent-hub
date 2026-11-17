"""Tests for tools/attribution_check.py (check quoted_passages_attributed), run on temp trees."""
import hashlib
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("attribution_check", REPO / "tools" / "attribution_check.py")
ac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ac)

UPSTREAM = [f"upstream rule line {i}: always state the evidence before the claim" for i in range(1, 13)]
UP_PATH = "skills/demo/SKILL.md"
ORIGIN = "acme/demo-pack"
PIN = "0123456789abcdef0123456789abcdef01234567"
NOTICE = f"# Third-party notices\n\n### {ORIGIN}\n\nMIT. Copyright (c) 2026 Acme.\n"
MARKER_FMT = ("<!-- vendored:begin id=b1 src={o}@{p}:{u}#L{a}-L{b} licence=MIT -->\n{body}\n"
              "<!-- vendored:end id=b1 -->\n")


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def block(lines, a=3, b=8, origin=ORIGIN):
    return MARKER_FMT.format(o=origin, p=PIN, u=UP_PATH, a=a, b=b, body="\n".join(lines))


class AttributionTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="wd-attr-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        up = "\n".join(UPSTREAM) + "\n"
        local = f"tools/upstream/acme-demo-pack/{UP_PATH}"
        write(self.root / local, up)
        sha = hashlib.sha256(up.encode()).hexdigest()
        write(self.root / "tools/upstream/manifest.yaml", (
            "version: 1\nsources:\n"
            f'  - origin: "{ORIGIN}"\n    pin: "{PIN}"\n    licence: "MIT"\n'
            f'    upstream_path: "{UP_PATH}"\n    local: "{local}"\n    sha256: "{sha}"\n    status: "pinned"\n'))
        write(self.root / "THIRD_PARTY_NOTICES.md", NOTICE)
        self.doc = self.root / "plugins/agent-hub/refs/rule.md"

    def problems(self):
        return ac.quoted_passages_attributed(self.root)

    def test_clean_tree_with_owned_text_only(self):
        write(self.doc, "Owned sentence one.\nOwned sentence two.\n")
        self.assertEqual(self.problems(), [])

    def test_marked_block_equal_to_upstream_is_green(self):
        write(self.doc, "Owned head.\n" + block(UPSTREAM[2:8]) + "Owned tail.\n")
        self.assertEqual(self.problems(), [])

    def test_uncredited_quote_is_red_then_green_when_marked(self):
        write(self.doc, "Owned head.\n" + "\n".join(UPSTREAM[4:7]) + "\nOwned tail.\n")
        got = self.problems()
        self.assertEqual(len(got), 1, got)
        self.assertIn("uncredited", got[0])
        self.assertIn("rule.md", got[0])
        write(self.doc, "Owned head.\n" + block(UPSTREAM[4:7], 5, 7) + "Owned tail.\n")
        self.assertEqual(self.problems(), [])

    def test_two_line_overlap_is_not_a_quote(self):
        write(self.doc, "\n".join(UPSTREAM[4:6]) + "\nOwned.\n")
        self.assertEqual(self.problems(), [])

    def test_one_changed_byte_inside_block_is_red_then_green(self):
        edited = list(UPSTREAM[2:8])
        edited[1] = edited[1].replace("always", "alwayz")
        write(self.doc, block(edited))
        got = self.problems()
        self.assertEqual(len(got), 1, got)
        self.assertIn("differs", got[0])
        write(self.doc, block(UPSTREAM[2:8]))
        self.assertEqual(self.problems(), [])

    def test_origin_without_notices_entry_is_red_then_green(self):
        write(self.root / "THIRD_PARTY_NOTICES.md", "# Third-party notices\n\n### other/pack\n")
        write(self.doc, block(UPSTREAM[2:8]))
        got = self.problems()
        self.assertEqual(len(got), 1, got)
        self.assertIn("THIRD_PARTY_NOTICES", got[0])
        write(self.root / "THIRD_PARTY_NOTICES.md", NOTICE)
        self.assertEqual(self.problems(), [])

    def test_block_naming_unknown_source_or_owed_row_is_red(self):
        write(self.doc, MARKER_FMT.format(o=ORIGIN, p=PIN, u="skills/none/SKILL.md", a=1, b=3, body="x\ny\nz"))
        self.assertIn("no manifest row", " ".join(self.problems()))
        man = self.root / "tools/upstream/manifest.yaml"
        man.write_text(man.read_text().replace('status: "pinned"', 'status: "owed"\n    owed_by: "H22a"'))
        write(self.doc, block(UPSTREAM[2:8]))
        self.assertIn("owed", " ".join(self.problems()))

    def test_tampered_pinned_copy_is_red(self):
        write(self.root / f"tools/upstream/acme-demo-pack/{UP_PATH}", "\n".join(UPSTREAM).replace("rule", "rulz") + "\n")
        self.assertIn("sha256", " ".join(self.problems()))

    def test_unterminated_block_is_red(self):
        write(self.doc, "<!-- vendored:begin id=b1 src=%s@%s:%s#L3-L8 licence=MIT -->\nline\n" % (ORIGIN, PIN, UP_PATH))
        self.assertIn("unterminated", " ".join(self.problems()))

    def test_quoted_in_credits_an_existing_file(self):
        write(self.doc, "\n".join(UPSTREAM[4:7]) + "\n")
        man = self.root / "tools/upstream/manifest.yaml"
        man.write_text(man.read_text() + '    quoted_in: [plugins/agent-hub/refs/*.md]\n')
        self.assertEqual(self.problems(), [])

    def test_main_exit_codes(self):
        write(self.doc, "\n".join(UPSTREAM[4:7]) + "\n")
        self.assertEqual(ac.main(["--root", str(self.root)]), 1)
        write(self.doc, "Owned.\n")
        self.assertEqual(ac.main(["--root", str(self.root)]), 0)


if __name__ == "__main__":
    unittest.main()
