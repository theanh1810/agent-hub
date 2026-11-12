"""Tests for plugins/agent-hub/hooks/worktree_create.py and worktree_remove.py (unittest and pytest).

Every case builds a temporary git repo, runs a hook by subprocess with CLAUDE_CONFIG_DIR=<tmp>/cfg,
CLAUDE_PROJECT_DIR=<repo> and the hook JSON on stdin, and never touches a real worktree or starts a service.
"""
import contextlib
import io
import json
import os
import platform
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HOOKS = Path(__file__).resolve().parents[2] / "plugins" / "agent-hub" / "hooks"
CREATE = HOOKS / "worktree_create.py"
REMOVE = HOOKS / "worktree_remove.py"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
SWEEP_CMD = "worktree-sweep.py --apply"
POSIX = os.name == "posix"


def git(cwd, *args):
    return subprocess.run(GIT + list(args), cwd=cwd, check=True, capture_output=True, text=True)


def run_hook(hook, arg, repo, cfg, extra_env=None):
    """CompletedProcess of `python3 hook` with the two environment variables above plus extra_env.

    arg is the worktree name for the create hook and the worktree path for the remove hook; it goes on stdin.
    """
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(cfg), CLAUDE_PROJECT_DIR=str(repo))
    env.pop("CLAUDE_WORKTREE_NAME", None)
    env.pop("CLAUDE_WORKTREE_CAP", None)
    env.update(extra_env or {})
    if hook == REMOVE:
        payload = {"hook_event_name": "WorktreeRemove", "worktree_path": str(arg)}
    else:
        payload = {"hook_event_name": "WorktreeCreate", "name": arg}
    return subprocess.run([sys.executable, str(hook)], input=json.dumps(payload), capture_output=True, text=True,
                          env=env, cwd=str(repo))


class WorktreeHooksTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='wt-hooks-')
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(os.path.realpath(tmp.name))
        self.cfg = self.tmp / 'cfg'
        self.base = self.cfg / 'worktrees'

    def repo(self, ignore_lock=False):
        r = self.tmp / 'repo'
        r.mkdir()
        git(r, 'init', '-q', '-b', 'main')
        (r / 'package-lock.json').write_text('{}\n')
        (r / 'node_modules' / 'pkg').mkdir(parents=True)
        (r / 'node_modules' / 'pkg' / 'index.js').write_text('x\n')
        (r / 'node_modules' / '.bin').mkdir()
        os.symlink('../pkg/index.js', r / 'node_modules' / '.bin' / 'x')
        ign = 'node_modules\n.next\ndist\nbuild\n.turbo\n.cache\n.venv\n' + ('package-lock.json\n' if ignore_lock else '')
        (r / '.gitignore').write_text(ign)
        git(r, 'add', '-A', '.')
        git(r, 'commit', '-q', '-m', 'init')
        return r

    def create(self, repo, name, **env):
        return run_hook(CREATE, name, repo, self.cfg, env)

    def test_clone_identical_lockfiles(self):
        r = self.repo(); p = self.create(r, 'a')
        self.assertEqual(p.returncode, 0, p.stderr)
        t = self.base / 'a'
        self.assertEqual(p.stdout.strip().splitlines(), [str(t)])
        self.assertTrue((t / 'node_modules' / 'pkg' / 'index.js').exists())

    def test_clone_keeps_relative_symlink(self):
        r = self.repo(); self.create(r, 'a')
        link = self.base / 'a' / 'node_modules' / '.bin' / 'x'
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), '../pkg/index.js')
        self.assertTrue(str(link.resolve()).startswith(str((self.base / 'a').resolve())))

    def test_lockfile_differs_no_clone(self):
        # lockfile ignored by git: present in the repo, absent in the target
        r = self.repo(ignore_lock=True)
        p = self.create(r, 'a')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse((self.base / 'a' / 'node_modules').exists())
        self.assertIn('node_modules not cloned', p.stderr)

    def test_clone_failure_falls_back(self):
        r = self.repo()
        sys.path.insert(0, str(HOOKS))
        import worktree_create as wc
        real_run = subprocess.run

        def failing(argv, *a, **kw):
            if argv and argv[0] == "cp":
                return subprocess.CompletedProcess(argv, 1, "", "clone failed")
            return real_run(argv, *a, **kw)

        env = dict(CLAUDE_CONFIG_DIR=str(self.cfg), CLAUDE_PROJECT_DIR=str(r))
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, env), mock.patch.object(wc.subprocess, "run", failing), \
                mock.patch.object(sys, "stdin", io.StringIO(json.dumps({"name": "a"}))), \
                mock.patch.object(wc, "clone_command", lambda s, d, system=None: ["cp", "-R", s, d]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = wc.main()
        self.assertEqual(rc, 0, err.getvalue())
        self.assertFalse((self.base / "a" / "node_modules").exists())
        self.assertIn("node_modules not cloned", err.getvalue())
        self.assertEqual(out.getvalue().strip(), str(self.base / "a"))

    def test_clone_command_per_os(self):
        sys.path.insert(0, str(HOOKS))
        import worktree_create as wc
        self.assertEqual(wc.clone_command("s", "d", "Darwin"), ["cp", "-c", "-R", "s", "d"])
        self.assertEqual(wc.clone_command("s", "d", "Linux"), ["cp", "--reflink=auto", "-R", "s", "d"])
        self.assertIsNone(wc.clone_command("s", "d", "Windows"))

    def test_repo_without_node_modules(self):
        r = self.tmp / "repo"; r.mkdir()
        git(r, "init", "-q", "-b", "main")
        (r / "a.txt").write_text("x\n")
        git(r, "add", "-A", "."); git(r, "commit", "-q", "-m", "init")
        p = self.create(r, "a")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), str(self.base / "a"))
        self.assertTrue((self.base / "a" / "a.txt").exists())
        self.assertNotIn("not cloned", p.stderr)

    def test_not_a_git_repo_archive_copy(self):
        r = self.tmp / "plain"; (r / "src").mkdir(parents=True)
        (r / "src" / "f.txt").write_text("x")
        (r / "node_modules").mkdir(); (r / "node_modules" / "m").write_text("x")
        (r / "dist").mkdir(); (r / "dist" / "o").write_text("x")
        p = self.create(r, "a")
        self.assertEqual(p.returncode, 0, p.stderr)
        t = self.base / "a"
        self.assertEqual(p.stdout.strip(), str(t))
        self.assertTrue((t / "src" / "f.txt").exists())
        self.assertFalse((t / "node_modules").exists())
        self.assertFalse((t / "dist").exists())
        self.assertTrue((self.base / ".a.complete").exists())

    def test_remove_refuses_outside_root(self):
        r = self.repo()
        outside = self.tmp / "victim"; outside.mkdir(); (outside / "keep").write_text("x")
        self.base.mkdir(parents=True)
        for name in ("../victim", "a/b", ".."):
            p = run_hook(REMOVE, os.path.join(str(self.base), name), r, self.cfg)
            self.assertEqual(p.returncode, 2, p.stderr)
            self.assertIn("refusing unsafe name", p.stderr)
        self.assertTrue((outside / "keep").exists())

    @unittest.skipUnless(POSIX, "symlink needs privileges on Windows")
    def test_remove_refuses_symlink_escaping_root(self):
        r = self.repo()
        outside = self.tmp / "victim"; outside.mkdir(); (outside / "keep").write_text("x")
        self.base.mkdir(parents=True)
        os.symlink(outside, self.base / "evil")
        p = run_hook(REMOVE, self.base / "evil", r, self.cfg)
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertTrue((outside / "keep").exists())

    def test_create_remove_cycles_leave_nothing(self):
        r = self.repo()
        for n in range(4):
            p = self.create(r, 'feat-%d' % n)
            self.assertEqual(p.returncode, 0, p.stderr)
            q = run_hook(REMOVE, p.stdout.strip(), r, self.cfg)
            self.assertEqual(q.returncode, 0, q.stderr)
        self.assertEqual([d for d in self.base.iterdir() if d.is_dir()], [])
        self.assertEqual(len(git(r, 'worktree', 'list').stdout.strip().splitlines()), 1)

    def test_slash_name_becomes_dash_and_removes(self):
        r = self.repo()
        p = self.create(r, 'feature/auth')
        self.assertEqual(p.returncode, 0, p.stderr)
        t = self.base / 'feature-auth'
        self.assertEqual(p.stdout.strip(), str(t))
        self.assertTrue((self.base / '.feature-auth.complete').exists())
        q = run_hook(REMOVE, p.stdout.strip(), r, self.cfg)
        self.assertEqual(q.returncode, 0, q.stderr)
        self.assertFalse(t.exists())

    def test_create_refuses_parent_escape(self):
        r = self.repo()
        before = git(r, 'worktree', 'list').stdout
        p = self.create(r, '../x')
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertIn("refusing unsafe name '../x'", p.stderr)
        self.assertFalse((self.cfg / 'x').exists())
        self.assertEqual(git(r, 'worktree', 'list').stdout, before)

    def test_remove_without_path_is_a_no_op(self):
        r = self.repo()
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.cfg), CLAUDE_PROJECT_DIR=str(r))
        p = subprocess.run([sys.executable, str(REMOVE)], input='{}', capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('no worktree_path on stdin', p.stderr)

    def test_build_output_never_copied(self):
        r = self.repo()
        for d in ('.next', 'dist', 'build', '.turbo', '.cache', '.venv'):
            (r / d).mkdir(); (r / d / 'f').write_text('x')
        p = self.create(r, 'a')
        self.assertEqual(p.returncode, 0, p.stderr)
        for d in ('.next', 'dist', 'build', '.turbo', '.cache', '.venv'):
            self.assertFalse((self.base / 'a' / d).exists(), d)

    def test_orphan_marker_deleted(self):
        r = self.repo()
        self.base.mkdir(parents=True)
        (self.base / '.gone.complete').write_text('')
        (self.base / 'live').mkdir()
        (self.base / '.live.complete').write_text('')
        p = self.create(r, 'a')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse((self.base / '.gone.complete').exists())
        self.assertTrue((self.base / '.live.complete').exists())

    def test_cap_refuses_fourth(self):
        r = self.repo()
        for n in 'abc':
            self.assertEqual(self.create(r, n).returncode, 0)
        p = self.create(r, 'd')
        self.assertEqual(p.returncode, 1)
        self.assertFalse((self.base / 'd').exists())
        for n in 'abc':
            self.assertIn(str(self.base / n), p.stderr)
        self.assertIn(SWEEP_CMD, p.stderr)
        self.assertEqual(self.create(r, 'd', CLAUDE_WORKTREE_CAP='4').returncode, 0)

    def _monorepo(self, track_sublock):
        r = self.repo()
        w = r / 'apps' / 'web'
        (w / 'node_modules' / 'pkg').mkdir(parents=True)
        (w / 'package.json').write_text('{}\n')
        (w / 'node_modules' / 'pkg' / 'index.js').write_text('x\n')
        (w / 'package-lock.json').write_text('{"v":2}\n')
        if not track_sublock:
            with open(r / '.gitignore', 'a') as f:
                f.write('apps/web/package-lock.json\n')
        git(r, 'add', '-A', '.')
        git(r, 'commit', '-q', '-m', 'web')
        return r

    def test_sub_lockfile_differs_no_clone(self):
        r = self._monorepo(track_sublock=False)
        p = self.create(r, 'a')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip().splitlines(), [str(self.base / 'a')])
        self.assertFalse((self.base / 'a' / 'node_modules').exists())
        self.assertFalse((self.base / 'a' / 'apps' / 'web' / 'node_modules').exists())
        self.assertIn('node_modules not cloned (lockfile differs)', p.stderr)

    def test_sub_lockfile_identical_clones_all(self):
        r = self._monorepo(track_sublock=True)
        p = self.create(r, 'a')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue((self.base / 'a' / 'node_modules' / 'pkg' / 'index.js').exists())
        self.assertTrue((self.base / 'a' / 'apps' / 'web' / 'node_modules' / 'pkg' / 'index.js').exists())
        self.assertNotIn('not cloned', p.stderr)

    def test_invalid_cap_falls_back_and_refuses(self):
        r = self.repo()
        for n in 'abc':
            self.assertEqual(self.create(r, n).returncode, 0)
        p = self.create(r, 'd', CLAUDE_WORKTREE_CAP='abc')
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertFalse((self.base / 'd').exists())
        self.assertIn('CLAUDE_WORKTREE_CAP=abc is not a whole number; using 3', p.stderr)
        self.assertIn('refusing a new worktree, 3 exist (cap 3)', p.stderr)
        self.assertIn(SWEEP_CMD, p.stderr)

    def test_invalid_cap_allows_under_default(self):
        r = self.repo()
        for n in 'ab':
            self.assertEqual(self.create(r, n).returncode, 0)
        p = self.create(r, 'c', CLAUDE_WORKTREE_CAP='abc')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip().splitlines(), [str(self.base / 'c')])
        self.assertIn('CLAUDE_WORKTREE_CAP=abc is not a whole number; using 3', p.stderr)
        self.assertNotIn('integer expression expected', p.stderr)

    def _detached_commit(self, name):
        r = self.repo(); self.assertEqual(self.create(r, name).returncode, 0)
        t = self.base / name
        (t / 'new.txt').write_text('n')
        git(t, 'add', 'new.txt'); git(t, 'commit', '-q', '-m', 'work')
        return r, t, git(t, 'rev-parse', 'HEAD').stdout.strip()

    def test_remove_pins_detached_head(self):
        r, t, sha = self._detached_commit('a')
        p = run_hook(REMOVE, self.base / 'a', r, self.cfg)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(git(r, 'rev-parse', 'refs/backup/wt/a').stdout.strip(), sha)
        self.assertFalse(t.exists()); self.assertFalse((self.base / '.a.complete').exists())

    def test_remove_pin_name_clash(self):
        r, t, sha = self._detached_commit('a')
        other = git(r, 'rev-parse', 'main').stdout.strip()
        git(r, 'update-ref', 'refs/backup/wt/a', other)
        p = run_hook(REMOVE, self.base / 'a', r, self.cfg)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(git(r, 'rev-parse', f'refs/backup/wt/a-{sha[:7]}').stdout.strip(), sha)

    def test_remove_marker_without_target(self):
        r = self.repo(); self.base.mkdir(parents=True)
        (self.base / '.a.complete').write_text('')
        p = run_hook(REMOVE, self.base / 'a', r, self.cfg)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse((self.base / '.a.complete').exists())


if __name__ == '__main__':
    unittest.main()
