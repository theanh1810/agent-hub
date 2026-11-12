#!/usr/bin/env python3
"""Effort variants: agents/<role>-<effort>.md rendered from agents/<role>.md of one plugin folder.

A variant is its base byte for byte except four frontmatter lines: name, description, effort and
maxTurns (refs/effort-routing.md § Turn caps). Variants are release artefacts: they are written
into the given output tree only, never into plugins/.

Usage: effort-variants.py --out DIR [--plugin DIR] [ROLE ...]
  --plugin DIR   the plugin folder holding agents/ and refs/ (default: plugins/agent-hub of this repo)
  --out DIR      the tree that receives DIR/agents/<variant>.md
  ROLE ...       only the variants of these roles (default: all)
Exit 0 written, 2 when a base agent is missing (the message names it) or the arguments are wrong.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PLUGIN = os.path.join(REPO, 'plugins', 'agent-hub')
VARIANTS = (
    'brainstorm-high', 'brainstorm-max', 'brainstorm-xhigh',
    'designer-high', 'designer-medium',
    'devops-low', 'devops-xhigh',
    'implement-high', 'implement-medium',
    'planner-high', 'planner-medium',
    'reviewer-high', 'reviewer-max', 'reviewer-xhigh',
    'test-high', 'test-medium',
)


def base_path(plugin, variant):
    return os.path.join(plugin, 'agents', variant.rsplit('-', 1)[0] + '.md')


def turn_caps(plugin):
    path = os.path.join(plugin, 'refs', 'effort-routing.md')
    if not os.path.exists(path):
        return {}
    text = open(path, encoding='utf-8').read()
    sec = text.split('\n## Turn caps\n', 1)[1].split('\n## ', 1)[0] if '\n## Turn caps\n' in text else ''
    return dict(re.findall(r'^\| ([a-z-]+) \| (\d+) \|$', sec, re.M))


def render(plugin, variant, caps=None):
    role, effort = variant.rsplit('-', 1)
    base = open(base_path(plugin, variant), encoding='utf-8').read()
    caps = turn_caps(plugin) if caps is None else caps
    head, fence, body = base[len('---\n'):].partition('\n---\n')
    out = []
    for line in head.split('\n'):
        if line.startswith('name: '):
            line = f'name: {variant}'
        elif line.startswith('description: '):
            line = (f'description: "Effort variant of {role} at {effort}: the same rules as {role}. '
                    f'Spawn it only where refs/effort-routing.md § Variants names it."')
        elif line.startswith('effort: '):
            line = f'effort: {effort}'
        elif line.startswith('maxTurns: ') and variant in caps:
            line = f'maxTurns: {caps[variant]}'
        out.append(line)
    return '---\n' + '\n'.join(out) + fence + body


def build(plugin, out, roles=()):
    """Write the variants into out/agents; return their names. FileNotFoundError names a missing base."""
    todo = [v for v in VARIANTS if not roles or v.rsplit('-', 1)[0] in roles]
    for v in todo:
        if not os.path.isfile(base_path(plugin, v)):
            raise FileNotFoundError(base_path(plugin, v))
    caps = turn_caps(plugin)
    os.makedirs(os.path.join(out, 'agents'), exist_ok=True)
    for v in todo:
        path = os.path.join(out, 'agents', f'{v}.md')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(render(plugin, v, caps))
        os.chmod(path, 0o644)
    return todo


def main(argv):
    plugin, out, roles, i = DEFAULT_PLUGIN, None, [], 0
    while i < len(argv):
        a = argv[i]
        if a in ('--out', '--plugin') and i + 1 < len(argv):
            if a == '--out':
                out = argv[i + 1]
            else:
                plugin = argv[i + 1]
            i += 2
        elif a.startswith('--'):
            print(f'unknown or incomplete argument: {a}', file=sys.stderr)
            return 2
        else:
            roles.append(a)
            i += 1
    if not out:
        print('usage: effort-variants.py --out DIR [--plugin DIR] [ROLE ...]', file=sys.stderr)
        return 2
    if roles and not any(v.rsplit('-', 1)[0] in roles for v in VARIANTS):
        print(f'no variant is defined for {roles}', file=sys.stderr)
        return 2
    try:
        written = build(plugin, out, roles)
    except FileNotFoundError as exc:
        print(f'base agent missing: {exc}', file=sys.stderr)
        return 2
    print('written: ' + ' '.join(written))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
