"""Where the plan lane keeps its files: one named constant per location, and the helpers that resolve a change folder.

Each location lives here and nowhere else."""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # python3 -I leaves the script folder off sys.path
import _paths

if _paths.lib_path().is_dir():
    sys.path.insert(0, str(_paths.lib_path()))

CHANGES_DIR = 'openspec/changes'
ARCHIVE_DIR = 'openspec/changes/archive'
LIVE_SPECS_DIR = 'openspec/specs'
DEBT_FILE = 'openspec/_debt.md'
GLOSSARY_FILE = 'openspec/glossary.md'
SCOPE_FILE = 'openspec/scope.md'

# files of a change folder
PROPOSAL = 'proposal.md'
DESIGN = 'design.md'
TASKS = 'tasks.md'
SPECS_DIR = 'specs'
PLAN_VI = 'plan.vi.md'
APPROVAL = 'approval.md'
ERRORS = 'errors.yaml'
QUESTIONS = 'questions.md'
REVIEWS_DIR = 'reviews'

EPHEMERAL_DIR = '.cm-tmp'   # throwaway output (review packets) lives in <root>/.cm-tmp/<change>/
PLAN_ID = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')


def read_yaml(path):
    """the parsed YAML of a file"""
    import yaml
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def workspace_root(path):
    """-> the folder holding openspec/ that contains path"""
    p = os.path.abspath(path)
    while p != os.path.dirname(p):
        if os.path.isdir(os.path.join(p, 'openspec')) or os.path.basename(p) == 'openspec':
            return p if os.path.basename(p) != 'openspec' else os.path.dirname(p)
        p = os.path.dirname(p)
    raise ValueError(f'{path} is not inside an openspec/ workspace')


def ephemeral_dir(root, plan_id):
    """-> Path of the throwaway folder of a change, root/.cm-tmp/{plan_id}; not created here."""
    return Path(root) / EPHEMERAL_DIR / plan_id


def change_dir(root, plan_id):
    """-> Path of openspec/changes/<id> or its archive, None when there is none; the id must be lowercase kebab-case"""
    if not PLAN_ID.fullmatch(plan_id):
        raise ValueError('change id must be lowercase kebab-case')
    root = Path(root)
    dirs = sorted({p.resolve() for pattern in (f'{CHANGES_DIR}/{plan_id}', f'{ARCHIVE_DIR}/{plan_id}', f'{ARCHIVE_DIR}/????-??-??-{plan_id}')
                   for p in root.glob(pattern) if p.is_dir()})
    if len(dirs) > 1:
        raise ValueError(f'{plan_id}: expected one change folder, found {len(dirs)}: {[str(p) for p in dirs]}')
    return dirs[0] if dirs else None


def live_specs(folder):
    """-> the live specs folder of the workspace that holds change folder `folder`"""
    return Path(workspace_root(folder)) / LIVE_SPECS_DIR
