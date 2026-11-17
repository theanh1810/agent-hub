"""Tests for scripts/review-packet.py: the task table, the base lookup, the exit contract and the diff-only copy."""
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parents[2] / 'plugins' / 'agent-hub' / 'scripts' / 'review-packet.py'
sys.path.insert(0, str(SCRIPT.parent))
from plan_paths import ephemeral_dir  # noqa: E402
spec = importlib.util.spec_from_file_location('review_packet', SCRIPT)
RP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RP)

TASKS = """# Tasks: demo

## Wave 1

- [ ] 1.1 Edit a and b
  Files: a.txt, b.txt
  Covers: Valid login
  Done when: a changes
  Test: unit

- [ ] 1.2 Create c
  Files: c.txt
  Covers: none
  Done when: c exists
  Test: none
"""


def put(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


class Fixture:
    """root/openspec/changes/demo with tasks 1.1 (edits a.txt and b.txt) and 1.2 (c.txt); backups in root/bk/demo/1.1"""

    def __init__(self, where='openspec/changes/demo'):
        self.tmp = tempfile.TemporaryDirectory(prefix='review-packet-')
        self.root = Path(self.tmp.name)
        self.plan = self.root / where
        self.bk = self.root / 'bk'
        put(self.plan / 'tasks.md', TASKS)
        put(self.bk / 'demo/1.1/a.txt', 'one\ntwo\n')
        put(self.bk / 'demo/1.1/b.txt', 'alpha\nbeta\n')
        put(self.bk / 'demo/1.2/c.txt', '')
        put(self.root / 'a.txt', 'one\nTWO\n')
        put(self.root / 'b.txt', 'alpha\nBETA\n')
        put(self.root / 'c.txt', 'new\n')
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

    def test_table_and_diffs(self):
        self.assertEqual(self.fx.run(), 0)
        text = self.fx.packet()
        self.assertIn('| 1.1 | Valid login | unit |', text)
        self.assertIn('| 1.2 | none | none |', text)
        self.assertIn('+TWO', text)
        self.assertIn('+new', text)
        self.assertEqual(oct((self.fx.out / 'review-packet-r0.md').stat().st_mode & 0o777), '0o666' if os.name == 'nt' else '0o644')

    def test_missing_base_prints_no_base_and_exits_1(self):
        (self.fx.bk / 'demo/1.1/a.txt').unlink()
        self.assertEqual(self.fx.run(), 1)
        self.assertIn('NO BASE', self.fx.packet())

    def test_diff_only_file_carries_no_plan_text(self):
        self.fx.run()
        only = self.fx.only.read_text(encoding='utf-8')
        for token in ('Valid login', '1.1', 'demo', 'Covers'):
            self.assertNotIn(token, only)
        self.assertIn('+TWO', only)

    def test_base_dir_diffs_only_the_fix_round_change(self):
        fix = self.fx.root / 'fix'
        put(fix / 'a.txt', 'one\nTWO\n')
        put(self.fx.root / 'a.txt', 'one\nTWO\nthree\n')
        self.assertEqual(self.fx.run('--base-dir', str(fix)), 0)
        only = self.fx.only.read_text(encoding='utf-8')
        self.assertIn('+three', only)
        self.assertNotIn('-two', only)
        self.assertNotIn('b.txt', only)

    def test_base_dir_diffs_a_file_created_in_the_fix_round_against_empty(self):
        fix = self.fx.root / 'fix'
        fix.mkdir()
        put(self.fx.plan / 'errors.yaml', yaml.safe_dump({'errors': [
            {'round': 1, 'analysis': {'fix_list': [{'id': 'FX-1-1', 'files': [{'path': 'g.txt'}]}]}}]}))
        put(self.fx.root / 'g.txt', 'gee\n')
        self.assertEqual(self.fx.run('--base-dir', str(fix)), 0)
        self.assertIn('+gee', self.fx.only.read_text(encoding='utf-8'))
        self.assertIn('created in fix round', self.fx.packet())

    def test_missing_base_dir_and_empty_fix_diff_exit_1(self):
        self.assertEqual(self.fx.run('--base-dir', str(self.fx.root / 'nope')), 1)
        self.assertIn('NO BASE', self.fx.packet())
        fix = self.fx.root / 'fix'
        fix.mkdir()
        self.assertEqual(self.fx.run('--base-dir', str(fix)), 1)
        self.assertIn('NO BASE: empty fix diff', self.fx.packet())

    def test_unreadable_change_and_folder_outside_openspec_exit_2(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(RP.main([str(self.fx.root / 'openspec/changes/none'), '--round', '0']), 2)
        tmp = tempfile.TemporaryDirectory(prefix='review-packet-')
        self.addCleanup(tmp.cleanup)
        put(Path(tmp.name) / 'elsewhere/demo/tasks.md', TASKS)
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(RP.main([str(Path(tmp.name) / 'elsewhere/demo'), '--round', '0']), 2)
        self.assertIn('is not inside an openspec/ workspace', err.getvalue())

    def test_deleted_node_modules_file_is_one_line_in_both_outputs(self):
        put(self.fx.bk / 'demo/1.1/node_modules/pkg/index.js', 'BODY-ONE\nBODY-TWO\nBODY-THREE\n')
        put(self.fx.plan / 'tasks.md', TASKS.replace('a.txt, b.txt', 'a.txt, node_modules/pkg/index.js'))
        self.fx.run()
        for text in (self.fx.packet(), self.fx.only.read_text(encoding='utf-8')):
            self.assertEqual(text.count('node_modules/pkg/index.js deleted (3 lines)'), 1)
            self.assertNotIn('BODY-', text)

    def test_glob_path_is_labelled_and_does_not_exit_1(self):
        put(self.fx.plan / 'tasks.md', TASKS.replace('a.txt, b.txt', 'a.txt, logs/*.txt'))
        self.assertEqual(self.fx.run(), 0)
        self.assertIn('| logs/*.txt | glob: not expanded |', self.fx.packet())
        self.assertNotIn('NO BASE', self.fx.packet())

    def test_directory_path_expands_to_its_files(self):
        put(self.fx.bk / 'demo/1.1/d/x.txt', 'x1\n')
        put(self.fx.root / 'd/x.txt', 'x2\n')
        put(self.fx.root / 'd/y.txt', 'y\n')
        put(self.fx.plan / 'tasks.md', TASKS.replace('a.txt, b.txt', 'a.txt, d'))
        self.fx.run()
        self.assertIn('### d/x.txt', self.fx.packet())
        self.assertIn('### d/y.txt', self.fx.packet())

    def test_git_base_ref_is_read_with_git_show(self):
        if shutil.which('git') is None:
            self.skipTest('git missing')
        root = self.fx.root
        git = ['git', '-C', str(root), '-c', 'user.name=t', '-c', 'user.email=t@t']
        subprocess.run(git + ['init', '-q'], check=True)
        put(root / 'g.txt', 'g1\n')
        subprocess.run(git + ['add', 'g.txt'], check=True)
        subprocess.run(git + ['commit', '-q', '-m', 'base'], check=True)
        sha = subprocess.run(git + ['rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
        put(root / 'g.txt', 'g2\n')
        put(self.fx.plan / 'tasks.md', TASKS.replace('a.txt, b.txt', 'a.txt, g.txt'))
        self.fx.run('--base-ref', sha)
        self.assertIn(f'git {sha} (.)', self.fx.packet())
        self.assertIn('-g1', self.fx.packet())
        self.assertIn('+g2', self.fx.packet())

    def test_a_backup_of_another_plan_with_the_same_task_id_is_ignored(self):
        shutil.rmtree(self.fx.bk / 'demo')
        put(self.fx.bk / '1.1/a.txt', 'stale from another plan\n')
        self.assertEqual(self.fx.run(), 1)
        self.assertNotIn('stale from another plan', self.fx.packet())
        self.assertIn('NO BASE', self.fx.packet())

    def _git_repo(self):
        root = self.fx.root
        git = ['git', '-C', str(root), '-c', 'user.name=t', '-c', 'user.email=t@t']
        subprocess.run(git + ['init', '-q'], check=True)
        put(root / 'g.txt', 'g1\n')
        subprocess.run(git + ['add', 'g.txt'], check=True)
        subprocess.run(git + ['commit', '-q', '-m', 'base'], check=True)
        sha = subprocess.run(git + ['rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
        put(root / 'g.txt', 'g2\n')
        put(self.fx.plan / 'tasks.md', TASKS.replace('a.txt, b.txt', 'g.txt'))
        return sha

    def test_base_ref_in_a_git_work_tree_beats_a_backup(self):
        if shutil.which('git') is None:
            self.skipTest('git missing')
        sha = self._git_repo()
        put(self.fx.bk / 'demo/1.1/g.txt', 'backup body\n')
        self.fx.run('--base-ref', sha)
        self.assertIn(f'git {sha}', self.fx.packet())
        self.assertIn('-g1', self.fx.packet())
        self.assertNotIn('backup body', self.fx.packet())

    def test_invalid_base_ref_exits_2_and_writes_nothing(self):
        if shutil.which('git') is None:
            self.skipTest('git missing')
        self._git_repo()
        err = io.StringIO()
        with redirect_stderr(err):
            code = RP.main([str(self.fx.plan), '--round', '0', '--backups', str(self.fx.bk), '--out-dir', str(self.fx.out), '--base-ref', 'mian'])
        self.assertEqual(code, 2)
        self.assertIn('mian', err.getvalue())
        self.assertFalse(self.fx.out.exists())

    def test_path_outside_the_workspace_is_never_read(self):
        outside = Path(tempfile.mkdtemp(prefix='rp-outside-'))
        self.addCleanup(shutil.rmtree, outside, True)
        put(outside / 'secret.txt', 'TOP-SECRET-BODY\n')
        for name in (str(outside / 'secret.txt'), '../' + outside.name + '/secret.txt'):
            put(self.fx.plan / 'tasks.md', TASKS.replace('a.txt, b.txt', name))
            put(self.fx.bk / 'demo/1.1/placeholder', '')
            code = self.fx.run()
            self.assertEqual(code, 1, name)
            self.assertNotIn('TOP-SECRET-BODY', self.fx.packet(), name)
            self.assertIn('NO BASE: outside workspace', self.fx.packet(), name)

    def test_default_packet_goes_to_cm_tmp_and_leaves_the_change_folder_alone(self):
        with redirect_stderr(io.StringIO()):
            RP.main([str(self.fx.plan), '--round', '3', '--backups', str(self.fx.bk)])
        self.assertTrue((ephemeral_dir(self.fx.root, 'demo') / 'review-packet-r3.md').is_file())
        self.assertEqual(sorted(p.name for p in self.fx.plan.iterdir()), ['tasks.md'])

    def test_write_leaves_no_temp_file_when_replace_fails(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        real = RP.os.replace
        RP.os.replace = lambda *a, **k: (_ for _ in ()).throw(OSError('replace failed'))
        try:
            with self.assertRaises(OSError):
                RP.write(str(d / 'packet.md'), 'text')
        finally:
            RP.os.replace = real
        self.assertEqual([p.name for p in d.iterdir() if p.name.startswith('.review-packet-')], [])


def git(repo, *argv):
    out = subprocess.run(['git', '-C', str(repo), '-c', 'user.name=t', '-c', 'user.email=t@t', *argv], check=True, capture_output=True, text=True)
    return out.stdout.strip()


def init_repo(repo, branch='main'):
    Path(repo).mkdir(parents=True, exist_ok=True)
    git(repo, 'init', '-q')
    git(repo, 'symbolic-ref', 'HEAD', f'refs/heads/{branch}')


def commit_all(repo, msg='base'):
    git(repo, 'add', '-A')
    git(repo, 'commit', '-q', '-m', msg)


@unittest.skipIf(shutil.which('git') is None, 'git missing')
class SubRepoTests(unittest.TestCase):
    """a workspace root that is not a git work tree, with the code in sub-repos (R35)"""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='review-packet-ws-')
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.plan = self.root / 'openspec/changes/foo'
        self.bk = self.root / 'bk'
        self.out = self.root / 'out'
        self.only = self.root / 'd.md'

    def tasks(self, files):
        put(self.plan / 'tasks.md', TASKS.split('- [ ] 1.2')[0].replace('a.txt, b.txt', files))

    def run_rp(self, *extra):
        err = io.StringIO()
        with redirect_stderr(err):
            code = RP.main([str(self.plan), '--round', '0', '--backups', str(self.bk), '--out-dir', str(self.out),
                            '--diff-only-out', str(self.only), *extra])
        return code, err.getvalue()

    def packet(self):
        return (self.out / 'review-packet-r0.md').read_text(encoding='utf-8')

    def test_sub_repo_under_non_git_root_diffs_against_ref(self):
        put(self.root / 'api/a.py', 'x = 1\n')
        init_repo(self.root / 'api')
        commit_all(self.root / 'api')
        put(self.root / 'api/a.py', 'x = 2\n')
        self.tasks('api/a.py')
        code, _ = self.run_rp('--base-ref', 'HEAD')
        self.assertEqual(code, 0)
        only = self.only.read_text(encoding='utf-8')
        self.assertIn('### api/a.py', only)
        self.assertIn('+x = 2', only)
        self.assertIn('-x = 1', only)
        self.assertNotIn('NO BASE', only)
        self.assertIn('| api/a.py | git HEAD (api) |', self.packet())

    def test_sub_repo_directory_path_expands_in_its_repo(self):
        put(self.root / 'api/pkg/old.py', 'old\n')
        put(self.root / 'api/pkg/keep.py', 'keep\n')
        init_repo(self.root / 'api')
        commit_all(self.root / 'api')
        (self.root / 'api/pkg/old.py').unlink()
        put(self.root / 'api/pkg/new.py', 'new\n')
        self.tasks('api/pkg/')
        code, _ = self.run_rp('--base-ref', 'HEAD')
        self.assertEqual(code, 0)
        only = self.only.read_text(encoding='utf-8')
        self.assertIn('### api/pkg/old.py', only)
        self.assertIn('-old', only)
        self.assertIn('### api/pkg/new.py', only)
        self.assertIn('+new', only)

    def test_ref_missing_in_one_sub_repo_exits_2(self):
        for name, branch in (('api', 'main'), ('web', 'master')):
            put(self.root / name / 'f.py', 'v1\n')
            init_repo(self.root / name, branch)
            commit_all(self.root / name)
        self.tasks('api/f.py, web/f.py')
        code, err = self.run_rp('--base-ref', 'main')
        self.assertEqual(code, 2)
        self.assertIn('--base-ref main: not a commit in', err)
        self.assertIn('web', err)
        self.assertFalse(self.out.exists())

    def test_non_repo_path_beside_sub_repo_uses_backup(self):
        put(self.root / 'api/a.py', 'x = 1\n')
        init_repo(self.root / 'api')
        commit_all(self.root / 'api')
        put(self.root / 'api/a.py', 'x = 2\n')
        put(self.root / 'notes/x.md', 'after\n')
        self.tasks('api/a.py, notes/x.md')
        code, _ = self.run_rp('--base-ref', 'HEAD')
        self.assertEqual(code, 1)
        rows = [r for r in self.packet().splitlines() if r.startswith('| ') and 'NO BASE' in r]
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0].startswith('| notes/x.md |'), rows)
        self.assertIn('NO BASE: no backup at', rows[0])
        self.assertIn('| api/a.py | git HEAD (api) |', self.packet())
        put(self.bk / 'foo/1.1/notes/x.md', 'before\n')
        code, _ = self.run_rp('--base-ref', 'HEAD')
        self.assertEqual(code, 0)
        self.assertIn('| api/a.py | git HEAD (api) |', self.packet())
        self.assertRegex(self.packet(), r'\| notes/x\.md \| backup ')
        self.assertIn('-before', self.only.read_text(encoding='utf-8'))


class NoPlanTests(unittest.TestCase):
    """--files and --root: a lane with no tasks.md and no openspec/ folder (N1)"""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='review-packet-np-')
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.root = self.tmp / 'ws'
        self.record = self.root / 'docs/changes/adhoc/2026-11-17-fix-x'
        self.bk = self.tmp / 'bk'
        self.out = self.tmp / 'out'
        self.only = self.tmp / 'd.md'

    def run_rp(self, *extra, record=None):
        err = io.StringIO()
        with redirect_stderr(err):
            code = RP.main([str(record or self.record), '--round', '0', '--backups', str(self.bk), '--out-dir', str(self.out),
                            '--diff-only-out', str(self.only), *extra])
        return code, err.getvalue()

    def packet(self):
        return (self.out / 'review-packet-r0.md').read_text(encoding='utf-8')

    @unittest.skipIf(shutil.which('git') is None, 'git missing')
    def test_files_and_root_diff_exactly_those_files_in_a_git_repo(self):
        for n in ('a.txt', 'b.txt', 'c.txt'):
            put(self.root / n, f'{n} old\n')
        init_repo(self.root)
        commit_all(self.root)
        for n in ('a.txt', 'b.txt', 'c.txt'):
            put(self.root / n, f'{n} new\n')
        code, _ = self.run_rp('--files', 'a.txt, b.txt', '--root', str(self.root), '--base-ref', 'HEAD')
        self.assertEqual(code, 0)
        only = self.only.read_text(encoding='utf-8')
        self.assertIn('### a.txt', only)
        self.assertIn('### b.txt', only)
        self.assertIn('+a.txt new', only)
        self.assertNotIn('c.txt', only)
        self.assertNotIn('NO BASE', only)
        self.assertIn('# Review packet: 2026-11-17-fix-x round 0', self.packet())
        self.assertEqual(list(self.tmp.rglob('tasks.md')), [])
        self.assertFalse(list(self.tmp.rglob('openspec')))

    def test_path_outside_root_is_refused(self):
        put(self.root / 'a.txt', 'a\n')
        put(self.tmp / 'secret.txt', 'TOP-SECRET-BODY\n')
        code, _ = self.run_rp('--files', '../secret.txt', '--root', str(self.root))
        self.assertEqual(code, 1)
        self.assertIn('NO BASE: outside workspace', self.packet())
        self.assertNotIn('TOP-SECRET-BODY', self.packet())

    def test_files_without_root_and_no_openspec_exits_2_naming_root(self):
        put(self.root / 'a.txt', 'a\n')
        code, err = self.run_rp('--files', 'a.txt')
        self.assertEqual(code, 2)
        self.assertIn('--root', err)
        self.assertFalse(self.out.exists())

    def test_no_git_files_lane_uses_the_pre_edit_backup(self):
        put(self.root / 'a.txt', 'after\n')
        put(self.bk / '2026-11-17-fix-x/1/a.txt', 'before\n')
        code, _ = self.run_rp('--files', 'a.txt', '--root', str(self.root))
        self.assertEqual(code, 0)
        self.assertIn('-before', self.only.read_text(encoding='utf-8'))
        self.assertIn('+after', self.only.read_text(encoding='utf-8'))
        self.assertEqual(self.run_rp('--files', 'a.txt', '--root', str(self.root), '--task-id', '2')[0], 1)

    def test_files_lane_without_root_uses_an_openspec_ancestor(self):
        (self.root / 'openspec').mkdir(parents=True)
        put(self.root / 'a.txt', 'after\n')
        put(self.bk / '2026-11-17-fix-x/1/a.txt', 'before\n')
        self.assertEqual(self.run_rp('--files', 'a.txt')[0], 0)

    def test_empty_files_list_exits_2(self):
        code, err = self.run_rp('--files', ' , ', '--root', str(self.root))
        self.assertEqual(code, 2)
        self.assertIn('--files', err)


if __name__ == '__main__':
    unittest.main()
