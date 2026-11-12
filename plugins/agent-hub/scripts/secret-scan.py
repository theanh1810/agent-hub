#!/usr/bin/env python3
"""secret-scan: find secret-shaped strings in written evidence and print each hit masked.

usage: secret-scan.py PATH [PATH ...]

A PATH is a file or a directory (walked). Text files only: a file whose first 8 KB holds a NUL byte is skipped.
Each hit prints `path:line: <pattern-name> <fixed prefix>` for a high-confidence pattern (at most the prefix the pattern
itself defines, such as ghp_ or AKIA) and `path:line: <pattern-name> len=<N>` for a low-confidence one; never a character of the secret.
.secret-scan-allow, in a scanned directory (or in the folder of a scanned file), lists `path:line` pairs,
the path relative to that folder, for fixtures; an allowed hit prints `allowed` and does not fail.
There is no write mode: the writer redacts the value and runs the scan again.
A hit is skipped, not counted, when its value is a placeholder on a low-confidence pattern (bearer-token, cookie-value,
connection-password, generic-assignment) or a masked run of x or * on a high-confidence one.

Exit 0 no hit, 1 any hit, 2 usage error or an unreadable path.
"""
import argparse
import os
import re
import sys

ALLOW_FILE = '.secret-scan-allow'
SHOWN = 4
PROBE = 8192
# group 1 is the secret value; every pattern is linear in the line length, so a one-line HAR file is safe
# third field: True = high confidence, skipped only when the value is a masked run; False = low confidence,
# skipped when the value looks like a placeholder (the exemption of PLACEHOLDERISH and MASKED_VALUE below)
# fourth field: the fixed prefix a high-confidence hit may print, matched at the start of the value; None prints nothing of the value
PATTERNS = (
    ('bearer-token', re.compile(r'Authorization\W{1,6}Bearer\s+([\w.~+/=-]{8,})', re.I), False, None),
    ('bearer-token', re.compile(r'"name"\s*:\s*"Authorization"\s*,\s*"value"\s*:\s*"(?:Bearer\s+)?([^"\s]{8,})"', re.I), False, None),
    ('cookie-value', re.compile(r'\b(?:Set-)?Cookie\W{1,6}[\w.-]+=([^;\s"\']{4,})', re.I), False, None),
    ('cookie-value', re.compile(r'"name"\s*:\s*"(?:Set-)?Cookie"\s*,\s*"value"\s*:\s*"([^"]{4,})"', re.I), False, None),
    ('header-token', re.compile(r'"name"\s*:\s*"(?:PRIVATE-TOKEN|X-Api-Key)"\s*,\s*"value"\s*:\s*"([^"]{8,})"', re.I), False, None),
    ('github-token', re.compile(r'\b(gh[pous]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})'), True, re.compile(r'gh[pous]_|github_pat_')),
    ('sk-api-key', re.compile(r'\b(sk-[A-Za-z0-9_-]{20,})'), True, re.compile(r'sk-')),
    ('stripe-key', re.compile(r'\b(sk_(?:live|test)_\w{16,})'), True, re.compile(r'sk_(?:live|test)_')),
    ('gitlab-token', re.compile(r'\b(glpat-[\w-]{20,})'), True, re.compile(r'glpat-')),
    ('google-api-key', re.compile(r'\b(AIza[\w-]{35})'), True, re.compile(r'AIza')),
    ('aws-access-key', re.compile(r'\b(AKIA[0-9A-Z]{16})\b'), True, re.compile(r'AKIA')),
    ('jwt', re.compile(r'\b(eyJ[\w-]{5,}\.eyJ[\w-]{5,}\.[\w-]*)'), True, re.compile(r'eyJ')),
    ('private-key', re.compile(r'(-----BEGIN [A-Z ]*PRIVATE KEY-----)'), True, re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
    ('slack-webhook', re.compile(r'hooks\.slack\.com/services/([\w/]{8,})'), True, None),
    ('discord-webhook', re.compile(r'discord(?:app)?\.com/api/webhooks/\d+/([\w-]{8,})'), True, None),
    ('connection-password', re.compile(r'\b[a-z][a-z0-9+.-]*://[^\s:/@]+:([^\s@/]+)@', re.I), False, None),
    ('generic-assignment', re.compile(r'\b(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD)["\']?\s*=\s*["\']?([^\s"\']{8,})', re.I), False, None),
    ('generic-assignment', re.compile(r'\b(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD)["\']?\s*:\s*["\']([^\s"\']{8,})["\']', re.I), False, None),
    ('generic-assignment', re.compile(r'\b(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD)["\']?\s*:\s*((?=[\w.~+/=-]{8,}(?:[\s,;)]|$))[\w.~+/=-]*\d[\w.~+/=-]*)', re.I), False, None),
    ('slack-token', re.compile(r'\b(xox[baprs]-[A-Za-z0-9-]{10,})'), True, re.compile(r'xox[baprs]-')),
)
PLACEHOLDERISH = re.compile(r'\{[^}]{0,60}\}|<[a-z][a-z_-]*>|\*{3,}|x{4,}|redacted|masked|example|changeme|placeholder|dummy|sample|^your[_-]', re.I)
MASKED_VALUE = re.compile(r'^[A-Za-z_-]*[xX*]{4,}$')


def _raise(err):
    raise err


def read_allow(root):
    try:
        with open(os.path.join(root, ALLOW_FILE), encoding='utf-8') as f:
            return {line.strip() for line in f if line.strip() and not line.startswith('#')}
    except FileNotFoundError:
        return set()


def is_text(path):
    with open(path, 'rb') as f:
        return b'\0' not in f.read(PROBE)


def reveal(high, prefix, value):
    """what a hit may print: the fixed prefix of a high-confidence pattern, the length of a low-confidence value; never a character of the secret"""
    if high:
        m = prefix.match(value) if prefix else None
        return m.group(0) if m else ''
    return f'len={len(value)}'


def scan_file(path, rel, allow):
    hits = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for n, line in enumerate(f, 1):
            found = []
            for name, rx, high, prefix in PATTERNS:
                for m in rx.finditer(line):
                    if (MASKED_VALUE if high else PLACEHOLDERISH).search(m.group(1)):
                        continue
                    found.append((m.span(1), name, high, prefix, m.group(1)))
            firm = [s for s, _, high, _, _ in found if high]
            for (x, y), name, high, prefix, value in found:
                if not high and any(x < e and s < y for s, e in firm):
                    continue          # the same value is already one high-confidence hit
                allowed = f'{rel}:{n}' in allow
                hits.append((n, name, 'allowed' if allowed else reveal(high, prefix, value), allowed))
    return hits


def scan_arg(arg):
    """-> [(path, line, pattern name, shown text, allowed)]; raises OSError for an unreadable path"""
    if os.path.isdir(arg):
        root, paths = arg, []
        for d, dirs, names in os.walk(arg, onerror=_raise):
            dirs.sort()
            paths += [os.path.join(d, n) for n in sorted(names) if n != ALLOW_FILE]
    elif os.path.isfile(arg):
        root, paths = os.path.dirname(arg) or '.', [arg]
    else:
        raise FileNotFoundError(f'no such file or directory: {arg}')
    allow, out = read_allow(root), []
    for path in paths:
        if is_text(path):
            out += [(path, *hit) for hit in scan_file(path, os.path.relpath(path, root).replace(os.sep, '/'), allow)]
    return out


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('paths', nargs='+', metavar='PATH')
    failed, unreadable = False, False
    for arg in ap.parse_args(argv).paths:
        try:
            hits = scan_arg(arg)
        except OSError as e:
            print(f'secret-scan: cannot read {arg}: {e}', file=sys.stderr)
            unreadable = True
            continue
        for path, n, name, shown, allowed in hits:
            print(f'{path}:{n}: {name}' + (f' {shown}' if shown else ''))
            failed = failed or not allowed
    return 2 if unreadable else int(failed)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
