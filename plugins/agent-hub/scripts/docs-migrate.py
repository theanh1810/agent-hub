#!/usr/bin/env python3
"""docs-migrate: list every move, merge, prune, delete and stop for one workspace's agent-written docs.

T1 is the dry run only: nothing under the workspace changes (--apply, --verify, MIGRATION-MAP.tsv and --delete arrive in T2).
Target layout: docs/changes/<id>/ per change (<id> = plan_id), docs/changes/archive/<folder>/, docs/changes/adhoc/ (legacy adhoc
files, flat, names unchanged), docs/brainstorm/ (work with no change id, names unchanged).

usage: docs-migrate.py --workspace ROOT --out DIR [--profile prune|move-only] [--keep NAME]... [--dry-run]
  --profile move-only (default) writes no prune-list.tsv and no delete-list.tsv; --profile prune writes both.
  Outputs under --out: migration-map.tsv, weak.tsv, stops.tsv, summary.json, ids.txt (the id set, sorted, one per line) and, for
  profile prune, prune-list.tsv and delete-list.tsv.
  --keep NAME (repeatable): a ROOT/.cm-tmp entry the delete list never names.
exit codes: 0 plan written, no stop; 1 stops.tsv has rows (nothing else claims success); 2 refused (--out under ROOT/docs or
ROOT/.cm-tmp, bad arguments), nothing written.
Never opened: any file under docs/archives or docs/test-evidence (os.scandir and os.lstat only: names, file count, bytes);
docs/requietment is never listed.
"""
import argparse, csv, hashlib, json, os, re, shlex, shutil, subprocess, sys, tarfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))   # python3 -I leaves the script folder off sys.path, as plan-locate.py does
from plan_paths import KEEP_IN_PLACE   # the one copy; plan_paths.legacy_roots_reappeared reads it too

EXIT_OK, EXIT_STOPS, EXIT_REFUSED = 0, 1, 2
PROFILES = ('move-only', 'prune')
STAT_ONLY = ('docs/archives', 'docs/test-evidence')    # counted with os.lstat only, never opened
NEVER_LISTED = ('docs/requietment',)
# unchanged, no row: the live layer docs/specs (everything under it except docs/specs/changes, which is mapped)
UNCHANGED = ('docs/specs', 'docs/errors', 'docs/deferred-backlog.md', 'docs/adr', 'docs/devops', 'docs/audits',
             'docs/thresholds.yaml', 'docs/reviews/INDEX.md', 'docs/reviews/baselines',
             'docs/changes', 'docs/brainstorm')   # the last two: already migrated, so a second run maps nothing
ARCHIVE_DATE = re.compile(r'^\d{4}-\d{2}-\d{2}-')   # stripped from an archive folder name to get its id
# the id set: folder names under these roots (archive date stripped) plus every top-level plan_id value of docs/analysis/*.yaml (scrub-allow: legacy folder name)
ID_ROOTS = ('docs/plan', 'docs/specs/changes', 'docs/specs/changes/archive')
# strong keys, strongest first; only a strong key maps a file into docs/changes/<id>/ automatically
STRONG_KEYS = ('record-id',     # the file's top-level plan_id or slug value is in the id set
               'design-row',    # a DESIGN.md row labelled 'Ma plan' or 'Plan:' (with the Vietnamese diacritics) whose value is in the id set
               'design-ref',    # a design folder cited by design_brief_ref in the task files of exactly one id
               'folder-name')   # the containing folder name equals an id
# weak (never auto-mapped): a basename prefix '<id>-' or a topic resemblance -> docs/brainstorm/ keeping the name, one weak.tsv row
ACTIONS = ('move', 'merge', 'prune', 'delete', 'keep')   # keep: counted in summary.json only, no row in migration-map.tsv
STOPS = ('no-rule', 'two-sources', 'target-exists', 'archive-twin', 'forbidden-source', 'prune-protected')
MAP_COLUMNS = ('old', 'new', 'action', 'key', 'strength')    # strength: strong | weak | rule (decided by path structure, no key)
WEAK_COLUMNS = ('path', 'candidate_ids', 'why')
STOP_COLUMNS = ('path', 'stop', 'detail')
PRUNE_COLUMNS = ('category', 'path', 'files', 'bytes', 'citations', 'in_backup')   # files is 1 per row; in_backup is always 'yes' (the U10 tar holds them)
DELETE_COLUMNS = ('category', 'path', 'files', 'bytes')      # category cm-tmp|test-evidence|archives; files and bytes from os.lstat only; one row per .cm-tmp entry, docs/test-evidence, docs/archives
# APPROVED.tsv (T2 --delete) is the live prune-list.tsv and delete-list.tsv rows concatenated under the header category, path, files, bytes
# the six U8 categories: amend = basename amend-*.md; bak = suffix .bak; evidence / validation = every file under a folder of that
# name; results = basename results.md; image = images beyond KEEP_IMAGES per group
PRUNE_CATEGORIES = ('amend', 'bak', 'evidence', 'validation', 'results', 'image')
PRUNE_ROOTS = ('docs/plan', 'docs/specs/changes', 'docs/reviews', 'docs/changes')   # docs/changes so T2's --delete recomputes on the moved tree
IMAGE_SUFFIXES = ('.png', '.jpg', '.jpeg', '.webp', '.gif')
KEEP_IMAGES = 3


@dataclass
class Plan:
    root: str = ''
    rows: list = field(default_factory=list)       # (old, new, action, key, strength)
    weak: list = field(default_factory=list)       # (path, candidate_ids, why)
    stops: list = field(default_factory=list)      # (path, stop, detail)
    prune: list = field(default_factory=list)      # (path, category, bytes, citations, 'yes')
    delete: list = field(default_factory=list)     # (category, path, files, bytes)
    stat_only: dict = field(default_factory=dict)  # 'docs/archives' -> {'files': n, 'bytes': b}
    ids: list = field(default_factory=list)        # the id set (keys of id_set), sorted; written as ids.txt
    keep: list = field(default_factory=list)       # (path, bytes) of files that stay: counted in summary.json only
    sizes: dict = field(default_factory=dict)      # old path -> bytes (os.lstat), for summary.json
    existing: set = field(default_factory=set)     # casefolded relative paths of every inventoried file


ARCHIVE_ROOT = 'docs/specs/changes/archive'
VALID_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]*')


def under(path, top):
    """True when path equals top or lies inside it (both resolved)"""
    path, top = Path(path).resolve(), Path(top).resolve()
    return path == top or top in path.parents


def rel_under(rel, top):
    return rel == top or rel.startswith(top + '/')


def archive_twin(names, plan_id):
    """the archive folder names that are the twin of plan_id: exactly <id> or <YYYY-MM-DD>-<id>; a longer name never matches"""
    return [n for n in names if n == plan_id or re.fullmatch(r'\d{4}-\d{2}-\d{2}-' + re.escape(plan_id), n)]


def change_home(i, ids, ctx):
    """-> 'docs/changes/<i>' or 'docs/changes/archive/<twin>', or a stop dict: the one folder where every file of change i lands.
    docs/plan/<i>/plan.yaml present, or docs/specs/changes in the id's roots -> docs/changes/<i>; the id's plan archived (ARCHIVE_ROOT in
    its roots) -> docs/changes/archive/<twin> from archive_twin() (0 or more than one twin: stop 'archive-twin'); else docs/changes/<i>"""
    roots = ids.get(i, {}).get('roots', [])
    if f'docs/plan/{i}/plan.yaml' in ctx['files'] or 'docs/specs/changes' in roots:
        return f'docs/changes/{i}'
    if ARCHIVE_ROOT in roots:
        twin = archive_twin(ctx['archive_names'], i)
        if len(twin) != 1:
            return {'stop': 'archive-twin', 'detail': f'{len(twin)} archive folders match {i}: {",".join(twin)}'}
        return f'docs/changes/archive/{twin[0]}'
    return f'docs/changes/{i}'


def count_tree(path):
    """-> (files, bytes, flagged): os.scandir and os.lstat only, so no file is ever opened; flagged is True when the tree holds a
    *.lock folder or a progress.yaml"""
    n = size = 0
    flagged = False
    stack = [path]
    while stack:
        with os.scandir(stack.pop()) as it:
            for e in it:
                if e.is_dir(follow_symlinks=False):
                    flagged = flagged or e.name.endswith('.lock')
                    stack.append(e.path)
                else:
                    flagged = flagged or e.name == 'progress.yaml'
                    n += 1
                    size += e.stat(follow_symlinks=False).st_size
    return n, size, flagged


def inventory(root):
    """-> (files, stat_only): every file under ROOT/docs as a relative posix path, skipping STAT_ONLY (counted with os.lstat:
    {'docs/archives': {'files': n, 'bytes': b}}, recursively, never opened) and NEVER_LISTED (not even listed)"""
    files, stat_only = [], {}

    def walk(rel):
        with os.scandir(root / rel) as it:
            entries = sorted(it, key=lambda e: e.name)
        for e in entries:
            child = f'{rel}/{e.name}'
            if child in NEVER_LISTED:
                continue
            if child in STAT_ONLY:
                if e.is_dir(follow_symlinks=False):
                    n, size, _ = count_tree(e.path)
                    stat_only[child] = {'files': n, 'bytes': size}
                continue
            if e.is_dir(follow_symlinks=False):
                walk(child)
            else:
                files.append(child)

    walk('docs')
    return files, stat_only


def load_yaml(root, rel, cache):
    if rel not in cache:
        try:
            cache[rel] = yaml.safe_load((Path(root) / rel).read_text(encoding='utf-8'))
        except Exception:
            cache[rel] = None
    return cache[rel]


def id_set(root, files, cache=None):
    """-> {id: {'roots': [...], 'archived': bool}} from ID_ROOTS folder names (ARCHIVE_DATE stripped) and every top-level plan_id
    of the legacy analysis `*.yaml` records, each read with yaml.safe_load"""
    cache = {} if cache is None else cache
    ids = {}

    def add(i, where):
        d = ids.setdefault(i, {'roots': [], 'archived': False})
        if where not in d['roots']:
            d['roots'].append(where)

    for f in files:
        p = f.split('/')
        if p[:2] == ['docs', 'plan'] and len(p) > 3:
            add(p[2], 'docs/plan')
        elif p[:3] == ['docs', 'specs', 'changes']:
            if p[3:4] == ['archive']:
                if len(p) > 5:
                    add(ARCHIVE_DATE.sub('', p[4]), ARCHIVE_ROOT)
            elif len(p) > 4:
                add(p[3], 'docs/specs/changes')
        elif len(p) == 3 and p[:2] == ['docs', 'analysis'] and p[2].endswith(('.yaml', '.yml')):
            doc = load_yaml(root, f, cache)
            pid = doc.get('plan_id') if isinstance(doc, dict) else None
            if isinstance(pid, str) and VALID_ID.fullmatch(pid):
                add(pid, 'docs/analysis')
    for d in ids.values():
        d['archived'] = ARCHIVE_ROOT in d['roots'] and 'docs/specs/changes' not in d['roots']
    return ids


def owner_id(rel, ids):
    """the change id a file belongs to by its path, or None"""
    p = rel.split('/')
    if p[:2] == ['docs', 'plan'] and len(p) > 3:
        return p[2]
    if p[:3] == ['docs', 'specs', 'changes']:
        if p[3:4] == ['archive']:
            return ARCHIVE_DATE.sub('', p[4]) if len(p) > 5 else None
        return p[3] if len(p) > 4 else None
    if p[:2] == ['docs', 'changes']:
        if p[2:3] == ['archive']:
            return ARCHIVE_DATE.sub('', p[3]) if len(p) > 4 else None
        return p[2] if len(p) > 3 else None
    if p[:2] == ['docs', 'reviews'] and len(p) > 2:
        key = p[2] if len(p) > 3 else re.sub(r'\.[^.]+$', '', p[2])
        return key if key in ids else None
    return None


DESIGN_ROW = re.compile(r'^\s*\|?\s*\**(?:m[\u00e3a] plan|plan)\**\s*[:|]\s*(.+)$', re.IGNORECASE)


def design_owner(slug, ids, ctx):
    """-> (id, key) for a design folder by its strongest key, or None: design-row, design-ref, folder-name"""
    cache = ctx['design_cache']
    if slug in cache:
        return cache[slug]
    hit = None
    brief = f'docs/design/{slug}/DESIGN.md'
    if brief in ctx['files']:
        try:
            text = (ctx['root'] / brief).read_text(encoding='utf-8', errors='replace')
        except OSError:
            text = ''
        found = set()
        for line in text.splitlines():
            m = DESIGN_ROW.match(line)
            if m:
                found |= {t for t in re.findall(r'[a-z0-9]+(?:-[a-z0-9]+)*', m.group(1).lower()) if t in ids}
        if len(found) == 1:
            hit = (next(iter(found)), 'design-row')
    if hit is None and len(ctx['design_refs'].get(slug, ())) == 1:
        hit = (next(iter(ctx['design_refs'][slug])), 'design-ref')
    if hit is None and slug in ids:
        hit = (slug, 'folder-name')
    cache[slug] = hit
    return hit


def prefix_candidates(stem, ids):
    return sorted(i for i in ids if stem.startswith(i + '-'))


def map_file(rel, ids, ctx):
    """-> (new, action, key, strength) or {'stop': name, 'detail': text}, the first rule that matches:
    docs/specs/changes/archive/<f>/<r> -> docs/changes/archive/<f>/<r> (move)
    docs/specs/changes/<id>/<r>        -> docs/changes/<id>/<r> (move)
    docs/plan/<id>/<r> where docs/plan/<id>/plan.yaml exists -> docs/changes/<id>/<r> (move)
    docs/plan/<id>/<r> sidecar (no plan.yaml) -> docs/changes/<id>/<r> when docs/specs/changes/<id>/ exists, or
        docs/changes/archive/<twin>/<r> where <twin> comes from archive_twin() over docs/specs/changes/archive (merge);
        the id has no change folder at all -> docs/changes/<id>/<r> (a new folder without plan.yaml, move)
    every strong-key row below lands in change_home(<id>): docs/changes/<id>/, or docs/changes/archive/<twin>/ when the id's plan is archived;
    docs/analysis/<slug>.* with a STRONG_KEYS key -> <home>/<basename>; docs/analysis/<id>/<r> -> <home>/<r>; (scrub-allow: legacy folder paths)
        no key or a weak one, docs/analysis/assets, docs/analysis/scout, rejected-requests.md -> docs/brainstorm/<same relative path> (scrub-allow: legacy folder paths)
    docs/design/<slug>/<r> -> <home>/design/<slug>/<r> with a strong key, else docs/brainstorm/<slug>/design/<r>
    docs/reviews/<id>/<r> and docs/reviews/<id>.md -> <home>/reviews/<name>; a prefix-only name is weak; other
        docs/reviews/<x> with no id -> docs/brainstorm/<x>
    docs/reviews/adhoc/<f> and docs/adhoc/<f> -> docs/changes/adhoc/<f> (flat, name unchanged)
    docs/integration/<f> -> docs/brainstorm/<f> (weak: topic only)
    UNCHANGED paths and this workspace's KEEP_IN_PLACE paths -> action keep; a path no rule covers -> stop 'no-rule'; a source under docs/archives or docs/requietment ->
    stop 'forbidden-source'"""
    p = rel.split('/')
    rest = lambda n: '/'.join(p[n:])
    rule = lambda new, action='move': (new, action, 'path', 'rule')
    stop = lambda name, detail='': {'stop': name, 'detail': detail}
    brainstorm = lambda new: (new, 'move', 'none', 'rule')
    if any(rel_under(rel, t) for t in ('docs/archives', 'docs/requietment')):
        return stop('forbidden-source', 'a source under archives/ or requietment/')
    if p[:3] == ['docs', 'specs', 'changes']:
        if p[3:4] == ['archive'] and len(p) > 5:
            return rule('docs/changes/archive/' + rest(4))
        if p[3:4] != ['archive'] and len(p) > 4:
            return rule('docs/changes/' + rest(3))
        return stop('no-rule', 'a file directly under docs/specs/changes')
    if any(rel_under(rel, u) for u in UNCHANGED):
        return (rel, 'keep', 'path', 'rule')
    if p[:2] == ['docs', 'plan'] and len(p) > 3:
        i, r = p[2], rest(3)
        home = change_home(i, ids, ctx)
        if isinstance(home, dict):
            return home
        roots = ids.get(i, {}).get('roots', [])
        merge = f'docs/plan/{i}/plan.yaml' not in ctx['files'] and ('docs/specs/changes' in roots or ARCHIVE_ROOT in roots)
        return rule(f'{home}/{r}', 'merge' if merge else 'move')
    if p[:2] == ['docs', 'analysis'] and len(p) > 2:
        if p[2] in ('assets', 'scout') or rel == 'docs/analysis/rejected-requests.md':  # scrub-allow: legacy folder path the migration reads
            return brainstorm('docs/brainstorm/' + rest(2))
        if len(p) == 3:
            doc = load_yaml(ctx['root'], rel, ctx['cache']) if p[2].endswith(('.yaml', '.yml')) else None
            vals = [doc.get(k) for k in ('plan_id', 'slug')] if isinstance(doc, dict) else []
            for v in vals:
                if isinstance(v, str) and v in ids:
                    home = change_home(v, ids, ctx)
                    return home if isinstance(home, dict) else (f'{home}/{p[2]}', 'move', 'record-id', 'strong')
            stem = re.sub(r'\.[^.]+$', '', p[2])
            cands = sorted(set(prefix_candidates(stem, ids)) | {c for v in vals if isinstance(v, str) for c in prefix_candidates(v, ids)})
            if cands:
                ctx['weak'][rel] = (','.join(cands), 'basename or slug starts with a known id; prefix is not a key')
                return ('docs/brainstorm/' + p[2], 'move', 'prefix', 'weak')
            return brainstorm('docs/brainstorm/' + p[2])
        if p[2] in ids:
            home = change_home(p[2], ids, ctx)
            return home if isinstance(home, dict) else (f'{home}/{rest(3)}', 'move', 'folder-name', 'strong')
        return brainstorm('docs/brainstorm/' + rest(2))
    if p[:2] == ['docs', 'design'] and len(p) > 3:
        hit = design_owner(p[2], ids, ctx)
        if hit:
            home = change_home(hit[0], ids, ctx)
            return home if isinstance(home, dict) else (f'{home}/design/{p[2]}/{rest(3)}', 'move', hit[1], 'strong')
        return brainstorm(f'docs/brainstorm/{p[2]}/design/{rest(3)}')
    if p[:3] == ['docs', 'reviews', 'adhoc'] and len(p) > 3:
        return rule('docs/changes/adhoc/' + p[-1])
    if p[:2] == ['docs', 'reviews'] and len(p) > 3:
        if p[2] in ids:
            home = change_home(p[2], ids, ctx)
            return home if isinstance(home, dict) else (f'{home}/reviews/{rest(3)}', 'move', 'folder-name', 'strong')
        return brainstorm('docs/brainstorm/' + rest(2))
    if p[:2] == ['docs', 'reviews'] and len(p) == 3:
        stem = re.sub(r'\.[^.]+$', '', p[2])
        if stem in ids:
            home = change_home(stem, ids, ctx)
            return home if isinstance(home, dict) else (f'{home}/reviews/{p[2]}', 'move', 'folder-name', 'strong')
        cands = prefix_candidates(stem, ids)
        if cands:
            ctx['weak'][rel] = (','.join(cands), 'basename starts with a known id; prefix is not a key')
            return ('docs/brainstorm/' + p[2], 'move', 'prefix', 'weak')
        return brainstorm('docs/brainstorm/' + p[2])
    if p[:2] == ['docs', 'adhoc'] and len(p) > 2:
        return rule('docs/changes/adhoc/' + p[-1])
    if p[:2] == ['docs', 'integration'] and len(p) > 2:
        ctx['weak'][rel] = ('', 'topic only: no id key')
        return ('docs/brainstorm/' + rest(2), 'move', 'topic', 'weak')
    if any(rel_under(rel, k) for k in KEEP_IN_PLACE.get(Path(ctx['root']).name, ())):
        return (rel, 'keep', 'path', 'rule')
    return stop('no-rule', 'no rule of the target layout covers this path')


def read_lines(root, rel, cache):
    if rel not in cache:
        try:
            cache[rel] = (Path(root) / rel).read_text(encoding='utf-8', errors='replace').splitlines()
        except OSError:
            cache[rel] = []
    return cache[rel]


def citations(root, path, files, cache=None, ids=None):
    """number of lines, summed over the .md and .yaml files of the change that owns path (its docs/plan or docs/specs/changes or
    docs/changes folder, the docs/plan sidecar of the same id, docs/reviews/<id>*), that contain the basename of path"""
    cache = {} if cache is None else cache
    ids = ids if ids is not None else {owner_id(f, {}) for f in files}
    owner = owner_id(path, ids)
    if owner is None:
        return 0
    pat = re.compile(r'(?<![\w.-])' + re.escape(path.rsplit('/', 1)[-1]) + r'(?![\w-])')
    total = 0
    for f in files:
        if f.endswith(('.md', '.yaml', '.yml')) and owner_id(f, ids) == owner:
            total += sum(1 for line in read_lines(root, f, cache) if pat.search(line))
    return total


def prune_category(rel):
    p = rel.split('/')
    name = p[-1]
    if re.fullmatch(r'amend-.*\.md', name):
        return 'amend'
    if name.endswith('.bak'):
        return 'bak'
    if 'evidence' in p[:-1]:
        return 'evidence'
    if 'validation' in p[:-1]:
        return 'validation'
    if name == 'results.md':
        return 'results'
    if name.lower().endswith(IMAGE_SUFFIXES) and 'assets' in p[:-1]:
        return 'image'
    return None


def prune_list(root, files, plan):
    """profile prune: one row per file of PRUNE_CATEGORIES under PRUNE_ROOTS. Image group = the first path segment under an
    assets/ folder, counted recursively; a file lying directly in assets/ is never selected; a group of KEEP_IMAGES or fewer is
    untouched; otherwise rank by citations (descending) then mtime (newest first), keep the top KEEP_IMAGES, list the rest.
    docs/reviews/baselines is never listed. A candidate named by a plan.yaml tasks[].file value, or lying under a tasks/ folder,
    adds the stop 'prune-protected' instead of a row"""
    root = Path(root)
    pool = [f for f in files if any(rel_under(f, r) for r in PRUNE_ROOTS) and not rel_under(f, 'docs/reviews/baselines')]
    ids = {owner_id(f, {}) for f in pool}
    ids.discard(None)
    ids |= {owner_id(f, {}) for f in files if f.startswith('docs/reviews/')} - {None}
    cache, named = {}, set()
    for f in pool:
        if f.rsplit('/', 1)[-1] == 'plan.yaml':
            doc = load_yaml(root, f, cache)
            tasks = doc.get('tasks') if isinstance(doc, dict) else None
            for t in tasks if isinstance(tasks, list) else []:
                if isinstance(t, dict) and isinstance(t.get('file'), str):
                    named.add(os.path.normpath(os.path.join(os.path.dirname(f), t['file'])).replace(os.sep, '/'))
    selected, groups = [], {}
    for f in pool:
        cat = prune_category(f)
        if cat is None:
            continue
        if cat != 'image':
            selected.append((f, cat, 0))
            continue
        p = f.split('/')
        k = p.index('assets')
        if len(p) > k + 2:   # a file lying directly in assets/ is never selected
            groups.setdefault('/'.join(p[:k + 2]), []).append(f)
    lines_cache = {}
    for members in groups.values():
        if len(members) <= KEEP_IMAGES:
            continue
        ranked = sorted(((citations(root, f, files, lines_cache, ids), os.lstat(root / f).st_mtime, f) for f in members),
                        key=lambda t: (-t[0], -t[1], t[2]))
        selected += [(f, 'image', c) for c, _, f in ranked[KEEP_IMAGES:]]
    for f, cat, cit in sorted(selected):
        if f in named or 'tasks' in f.split('/')[:-1]:
            plan.stops.append((f, 'prune-protected', 'named by a plan.yaml tasks[].file value or under a tasks/ folder'))
            continue
        plan.prune.append((f, cat, os.lstat(root / f).st_size, cit, 'yes'))


def delete_list(root, keep, stat_only=None):
    """profile prune: one row per ROOT/.cm-tmp entry not named in keep, plus docs/test-evidence and docs/archives, with file
    count and bytes from os.lstat; an entry holding a *.lock folder or progress.yaml is a stop 'forbidden-source'.
    -> (rows (category, path, files, bytes), stops)"""
    rows, stops = [], []
    tmp = Path(root) / '.cm-tmp'
    if tmp.is_dir():
        with os.scandir(tmp) as it:
            entries = sorted(it, key=lambda e: e.name)
        for e in entries:
            if e.name in keep:
                continue
            rel = f'.cm-tmp/{e.name}'
            if e.is_dir(follow_symlinks=False):
                n, size, flagged = count_tree(e.path)
                flagged = flagged or e.name.endswith('.lock')
            else:
                n, size, flagged = 1, e.stat(follow_symlinks=False).st_size, e.name == 'progress.yaml'
            if flagged:
                stops.append((rel, 'forbidden-source', 'holds a *.lock folder or progress.yaml: a live run'))
                continue
            rows.append(('cm-tmp', rel, n, size))
    for name, cat in (('docs/test-evidence', 'test-evidence'), ('docs/archives', 'archives')):
        if stat_only and name in stat_only:
            rows.append((cat, name, stat_only[name]['files'], stat_only[name]['bytes']))
    return rows, stops


def find_stops(plan):
    """adds 'two-sources' (two sources to one target, compared casefolded), 'target-exists' (the target already exists on disk,
    compared casefolded) and 'archive-twin' (0 or more than 1 archive_twin() match for a sidecar, added by map_file) to plan.stops"""
    by_target = {}
    for old, new, *_ in plan.rows:
        by_target.setdefault(new.casefold(), []).append((old, new))
    for group in by_target.values():
        if len({o for o, _ in group}) > 1:
            for old, new in group:
                plan.stops.append((old, 'two-sources', f'target {new} is also the target (compared casefolded) of another source'))
    for old, new, *_ in plan.rows:
        if new.casefold() in plan.existing:
            plan.stops.append((old, 'target-exists', f'{new} already exists (compared casefolded)'))


def build_plan(root, profile, keep):
    """inventory -> id_set -> map_file per file -> find_stops -> (profile prune) prune_list and delete_list; reads, never writes"""
    root = Path(root)
    files, stat_only = inventory(root)
    cache = {}
    ids = id_set(root, files, cache)
    design_refs = {}
    for f in files:
        if '/tasks/' in f and f.endswith(('.yaml', '.yml')):
            owner = owner_id(f, ids)
            if owner:
                for slug in re.findall(r'design_brief_ref:\s*[\'"]?docs/design/([^/\s\'"]+)', '\n'.join(read_lines(root, f, {}))):
                    design_refs.setdefault(slug, set()).add(owner)
    ctx = {'root': root, 'files': set(files), 'cache': cache, 'weak': {}, 'design_cache': {}, 'design_refs': design_refs,
           'archive_names': sorted({f.split('/')[4] for f in files if f.startswith(ARCHIVE_ROOT + '/') and f.count('/') >= 5})}
    plan = Plan(root=str(root), ids=sorted(ids), stat_only=stat_only, existing={f.casefold() for f in files})
    for rel in files:
        size = os.lstat(root / rel).st_size
        res = map_file(rel, ids, ctx)
        if isinstance(res, dict):
            plan.stops.append((rel, res['stop'], res['detail']))
            continue
        new, action, key, strength = res
        if action == 'keep':
            plan.keep.append((rel, size))
            continue
        plan.rows.append((rel, new, action, key, strength))
        plan.sizes[rel] = size
        if rel in ctx['weak']:
            plan.weak.append((rel, *ctx['weak'][rel]))
    find_stops(plan)
    if profile == 'prune':
        prune_list(root, files, plan)
        plan.delete, stops = delete_list(root, set(keep), stat_only)
        plan.stops += stops
    plan.stops.sort()
    return plan


def write_tsv(path, columns, rows):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerow(columns)
        w.writerows(rows)


def write_outputs(plan, out, profile):
    """under out: migration-map.tsv (MAP_COLUMNS), weak.tsv, stops.tsv (header row even when empty), ids.txt (the id set of the plan, sorted, one id per
    line, newline-terminated; T3 and WS-T1..WS-T3 loop over it to record verdicts.tsv), summary.json
    {'actions': {action: {'files': n, 'bytes': b}}, 'stat_only': {...}}; with profile prune also prune-list.tsv and delete-list.tsv"""
    out = Path(out)
    write_tsv(out / 'migration-map.tsv', MAP_COLUMNS, sorted(plan.rows))
    write_tsv(out / 'weak.tsv', WEAK_COLUMNS, sorted(plan.weak))
    write_tsv(out / 'stops.tsv', STOP_COLUMNS, plan.stops)
    (out / 'ids.txt').write_text(''.join(i + '\n' for i in sorted(plan.ids)), encoding='utf-8')
    actions = {a: {'files': 0, 'bytes': 0} for a in ACTIONS}
    for old, _, action, *_ in plan.rows:
        actions[action]['files'] += 1
        actions[action]['bytes'] += plan.sizes[old]
    actions['keep'] = {'files': len(plan.keep), 'bytes': sum(b for _, b in plan.keep)}
    if profile == 'prune':
        write_tsv(out / 'prune-list.tsv', PRUNE_COLUMNS,
                  [(cat, path, 1, size, cit, backup) for path, cat, size, cit, backup in plan.prune])
        write_tsv(out / 'delete-list.tsv', DELETE_COLUMNS, sorted(plan.delete, key=lambda r: (r[0], r[1])))
        actions['prune'] = {'files': len(plan.prune), 'bytes': sum(r[2] for r in plan.prune)}
        actions['delete'] = {'files': sum(r[2] for r in plan.delete), 'bytes': sum(r[3] for r in plan.delete)}
    summary = {'actions': actions, 'stat_only': plan.stat_only, 'stops': len(plan.stops)}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def parse_args(argv):
    ap = argparse.ArgumentParser(prog='docs-migrate.py', description=__doc__.splitlines()[0])
    ap.add_argument('--workspace', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--profile', choices=PROFILES, default='move-only')
    ap.add_argument('--keep', action='append', default=[])
    ap.add_argument('--dry-run', action='store_true', help='the default and, in T1, the only mode')
    ap.add_argument('--apply', action='store_true', help='re-plan, move, verify, write docs/changes/MIGRATION-MAP.tsv')
    ap.add_argument('--verify', action='store_true', help='verify a finished move against manifest-before.tsv and migration-map.tsv in --out')
    ap.add_argument('--delete', type=Path, metavar='APPROVED.tsv', help='remove exactly the approved prune and delete lists (profile prune); refused on Windows')
    ap.add_argument('--verdicts', type=Path, help='verdicts.tsv recorded before the move: id, status, plan_dir, analysis_ref, error')
    ap.add_argument('--locate', default=None,
                    help="plan-locate command, run as CMD --workspace ROOT ID; the word skip verifies without verdicts")
    ap.add_argument('--verify-tar', type=Path, metavar='TAR', help='stream TAR (mode r|gz, nothing extracted) and prove every row of --manifest: in_tar, bytes_equal, sha256_equal into tar-verify.tsv beside the manifest')
    ap.add_argument('--manifest', type=Path, help='manifest-before.tsv (path, bytes, sha256) that --verify-tar proves')
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    root, out = args.workspace.expanduser().resolve(), args.out.expanduser().resolve()
    if under(out, root / 'docs') or under(out, root / '.cm-tmp'):
        print(f'docs-migrate: --out {out} lies under the workspace docs/ or .cm-tmp/', file=sys.stderr)
        return EXIT_REFUSED
    if sum(map(bool, (args.apply, args.verify, args.delete, args.verify_tar))) > 1:
        print('docs-migrate: --apply, --verify, --delete and --verify-tar run one at a time', file=sys.stderr)
        return EXIT_REFUSED
    if args.verify_tar:
        return cmd_verify_tar(args)
    if args.apply:
        return cmd_apply(root, out, args)
    if args.verify:
        return cmd_verify(root, out, args)
    if args.delete:
        return cmd_delete(root, out, args)
    plan = build_plan(root, args.profile, args.keep)
    out.mkdir(parents=True, exist_ok=True)
    write_outputs(plan, out, args.profile)
    return EXIT_STOPS if plan.stops else EXIT_OK


MANIFEST_COLUMNS = ('path', 'bytes', 'sha256')             # manifest-before.tsv and manifest-after.tsv in --out
VERDICT_COLUMNS = ('id', 'status', 'plan_dir', 'analysis_ref', 'error')   # status ok|error; paths relative to ROOT, analysis_ref empty when null
MAP_FILE_COLUMNS = ('old_path', 'new_path', 'action')      # ROOT/docs/changes/MIGRATION-MAP.tsv, permanent; new_path '-' = deleted
FINAL_ACTIONS = ('moved', 'merged', 'pruned-in-backup', 'deleted-not-backed-up', 'kept-by-user', 'pending-delete')
FORBIDDEN_DELETE = ('docs/requietment', 'docs/specs', 'docs/reviews/baselines')   # a --delete path under one of these is refused
ACTION_FINAL = {'move': 'moved', 'merge': 'merged', 'prune': 'pending-delete', 'delete': 'pending-delete'}


MAP_FILE = 'docs/changes/MIGRATION-MAP.tsv'
LEGACY_ROOTS = ('docs/plan', 'docs/analysis', 'docs/design', 'docs/specs/changes', 'docs/adhoc', 'docs/integration', 'docs/reviews/adhoc')


class ArchivesMember(Exception):
    """a tar member named under docs/archives/ (U9: its content is never read)"""


def inside(path, top):
    """True when path equals top or lies under it; both absolute (os.path.commonpath, never a string prefix)"""
    return os.path.commonpath([str(path), str(top)]) == str(top)


def read_tsv(path):
    with open(path, encoding='utf-8', newline='') as f:
        return [{k: v or '' for k, v in row.items() if k is not None} for row in csv.DictReader(f, delimiter='\t')]


def entry_sha256(path):
    """sha256 of a file's bytes; of its link target for a symlink (a rename keeps both)"""
    if os.path.islink(path):
        return hashlib.sha256(os.readlink(path).encode('utf-8', 'surrogateescape')).hexdigest()
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def write_map(root, rows):
    """write ROOT/docs/changes/MIGRATION-MAP.tsv (MAP_FILE_COLUMNS) from (old_path, new_path, action) rows, sorted by old_path"""
    dest = Path(root) / MAP_FILE
    dest.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(dest, MAP_FILE_COLUMNS, sorted(rows))


def remove_empty_dirs(root, tops):
    """os.rmdir every empty folder under each top, deepest first, then the top itself; a folder that holds anything stays"""
    for top in tops:
        if not os.path.isdir(Path(root) / top):
            continue
        for dp, _, _ in os.walk(Path(root) / top, topdown=False):
            try:
                os.rmdir(dp)
            except OSError:
                pass


def remove_empty_parents(root, rel):
    """os.rmdir the folders a removed path left empty, up to but never including ROOT/docs and ROOT/.cm-tmp"""
    root = Path(root)
    stop = (root / 'docs', root / '.cm-tmp', root)
    d = (root / rel).parent
    while d not in stop and inside(d, root):
        try:
            os.rmdir(d)
        except OSError:
            break
        d = d.parent


def manifest(root, dest, exclude=STAT_ONLY + NEVER_LISTED + ('docs/changes/MIGRATION-MAP.tsv',)):
    """write dest (MANIFEST_COLUMNS): path relative to ROOT, bytes, sha256 of every file under ROOT/docs except the exclude roots
    and docs/changes/MIGRATION-MAP.tsv (hashing reads content, which U9 forbids for docs/archives and docs/test-evidence and the plan
    never does for docs/requietment)"""
    root = Path(root)
    rows = {}
    for rel in sorted(inventory(root)[0]):
        if any(rel_under(rel, x) for x in exclude):
            continue
        p = root / rel
        rows[rel] = (os.lstat(p).st_size, entry_sha256(p))
    write_tsv(dest, MANIFEST_COLUMNS, [(rel, size, digest) for rel, (size, digest) in rows.items()])
    return rows


def read_verdicts(path):
    """-> {id: row} from a verdicts.tsv with header VERDICT_COLUMNS (written by the T3 loop over plan-locate)"""
    rows = read_tsv(path)
    if rows and not set(VERDICT_COLUMNS) <= set(rows[0]):
        raise ValueError(f'{path}: header must be {", ".join(VERDICT_COLUMNS)}')
    return {r['id']: r for r in rows}


def check_verdicts(path, ids):
    """-> None, or why the --verdicts file cannot be trusted; read before anything is written or moved"""
    if not Path(path).is_file():
        return 'not a file'
    try:
        rows = read_tsv(path)
        read_verdicts(path)
    except (OSError, UnicodeDecodeError, csv.Error, ValueError) as e:
        return str(e)
    if not rows:
        return f'no header or no rows, expected columns {", ".join(VERDICT_COLUMNS)}'
    seen = set()
    for r in rows:
        if r['status'] not in ('ok', 'error'):
            return f'status of {r["id"] or "(blank id)"} is {r["status"]!r}, not ok or error'
        if not r['id'] or r['id'] in seen:
            return f'id {r["id"]!r} is blank or repeated'
        seen.add(r['id'])
    missing, extra = sorted(set(ids) - seen), sorted(seen - set(ids))
    if missing or extra:
        return f'ids differ from the re-planned ids: missing {missing[0] if missing else "-"}, extra {extra[0] if extra else "-"}'
    return None


def run_locate(cmd, root, plan_id):
    """cmd None (the default): the running interpreter + plan-locate.py beside this script, no PATH lookup. Else run shlex.split(cmd) (POSIX split on POSIX hosts, native split on Windows; a leading ~ expanded) + ['--workspace', ROOT, ID]; -> a VERDICT_COLUMNS row: exit 0 -> status ok with the
    JSON plan_dir and analysis_ref (null -> empty) minus the ROOT prefix; exit 1 -> status error with stderr after 'plan-locate: '
    minus the ROOT prefix"""
    root = Path(root)
    if cmd is None:
        toks = [sys.executable, str(Path(__file__).resolve().with_name('plan-locate.py'))]
    else:
        toks = shlex.split(cmd, posix=os.name != 'nt')
        if os.name == 'nt':
            toks = [t[1:-1] if len(t) >= 2 and t[0] == t[-1] and t[0] in '"\'' else t for t in toks]
    argv = [os.path.expanduser(a) for a in toks] + ['--workspace', str(root), plan_id]
    p = subprocess.run(argv, capture_output=True, text=True)
    strip = lambda s: s.replace(str(root) + os.sep, '').replace(str(root) + '/', '').replace(os.sep, '/')
    if p.returncode == 0:
        j = json.loads(p.stdout)
        return {'id': plan_id, 'status': 'ok', 'plan_dir': strip(j.get('plan_dir') or ''),
                'analysis_ref': strip(j.get('analysis_ref') or ''), 'error': ''}
    return {'id': plan_id, 'status': 'error', 'plan_dir': '', 'analysis_ref': '',
            'error': strip(p.stderr.strip().split('plan-locate: ', 1)[-1])}


def verdict_matches(old, new, to_new):
    """True when the post-move row new equals the pre-move row old mapped through to_new (old relative path -> new relative path or
    None): same status; ok rows: new plan_dir == the folder of to_new(old plan_dir + '/plan.yaml') and new analysis_ref ==
    to_new(old analysis_ref); error rows: the same text once the bracketed path list is removed (the paths necessarily change)"""
    if old['status'] != new['status']:
        return False
    if old['status'] == 'error':
        bare = lambda text: re.sub(r'\[.*\]', '[]', text)   # the bracketed path list changes with the move; the rest must not
        return bare(old['error']) == bare(new['error'])
    moved = to_new(old['plan_dir'] + '/plan.yaml')
    if moved is None or new['plan_dir'] != os.path.dirname(moved):
        return False
    return new['analysis_ref'] == ((to_new(old['analysis_ref']) or '') if old['analysis_ref'] else '')


def verify_moves(root, out, args):
    """-> list of problem strings (empty = pass): for each row of out/migration-map.tsv with action move or merge, the file at new has
    the sha256 recorded for old in out/manifest-before.tsv ('sha256 differs: <new path>'); file counts equal; exactly one plan.yaml per
    id that had one ('plan.yaml count changed: <id>'); unless args.locate is the word skip, for every id of args.verdicts the verdict
    of run_locate after the move satisfies verdict_matches ('verdict differs: <id>')"""
    root, out = Path(root), Path(out)
    before = {r['path']: r for r in read_tsv(out / 'manifest-before.tsv')}
    moves = {r['old']: r['new'] for r in read_tsv(out / 'migration-map.tsv') if r['action'] in ('move', 'merge')}
    problems = []
    for old, new in sorted(moves.items()):
        if not os.path.lexists(root / new):
            problems.append(f'missing after the move: {new}')
        elif old not in before:
            problems.append(f'not in manifest-before.tsv: {old}')
        elif entry_sha256(root / new) != before[old]['sha256']:
            problems.append(f'sha256 differs: {new}')
    now = [f for f in inventory(root)[0] if f != MAP_FILE]
    if len(now) != len(before):
        problems.append(f'file count differs: {len(before)} before, {len(now)} after')
    ids_file = out / 'ids.txt'
    for plan_id in ids_file.read_text(encoding='utf-8').split() if ids_file.is_file() else []:
        pat = re.compile(r'(?:^|/)(?:\d{4}-\d{2}-\d{2}-)?' + re.escape(plan_id) + r'/plan\.yaml$')
        if sum(1 for f in before if pat.search(f)) != sum(1 for f in now if pat.search(f)):
            problems.append(f'plan.yaml count changed: {plan_id}')
    if args.locate != 'skip':
        if not args.verdicts:
            problems.append('--verdicts is required unless --locate skip')
        else:
            to_new = lambda p: moves.get(p, p) if p else None
            for plan_id, old in sorted(read_verdicts(args.verdicts).items()):
                if not verdict_matches(old, run_locate(args.locate, root, plan_id), to_new):
                    problems.append(f'verdict differs: {plan_id}')
    return problems


def preflight_verdicts(root, plan, out, args):
    """-> list of problem strings (empty = pass). Builds out/.preflight-shadow/docs with the layout the move would produce (every file
    of inventory(root) at its mapped path, created empty; a basename plan.yaml copied; a symlink recreated), runs the real args.locate
    on it for every id of args.verdicts and compares with verdict_matches, so a verdict that would change is found before any rename.
    The shadow is removed in a finally"""
    root, out = Path(root), Path(out)
    shadow = out / '.preflight-shadow'
    moves = {old: new for old, new, action, *_ in plan.rows if action in ('move', 'merge')}
    to_new = lambda p: moves.get(p, p) if p else None
    problems = []
    try:
        for rel in inventory(root)[0]:
            src, dst = root / rel, shadow / moves.get(rel, rel)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_symlink():
                os.symlink(os.readlink(src), dst)
            elif src.name == 'plan.yaml':
                shutil.copyfile(src, dst)
            else:
                dst.touch()
        for plan_id, old in sorted(read_verdicts(args.verdicts).items()):
            new = run_locate(args.locate, shadow, plan_id)
            if not verdict_matches(old, new, to_new):
                show = lambda r: f'{r["status"]}/{r["analysis_ref"] or r["error"] or r["plan_dir"]}'
                problems.append(f'preflight: verdict differs: {plan_id} (now {show(old)}, after the move {show(new)})')
    finally:
        shutil.rmtree(shadow, ignore_errors=True)
    return problems


def write_migration_map(root, plan, out):
    """write ROOT/docs/changes/MIGRATION-MAP.tsv (MAP_FILE_COLUMNS): one row per moved or merged file with ACTION_FINAL, one row per
    prune file (new = its post-move path, action pending-delete), one folder line each for docs/test-evidence/ and docs/archives/
    (new '-', pending-delete, no file names); keep rows are not written"""
    prune = {path for path, *_ in plan.prune}
    rows = {}
    for old, new, action, *_ in plan.rows:
        rows[old] = (new, 'pending-delete' if old in prune else ACTION_FINAL[action])
    for path in prune:
        rows.setdefault(path, (path, 'pending-delete'))   # a prune file that is not moved stays at its path
    for cat, path, *_ in plan.delete:
        if cat in ('test-evidence', 'archives'):
            rows[path + '/'] = ('-', 'pending-delete')
    write_map(root, [(old, new, action) for old, (new, action) in rows.items()])


def cmd_apply(root, out, args):
    """re-plan (build_plan), call write_outputs so out/ids.txt and out/migration-map.tsv describe the tree about to move, and exit 1 on any stop; if nothing remains to move exit 0 touching nothing (manifest-before.tsv and the
    map stay). Otherwise write out/manifest-before.tsv, os.rename each move or merge row (parent folders created, nothing deleted),
    run verify_moves and exit 1 naming the first problem (the map is then NOT written and no legacy root is removed), else
    write_migration_map and os.rmdir the emptied legacy roots (docs/plan, docs/analysis, docs/design, docs/specs/changes,
    docs/adhoc, docs/integration, docs/reviews/adhoc, deepest first, only when empty); refuse (exit 2, nothing written or moved) when --verdicts is missing,
    unreadable, lacks the header, has a status other than ok|error, a blank or repeated id, or an id set other than the re-planned ids.
    Before write_outputs and the first rename (unless --locate skip) preflight_verdicts runs the real --locate on a shadow tree of the
    post-move layout; a verdict that would differ exits 2 'nothing moved', so out/ gets no list and no manifest"""
    if args.locate != 'skip' and not args.verdicts:
        print('docs-migrate: --apply needs --verdicts FILE, or --locate skip', file=sys.stderr)
        return EXIT_REFUSED
    plan = build_plan(root, args.profile, args.keep)
    out.mkdir(parents=True, exist_ok=True)
    if plan.stops:
        write_outputs(plan, out, args.profile)
        for path, stop, detail in plan.stops:
            print(f'docs-migrate: stop {stop}: {path} {detail}', file=sys.stderr)
        return EXIT_STOPS
    if not plan.rows:
        return EXIT_OK
    if args.locate != 'skip':
        why = check_verdicts(args.verdicts, plan.ids)
        if why:
            print(f'docs-migrate: --verdicts {args.verdicts}: {why}; nothing moved', file=sys.stderr)
            return EXIT_REFUSED
        problems = preflight_verdicts(root, plan, out, args)
        if problems:
            for problem in problems:
                print(f'docs-migrate: {problem}', file=sys.stderr)
            print('docs-migrate: nothing moved', file=sys.stderr)
            return EXIT_REFUSED
    write_outputs(plan, out, args.profile)
    manifest(root, out / 'manifest-before.tsv')
    for old, new, *_ in sorted(plan.rows):
        if os.path.lexists(root / new):
            print(f'docs-migrate: {new} exists; stopped before moving {old}', file=sys.stderr)
            return EXIT_STOPS
        (root / new).parent.mkdir(parents=True, exist_ok=True)
        os.rename(root / old, root / new)
    problems = verify_moves(root, out, args)
    for problem in problems:
        print(f'docs-migrate: {problem}', file=sys.stderr)
    if problems:
        return EXIT_STOPS
    write_migration_map(root, plan, out)
    remove_empty_dirs(root, LEGACY_ROOTS)
    return EXIT_OK


def cmd_verify(root, out, args):
    """verify_moves alone against out/manifest-before.tsv and out/migration-map.tsv: print each problem to stderr, exit 1 when any"""
    for name in ('manifest-before.tsv', 'migration-map.tsv'):
        if not (out / name).is_file():
            print(f'docs-migrate: {out / name} is missing: --verify needs the --out folder of the --apply run', file=sys.stderr)
            return EXIT_REFUSED
    problems = verify_moves(root, out, args)
    for problem in problems:
        print(f'docs-migrate: {problem}', file=sys.stderr)
    return EXIT_STOPS if problems else EXIT_OK


def refusal(root, approved, live, keep):
    """-> a message or None. Refuse (exit 1, before anything is removed) when the approved list is empty; or an approved row is absent from the live
    prune and delete lists recomputed by build_plan on the current tree, or its category, files or bytes differ from its live row (prune rows and
    delete rows alike; the message names the path); or a path lies outside ROOT/docs and ROOT/.cm-tmp, under FORBIDDEN_DELETE, or under a
    --keep entry (os.path.commonpath on resolved paths, never a string prefix). Approved rows that are a subset of the live rows pass: the user
    may drop rows at the approval and a dropped row stays on disk"""
    if not approved:
        return 'the approved list is empty'
    root = Path(root).resolve()
    allowed = [root / 'docs', root / '.cm-tmp']
    protected = [(f'protected {f}/', root / f) for f in FORBIDDEN_DELETE] + [(f'kept entry {k}', root / '.cm-tmp' / k) for k in keep]
    live_by_path = {r['path']: r for r in live}
    seen = set()
    for r in approved:
        path = r['path']
        if path in seen:
            return f'{path}: listed twice'
        seen.add(path)
        p = (root / path).resolve()
        if not any(p != a and inside(p, a) for a in allowed):
            return f'{path}: outside docs/ and .cm-tmp/'
        if str(p) != str(root / path):
            return f'{path}: not a plain path (a symlink or ..)'
        for why, f in protected:
            if inside(p, f.resolve()) or inside(f.resolve(), p):
                return f'{path}: lies in or over {why}'
        row = live_by_path.get(path)
        if row is None:
            return f'{path}: not a row of the live prune and delete lists'
        got, want = [r['category'], str(r['files']).strip(), str(r['bytes']).strip()], [row['category'], row['files'], row['bytes']]
        if got != want:
            return f'{path}: category, files, bytes {got} differ from the live row {want}'
    return None


def open_files(path):
    """-> lines of `lsof +D <path>` (stdout), empty when nothing is open; run once per approved path before any removal, any line stops"""
    p = str(path)
    argv = ['lsof', '+D', p] if os.path.isdir(p) and not os.path.islink(p) else ['lsof', p]
    r = subprocess.run(argv, capture_output=True, text=True)
    if r.stdout.strip():
        return r.stdout.strip().splitlines()
    if r.returncode not in (0, 1):
        raise RuntimeError(f'lsof exited {r.returncode}: {r.stderr.strip()}')   # no verdict on open files: stop
    return []


def cmd_delete(root, out, args):
    """profile prune only. Read APPROVED.tsv (header category, path, files, bytes; extra columns ignored), refusal(), open_files() per
    path (any open file -> exit 1 before any removal), then ONE shutil.rmtree or os.remove per exact approved path, never a glob;
    update each pending-delete row of the map under an approved path to pruned-in-backup (new is a path) or deleted-not-backed-up (new '-'),
    and each pending-delete row under a live row the approved list left out to kept-by-user (the path stays on disk); write
    out/manifest-after.tsv and compare it with manifest-before.tsv minus the approved pruned paths (exit 1 on a difference); os.rmdir emptied
    roots, ROOT/.cm-tmp only when empty. Windows (os.name == 'nt'): refused first, exit 1, nothing read or removed"""
    if os.name == 'nt':
        print('docs-migrate: lsof-based open-file check unavailable on Windows; nothing was removed', file=sys.stderr)
        return EXIT_STOPS
    if args.profile != 'prune':
        print('docs-migrate: --delete runs with --profile prune only', file=sys.stderr)
        return EXIT_REFUSED
    map_path = root / MAP_FILE
    for need in (args.delete, map_path, out / 'manifest-before.tsv'):
        if not need.is_file():
            print(f'docs-migrate: {need} is missing; nothing was removed', file=sys.stderr)
            return EXIT_STOPS
    approved = read_tsv(args.delete)
    if approved and not set(DELETE_COLUMNS) <= set(approved[0]):
        print(f'docs-migrate: {args.delete} must have the header {", ".join(DELETE_COLUMNS)}; nothing was removed', file=sys.stderr)
        return EXIT_STOPS
    plan = build_plan(root, 'prune', args.keep)
    live = [{'category': cat, 'path': path, 'files': '1', 'bytes': str(size)} for path, cat, size, *_ in plan.prune]
    live += [{'category': cat, 'path': path, 'files': str(n), 'bytes': str(size)} for cat, path, n, size in plan.delete]
    problem = refusal(root, approved, live, args.keep)
    if problem:
        print(f'docs-migrate: refused, nothing was removed: {problem}', file=sys.stderr)
        return EXIT_STOPS
    for r in approved:
        if not os.path.lexists(root / r['path']):
            continue
        try:
            held = open_files(root / r['path'])
        except (OSError, RuntimeError) as e:
            print(f'docs-migrate: lsof could not be run on {r["path"]}: {e}; nothing was removed', file=sys.stderr)
            return EXIT_STOPS
        if held:
            print(f'docs-migrate: open file under {r["path"]}; nothing was removed:\n' + '\n'.join(held), file=sys.stderr)
            return EXIT_STOPS
    removed = []
    for r in approved:   # one exact path at a time, never a glob
        p = root / r['path']
        try:
            if os.path.lexists(p):
                if os.path.isdir(p) and not os.path.islink(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
        except OSError as e:
            print(f'docs-migrate: removing {r["path"]} failed: {e}; the map was not updated', file=sys.stderr)
            return EXIT_STOPS
        removed.append(r['path'])
    approved_paths, live_paths = {r['path'] for r in approved}, {r['path'] for r in live}
    rows = [dict(r) for r in read_tsv(map_path)]
    have = {r['old_path'] for r in rows}
    for r in live:
        if r['path'] in ('docs/test-evidence', 'docs/archives') and r['path'] + '/' not in have:
            rows.append({'old_path': r['path'] + '/', 'new_path': '-', 'action': 'pending-delete'})
    pending = []
    for r in rows:
        if r['action'] != 'pending-delete':
            continue
        folder = r['new_path'] == '-'
        path = r['old_path'].rstrip('/') if folder else r['new_path']
        if path in approved_paths:
            r['action'] = 'deleted-not-backed-up' if folder else 'pruned-in-backup'
        elif path in live_paths:
            r['action'] = 'kept-by-user'
        else:
            pending.append(path)
    write_map(root, [(r['old_path'], r['new_path'], r['action']) for r in rows])
    code = EXIT_OK
    for path in pending:
        print(f'docs-migrate: map row still pending-delete, not a live row: {path}', file=sys.stderr)
        code = EXIT_STOPS
    pruned = {r['path'] for r in approved if r['category'] in PRUNE_CATEGORIES}
    moved = {r['old_path']: r['new_path'] for r in rows if r['new_path'] != '-'}
    expect = {}
    for old, r in ((r['path'], (r['bytes'], r['sha256'])) for r in read_tsv(out / 'manifest-before.tsv')):
        if moved.get(old, old) not in pruned:
            expect[moved.get(old, old)] = r
    after = {path: (str(size), digest) for path, (size, digest) in manifest(root, out / 'manifest-after.tsv').items()}
    for path in sorted(p for p in set(expect) | set(after) if expect.get(p) != after.get(p)):
        print(f'docs-migrate: manifest-after differs from manifest-before minus the pruned paths: {path}', file=sys.stderr)
        code = EXIT_STOPS
    for path in removed:
        remove_empty_parents(root, path)
    tmp = root / '.cm-tmp'
    if tmp.is_dir() and not any(tmp.iterdir()):
        os.rmdir(tmp)
    remove_empty_dirs(root, LEGACY_ROOTS)
    return code


def cmd_verify_tar(args):
    """--verify-tar TAR --manifest MANIFEST (AC-7, DC-50): refuse (EXIT_REFUSED) without --manifest; otherwise verify_tar(TAR, MANIFEST) ->
    (rows, failed), write tar-verify.tsv (TAR_VERIFY_COLUMNS) beside MANIFEST, print each failing path to stderr, return EXIT_STOPS when
    failed else EXIT_OK; a member under docs/archives/ prints its name and returns EXIT_STOPS before tar-verify.tsv is written"""
    if not args.manifest:
        print('docs-migrate: --verify-tar needs --manifest', file=sys.stderr)
        return EXIT_REFUSED
    try:
        rows, failed = verify_tar(args.verify_tar, args.manifest)
    except ArchivesMember as e:
        print(f'docs-migrate: tar member under docs/archives/: {e.args[0]}', file=sys.stderr)
        return EXIT_STOPS
    write_tsv(args.manifest.parent / 'tar-verify.tsv', TAR_VERIFY_COLUMNS, rows)
    for path in failed:
        print(f'docs-migrate: tar does not hold {path} byte-exact', file=sys.stderr)
    return EXIT_STOPS if failed else EXIT_OK


TAR_VERIFY_COLUMNS = ('path', 'in_tar', 'bytes_equal', 'sha256_equal')   # yes|no per column; one row per manifest row


def verify_tar(tar_path, manifest_path):
    """open tar_path with tarfile mode 'r|gz' (a forward stream, nothing extracted to disk) and read the manifest (MANIFEST_COLUMNS); for
    every regular member whose name is a manifest path, hash it in chunks and compare the byte count and sha256; a member whose name starts
    with docs/archives/ raises ArchivesMember(name) before its content is read (U9). -> (rows of TAR_VERIFY_COLUMNS in manifest order,
    failed: the paths with any 'no')"""
    manifest_rows = read_tsv(manifest_path)
    wanted = {r['path']: r for r in manifest_rows}
    found = {}
    with tarfile.open(tar_path, 'r|gz') as tf:
        for member in tf:
            name = member.name[2:] if member.name.startswith('./') else member.name
            if name == 'docs/archives' or name.startswith('docs/archives/'):
                raise ArchivesMember(name)
            if not member.isreg() or name not in wanted:
                continue
            h, n = hashlib.sha256(), 0
            f = tf.extractfile(member)
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
                n += len(chunk)
            found[name] = (n, h.hexdigest())
    rows, failed = [], []
    for r in manifest_rows:
        hit = found.get(r['path'])
        yn = lambda ok: 'yes' if ok else 'no'
        row = (r['path'], yn(hit), yn(hit and str(hit[0]) == r['bytes']), yn(hit and hit[1] == r['sha256']))
        rows.append(row)
        if 'no' in row[1:]:
            failed.append(r['path'])
    return rows, failed


if __name__ == '__main__':
    sys.exit(main())
