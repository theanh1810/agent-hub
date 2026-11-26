#!/usr/bin/env python3
"""ledger-record: write one review-and-test pass into errors.yaml from the agents' returned JSON.

usage: ledger-record.py --errors FILE --round N --input RETURN.json [--input ...]
                        [--source review-test] [--failure-docs DIR] [--close-resolved]
       ledger-record.py --self-test

Each --input holds one reviewer or test return, saved verbatim: the object is read from the last fenced `json` block,
or, in a file with no such block, from the first `{` (a raw JSON return, with or without the header line before it).
Only a return with `status: completed` is recorded; any other status is refused, because a failed or partial
return says nothing about the build. The script appends round N to FILE (created with `meta.error_loop_count: 0`
when absent): one entry per finding and per failed case, its text verbatim, its `location`, `rule`,
`recommendation`, `confidence` and `repro` as fields of their own, its severity mapped (blocking, warning,
suggestion become critical, major, minor; a failed case takes the severity test gave it). A severity the return
does not give is recorded as major with `severity_defaulted: true`. A `minor[]` line opening `[out-of-diff 🔴|🟠|🟡]`
stays `severity: minor` and gains `out_of_diff: true` and `real_severity` (critical, major or minor), its text
untouched. Every minor entry is also listed, with its description, under the round's `deferred_errors[]`. Earlier rounds keep every byte, line ends included (a CRLF file gets CRLF lines), with one exception: with
--close-resolved, on a pass that is not red, each earlier open entry named in `resolves[]` of a fix entry
(`errors[*].analysis.fix_list[*]`, nowhere else) gains a `closed_in: N` line under its `id`. --close-resolved
needs a reviewer return and a test return among the inputs: one of them alone cannot show a defect fixed.
stdout: one JSON line {"round", "verdict", "critical", "major", "minor", "entry_ids", "closed"}; status on stderr.
`analysis` and `meta` stay with brainstorm mode=error-batch: the script writes neither.

Exit 0 round written (any verdict) · 2 usage error, an unreadable or malformed input, a return that is not
`completed`, `minor` or `failed_test_case_ids` that is not a list of strings, a case id that is not a plain file
name · 3 FILE has a shape this script does not append to (round N already there, `errors:` is not the last
top-level key, or with --close-resolved FILE is not valid YAML or an entry to close is written in flow style or
has a YAML alias or anchor as its `id`). Nothing is written on 2 or 3.
"""
import argparse
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))
import yaml  # noqa: E402  (the plugin's bundled copy)

SEVERITY = {'blocking': 'critical', 'warning': 'major', 'suggestion': 'minor',
            'critical': 'critical', 'major': 'major', 'minor': 'minor'}
CONTROL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x85  ]')
NEW_FILE = 'meta:\n  error_loop_count: 0\nerrors:\n'
MINOR_REASON = 'minor: filed by agent-hub ledger, not fixed in this run'
RECORDED_STATUS = 'completed'
CASE_ID = re.compile(r'[A-Za-z0-9._-]+')
FINDING_FIELDS = ('rule', 'recommendation', 'confidence', 'repro')
OUT_OF_DIFF = re.compile(r'\[out-of-diff (🔴|🟠|🟡)\]\s*')
REAL_SEVERITY = {'🔴': 'critical', '🟠': 'major', '🟡': 'minor'}
ID_REFERENCE = re.compile(r'[ \t]*:[ \t]*[*&]')   # what follows an `id` key written as a YAML alias or anchor
FENCED_JSON = re.compile(r'(?msi)^```jsonc?[ \t]*\r?\n(.*?)^```[ \t]*\r?$')   # a return's object block (`json` or `jsonc`); prose before it may hold braces


class Shape(Exception):
    """The errors file cannot take an appended round."""


def quoted(value):
    """A JSON string is a valid YAML double-quoted scalar."""
    return json.dumps(CONTROL.sub(' ', str(value)), ensure_ascii=False)


def load_return(path):
    raw = open(path, encoding='utf-8').read()
    blocks = list(FENCED_JSON.finditer(raw))
    text = blocks[-1].group(1) if blocks else raw
    start = text.find('{')
    if start < 0:
        raise ValueError(f'{path}: no JSON object')
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as e:
        if not blocks:
            raise
        line = raw.count('\n', 0, blocks[-1].start()) + 1
        raise ValueError(f'{path}: the fenced block at line {line} is not valid JSON ({e}); a `jsonc` block may not keep comments or trailing commas')
    if not isinstance(obj, dict):
        raise ValueError(f'{path}: the return is not a JSON object')
    if obj.get('status') != RECORDED_STATUS:
        raise ValueError(f'{path}: status is {obj.get("status")!r}; only a `{RECORDED_STATUS}` return is recorded')
    return obj


def is_review(ret):
    return 'verdict' in ret or 'review_file' in ret


def objects(ret, key):
    """The list under key, every item an object; raises ValueError naming the first entry that is not."""
    items = ret.get(key) or []
    if not isinstance(items, list):
        raise ValueError(f'`{key}` is not a list')
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f'`{key}[{i}]` is not an object: {json.dumps(item, ensure_ascii=False)[:80]}')
    return items


def strings(ret, key):
    """The list under key, every item a string; raises ValueError naming the key or the first item that is not."""
    items = ret.get(key)
    if items is None:
        return []
    if not isinstance(items, list):
        raise ValueError(f'`{key}` is not a list')
    for i, item in enumerate(items):
        if not isinstance(item, str):
            raise ValueError(f'`{key}[{i}]` is not a string: {json.dumps(item, ensure_ascii=False)[:80]}')
    return items


def severity_of(given):
    """{severity} as given, or major marked as a default when the return gives none this script knows."""
    if given in SEVERITY:
        return {'severity': SEVERITY[given]}
    return {'severity': 'major', 'severity_defaulted': True}


def minor_entry(line):
    """Fields of one `minor[]` line: its location, and the real severity of an out-of-diff finding. The text stays verbatim."""
    text = line
    tag = OUT_OF_DIFF.match(text)
    extra = {'out_of_diff': True, 'real_severity': REAL_SEVERITY[tag.group(1)]} if tag else {}
    return {'severity': 'minor', **extra, 'location': text[tag.end() if tag else 0:].split(' — ')[0].strip(), 'text': text}


def failure_doc(docs_dir, case_id, fallback):
    """(evidence path, text) of a failed case: its failure doc when DIR holds one, else the fallback text."""
    if not isinstance(case_id, str) or not CASE_ID.fullmatch(case_id) or '..' in case_id:
        raise ValueError(f'case id {case_id!r} is not a plain name (letters, digits, `-`, `_`, `.`, no `..`)')
    if not docs_dir:
        return '', fallback
    root = os.path.realpath(docs_dir)
    path = os.path.join(docs_dir, f'{case_id}.md')
    if not os.path.isfile(path):
        return '', fallback
    if os.path.dirname(os.path.realpath(path)) != root:
        raise ValueError(f'case id {case_id!r}: {path} resolves outside {docs_dir}')
    return path, open(path, encoding='utf-8').read()


def entries_of(ret, docs_dir):
    """One dict per finding or failed case of a reviewer or test return: source, evidence, severity, location, text."""
    out = []
    if is_review(ret):
        base = {'source': 'reviewer-' + str(ret.get('mode') or 'task'), 'evidence': ret.get('review_file') or ''}
        for f in objects(ret, 'findings'):
            out.append({**base, **severity_of(f.get('severity')), 'location': f.get('location') or '',
                        **{k: f[k] for k in FINDING_FIELDS if f.get(k)}, 'text': str(f.get('description') or '')})
        for line in strings(ret, 'minor'):
            out.append({**base, **minor_entry(line)})
        return out
    flows = {f.get('test_case_id'): f for f in objects(ret, 'flow_results')}
    for case_id in strings(ret, 'failed_test_case_ids'):
        flow = flows.get(case_id) or {'test_case_id': case_id}
        evidence, text = failure_doc(docs_dir, case_id, json.dumps(flow, ensure_ascii=False))
        out.append({'source': 'test', 'evidence': evidence, **severity_of(flow.get('severity')), 'location': case_id, 'text': text})
    for case in objects(ret, 'exploratory_cases'):
        if case.get('status') == 'fail':
            evidence, text = failure_doc(docs_dir, case.get('id'), f"{case.get('id')}: {case.get('oracle')}")
            out.append({'source': 'test-explore', 'evidence': evidence, **severity_of(case.get('severity')),
                        'location': case['id'], 'text': text})
    for finding in objects(ret, 'fidelity_findings'):
        out.append({'source': 'test', 'evidence': finding.get('source_ref') or '', 'severity': 'major',
                    'location': str(finding.get('screen') or ''), 'text': json.dumps(finding, ensure_ascii=False)})
    return out


def literal(text, indent):
    """` |2-` block scalar holding text verbatim (line ends normalised, control characters dropped)."""
    text = CONTROL.sub('', text.replace('\r\n', '\n').replace('\r', '\n')).strip('\n')
    if not text.strip():
        return ' ""'
    pad = ' ' * indent
    return ' |2-\n' + '\n'.join(pad + line if line else '' for line in text.split('\n'))


def render_round(number, source, verdict, entries, base, eol='\n'):
    b = ' ' * base
    out = [f'{b}- round: {number}', f'{b}  round_source: {source}', f'{b}  verdict: {verdict}',
           f'{b}  entries:' + ('' if entries else ' []')]
    deferred = []
    for entry_id, e in entries:
        out += [f'{b}    - id: {entry_id}', f'{b}      source: {e["source"]}', f'{b}      evidence: {quoted(e["evidence"])}',
                f'{b}      severity: {e["severity"]}']
        if e.get('severity_defaulted'):
            out.append(f'{b}      severity_defaulted: true')
        real = f'real_severity: {e["real_severity"]}, out_of_diff: true, ' if e.get('out_of_diff') else ''
        if real:
            out += [f'{b}      real_severity: {e["real_severity"]}', f'{b}      out_of_diff: true']
        out += [f'{b}      {k}: {quoted(e[k])}' for k in ('location', *FINDING_FIELDS) if e.get(k)]
        out.append(f'{b}      text:' + literal(e['text'], base + 8))
        if e['severity'] == 'minor':
            deferred.append(f'{b}    - {{id: {quoted(entry_id)}, severity: minor, {real}source: {quoted(e["source"])}, '
                            f'location: {quoted(e["location"])}, description: {quoted(e["text"])}, '
                            f'reason: {quoted(MINOR_REASON)}, round: {number}}}')
    out += [f'{b}  deferred_errors:' + ('' if deferred else ' []'), *deferred, f'{b}  user_decisions: []']
    return ('\n'.join(out) + '\n').replace('\n', eol)


def read_existing(path, number):
    """(text ending in a line end, indent of `- round:`, the file's line end); raises Shape when a round cannot be appended."""
    if not os.path.exists(path):
        return NEW_FILE, 2, '\n'
    text = open(path, encoding='utf-8', newline='').read()
    eol = '\r\n' if re.search(r'\r?\n|$', text).group() == '\r\n' else '\n'   # the first line's own ending
    tops = re.findall(r'(?m)^([A-Za-z_][\w-]*):', text)
    head = re.search(r'(?m)^errors:[ \t]*(\[\s*\])?[ \t]*\r?$', text)
    if not tops or tops[-1] != 'errors' or not head:
        raise Shape('`errors:` is not the last top-level key')
    if head.group(1):
        text = text[:head.start()] + 'errors:' + eol + text[head.end():].lstrip('\r\n')
    first = re.search(r'(?m)^( *)- round:', text[head.start():])
    base = len(first.group(1)) if first else 2
    if re.search(rf'(?m)^ {{{base}}}- round: {number}[ \t]*\r?$', text):
        raise Shape(f'round {number} is already recorded')
    return (text if text.endswith('\n') else text + eol), base, eol


def child(node, key):
    """(key node, value node) of a mapping node's key, or (None, None)."""
    if isinstance(node, yaml.MappingNode):
        for k, v in node.value:
            if isinstance(k, yaml.ScalarNode) and k.value == key:
                return k, v
    return None, None


def items(node):
    return node.value if isinstance(node, yaml.SequenceNode) else []


def close_resolved(text, number, eol='\n'):
    """Add `closed_in: number` under the `id` of each open entry a fix entry resolves. Returns (text, closed ids).

    The file is parsed, so finding text is never read as structure: `resolves` counts only in
    `errors[*].analysis.fix_list[*]`, and the new line goes right after an entry's own `id` line, never inside a
    block scalar. Nothing is re-serialised: every existing byte stays."""
    try:
        root = yaml.compose(text, Loader=yaml.SafeLoader)
    except yaml.YAMLError as e:
        raise Shape(f'not valid YAML, nothing closed: {" ".join(str(e).split())[:200]}')
    rounds = items(child(root, 'errors')[1])
    resolved = {r.value for rnd in rounds for fix in items(child(child(rnd, 'analysis')[1], 'fix_list')[1])
                for r in items(child(fix, 'resolves')[1]) if isinstance(r, yaml.ScalarNode)}
    inserts, closed = [], []
    for rnd in rounds:
        for entry in items(child(rnd, 'entries')[1]):
            key, value = child(entry, 'id')
            if not isinstance(value, yaml.ScalarNode) or value.value not in resolved or child(entry, 'closed_in')[0]:
                continue
            line_start = text.rfind('\n', 0, key.start_mark.index) + 1
            if ID_REFERENCE.match(text, key.end_mark.index):
                raise Shape(f'entry {value.value} has a YAML alias or anchor as its `id`, cannot add `closed_in`')
            line_end = text.find('\n', value.end_mark.index)
            if line_end > 0 and text[line_end - 1] == '\r':
                line_end -= 1
            lead = text[line_start:key.start_mark.index]
            if entry.flow_style or lead.strip(' -') or value.style in ('|', '>') or '\n' in text[line_start:value.end_mark.index]:
                raise Shape(f'entry {value.value} is not a block mapping with a one-line `id`, cannot add `closed_in`')
            inserts.append((len(text) if line_end < 0 else line_end, f'{eol}{" " * len(lead)}closed_in: {number}'))
            closed.append(value.value)
    for at, line in reversed(inserts):
        text = text[:at] + line + text[at:]
    return text, closed


def write_atomic(path, text):
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix='.ledger-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def record(errors_path, number, inputs, source='review-test', docs_dir=None, close=False):
    returns = [(path, load_return(path)) for path in inputs]
    if close and {is_review(ret) for _, ret in returns} != {True, False}:
        raise ValueError('--close-resolved needs a reviewer return and a test return, each `completed`')
    found = []
    for path, ret in returns:
        try:
            found += entries_of(ret, docs_dir)
        except ValueError as e:
            raise ValueError(f'{path}: {e}')
    entries = [(f'E{number}-{i}', e) for i, e in enumerate(found, 1)]
    count = {s: sum(1 for _, e in entries if e['severity'] == s) for s in ('critical', 'major', 'minor')}
    verdict = 'red' if count['critical'] or count['major'] else 'yellow' if count['minor'] else 'green'
    text, base, eol = read_existing(errors_path, number)
    closed = []
    if close and verdict != 'red':
        text, closed = close_resolved(text, number, eol)
    write_atomic(errors_path, text + render_round(number, source, verdict, entries, base, eol))
    return {'round': number, 'verdict': verdict, **count, 'entry_ids': [i for i, _ in entries], 'closed': closed}


def self_test():
    with tempfile.TemporaryDirectory() as d:
        def put(name, obj, header=''):
            path = os.path.join(d, name)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(header + json.dumps(obj, ensure_ascii=False))
            return path
        finding = 'path check: uses `startswith`  # not canonical\n  indented "quoted" line\n\nlast: line'
        review = put('review.json', {'status': 'completed', 'mode': 'independent', 'verdict': 'blocking', 'review_file': 'review.md ## Round 1',
                                     'findings': [{'severity': 'blocking', 'description': finding, 'location': 'src/a.rs:10'}],
                                     'minor': ['src/b.rs:2 — unused import — delete it',
                                               '[out-of-diff 🔴] src/c.rs:7 — token logged — mask it']}, '[reviewer · model: opus]\n')
        test = put('test.json', {'status': 'completed', 'gate': 'RED', 'failed_test_case_ids': ['TC-1-2'],
                                 'flow_results': [{'test_case_id': 'TC-1-2', 'failed_stage': 'submit', 'severity': 'major'}]})
        errors = os.path.join(d, 'plan', 'errors.yaml')
        first = record(errors, 1, [review, test])
        assert (first['verdict'], first['critical'], first['major'], first['minor']) == ('red', 1, 1, 2), first
        body = open(errors, encoding='utf-8').read()
        assert body.startswith(NEW_FILE) and '          path check: uses `startswith`  # not canonical\n' in body, body
        assert body.count('- {id: "E1-2", severity: minor') == 1 and '  analysis:' not in body, body
        assert body.count('- {id: "E1-3", severity: minor, real_severity: critical, out_of_diff: true, ') == 1, body
        fixed = body.replace('    user_decisions: []', '    analysis:\n      fix_list:\n        - {id: FX-1-1, resolves: [E1-1, E1-4]}\n    user_decisions: []', 1)
        with open(errors, 'w', encoding='utf-8') as f:
            f.write(fixed)
        clean = put('clean.json', {'status': 'completed', 'mode': 'independent', 'verdict': 'pass',
                                   'review_file': 'review.md ## Round 2', 'findings': []})
        green = put('green.json', {'status': 'completed', 'gate': 'GREEN', 'failed_test_case_ids': []})
        second = record(errors, 2, [clean, green], close=True)
        assert (second['verdict'], second['closed']) == ('green', ['E1-1', 'E1-4']), second
        after = open(errors, encoding='utf-8').read()
        assert after.replace('        closed_in: 2\n', '').startswith(fixed) and after.count('closed_in: 2') == 2, after
        try:
            record(errors, 2, [clean])
        except Shape:
            pass
        else:
            raise AssertionError('a repeated round must be refused')
        assert open(errors, encoding='utf-8').read() == after
        for refused in ([put('failed.json', {'status': 'failed', 'gate': 'RED'})], [clean]):
            try:
                record(errors, 3, refused, close=True)
            except ValueError:
                pass
            else:
                raise AssertionError('a return that is not completed, or a close without both returns, must be refused')
        assert open(errors, encoding='utf-8').read() == after
    print('ledger-record self-test: ok', file=sys.stderr)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--errors')
    ap.add_argument('--round', type=int)
    ap.add_argument('--input', action='append', default=[])
    ap.add_argument('--source', default='review-test')
    ap.add_argument('--failure-docs')
    ap.add_argument('--close-resolved', action='store_true')
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if not a.errors or a.round is None or a.round < 1 or not a.input:
        ap.error('--errors, --round (1 or more) and at least one --input are required')
    try:
        result = record(a.errors, a.round, a.input, a.source, a.failure_docs, a.close_resolved)
    except Shape as e:
        print(f'ledger-record: {a.errors}: {e}', file=sys.stderr)
        return 3
    except (OSError, ValueError) as e:
        print(f'ledger-record: {e}', file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
