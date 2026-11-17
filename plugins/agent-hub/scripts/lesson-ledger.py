#!/usr/bin/env python3
"""lesson-ledger.py: the lesson ledger CLI behind `agent-hub lesson`.

usage: lesson-ledger.py sight --project P --type T --subject S --ref R --date D [--scope X] [--reader Y]
       lesson-ledger.py show [--project P] [--subject S]
       lesson-ledger.py promote --project P --type T --subject S
       lesson-ledger.py decline --project P --type T --subject S [--date D]
       lesson-ledger.py seed --json FILE

The ledger is config_dir()/memory/global/lessons.yaml (CLAUDE_CONFIG_DIR wins): a mapping with one key, lessons, holding the
list of entries ({lessons: []} when created empty). An entry is keyed by (project, type, subject). FILE of seed is the same
shape as JSON, {"lessons": [entry, ...]}.
An entry may carry declined (an ISO date string): `decline` sets it, a sighting that counts a new ref removes it.
Every command prints JSON on stdout. Exit 0, or 2 on bad input or a ledger that does not parse (that file is never overwritten).
"""
import argparse
import contextlib
import datetime
import fcntl
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python3 -I leaves the script folder off sys.path
import _paths

if _paths.lib_path().is_dir():
    sys.path.insert(0, str(_paths.lib_path()))
import yaml

KEY = ('project', 'type', 'subject')


class LedgerError(Exception):
    """the ledger cannot be used: it does not parse, or a command names no entry"""


def ledger_path():
    return _paths.config_dir() / 'memory' / 'global' / 'lessons.yaml'


@contextlib.contextmanager
def locked(path):
    """hold an exclusive lock on the sidecar <ledger>.lock for the whole read-modify-write"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path) + '.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def load(path):
    """-> the list of entries; a missing file is []; a file whose top level is not a mapping with a lessons list raises LedgerError"""
    if not path.is_file():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding='utf-8'))
    except (yaml.YAMLError, UnicodeDecodeError) as e:
        raise LedgerError(f'{path}: does not parse: {e}')
    if not isinstance(data, dict) or not isinstance(data.get('lessons'), list):
        raise LedgerError(f'{path}: want a mapping with a lessons list')
    return data['lessons']


def save(path, entries):
    """write a temp file in the same folder (mode 0600), then os.replace it over the ledger"""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix='.lessons-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            yaml.safe_dump({'lessons': entries}, f, sort_keys=False, allow_unicode=True)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def find(entries, key):
    return next((e for e in entries if tuple(e.get(k) for k in KEY) == key), None)


def sight(entries, a):
    key = (a.project, a.type, a.subject)
    e = find(entries, key)
    if e is None:
        entries.append({'project': a.project, 'type': a.type, 'subject': a.subject, 'scope': a.scope, 'reader': a.reader,
                        'count': 1, 'seen': [{'date': a.date, 'ref': a.ref}], 'stage': 'candidate', 'memory_id': None,
                        'created': a.date, 'updated': a.date})
        return {'count': 1, 'stage': 'candidate', 'new': True, 'counted': True}, True
    if any(s.get('ref') == a.ref for s in e['seen']):
        return {'count': e['count'], 'stage': e['stage'], 'new': False, 'counted': False}, False
    e['seen'].append({'date': a.date, 'ref': a.ref})
    e['count'] += 1
    e['updated'] = a.date
    e.pop('declined', None)      # a new sighting reopens the question the user said No to
    return {'count': e['count'], 'stage': e['stage'], 'new': False, 'counted': True}, True


def promote(entries, a):
    e = find(entries, (a.project, a.type, a.subject))
    if e is None:
        raise LedgerError(f'no entry for {a.project}/{a.type}/{a.subject}')
    e['stage'] = 'promoted'
    e['updated'] = datetime.date.today().isoformat()
    return {'count': e['count'], 'stage': 'promoted'}, True


def decline(entries, a):
    e = find(entries, (a.project, a.type, a.subject))
    if e is None or e.get('stage') == 'promoted':
        raise LedgerError(f'no candidate entry for {a.project}/{a.type}/{a.subject}')
    day = a.date or datetime.date.today().isoformat()
    if e.get('declined') == day:
        return {'declined': day, 'changed': False}, False
    e['declined'] = day
    return {'declined': day, 'changed': True}, True


def check_seed_entry(g, where):
    """the seed shape contract: seen items are {ref: non-empty str, date: str|null}, count an int >= 0, stage candidate|promoted"""
    if not isinstance(g, dict) or not all(isinstance(g.get(k), str) and g.get(k) for k in KEY):
        raise LedgerError(f'{where}: an entry lacks project, type or subject')
    name = '/'.join(g[k] for k in KEY)
    seen = g.get('seen', [])
    if not isinstance(seen, list):
        raise LedgerError(f'{where}: entry {name}: seen must be a list')
    for i, s in enumerate(seen):
        if not (isinstance(s, dict) and isinstance(s.get('ref'), str) and s['ref'] and (s.get('date') is None or isinstance(s['date'], str))):
            raise LedgerError(f'{where}: entry {name}: seen item {i} must be a mapping with ref (non-empty string) and date (string or null), got {s!r}')
    c = g.get('count', 0)
    if isinstance(c, bool) or not isinstance(c, int) or c < 0:
        raise LedgerError(f'{where}: entry {name}: count must be an int >= 0, got {c!r}')
    if g.get('stage', 'candidate') not in ('candidate', 'promoted'):
        raise LedgerError(f'{where}: entry {name}: stage must be candidate or promoted, got {g["stage"]!r}')


def seed(entries, a):
    try:
        with open(a.json, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise LedgerError(f'{a.json}: {e}')
    given = data.get('lessons') if isinstance(data, dict) else None
    if not isinstance(given, list):
        raise LedgerError(f'{a.json}: want a mapping with a lessons list')
    for g in given:      # every entry is checked before the first one is applied, so a bad seed writes nothing
        check_seed_entry(g, a.json)
    today = datetime.date.today().isoformat()
    keys = set()
    for g in given:
        key = tuple(g[k] for k in KEY)
        keys.add(key)
        e = find(entries, key)
        if e is None:
            e = {'project': g['project'], 'type': g['type'], 'subject': g['subject'], 'scope': g.get('scope'),
                 'reader': g.get('reader'), 'count': 0, 'seen': [], 'stage': 'candidate',
                 'memory_id': g.get('memory_id'), 'created': g.get('created', today), 'updated': today}
            entries.append(e)
        have = {s.get('ref') for s in e['seen']}
        for s in g.get('seen', []):
            if s['ref'] not in have:
                e['seen'].append(s)
                have.add(s['ref'])
        e['count'] = max(g.get('count', 0), e['count'], len(e['seen']))
        if g.get('stage') == 'promoted':
            e['stage'] = 'promoted'
        e['updated'] = today
    return {'seeded': len(given), 'merged': len(keys), 'entries': len(entries)}, True


def show(entries, a):
    return [e for e in entries if (not a.project or e.get('project') == a.project) and (not a.subject or e.get('subject') == a.subject)], False


def build_parser():
    ap = argparse.ArgumentParser(prog='agent-hub lesson')
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('sight')
    for n in ('project', 'type', 'subject', 'ref', 'date'):
        s.add_argument('--' + n, required=True)
    s.add_argument('--scope')
    s.add_argument('--reader')
    s.set_defaults(fn=sight)
    p = sub.add_parser('show')
    p.add_argument('--project')
    p.add_argument('--subject')
    p.set_defaults(fn=show)
    r = sub.add_parser('promote')
    for n in KEY:
        r.add_argument('--' + n, required=True)
    r.set_defaults(fn=promote)
    c = sub.add_parser('decline')
    for n in KEY:
        c.add_argument('--' + n, required=True)
    c.add_argument('--date')
    c.set_defaults(fn=decline)
    d = sub.add_parser('seed')
    d.add_argument('--json', required=True)
    d.set_defaults(fn=seed)
    return ap


def main(argv):
    a = build_parser().parse_args(argv)
    path = ledger_path()
    try:
        with locked(path):
            entries = load(path)
            out, changed = a.fn(entries, a)
            if changed:
                save(path, entries)
    except (LedgerError, OSError, ValueError, KeyError) as e:
        print(f'lesson-ledger: {e}', file=sys.stderr)
        return 2
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
