"""Tests for tools/store_checks.py: each of the four store checks is green on a clean store, red on one planted violation,
green again once the violation is undone. Stores are built in temp dirs."""
import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import store_checks  # noqa: E402

TEXT = "<!-- owned head: proposal only, never writes agents -->\nbody\n"
NOTICE = "Copyright (c) 2025 Fixture Holder"


class StoreCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.store = self.root / "store"
        (self.store / "demo").mkdir(parents=True)
        self.text = self.store / "demo" / "text.md"
        self.text.write_text(TEXT, encoding="utf-8")
        self.notices = self.root / "THIRD_PARTY_NOTICES.md"
        self.notices.write_text(f"demo: {NOTICE}\n", encoding="utf-8")
        self.row = {
            "id": "demo", "kind": "skill", "origin": "fixture", "licence": "MIT", "notice": NOTICE,
            "files": [{"path": "text.md", "sha256": hashlib.sha256(TEXT.encode()).hexdigest(), "lines": 2}],
            "signal": {"files": ["tsconfig.json"], "deps": [], "task": "x"}, "roles": ["implement"],
            "side_effects": "none", "guard": None, "status": "ready", "unblock": None,
        }
        self.save()

    def save(self):
        (self.store / "catalog.yaml").write_text(yaml.safe_dump([self.row]), encoding="utf-8")

    def run_check(self, name):
        fn = getattr(store_checks, name)
        return fn(self.store, self.notices) if name == "store_licensed" else fn(self.store)


class NoExec(StoreCase):
    def test_clean_green(self):
        self.assertEqual(store_checks.store_no_exec(self.store), [])

    def test_sh_file_red_then_green(self):
        sh = self.store / "demo" / "run.sh"
        sh.write_text("echo hi\n")
        self.assertTrue(store_checks.store_no_exec(self.store))
        sh.unlink()
        self.assertEqual(store_checks.store_no_exec(self.store), [])

    def test_other_script_extensions_and_exec_bit_red(self):
        for ext in (".js", ".mjs", ".cjs", ".ts", ".py"):
            p = self.store / "demo" / f"x{ext}"
            p.write_text("1")
            self.assertTrue(store_checks.store_no_exec(self.store), ext)
            p.unlink()
        self.text.chmod(0o755)
        self.assertTrue(store_checks.store_no_exec(self.store))
        self.text.chmod(0o644)
        self.assertEqual(store_checks.store_no_exec(self.store), [])


class Pinned(StoreCase):
    def test_clean_green(self):
        self.assertEqual(store_checks.store_pinned(self.store), [])

    def test_one_changed_byte_red_then_green(self):
        self.text.write_text(TEXT.replace("body", "bodz"), encoding="utf-8")
        self.assertTrue(store_checks.store_pinned(self.store))
        self.text.write_text(TEXT, encoding="utf-8")
        self.assertEqual(store_checks.store_pinned(self.store), [])


class GuardPresent(StoreCase):
    def test_none_needs_no_guard(self):
        self.assertEqual(store_checks.store_guard_present(self.store), [])

    def test_side_effects_without_guard_red_then_green(self):
        self.row["side_effects"] = "writes files"
        self.save()
        self.assertTrue(store_checks.store_guard_present(self.store))
        self.row["guard"] = "proposal only; never writes agents or skills"
        self.save()
        self.assertEqual(store_checks.store_guard_present(self.store), [])

    def test_guard_without_owned_head_red(self):
        self.row.update(side_effects="writes files", guard="proposal only")
        self.text.write_text("body only\n", encoding="utf-8")
        self.save()
        self.assertTrue(store_checks.store_guard_present(self.store))


class Licensed(StoreCase):
    def test_clean_green(self):
        self.assertEqual(self.run_check("store_licensed"), [])

    def test_ready_without_licence_red_then_green(self):
        self.row["licence"] = None
        self.save()
        self.assertTrue(self.run_check("store_licensed"))
        self.row["licence"] = "Apache-2.0"
        self.save()
        self.assertEqual(self.run_check("store_licensed"), [])

    def test_licence_outside_allowlist_and_missing_notice_red(self):
        self.row["licence"] = "GPL-3.0"
        self.save()
        self.assertTrue(self.run_check("store_licensed"))
        self.row["licence"] = "MIT"
        self.save()
        self.notices.write_text("nothing here\n", encoding="utf-8")
        self.assertTrue(self.run_check("store_licensed"))

    def test_non_ready_row_needs_no_licence(self):
        self.row.update(status="blocked_licence", licence=None)
        self.save()
        self.assertEqual(self.run_check("store_licensed"), [])


if __name__ == "__main__":
    unittest.main()
