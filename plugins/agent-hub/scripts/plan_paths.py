"""Path helpers shared by plan-locate.py, plan-verify.py, review-packet.py and change-map.py: the workspace root, the plan folder of an id, its record, and an old path's new location."""
import csv
import os
import re
from pathlib import Path


def workspace_root(path):
    p = os.path.abspath(path)
    while p != os.path.dirname(p):
        if os.path.basename(p) == 'docs':
            return os.path.dirname(p)
        p = os.path.dirname(p)
    raise ValueError(f'{path} is not inside a docs/ folder')


PLAN_ID = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
CHANGE_PATTERNS = ('docs/changes/{id}', 'docs/changes/archive/{id}', 'docs/changes/archive/????-??-??-{id}')   # searched first
LEGACY_PATTERNS = ('docs/plan/{id}', 'docs/specs/changes/{id}', 'docs/specs/changes/archive/{id}',
                   'docs/specs/changes/archive/????-??-??-{id}')   # the four of plan-locate.py today
MAP_FILE = 'docs/changes/MIGRATION-MAP.tsv'   # header old_path, new_path, action; new_path '-' means the path was deleted
LEGACY_ROOTS = ('docs/plan', 'docs/analysis', 'docs/design', 'docs/specs/changes', 'docs/adhoc', 'docs/integration', 'docs/reviews/adhoc')

# long-lived project docs owned by no change: kept in place, no row; keyed by the workspace directory name.
# Empty in the shipped package; a project lists its own paths here.
KEEP_IN_PLACE = {}

# The fixed run-file names of a change folder (design.md, Run files). Nothing outside this set is written there.
REVIEW_FILE = 'review.md'
EVIDENCE_DIR = 'evidence'
CHANGE_MAP_MD = 'change-map.md'
EPHEMERAL_DIR = '.cm-tmp'   # change-map.json and review packets live in <root>/.cm-tmp/<plan_id>/


def ephemeral_dir(root, plan_id):
    """-> Path of the throwaway folder of a plan, root/.cm-tmp/{plan_id}; not created here."""
    return Path(root) / EPHEMERAL_DIR / plan_id


def tasks_of(plan_dir, idx, read):
    """-> the task dicts of a plan index. Inline tasks come first: an entry holds the task itself and is returned as a copy. Only a plan
    that has a tasks/ folder (the legacy layout) and an entry naming a file reads that file through read(path), which may raise OSError
    or yaml.YAMLError as before."""
    split = os.path.isdir(os.path.join(plan_dir, 'tasks'))
    return [read(os.path.join(plan_dir, e['file'])) if split and isinstance(e, dict) and 'file' in e else dict(e) for e in idx['tasks']]


def plan_dir(root, plan_id):
    """-> Path of the one folder holding plan.yaml for plan_id: search CHANGE_PATTERNS, then LEGACY_PATTERNS, under root (str or Path).
    The id must match PLAN_ID else ValueError('plan id must be lowercase kebab-case'). Folders are compared resolved (one symlink twin
    counts once). Zero or more than one folder raises ValueError(f'{plan_id}: expected one plan, found {n}: {[plan.yaml paths]}'),
    the text plan-locate.py raised before. A folder without plan.yaml is not returned (see change_dir)."""
    if not PLAN_ID.fullmatch(plan_id):
        raise ValueError('plan id must be lowercase kebab-case')
    root = Path(root)
    paths = sorted({p.resolve() for pattern in CHANGE_PATTERNS + LEGACY_PATTERNS
                    for p in root.glob(pattern.format(id=plan_id) + '/plan.yaml') if p.is_file()})
    if len(paths) != 1:
        raise ValueError(f'{plan_id}: expected one plan, found {len(paths)}: {[str(p) for p in paths]}')
    return paths[0].parent


def change_dir(root, plan_id):
    """-> Path of the change folder for plan_id among CHANGE_PATTERNS (plan.yaml or not), None when there is none; more than one
    raises ValueError(f'{plan_id}: expected one change folder, found {n}: {[paths]}'). A folder without plan.yaml (a strong key with
    no plan) is returned here and nowhere else."""
    if not PLAN_ID.fullmatch(plan_id):
        raise ValueError('plan id must be lowercase kebab-case')
    root = Path(root)
    dirs = sorted({p.resolve() for pattern in CHANGE_PATTERNS for p in root.glob(pattern.format(id=plan_id)) if p.is_dir()})
    if len(dirs) > 1:
        raise ValueError(f'{plan_id}: expected one change folder, found {len(dirs)}: {[str(p) for p in dirs]}')
    return dirs[0] if dirs else None


def record(plan_dir, root, plan_id):
    """-> Path of the one machine record, None when none: the candidates in order are {plan_dir}/design.yaml, {plan_dir}/{id}.yaml (a
    migrated record keeps its name), the legacy analysis folder's {id}.yaml, root/docs/brainstorm/{id}.yaml. More than one present raises
    ValueError(f'{plan_id}: multiple machine records: {[str(p) for p in existing]}'), the text plan-locate.py raised before."""
    root = Path(root)
    candidates = [Path(plan_dir) / 'design.yaml', Path(plan_dir) / f'{plan_id}.yaml',
                  root / f'docs/analysis/{plan_id}.yaml',   # scrub-allow: legacy record location read when present
                  root / f'docs/brainstorm/{plan_id}.yaml']
    existing = [p for p in candidates if p.is_file()]
    if len(existing) > 1:
        raise ValueError(f'{plan_id}: multiple machine records: {[str(p) for p in existing]}')
    return existing[0] if existing else None


def resolve(root, old_path):
    """-> the new path (relative to root, as stored in MAP_FILE) of old_path, else None. old_path may be absolute under root (made
    relative first). Rows come from root/MAP_FILE (no file: None). An exact old_path row wins; else the row whose old_path, taken as
    a folder (a trailing '/' ignored, matched on whole path components), is the longest ancestor of old_path gives new_path + the rest;
    a row whose new_path is '-' (deleted) gives None."""
    root = Path(root)
    map_file = root / MAP_FILE
    if not map_file.is_file():
        return None
    old = str(old_path)
    if os.path.isabs(old):
        old = os.path.relpath(old, str(root))
    old = old.replace(os.sep, '/')
    with open(map_file, encoding='utf-8', newline='') as fh:
        rows = [(r['old_path'], r['new_path']) for r in csv.DictReader(fh, delimiter='\t') if r.get('old_path')]
    for src, dst in rows:
        if src == old:
            return None if dst == '-' else dst
    best = None
    for src, dst in rows:
        folder = src.rstrip('/')
        if old.startswith(folder + '/') and (best is None or len(folder) > len(best[0])):
            best = (folder, dst)
    if best is None or best[1] == '-':
        return None
    return best[1].rstrip('/') + old[len(best[0]):]


def legacy_roots_reappeared(root):
    """-> the entries of LEGACY_ROOTS that exist as directories under root, in LEGACY_ROOTS order, but only when root/MAP_FILE exists
    (a workspace not yet migrated returns []). A root counts when it is empty, or holds an entry (folder, file or symlink, os.walk)
    that is neither equal to or under a KEEP_IN_PLACE path of Path(root).name nor a folder on the way to one"""
    root = Path(root)
    if not (root / MAP_FILE).is_file():
        return []
    kept = KEEP_IN_PLACE.get(root.name, ())
    ignorable = lambda rel: any(rel == k or rel.startswith(k + '/') or k.startswith(rel + '/') for k in kept)
    found = []
    for r in LEGACY_ROOTS:
        top = root / r
        if not top.is_dir():
            continue
        entries = [os.path.relpath(os.path.join(dp, n), root).replace(os.sep, '/') for dp, ds, fs in os.walk(top) for n in ds + fs]
        if not entries or not all(ignorable(e) for e in entries):
            found.append(r)
    return found


def sidecar_dir(root, plan_id):
    """-> Path of the folder that holds a plan's errors.yaml, change-map.* and reviews/ (the one place the legacy sidecar is chosen):
    plan_dir(root, plan_id) lies under docs/specs/changes/ (archive included) and root/docs/plan/{plan_id} is a directory -> that
    directory; every other plan -> plan_dir(root, plan_id) itself. It never builds a docs/plan path for a docs/changes or docs/plan
    plan, and raises what plan_dir raises."""
    root = Path(root)
    folder = plan_dir(root, plan_id)
    legacy = (root / 'docs/plan' / plan_id)
    if (root / 'docs/specs/changes').resolve() in folder.parents and legacy.is_dir():
        return legacy
    return folder

