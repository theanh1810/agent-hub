"""Tests for scripts/review-packet.py: the table join, the base lookup, the exit contract and the diff-only copy."""
import datetime
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
from contextlib import redirect_stderr
import sys

import yaml

SCRIPT = Path(__file__).resolve().parents[2] / 'plugins' / 'agent-hub' / 'scripts' / 'review-packet.py'
sys.path.insert(0, str(SCRIPT.parent))
from plan_paths import ephemeral_dir  # noqa: E402
spec = importlib.util.spec_from_file_location('review_packet', SCRIPT)
RP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RP)


def put(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def dump(path, data):
    put(path, yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


class Fixture:
    """root/docs/plan/demo with tasks T1 (edits a.txt and b.txt) and T2 (creates c.txt); backups in root/bk/T1"""

    def __init__(self, commands=True, ac_check=True, at='2020-01-01T00:00:00+00:00', where='docs/plan/demo'):
        self.tmp = tempfile.TemporaryDirectory(prefix='review-packet-')
        self.root = Path(self.tmp.name)
        self.plan = self.root / where
        self.bk = self.root / 'bk'
        put(self.bk / 'T1/a.txt', 'one\ntwo\n')
        put(self.bk / 'T1/b.txt', 'alpha\nbeta\n')
        put(self.root / 'a.txt', 'one\nTWO\n')
        put(self.root / 'b.txt', 'alpha\nBETA\n')
        put(self.root / 'c.txt', 'new\n')
        run = [{'cmd': 'pytest a', 'exit': 0, 'evidence_path': 'e1', 'tc_id': 'TC-T1-1'}] if commands else []
        dump(self.plan / 'plan.yaml', {
            'plan_id': 'demo', 'approval': {'by': 'user: go ahead, verbatim', 'fingerprint': 'x', **({'at': at} if at else {})},
            'validation_strategy': {'review_deep_paths': [{'path': 'b.txt', 'section': None, 'reason': 'risky'}]},
            'tasks': [{'id': 'T1', 'wave': 'W1', 'file': 'tasks/W1/T1.yaml', 'depends_on': []},
                      {'id': 'T2', 'wave': 'W1', 'file': 'tasks/W1/T2.yaml', 'depends_on': []}]})
        dump(self.plan / 'tasks/W1/T1.yaml', {
            'id': 'T1', 'acceptance_criteria': ['AC-1: a changes'],
            'files': [{'path': 'a.txt', 'change': 'edit', 'why': 'w'}, {'path': 'b.txt', 'change': 'edit', 'why': 'w'}],
            'test_cases': [{'id': 'TC-T1-1', 'covers_acceptance': 'T1/AC-1'}],
            'result': {'commands': run, 'ac_check': [{'ac': 'AC-1', 'met': True, 'evidence': ['a.txt:2'], 'tc_ids': ['TC-T1-1'],
                                                       'note': 'a changed'}] if ac_check else None}})
        dump(self.plan / 'tasks/W1/T2.yaml', {
            'id': 'T2', 'acceptance_criteria': ['AC-1: c exists'],
            'files': [{'path': 'c.txt', 'change': 'create', 'why': 'w'}],
            'test_cases': [{'id': 'TC-T2-1', 'covers_acceptance': 'T2/AC-1'}],
            'result': {'commands': [{'cmd': 'test -f c.txt', 'exit': 0, 'evidence_path': 'e2', 'tc_id': 'TC-T2-1'}],
                       'ac_check': [{'ac': 'AC-1', 'met': False, 'evidence': [], 'tc_ids': ['TC-T2-1'],
                                     'note': 'c.txt not yet checked'}] if ac_check else None}})
        self.out = self.root / 'out'
        self.only = self.root / 'diff-only.md'

    def run(self, *extra):
        with redirect_stderr(io.StringIO()):
            return RP.main([str(self.plan), '--round', '0', '--backups', str(self.bk), '--out-dir', str(self.out),
                            '--diff-only-out', str(self.only), *extra])

    def packet(self):
        return (self.out / 'review-packet-r0.md').read_text(encoding='utf-8')


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        self.addCleanup(self.fx.tmp.cleanup)

    def test_table_join_and_deep_first(self):
        self.assertEqual(self.fx.run(), 0)
        text = self.fx.packet()
        self.assertIn('| T1 | AC-1 | TC-T1-1 | pytest a | 0 | true | a.txt:2 | a changed |', text)
        self.assertIn('| T2 | AC-1 | TC-T2-1 | test -f c.txt | 0 | false |  | c.txt not yet checked |', text)
        self.assertIn('+TWO', text)
        self.assertLess(text.index('### b.txt DEEP (whole file: risky)'), text.index('### a.txt'))
        self.assertEqual(oct((self.fx.out / 'review-packet-r0.md').stat().st_mode & 0o777), '0o666' if os.name == 'nt' else '0o644')

    def test_created_path_diffs_against_empty(self):
        self.fx.run()
        self.assertIn('+new', self.fx.packet())
        self.assertIn('created: diffs against empty', self.fx.packet())

    def test_missing_base_prints_no_base_and_exits_1(self):
        (self.fx.bk / 'T1/a.txt').unlink()
        self.assertEqual(self.fx.run(), 1)
        self.assertIn('NO BASE', self.fx.packet())

    def test_case_without_command_row_is_not_run(self):
        fx = Fixture(commands=False)
        self.addCleanup(fx.tmp.cleanup)
        self.assertEqual(fx.run(), 1)
        self.assertIn('| T1 | AC-1 | TC-T1-1 | not run |  | true | a.txt:2 | a changed |', fx.packet())

    def test_diff_only_file_carries_no_plan_text(self):
        self.fx.run()
        only = self.fx.only.read_text(encoding='utf-8')
        for token in ('AC-', 'TC-', 'T1', 'T2', 'risky', 'demo'):
            self.assertNotIn(token, only)
        self.assertIn('+TWO', only)

    def test_base_dir_diffs_only_the_fix_round_change(self):
        fix = self.fx.root / 'fix'
        put(fix / 'a.txt', 'one\nTWO\n')                      # copy taken before the fix round
        put(self.fx.root / 'a.txt', 'one\nTWO\nthree\n')      # the fix round's edit
        self.assertEqual(self.fx.run('--base-dir', str(fix)), 0)
        only = self.fx.only.read_text(encoding='utf-8')
        self.assertIn('+three', only)
        self.assertNotIn('-two', only)                        # the first task's change is not re-shown
        self.assertNotIn('b.txt', only)                       # no copy under --base-dir: left out
        self.assertNotIn('NO BASE', self.fx.packet())

    def test_base_dir_shows_a_fix_path_in_no_task(self):
        fix = self.fx.root / 'fix'
        put(fix / 'd.txt', 'd\n')                             # d.txt is in no task's files[]
        put(self.fx.root / 'd.txt', 'D\n')
        self.assertEqual(self.fx.run('--base-dir', str(fix)), 0)
        only = self.fx.only.read_text(encoding='utf-8')
        self.assertIn('### d.txt', only)
        self.assertIn('+D', only)

    def test_base_dir_diffs_a_file_created_in_the_fix_round_against_empty(self):
        fix = self.fx.root / 'fix'
        fix.mkdir()
        dump(self.fx.plan / 'errors.yaml', {'errors': [
            {'round': 1, 'analysis': {'fix_list': [{'id': 'FX-1-1', 'files': [{'path': 'g.txt'}]}]}}]})
        put(self.fx.root / 'g.txt', 'gee\n')                  # created by the fix round: no copy
        self.assertEqual(self.fx.run('--base-dir', str(fix)), 0)
        self.assertIn('+gee', self.fx.only.read_text(encoding='utf-8'))
        self.assertIn('created in fix round', self.fx.packet())

    def test_missing_base_dir_exits_1_with_no_base_row(self):
        self.assertEqual(self.fx.run('--base-dir', str(self.fx.root / 'nope')), 1)
        self.assertIn('NO BASE', self.fx.packet())
        self.assertIn('NO BASE', self.fx.only.read_text(encoding='utf-8'))

    def test_empty_fix_diff_exits_1(self):
        fix = self.fx.root / 'fix'
        fix.mkdir()                                           # no copy, no errors.yaml
        self.assertEqual(self.fx.run('--base-dir', str(fix)), 1)
        self.assertIn('NO BASE: empty fix diff', self.fx.packet())

    def test_absolute_files_path_diffs_against_its_backup(self):
        t1 = self.fx.plan / 'tasks/W1/T1.yaml'
        data = yaml.safe_load(t1.read_text(encoding='utf-8'))
        data['files'][0]['path'] = str(self.fx.root / 'a.txt')   # absolute, backup stays at bk/T1/a.txt
        dump(t1, data)
        self.assertEqual(self.fx.run(), 0)
        only = self.fx.only.read_text(encoding='utf-8')
        self.assertIn('-two', only)
        self.assertIn('+TWO', only)

    def test_unreadable_plan_exits_2(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(RP.main([str(self.fx.root / 'docs/plan/none'), '--round', '0']), 2)

    def test_plan_dir_outside_docs_exits_2(self):
        tmp = tempfile.TemporaryDirectory(prefix='review-packet-')
        self.addCleanup(tmp.cleanup)
        plan = Path(tmp.name) / 'elsewhere/demo'
        dump(plan / 'plan.yaml', {'plan_id': 'demo', 'tasks': []})
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(RP.main([str(plan), '--round', '0']), 2)
        self.assertIn('is not inside a docs/ folder', err.getvalue())

    def test_backup_copied_with_cp_c_after_approval_is_not_flagged(self):
        old = time.mktime((2019, 1, 1, 0, 0, 0, 0, 0, -1))
        os.utime(self.fx.bk / 'T1/a.txt', (old, old))
        self.fx.run()
        self.assertNotIn('OLDER THAN APPROVAL', self.fx.packet())

    def test_backup_folder_created_before_approval_is_flagged(self):
        fx = Fixture(at='2999-01-01T00:00:00+00:00')
        self.addCleanup(fx.tmp.cleanup)
        fx.run()
        self.assertIn('OLDER THAN APPROVAL', fx.packet())

    def test_write_leaves_no_temp_file_when_replace_fails(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        real = RP.os.replace
        def boom(*a, **k):
            raise OSError('replace failed')
        RP.os.replace = boom
        try:
            with self.assertRaises(OSError):
                RP.write(str(d / 'packet.md'), 'text')
        finally:
            RP.os.replace = real
        self.assertEqual([p.name for p in d.iterdir() if p.name.startswith('.review-packet-')], [])

    def test_approval_at_read_as_a_yaml_datetime_is_compared(self):
        fx = Fixture(at=datetime.datetime(2999, 1, 1, tzinfo=datetime.timezone.utc))
        self.addCleanup(fx.tmp.cleanup)
        fx.run()
        self.assertIn('OLDER THAN APPROVAL', fx.packet())

    def test_missing_approval_at_says_time_unknown_and_flags_nothing(self):
        fx = Fixture(at=None)
        self.addCleanup(fx.tmp.cleanup)
        fx.run()
        self.assertIn('Approval time unknown', fx.packet())
        self.assertNotIn('OLDER THAN APPROVAL', fx.packet())

    def test_diff_only_marks_a_deep_path_without_its_reason(self):
        self.fx.run()
        only = self.fx.only.read_text(encoding='utf-8')
        self.assertIn('### b.txt DEEP\n', only)
        self.assertNotIn('DEEP (', only)
        self.assertNotIn('risky', only)

    def delete_files(self, *names):
        t1 = yaml.safe_load((self.fx.plan / 'tasks/W1/T1.yaml').read_text())
        t1['files'] += [{'path': n, 'change': 'delete', 'why': 'w'} for n in names]
        dump(self.fx.plan / 'tasks/W1/T1.yaml', t1)

    def test_deleted_node_modules_file_is_one_line_in_both_outputs(self):
        put(self.fx.bk / 'T1/node_modules/pkg/index.js', 'BODY-ONE\nBODY-TWO\nBODY-THREE\n')
        self.delete_files('node_modules/pkg/index.js')
        self.fx.run()
        for text in (self.fx.packet(), self.fx.only.read_text(encoding='utf-8')):
            self.assertEqual(text.count('node_modules/pkg/index.js deleted (3 lines)'), 1)
            self.assertNotIn('BODY-', text)

    def test_deleted_file_outside_node_modules_keeps_its_content(self):
        put(self.fx.bk / 'T1/gone.txt', 'keepme\n')
        self.delete_files('gone.txt')
        self.fx.run()
        for text in (self.fx.packet(), self.fx.only.read_text(encoding='utf-8')):
            self.assertIn('-keepme', text)
            self.assertNotIn('deleted (', text)

    def test_glob_path_is_labelled_and_does_not_exit_1(self):
        t1 = yaml.safe_load((self.fx.plan / 'tasks/W1/T1.yaml').read_text())
        t1['files'].append({'path': 'logs/*.txt', 'change': 'edit', 'why': 'w'})
        dump(self.fx.plan / 'tasks/W1/T1.yaml', t1)
        self.assertEqual(self.fx.run(), 0)
        self.assertIn('| logs/*.txt | glob: not expanded |', self.fx.packet())
        for text in (self.fx.packet(), self.fx.only.read_text(encoding='utf-8')):
            self.assertIn('glob: not expanded, diff skipped', text)
            self.assertNotIn('NO BASE', text)

    def test_directory_path_expands_to_its_files(self):
        put(self.fx.bk / 'T1/d/x.txt', 'x1\n')
        put(self.fx.root / 'd/x.txt', 'x2\n')
        put(self.fx.root / 'd/y.txt', 'y\n')
        t1 = yaml.safe_load((self.fx.plan / 'tasks/W1/T1.yaml').read_text())
        t1['files'].append({'path': 'd', 'change': 'edit', 'why': 'w'})
        dump(self.fx.plan / 'tasks/W1/T1.yaml', t1)
        self.fx.run()
        text = self.fx.packet()
        self.assertIn('### d/x.txt', text)
        self.assertIn('### d/y.txt', text)

    def test_git_base_uses_argv_show(self):
        root = self.fx.root
        if shutil.which('git') is None:
            self.skipTest('git missing')
        git = ['git', '-C', str(root), '-c', 'user.name=t', '-c', 'user.email=t@t']
        subprocess.run(git + ['init', '-q'], check=True)
        put(root / 'g.txt', 'g1\n')
        subprocess.run(git + ['add', 'g.txt'], check=True)
        subprocess.run(git + ['commit', '-q', '-m', 'base'], check=True)
        sha = subprocess.run(git + ['rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
        put(root / 'g.txt', 'g2\n')
        t1 = yaml.safe_load((self.fx.plan / 'tasks/W1/T1.yaml').read_text())
        t1['files'].append({'path': 'g.txt', 'change': 'edit', 'why': 'w'})
        t1['result']['baseline'] = {'head': sha, 'dirty_paths': []}
        dump(self.fx.plan / 'tasks/W1/T1.yaml', t1)
        self.fx.run()
        text = self.fx.packet()
        self.assertIn(f'git {sha}', text)
        self.assertIn('-g1', text)
        self.assertIn('+g2', text)

    def test_git_base_directory_lists_each_file_once(self):
        root = self.fx.root
        if shutil.which('git') is None:
            self.skipTest('git missing')
        git = ['git', '-C', str(root), '-c', 'user.name=t', '-c', 'user.email=t@t']
        subprocess.run(git + ['init', '-q'], check=True)
        put(root / 'd/x.txt', 'x1\n')
        subprocess.run(git + ['add', 'd/x.txt'], check=True)
        subprocess.run(git + ['commit', '-q', '-m', 'base'], check=True)
        sha = subprocess.run(git + ['rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
        put(root / 'd/x.txt', 'x2\n')
        put(root / 'd/y.txt', 'y\n')
        t1 = yaml.safe_load((self.fx.plan / 'tasks/W1/T1.yaml').read_text())
        t1['files'].append({'path': 'd', 'change': 'edit', 'why': 'w'})
        t1['result']['baseline'] = {'head': sha, 'dirty_paths': []}
        dump(self.fx.plan / 'tasks/W1/T1.yaml', t1)
        self.fx.run()
        text = self.fx.packet()
        self.assertEqual([ln for ln in text.splitlines() if ln.startswith('### d')], ['### d/x.txt', '### d/y.txt'])
        self.assertIn('-x1', text)
        self.assertIn('+x2', text)


class PacketLocationTests(unittest.TestCase):
    """without --out-dir the packet goes to ephemeral_dir(root, plan_id), i.e. <root>/.cm-tmp/<plan_id>/; the change folder and any
    legacy sidecar get nothing (review-packet writes nothing in the change folder)"""

    def build(self, where, old_sidecar=False):
        fx = Fixture(where=where)
        self.addCleanup(fx.tmp.cleanup)
        if old_sidecar:
            (fx.root / 'docs/plan/demo').mkdir(parents=True)
        with redirect_stderr(io.StringIO()):
            RP.main([str(fx.plan), '--round', '3', '--backups', str(fx.bk)])
        return fx

    def test_a_docs_changes_plan_writes_its_packet_under_cm_tmp(self):
        fx = self.build('docs/changes/demo')
        self.assertTrue((ephemeral_dir(fx.root, 'demo') / 'review-packet-r3.md').is_file())
        self.assertFalse((fx.plan / 'reviews').exists())
        self.assertFalse((fx.root / 'docs/plan').exists())

    def test_a_legacy_plan_with_an_old_sidecar_gets_no_packet_there(self):  # legacy is read, never written
        fx = self.build('docs/specs/changes/demo', old_sidecar=True)
        self.assertTrue((ephemeral_dir(fx.root, 'demo') / 'review-packet-r3.md').is_file())
        self.assertFalse((fx.root / 'docs/plan/demo/reviews').exists())
        self.assertFalse((fx.plan / 'reviews').exists())

    def test_a_legacy_plan_folder_with_reviews_keeps_it_untouched(self):
        fx = Fixture(where='docs/changes/demo')
        self.addCleanup(fx.tmp.cleanup)
        put(fx.plan / 'reviews/review-packet-r1.md', 'old packet\n')
        with redirect_stderr(io.StringIO()):
            RP.main([str(fx.plan), '--round', '3', '--backups', str(fx.bk)])
        self.assertEqual((fx.plan / 'reviews/review-packet-r1.md').read_text(encoding='utf-8'), 'old packet\n')
        self.assertEqual(sorted(x.name for x in (fx.plan / 'reviews').iterdir()), ['review-packet-r1.md'])
        self.assertTrue((ephemeral_dir(fx.root, 'demo') / 'review-packet-r3.md').is_file())


class AcCheckTests(unittest.TestCase):
    def test_ac_without_entry_prints_no_entry_and_exits_1(self):
        fx = Fixture(ac_check=False)
        self.addCleanup(fx.tmp.cleanup)
        self.assertEqual(fx.run(), 1)
        self.assertIn('| T1 | AC-1 | TC-T1-1 | pytest a | 0 | no entry |  |  |', fx.packet())

    def test_ac_check_that_is_not_a_list_counts_as_no_entry(self):
        fx = Fixture()
        self.addCleanup(fx.tmp.cleanup)
        t1 = yaml.safe_load((fx.plan / 'tasks/W1/T1.yaml').read_text())
        t1['result']['ac_check'] = 'done'
        dump(fx.plan / 'tasks/W1/T1.yaml', t1)
        self.assertEqual(fx.run(), 1)
        self.assertIn('no entry', fx.packet())

    def test_diff_only_file_still_has_no_ac_text(self):
        fx = Fixture()
        self.addCleanup(fx.tmp.cleanup)
        fx.run()
        only = fx.only.read_text(encoding='utf-8')
        for token in ('AC-', 'a changed', 'no entry', 'met'):
            self.assertNotIn(token, only)


if __name__ == '__main__':
    unittest.main()
