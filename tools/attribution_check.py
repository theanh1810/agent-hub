#!/usr/bin/env python3
"""attribution_check.py: check `quoted_passages_attributed`.

Every block between vendored markers must be byte-equal to the pinned upstream lines it names, and its origin must
have an entry (a heading naming `owner/repo`) in THIRD_PARTY_NOTICES.md. A run of MIN_RUN or more consecutive lines
identical to a pinned upstream file, outside markers, is an uncredited quote and fails.

Marker format (blueprint 3.9):
  <!-- vendored:begin id=<id> src=<owner/repo>@<pin>:<upstream path>#L<a>-L<b> licence=<SPDX> -->
  ...the upstream lines a..b, unchanged...
  <!-- vendored:end id=<id> -->

Data: tools/upstream/manifest.yaml (rows: origin, pin, upstream_path, local, sha256, status pinned|owed, optional
quoted_in: paths or globs that already quote the source without markers).
Usage: attribution_check.py [--root DIR]    exit 0 clean, 1 problems (one per line on stdout), 2 bad input.
Wiring: tools/check-ruleset.sh imports this module and calls quoted_passages_attributed(); by hand run `python3 -B -I tools/attribution_check.py`."""
import fnmatch
import hashlib
import os
import re
import sys

MIN_RUN = 3          # consecutive identical lines that make a quote
MIN_CHARS = 60       # stripped characters a run needs, so a run of "---" or "```" lines is not a quote
MAX_BYTES = 1_000_000
TEXT_EXT = ('.md', '.py', '.sh', '.yaml', '.yml', '.txt', '.json', '.toml')
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', 'build', '.cm-tmp'}
BEGIN = re.compile(r'^<!-- vendored:begin id=(\S+) src=([^@\s]+)@(\S+?):(\S+)#L(\d+)-L(\d+) licence=(\S+) -->\s*$')
END = re.compile(r'^<!-- vendored:end id=(\S+) -->\s*$')


def parse_manifest(text):
    """Flat YAML subset: `sources:` then `- key: value` items; scalars plain or double-quoted, lists as [a, b]."""
    rows, cur = [], None
    for raw in text.split('\n'):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        m = re.match(r'^(\s*)(- )?([A-Za-z_][\w]*):\s*(.*)$', line)
        if not m or not m.group(1) + (m.group(2) or ''):
            continue                       # top-level scalar (version, sources)
        if m.group(2):
            cur = {}
            rows.append(cur)
        if cur is None:
            continue
        val = m.group(4)
        if val.startswith('[') and val.endswith(']'):
            cur[m.group(3)] = [v.strip().strip('"') for v in val[1:-1].split(',') if v.strip()]
        elif len(val) >= 2 and val[0] == val[-1] == '"':
            cur[m.group(3)] = val[1:-1].replace('\\"', '"')
        else:
            cur[m.group(3)] = val
    return rows


def read_bytes(path):
    with open(path, 'rb') as f:
        return f.read()


def split_lines(data):
    lines = data.decode('utf-8', errors='replace').split('\n')
    return lines[:-1] if lines and lines[-1] == '' else lines


def pin_matches(a, b):
    short, long_ = sorted((a, b), key=len)
    return len(short) >= 7 and long_.startswith(short) or a == b


def notices_has(notices, origin):
    return any(l.lstrip().startswith('#') and origin.lower() in l.lower() for l in notices.split('\n'))


def scan_blocks(lines):
    """Return (blocks, masked line indices, problems). A block is (id, begin idx, end idx, header groups)."""
    blocks, masked, problems = [], set(), []
    i = 0
    while i < len(lines):
        m = BEGIN.match(lines[i])
        if not m:
            i += 1
            continue
        j = i + 1
        while j < len(lines) and not END.match(lines[j]) and not BEGIN.match(lines[j]):
            j += 1
        if j >= len(lines) or not END.match(lines[j]) or END.match(lines[j]).group(1) != m.group(1):
            problems.append((i + 1, f'unterminated vendored block id={m.group(1)}'))
            masked.update(range(i, min(j, len(lines))))
            i = j
            continue
        blocks.append((m.group(1), i, j, m.groups()))
        masked.update(range(i, j + 1))
        i = j + 1
    return blocks, masked, problems


def quoted_passages_attributed(root, min_run=MIN_RUN):
    """Return a list of problem strings; empty means the check passes."""
    root = os.path.abspath(root)
    out = []
    man_path = os.path.join(root, 'tools', 'upstream', 'manifest.yaml')
    rows = []
    if os.path.isfile(man_path):
        with open(man_path, encoding='utf-8') as f:
            rows = parse_manifest(f.read())
    notices_path = os.path.join(root, 'THIRD_PARTY_NOTICES.md')
    notices = read_bytes(notices_path).decode('utf-8', errors='replace') if os.path.isfile(notices_path) else ''
    by_key = {}
    cache = {}                                           # local path -> lines of a verified pinned copy
    for r in rows:
        if r.get('status') == 'pinned':
            p = os.path.join(root, r.get('local', ''))
            if not os.path.isfile(p):
                out.append(f'manifest: {r.get("local")} is missing')
                continue
            data = read_bytes(p)
            if hashlib.sha256(data).hexdigest() != r.get('sha256'):
                out.append(f'manifest: sha256 of {r["local"]} differs from its row')
                continue
            cache[r['local']] = split_lines(data)
        by_key[(r.get('origin', '').lower(), r.get('upstream_path'))] = r

    index = {}                                           # N consecutive lines -> [(row, first line number)]
    for r in rows:
        lines = cache.get(r.get('local'))
        if lines is None or r.get('upstream_path', '').rsplit('/', 1)[-1].upper().startswith('LICENSE'):
            continue
        for k in range(len(lines) - min_run + 1):
            key = tuple(l.rstrip() for l in lines[k:k + min_run])
            index.setdefault(key, []).append((r, k + 1))

    for dirpath, dirs, files in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, '/')
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and (rel_dir + '/' + d).lstrip('./') != 'tools/upstream')
        for name in sorted(files):
            if not name.endswith(TEXT_EXT):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace(os.sep, '/')
            if os.path.islink(path) or os.path.getsize(path) > MAX_BYTES:
                continue
            lines = split_lines(read_bytes(path))
            blocks, masked, bad = scan_blocks(lines)
            out.extend(f'{rel}:{n}: {msg}' for n, msg in bad)
            for bid, b, e, (_, origin, pin, upath, a, z, lic) in blocks:
                a, z = int(a), int(z)
                where = f'{rel}:{b + 1}: vendored block id={bid}'
                row = by_key.get((origin.lower(), upath))
                if row is None:
                    out.append(f'{where}: no manifest row for {origin} {upath}')
                    continue
                if row.get('status') != 'pinned':
                    out.append(f'{where}: source is owed ({row.get("owed_by", "scan unnamed")}), no pinned copy to compare')
                    continue
                if not pin_matches(pin, row.get('pin', '')):
                    out.append(f'{where}: pin {pin} is not the manifest pin {row.get("pin")}')
                if not notices_has(notices, origin):
                    out.append(f'{where}: origin {origin} has no entry in THIRD_PARTY_NOTICES.md')
                up = cache.get(row['local'])
                if up is None:
                    out.append(f'{where}: pinned copy of {upath} unusable')
                elif not (1 <= a <= z <= len(up)):
                    out.append(f'{where}: lines {a}-{z} outside {upath} ({len(up)} lines)')
                elif lines[b + 1:e] != up[a - 1:z]:
                    out.append(f'{where}: content differs from {origin}@{pin[:12]} {upath}:{a}-{z}')
            flagged = {}
            for k in range(len(lines) - min_run + 1):
                if any(x in masked for x in range(k, k + min_run)):
                    continue
                win = lines[k:k + min_run]
                hits = index.get(tuple(l.rstrip() for l in win))
                if not hits or sum(len(l.strip()) for l in win) < MIN_CHARS or sum(1 for l in win if l.strip()) < 2:
                    continue
                for row, ul in hits:
                    if any(fnmatch.fnmatch(rel, g) for g in (row.get('quoted_in') or [])):
                        if not notices_has(notices, row['origin']):
                            out.append(f'{rel}:{k + 1}: quoted_in credit names {row["origin"]}, which has no entry in THIRD_PARTY_NOTICES.md')
                        break
                    flagged.setdefault(k, (row, ul))
                    break
            starts = sorted(flagged)
            g = 0
            while g < len(starts):
                h = g
                while h + 1 < len(starts) and starts[h + 1] == starts[h] + 1:
                    h += 1
                row, ul = flagged[starts[g]]
                out.append(f'{rel}:{starts[g] + 1}-{starts[h] + min_run}: uncredited quote of {row["origin"]} '
                           f'{row["upstream_path"]}:{ul} ({min_run}+ identical lines outside vendored markers)')
                g = h + 1
    return out


def main(argv):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if argv[:1] == ['--root'] and len(argv) == 2:
        root = argv[1]
    elif argv:
        print('usage: attribution_check.py [--root DIR]', file=sys.stderr)
        return 2
    problems = quoted_passages_attributed(root)
    for p in problems:
        print(p)
    if problems:
        print(f'quoted_passages_attributed: {len(problems)} problem(s)', file=sys.stderr)
        return 1
    print('quoted_passages_attributed: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
