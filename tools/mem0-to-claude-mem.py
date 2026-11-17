#!/usr/bin/env python3
"""mem0-to-claude-mem.py: turn a mem0 export into claude-mem save payloads and ledger seeds, then post them.

usage: mem0-to-claude-mem.py plan --export EXPORT.json --out DIR
       mem0-to-claude-mem.py post --payloads DIR/payloads.jsonl --done DIR/done.log --evidence EVIDENCE.yaml

plan  reads the export (a JSON array of {id, memory, metadata, ...}), creates DIR if missing and writes
      DIR/payloads.jsonl (one save payload per line, export order) and DIR/lesson-seeds.json ({"lessons": [...]}, the
      shape `agent-hub lesson seed --json` reads, one entry per unique (project, type, subject)). Prints
      {"payloads": N, "seeds": unique keys, "seed_inputs": recurring_pitfall records, "unparsed_seen": [mem0_id], "out": DIR}.
post  sends every payload whose mem0_id is not a line of the done log to the claude-mem worker save endpoint named by
      the evidence file (worker.base_url, worker.save_endpoint {method, path, body_fields}), appends the mem0_id after
      each 2xx, and prints {"posted": N, "skipped": M}. Never deletes anything.
Exit 0 done; 1 the worker answered non-2xx or was unreachable (response on stderr, the done log keeps what landed);
2 bad input (an export that is not a JSON array writes nothing); 3 the evidence records no worker save endpoint
(feed the JSONL through the claude-mem save tool instead; done.log is the resume point for that path too).
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'plugins', 'agent-hub', 'lib'))   # vendored PyYAML; python3 -I leaves the script folder off sys.path
import yaml


def err(msg):
    print(f'mem0-to-claude-mem: {msg}', file=sys.stderr)


def project_of(md):
    """a fleet lesson, a global scope or no project is project 'global'; any other project keeps its name"""
    p = md.get('project')
    if not p or p == 'fleet' or md.get('scope') == 'global':
        return 'global'
    return p


STAGE = {'candidate': 'candidate', 'pattern': 'promoted', 'awaiting_approval': 'candidate'}   # format.md:59 to the ledger; closeout.md:119-127


def parse_seen(raw):
    """-> (seen [{date, ref}], clean): mapping items kept; flat strings 'date.X' then 'ref.Y' split at the first '.' only"""
    seen, clean, pending = [], isinstance(raw, (list, type(None))), None
    for it in (raw if isinstance(raw, list) else []):
        if isinstance(it, dict):
            if isinstance(it.get('ref'), str) and it['ref'] and (it.get('date') is None or isinstance(it['date'], str)):
                seen.append({'date': it.get('date'), 'ref': it['ref']})
            else:
                clean = False
            continue
        kind, _, val = it.partition('.') if isinstance(it, str) else ('', '', '')
        if kind == 'date' and val:
            clean = clean and pending is None       # a date with no ref after it is a pair without a ref
            pending = val
        elif kind == 'ref' and val:
            seen.append({'date': pending, 'ref': val})
            pending = None
        else:
            clean = False
    return seen, clean and pending is None


def parse_count(raw):
    """-> (count, clean): an int is kept, a digit string becomes an int, absent counts 2 (dedup.md rule 4); anything else counts 2 and is unclean"""
    if raw is None:
        return 2, True
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
        return raw, True
    if isinstance(raw, str) and raw.isdigit():
        return int(raw), True
    return 2, False


def map_memory(m):
    """-> (payload, seed or None, clean) for one export entry; the text is carried verbatim"""
    md = dict(m.get('metadata') or {})
    text = m['memory']
    title = md.get('subject') or text[:60]
    project = project_of(md)
    payload = {'project': project, 'title': title, 'text': text, 'metadata': dict(md, mem0_id=m['id'])}
    seed, clean = None, True
    if md.get('type') == 'recurring_pitfall':
        seen, c1 = parse_seen(md.get('seen'))
        count, c2 = parse_count(md.get('count'))
        clean = c1 and c2
        seed = {'project': project, 'type': 'recurring_pitfall', 'subject': md.get('subject') or title,
                'count': count, 'seen': seen, 'stage': STAGE.get(md.get('stage'), 'candidate'),
                'scope': md.get('scope'), 'reader': md.get('reader')}
    return payload, seed, clean


def merge_seeds(seeds):
    """one entry per (project, type, subject): seen union by ref ordered by date, count = max(counts, len(seen)), promoted when any is"""
    merged = {}
    for s in seeds:
        key = (s['project'], s['type'], s['subject'])
        e = merged.setdefault(key, dict(s, seen=[], count=0, stage='candidate'))
        have = {x['ref'] for x in e['seen']}
        e['seen'] += [x for x in s['seen'] if x['ref'] not in have and not have.add(x['ref'])]
        e['count'] = max(e['count'], s['count'])
        if s['stage'] == 'promoted':
            e['stage'] = 'promoted'
    for e in merged.values():
        e['seen'].sort(key=lambda x: (x['date'] is None, x['date'] or ''))
        e['count'] = max(e['count'], len(e['seen']))
    return list(merged.values())


def cmd_plan(a):
    try:
        with open(a.export, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        err(f'{a.export}: {e}')
        return 2
    if not isinstance(data, list) or not all(isinstance(m, dict) and isinstance(m.get('id'), str) and isinstance(m.get('memory'), str) for m in data):
        err(f'{a.export}: want a JSON array of {{id, memory, metadata}} objects')
        return 2
    mapped = [map_memory(m) for m in data]
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, 'payloads.jsonl'), 'w', encoding='utf-8', newline='\n') as f:
        for payload, _, _ in mapped:
            f.write(json.dumps(payload, ensure_ascii=False) + '\n')
    inputs = [s for _, s, _ in mapped if s]
    seeds = merge_seeds(inputs)
    with open(os.path.join(a.out, 'lesson-seeds.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'lessons': seeds}, f, ensure_ascii=False, indent=2)
        f.write('\n')
    unparsed = [p['metadata']['mem0_id'] for p, _, clean in mapped if not clean]
    print(json.dumps({'payloads': len(mapped), 'seeds': len(seeds), 'seed_inputs': len(inputs), 'unparsed_seen': unparsed, 'out': a.out}, ensure_ascii=False))
    return 0


def body_for(payload, fields):
    """keep only the keys the worker accepts; the dropped keys ride in the text as a trailing 'meta:' line"""
    body = {k: v for k, v in payload.items() if k in fields}
    dropped = {k: v for k, v in payload.items() if k not in fields}
    if dropped:
        body['text'] = payload['text'] + '\nmeta: ' + json.dumps(dropped, ensure_ascii=False, sort_keys=True)
    return body


def cmd_post(a):
    try:
        with open(a.evidence, encoding='utf-8') as f:
            ev = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as e:
        err(f'{a.evidence}: {e}')
        return 2
    worker = ev.get('worker') if isinstance(ev, dict) else None
    ep = worker.get('save_endpoint') if isinstance(worker, dict) else None
    if not ep:
        err('the evidence records no worker save endpoint: feed the JSONL through the save tool')
        return 3
    fields = set(ep.get('body_fields') or [])
    if 'text' not in fields:
        err('save_endpoint.body_fields does not accept text')
        return 2
    url = str(worker.get('base_url', '')).rstrip('/') + ep['path']
    try:
        with open(a.payloads, encoding='utf-8', newline='\n') as f:
            payloads = [json.loads(line) for line in f.read().split('\n') if line.strip()]
        ids = [p['metadata']['mem0_id'] for p in payloads]
    except (OSError, ValueError, KeyError, TypeError) as e:
        err(f'{a.payloads}: {e}')
        return 2
    done = set()
    if os.path.isfile(a.done):
        with open(a.done, encoding='utf-8') as f:
            done = {line.strip() for line in f if line.strip()}
    os.makedirs(os.path.dirname(os.path.abspath(a.done)), exist_ok=True)
    posted = skipped = 0
    for payload, mem_id in zip(payloads, ids):
        if mem_id in done:
            skipped += 1
            continue
        req = urllib.request.Request(url, data=json.dumps(body_for(payload, fields), ensure_ascii=False).encode('utf-8'),
                                     method=ep.get('method', 'POST'), headers={'Content-Type': 'application/json; charset=utf-8'})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                ok = 200 <= resp.status < 300
                reply = resp.read().decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            ok, reply = False, 'HTTP %d %s' % (e.code, e.read().decode('utf-8', 'replace'))
        except (urllib.error.URLError, OSError) as e:
            ok, reply = False, str(e)
        if not ok:
            print(reply, file=sys.stderr)
            return 1
        with open(a.done, 'a', encoding='utf-8', newline='\n') as f:
            f.write(mem_id + '\n')
        done.add(mem_id)
        posted += 1
    print(json.dumps({'posted': posted, 'skipped': skipped}))
    return 0


def main(argv):
    ap = argparse.ArgumentParser(prog='mem0-to-claude-mem')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('plan')
    p.add_argument('--export', required=True)
    p.add_argument('--out', required=True)
    p.set_defaults(fn=cmd_plan)
    q = sub.add_parser('post')
    q.add_argument('--payloads', required=True)
    q.add_argument('--done', required=True)
    q.add_argument('--evidence', required=True)
    q.set_defaults(fn=cmd_post)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
