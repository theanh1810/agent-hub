#!/usr/bin/env python3
"""PostToolUse(Edit|Write|MultiEdit) hook: an opt-in formatter and linter for the file just edited.

Does nothing unless the env var AGENT_HUB_FORMAT_ON_EDIT is '1' (a project opts in through the env block of its
.claude/settings.json). It finds the nearest package.json above the edited file, runs that project's own
node_modules/.bin/prettier --write on a file prettier formats, then node_modules/.bin/eslint --no-fix on a JS-family file
and, when eslint reports findings, prints the first 20 lines to stderr and exits 2 so the agent sees them.
Never npx, never a download, never a global binary. Any error or timeout exits 0 silently: a convenience, not a gate.
"""
import json
import os
import subprocess
import sys

OPT_IN = 'AGENT_HUB_FORMAT_ON_EDIT'
PRETTIER_EXT = {'.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.vue', '.json', '.css', '.scss', '.less', '.html', '.md', '.mdx',
                '.yaml', '.yml', '.graphql'}
ESLINT_EXT = {'.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.vue'}
MAX_LINES = 20
TIMEOUT = 12


def package_root(path):
    """the nearest folder above path that holds a package.json, or None"""
    d = os.path.dirname(os.path.abspath(path))
    while True:
        if os.path.isfile(os.path.join(d, 'package.json')):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def local_bin(root, name):
    p = os.path.join(root, 'node_modules', '.bin', name)
    return p if os.path.isfile(p) and os.access(p, os.X_OK) else None


def run(cmd, root):
    return subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=TIMEOUT)


def main():
    if os.environ.get(OPT_IN) != '1':
        return 0
    try:
        data = json.loads(sys.stdin.read())
        path = data['tool_input']['file_path']
        if not isinstance(path, str) or not os.path.isfile(path):
            return 0
        root = package_root(path)
        if root is None:
            return 0
        ext = os.path.splitext(path)[1].lower()
        prettier = local_bin(root, 'prettier')
        if prettier and ext in PRETTIER_EXT:
            run([prettier, '--write', path], root)
        eslint = local_bin(root, 'eslint')
        if eslint and ext in ESLINT_EXT:
            res = run([eslint, '--no-fix', path], root)
            if res.returncode == 1:
                lines = (res.stdout or res.stderr).splitlines()[:MAX_LINES]
                sys.stderr.write('\n'.join(lines) + '\n')
                return 2
    except Exception:
        return 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
