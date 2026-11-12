#!/usr/bin/env python3
"""package.py: build build/release/, a copy of the marketplace with every plugin and the generated effort variants.

Usage: package.py [--out DIR] [--no-validate]
  --out DIR       release tree (default: build/release in this repo); an existing tree is replaced
  --no-validate   skip `claude plugin validate` even when claude is on PATH
Steps: copy .claude-plugin/ and plugins/ (no caches), render the variants into the agent-hub plugin of the
copy, write VERSION (the agent-hub plugin version), run `claude plugin validate` if claude exists.
Exit 0 built, 1 validate failed, 2 a base agent is missing (the message names it) or bad arguments.
Publishing the tree is not done here."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IGNORE = shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store', '.pytest_cache')
TOP_FILES = ('README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md')


def load_variants():
    spec = importlib.util.spec_from_file_location('effort_variants', os.path.join(REPO, 'tools', 'effort-variants.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(repo=REPO, out=None, validate=True):
    """Build the release tree; return (exit code, message)."""
    out = out or os.path.join(repo, 'build', 'release')
    plugin_src = os.path.join(repo, 'plugins', 'agent-hub')
    try:
        variants = load_variants()
        # fail before touching the old tree when a base agent is missing
        for v in variants.VARIANTS:
            if not os.path.isfile(variants.base_path(plugin_src, v)):
                return 2, f'base agent missing: {variants.base_path(plugin_src, v)}'
        if os.path.isdir(out):
            shutil.rmtree(out)
        os.makedirs(out)
        shutil.copytree(os.path.join(repo, '.claude-plugin'), os.path.join(out, '.claude-plugin'), ignore=IGNORE)
        shutil.copytree(os.path.join(repo, 'plugins'), os.path.join(out, 'plugins'), ignore=IGNORE)
        for name in TOP_FILES:
            if os.path.isfile(os.path.join(repo, name)):
                shutil.copy2(os.path.join(repo, name), os.path.join(out, name))
        written = variants.build(plugin_src, os.path.join(out, 'plugins', 'agent-hub'))
        with open(os.path.join(plugin_src, '.claude-plugin', 'plugin.json'), encoding='utf-8') as f:
            version = json.load(f)['version']
        with open(os.path.join(out, 'VERSION'), 'w', encoding='utf-8') as f:
            f.write(version + '\n')
    except FileNotFoundError as exc:
        return 2, f'missing: {exc}'
    msg = f'built {out}: {len(written)} variants, version {version}'
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
