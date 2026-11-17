#!/usr/bin/env python3
"""plan-check: the five machine checks of a change folder, and its approval stamp.

usage: plan-check.py CHANGE_DIR [--stamped]             run the five checks; last line `plan-check: N/5 passed`; exit 0 only when all pass.
                                                        Before the gate an absent or stale stamp is PENDING, not a failure: last line
                                                        `plan-check: 4/4 passed, stamp pending`, exit 0. With --stamped (main thread before each
                                                        wave, the last implement spawn at closeout) an absent or stale stamp fails.
       plan-check.py stamp CHANGE_DIR --words FILE      write approval.md with the stamp and the user's words verbatim;
                                                        a re-stamp keeps the earlier stamps and words under ## Earlier approvals

Checks: (1) every task has Files, Covers, Done when, Test, no task id appears twice and every task line sits under a `## Wave <n>` heading; (2) every Covers names a scenario in the change's spec deltas or the live
specs; (3) task ids of tasks.md and plan.vi.md are the same set, each once in plan.vi.md; (4) approval.md holds a stamp that matches the folder now (absent or stale: pending before the gate, a failure with --stamped);
(5) every task block of plan.vi.md holds the data-and-screens section heading (DATA_HEADING) on a line of its own.
The stamp is sha256 over the sorted (task id, Files) pairs and the bytes of specs/** under the change; prose files do not enter it.
It is computed only when check 1 passes: a duplicated id would otherwise hide a task's Files from it."""
import argparse
import hashlib
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # python3 -I leaves the script folder off sys.path
import plan_paths as P

KEYS = ('Files', 'Covers', 'Done when', 'Test')
DATA_HEADING = '#### Dữ liệu và màn hình bị ảnh hưởng'  # scrub-allow: the Vietnamese heading the check matches
DATA_LINE = re.compile(r'^' + re.escape(unicodedata.normalize('NFC', DATA_HEADING)) + r'\s*$', re.M)
WAVE_HEADING = re.compile(r'^## Wave \d+\b')
ANY_WAVE_WORD = re.compile(r'^#{1,6}\s*Wave\b', re.I)
H2 = re.compile(r'^## \S')
TASK_LINE = re.compile(r'^- \[[ xX]\] (\d+\.\d+) (.+?)\s*$')
KEY_LINE = re.compile(r'^\s+(Files|Covers|Done when|Test):[ \t]*(.*?)\s*$')
SCENARIO = re.compile(r'^#### Scenario:\s*(.+?)\s*$', re.M)
BLOCK = re.compile(r'^### (\d+\.\d+)\b.*$', re.M)
STAMP_LINE = re.compile(r'^stamp:\s*([0-9a-f]{12})\s*$', re.M)


def id_key(tid):
    return tuple(int(n) for n in tid.split('.'))


def scan_tasks(text):
    """-> ({task id: {key: value}}, [structure problem]) from tasks.md; a key that is absent is absent from the dict.
    Problems: a duplicated task id (the first block is kept), a task line outside any `## Wave <n>` section."""
    tasks, problems, current, wave, seen = {}, [], None, None, set()   # wave: None, 'ok' or 'malformed'
    for line in text.splitlines():
        if ANY_WAVE_WORD.match(line) or H2.match(line):
            wave = 'ok' if WAVE_HEADING.match(line) else 'malformed' if ANY_WAVE_WORD.match(line) else None
            continue
        m = TASK_LINE.match(line)
        if m:
            tid = m.group(1)
            if wave != 'ok':
                problems.append(f'task {tid} is outside a `## Wave <n>` section' + (' (malformed wave heading)' if wave else ''))
            if tid in seen:
                problems.append(f'duplicate task id {tid} in tasks.md')
                current = {}   # the second block never overwrites the first
                continue
            seen.add(tid)
            current = tasks.setdefault(tid, {})
            continue
        k = KEY_LINE.match(line)
        if k and current is not None:
            current[k.group(1)] = k.group(2)
    return tasks, problems


def parse_tasks(text):
    return scan_tasks(text)[0]


def csv(value):
    return [v.strip() for v in value.split(',') if v.strip()]


def scenarios(folder):
    names = set()
    for base in (folder / P.SPECS_DIR, P.live_specs(folder)):
        for f in base.rglob('spec.md') if base.is_dir() else []:
            names |= set(SCENARIO.findall(f.read_text(encoding='utf-8')))
    return names


def compute_stamp(folder):
    """-> first 12 hex of sha256 over sorted (task id, sorted Files) pairs and the bytes of specs/** by sorted path.
    The caller computes it only after check 1 passed (unique ids, every task under a wave)."""
    h = hashlib.sha256()
    tasks = parse_tasks((folder / P.TASKS).read_text(encoding='utf-8'))
    for tid in sorted(tasks, key=id_key):
        h.update(f"{tid}\0{chr(0).join(sorted(csv(tasks[tid].get('Files', ''))))}\n".encode('utf-8'))
    specs = folder / P.SPECS_DIR
    for f in sorted(p for p in specs.rglob('*') if p.is_file()) if specs.is_dir() else []:
        h.update(f.relative_to(folder).as_posix().encode('utf-8') + b'\0' + f.read_bytes() + b'\0')
    return h.hexdigest()[:12]


def scan_blocks(text):
    """-> ({task id: block text}, [duplicated task id]) of plan.vi.md, one block per `### <id>` heading (the first of a duplicate is kept)"""
    marks = list(BLOCK.finditer(text))
    out, dups = {}, []
    for i, m in enumerate(marks):
        body = text[m.end():marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        if m.group(1) in out:
            dups.append(m.group(1))
        else:
            out[m.group(1)] = body
    return out, dups


def blocks(text):
    return scan_blocks(text)[0]


def run_checks(folder, stamped=False):
    """-> [(number, passed, detail)] for the five checks; passed is None for a stamp not written yet when stamped is False"""
    folder = Path(folder)
    tasks, problems = scan_tasks((folder / P.TASKS).read_text(encoding='utf-8')) if (folder / P.TASKS).is_file() else ({}, [])
    vi, vi_dups = scan_blocks((folder / P.PLAN_VI).read_text(encoding='utf-8')) if (folder / P.PLAN_VI).is_file() else ({}, [])
    out = []
    gaps = problems + [f'{t} lacks {k}' for t in sorted(tasks, key=id_key) for k in KEYS if not tasks[t].get(k)]
    check1 = bool(tasks) and not gaps
    out.append((1, check1, '; '.join(gaps) or ('no task found in tasks.md' if not tasks else 'ok')))
    known = scenarios(folder)
    unknown = [f'{t}: {n}' for t in sorted(tasks, key=id_key) for n in csv(tasks[t].get('Covers', ''))
               if n.lower() != 'none' and n not in known]
    out.append((2, not unknown, 'unknown scenario ' + '; '.join(unknown) if unknown else 'ok'))
    only_t, only_v = sorted(set(tasks) - set(vi), key=id_key), sorted(set(vi) - set(tasks), key=id_key)
    drift = ([f'only in tasks.md: {only_t}; only in plan.vi.md: {only_v}'] if only_t or only_v else []) + [f'duplicate task id {t} in plan.vi.md' for t in vi_dups]
    out.append((3, not drift, '; '.join(drift) or 'ok'))
    approval = folder / P.APPROVAL
    found = STAMP_LINE.search(approval.read_text(encoding='utf-8')) if approval.is_file() else None
    if not check1:
        out.append((4, False, 'stamp not computed: check 1 failed'))
    elif not found:
        out.append((4, False, f'{P.APPROVAL} has no stamp line') if stamped else (4, None, 'not stamped yet (pending)'))
    else:
        now = compute_stamp(folder)
        out.append((4, True, 'ok') if found.group(1) == now else (4, False, f'stamp {found.group(1)} is stale (now {now})') if stamped
                   else (4, None, f'stamp {found.group(1)} is stale (now {now}): re-approval pending'))
    bare = [t for t in sorted(vi, key=id_key) if not DATA_LINE.search(unicodedata.normalize('NFC', vi[t]))]
    out.append((5, not bare, f'no data section in {bare}' if bare else 'ok'))
    return out


EARLIER = '## Earlier approvals'
EARLIER_BLOCK = re.compile(r'^### earlier stamp (\S+)\s*$', re.M)


def earlier_approvals(old):
    """-> the `## Earlier approvals` section for a re-stamp: the old file's own stamp and words as one `### earlier stamp <hex>` block,
    then the blocks that file already held, unchanged. No line of it starts with `stamp:`, so STAMP_LINE matches only the new stamp."""
    head, _, held = old.partition('\n' + EARLIER + '\n')
    m = STAMP_LINE.search(head)
    words = head.split("## User's words", 1)
    body = words[1].strip('\n') if len(words) == 2 else head.strip('\n') if not m else ''
    block = f"### earlier stamp {m.group(1) if m else 'none'}\n{body}\n"
    kept = f"\n{held.strip(chr(10))}\n" if held.strip() else ''
    return f"\n{EARLIER}\n\n{block}{kept}"


def write_stamp(folder, words):
    """Writes approval.md; returns False (nothing written) when check 1 fails, since the stamp would hide a task's Files."""
    ok, detail = run_checks(folder)[0][1:]
    if not ok:
        print(f'plan-check: no stamp, check 1 failed: {detail}', file=sys.stderr)
        return False
    text = f"# Approval\n\nstamp: {compute_stamp(folder)}\n\n## User's words\n\n{Path(words).read_text(encoding='utf-8').strip()}\n"
    approval = Path(folder) / P.APPROVAL
    if approval.is_file():
        text += earlier_approvals(approval.read_text(encoding='utf-8'))
    approval.write_text(text, encoding='utf-8')
    return True


def main(argv):
    ap = argparse.ArgumentParser(prog='plan-check', description=__doc__.split('\n')[0])
    ap.add_argument('args', nargs='+', metavar='[stamp] CHANGE_DIR')
    ap.add_argument('--words')
    ap.add_argument('--stamped', action='store_true', help='an absent approval stamp fails instead of pending')
    a = ap.parse_args(argv)
    stamping = a.args[0] == 'stamp'
    folder = Path(a.args[-1])
    if len(a.args) != (2 if stamping else 1) or not (folder / P.TASKS).is_file():
        print(f'plan-check: give a change folder holding {P.TASKS}', file=sys.stderr)
        return 2
    if stamping:
        if not a.words or not Path(a.words).is_file():
            print('plan-check: stamp needs --words FILE with the user\'s words', file=sys.stderr)
            return 2
        if not write_stamp(folder, a.words):
            return 1
        print(f'plan-check: wrote {folder / P.APPROVAL}')
        return 0
    results = run_checks(folder, stamped=a.stamped)
    for n, ok, detail in results:
        print(f"{'PENDING' if ok is None else 'PASS' if ok else 'FAIL'} {n} {detail}")
    passed = sum(ok is True for _, ok, _ in results)
    if any(ok is None for _, ok, _ in results) and not any(ok is False for _, ok, _ in results):
        print(f'plan-check: {passed}/4 passed, stamp pending')
        return 0
    print(f'plan-check: {passed}/5 passed')
    return 0 if passed == 5 else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
