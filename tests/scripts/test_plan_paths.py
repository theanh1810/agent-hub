"""Tests for scripts/plan_paths.py and scripts/plan-locate.py: the location constants and the change-folder lookup."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / 'plugins' / 'agent-hub' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import plan_paths as PP  # noqa: E402
spec = importlib.util.spec_from_file_location('plan_locate', SCRIPTS / 'plan-locate.py')
PL = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PL)   # a hyphenated file name: loaded by path


def put(root, rel, text='x\n'):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')
    return p


class RootCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='plan-paths-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()


class ConstantTests(unittest.TestCase):
    def test_the_location_constants(self):
        self.assertEqual((PP.CHANGES_DIR, PP.LIVE_SPECS_DIR, PP.DEBT_FILE, PP.GLOSSARY_FILE),
                         ('openspec/changes', 'openspec/specs', 'openspec/_debt.md', 'openspec/glossary.md'))
        self.assertEqual(PP.SCOPE_FILE, 'openspec/scope.md')
        self.assertEqual((PP.TASKS, PP.PLAN_VI, PP.APPROVAL, PP.ERRORS, PP.QUESTIONS, PP.REVIEWS_DIR),
                         ('tasks.md', 'plan.vi.md', 'approval.md', 'errors.yaml', 'questions.md', 'reviews'))


class ChangeDirTests(RootCase):
    def test_active_archive_and_dated_archive_resolve(self):
        for rel, cid in (('openspec/changes/n1', 'n1'), ('openspec/changes/archive/n2', 'n2'), ('openspec/changes/archive/2026-01-02-n3', 'n3')):
            with self.subTest(rel=rel):
                put(self.root, f'{rel}/tasks.md')
                self.assertEqual(PP.change_dir(self.root, cid), self.root / rel)

    def test_unknown_id_is_none_two_folders_and_bad_id_raise(self):
        self.assertIsNone(PP.change_dir(self.root, 'absent'))
        put(self.root, 'openspec/changes/n5/tasks.md')
        put(self.root, 'openspec/changes/archive/n5/tasks.md')
        with self.assertRaisesRegex(ValueError, r'^n5: expected one change folder, found 2: '):
            PP.change_dir(self.root, 'n5')
        with self.assertRaisesRegex(ValueError, 'lowercase kebab-case'):
            PP.change_dir(self.root, 'Bad_ID')

    def test_workspace_root_and_live_specs(self):
        folder = put(self.root, 'openspec/changes/w1/tasks.md').parent
        self.assertEqual(Path(PP.workspace_root(folder)), self.root)
        self.assertEqual(PP.live_specs(folder), self.root / 'openspec/specs')
        with self.assertRaises(ValueError):
            PP.workspace_root('/')

    def test_ephemeral_dir_is_not_created(self):
        self.assertEqual(PP.ephemeral_dir(self.root, 'demo'), self.root / '.cm-tmp' / 'demo')
        self.assertFalse((self.root / '.cm-tmp').exists())


class LocateTests(RootCase):
    def test_locate_reports_the_change_files(self):
        put(self.root, 'openspec/changes/p1/tasks.md')
        got = PL.locate(self.root, 'p1')
        self.assertEqual((got['plan_id'], got['tasks_ref'], got['plan_vi_ref'], got['archived']),
                         ('p1', str(self.root / 'openspec/changes/p1/tasks.md'), str(self.root / 'openspec/changes/p1/plan.vi.md'), False))
        put(self.root, 'openspec/changes/archive/p2/tasks.md')
        self.assertTrue(PL.locate(self.root, 'p2')['archived'])

    def test_a_workspace_path_named_archive_does_not_archive_a_live_change(self):
        shop = self.root / 'archive' / 'shop'
        put(shop, 'openspec/changes/live-one/tasks.md')
        put(shop, 'openspec/changes/archive/done-one/tasks.md')
        self.assertFalse(PL.locate(shop, 'live-one')['archived'])
        self.assertTrue(PL.locate(shop, 'done-one')['archived'])

    def test_a_folder_without_tasks_md_and_an_unknown_id_raise(self):
        put(self.root, 'openspec/changes/p3/proposal.md')
        for cid in ('p3', 'zzz'):
            with self.assertRaisesRegex(ValueError, 'expected one change folder with tasks.md'):
                PL.locate(self.root, cid)

    def test_cli_prints_json_and_exits_1_with_the_error_on_stderr(self):
        put(self.root, 'openspec/changes/c1/tasks.md')
        run = lambda cid: subprocess.run([sys.executable, str(SCRIPTS / 'plan-locate.py'), '--workspace', str(self.root), cid], capture_output=True, text=True)
        ok = run('c1')
        self.assertEqual((ok.returncode, json.loads(ok.stdout)['plan_id']), (0, 'c1'))
        bad = run('nope')
        self.assertEqual(bad.returncode, 1)
        self.assertTrue(bad.stderr.startswith('plan-locate: nope: expected one change folder'))


if __name__ == '__main__':
    unittest.main()
