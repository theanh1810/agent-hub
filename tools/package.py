#!/usr/bin/env python3
"""package.py: build build/release/, a copy of the marketplace with every plugin.

Usage: package.py [--out DIR] [--no-validate]
  --out DIR       release tree (default: build/release in this repo); a tree this tool built is replaced, an empty folder is
                  reused, any other existing folder is refused; the repo, its ancestors and the home folder are always refused
  --no-validate   skip `claude plugin validate` even when claude is on PATH
Steps: copy .claude-plugin/ and plugins/ (no caches), copy LICENSE and THIRD_PARTY_NOTICES.md into every
plugin of the copy, write VERSION (the agent-hub plugin version), run `claude plugin validate` if claude exists.
Exit 0 built, 1 validate failed, 2 a required file is missing (the message names it), an --out that is refused, or bad arguments.
The agents directory is copied as is: one file per role, no effort variant (effort is passed per spawn).
Publishing the tree is not done here."""
import json
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IGNORE = shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store', '.pytest_cache')
TOP_FILES = ('README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md')
PLUGIN_FILES = ('LICENSE', 'THIRD_PARTY_NOTICES.md')   # each plugin is installed alone, so each carries both
MARKER = '.agent-hub-package'   # written into every tree this tool builds; its presence lets a later run replace the tree


def out_error(repo, out):
    """-> the reason `out` must not be deleted and rebuilt, else None"""
    out, repo = os.path.realpath(out), os.path.realpath(repo)
    home = os.path.realpath(os.path.expanduser('~'))
    for label, path in (('the repo root', repo), ('the home folder', home)):
        if out == path or path.startswith(out.rstrip(os.sep) + os.sep):
            return f'--out {out} is {label} or one of its ancestors'
    if os.path.lexists(out) and not os.path.isdir(out):
        return f'--out {out} exists and is not a folder'
    if os.path.isdir(out) and os.listdir(out) and not os.path.isfile(os.path.join(out, MARKER)):
        return f'--out {out} is not empty and has no {MARKER} (this tool did not build it)'
    return None


def build(repo=REPO, out=None, validate=True):
    """Build the release tree; return (exit code, message)."""
    out = out or os.path.join(repo, 'build', 'release')
    plugin_src = os.path.join(repo, 'plugins', 'agent-hub')
    for name in PLUGIN_FILES:   # checked before anything is deleted or copied
        if not os.path.isfile(os.path.join(repo, name)):
            return 2, f'missing: {name} (every packaged plugin carries it)'
    refused = out_error(repo, out)
    if refused:
        return 2, refused
    try:
        if os.path.isdir(out):
            shutil.rmtree(out)
        os.makedirs(out)
        with open(os.path.join(out, MARKER), 'w', encoding='utf-8') as f:
            f.write('built by tools/package.py; a later run may replace this folder\n')
        shutil.copytree(os.path.join(repo, '.claude-plugin'), os.path.join(out, '.claude-plugin'), ignore=IGNORE)
        shutil.copytree(os.path.join(repo, 'plugins'), os.path.join(out, 'plugins'), ignore=IGNORE)
        for name in TOP_FILES:
            if os.path.isfile(os.path.join(repo, name)):
                shutil.copy2(os.path.join(repo, name), os.path.join(out, name))
        plugins_out = os.path.join(out, 'plugins')
        for name in PLUGIN_FILES:
            for plugin in sorted(os.listdir(plugins_out)):
                if os.path.isdir(os.path.join(plugins_out, plugin)):
                    shutil.copy2(os.path.join(repo, name), os.path.join(plugins_out, plugin, name))
        with open(os.path.join(plugin_src, '.claude-plugin', 'plugin.json'), encoding='utf-8') as f:
            version = json.load(f)['version']
        with open(os.path.join(out, 'VERSION'), 'w', encoding='utf-8') as f:
            f.write(version + '\n')
    except FileNotFoundError as exc:
        return 2, f'missing: {exc}'
    msg = f'built {out}, version {version}'
    if validate and shutil.which('claude'):
        res = subprocess.run(['claude', 'plugin', 'validate', out], capture_output=True, text=True)
        if res.returncode != 0:
            return 1, msg + f'; claude plugin validate exit {res.returncode}: {(res.stdout + res.stderr).strip()}'
        msg += '; claude plugin validate ok'
    return 0, msg


def main(argv):
    out, validate, i = None, True, 0
    while i < len(argv):
        if argv[i] == '--out' and i + 1 < len(argv):
            out, i = argv[i + 1], i + 2
        elif argv[i] == '--no-validate':
            validate, i = False, i + 1
        else:
            print('usage: package.py [--out DIR] [--no-validate]', file=sys.stderr)
            return 2
    code, msg = build(out=out, validate=validate)
    print(msg, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
