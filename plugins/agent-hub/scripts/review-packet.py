#!/usr/bin/env python3
"""review-packet: write a change's review packet and a diff-only copy for the independent code review.

usage: review-packet.py CHANGE_DIR --round N [--backups DIR] [--base-ref REF] [--base-dir DIR] [--out-dir DIR] [--diff-only-out PATH]
                        [--files PATH,PATH,... --root DIR [--task-id ID]]

CHANGE_DIR is openspec/changes/<change> holding tasks.md. The packet is <root>/.cm-tmp/<change>/review-packet-r<N>.md
(plan_paths.ephemeral_dir; --out-dir replaces that folder); <root> holds the openspec/ folder (--root DIR names it instead). It holds
(1) the base of each path, (2) a task | covers | test table from tasks.md, (3) one unified diff per path any task lists in Files:.
--diff-only-out writes section (3) alone: no task id, scenario or plan text, and none of the change folder's own files.
A lane with no plan files (a small change, a config batch) gives --files, the touched paths: they replace the read of tasks.md, section (2)
has no rows, and CHANGE_DIR is only the record folder whose name is the plan id. With --files and --root the script needs neither tasks.md
nor an openspec/ folder; --files without --root still looks for an openspec/ ancestor and exits 2 naming --root when there is none.
--task-id ID (default 1) names the backup folder of those paths: <backups>/<plan id>/<ID>/<path>.

The git decision is made per path, never once at <root>: with --base-ref REF, a path inside a git work tree (found from the nearest existing
folder of <root>/<path>, so a workspace root that is not a repo can hold sub-repos) is read with `git -C <top> show REF:<path relative to
top>` and a directory path expands with `git ls-tree` there (backups are then ignored; a REF that is not a commit in that top is exit 2).
A path in no git tree, or no --base-ref: <backups>/<plan id>/<first task id>/<path> (default $AGENT_HUB_BACKUPS, else ~/.claude-backups;
the plan id is the change folder's name, so another plan's backup never matches), else NO BASE (the diff is skipped). Section (1) names
the repo as `git REF (<top relative to root>)`, `.` for the root or a repo above it. An absolute path is looked up
relative to <root>. A path that resolves outside <root> is never read: one `NO BASE: outside workspace` row.
--base-dir DIR (a fix round) replaces the task paths: it diffs every file under DIR, plus every file the last errors.yaml round
names in analysis.fix_list, against its copy DIR/<path>, or against empty when it has none. A missing DIR or no changed path is one NO BASE row.
A glob path (`*`, `?`, `[`) prints `glob: not expanded` and is skipped, not a NO BASE row. A deleted file under node_modules/ is one
line, `<path> deleted (<n> lines)`. Diffs use difflib only: never /usr/bin/diff and never `git diff`.

Exit 0 written; 1 written, but a NO BASE row exists; 2 usage error or unreadable change folder.
"""
import argparse
import datetime
import difflib
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python3 -I leaves the script folder off sys.path
import plan_paths as P
from plan_paths import ephemeral_dir, read_yaml, workspace_root

_spec = importlib.util.spec_from_file_location('plan_check', Path(__file__).with_name('plan-check.py'))
plan_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plan_check)


def load_tasks(folder):
    """-> {task id: {key: value}} of tasks.md; ValueError when unreadable or empty"""
    try:
        tasks = plan_check.parse_tasks((Path(folder) / P.TASKS).read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError) as e:
        raise ValueError(f'{folder}: {type(e).__name__}: {e}')
    if not tasks:
        raise ValueError(f'{folder}: no task in {P.TASKS}')
    return tasks


def first_touch(tasks):
    """-> {path: first task id} in first-touch order"""
    seen = {}
    for tid in sorted(tasks, key=plan_check.id_key):
        for path in plan_check.csv(tasks[tid].get('Files', '')):
            seen.setdefault(path, tid)
    return seen


def run_git(root, *argv):
    """argv list, no shell; -> stdout text or None when git or the object is missing"""
    try:
        p = subprocess.run(['git', '-C', root, *argv], capture_output=True)
    except OSError:
        return None
    return p.stdout.decode('utf-8', 'replace') if p.returncode == 0 else None


def list_files(base):
    return sorted(os.path.relpath(os.path.join(d, n), base).replace(os.sep, '/') for d, _, names in os.walk(base) for n in names)


def read_text(path):
    with open(path, 'rb') as f:
        return f.read().decode('utf-8', 'replace')


def under(ref, root, name):
    """backup copy of name under ref; an absolute name is taken relative to root, since os.path.join drops ref for it"""
    return os.path.join(ref, os.path.relpath(name, root) if os.path.isabs(name) else name)


def rel_to(top, root, name):
    """name (relative to root, or absolute) as a posix path relative to the git top that holds it"""
    return os.path.relpath(os.path.realpath(os.path.join(root, name)), top).replace(os.sep, '/')


def git_top(root, path, tops):
    """-> the git top-level of root/path, found from its nearest existing folder (its own, else the first existing parent); None in no git tree.
    tops caches the answer per folder."""
    d = os.path.join(root, path)
    while not os.path.isdir(d) and d != os.path.dirname(d):
        d = os.path.dirname(d)
    if d not in tops:
        top = (run_git(d, 'rev-parse', '--show-toplevel') or '').strip()
        tops[d] = os.path.realpath(top) if top else None
    return tops[d]


def expand(root, path, kind, ref, top=None):
    """-> [file path]: a directory path becomes the files under it, base side and live side; ref is the commit for kind git, with its repo top"""
    names = set()
    if os.path.isdir(os.path.join(root, path)):
        names |= {f'{path.rstrip("/")}/{n}' for n in list_files(os.path.join(root, path))}
    if kind == 'git':
        rel = rel_to(top, root, path)
        for n in set((run_git(top, 'ls-tree', '-r', '--name-only', ref, '--', rel) or '').split('\n')) - {''}:
            names.add(path if n == rel else f'{path.rstrip("/")}/{n[len(rel) + 1:]}')
    elif kind == 'backup' and os.path.isdir(under(ref, root, path)):
        names |= {f'{path.rstrip("/")}/{n}' for n in list_files(under(ref, root, path))}
    return sorted(names) or [path]


def base_text(root, name, kind, ref, top=None):
    if kind == 'git':
        return run_git(top, 'show', f'{ref}:{rel_to(top, root, name)}') or ''
    p = under(ref, root, name)
    return read_text(p) if os.path.isfile(p) else ''


def inside(root, name):
    """True when root/name (or the absolute name) resolves to root or below it"""
    top = Path(root).resolve()
    live = Path(os.path.join(root, name)).resolve()
    return live == top or top in live.parents


def pick_base(root, backups, plan_id, path, task_id, base_ref, top):
    """-> (kind, ref, detail): kind backup|git|glob|none; top is the git top-level holding path, None for no git tree"""
    if any(c in path for c in '*?['):
        return 'glob', None, 'glob: not expanded'
    if not inside(root, path):
        return 'none', None, 'NO BASE: outside workspace'
    if base_ref and top:
        shown = os.path.relpath(top, os.path.realpath(root)).replace(os.sep, '/')
        return 'git', base_ref, f"git {base_ref} ({'.' if shown == '.' or shown.startswith('..') else shown})"
    ref = os.path.join(backups, plan_id, task_id)
    copy = under(ref, root, path)
    if os.path.exists(copy):
        return 'backup', ref, f'backup {copy}'
    return 'none', None, f'NO BASE: no backup at {copy}'


def unified(name, old, new):
    lines = list(difflib.unified_diff(old.splitlines(), new.splitlines(), f'a/{name}', f'b/{name}', lineterm=''))
    return '\n'.join(lines) if lines else '(no change)'


def fix_round_paths(folder, root):
    """-> sorted paths of the last errors.yaml round whose analysis.fix_list names files, relative to root"""
    path = os.path.join(folder, P.ERRORS)
    try:
        doc = read_yaml(path) if os.path.isfile(path) else None
    except Exception:   # an unreadable errors.yaml means no fix-round paths, not a crash
        doc = None
    rounds = (doc.get('errors') or []) if isinstance(doc, dict) else []
    for r in reversed([r for r in rounds if isinstance(r, dict)]):
        fixes = ((r.get('analysis') or {}).get('fix_list')) or []
        names = [f['path'] for x in fixes if isinstance(x, dict) for f in (x.get('files') or [])
                 if isinstance(f, dict) and isinstance(f.get('path'), str) and f['path']]
        if names:
            return sorted({os.path.relpath(n, root).replace(os.sep, '/') if os.path.isabs(n) else n for n in names})
    return []


def collect_fix(root, base_dir, extra):
    """--base-dir rows: every file under base_dir plus the fix round's paths, each against its copy there or against empty"""
    if not os.path.isdir(base_dir):
        return [dict(path=base_dir, files=[(base_dir, None)], detail='NO BASE: fix-round base dir missing', none=True)]
    rows = []
    for name in sorted(set(list_files(base_dir)) | set(extra)):
        if not inside(root, name):
            rows.append(dict(path=name, files=[(name, None)], detail='NO BASE: outside workspace', none=True))
            continue
        copy, live = os.path.join(base_dir, name), os.path.join(root, name)
        old = read_text(copy) if os.path.isfile(copy) else ''
        new = read_text(live) if os.path.isfile(live) else ''
        if old != new:
            detail = f'fix-round base {copy}' if os.path.isfile(copy) else 'created in fix round: diffs against empty'
            rows.append(dict(path=name, files=[(name, unified(name, old, new))], detail=detail, none=False))
    return rows or [dict(path='(fix round)', files=[('(fix round)', None)], detail='NO BASE: empty fix diff', none=True)]


def collect(root, backups, plan_id, tasks, base_ref):
    """-> rows [dict(path, files [(name, diff|None)], detail, none)] in first-touch order; ValueError when base_ref is not a commit"""
    tops, checked = {}, set()
    rows = []
    for path, tid in first_touch(tasks).items():
        top = git_top(root, path, tops) if base_ref and not any(c in path for c in '*?[') and inside(root, path) else None
        if top and top not in checked:
            if run_git(top, 'rev-parse', '--verify', '--quiet', f'{base_ref}^{{commit}}') is None:
                raise ValueError(f'--base-ref {base_ref}: not a commit in {top}')
            checked.add(top)
        kind, ref, detail = pick_base(root, backups, plan_id, path, tid, base_ref, top)
        files = []
        for name in ([path] if kind in ('glob', 'none') else expand(root, path, kind, ref, top)):
            if kind == 'glob':
                files.append((name, 'glob: not expanded, diff skipped'))
            elif kind == 'none':
                files.append((name, None))
            else:
                live = os.path.join(root, name)
                old = base_text(root, name, kind, ref, top)
                if old and not os.path.isfile(live) and 'node_modules' in name.split('/'):
                    files.append((name, f'{name} deleted ({len(old.splitlines())} lines)'))
                else:
                    files.append((name, unified(name, old, read_text(live) if os.path.isfile(live) else '')))
        rows.append(dict(path=path, files=files, detail=detail, none=kind == 'none'))
    return rows


def cell(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def packet(plan_id, tasks, rows, rnd):
    out = [f'# Review packet: {plan_id} round {rnd}', '', f'Generated {datetime.datetime.now():%Y-%m-%d %H:%M}.', '',
           '## 1. Base of each path', '', '| path | base |', '|---|---|']
    out += [f"| {cell(r['path'])} | {cell(r['detail'])} |" for r in rows]
    out += ['', '## 2. Task, covers, test', '', '| task | covers | test |', '|---|---|---|']
    out += [f"| {tid} | {cell(tasks[tid].get('Covers', ''))} | {cell(tasks[tid].get('Test', ''))} |" for tid in sorted(tasks, key=plan_check.id_key)]
    out += ['', '## 3. Diffs', '']
    for r in rows:
        for name, diff in r['files']:
            out += [f'### {name}', '', '````diff', diff if diff is not None else 'NO BASE: diff skipped', '````', '']
    return '\n'.join(out)


def diff_only(rows, folder, root):
    own = os.path.relpath(os.path.abspath(folder), root).replace(os.sep, '/') + '/'
    out = []
    for r in rows:
        for name, diff in r['files']:
            if not name.startswith(own):
                out += [f'### {name}', '', '````diff', diff if diff is not None else 'NO BASE: diff skipped', '````', '']
    return '\n'.join(out)


def write(path, text):
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix='.review-packet-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    os.chmod(path, 0o644)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('change_dir')
    ap.add_argument('--round', type=int, required=True, dest='rnd')
    ap.add_argument('--backups', default=os.environ.get('AGENT_HUB_BACKUPS') or os.path.expanduser('~/.claude-backups'))
    ap.add_argument('--base-ref')
    ap.add_argument('--base-dir')
    ap.add_argument('--out-dir')
    ap.add_argument('--diff-only-out')
    ap.add_argument('--files', help='comma-separated touched paths; replaces the read of tasks.md')
    ap.add_argument('--root', help='the workspace root; replaces the lookup of an openspec/ ancestor')
    ap.add_argument('--task-id', default='1', help='backup folder of the --files paths (default 1)')
    a = ap.parse_args(argv)
    try:
        if a.files is not None:
            names = [n.strip() for n in a.files.split(',') if n.strip()]
            if not names:
                raise ValueError('--files names no path')
            tasks = {a.task_id: {'Files': ','.join(names)}}
        else:
            tasks = load_tasks(a.change_dir)
        if a.root:
            if not os.path.isdir(a.root):
                raise ValueError(f'--root {a.root}: not a folder')
            root = os.path.abspath(a.root)
        else:
            try:
                root = workspace_root(a.change_dir)
            except ValueError as e:
                raise ValueError(f'{e}; with --files give --root DIR' if a.files is not None else str(e))
    except ValueError as e:
        print(f'review-packet: {e}', file=sys.stderr)
        return 2
    plan_id = os.path.basename(os.path.abspath(a.change_dir))
    try:
        rows = collect_fix(root, a.base_dir, fix_round_paths(a.change_dir, root)) if a.base_dir else collect(root, a.backups, plan_id, tasks, a.base_ref)
    except ValueError as e:
        print(f'review-packet: {e}', file=sys.stderr)
        return 2
    folder = a.out_dir or str(ephemeral_dir(root, plan_id))
    write(os.path.join(folder, f'review-packet-r{a.rnd}.md'), packet(plan_id, {} if a.files is not None else tasks, rows, a.rnd))
    if a.diff_only_out:
        write(a.diff_only_out, diff_only(rows, a.change_dir, root))
    return int(any(r['none'] for r in rows))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
