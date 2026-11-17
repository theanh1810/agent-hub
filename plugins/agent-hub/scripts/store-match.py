#!/usr/bin/env python3
"""agent-hub store: match, list, verify over store/catalog.yaml. Read only: no network, no write.

  store-match.py match  [--repo DIR] [--files PATH...] [--role ROLE] [--catalog FILE]
  store-match.py list   [--catalog FILE]
  store-match.py verify [--catalog FILE]

`match` prints `id · path · read when` per `ready` row whose signal matches. A signal is
{files[], deps[], task}: files and deps are each any-of, and when both are given both must hold.
A file entry may be a glob (`vite.config.*`), a directory (`wp-content/`) or `head:<text>`, which looks for
the text in the first 30 lines of a root `*.php` or `style.css`. Deps come from package.json and composer.json.
A row with no files and no deps (a thinking text) never matches a repo."""
import argparse
import fnmatch
import hashlib
import json
import sys
from pathlib import Path

import yaml

STORE = Path(__file__).resolve().parents[1] / 'store'
SEP = ' · '
HEAD_LINES = 30
MANIFESTS = ('package.json', 'composer.json')
DEP_KEYS = ('dependencies', 'devDependencies', 'peerDependencies', 'require', 'require-dev')


def load_catalog(path):
    data = yaml.safe_load(Path(path).read_text(encoding='utf-8')) or []
    return data['entries'] if isinstance(data, dict) else data


def read_deps(root):
    deps = set()
    for name in MANIFESTS:
        p = root / name
        if not p.is_file():
            continue
        try:
            doc = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if not isinstance(doc, dict):
            continue
        for key in DEP_KEYS:
            if isinstance(doc.get(key), dict):
                deps.update(doc[key])
    return deps


def head_text(root):
    out = []
    for p in sorted(list(root.glob('*.php')) + [root / 'style.css']):
        if p.is_file():
            with p.open(encoding='utf-8', errors='replace') as f:
                out.extend(line for _, line in zip(range(HEAD_LINES), f))
    return ''.join(out)


def file_hit(root, pattern, head):
    if pattern.startswith('head:'):
        return pattern[5:] in head
    if pattern.endswith('/'):
        return (root / pattern[:-1]).is_dir()
    return any(fnmatch.fnmatch(p.name, pattern) for p in root.iterdir())


def root_matches(signal, root):
    files, deps = signal.get('files') or [], signal.get('deps') or []
    if not files and not deps or not root.is_dir():
        return False
    head = head_text(root) if any(f.startswith('head:') for f in files) else ''
    have = read_deps(root) if deps else set()
    return (not files or any(file_hit(root, f, head) for f in files)) and (not deps or any(d in have for d in deps))


def package_root(repo, rel):
    p = (repo / rel).resolve()
    p = p if p.is_dir() else p.parent
    while p != repo and repo in p.parents:
        if any((p / m).is_file() for m in MANIFESTS):
            return p
        p = p.parent
    return repo


def match(entries, repo, files=(), role=None):
    repo = Path(repo).resolve()
    roots = [repo] + [package_root(repo, f) for f in files]
    roots = list(dict.fromkeys(roots))
    lines = []
    for e in entries:
        if e.get('status') != 'ready' or (role and role not in (e.get('roles') or [])):
            continue
        if any(root_matches(e.get('signal') or {}, r) for r in roots):
            main = ((e.get('files') or [{}])[0]).get('path', 'text.md')
            lines.append(SEP.join((e['id'], f"store/{e['id']}/{main}", (e.get('signal') or {}).get('task', ''))))
    return lines


def verify(entries, store):
    bad = []
    for e in entries:
        for f in e.get('files') or []:
            p = Path(store) / e['id'] / f['path']
            if not p.is_file():
                bad.append(f"{e['id']}: missing {f['path']}")
            elif hashlib.sha256(p.read_bytes()).hexdigest() != f.get('sha256'):
                bad.append(f"{e['id']}: sha256 differs for {f['path']}")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(prog='agent-hub store')
    ap.add_argument('cmd', choices=('match', 'list', 'verify'))
    ap.add_argument('--catalog', default=str(STORE / 'catalog.yaml'))
    ap.add_argument('--repo', default='.')
    ap.add_argument('--files', nargs='*', default=[])
    ap.add_argument('--role')
    a = ap.parse_args(argv)
    entries = load_catalog(a.catalog)
    if a.cmd == 'match':
        if not Path(a.repo).is_dir():
            print(f'store match: {a.repo} is not a directory', file=sys.stderr)
            return 2
        for line in match(entries, a.repo, a.files, a.role):
            print(line)
    elif a.cmd == 'list':
        for e in entries:
            print(SEP.join((e['id'], e.get('status', ''), e.get('unblock') or e.get('reason') or '')))
    else:
        bad = verify(entries, Path(a.catalog).parent)
        for b in bad:
            print(b)
        return 1 if bad else 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
