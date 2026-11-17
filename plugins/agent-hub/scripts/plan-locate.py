#!/usr/bin/env python3
"""Resolve one change folder under openspec/changes (archive included) and print its files as JSON."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # python3 -I leaves the script folder off sys.path
import plan_paths as P


def locate(root, plan_id):
    folder = P.change_dir(root, plan_id)
    if folder is None or not (folder / P.TASKS).is_file():
        raise ValueError(f'{plan_id}: expected one change folder with {P.TASKS}, found none')
    return {'plan_id': plan_id, 'change_dir': str(folder), 'tasks_ref': str(folder / P.TASKS),
            'plan_vi_ref': str(folder / P.PLAN_VI), 'design_ref': str(folder / P.DESIGN),
            'archived': folder.parent.name == 'archive' and folder.parent.parent.name == 'changes'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('plan_id')
    args = parser.parse_args()
    try:
        print(json.dumps(locate(args.workspace.expanduser().resolve(), args.plan_id), indent=2))
    except (ValueError, OSError) as exc:
        print(f'plan-locate: {exc}', file=sys.stderr)
        sys.exit(1)
