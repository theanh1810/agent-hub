#!/usr/bin/env python3
"""idle-report: what one Claude Code session paid in cache writes, and how much of it followed an idle gap.

usage: idle-report.py <session.jsonl | session dir> [--json]
       idle-report.py --self-test

Reads the session transcript `<session>.jsonl` and every `<session>/subagents/agent-*.jsonl` beside it; an
agent's type is `agentType` of its sibling `agent-<id>.meta.json` (`unknown` when that is missing or not a plain
name). A model call is one assistant message: transcript lines sharing a `message.id` are one call, and a
`<synthetic>` message is none. Per agent type, and for the main thread: the calls, the cache-write tokens split
by lifetime (5m, 1h), and the gaps between consecutive calls of one transcript in three buckets (under 5 min,
5 to 60 min, over 60 min) with the cache-write and cache-read tokens of the call that followed each gap, plus
the idle hours of the gaps of 5 min or more. Then the 10 largest cache writes that followed such a gap.

Read-only. Prints numbers, agent types and timestamps and nothing else from a transcript: no path, message
text or tool input. A line that is not JSON, not an assistant message or has no readable timestamp is skipped.
stdout: the table, or with --json one JSON object {"groups", "total", "top_rewrites"}; status on stderr.

Exit 0 report printed (or self-test passed) · 1 self-test failed · 2 usage error, or a path that is not an
existing regular file or directory (a FIFO, a device and `/` are refused).
"""
import argparse
import json
import re
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

MAIN = 'main'
UNKNOWN = 'unknown'
SYNTHETIC_MODEL = '<synthetic>'
AGENT_TYPE = re.compile(r'[A-Za-z0-9._:-]{1,80}')
IDLE_SECONDS = 5 * 60       # the 5-minute cache lifetime: a longer gap rewrites the cache
LONG_SECONDS = 60 * 60      # the 1-hour cache lifetime
BUCKETS = ('lt_5m', '5m_60m', 'gt_60m')
BUCKET_LABELS = {'lt_5m': '<5m', '5m_60m': '5-60m', 'gt_60m': '>60m'}
TOP_REWRITES = 10
STAMP = '%Y-%m-%dT%H:%M:%SZ'


def number(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def is_regular(path):
    """True for a regular file, after following a symlink: a FIFO or device would block a read forever."""
    try:
        return stat.S_ISREG(path.stat().st_mode)
    except OSError:
        return False


def parse_stamp(text):
    """A timestamp as an aware datetime; a trailing `Z` is `+00:00` because Python below 3.11 rejects `Z`."""
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    at = datetime.fromisoformat(text)
    return at if at.tzinfo else at.replace(tzinfo=timezone.utc)


def parse_lines(handle):
    """(message, usage, at) of each assistant line of an open transcript, read line by line."""
    for line in handle:
        try:
            entry = json.loads(line)
            message = entry['message']
            usage = message['usage']
            if entry['type'] != 'assistant' or message.get('model') == SYNTHETIC_MODEL:
                continue
            at = parse_stamp(entry['timestamp'])
            if not isinstance(usage, dict):
                continue
        except (ValueError, KeyError, TypeError, AttributeError):
            continue
        yield message, usage, at


def read_calls(path):
    """The model calls of one transcript in time order: [{at, write, write_5m, write_1h, read}]."""
    calls, by_id = [], {}
    if not is_regular(path):
        return calls
    try:
        with path.open(encoding='utf-8', errors='replace') as handle:
            parsed = list(parse_lines(handle))
    except OSError:
        return calls
    for message, usage, at in parsed:
        split = usage.get('cache_creation')
        split = split if isinstance(split, dict) else {}
        call = {'at': at, 'write': number(usage.get('cache_creation_input_tokens')),
                'write_5m': number(split.get('ephemeral_5m_input_tokens')),
                'write_1h': number(split.get('ephemeral_1h_input_tokens')),
                'read': number(usage.get('cache_read_input_tokens'))}
        message_id = message.get('id')
        earlier = by_id.get(message_id) if isinstance(message_id, str) else None
        if earlier is not None:
            call['at'] = earlier['at']
            earlier.update(call)
            continue
        if isinstance(message_id, str):
            by_id[message_id] = call
        calls.append(call)
    return sorted(calls, key=lambda c: c['at'])


def agent_type(transcript):
    meta = transcript.with_name(transcript.stem + '.meta.json')
    if not is_regular(meta):
        return UNKNOWN
    try:
        name = json.loads(meta.read_text(encoding='utf-8'))['agentType']
    except (OSError, ValueError, KeyError, TypeError):
        return UNKNOWN
    return name if isinstance(name, str) and AGENT_TYPE.fullmatch(name) else UNKNOWN


def is_subagent_transcript(path):
    return path.name.startswith('agent-') and path.suffix == '.jsonl'


def direct_label(transcript):
    """A subagent transcript given on its own: its meta file's agent type, else its file name."""
    label = agent_type(transcript)
    if label != UNKNOWN:
        return label
    return transcript.stem if AGENT_TYPE.fullmatch(transcript.stem) else UNKNOWN


def session_files(target):
    """(main transcript or None, session dir) for a transcript path or a session dir."""
    if target.is_dir():
        transcript = target.with_name(target.name + '.jsonl')
        return (transcript if transcript.is_file() else None), target
    return target, target.with_suffix('')


def new_group():
    return {'calls': 0, 'streams': 0, 'cache_write': 0, 'cache_write_5m': 0, 'cache_write_1h': 0,
            'gaps': {b: {'count': 0, 'cache_write': 0, 'cache_read': 0} for b in BUCKETS}, 'idle_hours': 0.0}


def bucket(seconds):
    if seconds < IDLE_SECONDS:
        return 'lt_5m'
    return '5m_60m' if seconds <= LONG_SECONDS else 'gt_60m'


def add_stream(group, name, calls, rewrites):
    group['streams'] += 1
    group['calls'] += len(calls)
    for call in calls:
        group['cache_write'] += call['write']
        group['cache_write_5m'] += call['write_5m']
        group['cache_write_1h'] += call['write_1h']
    for before, after in zip(calls, calls[1:]):
        seconds = (after['at'] - before['at']).total_seconds()
        cell = group['gaps'][bucket(seconds)]
        cell['count'] += 1
        cell['cache_write'] += after['write']
        cell['cache_read'] += after['read']
        if seconds >= IDLE_SECONDS:
            group['idle_hours'] += seconds / 3600
            rewrites.append({'agent_type': name, 'gap_minutes': round(seconds / 60, 1), 'cache_write': after['write'],
                             'timestamp': after['at'].astimezone(timezone.utc).strftime(STAMP)})


def build(target):
    if target.is_file() and is_subagent_transcript(target):
        streams = [(direct_label(target), target)]
    else:
        transcript, session_dir = session_files(target)
        streams = [(MAIN, transcript)] if transcript else []
        agents = session_dir / 'subagents'
        if agents.is_dir():
            streams += [(agent_type(p), p) for p in sorted(agents.glob('agent-*.jsonl')) if is_regular(p)]
    groups, rewrites = {}, []
    for name, path in streams:
        add_stream(groups.setdefault(name, new_group()), name, read_calls(path), rewrites)
    total = new_group()
    for group in groups.values():
        for key in ('calls', 'streams', 'cache_write', 'cache_write_5m', 'cache_write_1h', 'idle_hours'):
            total[key] += group[key]
        for b in BUCKETS:
            for key, value in group['gaps'][b].items():
                total['gaps'][b][key] += value
    for group in list(groups.values()) + [total]:
        group['idle_hours'] = round(group['idle_hours'], 2)
    ordered = {name: groups[name] for name in sorted(groups, key=lambda n: (n != MAIN, n))}
    rewrites.sort(key=lambda r: (-r['cache_write'], r['timestamp']))
    return {'groups': ordered, 'total': total, 'top_rewrites': rewrites[:TOP_REWRITES]}


def table(rows):
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    return ['  '.join(cell.ljust(w) if i == 0 else cell.rjust(w) for i, (cell, w) in enumerate(zip(row, widths))).rstrip()
            for row in rows]


def render(report):
    named = list(report['groups'].items()) + [('total', report['total'])]
    lines = ['Model calls and cache writes (tokens)']
    lines += table([('agent', 'calls', 'transcripts', 'cache-write', '5m', '1h')] + [
        (name, f"{g['calls']:,}", f"{g['streams']:,}", f"{g['cache_write']:,}", f"{g['cache_write_5m']:,}", f"{g['cache_write_1h']:,}")
        for name, g in named])
    lines += ['', 'Gaps between consecutive calls: count, then cache-write and cache-read tokens of the call after the gap']
    header = ['agent']
    for b in BUCKETS:
        header += [BUCKET_LABELS[b] + ' n', 'write', 'read']
    rows = [tuple(header + ['idle h (>=5m)'])]
    for name, g in named:
        row = [name]
        for b in BUCKETS:
            cell = g['gaps'][b]
            row += [f"{cell['count']:,}", f"{cell['cache_write']:,}", f"{cell['cache_read']:,}"]
        rows.append(tuple(row + [f"{g['idle_hours']:.2f}"]))
    lines += table(rows)
    lines += ['', f'Largest cache writes after a gap of 5 min or more (top {TOP_REWRITES})']
    if report['top_rewrites']:
        lines += table([('agent', 'gap min', 'cache-write', 'timestamp')] + [
            (r['agent_type'], f"{r['gap_minutes']:.1f}", f"{r['cache_write']:,}", r['timestamp']) for r in report['top_rewrites']])
    else:
        lines.append('none')
    return '\n'.join(lines)


def self_test():
    def line(message_id, stamp, write):
        return json.dumps({'type': 'assistant', 'timestamp': stamp, 'message': {'id': message_id, 'usage': {
            'cache_creation_input_tokens': write, 'cache_read_input_tokens': 1,
            'cache_creation': {'ephemeral_5m_input_tokens': write, 'ephemeral_1h_input_tokens': 0}}}})
    with tempfile.TemporaryDirectory(prefix='idle-report-') as tmp:
        root = Path(tmp).resolve()
        (root / 's' / 'subagents').mkdir(parents=True)
        (root / 's.jsonl').write_text('not json\n' + line('a', '2026-01-01T00:00:00Z', 5) + '\n'
                                      + line('b', '2026-01-01T00:10:00Z', 7) + '\n', encoding='utf-8')
        (root / 's' / 'subagents' / 'agent-1.jsonl').write_text(line('c', '2026-01-01T00:00:00Z', 3) + '\n', encoding='utf-8')
        (root / 's' / 'subagents' / 'agent-1.meta.json').write_text('{"agentType": "scout"}', encoding='utf-8')
        report = build(root / 's.jsonl')
    main = report['groups'][MAIN]
    ok = (main['calls'] == 2 and main['gaps']['5m_60m'] == {'count': 1, 'cache_write': 7, 'cache_read': 1}
          and report['groups']['scout']['cache_write_5m'] == 3 and report['total']['cache_write'] == 15
          and [r['cache_write'] for r in report['top_rewrites']] == [7] and 'scout' in render(report))
    print('idle-report self-test: ' + ('ok' if ok else 'FAILED'), file=sys.stderr)
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('session', nargs='?', help='the session transcript (<session>.jsonl) or the session dir beside it')
    ap.add_argument('--json', action='store_true', help='print one JSON object in place of the table')
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if not a.session:
        ap.print_usage(sys.stderr)
        return 2
    target = Path(a.session).expanduser().resolve()
    if not target.name or not (target.is_dir() or is_regular(target)):
        print('idle-report: not an existing regular file or directory', file=sys.stderr)
        return 2
    report = build(target)
    print(json.dumps(report) if a.json else render(report))
    return 0


if __name__ == '__main__':
    sys.exit(main())
