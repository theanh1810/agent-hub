#!/usr/bin/env python3
"""Context size at the first model call of each subagent run, by agent type.

Reads <logs>/*/*/subagents/*.meta.json and the matching .jsonl transcripts.
First-call context = input + cache_creation + cache_read tokens of the first
assistant entry carrying usage. Aggregates only. Writes only to --out."""
import argparse, glob, json, os, statistics as st, sys, time


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--logs', required=True, help='session-log directory (Claude Code projects dir)')
    ap.add_argument('--days', type=float, default=14, help='window in days (default 14)')
    ap.add_argument('--out', required=True, help='output file to write')
    a = ap.parse_args(argv)
    cut = time.time() - a.days * 86400
    rows = {}
    for meta in glob.glob(os.path.join(a.logs, '*', '*', 'subagents', '*.meta.json')):
        tr = meta[:-len('.meta.json')] + '.jsonl'
        if not os.path.isfile(tr) or os.path.getmtime(tr) < cut:
            continue
        try:
            at = json.load(open(meta)).get('agentType') or '?'
        except Exception:
            continue
        first = None; seen = set(); turns = 0; peak = 0; model = None
        try:
            for line in open(tr, encoding='utf-8', errors='replace'):
                if '"usage"' not in line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                m = e.get('message') or {}
                u = m.get('usage')
                if e.get('type') != 'assistant' or not u:
                    continue
                rid = e.get('requestId') or m.get('id')
                ctx = sum(u.get(k) or 0 for k in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens'))
                if first is None:
                    first = (ctx, (u.get('cache_read_input_tokens') or 0) / ctx if ctx else 0.0)
                    model = m.get('model')
                if rid not in seen:
                    seen.add(rid); turns += 1
                peak = max(peak, ctx)
        except OSError:
            continue
        if first:
            rows.setdefault(at, []).append((first[0], first[1], turns, peak, model))
    out = [f"window: last {a.days:g} days; agent types: {len(rows)}; runs: {sum(len(v) for v in rows.values())}",
           f"{'agent type':<34}{'n':>4}{'first-call ctx median':>23}{'min':>8}{'max':>8}{'cache-read share':>18}{'turns med':>10}{'peak ctx med':>13}  models"]
    for at, v in sorted(rows.items(), key=lambda kv: -len(kv[1])):
        c = [x[0] for x in v]
        models = sorted({(x[4] or '?').replace('claude-', '') for x in v})
        out.append(f"{at:<34}{len(v):>4}{round(st.median(c)):>23}{min(c):>8}{max(c):>8}{st.median([x[1] for x in v]):>18.2f}"
                   f"{round(st.median([x[2] for x in v])):>10}{round(st.median([x[3] for x in v])):>13}  {','.join(models)[:60]}")
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
