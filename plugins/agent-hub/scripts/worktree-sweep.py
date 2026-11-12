#!/usr/bin/env python3
"""worktree-sweep.py [--apply] [--repo PATH ...] [--orphans DIR] [--json]

Judges every linked worktree of each --repo (git worktree list --porcelain, the first entry is the main worktree and is skipped)
and every child folder of --orphans that has no .git file (those with a .git print one "KEEP <n> worktrees of <repo>" line per repository). Prints "PASS remove <path> (<KB> KB)" or "KEEP <path>: <reason>" per
path, then "removed N (X MB) | kept M". Removes only with --apply, only a path that passes all four conditions, with
`git -C <repo> worktree remove <path>` and no force option of any kind; never deletes a branch. Exit 0, or 2 on bad arguments. On Windows it prints 'worktree-sweep: not supported on Windows' and exits 0 without judging or removing anything.

Conditions, first failure wins: (1) every commit of the worktree is saved: none that the base branch lacks (git cherry), or HEAD reachable from a local branch or a refs/backup/wt ref, or, with --apply, pinned to refs/backup/wt/<name> first (a dry run prints PIN would and goes on as if pinned, writing no ref), (2) every changed, untracked or
ignored path outside the regenerable list has identical bytes in the main worktree, (3) no process has its cwd inside, (4) git agrees
to remove it. Every unknown keeps the path."""
import argparse
import filecmp
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python3 -I leaves the script folder off sys.path
from _paths import config_dir

REGENERABLE = ('node_modules', 'dist', 'build', '.next', 'target', 'coverage', '.turbo', '__pycache__', '.venv')
TASK_DB = 'task-db.sh'   # looked up on PATH; WORKTREE_SWEEP_TASK_DB overrides it (tests use a stub)
APPLY = False      # set by main(); read by judge_worktree
JSON_OUT = False   # set by main(); keeps stdout valid JSON
TIMEOUT = 30   # seconds per git, lsof or du call; a timeout is KEEP timeout:<cmd>


class Timeout(Exception):
    pass


def label(cmd):
    sub = next((c for c in cmd[1:] if not c.startswith('-') and '/' not in c), '')
    return f'{cmd[0]} {sub}'.strip()


def run(cmd, cwd=None):
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        raise Timeout(label(cmd))


def base_branch(wt):
    ref = run(['git', 'symbolic-ref', '-q', '--short', 'refs/remotes/origin/HEAD'], wt)
    if ref.returncode == 0 and ref.stdout.strip():
        return ref.stdout.strip()
    for name in ('main', 'master'):
        if run(['git', 'rev-parse', '--verify', '-q', name], wt).returncode == 0:
            return name
    return None


def say(msg):
    print(msg, file=sys.stderr if JSON_OUT else sys.stdout)


def condition_saved(wt, name, apply):
    base = base_branch(wt)
    if base is None:
        return 'base-unknown'
    out = run(['git', 'cherry', base, 'HEAD'], wt)
    if out.returncode != 0:
        return f'cherry-failed:{out.stderr.strip().splitlines()[0] if out.stderr.strip() else out.returncode}'
    n = sum(1 for line in out.stdout.splitlines() if line.startswith('+'))
    if not n:
        return None
    held = run(['git', 'for-each-ref', '--contains', 'HEAD', 'refs/heads', 'refs/backup/wt'], wt)
    if held.returncode == 0 and held.stdout.strip():
        return None
    ref = f'refs/backup/wt/{name}'
    head = run(['git', 'rev-parse', 'HEAD'], wt).stdout.strip()
    at = run(['git', 'rev-parse', '-q', '--verify', ref], wt)
    if at.returncode == 0 and at.stdout.strip() != head:
        ref = f'{ref}-{head[:7]}'
    if apply:
        if run(['git', 'update-ref', ref, 'HEAD'], wt).returncode != 0:
            return f'pin-failed:{ref}'
        say(f'PIN {wt} -> {ref}')
        return None
    say(f'PIN would {wt} -> {ref}')
    return None


def regenerable(rel):
    return any(part in REGENERABLE for part in rel.split('/'))


def same_bytes(wt, main, rel):
    """True when the file at rel exists in both trees with identical bytes; a folder compares every file under it."""
    a, b = os.path.join(wt, rel), os.path.join(main, rel)
    try:
        if os.path.isdir(a) and not os.path.islink(a):
            for root, dirs, files in os.walk(a):
                dirs[:] = [d for d in dirs if d not in REGENERABLE]
                for name in files:
                    sub = os.path.relpath(os.path.join(root, name), wt)
                    if not filecmp.cmp(os.path.join(wt, sub), os.path.join(main, sub), shallow=False):
                        return False
            return True
        return os.path.isfile(b) and filecmp.cmp(a, b, shallow=False)
    except OSError:
        return False


def condition_dirty(wt, main, identical_untracked):
    """None, or dirty:<path>; appends the untracked paths whose bytes equal the main copy to identical_untracked."""
    out = run(['git', 'status', '--porcelain', '-z', '--untracked-files=all', '--ignored'], wt)
    if out.returncode != 0:
        return 'status-failed'
    entries = out.stdout.split('\0')
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        code, rel = entry[:2], entry[3:].rstrip('/')
        if code[0] in 'RC':
            i += 1   # the source path of a rename or copy follows as its own entry
        if regenerable(rel):
            continue
        if not same_bytes(wt, main, rel):
            return f'dirty:{rel}'
        if code == '??':
            identical_untracked.append(rel)
    return None


def condition_in_use(wt):
    out = run(['lsof', '-d', 'cwd', '-Fpn'])
    lines = out.stdout.splitlines()
    if not any(line.startswith('p') for line in lines):   # this sweep's own process always has a cwd: no listing means lsof failed
        return f'in-use-unknown:lsof exit {out.returncode}'
    pid = None
    for line in lines:
        if line.startswith('p'):
            pid = line[1:]
        elif line.startswith('n'):
            cwd = os.path.realpath(line[1:])
            if cwd == wt or cwd.startswith(wt + os.sep):
                return f'in-use:{pid}'
    return None


def judge_worktree(wt, main, identical_untracked):
    return condition_saved(wt, os.path.basename(wt), APPLY) or condition_dirty(wt, main, identical_untracked) or condition_in_use(wt)


def judge_orphan(path):
    return None if not os.listdir(path) else 'not-a-worktree'


def drop_marker(path):
    marker = os.path.join(os.path.dirname(path), f'.{os.path.basename(path)}.complete')
    if os.path.isfile(marker):
        os.remove(marker)


def drop_orphan_markers(folder):
    for entry in os.listdir(folder):
        if entry.startswith('.') and entry.endswith('.complete') and len(entry) > len('..complete'):
            if not os.path.isdir(os.path.join(folder, entry[1:-len('.complete')])):
                os.remove(os.path.join(folder, entry))


def remove_worktree(repo, wt, identical_untracked):
    """git refuses a worktree holding untracked files; those proven identical to the main copy are moved aside first and put back
    when git refuses, times out or anything fails midway, so a KEEP line always means the worktree is whole."""
    aside = tempfile.mkdtemp(prefix='worktree-sweep-')
    moved, out = [], None
    try:
        for rel in identical_untracked:
            dst = os.path.join(aside, str(len(moved)))
            shutil.move(os.path.join(wt, rel), dst)
            moved.append((rel, dst))
        out = run(['git', '-C', repo, 'worktree', 'remove', wt])
    finally:
        if out is None or out.returncode != 0:
            for rel, dst in moved:
                shutil.move(dst, os.path.join(wt, rel))
        shutil.rmtree(aside, ignore_errors=True)
    if out.returncode != 0:
        return 'refused:' + (out.stderr.strip().splitlines() or [str(out.returncode)])[0]
    drop_marker(wt)
    return None


def size_kb(path):
    out = run(['du', '-sk', path])
    try:
        return int(out.stdout.split()[0])
    except (IndexError, ValueError):
        return 0


def linked_worktrees(repo):
    out = run(['git', 'worktree', 'list', '--porcelain'], repo)
    paths = [os.path.realpath(line[len('worktree '):]) for line in out.stdout.splitlines() if line.startswith('worktree ')]
    return (paths[0], paths[1:]) if paths else (None, [])


def owner_repo(child):
    """The main worktree of the repository whose linked worktree `child` is, from its .git file; `child` itself when unknown."""
    try:
        with open(os.path.join(child, '.git'), encoding='utf-8') as f:
            line = f.readline().strip()
    except (OSError, ValueError):
        return child
    if not line.startswith('gitdir: '):
        return child
    gitdir = os.path.realpath(os.path.join(child, line[len('gitdir: '):]))
    if os.path.basename(os.path.dirname(gitdir)) != 'worktrees':
        return child
    common = os.path.dirname(os.path.dirname(gitdir))
    return os.path.dirname(common) if os.path.basename(common) == '.git' else common


def main(argv=None):
    ap = argparse.ArgumentParser(prog='worktree-sweep.py')
    ap.add_argument('--apply', action='store_true', help='remove the paths that pass; without it nothing is removed')
    ap.add_argument('--repo', action='append', default=[], metavar='PATH', help='a repo whose linked worktrees are judged')
    ap.add_argument('--orphans', metavar='DIR', help='a folder whose children without a .git file are judged')
    ap.add_argument('--json', action='store_true', help='print the result as a JSON list')
    args = ap.parse_args(argv)
    if os.name == 'nt':
        print('worktree-sweep: not supported on Windows')
        return 0
    global APPLY, JSON_OUT
    APPLY, JSON_OUT = args.apply, args.json
    if not args.repo and not args.orphans:
        default = Path(config_dir()) / 'worktrees'
        if not default.is_dir():
            print('removed 0 (0 MB) | kept 0 | no worktrees folder under the config dir')
            return 0
        args.orphans = str(default)
    for path in args.repo + ([args.orphans] if args.orphans else []):
        if not os.path.isdir(path):
            ap.error(f'not a folder: {path}')

    candidates = []   # (kind, repo, path)
    for repo in args.repo:
        main_wt, linked = linked_worktrees(repo)
        candidates += [('worktree', main_wt, wt) for wt in linked]
    if args.orphans:
        for name in sorted(os.listdir(args.orphans)):
            child = os.path.realpath(os.path.join(args.orphans, name))
            if os.path.isdir(child) and not os.path.lexists(os.path.join(child, '.git')):
                candidates.append(('orphan', None, child))
            elif os.path.isdir(child) and child not in {c[2] for c in candidates}:
                candidates.append(('linked', owner_repo(child), child))   # a worktree: judged only through its --repo, listed so the count is whole

    if args.orphans and args.apply:
        drop_orphan_markers(args.orphans)
    results = []
    for kind, main_wt, path in candidates:
        kb = 0
        identical = []
        try:
            if kind == 'linked':
                reason = 'has-git:pass its repository as --repo'
            else:
                reason = judge_worktree(path, main_wt, identical) if kind == 'worktree' else judge_orphan(path)
            kb = size_kb(path) if reason is None else 0
            if reason is None and args.apply:
                if kind == 'worktree':
                    reason = remove_worktree(main_wt, path, identical)
                else:
                    os.rmdir(path)
                    drop_marker(path)
        except Timeout as exc:
            reason = f'timeout:{exc}'
        except Exception as exc:   # an unknown keeps the path
            reason = f'error:{type(exc).__name__}'
        results.append({'path': path, 'verdict': 'PASS' if reason is None else 'KEEP', 'reason': reason, 'kb': kb if reason is None else 0})

    passed = [r for r in results if r['verdict'] == 'PASS']
    kept = len(results) - len(passed)
    mb = sum(r['kb'] for r in passed) // 1024
    uncommitted = sum(1 for r in results if (r['reason'] or '').startswith('dirty:'))
    if args.apply and passed:
        task_db = os.environ.get('WORKTREE_SWEEP_TASK_DB', TASK_DB)
        try:
            res = run([task_db, 'sweep'])
            for line in res.stdout.splitlines():
                say(line)
            if res.returncode != 0:
                say(f'KEEP task-db.sh sweep: exit {res.returncode}')
        except Timeout:
            say('KEEP task-db.sh sweep: timeout')
        except OSError as exc:
            say(f'KEEP task-db.sh sweep: {type(exc).__name__}')
    if args.json:
        print(json.dumps(results))
        return 0
    groups = {}
    for kind, owner, path in candidates:
        if kind == 'linked':
            groups.setdefault(owner, []).append(path)
    grouped = {p for paths in groups.values() for p in paths}
    for r in results:
        if r['path'] in grouped:
            continue
        print(f"PASS remove {r['path']} ({r['kb']} KB)" if r['verdict'] == 'PASS' else f"KEEP {r['path']}: {r['reason']}")
    for owner in sorted(groups):
        print(f'KEEP {len(groups[owner])} worktrees of {owner}: not judged, pass that repository as --repo')
    if args.apply:
        print(f'removed {len(passed)} ({mb} MB) | kept {kept} | kept-uncommitted {uncommitted}')
    else:
        print(f'removed 0 (0 MB) | kept {kept} | would remove {len(passed)} ({mb} MB), dry run: pass --apply | kept-uncommitted {uncommitted}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
