#!/usr/bin/env python3
"""change-map: turn a finished plan or an adhoc record into change-map.json and change-map.md.

usage: change-map.py --plan PLAN_DIR --workspace-root ROOT
       change-map.py --adhoc RECORD.md --workspace-root ROOT

--plan writes change-map.{json,md} into the plan folder (a legacy plan in docs/specs/changes whose docs/plan/<plan_id>/ already exists
keeps it there); --adhoc writes ROOT/docs/changes/adhoc/<date>-<slug>/change-map.{json,md}, the date being the record's own. A legacy
docs root back in a migrated workspace (docs/changes/MIGRATION-MAP.tsv present) prints one WARN line on stderr.
The JSON is change-map.json schema_version 1, the contract of the claude-manager change claude-change-visibility.
Exit 0 whatever it finds (a mismatch warns and never blocks); 2 when the input cannot be loaded.

Every path a record declares is relative to the workspace root, a sub-repo path carrying its folder; an absolute path under the root or a
leading ./ is normalised first. auto_limits lists the checks that could not run, in LIMIT_ORDER: no_git (no git root), no_commit (a task with
a result has no commit), commit_unknown (a commit no root knows), no_specs (no docs/specs/use-cases, docs/specs/changes or docs/changes/*/specs). Each task carries
its own list, the plan's list is their union, and a task with no_commit or commit_unknown gets no diff rule.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tomllib

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python3 -I leaves the script folder off sys.path
import plan_paths

DERIVED_KEYS = ('dependencies', 'tests', 'mismatch')
SECTION_KEYS = ('purpose', 'flow', 'ui', 'endpoints', 'db_schema', 'data_reads', 'data_writes', 'business_rules', 'access',
                'events_jobs', 'config', 'dependencies', 'code_changes', 'tests', 'risk_rollback', 'mismatch')
DECLARED_KEYS = tuple(k for k in SECTION_KEYS if k not in DERIVED_KEYS)
IGNORED_PREFIXES = ('docs/plan/', 'docs/reviews/', 'docs/changes/', 'docs/brainstorm/', '.cm-tmp/')   # the record's own files are not part of the change
MANIFESTS = ('package.json', 'package-lock.json', 'pnpm-lock.yaml', 'yarn.lock', 'Cargo.toml', 'Cargo.lock',
             'pyproject.toml', 'requirements.txt', 'go.mod', 'go.sum')
DEP_MANIFESTS = ('package.json', 'Cargo.toml', 'pyproject.toml', 'requirements.txt', 'go.mod')   # lockfiles stay in MANIFESTS, never config
LIMIT_ORDER = ('no_git', 'no_commit', 'commit_unknown', 'no_specs')
MIGRATION = re.compile(r'(^|/)(migrations?|migrate)/|\.sql$')
CONFIG = re.compile(r'(^|/)(\.env[^/]*|config/.*|settings\.[A-Za-z]+|[^/]+\.(toml|ini|cfg))$')
UI = re.compile(r'\.(tsx|jsx|vue|svelte|css|scss|html)$|(^|/)(components|screens|pages|views|ui)/')
SHA = re.compile(r'[0-9a-fA-F]{7,40}')


def die(msg):
    """print the reason on stderr and exit 2: the input could not be loaded"""
    print(f'change-map: {msg}', file=sys.stderr)
    sys.exit(2)


def read_yaml(path):
    """the parsed YAML of a file"""
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_plan(plan_dir):
    """-> (meta, tasks). meta is {kind: 'plan', id, title, purpose, standard}: title and purpose are the plan objective (plan_id when
    there is none); standard is true when validation_strategy.change_record_standard is 1. Each task is its whole record.
    Inline tasks of plan.yaml come first; a legacy plan with a tasks/ folder reads tasks/{wave}/{id}.yaml from the index entries' file.
    A missing or unparsable file raises OSError or yaml.YAMLError, which main turns into exit 2."""
    idx = read_yaml(os.path.join(plan_dir, 'plan.yaml'))
    tasks = plan_paths.tasks_of(plan_dir, idx, read_yaml)
    objective = str(idx.get('objective') or idx['plan_id']).strip()
    standard = (idx.get('validation_strategy') or {}).get('change_record_standard') == 1
    return {'kind': 'plan', 'id': str(idx['plan_id']), 'title': objective, 'purpose': objective, 'standard': standard}, tasks


def load_adhoc(path):
    """-> (meta, tasks) from the YAML front matter between the first two `---` lines of an adhoc record: slug, date, run, files_changed,
    commits (default []), data_impact. One task whose id and title are the slug, status done, result {run, files_changed, commits, data_impact}. An adhoc record
    is a standard record, so standard is True; its purpose is the tasks' own. meta also carries date, the front matter's date as a string,
    which names the adhoc folder. No front matter raises ValueError; no date raises KeyError."""
    with open(path, encoding='utf-8') as f:
        m = re.match(r'---\n(.*?)\n---\n', f.read(), re.S)
    if not m:
        raise ValueError('no YAML front matter')
    fm = yaml.safe_load(m.group(1))
    slug = str(fm['slug'])
    result = {k: fm.get(k) for k in ('run', 'files_changed', 'commits', 'data_impact')}
    result['commits'] = result['commits'] or []
    task = {'id': slug, 'title': slug, 'status': 'done', 'result': result}
    return {'kind': 'adhoc', 'id': slug, 'title': slug, 'purpose': None, 'standard': True, 'date': str(fm['date'])}, [task]


def to_section(value):
    """-> a Section of the contract: {'none': reason} for the string 'none: <reason>' (a string without the prefix keeps its text),
    {'entries': [...]} for a list, {'entries': [value]} for a non-empty dict (risk_rollback), {'none': None} for anything absent."""
    if isinstance(value, str):
        return {'none': value[5:].strip() if value.startswith('none:') else value}
    if isinstance(value, list):
        return {'entries': value}
    if isinstance(value, dict) and value:
        return {'entries': [value]}
    return {'none': None}


def filled(value):
    """True for a declared key that is written: a non-empty list or dict, or a string starting 'none:'"""
    return isinstance(value, str) and value.startswith('none:') or isinstance(value, (list, dict)) and bool(value)


def git_roots(root):
    """-> the workspace root and its direct children that hold a .git, as absolute paths; [] when none does"""
    cands = [root] + sorted(os.path.join(root, d) for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))
    return [c for c in cands if os.path.exists(os.path.join(c, '.git'))]


def git_out(repo, *args):
    """stdout of `git -C repo args` as text. An argument list, never a shell: a sha or path from a record cannot become a command."""
    return subprocess.run(['git', '-C', repo, *args], capture_output=True).stdout.decode('utf-8', 'replace')


def find_repo(roots, sha):
    """-> the first git root that knows the commit, or None. A value that is not 7-40 hex digits is never passed to git."""
    if not SHA.fullmatch(sha):
        return None
    for r in roots:
        if subprocess.run(['git', '-C', r, 'cat-file', '-e', f'{sha}^{{commit}}'], capture_output=True).returncode == 0:
            return r
    return None


def git_show(repo, spec):
    """-> the text of `git show spec` (rev:path), or None when git exits non-zero (the file or the parent commit is absent)"""
    p = subprocess.run(['git', '-C', repo, 'show', spec], capture_output=True)
    return p.stdout.decode('utf-8', 'replace') if p.returncode == 0 else None


def commit_files(repo, root, sha):
    """-> the paths one commit changed, relative to the workspace root (prefixed by the repo's folder when the repo is a child of root).
    Reads `git show --name-only --format= -z`, so a path with spaces or unicode arrives unquoted."""
    rel = os.path.relpath(repo, root)
    names = [n for n in git_out(repo, 'show', '--name-only', '--format=', '-z', sha).split('\0') if n]
    return names if rel == '.' else [f'{rel}/{n}' for n in names]


PEP508 = re.compile(r'\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*([^;#]*)')


def py_req(line):
    """-> (name, specifier) of one PEP 508 requirement line, or None"""
    m = PEP508.match(line)
    return (m.group(1), m.group(2).replace(' ', '').strip()) if m else None


def toml_ver(v):
    """-> the version of a Cargo or poetry dependency value: the string, a table's version, else ''"""
    return str(v if isinstance(v, str) else v.get('version', '')) if isinstance(v, (str, dict)) else ''


def parse_deps(name, text):
    """-> {dependency name: version} of one manifest text. {} for text None (that side of the commit lacks the file); None when the text
    does not parse, so no entry is made for the file. package.json: dependencies, devDependencies, peerDependencies, optionalDependencies.
    Cargo.toml: [dependencies], [dev-dependencies], [build-dependencies]. pyproject.toml: [project].dependencies and [tool.poetry.dependencies]
    minus python. requirements.txt: name + specifier, blank, comment and -r/-e/-- lines skipped. go.mod: require lines, single and block."""
    if text is None:
        return {}
    out = {}
    try:
        if name == 'package.json':
            for k in ('dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies'):
                out.update({str(n): str(v) for n, v in (json.loads(text).get(k) or {}).items()})
        elif name == 'Cargo.toml':
            doc = tomllib.loads(text)
            for k in ('dependencies', 'dev-dependencies', 'build-dependencies'):
                out.update({n: toml_ver(v) for n, v in (doc.get(k) or {}).items()})
        elif name == 'pyproject.toml':
            doc = tomllib.loads(text)
            out.update(dict(r for r in map(py_req, (doc.get('project') or {}).get('dependencies') or []) if r))
            poetry = ((doc.get('tool') or {}).get('poetry') or {}).get('dependencies') or {}
            out.update({n: toml_ver(v) for n, v in poetry.items() if n != 'python'})
        elif name == 'requirements.txt':
            lines = [ln.strip().rstrip('\\').strip() for ln in text.splitlines()]
            for ln in lines:
                if not ln or ln.startswith(('#', '-')):
                    continue
                if '://' in ln or ln.startswith(('git+', 'hg+', 'svn+', 'bzr+')):
                    egg = re.search(r'#egg=([A-Za-z0-9][A-Za-z0-9._-]*)', ln)
                    if egg:
                        out[egg.group(1)] = ''
                    continue
                r = py_req(ln)
                if r:
                    out[r[0]] = r[1]
        elif name == 'go.mod':
            block = False
            for ln in text.splitlines():
                s = ln.split('//')[0].strip()
                m = re.match(r'require\s*(.*)$', s)
                if block and s == ')':
                    block = False
                elif block or m:
                    rest = s if block else m.group(1).strip()
                    if rest == '(':
                        block = True
                    elif len(rest.split()) >= 2:
                        out[rest.split()[0]] = rest.split()[1]
    except (ValueError, TypeError, AttributeError):
        return None
    return out


def manifest_entries(repo, sha, inner, shown):
    """-> dependency entries {file, name, change: added|removed|changed, version}, sorted by name, from the parsed dependency lists of one
    manifest (path `inner` inside repo, shown as `shown`) before and after one commit: only after is added (new version), only before is
    removed (old version), both with another version is changed (new version), equal is nothing. A side that fails to parse yields no entry."""
    base = os.path.basename(inner)
    before, after = parse_deps(base, git_show(repo, f'{sha}^:{inner}')), parse_deps(base, git_show(repo, f'{sha}:{inner}'))
    if before is None or after is None:
        return []
    return [{'file': shown, 'name': n, 'change': 'added' if n not in before else 'removed' if n not in after else 'changed',
             'version': after[n] if n in after else before[n]}
            for n in sorted(set(before) | set(after)) if n not in before or n not in after or before[n] != after[n]]


def derive_tests(result):
    """-> tests entries: one per result.ac_check row {source: 'ac_check', text: '<ac>: <note>', result: pass|fail} (met true is pass, anything
    else fail) and one per result.verification line {source: 'verification', text, result: 'unknown'}. A verification that is a string is one
    line and a non-list ac_check has no rows."""
    ac, v = result.get('ac_check'), result.get('verification')
    out = [{'source': 'ac_check', 'text': f"{r.get('ac')}: {r.get('note') or ''}".strip(), 'result': 'pass' if r.get('met') is True else 'fail'}
           for r in (ac if isinstance(ac, list) else []) if isinstance(r, dict)]
    return out + [{'source': 'verification', 'text': str(x), 'result': 'unknown'} for x in (v if isinstance(v, list) else [v] if v else [])]


def norm_path(p, root):
    """-> a declared path as the diff names it: an absolute path under root becomes relative to root, a leading ./ is dropped"""
    p = str(p)
    if os.path.isabs(p):
        rel = os.path.relpath(p, root)
        return p if rel == '..' or rel.startswith('..' + os.sep) else rel
    while p.startswith('./'):
        p = p[2:]
    return p


def declared_paths(result, root):
    """-> the paths a task declares as changed, through norm_path: result.files_changed (each a string or {path}) and result.data_impact.code_changes[].file"""
    fc = result.get('files_changed')
    paths = {(f.get('path') or f.get('file')) if isinstance(f, dict) else f for f in (fc if isinstance(fc, list) else [])}
    di = result.get('data_impact')
    cc = di.get('code_changes') if isinstance(di, dict) else None
    paths |= {c.get('file') for c in cc if isinstance(c, dict)} if isinstance(cc, list) else set()
    return {norm_path(p, root) for p in paths if p}


def read_specs(root):
    """-> the text of every file under root/docs/specs/use-cases, root/docs/specs/changes and root/docs/changes/*/specs; None when none of
    them is a directory"""
    out, found = [], False
    tops = ['docs/specs/use-cases', 'docs/specs/changes']
    if os.path.isdir(os.path.join(root, 'docs/changes')):
        tops += [os.path.join('docs/changes', n, 'specs') for n in sorted(os.listdir(os.path.join(root, 'docs/changes')))]
    for top in tops:
        found = found or os.path.isdir(os.path.join(root, top))
        for d, _, names in os.walk(os.path.join(root, top)):
            for n in names:
                with open(os.path.join(d, n), encoding='utf-8', errors='replace') as f:
                    out.append(f.read())
    return out if found else None


def ac_in(part, text):
    """True when the id `part` is in text as a whole token: UC-01 is not in UC-010, AC-1 is not in AC-12"""
    return re.search(r'(?<![A-Za-z0-9-])' + re.escape(part) + r'(?![A-Za-z0-9])', text) is not None


def find_mismatches(task, standard, diff, specs):
    """-> the mismatch entries {code, task_id, file|ac} of one task, the seven codes of design D3, never user copy.
    task is {id, status, result}; diff is None when the diff rules are off (no git root, no commit, or a commit no root knows), else
    {declared, changed, owned, attached}: the task's declared paths and the group's changed paths (both without IGNORED_PREFIXES), the changed
    paths the task owns (declared, or attached to it) and those attached to it because no task of its commit group declares them; specs is
    read_specs(root), None when there is no spec folder.
    record_missing: standard and status done, and result.run lacks started_at or finished_at, or one of DECLARED_KEYS is not filled.
    changed_not_declared: a path of diff['attached']. declared_not_changed: declared minus changed.
    migration_undeclared / config_undeclared / ui_undeclared: an owned path matching MIGRATION / CONFIG / UI (manifests are never
    config) while data_impact.db_schema / config / ui is a 'none:' string.
    ac_not_found: only when specs is not None; a data_impact.business_rules[].ac whose parts (split on '/') are not all found, as whole
    tokens, in one spec text."""
    tid, res, out = task['id'], task.get('result') or {}, []
    di = res.get('data_impact') if isinstance(res.get('data_impact'), dict) else {}
    run = res.get('run') if isinstance(res.get('run'), dict) else {}
    if standard and task.get('status') == 'done' and not (run.get('started_at') and run.get('finished_at') and all(filled(di.get(k)) for k in DECLARED_KEYS)):
        out.append({'code': 'record_missing', 'task_id': tid})
    if diff is not None:
        out += [{'code': 'changed_not_declared', 'task_id': tid, 'file': p} for p in sorted(diff['attached'])]
        out += [{'code': 'declared_not_changed', 'task_id': tid, 'file': p} for p in sorted(diff['declared'] - diff['changed'])]
        for code, key, pat in (('migration_undeclared', 'db_schema', MIGRATION), ('config_undeclared', 'config', CONFIG), ('ui_undeclared', 'ui', UI)):
            if isinstance(di.get(key), str) and di[key].startswith('none:'):
                out += [{'code': code, 'task_id': tid, 'file': p} for p in sorted(diff['owned']) if pat.search(p) and os.path.basename(p) not in MANIFESTS]
    rules = di.get('business_rules') if isinstance(di.get('business_rules'), list) else []
    for r in rules:
        ac = r.get('ac') if isinstance(r, dict) else None
        if ac and specs is not None and not any(all(ac_in(part, text) for part in str(ac).split('/')) for text in specs):
            out.append({'code': 'ac_not_found', 'task_id': tid, 'ac': ac})
    return out


def build_model(meta, tasks, root):
    """-> the change-map.json v1 dict: {schema_version: 1, kind, id, title, generated_at (UTC, seconds), standard, auto_limits, sections, tasks}.
    Per task: id, title, status, has_result (result is a dict), run ({started_at, finished_at} or None), files_changed (sorted declared_paths),
    auto_limits (its own subset of LIMIT_ORDER: no_git and no_specs when they hold for the run, no_commit when a git root exists and a task with a
    result lists no commit, commit_unknown when one of its commits resolves in no root; the last two only on the task concerned), sections: the 13
    declared keys through to_section, then dependencies {entries}, tests {entries}, mismatch {entries}. The plan's auto_limits is the ordered union
    of the tasks' lists, or the project-wide codes alone when there is no task. A task with no_git, no_commit or commit_unknown has no diff.
    Tasks whose commits share a sha form a group (plan order kept); the group's changed set is the union of commit_files over its shas, minus
    IGNORED_PREFIXES. A declared path (norm_path) absent from it but present as '<repo folder>/<path>' for exactly one child repo that resolved a
    group sha counts as that path. A changed file that no task of the group declares is attached once, to the first task whose files[].path lists it,
    else to the first task of the group; a task is charged only with its own declared and attached files, and its migration, config, ui rules
    and its dependencies (parse_deps over the owned manifests of DEP_MANIFESTS in its own commits) read only the files it owns.
    Plan-level sections: purpose is [meta purpose] when there is one; every other key concatenates the tasks' entries, each dict tagged task_id
    (a plain string becomes {text, task_id}); a key with no entry is {'none': first task reason} and a derived key is always {'entries': [...]}."""
    roots = git_roots(root)
    specs = read_specs(root)
    cache = {}

    def commit(sha):
        if sha not in cache:
            repo = find_repo(roots, sha)
            cache[sha] = (repo, commit_files(repo, root, sha) if repo else None)
        return cache[sha]

    info = []
    for t in tasks:
        res = t.get('result') if isinstance(t.get('result'), dict) else None
        shas = list(dict.fromkeys(str(s) for s in (res or {}).get('commits') or [])) if isinstance((res or {}).get('commits'), list) else []
        known = bool(roots) and all(commit(s)[0] for s in shas)
        limits = {'no_git'} if not roots else {'no_commit'} if res is not None and not shas else {'commit_unknown'} if not known else set()
        if specs is None:
            limits.add('no_specs')
        info.append({'t': t, 'res': res, 'r': res or {}, 'shas': shas if roots and known else [], 'limits': limits, 'diff': None, 'deps': []})
    parent = list(range(len(info)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    first = {}
    for i, x in enumerate(info):
        for s in x['shas']:
            if s in first:
                parent[find(i)] = find(first[s])
            else:
                first[s] = i
    groups = {}
    for i, x in enumerate(info):
        if x['shas']:
            groups.setdefault(find(i), []).append(i)
    for members in groups.values():
        shas = list(dict.fromkeys(s for i in members for s in info[i]['shas']))
        changed, rels = set(), set()
        for s in shas:
            repo, names = commit(s)
            changed |= set(names)
            rels |= {os.path.relpath(repo, root)} - {'.'}
        real = {p for p in changed if not p.startswith(IGNORED_PREFIXES)}

        def resolve(p):
            hits = [f'{rel}/{p}' for rel in sorted(rels) if f'{rel}/{p}' in real]
            return p if p in real or len(hits) != 1 else hits[0]

        declared = {i: {resolve(p) for p in declared_paths(info[i]['r'], root) if not p.startswith(IGNORED_PREFIXES)} for i in members}
        listed = {i: {resolve(norm_path(f.get('path'), root)) for f in info[i]['t'].get('files') or [] if isinstance(f, dict) and f.get('path')} for i in members}
        attached = {i: set() for i in members}
        for f in sorted(real - set().union(*declared.values())):
            attached[next((i for i in members if f in listed[i]), members[0])].add(f)
        for i in members:
            owned = (real & declared[i]) | attached[i]
            info[i]['diff'] = {'declared': declared[i], 'changed': real, 'owned': owned, 'attached': attached[i]}
            for s in info[i]['shas']:
                repo, names = commit(s)
                rel = os.path.relpath(repo, root)
                info[i]['deps'] += [e for n in names if n in owned and os.path.basename(n) in DEP_MANIFESTS
                                    for e in manifest_entries(repo, s, n if rel == '.' else n[len(rel) + 1:], n)]
    done = []
    for x in info:
        t, res, r = x['t'], x['res'], x['r']
        di = r.get('data_impact') if isinstance(r.get('data_impact'), dict) else {}
        sections = {k: to_section(di.get(k)) for k in DECLARED_KEYS}
        sections['dependencies'] = {'entries': x['deps']}
        sections['tests'] = {'entries': derive_tests(r)}
        sections['mismatch'] = {'entries': find_mismatches({'id': t['id'], 'status': t.get('status'), 'result': res}, meta['standard'], x['diff'], specs)}
        run = r.get('run') if isinstance(r.get('run'), dict) else {}
        done.append({'id': str(t['id']), 'title': str(t.get('title') or t['id']), 'status': str(t.get('status')), 'has_result': res is not None,
                     'run': {'started_at': run['started_at'], 'finished_at': run['finished_at']} if run.get('started_at') and run.get('finished_at') else None,
                     'files_changed': sorted(declared_paths(r, root)), 'auto_limits': [c for c in LIMIT_ORDER if c in x['limits']], 'sections': sections})
    plan = {}
    for k in SECTION_KEYS:
        entries = [meta['purpose']] if k == 'purpose' and meta['purpose'] else [
            dict(e, task_id=t['id']) if isinstance(e, dict) else {'text': e, 'task_id': t['id']}
            for t in done for e in t['sections'][k].get('entries', [])]
        reasons = [t['sections'][k]['none'] for t in done if t['sections'][k].get('none')]
        plan[k] = {'entries': entries} if entries or k in DERIVED_KEYS else {'none': reasons[0] if reasons else None}
    union = {c for d in done for c in d['auto_limits']} if done else {c for c, on in (('no_git', not roots), ('no_specs', specs is None)) if on}
    return {'schema_version': 1, 'kind': meta['kind'], 'id': meta['id'], 'title': meta['title'],
            'generated_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'standard': meta['standard'], 'auto_limits': [c for c in LIMIT_ORDER if c in union], 'sections': plan, 'tasks': done}


def render_markdown(model):
    """-> the Markdown text: a title line, then one `## <key>` heading per SECTION_KEYS entry in order (English key names, never screen copy),
    each followed by one bullet per entry as sorted-key JSON, or by 'none: <reason>'. No other `## ` line."""
    lines = [f"# {model['title']}", '', f"{model['kind']} {model['id']} - standard {str(model['standard']).lower()} - generated {model['generated_at']}", '']
    if model['auto_limits']:
        lines += ['auto_limits: ' + ', '.join(model['auto_limits']), '']
    for k in SECTION_KEYS:
        s = model['sections'][k]
        lines += [f'## {k}', '']
        if 'entries' in s:
            lines += [f'- {json.dumps(e, ensure_ascii=False, sort_keys=True)}' for e in s['entries']] or ['(no entries)']
        else:
            lines.append(f"none: {s['none'] or ''}".strip())
        lines.append('')
    return '\n'.join(lines)


def write_atomic(path, text):
    """writes text to <path>.tmp.<pid> in the same folder, then os.replace onto path; the temporary file is removed when anything fails"""
    tmp = f'{path}.tmp.{os.getpid()}'
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def write_outputs(model, json_path, md_path=None):
    """writes the model as UTF-8 JSON (sorted keys, indent 2) to json_path, then render_markdown to md_path (default: json_path with .json
    replaced by .md), creating both folders. Atomic per file: a reader sees the old or the new file, never a torn one. The files are regenerated after every
    task result and once more by the wave_commit spawn, the map of record."""
    md_path = md_path or json_path[:-len('.json')] + '.md'
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    write_atomic(json_path, json.dumps(model, ensure_ascii=False, sort_keys=True, indent=2))
    write_atomic(md_path, render_markdown(model))


def main(argv=None):
    """CLI. Either mode writes change-map.json to plan_paths.ephemeral_dir(root, id) and change-map.md to the change folder: --plan's own folder,
    ROOT/docs/changes/adhoc/<date>-<slug>/ for --adhoc. Nothing else is written there.
    A non-empty plan_paths.legacy_roots_reappeared prints one WARN line on stderr.
    -> 0 on any finding; die (exit 2) when the input cannot be loaded (OSError, ValueError, KeyError, TypeError, AttributeError, yaml.YAMLError)."""
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--plan')
    g.add_argument('--adhoc')
    ap.add_argument('--workspace-root', required=True)
    a = ap.parse_args(argv)
    root = os.path.abspath(a.workspace_root)
    try:
        if a.plan:
            meta, tasks = load_plan(os.path.abspath(a.plan))
            md_dir = os.path.abspath(a.plan)
        else:
            meta, tasks = load_adhoc(os.path.abspath(a.adhoc))
            md_dir = os.path.join(root, 'docs/changes/adhoc', f"{meta['date']}-{meta['id']}")
        key = meta['id'] if a.plan else f"{meta['date']}-{meta['id']}"
        write_outputs(build_model(meta, tasks, root), str(plan_paths.ephemeral_dir(root, key) / 'change-map.json'),
                      os.path.join(md_dir, plan_paths.CHANGE_MAP_MD))
        back = plan_paths.legacy_roots_reappeared(root)
        if back:
            print(f"change-map: WARN legacy docs root back in a migrated workspace: {', '.join(back)}", file=sys.stderr)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, yaml.YAMLError) as e:
        die(f'cannot load {a.plan or a.adhoc}: {type(e).__name__}: {e}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
