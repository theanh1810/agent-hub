#!/usr/bin/env python3
"""review-packet: write a batch plan's review packet and a diff-only copy for the independent layer.

usage: review-packet.py PLAN_DIR --round N [--backups DIR] [--base-dir DIR] [--out-dir DIR] [--diff-only-out PATH]

PLAN_DIR holds plan.yaml (split or single-file). The packet is
<root>/.cm-tmp/<plan_id>/review-packet-r<N>.md (plan_paths.ephemeral_dir; --out-dir replaces that folder), where <root> is the
parent of the docs/ folder PLAN_DIR sits in; the change folder and any legacy reviews/ get nothing. It holds (1) a header, (2) a task | AC | case | cmd | exit | met | evidence | note table (the last three from
result.ac_check, `no entry` when an AC has none) and
(3) one unified diff per path any task lists in files[], the validation_strategy.review_deep_paths first.
--diff-only-out writes section (3) alone: no task id, AC or plan text, and none of the plan's own files. A deep path's header
ends with DEEP and carries no reason.

The base of a path is `git show <baseline.head>:<path>` of the first task touching it when <root> is a git work tree
and that task's result.baseline.head is a sha; otherwise <backups>/<first task id>/<path> (default $AGENT_HUB_BACKUPS, else ~/.claude-backups).
A backup copy is looked up by the path relative to <root> when files[].path is absolute. --base-dir DIR (a fix round)
replaces the task paths: it diffs every file under DIR, plus every files[].path of the last PLAN_DIR/errors.yaml round
with a non-empty analysis.fix_list, against its copy DIR/<path relative to <root>>, or against empty when it has none
(created in the fix round); an unchanged path and a path neither under DIR nor in that fix_list are left out. A missing
DIR, or no changed path, is one NO BASE row and exit 1.
A path created by its first task diffs against empty; no base prints NO BASE and skips the diff; a glob path (`*`, `?` or `[`) is not expanded, prints `glob: not expanded` and skips the diff, and is not a NO BASE row. A backup is dated by the creation
time of its <backups>/<task id>/ folder (st_birthtime, st_ctime where a file system keeps none), never by the copied file's mtime,
which `cp -c` keeps from the source; it is flagged OLDER THAN APPROVAL when that time is before plan.yaml approval.at. With no
approval.at the packet says the approval time is unknown and flags nothing. A deleted file under a node_modules/ segment is one
line, `<path> deleted (<n> lines)`, n the line count of its base copy, never its content.
Diffs use difflib only: never /usr/bin/diff and never `git diff`, which the RTK hook rewrites.

Exit 0 written; 1 written, but a NO BASE, `not run` or `no entry` row exists (a glob row is none of them); 2 usage error or unreadable plan.
"""
import argparse
import datetime
import os
import re
import subprocess
import sys
import tempfile
import difflib
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python3 -I leaves the script folder off sys.path
import plan_paths
from plan_paths import ephemeral_dir, workspace_root


def read_yaml(path):
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_plan(plan_dir):
    """-> plan.yaml dict and its tasks (each with its task file merged in); ValueError when unreadable"""
    try:
        idx = read_yaml(os.path.join(plan_dir, 'plan.yaml'))
        tasks = plan_paths.tasks_of(plan_dir, idx, read_yaml)
    except (OSError, UnicodeDecodeError, yaml.YAMLError, TypeError, KeyError) as e:
        raise ValueError(f'{plan_dir}: {type(e).__name__}: {e}')
    if not isinstance(idx, dict) or not all(isinstance(t, dict) and t.get('id') for t in tasks):
        raise ValueError(f'{plan_dir}: plan.yaml or a task file is not a mapping with an id')
    return idx, tasks


def first_touch(tasks):
    """-> {path: (first task, change)} in first-touch order, files[].path of every task deduplicated"""
    seen = {}
    for t in tasks:
        for f in t.get('files') or []:
            if isinstance(f, dict) and f.get('path') and f['path'] not in seen:
                seen[f['path']] = (t, f.get('change'))
    return seen


def run_git(root, *argv):
    """argv list, no shell; -> stdout text or None when git or the object is missing"""
    try:
        p = subprocess.run(['git', '-C', root, *argv], capture_output=True)
    except OSError:
        return None
    return p.stdout.decode('utf-8', 'replace') if p.returncode == 0 else None


def list_files(base):
    return sorted(os.path.relpath(os.path.join(d, n), base) for d, _, names in os.walk(base) for n in names)


def read_text(path):
    with open(path, 'rb') as f:
        return f.read().decode('utf-8', 'replace')


def under(ref, root, name):
    """backup copy of name under ref; an absolute name is taken relative to root, since os.path.join drops ref for it"""
    return os.path.join(ref, os.path.relpath(name, root) if os.path.isabs(name) else name)


def expand(root, path, base_kind, base_ref):
    """-> [(file path, base text or None)] : a directory path becomes the files under it, base side and live side"""
    live = os.path.join(root, path)
    names = set()
    if os.path.isdir(live):
        names |= {os.path.join(path, n) for n in list_files(live)}
    if base_kind == 'git':
        listed = run_git(root, 'ls-tree', '-r', '--name-only', base_ref, '--', path)
        names |= set((listed or '').split('\n')) - {''}
    elif base_kind == 'backup' and os.path.isdir(under(base_ref, root, path)):
        names |= {os.path.join(path, n) for n in list_files(under(base_ref, root, path))}
    return sorted(names) or [path]


def base_text(root, name, kind, ref):
    if kind == 'none':
        return None
    if kind == 'empty':
        return ''
    if kind == 'git':
        return run_git(root, 'show', f'{ref}:{name}') or ''
    p = under(ref, root, name)
    return read_text(p) if os.path.isfile(p) else ''


def pick_base(root, backups, path, task, change, is_git):
    """-> (kind, ref, detail, taken): kind git|backup|empty|glob|none; taken is when a backup folder was created, else ''"""
    if any(c in path for c in '*?['):
        return 'glob', None, 'glob: not expanded', ''
    head = ((task.get('result') or {}).get('baseline') or {}).get('head')
    if change == 'create':
        return 'empty', None, 'created: diffs against empty', ''
    if is_git and isinstance(head, str) and re.fullmatch(r'[0-9a-f]{7,40}', head):
        return 'git', head, f'git {head}', ''
    ref = os.path.join(backups, str(task['id']))
    copy = under(ref, root, path)
    if os.path.exists(copy):
        st = os.stat(ref)
        taken = datetime.datetime.fromtimestamp(getattr(st, 'st_birthtime', st.st_ctime))
        return 'backup', ref, f'backup {copy} folder created {taken:%Y-%m-%d %H:%M}', taken
    return 'none', None, f'NO BASE: no backup at {copy}', ''


def unified(name, old, new):
    if old is None:
        return None
    lines = list(difflib.unified_diff(old.splitlines(), new.splitlines(), f'a/{name}', f'b/{name}', lineterm=''))
    return '\n'.join(lines) if lines else '(no change)'


def approval_time(idx):
    """-> the datetime of plan.yaml approval.at in local time, or None when it is absent or not a datetime"""
    at = (idx.get('approval') or {}).get('at')
    if isinstance(at, str):
        try:
            at = datetime.datetime.fromisoformat(at.replace('Z', '+00:00'))
        except ValueError:
            return None
    if not isinstance(at, datetime.datetime):
        return None
    return at.astimezone().replace(tzinfo=None) if at.tzinfo else at


def approval_note(idx, plan_dir):
    at = approval_time(idx)
    if at:
        return f'Approval time: {at:%Y-%m-%d %H:%M} (plan.yaml approval.at).'
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(plan_dir, 'plan.yaml')))
    return f'Approval time unknown: plan.yaml has no approval.at (plan.yaml was modified {mtime:%Y-%m-%d %H:%M}); no backup is compared.'


def fix_round_paths(plan_dir, root):
    """-> sorted files[].path of the last PLAN_DIR/errors.yaml round whose analysis.fix_list names one, relative to root"""
    path = os.path.join(plan_dir, 'errors.yaml')
    try:
        doc = read_yaml(path) if os.path.isfile(path) else None
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        doc = None
    rounds = (doc.get('errors') or []) if isinstance(doc, dict) else []
    for r in reversed([r for r in rounds if isinstance(r, dict)]):
        fixes = ((r.get('analysis') or {}).get('fix_list')) or []
        names = [f['path'] for x in fixes if isinstance(x, dict) for f in (x.get('files') or [])
                 if isinstance(f, dict) and isinstance(f.get('path'), str) and f['path']]
        if names:
            return sorted({os.path.relpath(n, root) if os.path.isabs(n) else n for n in names})
    return []


def collect_fix(root, base_dir, extra):
    """--base-dir rows: every file under base_dir plus the fix round's paths, each against its copy there or against empty"""
    if not os.path.isdir(base_dir):
        return [dict(path=base_dir, files=[(base_dir, None)], detail='NO BASE: fix-round base dir missing', flag='', none=True)]
    rows = []
    for name in sorted(set(list_files(base_dir)) | set(extra)):
        copy = os.path.join(base_dir, name)
        live = os.path.join(root, name)
        old = read_text(copy) if os.path.isfile(copy) else ''
        new = read_text(live) if os.path.isfile(live) else ''
        if old == new:
            continue
        detail = f'fix-round base {copy}' if os.path.isfile(copy) else 'created in fix round: diffs against empty'
        rows.append(dict(path=name, files=[(name, unified(name, old, new))], detail=detail, flag='', none=False))
    return rows or [dict(path='(fix round)', files=[('(fix round)', None)], detail='NO BASE: empty fix diff', flag='', none=True)]


def collect(root, backups, idx, tasks):
    """-> rows [dict(path, files [(name, diff|None)], detail, flag)] in first-touch order"""
    is_git = (run_git(root, 'rev-parse', '--is-inside-work-tree') or '').strip() == 'true'
    approved = approval_time(idx)
    rows = []
    for path, (task, change) in first_touch(tasks).items():
        kind, ref, detail, taken = pick_base(root, backups, path, task, change, is_git)
        flag = 'OLDER THAN APPROVAL' if taken and approved and taken < approved else ''
        files = []
        for name in expand(root, path, kind, ref):
            if kind == 'glob':
                files.append((name, 'glob: not expanded, diff skipped'))
                continue
            live = os.path.join(root, name)
            old = base_text(root, name, kind, ref)
            if old and not os.path.isfile(live) and 'node_modules' in name.split('/'):
                files.append((name, f'{name} deleted ({len(old.splitlines())} lines)'))
                continue
            new = read_text(live) if os.path.isfile(live) else ''
            files.append((name, unified(name, old, new)))
        rows.append(dict(path=path, files=files, detail=detail, flag=flag, none=kind == 'none'))
    return rows


def deep_reason(deep, name):
    hits = [d for d in deep if isinstance(d, dict) and d.get('path') and
            (name == d['path'] or name.startswith(d['path'].rstrip('/') + '/'))]
    return '; '.join(f"{d.get('section') or 'whole file'}: {d.get('reason')}" for d in hits)


def cell(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def verdict(entry):
    """-> (met, evidence, note) cells of one result.ac_check entry, verbatim; `no entry` when there is none"""
    if entry is None:
        return 'no entry', '', ''
    evidence = entry.get('evidence')
    evidence = evidence if isinstance(evidence, list) else [evidence] if evidence else []
    return str(entry.get('met')).lower(), '; '.join(str(v) for v in evidence), entry.get('note') or ''


def ac_rows(tasks):
    """-> table lines and the number of gaps (`not run` rows)"""
    out, gaps = [], 0
    for t in tasks:
        tid = t['id']
        cmds = [c for c in ((t.get('result') or {}).get('commands') or []) if isinstance(c, dict)]
        checks = (t.get('result') or {}).get('ac_check')
        checks = {e.get('ac'): e for e in checks if isinstance(e, dict)} if isinstance(checks, list) else {}
        cases = [c for c in t.get('test_cases') or [] if isinstance(c, dict)]
        for ac in t.get('acceptance_criteria') or []:
            m = re.match(r'AC-\d+(?=:)', str(ac))
            if not m:
                continue
            keys = {f'{tid}/{m.group(0)}'} | set(re.findall(r'UC-\d+/AC-\d+', str(ac).partition('→')[2]))
            mine = [c for c in cases if keys & {str(x).strip() for x in (c.get('covers_acceptance') if isinstance(c.get('covers_acceptance'), list) else [c.get('covers_acceptance')])}]
            entry = checks.get(m.group(0))
            gaps += entry is None
            if not mine:
                out.append((tid, m.group(0), 'no case', '', '') + verdict(entry))
            for c in mine:
                ran = [x for x in cmds if x.get('tc_id') == c.get('id')]
                if not ran:
                    gaps += 1
                    out.append((tid, m.group(0), c.get('id'), 'not run', '') + verdict(entry))
                out += [(tid, m.group(0), c.get('id'), x.get('cmd'), x.get('exit')) + verdict(entry) for x in ran]
    lines = ['| task | AC | case | cmd | exit | met | evidence | note |', '|---|---|---|---|---|---|---|---|']
    lines += ['| ' + ' | '.join(cell(v) for v in r) + ' |' for r in out]
    return lines, gaps


def packet(idx, tasks, rows, deep, rnd, note):
    table, gaps = ac_rows(tasks)
    order = sorted(((deep_reason(deep, n), n, d) for r in rows for n, d in r['files']), key=lambda x: not x[0])
    out = [f"# Review packet: {idx.get('plan_id')} round {rnd}", '',
           f"Generated {datetime.datetime.now():%Y-%m-%d %H:%M}.", '', note, '', '## 1. Base of each path', '',
           '| path | base |', '|---|---|']
    out += [f"| {cell(r['path'])} | {cell(r['detail'])}{' ' + r['flag'] if r['flag'] else ''} |" for r in rows]
    out += ['', '## 2. Task, AC, case, command, exit', ''] + table + ['', '## 3. Diffs', '']
    for why, name, diff in order:
        out += [f"### {name}" + (f" DEEP ({why})" if why else ''), '',
                '````diff', diff if diff is not None else 'NO BASE: diff skipped', '````', '']
    return '\n'.join(out), gaps


def diff_only(rows, deep, plan_dir, root):
    own = os.path.relpath(os.path.abspath(plan_dir), root) + '/'
    items = [(deep_reason(deep, n), n, d) for r in rows for n, d in r['files'] if not n.startswith(own)]
    out = []
    for why, name, diff in sorted(items, key=lambda x: not x[0]):
        out += [f'### {name}' + (' DEEP' if why else ''), '', '````diff', diff if diff is not None else 'NO BASE: diff skipped', '````', '']
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
    ap.add_argument('plan_dir')
    ap.add_argument('--round', type=int, required=True, dest='rnd')
    ap.add_argument('--backups', default=os.environ.get('AGENT_HUB_BACKUPS') or os.path.expanduser('~/.claude-backups'))
    ap.add_argument('--base-dir')
    ap.add_argument('--out-dir')
    ap.add_argument('--diff-only-out')
    a = ap.parse_args(argv)
    try:
        idx, tasks = load_plan(a.plan_dir)
        root = workspace_root(a.plan_dir)
    except ValueError as e:
        print(f'review-packet: {e}', file=sys.stderr)
        return 2
    deep = ((idx.get('validation_strategy') or {}).get('review_deep_paths')) or []
    rows = collect_fix(root, a.base_dir, fix_round_paths(a.plan_dir, root)) if a.base_dir else collect(root, a.backups, idx, tasks)
    text, gaps = packet(idx, tasks, rows, deep, a.rnd, approval_note(idx, a.plan_dir))
    try:
        folder = a.out_dir or str(ephemeral_dir(root, str(idx.get('plan_id'))))
    except ValueError as e:
        print(f'review-packet: {e}', file=sys.stderr)
        return 2
    write(os.path.join(folder, f'review-packet-r{a.rnd}.md'), text)
    if a.diff_only_out:
        write(a.diff_only_out, diff_only(rows, deep, a.plan_dir, root))
    return int(bool(gaps or any(r['none'] for r in rows)))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
