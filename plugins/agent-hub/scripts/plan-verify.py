#!/usr/bin/env python3
"""plan-verify: the mechanical gates of a plan, or of a brainstorm change_design, in one run.

The mechanical checks (anchors exactly once, the clone simulation, the plan gates) live in
this script. Brainstorm runs it on its design, planner on
the plan before it returns, reviewer on the plan it critiques; each reads the lines below
instead of re-deriving them.

usage:
  agent-hub check plan TARGET   (runs this script; plan-verify.py TARGET is the same)
  plan-verify.py TARGET [--root DIR] [--analysis FILE] [--ceiling-exception TASK_ID]...
                        [--clone DIR [--after-task CMD]] [--exclude PATTERN]...
                        [--approve "USER WORDS"]

TARGET is a plan folder holding plan.yaml (split or single-file; docs/changes/{id}/, or the legacy docs/plan/{id}/ and
docs/specs/changes/{id}/), or a record {slug}.yaml in docs/brainstorm/ or the legacy analysis folder
carrying change_design (design mode: the checks a task-level design can fail; steps and test
cases are checked only where the design carries them). Files resolve from the workspace root,
the parent of the docs/ folder TARGET sits in, or --root. --analysis names the record holding
binding_scope when it is not the plan's design.yaml or {plan_id}.yaml, or the legacy analysis folder's {plan_id}.yaml or
docs/brainstorm/{plan_id}.yaml.
--ceiling-exception names a task the user allowed over 5 files; cite the decision beside the call.

anchors applies every step not yet done, in wave order, in memory by default: each edit's before must occur exactly once at the moment it is applied, and a step file must stay inside the root unless it is absolute or ~-led, outside the root, and listed in binding_scope.files_allowed ; such a file is read in place and, under --clone, changed in memory only.
--clone copies the workspace to DIR with rsync --delete --delete-excluded, so a reused DIR loses what the source lacks, and is not a sandbox: DIR must be new, empty or hold the marker .plan-verify-clone, and may not be, contain or sit inside the root unless under a folder excluded from the copy
(the config-dir runtime folders are excluded by default when the root is the config dir, --exclude adds patterns). It applies the steps on disk and runs each run step there, with DIR as cwd, the root path rewritten to DIR (a path assembled at run time is not rewritten), then checks the exit code the step's expect names and any "prints: TEXT" that follows the exit code; other prose after the code is counted, not compared.
--after-task CMD runs in DIR after each task with {root} replaced by DIR. A refusal or load failure exits 2 with one line on stdout.

trace reads requirements[] from plan.yaml (change_design.plan in design mode): every requirement is delivered by >=1 task carrying a test
case (or, in a design, a test_plan case), and every task but closeout names >=1 in covers_requirements. ac_trace takes covers_acceptance
only as {task_id}/AC-n of the task's own criteria or as the UC-XXX/AC-N one of them names after '→', with that UC in covers_uc, so every
case reaches a requirement through its task.

placeholders fails a plan.yaml or task value (12 characters or more) that equals a scalar of a TEMPLATE_SOURCES yaml byte for byte, and a mirror
line that repeats a template line holding a {..} or <..> token with a space or a non-ASCII letter in it; a line opening with `<!--` is not compared. It also compares every line of proposal.md, design.md and specs/**/spec.md of the change folder (resolved as spec_delta resolves it) with the lines of the template that file is made from, headings aside, and fails a line left verbatim, naming file:line.

layers runs only on a plan whose plan.yaml (change_design.plan in design mode) carries test_schema: layers: every case has a layer from the six ids and no type, every task has touches (empty only on a closeout or docs-only task), and each touch has a case of its required layer or a layer_waivers entry with a reason and a file:line; a plan without the key skips it.

surfaces reads affected_surfaces from the plan index (change_design.plan in design mode): a surface with no task_ids and no reason prints WARN and still passes, a task id outside the plan fails, the string 'N/A: reason' passes, and a plan without the key skips the check.

approval compares a hash of the plan with the one --approve "USER WORDS" stamped into plan.yaml (approval: {by, at, fingerprint, spec_fingerprint}; at is an ISO 8601 datetime with the local time zone). The hash is sha256 of the canonical JSON of plan.yaml and every task file, without the approval block and without what execution writes back (status, blocker, result, each step's done); a plan edited after the stamp fails 'changed after approval, re-approve', and a plan with no approval block passes.

spec_delta reads the change folder (the plan folder when it lies under docs/changes or docs/specs/changes, else the legacy analysis folder's {plan_id}/ for proposal.md and design.md only; a design record takes docs/changes/{plan_id}/ when that folder exists). Every specs/**/spec.md holds only the sections of the delta template; each requirement heading is '### Requirement: UC-n/AC-n - name' and its id appears once in the change; an ADDED or MODIFIED requirement has SHALL or MUST and at least one '#### Scenario:' with a WHEN and a THEN bullet; REMOVED has Reason and Migration; RENAMED has FROM and TO; a new UC id has a '## Purpose'. proposal.md and design.md carry every '## ' heading of their template, in order. A plan with no change files skips the check.

ac_results reads validation_strategy.ac_check_from (a wave id): every task at or after that wave whose status is reviewing, done or accepted_partial and whose result is not null has exactly one result.ac_check entry per acceptance criterion; met true needs evidence and, for each tc_id, a result.commands[] row of that tc_id, and the last such row exits 0; met false needs a note. A failure names the task and the AC. A plan without the key, or a design record, skips the check.

logic_task_fields reads touches, before_after, logic, approach, alternatives_rejected and user_visible_rules of every task but a closeout task (owner set, agent absent). A task whose touches hold screen, logic, api or state (LOGIC_TOUCHES; refs/plan-files.md § Task sections of the mirror) fails unless before_after, logic, approach{chosen, why, cost} and alternatives_rejected are filled ([{none_because}] counts); a user_visible_rules entry with an empty rule or ac fails on any task; touches or user_visible_rules that is neither absent nor a list fails. A failure names <id>:<key>. A plan runs it only when a task of the plan, or of its analysis record's change_design, carries before_after or user_visible_rules, and reports 'skipped: plan predates the task standard' otherwise; a design record always runs it.

decision_checklist reads change_design.decision_checklist of the analysis record (the TARGET itself in design mode; in plan mode --analysis, else the record plan_paths.record finds: design.yaml or {plan_id}.yaml in the plan folder, else the legacy analysis folder's {plan_id}.yaml, else docs/brainstorm/{plan_id}.yaml). A design record without a list fails; a plan whose record lacks the key reports 'skipped: record predates the decision checklist'. Every one of the seven CHECKLIST_AREAS (copy, screen_states, check_reach, out_of_scope, business_rules, irreversible, dependency) needs at least one entry {id: DC-n, area, item, decision, source}; item and decision are non-empty and source is an id of the record's user_decisions_verbatim or the decision starts 'none:'. A failure names the area or <DC id>:<field>.

screen_states runs only on a plan whose validation_strategy carries state_case_standard: 1 (change_design.plan in design mode). Every task touching screen but closeout carries screen_states {states, themes} with the six BASE_STATES (loading, empty, error, fallback, success, disabled) and a non-empty themes; in plan mode each listed state in each listed theme needs a case whose states and themes name it (a case without themes counts as light) or a state_waivers entry with a reason and a file:line. A failure names the task, state and theme. duplicate_cases, plan mode only and gated the same way, prints WARN, never FAIL, for two cases on the same layer that share at least one AC and at least one state (a case without states is never a duplicate), naming both ids.

close runs only on a plan whose errors.yaml (in the plan folder, else docs/plan/{plan_id}/ for a legacy plan whose plan.yaml sits in docs/specs/changes) carries meta.close_criteria: 1, written by brainstorm error-batch from the close-criteria change on; no errors.yaml, or one without the marker, passes, and a design record skips it. Every entry of every round needs a severity of critical, major or minor; every analysis.deferred_errors[] entry needs a non-empty id, source, location and reason and a severity of critical, major or minor, and every minor entry needs its id in its own round's deferred_errors[]; in the last round whose round_source is review-test, user-final-gate or user-extra-round, a critical or major entry whose id is in no deferred_errors[] of that round is open and fails, a WARN when a task of the plan is accepted_partial; meta.error_loop_count above 3 and more than one user-final-gate round also fail. A failure names the id and the field.

Exit 0 when every check passes, 1 otherwise; the last line is 'N/M checks passed'. Exit 2, with one 'plan-verify: ...' line, for a refused --clone or a TARGET that cannot be loaded.
"""
import argparse, datetime, fnmatch, glob, hashlib, importlib.util, json, os, re, subprocess, sys, tempfile
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python3 -I leaves the script folder off sys.path, and spec_refs sits beside this file
from spec_refs import HEADING, catalog, missing_references
import plan_paths
from _paths import plugin_root, config_dir

HOME = str(plugin_root())   # the plugin folder: templates and scripts resolve from here
TEMPLATE = os.path.join(HOME, 'templates/plan/task-template.yaml')
REQUIRED = ('id', 'title', 'what', 'purpose', 'solution', 'status', 'review_checkpoint',
            'acceptance_criteria', 'verification', 'test_cases')
DESIGN_REQUIRED = ('id', 'title', 'what', 'purpose', 'solution', 'acceptance_criteria')
ACTIONS = ('edit', 'create', 'delete', 'run')
CLAUDE_EXCLUDES = ('/plugins/', '/projects/', '/file-history/', '/cache/', '/worktrees/', '/jobs/',
                   '/backups/', '/.cm-tmp/', '/todos/', '/shell-snapshots/', '/statsig/',
                   '/session-env/', '/sessions/', '/paste-cache/', '/logs/', '/debug/', '/telemetry/',
                   '/ide/', '/tasks/', '/state/', '/history.jsonl', '/daemon*', '/*.zip', '/feedback/')
AC_ID = re.compile(r'\bAC-\d+\b')
UC_AC = re.compile(r'\bUC-\d+/AC-\d+\b')
# The one list of template files chk_placeholders compares a plan against; a new template is appended here.
TEMPLATE_SOURCES = ['templates/plan/task-template.yaml', 'templates/plan/plan-template.yaml',
                    'templates/plan/plan-lite-template.yaml', 'templates/plan/plan.lang-template.md',
                    'templates/plan/plan.lang-lite-template.md',
                    'templates/analysis/proposal-template.md', 'templates/analysis/design-template.md',
                    'templates/spec/spec-delta-template.md']
MIN_LEAF = 12   # a shorter template value (`pending`, `edit`) is a legitimate copy
STRUCTURAL_KEYS = ('id', 'wave', 'file', 'path', 'depends_on', 'kind', 'field')   # an id, a path or a closed vocabulary that repeats in every plan by design, e.g. tasks/W1/W1-T1.yaml, partial_failure
PLACEHOLDER = re.compile(r'[{<][^{}<>]*[^\x21-\x7e][^{}<>]*[}>]')   # a token holding a space or a non-ASCII letter; `{task_id}` and `<wave>` are legitimate paths
# The layer ids and the touch -> required layer map of refs/roles/planner/test-cases.md § Layers and § Layers by what the task touches; edit them together; check-ruleset touch_layer_agrees compares them.
LAYERS = ('unit', 'integration', 'contract', 'e2e', 'security', 'local_validation')
TOUCH_LAYER = {'logic': 'unit', 'api': 'integration', 'shape': 'contract', 'screen': 'e2e', 'input': 'security', 'state': 'local_validation'}
# A logic task is one whose touches hold one of these; its home is refs/plan-files.md § Task sections of the mirror. chk_logic_task_fields reads it.
LOGIC_TOUCHES = ('screen', 'logic', 'api', 'state')


def load_yaml(p):
    with open(p, encoding='utf-8') as f:
        return yaml.safe_load(f)


def workspace_root(path):
    try:
        return plan_paths.workspace_root(path)
    except ValueError as e:
        die(str(e))


def load(target, analysis, root_arg=None):
    """-> mode, plan_id, plan_dir, tasks (each with wave and depends_on), wave order, binding_scope, requirements, the plan-level dict, the analysis record's change_design tasks"""
    if os.path.isdir(target):
        idx = load_yaml(os.path.join(target, 'plan.yaml'))
        entries = idx.get('tasks') or []
        tasks = []
        for e, t in zip(entries, plan_paths.tasks_of(target, {'tasks': entries}, load_yaml)):   # inline tasks first, tasks/ files second
            t['wave'], t['depends_on'] = e.get('wave'), e.get('depends_on') or []
            tasks.append(t)
        mode, plan_id, plan_dir, waves = 'plan', idx.get('plan_id'), target, idx.get('waves')
        root = root_arg or workspace_root(target)
        rec = analysis or plan_paths.record(target, root, plan_id)   # {plan_dir}/design.yaml or {id}.yaml, else docs/analysis, docs/brainstorm
        recd = (load_yaml(rec) or {}) if rec else {}
        scope = recd.get('binding_scope') if rec else None
        rcd = recd.get('change_design')
        rcp = rcd.get('plan') if isinstance(rcd, dict) else None
        rtasks = rcp['tasks'] if isinstance(rcp, dict) and isinstance(rcp.get('tasks'), list) else []
        reqs = idx.get('requirements')
        doc = idx
    else:
        d = load_yaml(target)
        if not isinstance(d, dict) or 'change_design' not in d:
            raise ValueError(f"{target} has no change_design; TARGET must be a plan folder (e.g. {os.path.dirname(target) or '.'}) or a record {{slug}}.yaml (docs/brainstorm/, or the legacy analysis folder) carrying change_design")
        cd = d['change_design']
        edits = cd.get('edits') or {}
        tasks = []
        for t in cd['plan']['tasks']:
            t = dict(t)
            t.setdefault('depends_on', [])
            if 'steps' not in t and t['id'] in edits:
                t['steps'] = [dict(s, done=False) for s in edits[t['id']]]
            tasks.append(t)
        mode, plan_id, waves = 'design', d.get('plan_id'), cd['plan'].get('waves')
        root = root_arg or workspace_root(target)
        candidates = (os.path.join(root, 'docs/specs/changes', plan_id or ''), os.path.join(root, 'docs/plan', plan_id or ''))
        made = plan_paths.change_dir(root, plan_id) if plan_id else None   # docs/changes/{id}, archive included, plan.yaml or not
        plan_dir = (os.path.join(root, os.path.relpath(os.path.realpath(made), os.path.realpath(root))) if made   # symlink-safe
                    else next((p for p in candidates if os.path.isdir(p)), candidates[-1]))
        scope = d.get('binding_scope')
        reqs = cd['plan'].get('requirements')
        doc = cd['plan']
        rtasks = []
    order = [w['id'] for w in waves] if waves else []
    order += [t['wave'] for t in tasks if t.get('wave') and t['wave'] not in order]
    return mode, plan_id, plan_dir, root, tasks, order, scope, reqs, doc, rtasks


def is_closeout(t):
    return 'owner' in t and 'agent' not in t


def chk_task_keys(ctx):
    bad, keys = [], set(load_yaml(TEMPLATE)) | {'wave', 'depends_on', 'owner'}   # owner: the closeout task, the template's CLOSEOUT note
    for t in ctx['tasks']:
        need = REQUIRED if ctx['mode'] == 'plan' else DESIGN_REQUIRED
        empty = [k for k in need if t.get(k) in (None, '', [], {})
                 and not (k == 'test_cases' and is_closeout(t) and t.get(k) == [])]
        if empty:
            bad.append(f"{t.get('id')}: empty {empty}")
        if ctx['mode'] == 'plan':
            extra = sorted(set(t) - keys)
            if extra:
                bad.append(f"{t.get('id')}: keys outside the template {extra}")
    ids = [str(t.get('id')) for t in ctx['tasks']]
    bad += [f"{i}: listed twice" for i in sorted({i for i in ids if ids.count(i) > 1})]
    return not bad, f"{len(ctx['tasks'])} tasks, off={bad}"


def chk_files_ceiling(ctx):
    bad = []
    for t in ctx['tasks']:
        fs = t.get('files') or []
        shape = [i for i, f in enumerate(fs) if not isinstance(f, dict) or set(f) != {'path', 'change', 'why'}
                 or f.get('change') not in ('create', 'edit', 'delete')]
        if shape:
            bad.append(f"{t['id']}: files{shape} not {{path, change, why}} with change create|edit|delete")
        if len(fs) > 5 and t['id'] not in ctx['exceptions']:
            bad.append(f"{t['id']}: {len(fs)} files > 5")
    return not bad, f"exceptions={sorted(ctx['exceptions'])}, off={bad}"


def chk_review_checkpoint(ctx):
    bad = []
    for t in ctx['tasks']:
        rc = t.get('review_checkpoint')
        if rc is None and ctx['mode'] == 'design':
            continue
        rc = rc if isinstance(rc, dict) else {}
        focus, est = rc.get('focus') or [], rc.get('estimate_min')
        if not focus or len(focus) > 4:
            bad.append(f"{t['id']}: focus has {len(focus)} items, want 1-4")
        if not isinstance(est, int) or est > 5:
            bad.append(f"{t['id']}: estimate_min {est!r}, want ≤5")
    return not bad, f"off={bad}"


def chk_ac_trace(ctx):
    bad = missing_references(ctx['tasks'], ctx['root'], ctx['plan_dir'])
    for t in ctx['tasks']:
        acs = t.get('acceptance_criteria') or []
        own, links = set(), {}
        for a in acs:
            m = re.match(r'AC-\d+(?=:)', str(a))
            if not m:
                continue
            own.add(m.group(0))
            links[f"{t['id']}/{m.group(0)}"] = m.group(0)
            for u in UC_AC.findall(str(a).partition('→')[2]):
                links[u] = m.group(0)
        if len(own) != len(acs):
            bad.append(f"{t['id']}: {len(acs) - len(own)} criteria not starting 'AC-n:' or repeating an id")
        cases = t.get('test_cases')
        if not cases:
            if ctx['mode'] == 'plan' and not is_closeout(t):
                bad.append(f"{t['id']}: no test_cases")
            continue
        ucs, covered = set(t.get('covers_uc') or []), set()
        for c in cases:
            if not isinstance(c, dict):
                continue
            v = c.get('covers_acceptance')
            for x in (v if isinstance(v, list) else [v]):
                x = str(x).strip()
                if x not in links:
                    bad.append(f"{t['id']} {c.get('id')}: covers_acceptance {x!r} is neither {t['id']}/AC-n of its criteria "
                               "nor a UC-XXX/AC-N one of them names after →")
                elif x.startswith('UC-') and x.split('/')[0] not in ucs:
                    bad.append(f"{t['id']} {c.get('id')}: {x} names a UC outside covers_uc")
                else:
                    covered.add(links[x])
        if own - covered:
            bad.append(f"{t['id']}: {sorted(own - covered)} covered by no case")
    return not bad, f"off={bad}"


def chk_trace(ctx):
    reqs, bad, ids = ctx['requirements'], [], []
    if not isinstance(reqs, list) or not reqs:
        return False, "off=['no requirements[] at the plan\'s top level']"
    for r in reqs:
        if not (isinstance(r, dict) and re.fullmatch(r'R-\d+', str(r.get('id')))
                and str(r.get('text') or '').strip() and str(r.get('source') or '').strip()):
            bad.append(f"requirement {str(r)[:60]}: not {{id: R-n, text, source}}")
            continue
        ids.append(r['id'])
    bad += [f"{i}: listed twice" for i in sorted({i for i in ids if ids.count(i) > 1})]
    by = {i: [] for i in ids}
    for t in ctx['tasks']:
        if is_closeout(t):
            continue
        cr = t.get('covers_requirements') or []
        if not isinstance(cr, list):
            bad.append(f"{t['id']}: covers_requirements is not a list")
            continue
        if not cr:
            bad.append(f"{t['id']}: covers no requirement")
        for i in cr:
            if i in by:
                by[i].append(t)
            else:
                bad.append(f"{t['id']}: covers_requirements names {i}, not in requirements[]")
    for i, ts in by.items():
        if not ts:
            bad.append(f"{i}: delivered by no task")
        elif not any(t.get('test_cases') or (t.get('test_plan') or {}).get('cases') for t in ts):
            bad.append(f"{i}: no task of {[t['id'] for t in ts]} carries a test case")
    return not bad, f"{len(ids)} requirements, off={bad}"


def external_step_path(f, ctx):
    """-> the real path of step file f when it is absolute or ~-led, not the root or inside it by file identity (samefile on each existing ancestor of the realpath), no .. component, whose realpath equals the realpath of a files_allowed entry, else None"""
    def ok(p):
        return isinstance(p, str) and (os.path.isabs(p) or p.startswith('~')) and '..' not in p.split('/')
    allowed = ((ctx.get('scope') or {}).get('files_allowed')) or []
    if not ok(f):
        return None
    real = os.path.realpath(os.path.expanduser(f))
    try:
        p = real
        while True:
            if os.path.exists(p) and os.path.samefile(p, ctx['root']):
                return None
            if os.path.dirname(p) == p:
                break
            p = os.path.dirname(p)
    except OSError:
        return None
    listed = {os.path.realpath(os.path.expanduser(q)) for q in allowed if ok(q) and not q.endswith('/')}
    return real if real in listed else None


def chk_steps_shape(ctx):
    bad, keys, n = [], set(load_yaml(TEMPLATE)['steps'][0]), 0
    for t in ctx['tasks']:
        st = t.get('steps')
        if not st:
            if ctx['mode'] == 'plan':
                bad.append(f"{t['id']}: no steps[]")
            continue
        n += len(st)
        for i, s in enumerate(st, 1):
            if not isinstance(s, dict) or set(s) != keys or s.get('action') not in ACTIONS:
                bad.append(f"{t['id']} step {i}: keys or action differ from the template")
                continue
            if s['n'] != i:
                bad.append(f"{t['id']} step {i}: n={s['n']}")
            f = s.get('file')
            if isinstance(f, str) and (os.path.isabs(f) or f.startswith('~') or '..' in f.split('/')) and external_step_path(f, ctx) is None:
                bad.append(f"{t['id']} step {i}: file {f!r} is absolute, starts with ~ or has a .. component, and not listed in binding_scope.files_allowed")
            if s['action'] == 'run' and not (isinstance(s['expect'], str) and re.match(r'(?:exit |rc=)\d+', s['expect'].strip())):
                bad.append(f"{t['id']} step {i}: expect names no exit code")
            if s['action'] == 'edit' and not (isinstance(s['before'], str) and s['before']):
                bad.append(f"{t['id']} step {i}: edit with an empty before")
    return not bad, f"{n} steps, off={bad}"


def reaches(tasks):
    by = {t['id']: t for t in tasks}

    def deps(i, seen=None):
        seen = set() if seen is None else seen
        for d in by[i].get('depends_on') or []:
            for x in ([k for k in by if k != i] if d == 'ALL' else [d]):
                if x in by and x not in seen:
                    seen.add(x)
                    deps(x, seen)
        return seen
    return {i: deps(i) for i in by}


def chk_dag(ctx):
    bad, tasks, order = [], ctx['tasks'], ctx['order']
    ids = {t['id'] for t in tasks}
    for t in tasks:
        miss = [d for d in t.get('depends_on') or [] if d != 'ALL' and d not in ids]
        if miss:
            bad.append(f"{t['id']}: depends on unknown {miss}")
    if bad:
        return False, f"off={bad}"
    r = reaches(tasks)
    bad += [f"{i}: in a depends_on cycle" for i in r if i in r[i] and not any(
        d == 'ALL' for d in next(t for t in tasks if t['id'] == i).get('depends_on') or [])]
    pos = {w: k for k, w in enumerate(order)}
    waved = bool(order) and all(t.get('wave') in pos for t in tasks)
    if waved:
        for t in tasks:
            for d in t.get('depends_on') or []:
                if d != 'ALL' and pos[next(x for x in tasks if x['id'] == d)['wave']] >= pos[t['wave']]:
                    bad.append(f"{t['id']} ({t['wave']}) depends on {d} in the same or a later wave")
    paths = {t['id']: {f['path'] for f in t.get('files') or [] if isinstance(f, dict)} for t in tasks}
    for a in range(len(tasks)):
        for b in range(a + 1, len(tasks)):
            x, y = tasks[a]['id'], tasks[b]['id']
            both = paths[x] & paths[y]
            if not both:
                continue
            if waved and tasks[a]['wave'] == tasks[b]['wave']:
                bad.append(f"{x} and {y} share {sorted(both)} in wave {tasks[a]['wave']}")
            elif x not in r[y] and y not in r[x]:
                bad.append(f"{x} and {y} share {sorted(both)} with no depends_on path between them")
    return not bad, f"waves={len(order) if waved else 'none'}, off={bad}"


def chk_scope(ctx):
    s = ctx['scope']
    if not s:
        return True, 'skipped: no binding_scope found'
    allow, forbid = s.get('files_allowed') or [], s.get('files_forbidden') or []

    def hit(p, pats):
        return any(p == q or (q.endswith('/') and p.startswith(q)) for q in pats)
    bad = []
    for t in ctx['tasks']:
        for f in t.get('files') or []:
            p = f.get('path') if isinstance(f, dict) else None
            if p and not hit(p, allow):
                bad.append(f"{t['id']}: {p} outside files_allowed")
            if p and hit(p, forbid):
                bad.append(f"{t['id']}: {p} in files_forbidden")
    return not bad, f"{len(allow)} allowed, off={bad}"


def ordered(ctx):
    pos = {w: k for k, w in enumerate(ctx['order'])}
    return sorted(ctx['tasks'], key=lambda t: pos.get(t.get('wave'), len(pos)))


CLONE_MARKER = '.plan-verify-clone'


def die(msg):
    print(f'plan-verify: {msg}')
    sys.exit(2)


def rel_under(path, top):
    """the part of path below its first existing ancestor that is top (os.path.samefile), '' when path is top, None otherwise"""
    if not os.path.exists(top):
        return None
    tail, p = [], os.path.abspath(path)
    while True:
        if os.path.exists(p) and os.path.samefile(p, top):
            return os.sep.join(reversed(tail))
        up = os.path.dirname(p)
        if up == p:
            return None
        tail.append(os.path.basename(p))
        p = up


def clone_refusal(clone, root, exc):
    if rel_under(clone, os.sep) == '' or rel_under(clone, os.path.expanduser('~')) == '':
        return f'{clone} is the filesystem root or the home folder'
    inside = rel_under(clone, root)
    if inside == '' or rel_under(root, clone) is not None:
        return f'{clone} is, or contains, the root {root}'
    if inside:
        first = inside.split(os.sep)[0]
        if not any(fnmatch.fnmatch(first, e.strip('/')) for e in exc):
            return f'{clone} sits inside the root and {first}/ is not excluded from the copy'
    if os.path.lexists(clone) and not os.path.isdir(clone):
        return f'{clone} exists and is not a directory'
    if os.path.isdir(clone) and os.listdir(clone) and not os.path.isfile(os.path.join(clone, CLONE_MARKER)):
        return f'{clone} is a non-empty folder without the marker {CLONE_MARKER}'
    return None


def to_clone(cmd, root, clone):
    names = [root.rstrip('/')]
    pat = '(?:' + '|'.join(re.escape(n) for n in names) + r')(?![\w.-])'
    return re.sub(pat, lambda m: clone.rstrip('/'), cmd)


def chk_anchors(ctx):
    root, clone, bad, texts, skipped, applied = ctx['root'], ctx['clone'], [], {}, [], 0
    base = clone or root
    ran = unverified = external = 0
    rel_plan = os.path.relpath(ctx['plan_dir'], root) + '/'
    plan_written = os.path.isdir(ctx['plan_dir'])
    for t in ordered(ctx):
        for s in t.get('steps') or []:
            if not isinstance(s, dict) or s.get('done') is True:
                continue
            f, act = s.get('file') or '', s.get('action')
            ext = external_step_path(f, ctx) if act in ('edit', 'create', 'delete') else None
            path = ext or os.path.join(base, f)
            if act == 'run':
                if not clone:
                    skipped.append(f"{t['id']}#{s['n']}")
                    continue
                p = subprocess.run(to_clone(s['after'], root, clone), shell=True, capture_output=True, text=True,
                                   executable='/bin/bash', cwd=clone)
                ran += 1
                exp = str(s.get('expect') or '').strip()
                m = re.match(r'(?:exit |rc=)(\d+)', exp)
                rest = exp[m.end():].strip(' ,;\n') if m else ''
                if not m:
                    bad.append(f"{t['id']}#{s['n']}: expect names no exit code")
                elif int(m.group(1)) != p.returncode:
                    bad.append(f"{t['id']}#{s['n']}: exit {p.returncode}, expect {exp[:60]!r}")
                elif rest.startswith('prints: '):
                    want = rest[len('prints: '):].splitlines()[0]
                    if want not in p.stdout:
                        bad.append(f"{t['id']}#{s['n']}: stdout lacks {want!r}")
                elif rest:
                    unverified += 1
                continue
            if not ext and not os.path.realpath(path).startswith(os.path.realpath(base).rstrip(os.sep) + os.sep):
                bad.append(f"{t['id']}#{s['n']}: {f} escapes the {'clone' if clone else 'root'}")
                continue
            if f.startswith(rel_plan) and not plan_written:
                skipped.append(f"{t['id']}#{s['n']} (plan file, not written yet)")
                continue
            if path not in texts:
                texts[path] = open(path, encoding='utf-8').read() if os.path.isfile(path) else None
            cur = texts[path]
            if act == 'create':
                if cur is not None:
                    bad.append(f"{t['id']}#{s['n']}: create, but {f} exists")
                texts[path] = s['after']
            elif act == 'delete':
                if cur is None:
                    bad.append(f"{t['id']}#{s['n']}: delete, but {f} does not exist")
                texts[path] = None
            else:
                c = cur.count(s['before']) if cur is not None else 0
                if c != 1:
                    bad.append(f"{t['id']}#{s['n']}: before occurs {c} times in {f}")
                    continue
                texts[path] = cur.replace(s['before'], s['after'], 1)
            applied += 1
            external += 1 if ext else 0
            if clone and not ext:
                if texts[path] is None:
                    os.remove(path)
                else:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, 'w', encoding='utf-8') as fh:
                        fh.write(texts[path])
        if clone and ctx['after_task']:
            p = subprocess.run(to_clone(ctx['after_task'], root, clone).replace('{root}', clone.rstrip('/')), shell=True,
                               capture_output=True, text=True, executable='/bin/bash', cwd=clone)
            last = (p.stdout.strip().splitlines() or [''])[-1]
            print(f"      after {t['id']}: exit {p.returncode} {last}")
            if p.returncode:
                bad.append(f"after {t['id']}: exit {p.returncode} {last}")
    ran_note = (f", {ran} ran, {unverified} output unverified" if clone else '') + (f", {external} external in memory" if external else '')
    return not bad, f"{applied} applied, {len(skipped)} not simulated {skipped[:6]}{ran_note}, off={bad}"


MIRROR_HEAD = re.compile(r'^### (\d+)\. (\S+) \xb7 ', re.M)    # '### n. <task id> · title'
MIRROR_TICK = re.compile(r'^- \[([ x])\] (\d+)\.(\d+) ', re.M)   # '- [ ] n.m' or '- [x] n.m'
LEGACY_SECTIONS = ('\u0110\u1ec1 xu\u1ea5t', 'Thi\u1ebft k\u1ebf')   # scrub-allow: legacy mirror section headings a split plan's mirror carried


def mirror_file(plan_dir):
    """-> the path of the plan's mirror, a plan.<lang>.md of the plan folder (the first in name order; the legacy Vietnamese mirror
    is one of them), None when the folder has none; a plan in the reply language has no mirror"""
    found = sorted(glob.glob(os.path.join(glob.escape(plan_dir), 'plan.*.md')))
    return found[0] if found else None


def mirror_shape(label, tasks, mirror, split, keys):
    """-> the list of offences of one plan's mirror text against its tasks: per task a non-empty steps[] whose keys equal the template's
    step keys and whose action is one of ACTIONS, every run step's expect opening 'exit N' or 'rc=N', exactly one '### n. <id> · ' heading,
    the '- [ ] n.m' lines under number n equal to the step numbers and '[x]' only on a done step; a heading naming no task, or a repeated
    task id or number, is an offence; a split plan's mirror also carries the two legacy section headings"""
    bad, num, ticks = [], {}, {}
    for n, tid in MIRROR_HEAD.findall(mirror):
        if tid in num or n in num.values():
            bad.append(f"{label}: heading {n}. {tid} repeats a task id or a number")
        num[tid] = n
    for x, n, m in MIRROR_TICK.findall(mirror):
        ticks.setdefault(n, []).append((m, x))
    if split:
        bad += [f"{label}: mirror has no '## {h}'" for h in LEGACY_SECTIONS if not re.search(rf'^## {h}$', mirror, re.M)]
    ids = set()
    for t in tasks:
        tid = t.get('id') if isinstance(t, dict) else None
        ids.add(tid)
        st = t.get('steps') if isinstance(t, dict) else None
        if not isinstance(st, list) or not st:
            bad.append(f"{label}: {tid} has no steps[]")
            continue
        wrong = [i for i, s in enumerate(st) if not isinstance(s, dict) or (keys and set(s) != keys) or s.get('action') not in ACTIONS]
        if wrong:
            bad.append(f"{label}: {tid} steps{wrong} differ from the template keys or action")
        noexp = [s.get('n') for s in st if isinstance(s, dict) and s.get('action') == 'run'
                 and not (isinstance(s.get('expect'), str) and re.match(r'(exit |rc=)\d+', s['expect'].strip()))]
        if noexp:
            bad.append(f"{label}: {tid} run steps n={noexp}: expect names no exit code")
        if tid not in num:
            bad.append(f"{label}: mirror has no '### n. {tid} \xb7 ' heading")
            continue
        done = {str(s.get('n')): s.get('done') for s in st if isinstance(s, dict)}
        got = ticks.get(num[tid], [])
        if sorted(m for m, _ in got) != sorted(done):
            bad.append(f"{label}: {tid} steps n={sorted(done)} but mirror lines {num[tid]}.m m={sorted(m for m, _ in got)}")
        bad += [f"{label}: {num[tid]}.{m} is ticked but step {m} of {tid} is not done" for m, x in got if x == 'x' and done.get(m) is not True]
    bad += [f"{label}: heading {tid} names no task" for tid in sorted(set(num) - ids)]
    return bad


def chk_mirror(ctx):
    """the plan's own mirror against its own tasks, in process: no ruleset run and no other plan or template is read. No mirror file
    passes (a plan in the reply language has none); design mode and PLAN_VERIFY_SKIP_MIRROR=1 skip."""
    if ctx['mode'] != 'plan' or os.environ.get('PLAN_VERIFY_SKIP_MIRROR') == '1':
        return True, 'skipped: design mode has no mirror' if ctx['mode'] != 'plan' else 'skipped: PLAN_VERIFY_SKIP_MIRROR=1 (gate-test fixtures only)'
    mirror = mirror_file(ctx['plan_dir'])
    if mirror is None:
        return True, 'skipped: no mirror (English reply language), no ruleset run, off=[]'
    label = os.path.basename(ctx['plan_dir'].rstrip('/'))
    try:
        keys = set(load_yaml(TEMPLATE)['steps'][0])
        with open(mirror, encoding='utf-8') as f:
            text = f.read()
    except (OSError, UnicodeDecodeError, yaml.YAMLError, TypeError, KeyError, IndexError) as e:
        return False, f"{label}: unreadable ({type(e).__name__}), off=[]"
    split = os.path.isdir(os.path.join(ctx['plan_dir'], 'tasks'))
    off = mirror_shape(label, ctx.get('tasks') or [], text, split, keys)
    return not off, f"no ruleset run; {os.path.basename(mirror)} against {len(ctx.get('tasks') or [])} tasks, off={off}"


def template_leaves(node, path=''):
    """-> (key path, string) for every string leaf of a parsed template or plan; STRUCTURAL_KEYS are skipped"""
    if isinstance(node, dict):
        return [x for k, v in node.items() if k not in STRUCTURAL_KEYS
                for x in template_leaves(v, f'{path}.{k}' if path else str(k))]
    if isinstance(node, list):
        return [x for i, v in enumerate(node) for x in template_leaves(v, f'{path}[{i}]')]
    return [(path, node)] if isinstance(node, str) else []


def change_files(ctx):
    """-> folder, spec paths, names of the proposal.md and design.md present: the change folder as chk_spec_delta and chk_placeholders both read it"""
    root = ctx['root']
    changes = os.path.relpath(ctx['plan_dir'], root).startswith(('docs/changes/', 'docs/specs/changes/'))
    folder = ctx['plan_dir'] if changes else os.path.join(root, 'docs/analysis', str(ctx['plan_id']))
    specs = sorted(glob.glob(os.path.join(folder, 'specs/**/spec.md'), recursive=True)) if changes else []
    docs = [n for n in ('proposal.md', 'design.md') if os.path.isfile(os.path.join(folder, n))]
    return folder, specs, docs


def sidecar(ctx, name):
    """-> the path of a file the plan keeps beside it (errors.yaml, change-map.json): in the plan folder, else, for a legacy plan whose
    plan.yaml sits in docs/specs/changes, in the old docs/plan/{plan_id}/ that plan_paths.sidecar_dir names; the first one that
    exists, else the plan folder's own path. No lookup here builds a docs/plan/{plan_id}/ path itself."""
    folders = [ctx['plan_dir']]
    try:
        folders.append(str(plan_paths.sidecar_dir(ctx['root'], str(ctx['plan_id']))))
    except ValueError:
        pass   # a plan folder not named by its plan_id (or an ambiguous id) has no legacy sidecar to find
    for folder in folders:
        p = os.path.join(folder, name)
        if os.path.isfile(p):
            return p
    return os.path.join(ctx['plan_dir'], name)


def change_template_lines(rel):
    """the lines of a change-file template that a finished file must not repeat: not a heading, and holding a {..} or <..> token or a comment"""
    with open(os.path.join(HOME, rel), encoding='utf-8') as f:
        return {l.strip() for l in f.read().splitlines() if l.strip() and not l.lstrip().startswith('#') and PLACEHOLDER.search(l)}


def chk_placeholders(ctx):
    values, lines, bad = {}, {}, []
    for rel in TEMPLATE_SOURCES:
        with open(os.path.join(HOME, rel), encoding='utf-8') as f:
            text = f.read()
        if rel.endswith('.md'):
            for l in text.splitlines():
                if not l.lstrip().startswith('<!--') and PLACEHOLDER.search(l):
                    lines.setdefault(l.rstrip(), rel)
        else:
            for p, v in template_leaves(yaml.safe_load(text)):
                if len(v) >= MIN_LEAF:
                    values.setdefault(v, f'{rel}:{p}')
    plan_level = {k: v for k, v in (ctx['doc'] or {}).items() if k != 'tasks'}
    for label, node in [('plan.yaml', plan_level)] + [(t.get('id'), t) for t in ctx['tasks']]:
        for p, v in template_leaves(node):
            if v in values:
                bad.append(f"{label} {p}: {v[:50]!r} is the example value at {values[v]}")
    mirror = mirror_file(ctx['plan_dir']) if ctx['mode'] == 'plan' else None
    if mirror:
        with open(mirror, encoding='utf-8') as f:
            for n, l in enumerate(f.read().splitlines(), 1):
                if l.rstrip() in lines:
                    bad.append(f"{os.path.basename(mirror)}:{n}: line copied from {lines[l.rstrip()]}")
    if ctx['mode'] == 'plan':
        folder, specs, docs = change_files(ctx)
        made = [(os.path.join(folder, n), 'templates/analysis/' + n.replace('.md', '-template.md')) for n in docs]
        for path, tpl in made + [(p, DELTA_TEMPLATE) for p in specs]:
            want = change_template_lines(tpl)
            with open(path, encoding='utf-8') as f:
                for n, l in enumerate(f.read().splitlines(), 1):
                    if l.strip() in want:
                        bad.append(f"{os.path.relpath(path, ctx['root'])}:{n}: line copied from {tpl}")
    return not bad, f"{len(values)} template values, {len(lines)} template lines, off={bad}"


def layers_exempt(t):
    """closeout, or a docs-only task: the exemptions of test-cases.md § Exemptions that a task file can show"""
    paths = [f.get('path') or '' for f in t.get('files') or [] if isinstance(f, dict)]
    return is_closeout(t) or bool(paths) and all(p.endswith('.md') or p.startswith('docs/') for p in paths)


def chk_layers(ctx):
    if (ctx['doc'] or {}).get('test_schema') != 'layers':
        return True, 'skipped: the plan carries no test_schema: layers'
    bad = []
    for t in ctx['tasks']:
        tid, touches = t.get('id'), t.get('touches')
        if not touches and not layers_exempt(t):
            bad.append(f"{tid}: touches is {'absent' if touches is None else 'empty'} and no exemption covers the task")
        bad += [f"{tid}: touches {x!r} is not one of {sorted(TOUCH_LAYER)}" for x in touches or [] if x not in TOUCH_LAYER]
        if ctx['mode'] != 'plan':
            continue
        have, waived = set(), set()
        for c in t.get('test_cases') or []:
            if not isinstance(c, dict):
                continue
            if 'type' in c:
                bad.append(f"{tid} {c.get('id')}: carries type, want layer")
            if c.get('layer') in LAYERS:
                have.add(c['layer'])
            else:
                bad.append(f"{tid} {c.get('id')}: layer {c.get('layer')!r} is not one of {list(LAYERS)}")
        for w in t.get('layer_waivers') or []:
            if isinstance(w, dict) and str(w.get('reason') or '').strip() and re.search(r'\S+:\d+', str(w.get('evidence') or '')):
                waived.add(w.get('layer'))
            else:
                bad.append(f"{tid}: layer_waivers entry {str(w)[:50]!r} lacks a reason or a file:line evidence")
        bad += [f"{tid}: touches {x} needs a {TOUCH_LAYER[x]} case or a layer_waivers entry" for x in touches or []
                if x in TOUCH_LAYER and TOUCH_LAYER[x] not in have | waived]
    return not bad, f"{len(ctx['tasks'])} tasks, off={bad}"


def chk_surfaces(ctx):
    sf = (ctx['doc'] or {}).get('affected_surfaces')
    if sf is None:
        return True, 'skipped: the plan carries no affected_surfaces'
    if isinstance(sf, str):
        return sf.startswith('N/A:'), f"{sf[:60]!r}"
    if not isinstance(sf, list):
        return False, "off=['affected_surfaces is neither a list nor an N/A: reason string']"
    ids, bad, warn = {t.get('id') for t in ctx['tasks']}, [], []
    for s in sf:
        if not isinstance(s, dict):
            bad.append(f"surface {str(s)[:40]!r}: not a mapping")
            continue
        tids = s.get('task_ids') or []
        bad += [f"{s.get('id')}: task_ids names {i}, not in the plan" for i in tids if i not in ids]
        if not tids and not s.get('reason'):
            warn.append(f"{s.get('id')}: no task and no reason")
    return not bad, f"{len(sf)} surfaces, {f'WARN={warn}, ' if warn else ''}off={bad}"


EXEC_KEYS = ('status', 'blocker', 'result')   # what an executing agent writes into a task record: refs/roles/implement/close-task.md § Write the result into the plan, with each step's done


def strip_exec(t):
    """a task record without what execution writes back, so running the plan does not change its fingerprint"""
    t = {k: v for k, v in t.items() if k not in EXEC_KEYS}
    if isinstance(t.get('steps'), list):
        t['steps'] = [{k: v for k, v in s.items() if k != 'done'} if isinstance(s, dict) else s for s in t['steps']]
    if isinstance(t.get('subtasks'), list):
        t['subtasks'] = [strip_exec(s) if isinstance(s, dict) else s for s in t['subtasks']]
    return t


def plan_fingerprint(plan_dir):
    """sha256 of the canonical JSON (sorted keys) of plan.yaml and every task file, minus the approval block and the execution-owned keys"""
    idx = load_yaml(os.path.join(plan_dir, 'plan.yaml'))
    entries = idx.get('tasks') or []
    split = os.path.isdir(os.path.join(plan_dir, 'tasks'))
    body = {'plan': {k: v for k, v in idx.items() if k not in ('approval', 'tasks')},
            'index': [strip_exec(dict(e)) for e in entries],
            'files': [strip_exec(load_yaml(os.path.join(plan_dir, e['file']))) for e in entries] if split else []}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, default=str).encode('utf-8')).hexdigest()


def spec_fingerprint(plan_dir, root=None):
    """-> (sha256 of the canonical JSON list of [path, sha256 of the bytes] pairs over the files the plan's covers_uc ids resolve to through spec_refs.catalog, those paths); (None, []) when no task names a UC"""
    root = root or workspace_root(plan_dir)
    idx = load_yaml(os.path.join(plan_dir, 'plan.yaml'))
    split = os.path.isdir(os.path.join(plan_dir, 'tasks'))
    ucs = set()
    for e in idx.get('tasks') or []:
        ucs.update((load_yaml(os.path.join(plan_dir, e['file'])) if split else e).get('covers_uc') or [])
    if not ucs:
        return None, []
    paths = sorted({os.path.relpath(p, root) for ref, ps in catalog(root, plan_dir).items() if ref.split('/')[0] in ucs for p in ps})
    def digest(p):
        with open(os.path.join(root, p), 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    pairs = [[p, digest(p)] for p in paths if os.path.isfile(os.path.join(root, p))]
    return hashlib.sha256(json.dumps(pairs).encode('utf-8')).hexdigest(), [p for p, _ in pairs]


def stamp_approval(plan_dir, words):
    """write the approval block at the end of plan.yaml, replacing a prior one; nothing else in the file changes.
    The new text goes to a temp file in the same folder and replaces plan.yaml through os.replace, so a failed stamp leaves the old file whole and no temp file behind."""
    p = os.path.join(plan_dir, 'plan.yaml')
    with open(p, encoding='utf-8') as f:
        text = re.sub(r'^approval:.*(?:\n[ \t]+.*)*\n?', '', f.read(), flags=re.M)
    at = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    block = (f"approval:\n  by: {json.dumps(words, ensure_ascii=False)}\n  at: {json.dumps(at)}\n"
             f"  fingerprint: {json.dumps(plan_fingerprint(plan_dir))}\n  spec_fingerprint: {json.dumps(spec_fingerprint(plan_dir)[0])}\n")
    fd, tmp = tempfile.mkstemp(dir=plan_dir, prefix='.plan.yaml.')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(text.rstrip('\n') + '\n' + block)
        os.chmod(tmp, os.stat(p).st_mode & 0o777)
        os.replace(tmp, p)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def chk_approval(ctx):
    if ctx['mode'] != 'plan':
        return True, 'skipped: design mode has no approval'
    ap = load_yaml(os.path.join(ctx['plan_dir'], 'plan.yaml')).get('approval')
    if not ap:
        return True, 'no approval block: not yet approved'
    if not isinstance(ap, dict) or not ap.get('fingerprint'):
        return False, "off=['approval block has no fingerprint']"
    if plan_fingerprint(ctx['plan_dir']) != ap['fingerprint']:
        return False, "off=['changed after approval, re-approve']"
    fp = f"approved, fingerprint {str(ap['fingerprint'])[:12]}"
    stamped = ap.get('spec_fingerprint')
    if not isinstance(stamped, str):
        return True, f"{fp}, spec part not stamped, off=[]"
    idx = load_yaml(os.path.join(ctx['plan_dir'], 'plan.yaml'))
    split = os.path.isdir(os.path.join(ctx['plan_dir'], 'tasks'))
    tasks = [load_yaml(os.path.join(ctx['plan_dir'], e['file'])) if split else e for e in idx.get('tasks') or []]
    if not any(t.get('status') in ('pending', 'implementing', 're_implement') for t in tasks):
        return True, f"{fp}, spec part not checked: the last wave ran, off=[]"
    now, paths = spec_fingerprint(ctx['plan_dir'], ctx['root'])
    if now != stamped:
        where = ', '.join(paths) or 'the covers_uc files'
        return False, f"off=['spec changed after approval (covered: {where}), re-approve']"
    return True, f"{fp}, spec part unchanged, off=[]"


REQ_NAME = re.compile(HEADING.pattern + r' - \S')   # '### Requirement: UC-n/AC-n - name', the id form of spec_refs.HEADING plus its name
DELTA_TEMPLATE = 'templates/spec/spec-delta-template.md'


def template_headings(rel):
    """the `## ` headings of a template, in order: the one home of each heading list chk_spec_delta checks"""
    with open(os.path.join(HOME, rel), encoding='utf-8') as f:
        return re.findall(r'^## (.+?)\s*$', f.read(), re.M)


def spec_problems(name, text, live_ucs, seen):
    """-> the problems of one specs/**/spec.md; seen maps each requirement id of the change to its file"""
    bad, sect, req, blocks, body, present = [], None, None, [], {}, []
    sections = template_headings(DELTA_TEMPLATE)
    for line in text.splitlines():
        if line.startswith('## '):
            sect, req = line[3:].strip(), None
            present.append(sect)
            body[sect] = []
            if sect not in sections:
                bad.append(f"{name}: '## {sect}' is not a section of the delta template")
        elif sect is not None:
            body[sect].append(line)
            if line.startswith('### Requirement:'):
                req = (sect, line, [])
                blocks.append(req)
            elif line.startswith('### '):
                req = None
            elif req is not None:
                req[2].append(line)
    for sect, head, lines in blocks:
        m = REQ_NAME.match(head)
        if not m:
            bad.append(f"{name}: requirement heading {head[:60]!r} is not '### Requirement: UC-n/AC-n - name'")
            continue
        rid, block = m.group(1), '\n'.join(lines)
        if rid in seen:
            bad.append(f"{rid}: appears twice in the change ({seen[rid]} and {name})")
        seen[rid] = name
        if sect in ('ADDED Requirements', 'MODIFIED Requirements'):
            if not re.search(r'\b(SHALL|MUST)\b', block):
                bad.append(f"{rid}: no SHALL or MUST")
            scenarios = block.split('#### Scenario:')[1:]
            if not scenarios:
                bad.append(f"{rid}: no '#### Scenario:'")
            if any(not (re.search(r'^\s*-\s+\*\*WHEN\*\*', s, re.M) and re.search(r'^\s*-\s+\*\*THEN\*\*', s, re.M)) for s in scenarios):
                bad.append(f"{rid}: a scenario lacks its WHEN or THEN bullet")
            if sect == 'ADDED Requirements' and rid.split('/')[0] not in live_ucs and 'Purpose' not in present:
                bad.append(f"{rid}: a new UC with no '## Purpose'")
        elif sect == 'REMOVED Requirements':
            bad += [f"{rid}: REMOVED without {k}" for k in ('Reason', 'Migration') if f'**{k}**' not in block]
    renamed = '\n'.join(body.get('RENAMED Requirements', []))
    if 'RENAMED Requirements' in body and not (re.search(r'^\s*-\s+FROM:', renamed, re.M) and re.search(r'^\s*-\s+TO:', renamed, re.M)):
        bad.append(f"{name}: RENAMED without FROM and TO")
    return bad


def chk_spec_delta(ctx):
    root = ctx['root']
    folder, specs, docs = change_files(ctx)
    if not specs and not docs:
        return True, 'skipped: no change files'
    ucs = glob.glob(os.path.join(root, 'docs/specs/use-cases/**/UC-*.md'), recursive=True)
    live = {re.match(r'UC-\d+', os.path.basename(p)).group() for p in ucs
            if '_legacy' not in p.split(os.sep) and re.match(r'UC-\d+', os.path.basename(p))}
    bad, seen = [], {}
    for p in specs:
        with open(p, encoding='utf-8') as f:
            bad += spec_problems(os.path.relpath(p, folder), f.read(), live, seen)
    for n in docs:
        want = template_headings('templates/analysis/' + n.replace('.md', '-template.md'))
        with open(os.path.join(folder, n), encoding='utf-8') as f:
            got = re.findall(r'^## (.+?)\s*$', f.read(), re.M)
        k = 0
        for h in want:
            if h in got[k:]:
                k = got.index(h, k) + 1
            else:
                bad.append(f"{n}: heading '## {h}' is missing or out of order")
    return not bad, f"{len(specs)} specs, {len(docs)} of proposal.md and design.md, off={bad}"


def chk_ac_results(ctx):
    if ctx['mode'] != 'plan':
        return True, 'skipped: design mode has no finished task'
    start = ((ctx['doc'] or {}).get('validation_strategy') or {}).get('ac_check_from')
    if not start:
        return True, 'skipped: plan predates ac_check (no validation_strategy.ac_check_from)'
    order = ctx['order']
    if start not in order:
        return False, f"off=['ac_check_from {start} is not a wave of the plan']"
    bad, n = [], 0
    for t in ctx['tasks']:
        res = t.get('result')
        if (t.get('status') not in ('reviewing', 'done', 'accepted_partial') or not isinstance(res, dict)
                or t.get('wave') not in order or order.index(t['wave']) < order.index(start)):
            continue
        n += 1
        acs = [m.group(0) for m in (re.match(r'AC-\d+(?=:)', str(a)) for a in t.get('acceptance_criteria') or []) if m]
        entries = res.get('ac_check')
        if not isinstance(entries, list):
            bad.append(f"{t['id']}: result has no ac_check list")
            continue
        got = [e.get('ac') if isinstance(e, dict) else None for e in entries]
        bad += [f"{t['id']} {ac}: {got.count(ac)} ac_check entries, want exactly 1" for ac in acs if got.count(ac) != 1]
        bad += [f"{t['id']}: ac_check names {x!r}, not an AC of the task" for x in sorted({str(g) for g in got if g not in acs})]
        cases = {c.get('id') for c in t.get('test_cases') or [] if isinstance(c, dict)}
        exits = {}
        for c in res.get('commands') or []:
            if isinstance(c, dict) and c.get('tc_id'):
                exits.setdefault(c['tc_id'], []).append(c.get('exit'))
        for e in entries:
            if not isinstance(e, dict) or e.get('ac') not in acs:
                continue
            where = f"{t['id']} {e['ac']}"
            if not isinstance(e.get('met'), bool):
                bad.append(f"{where}: met is not true or false")
            elif e['met']:
                if not e.get('evidence'):
                    bad.append(f"{where}: met true with no evidence")
                for tc in e.get('tc_ids') or []:
                    if tc not in cases:
                        bad.append(f"{where}: {tc} is not a case of the task")
                    elif not exits.get(tc) or exits[tc][-1] != 0:
                        bad.append(f"{where}: {tc} has no result.commands[] row, or its last row has a non-zero exit")
            elif not str(e.get('note') or '').strip():
                bad.append(f"{where}: met false with no note")
    return not bad, f"{n} finished tasks from {start}, off={bad}"


def filled(v):
    return isinstance(v, str) and bool(v.strip())


def chk_logic_task_fields(ctx):
    if ctx['mode'] == 'plan':
        pool = [t for t in list(ctx['tasks']) + list(ctx.get('record_tasks') or []) if isinstance(t, dict)]
        if not any(t.get('before_after') is not None or t.get('user_visible_rules') is not None for t in pool):
            return True, 'skipped: plan predates the task standard (no task of the plan or of its analysis record carries before_after or user_visible_rules)'
    miss, rules, logic = [], [], 0
    for t in ctx['tasks']:
        if is_closeout(t):
            continue
        tid = t.get('id')
        touches, uvr = t.get('touches'), t.get('user_visible_rules')
        if touches is not None and not isinstance(touches, list):
            miss.append(f'{tid}:touches')
            touches = []
        if uvr is not None and not isinstance(uvr, list):
            rules.append(f'{tid}:user_visible_rules')
            uvr = []
        if {x for x in touches or [] if isinstance(x, str)} & set(LOGIC_TOUCHES):
            logic += 1
            ba, lg, ap, alt = t.get('before_after'), t.get('logic'), t.get('approach'), t.get('alternatives_rejected')
            if not (isinstance(ba, list) and ba and all(isinstance(x, dict) and all(filled(x.get(k)) for k in ('aspect', 'before', 'after')) for x in ba)):
                miss.append(f'{tid}:before_after')
            if not (isinstance(lg, list) and lg and all(filled(x) for x in lg)):
                miss.append(f'{tid}:logic')
            ap = ap if isinstance(ap, dict) else {}
            miss += [f'{tid}:approach.{k}' for k in ('chosen', 'why', 'cost') if not filled(ap.get(k))]
            if not (isinstance(alt, list) and alt and all(isinstance(x, dict) and (filled(x.get('none_because')) or (filled(x.get('option')) and filled(x.get('why_not')))) for x in alt)):
                miss.append(f'{tid}:alternatives_rejected')
        for i, r in enumerate(uvr or []):
            if not (isinstance(r, dict) and filled(r.get('rule')) and filled(r.get('ac'))):
                rules.append(f'{tid}:user_visible_rules[{i}]')
    return not (miss or rules), f"logic tasks={logic}, missing={miss}, rules without ac={rules}"


CHECKLIST_AREAS = ('copy', 'screen_states', 'check_reach', 'out_of_scope', 'business_rules', 'irreversible', 'dependency')


def chk_decision_checklist(ctx):
    if ctx['mode'] == 'plan':
        rec = ctx.get('analysis') or plan_paths.record(ctx['target'], ctx['root'], ctx['plan_id'])
    else:
        rec = ctx['target']
    recd = (load_yaml(rec) or {}) if rec else {}
    cd = recd.get('change_design') if isinstance(recd.get('change_design'), dict) else {}
    dc = cd.get('decision_checklist')
    if ctx['mode'] == 'plan' and dc is None:
        return True, 'skipped: record predates the decision checklist'
    if not isinstance(dc, list):
        return False, 'change_design.decision_checklist is absent or not a list'
    qids = {str(e.get('id')) for e in recd.get('user_decisions_verbatim') or [] if isinstance(e, dict)}
    bad = []
    for i, e in enumerate(dc):
        e = e if isinstance(e, dict) else {}
        ok_id = re.fullmatch(r'DC-\d+', str(e.get('id') or ''))
        did = e['id'] if ok_id else f'entry[{i}]'
        if not ok_id:
            bad.append(f'{did}:id')
        if e.get('area') not in CHECKLIST_AREAS:
            bad.append(f'{did}:area')
        bad += [f'{did}:{k}' for k in ('item', 'decision') if not filled(e.get(k))]
        if not (str(e.get('source') or '').strip() in qids or str(e.get('decision') or '').strip().startswith('none:')):
            bad.append(f'{did}:source')
    have = {e.get('area') for e in dc if isinstance(e, dict)}
    missing = [a for a in CHECKLIST_AREAS if a not in have]
    return not (bad or missing), f'{len(dc)} entries, missing areas={missing}, off={bad}'


DATA_IMPACT_KEYS = ('purpose', 'flow', 'ui', 'endpoints', 'db_schema', 'data_reads', 'data_writes', 'business_rules', 'access',
                    'events_jobs', 'config', 'code_changes', 'risk_rollback')


def in_memory_change_map(ctx):
    """-> the change-map model of the plan under check, built in process by change-map.py's build_model; nothing is written"""
    spec = importlib.util.spec_from_file_location('change_map_builder', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'change-map.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    meta, tasks = mod.load_plan(ctx['plan_dir'])
    return mod.build_model(meta, tasks, ctx['root'])


def chk_data_impact(ctx):
    """a plan marked validation_strategy.change_record_standard: 1 must give every done task result.run and the 13 declared keys
    (a non-empty list or dict, or a string starting 'none:'); a legacy change-map.json beside the plan is read, else the map is built in memory; a listed mismatch is a WARN, never a FAIL;
    an unreadable map is a WARN naming the error"""
    if ctx['mode'] != 'plan':
        return True, 'skipped: design mode has no finished task'
    if ((ctx['doc'] or {}).get('validation_strategy') or {}).get('change_record_standard') != 1:
        return True, 'skipped: plan predates the change-record standard (no validation_strategy.change_record_standard)'

    def filled(v):
        return isinstance(v, str) and v.startswith('none:') or isinstance(v, (list, dict)) and bool(v)
    bad = []
    for t in ctx['tasks']:
        if t.get('status') != 'done':
            continue
        res = t.get('result') if isinstance(t.get('result'), dict) else {}
        run = res.get('run') if isinstance(res.get('run'), dict) else {}
        di = res.get('data_impact') if isinstance(res.get('data_impact'), dict) else {}
        miss = [f'run.{k}' for k in ('started_at', 'finished_at') if not run.get(k)] + [k for k in DATA_IMPACT_KEYS if not filled(di.get(k))]
        if miss:
            bad.append(f"{t['id']}: missing {miss}")
    if bad:
        return False, f'off={bad}'
    try:
        legacy = sidecar(ctx, 'change-map.json')   # a plan folder or old sidecar json from an earlier run: read, never written
        if os.path.isfile(legacy):
            with open(legacy, encoding='utf-8') as f:
                cm = json.load(f)
        else:
            cm = in_memory_change_map(ctx)
        entries = cm['sections']['mismatch']['entries']
        found = len(entries)
        names = ', '.join(sorted({str(e.get('file') or e.get('path') or e.get('task_id') or e.get('code')) for e in entries if isinstance(e, dict)}))
        lim = [str(c) for c in (cm.get('auto_limits') or [])]
    except (OSError, ValueError, KeyError, TypeError, AttributeError, yaml.YAMLError) as e:
        return 'WARN', f'change-map.json unreadable: {type(e).__name__}: {e}; none blocks'
    if found:
        return 'WARN', f'{found} mismatches in change-map.json ({names}); none blocks'
    note = f"; not checked: {', '.join(lim)}" if lim else ''
    return True, 'every done task carries run and the 13 keys, no mismatch listed' + note


CLOSE_SEVERITIES = ('critical', 'major', 'minor')   # refs/roles/brainstorm/error-batch.md § Procedure step 2
CLOSE_LEDGER_FIELDS = ('id', 'severity', 'source', 'location', 'reason')   # one deferred_errors[] entry, step 5 of the same file
CLOSE_PASS_SOURCES = ('review-test', 'user-final-gate', 'user-extra-round')   # the rounds that record a review-and-test pass


def chk_close(ctx):
    """a plan whose errors.yaml carries meta.close_criteria: 1 must have a severity on every entry, a complete ledger entry, every minor entry in its round's ledger, no open critical/major in its last pass round, error_loop_count <= 3 and at most one user-final-gate round; no errors.yaml or no marker is a PASS, an open entry under an accepted_partial task a WARN"""
    if ctx['mode'] != 'plan':
        return True, 'skipped: design mode has no errors.yaml'
    path = sidecar(ctx, 'errors.yaml')
    if not os.path.isfile(path):
        return True, 'no errors.yaml: nothing recorded'
    doc = load_yaml(path)
    doc = doc if isinstance(doc, dict) else {}
    meta = doc.get('meta') if isinstance(doc.get('meta'), dict) else {}
    if meta.get('close_criteria') != 1:
        return True, 'skipped: errors.yaml predates the close criteria (no meta.close_criteria)'
    rounds = [r for r in as_list(doc.get('errors')) if isinstance(r, dict)]

    def ledger(r):
        an = r.get('analysis') if isinstance(r.get('analysis'), dict) else {}
        return [d if isinstance(d, dict) else {} for d in as_list(an.get('deferred_errors'))]
    bad, deferred = [], 0
    for r in rounds:
        entries = [e for e in as_list(r.get('entries')) if isinstance(e, dict)]
        bad += [f"{e.get('id')}: severity" for e in entries if e.get('severity') not in CLOSE_SEVERITIES]
        held_here = {d.get('id') for d in ledger(r)}
        bad += [f"{e.get('id')}: not in ledger" for e in entries if e.get('severity') == 'minor' and e.get('id') not in held_here]
        for d in ledger(r):
            deferred += 1
            bad += [f"{d.get('id')}: {k}" for k in CLOSE_LEDGER_FIELDS if not d.get(k)]
            if d.get('severity') and d.get('severity') not in CLOSE_SEVERITIES:
                bad.append(f"{d.get('id')}: ledger severity")
    last = next((r for r in reversed(rounds) if r.get('round_source') in CLOSE_PASS_SOURCES), None)
    held = {d.get('id') for d in ledger(last)} if last else set()
    open_ids = [e.get('id') for e in as_list((last or {}).get('entries'))
                if isinstance(e, dict) and e.get('severity') in ('critical', 'major') and e.get('id') not in held]
    n = meta.get('error_loop_count')
    if isinstance(n, int) and n > 3:
        bad.append(f'error_loop_count {n}')
    users = sum(1 for r in rounds if r.get('round_source') == 'user-final-gate')
    if users > 1:
        bad.append(f'user-final-gate rounds {users}')
    partial = any(t.get('status') == 'accepted_partial' for t in ctx['tasks'])
    if open_ids and not partial:
        bad += [f'open {i}' for i in open_ids]
    if bad:
        return False, f'off={bad}'
    if open_ids:
        return 'WARN', f'accepted_partial task: open {open_ids}; none blocks'
    return True, f'{len(rounds)} rounds, {deferred} deferred, 0 open'


BASE_STATES = ('loading', 'empty', 'error', 'fallback', 'success', 'disabled')


def state_standard(ctx):
    return ((ctx['doc'] or {}).get('validation_strategy') or {}).get('state_case_standard') == 1


def as_list(v):
    return v if isinstance(v, list) else []


def chk_screen_states(ctx):
    if not state_standard(ctx):
        return True, 'skipped: plan predates the screen-state standard (no validation_strategy.state_case_standard)'
    bad, n = [], 0
    for t in ctx['tasks']:
        if is_closeout(t) or 'screen' not in as_list(t.get('touches')):
            continue
        n += 1
        tid = t.get('id')
        ss = t.get('screen_states') if isinstance(t.get('screen_states'), dict) else {}
        states = [s for s in as_list(ss.get('states')) if isinstance(s, str)]
        themes = [s for s in as_list(ss.get('themes')) if isinstance(s, str)]
        bad += [f'{tid}: screen_states lacks {s}' for s in BASE_STATES if s not in states]
        if not themes:
            bad.append(f'{tid}: screen_states.themes is empty')
        if ctx['mode'] != 'plan':
            continue
        waived = set()
        for w in as_list(t.get('state_waivers')):
            if isinstance(w, dict) and filled(w.get('reason')) and re.search(r'\S+:\d+', str(w.get('evidence') or '')):
                waived.add(w.get('state'))
            else:
                bad.append(f"{tid}: state_waivers entry {str(w)[:50]!r} lacks a reason or a file:line evidence")
        cases = [c for c in as_list(t.get('test_cases')) if isinstance(c, dict)]
        for s in states:
            for th in themes:
                if s not in waived and not any(s in as_list(c.get('states')) and th in (as_list(c.get('themes')) or ['light']) for c in cases):
                    bad.append(f'{tid}: state {s} has no case in theme {th}')
    return not bad, f'{n} screen tasks, off={bad}'


def chk_duplicate_cases(ctx):
    if ctx['mode'] != 'plan':
        return True, 'skipped: design mode has no test cases'
    if not state_standard(ctx):
        return True, 'skipped: plan predates the screen-state standard (no validation_strategy.state_case_standard)'
    seen, dup = [], []
    for t in ctx['tasks']:
        for c in as_list(t.get('test_cases')):
            if not isinstance(c, dict):
                continue
            ac = c.get('covers_acceptance')
            key = (frozenset([ac] if isinstance(ac, str) else as_list(ac)), c.get('layer'), frozenset(as_list(c.get('states'))))
            dup += [f"{o} and {c.get('id')}" for o, k in seen if k[1] == key[1] and k[0] & key[0] and k[2] & key[2]]   # same layer, a shared AC, a shared state
            seen.append((c.get('id'), key))
    return ('WARN' if dup else True), f'{len(seen)} cases, duplicates={dup}; none blocks'


def chk_legacy_roots(ctx):
    """a workspace that holds docs/changes/MIGRATION-MAP.tsv has been migrated and must not grow a legacy docs root again: FAIL naming each
    root plan_paths.legacy_roots_reappeared lists; a workspace without the map, or with none of those roots, passes"""
    back = plan_paths.legacy_roots_reappeared(ctx['root'])
    if back:
        return False, 'legacy root back in a migrated workspace: ' + ', '.join(back)
    return True, 'no legacy docs root in a migrated workspace (or no docs/changes/MIGRATION-MAP.tsv)'


CHECKS = (chk_task_keys, chk_files_ceiling, chk_review_checkpoint, chk_ac_trace, chk_trace, chk_steps_shape,
          chk_dag, chk_scope, chk_anchors, chk_mirror, chk_placeholders, chk_layers, chk_screen_states, chk_duplicate_cases, chk_surfaces, chk_approval,
          chk_spec_delta, chk_ac_results, chk_logic_task_fields, chk_decision_checklist, chk_data_impact, chk_close, chk_legacy_roots)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('target')
    ap.add_argument('--root')
    ap.add_argument('--analysis')
    ap.add_argument('--ceiling-exception', action='append', default=[])
    ap.add_argument('--clone')
    ap.add_argument('--after-task')
    ap.add_argument('--exclude', action='append', default=[])
    ap.add_argument('--approve', metavar='USER_WORDS')
    a = ap.parse_args()
    missing = [t for t in [TEMPLATE] + [os.path.join(HOME, r) for r in TEMPLATE_SOURCES] if not os.path.isfile(t)]
    if missing:
        die(f'template file missing: {missing[0]}')
    try:
        mode, plan_id, plan_dir, root, tasks, order, scope, reqs, doc, rtasks = load(a.target, a.analysis, a.root and os.path.abspath(a.root))
    except (OSError, ValueError, yaml.YAMLError, KeyError, TypeError, AttributeError) as e:
        die(f"cannot load {a.target}: {type(e).__name__}: {' '.join(str(e).split())}")
    clone = None
    if a.clone:
        exc = list(a.exclude) + (list(CLAUDE_EXCLUDES) if os.path.realpath(root) == os.path.realpath(config_dir()) else [])
        clone = os.path.realpath(a.clone)
        try:
            why = clone_refusal(clone, os.path.realpath(root), exc)
            if why:
                die(f'refusing --clone DIR: {why}')
            os.makedirs(clone, exist_ok=True)
            if os.path.isfile(os.path.join(clone, CLONE_MARKER)):
                for d, subs, _ in os.walk(clone):
                    for x in subs:
                        p = os.path.join(d, x)
                        m = os.lstat(p).st_mode
                        if not os.path.islink(p) and m & 0o700 != 0o700:
                            os.chmod(p, m | 0o700)
            try:
                subprocess.run(['rsync', '-a', '--delete', '--delete-excluded'] + [f'--exclude={e}' for e in exc]
                               + [root.rstrip('/') + '/', clone + '/'], check=True, capture_output=True, text=True)
            except FileNotFoundError:
                die('--clone copy failed: rsync not found')
            except subprocess.CalledProcessError as e:
                err = e.stderr.strip().splitlines()[:1]
                try:
                    open(os.path.join(clone, CLONE_MARKER), 'w').close()
                except OSError:
                    pass
                die(f'--clone copy failed: rsync exit {e.returncode}' + (f': {err[0]}' if err else ''))
            open(os.path.join(clone, CLONE_MARKER), 'w').close()
        except OSError as e:
            die(f"--clone copy failed: {type(e).__name__}: {' '.join(str(e).split())}")
    ctx = dict(mode=mode, plan_id=plan_id, plan_dir=plan_dir, root=root, tasks=tasks, order=order, scope=scope, requirements=reqs, doc=doc, record_tasks=rtasks,
               exceptions=set(a.ceiling_exception), clone=clone, after_task=a.after_task, target=a.target, analysis=a.analysis)
    if a.approve is not None:
        if mode != 'plan' or not a.approve.strip():
            die('--approve needs a plan folder and the user words, not a design record or an empty string')
        stamp_approval(plan_dir, a.approve)
    fails = warns = 0
    print(f"plan-verify {mode} {plan_id}: {len(tasks)} tasks, root {root}")
    for fn in CHECKS:
        try:
            ok, measured = fn(ctx)
        except (OSError, KeyError, TypeError, ValueError, StopIteration, AttributeError, yaml.YAMLError) as e:
            ok, measured = False, f"raised {type(e).__name__}: {e}"
        fails += 0 if ok else 1
        warns += 1 if ok == 'WARN' else 0
        print(f"{'WARN' if ok == 'WARN' else 'PASS' if ok else 'FAIL'}  {fn.__name__[4:]:<18} {measured}")
    print(f"\n{len(CHECKS) - fails}/{len(CHECKS)} checks passed" + (f", {warns} warnings" if warns else ''))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
