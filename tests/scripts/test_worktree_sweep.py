"""Tests for scripts/worktree-sweep.py: every case builds temporary git repos and runs the CLI (two cases patch the module in-process)."""
import atexit
import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[2] / 'plugins' / 'agent-hub' / 'scripts' / 'worktree-sweep.py'
GIT = ['git', '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false']


_STUB_DIR = tempfile.mkdtemp(prefix='wt-sweep-stub-')
atexit.register(shutil.rmtree, _STUB_DIR, True)
STUB = os.path.join(_STUB_DIR, 'task-db.sh')
with open(STUB, 'w') as _f:
    _f.write('#!/bin/sh\nexit 0\n')
os.chmod(STUB, 0o755)
os.environ['WORKTREE_SWEEP_TASK_DB'] = STUB   # in-process tests too: no test reaches the real task-db.sh ledger


def sweep(*args, task_db=STUB):
    env = dict(os.environ, WORKTREE_SWEEP_TASK_DB=task_db)
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env)


def git(cwd, *args):
    return subprocess.run(GIT + list(args), cwd=cwd, check=True, capture_output=True, text=True)


def load_module():
    spec = importlib.util.spec_from_file_location('worktree_sweep', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class WorktreeSweepTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='wt-sweep-')
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(os.path.realpath(tmp.name))

    def repo(self, branch='main'):
        repo = self.tmp / 'repo'
        repo.mkdir()
        git(repo, 'init', '-q', '-b', branch)
        (repo / 'README.md').write_text('hello\n')
        (repo / '.gitignore').write_text('.env\nnode_modules\n')
        git(repo, 'add', '-A')
        git(repo, 'commit', '-q', '-m', 'init')
        return repo

    def worktree(self, repo, name='wt1'):
        path = self.tmp / name
        git(repo, 'worktree', 'add', '-q', '-b', name, str(path))
        return path

    def listed(self, repo):
        return git(repo, 'worktree', 'list', '--porcelain').stdout

    def test_merged_clean_worktree_removed(self):
        repo = self.repo()
        wt = self.worktree(repo)
        out = sweep('--apply', '--repo', str(repo)).stdout
        self.assertIn(f'PASS remove {wt}', out)
        self.assertFalse(wt.exists())
        self.assertNotIn(str(wt), self.listed(repo))
        self.assertIn('removed 1', out)

    def test_branch_reachable_removed(self):
        repo = self.repo()
        wt = self.worktree(repo)
        (wt / 'new.txt').write_text('x\n')
        git(wt, 'add', '-A')
        git(wt, 'commit', '-q', '-m', 'work')
        out = sweep('--apply', '--repo', str(repo)).stdout
        self.assertIn(f'PASS remove {wt}', out)
        self.assertFalse(wt.exists())
        self.assertIn('wt1', git(repo, 'branch', '--list', 'wt1').stdout)

    def test_untracked_differing_file_kept(self):
        repo = self.repo()
        wt = self.worktree(repo)
        (repo / 'notes.txt').write_text('main copy\n')
        (wt / 'notes.txt').write_text('worktree copy\n')
        out = sweep('--apply', '--repo', str(repo)).stdout
        self.assertIn(f'KEEP {wt}: dirty:notes.txt', out)
        self.assertTrue(wt.exists())

    def test_untracked_identical_file_removed(self):
        repo = self.repo()
        wt = self.worktree(repo)
        (repo / 'notes.txt').write_text('same\n')
        (wt / 'notes.txt').write_text('same\n')
        out = sweep('--apply', '--repo', str(repo)).stdout
        self.assertIn(f'PASS remove {wt}', out)
        self.assertFalse(wt.exists())

    def test_ignored_env_kept(self):
        repo = self.repo()
        wt = self.worktree(repo)
        (wt / '.env').write_text('SECRET=1\n')
        out = sweep('--apply', '--repo', str(repo)).stdout
        self.assertIn(f'KEEP {wt}: dirty:.env', out)
        self.assertTrue((wt / '.env').exists())

    def test_ignored_node_modules_removed(self):
        repo = self.repo()
        wt = self.worktree(repo)
        (wt / 'node_modules').mkdir()
        (wt / 'node_modules' / 'x').write_text('x\n')
        out = sweep('--apply', '--repo', str(repo)).stdout
        self.assertIn(f'PASS remove {wt}', out)
        self.assertFalse(wt.exists())

    def test_empty_orphan_removed(self):
        orphans = self.tmp / 'orphans'
        child = orphans / 'old-task'
        child.mkdir(parents=True)
        marker = orphans / '.old-task.complete'
        marker.write_text('')
        out = sweep('--apply', '--orphans', str(orphans)).stdout
        self.assertIn(f'PASS remove {child}', out)
        self.assertFalse(child.exists())
        self.assertFalse(marker.exists())

    def test_nonempty_orphan_kept(self):
        orphans = self.tmp / 'orphans'
        child = orphans / 'old-task'
        child.mkdir(parents=True)
        (child / 'keep.txt').write_text('data\n')
        out = sweep('--apply', '--orphans', str(orphans)).stdout
        self.assertIn(f'KEEP {child}: not-a-worktree', out)
        self.assertTrue((child / 'keep.txt').exists())

    def test_dry_run_removes_nothing(self):
        repo = self.repo()
        wt = self.worktree(repo)
        orphans = self.tmp / 'orphans'
        (orphans / 'empty').mkdir(parents=True)
        out = sweep('--repo', str(repo), '--orphans', str(orphans)).stdout
        self.assertEqual(out.count('PASS remove'), 2)
        self.assertIn('removed 0', out)
        self.assertTrue(wt.exists())
        self.assertTrue((orphans / 'empty').exists())

    def test_process_cwd_inside_kept(self):
        repo = self.repo()
        wt = self.worktree(repo)
        proc = subprocess.Popen(['sleep', '30'], cwd=wt)
        self.addCleanup(proc.wait)
        self.addCleanup(proc.kill)
        out = sweep('--apply', '--repo', str(repo)).stdout
        self.assertIn(f'KEEP {wt}: in-use:{proc.pid}', out)
        self.assertTrue(wt.exists())

    def test_second_run_idempotent(self):
        repo = self.repo()
        self.worktree(repo)
        sweep('--apply', '--repo', str(repo))
        out = sweep('--apply', '--repo', str(repo)).stdout
        self.assertNotIn('PASS', out)
        self.assertIn('removed 0', out)

    def test_git_timeout_keeps(self):
        repo = self.repo()
        wt = self.worktree(repo)
        mod = load_module()
        real = subprocess.run

        def slow(cmd, *a, **kw):
            if 'cherry' in cmd:
                raise subprocess.TimeoutExpired(cmd, kw.get('timeout', 1))
            return real(cmd, *a, **kw)

        buf = io.StringIO()
        with mock.patch.object(mod, 'TIMEOUT', 1), mock.patch.object(mod.subprocess, 'run', side_effect=slow), contextlib.redirect_stdout(buf):
            mod.main(['--apply', '--repo', str(repo)])
        self.assertIn(f'KEEP {wt}: timeout:git cherry', buf.getvalue())
        self.assertTrue(wt.exists())

    def test_base_unknown_keeps(self):
        repo = self.repo(branch='trunk')
        wt = self.worktree(repo)
        out = sweep('--apply', '--repo', str(repo)).stdout
        self.assertIn(f'KEEP {wt}: base-unknown', out)
        self.assertTrue(wt.exists())

    def test_lsof_failure_keeps(self):
        repo = self.repo()
        wt = self.worktree(repo)
        mod = load_module()
        real_run = mod.run

        def failing_lsof(cmd, cwd=None):
            if cmd[0] == 'lsof':
                return subprocess.CompletedProcess(cmd, 1, '', 'lsof: blocked')
            return real_run(cmd, cwd)

        buf = io.StringIO()
        with mock.patch.object(mod, 'run', failing_lsof), contextlib.redirect_stdout(buf):
            mod.main(['--apply', '--repo', str(repo)])
        self.assertIn(f'KEEP {wt}: in-use-unknown:lsof exit 1', buf.getvalue())
        self.assertTrue(wt.exists())

    def test_refused_removal_restores_identical_untracked(self):
        repo = self.repo()
        locked = self.worktree(repo, 'locked')
        (repo / 'notes.md').write_text('same\n')
        (locked / 'notes.md').write_text('same\n')
        git(repo, 'worktree', 'lock', str(locked))
        out = sweep('--apply', '--repo', str(repo)).stdout
        self.assertIn(f'KEEP {locked}: refused:', out)
        self.assertEqual((locked / 'notes.md').read_text(), 'same\n')

    def test_orphans_lists_a_child_with_git(self):
        repo = self.repo()
        orphans = self.tmp / 'orphans'
        orphans.mkdir()
        wt = orphans / 'wt'
        git(repo, 'worktree', 'add', '-q', '-b', 'wt', str(wt))
        out = sweep('--apply', '--orphans', str(orphans)).stdout
        self.assertIn(f'KEEP 1 worktrees of {repo}: not judged, pass that repository as --repo', out)
        self.assertNotIn(f'KEEP {wt}:', out)
        self.assertIn('kept 1', out)
        self.assertTrue(wt.exists())

    def test_missing_repo_exits_2(self):
        p = sweep('--repo', str(self.tmp / 'nonexistent'))
        self.assertEqual(p.returncode, 2)
        self.assertIn('not a folder', p.stderr)
        self.assertNotIn('Traceback', p.stderr)

    def test_refused_removal_keeps_rest(self):
        repo = self.repo()
        locked = self.worktree(repo, 'locked')
        other = self.worktree(repo, 'other')
        git(repo, 'worktree', 'lock', str(locked))
        out = sweep('--apply', '--repo', str(repo)).stdout
        self.assertIn(f'KEEP {locked}: refused:', out)
        self.assertTrue(locked.exists())
        self.assertIn(f'PASS remove {other}', out)
        self.assertFalse(other.exists())

    def test_worktree_added_during_run(self):
        repo = self.repo()
        first = self.worktree(repo, 'first')
        mod = load_module()
        late = self.tmp / 'late'
        real_judge = mod.judge_worktree
        calls = []

        def judge_and_add(wt, main, identical):
            if not calls:
                calls.append(1)
                git(repo, 'worktree', 'add', '-q', '-b', 'late', str(late))
            return real_judge(wt, main, identical)

        buf = io.StringIO()
        with mock.patch.object(mod, 'judge_worktree', judge_and_add), contextlib.redirect_stdout(buf):
            mod.main(['--apply', '--repo', str(repo)])
        out = buf.getvalue()
        self.assertIn(f'PASS remove {first}', out)
        self.assertNotIn(str(late), out)   # discovered before it existed: skipped, never half-removed
        self.assertTrue((late / '.git').exists())
        self.assertIn(str(late), self.listed(repo))

    def detached(self, repo, name='det'):
        path = self.tmp / name
        git(repo, 'worktree', 'add', '-q', '--detach', str(path))
        (path / 'new.txt').write_text('x\n')
        git(path, 'add', '-A')
        git(path, 'commit', '-q', '-m', 'work')
        return path

    def test_detached_commit_pinned_then_removed(self):
        repo = self.repo()
        wt = self.detached(repo)
        sha = git(wt, 'rev-parse', 'HEAD').stdout.strip()
        out = sweep('--apply', '--repo', str(repo)).stdout
        self.assertIn(f'PIN {wt} -> refs/backup/wt/det', out)
        self.assertEqual(git(repo, 'rev-parse', 'refs/backup/wt/det').stdout.strip(), sha)
        self.assertFalse(wt.exists())

    def test_detached_commit_dry_run_predicts_removal(self):
        repo = self.repo()
        wt = self.detached(repo)
        out = sweep('--repo', str(repo)).stdout
        self.assertIn(f'PIN would {wt} -> refs/backup/wt/det', out)
        self.assertIn(f'PASS remove {wt}', out)
        self.assertNotIn(f'KEEP {wt}', out)
        self.assertEqual(git(repo, 'for-each-ref', 'refs/backup/wt').stdout.strip(), '')
        self.assertTrue(wt.exists())
        self.assertIn('removed 0', out)

    def test_detached_dry_run_matches_apply(self):
        repo = self.repo()
        wt = self.detached(repo)
        sha = git(wt, 'rev-parse', 'HEAD').stdout.strip()
        dry = sweep('--repo', str(repo)).stdout
        app = sweep('--apply', '--repo', str(repo)).stdout
        passed = lambda t: {l.split()[2] for l in t.splitlines() if l.startswith('PASS remove ')}
        self.assertEqual(passed(dry), passed(app))
        self.assertEqual(passed(dry), {str(wt)})
        self.assertIn(f'PIN {wt} -> refs/backup/wt/det', app)
        self.assertEqual(git(repo, 'rev-parse', 'refs/backup/wt/det').stdout.strip(), sha)
        self.assertFalse(wt.exists())

    def test_detached_dry_run_judges_dirty(self):
        repo = self.repo()
        wt = self.detached(repo)
        (repo / 'notes.txt').write_text('main copy\n')
        (wt / 'notes.txt').write_text('worktree copy\n')
        out = sweep('--repo', str(repo)).stdout
        self.assertIn(f'PIN would {wt} -> refs/backup/wt/det', out)
        self.assertIn(f'KEEP {wt}: dirty:notes.txt', out)
        self.assertEqual(git(repo, 'for-each-ref', 'refs/backup/wt').stdout.strip(), '')
        self.assertTrue((wt / 'notes.txt').exists())

    def test_uncommitted_counted(self):
        repo = self.repo()
        wt = self.worktree(repo)
        (repo / 'notes.txt').write_text('main copy\n')
        (wt / 'notes.txt').write_text('worktree copy\n')
        out = sweep('--apply', '--repo', str(repo)).stdout
        self.assertIn(f'KEEP {wt}: dirty:notes.txt', out)
        self.assertIn('kept-uncommitted 1', out)

    def test_orphan_marker_deleted(self):
        folder = self.tmp / 'orph'
        (folder / 'live').mkdir(parents=True)
        (folder / 'live' / 'f.txt').write_text('x\n')
        (folder / '.gone.complete').write_text('')
        (folder / '.live.complete').write_text('')
        sweep('--apply', '--orphans', str(folder))
        self.assertFalse((folder / '.gone.complete').exists())
        self.assertTrue((folder / '.live.complete').exists())

    def counting_stub(self, code=0):
        counter = self.tmp / 'calls.txt'
        stub = self.tmp / 'stub-task-db.sh'
        stub.write_text(f'#!/bin/sh\necho call >> {counter}\nexit {code}\n')
        stub.chmod(0o755)
        return stub, counter

    def test_task_db_sweep_runs_once(self):
        repo = self.repo()
        a, b = self.worktree(repo, 'a'), self.worktree(repo, 'b')
        stub, counter = self.counting_stub()
        sweep('--repo', str(repo), task_db=str(stub))
        self.assertFalse(counter.exists())
        sweep('--apply', '--repo', str(repo), task_db=str(stub))
        self.assertEqual(len(counter.read_text().splitlines()), 1)
        self.assertFalse(a.exists() or b.exists())

    def test_task_db_failure_only_warns(self):
        repo = self.repo()
        wt = self.worktree(repo)
        stub, _ = self.counting_stub(code=1)
        res = sweep('--apply', '--repo', str(repo), task_db=str(stub))
        self.assertIn('KEEP task-db.sh sweep:', res.stdout)
        self.assertEqual(res.returncode, 0)
        self.assertFalse(wt.exists())
        wt2 = self.worktree(repo, 'wt2')
        res = sweep('--apply', '--repo', str(repo), task_db=str(self.tmp / 'missing.sh'))
        self.assertIn('KEEP task-db.sh sweep:', res.stdout)
        self.assertEqual(res.returncode, 0)
        self.assertFalse(wt2.exists())


if __name__ == '__main__':
    unittest.main()
