#!/usr/bin/env python3
"""Resolve one plan across docs/changes, docs/plan, docs/specs/changes and their archives; --resolve maps an old path through docs/changes/MIGRATION-MAP.tsv."""
import argparse
import json
from pathlib import Path
import sys
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))   # python3 -I leaves the script folder off sys.path
import plan_paths


def locate(root, plan_id):
    parent = plan_paths.plan_dir(root, plan_id)   # checks the id and raises 'expected one plan, found N' as before
    path = parent / 'plan.yaml'
    doc = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(doc, dict) or doc.get('plan_id') != plan_id:
        raise ValueError(f'{path}: plan_id does not match {plan_id}')
    change = parent if any((root / r).resolve() in parent.parents for r in ('docs/changes', 'docs/specs/changes')) else None
    record = plan_paths.record(parent, root, plan_id)   # raises 'multiple machine records' as before
    existing = [record] if record else []
    return {'plan_id': plan_id, 'plan_dir': str(parent), 'plan_ref': str(path),
            'change_dir': str(change) if change else None,
            'analysis_ref': str(existing[0]) if existing else None,
            'change_design_ref': str(existing[0]) + '#change_design' if existing else None}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--resolve', metavar='PATH', help='print the new path of an old path through docs/changes/MIGRATION-MAP.tsv; exit 1 when unmapped')
    parser.add_argument('plan_id', nargs='?')
    args = parser.parse_args()
    root = args.workspace.expanduser().resolve()
    if args.resolve:
        new = plan_paths.resolve(root, args.resolve)
        if new is None:
            print(f'plan-locate: {args.resolve} is not mapped by {plan_paths.MAP_FILE}', file=sys.stderr)
            sys.exit(1)
        print(new)
        sys.exit(0)
    try:
        if not args.plan_id:
            raise ValueError('give a plan id or --resolve PATH')
        print(json.dumps(locate(root, args.plan_id), indent=2))
    except (ValueError, OSError, yaml.YAMLError) as exc:
        print(f'plan-locate: {exc}', file=sys.stderr)
        sys.exit(1)
