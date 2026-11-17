#!/usr/bin/env python3
"""Which tools each fleet role called, from local subagent transcripts.

Groups by role (agent type minus plugin prefix and effort suffix). MCP tools
are grouped as mcp__<server> with the distinct tool names. Aggregates only.
Writes only to --out."""
import argparse, collections, glob, json, os, re, sys, time

ROLES = {'brainstorm', 'scout', 'designer', 'implement', 'reviewer', 'test', 'devops'}


def role(at):
    r = re.sub(r'^agent-hub:', '', at)
    r = re.sub(r'-(low|medium|high|xhigh|max)$', '', r)
    return r if r in ROLES else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--logs', required=True, help='session-log directory (Claude Code projects dir)')
    ap.add_argument('--days', type=float, default=30, help='window in days (default 30)')
    ap.add_argument('--out', required=True, help='output file to write')
    a = ap.parse_args(argv)
    cut = time.time() - a.days * 86400
    runs = collections.Counter(); tools = collections.defaultdict(collections.Counter)
    mcp = collections.defaultdict(lambda: collections.defaultdict(set)); skills = collections.defaultdict(collections.Counter)
    for meta in glob.glob(os.path.join(a.logs, '*', '*', 'subagents', '*.meta.json')):
        tr = meta[:-len('.meta.json')] + '.jsonl'
        if not os.path.isfile(tr) or os.path.getmtime(tr) < cut:
            continue
        try:
            r = role(json.load(open(meta)).get('agentType') or '')
        except Exception:
            continue
        if not r:
            continue
        runs[r] += 1
        for line in open(tr, encoding='utf-8', errors='replace'):
            if '"tool_use"' not in line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get('type') != 'assistant':
                continue
            for c in ((e.get('message') or {}).get('content') or []):
                if isinstance(c, dict) and c.get('type') == 'tool_use':
                    n = c.get('name') or '?'
                    if n.startswith('mcp__'):
                        p = n.split('__'); srv = '__'.join(p[:2])
                        mcp[r][srv].add(p[-1]); tools[r][srv] += 1
                    else:
                        tools[r][n] += 1
                        if n == 'Skill':
                            skills[r][str((c.get('input') or {}).get('skill'))] += 1
    out = [f"window {a.days:g} days"]
    for r in sorted(runs, key=lambda k: -runs[k]):
        t = tools[r]
        out.append(f"\n## {r}: {runs[r]} runs, {sum(t.values())} tool calls")
        out.append('   ' + ' · '.join(f"{k} {v}" + (f" ({len(mcp[r][k])} tools: {','.join(sorted(mcp[r][k]))[:120]})" if k.startswith('mcp__') else '') for k, v in t.most_common()))
        if skills[r]:
            out.append('   skills: ' + ' · '.join(f"{k} {v}" for k, v in skills[r].most_common()))
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
