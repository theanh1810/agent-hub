#!/usr/bin/env python3
"""Bootstrap floor per role in bytes: agent file + core + eager skills.

S0 = the whole core; S1 = a subagent gets the subagent view of rules/core.md
(hooks/rules_inject.view_text: the main-only fenced blocks dropped, as the hook
injects it); S2 = S1 minus the eager-skill trim. Roles whose agent file is
absent are skipped. Frontmatter is parsed by hand (runs under python3 -I).
Reads <plugin-root>; writes only to --out."""
import argparse, importlib.util, os, sys

RATIO = 2.733
TRIM = {'scout': ['context-memory'], 'implement': ['gitnexus-flow'], 'reviewer': ['gitnexus-flow']}
ROLES = ['reviewer', 'implement', 'test', 'brainstorm', 'devops', 'designer', 'scout']


def subagent_view(root, core):
    """The core as the SubagentStart hook injects it, before the install-root substitution; the whole core when the plugin has no hook."""
    hook = os.path.join(root, 'hooks', 'rules_inject.py')
    if not os.path.isfile(hook):
        return core
    sys.path.insert(0, os.path.join(root, 'hooks'))
    try:
        spec = importlib.util.spec_from_file_location('rules_inject', hook)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod.view_text(core, 'subagent')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plugin-root', required=True, help='plugin root (holds rules/, agents/, skills/)')
    ap.add_argument('--out', required=True, help='output file to write')
    a = ap.parse_args(argv)
    root = a.plugin_root
    core = open(os.path.join(root, 'rules/core.md'), encoding='utf-8').read()
    kept = subagent_view(root, core)
    core_b, sub_b = len(core.encode()), len(kept.encode())
    size = lambda p: os.path.getsize(os.path.join(root, p))

    def fm(role):
        t = open(os.path.join(root, f'agents/{role}.md'), encoding='utf-8').read().split('---')[1]
        skills, on = [], False
        for l in t.splitlines():
            if l.startswith('skills:'):
                on = True; continue
            if on and l.startswith('  - '):
                skills.append(l[4:].strip())
            elif on:
                on = False
        return skills, 'omitClaudeMd: true' in t

    out = [f"core.md {core_b} B; subagent view {sub_b} B; dropped {core_b - sub_b} B in {core.count('<!-- main-only:begin -->')} blocks"]
    out.append(f"{'role':<13}{'agent':>7}{'skills':>8} | {'S0 B':>7}{'tok':>7} | {'S1 B':>7}{'tok':>7} | {'S2 B':>7}{'tok':>7} | S0->S2")
    tot = [0, 0, 0]
    for role in ROLES:
        if not os.path.isfile(os.path.join(root, f'agents/{role}.md')):
            continue
        skills, omit = fm(role)
        ag = size(f'agents/{role}.md'); sk = sum(size(f'skills/{s}/SKILL.md') for s in skills)
        s0 = ag + sk + (0 if omit else core_b)
        s1 = ag + sk + (0 if omit else sub_b)
        s2 = s1 - sum(size(f'skills/{s}/SKILL.md') for s in TRIM.get(role, []) if s in skills)
        for i, v in enumerate((s0, s1, s2)):
            tot[i] += v
        out.append(f"{role:<13}{ag:>7}{sk:>8} | {s0:>7}{round(s0/RATIO):>7} | {s1:>7}{round(s1/RATIO):>7} | {s2:>7}{round(s2/RATIO):>7} | {100*(s2-s0)/s0:+.0f}%")
    out.append(f"sum {tot} {[round(t/RATIO) for t in tot]}")
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
