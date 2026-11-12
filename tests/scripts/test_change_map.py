"""Tests for scripts/change-map.py: each case builds a tiny workspace (a git repo, the marked fixture plan with the commit's sha) and runs the CLI."""
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

SCRIPT = Path(__file__).resolve().parents[2] / 'plugins' / 'agent-hub' / 'scripts' / 'change-map.py'
FIX = Path(__file__).resolve().parent / 'fixtures' / 'change-map'
sys.path.insert(0, str(SCRIPT.parent))
from plan_paths import ephemeral_dir  # noqa: E402
KEYS = ['purpose', 'flow', 'ui', 'endpoints', 'db_schema', 'data_reads', 'data_writes', 'business_rules', 'access', 'events_jobs',
        'config', 'dependencies', 'code_changes', 'tests', 'risk_rollback', 'mismatch']
GIT = ['git', '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false']


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def load_module():
    spec = importlib.util.spec_from_file_location('change_map', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Workspace:
    """a temp workspace; with git, one commit of `files` (a path tuple, or a {path: text} dict) and the marked plan holding its sha (the plan is added after the commit)"""

    def __init__(self, case, files=('src/app.py',), git=True, where='docs/plan/demo-marked'):
        tmp = tempfile.TemporaryDirectory(prefix='change-map-')
        case.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        sha = 'none'
        if git:
            subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        self.write(files)
        if git:
            sha = self.commit({})
        self.sha = sha
        self.plan = self.root / where
        shutil.copytree(FIX / 'marked-plan', self.plan)
        t = self.plan / 'tasks/W1/W1-T1.yaml'
        t.write_text(t.read_text(encoding='utf-8').replace('__SHA__', sha), encoding='utf-8')

    def write(self, files, base=None):
        for f, text in (files.items() if isinstance(files, dict) else ((f, 'x\n') for f in files)):
            p = (base or self.root) / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding='utf-8')

    def commit(self, files, repo=None):
        """writes `files`, commits everything in `repo` (default the root) and returns the sha"""
        repo = repo or self.root
        self.write(files, repo)
        subprocess.run([*GIT, '-C', str(repo), 'add', '-A'], check=True)
        subprocess.run([*GIT, '-C', str(repo), 'commit', '-q', '-m', 'c', '--allow-empty'], check=True)
        return subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()

    def child_repo(self, name, files):
        """a git repo in the folder `name` of the root, with one commit of `files`; returns the sha"""
        (self.root / name).mkdir()
        subprocess.run(['git', 'init', '-q', str(self.root / name)], check=True)
        return self.commit(files, self.root / name)

    def edit_task(self, fn, tid='W1-T1'):
        p = self.plan / f'tasks/W1/{tid}.yaml'
        t = yaml.safe_load(p.read_text(encoding='utf-8'))
        fn(t)
        p.write_text(yaml.safe_dump(t, allow_unicode=True, sort_keys=False), encoding='utf-8')

    def declare(self, *paths):
        self.edit_task(lambda t: t['result']['files_changed'].extend({'path': p, 'note': 'n'} for p in paths))

    def set_declared(self, tid, *paths, commits=None):
        """the task declares exactly `paths` (code_changes set to a none: string); commits replaces result.commits when given"""
        def fn(t):
            t['result'].update(files_changed=[{'path': p, 'note': 'n'} for p in paths])
            t['result']['data_impact']['code_changes'] = 'none: n'
            if commits is not None:
                t['result']['commits'] = list(commits)
        self.edit_task(fn, tid)

    def add_task(self, tid, declared=(), listed=(), shas=()):
        """a second task of the plan: files[] lists `listed`, the result declares `declared` and carries `shas`"""
        t = yaml.safe_load((self.plan / 'tasks/W1/W1-T1.yaml').read_text(encoding='utf-8'))
        t['id'] = t['title'] = tid
        t['files'] = [{'path': p, 'change': 'edit', 'why': 'w'} for p in listed]
        t['result'].update(commits=list(shas), files_changed=[{'path': p, 'note': 'n'} for p in declared])
        t['result']['data_impact']['code_changes'] = 'none: n'
        (self.plan / f'tasks/W1/{tid}.yaml').write_text(yaml.safe_dump(t, allow_unicode=True, sort_keys=False), encoding='utf-8')
        idx = yaml.safe_load((self.plan / 'plan.yaml').read_text(encoding='utf-8'))
        idx['tasks'].append({'id': tid, 'wave': 'W1', 'file': f'tasks/W1/{tid}.yaml', 'depends_on': []})
        (self.plan / 'plan.yaml').write_text(yaml.safe_dump(idx, allow_unicode=True, sort_keys=False), encoding='utf-8')

    def build(self):
        p = run('--plan', str(self.plan), '--workspace-root', str(self.root))
        out = ephemeral_dir(self.root, self.plan.name) / 'change-map.json'   # the json is throwaway: <root>/.cm-tmp/<plan_id>/
        if not out.exists():   # a run of the previous layout left it in the plan folder; the location cases below assert the real place
            out = self.plan / 'change-map.json'
        return p, (json.loads(out.read_text(encoding='utf-8')) if out.exists() else None)

def mismatches(m):
    return [(e['code'], e.get('file') or e.get('ac')) for e in m['sections']['mismatch']['entries']]


def task_map(m, tid):
    return next(t for t in m['tasks'] if t['id'] == tid)


def task_mismatches(m, tid):
    return [(e['code'], e.get('file') or e.get('ac')) for e in task_map(m, tid)['sections']['mismatch']['entries']]


class ChangeMapTests(unittest.TestCase):
    def test_clean_marked_plan_has_no_mismatch(self):
        p, m = Workspace(self).build()
        self.assertEqual(p.returncode, 0)
        self.assertEqual((m['schema_version'], m['kind'], m['standard'], m['auto_limits']), (1, 'plan', True, ['no_specs']))
        self.assertEqual(sorted(m['sections']), sorted(KEYS))
        self.assertEqual(sorted(m['tasks'][0]['sections']), sorted(KEYS))
        self.assertEqual(mismatches(m), [])

    def test_record_missing(self):
        w = Workspace(self)
        w.edit_task(lambda t: t['result']['data_impact'].pop('ui'))
        p, m = w.build()
        self.assertEqual((p.returncode, mismatches(m)), (0, [('record_missing', None)]))
        self.assertEqual(m['sections']['mismatch']['entries'][0]['task_id'], 'W1-T1')

    def test_changed_not_declared(self):
        p, m = Workspace(self, files=('src/app.py', 'src/extra.py')).build()
        self.assertEqual((p.returncode, mismatches(m)), (0, [('changed_not_declared', 'src/extra.py')]))

    def test_declared_not_changed(self):
        w = Workspace(self)
        w.declare('src/ghost.py')
        self.assertEqual(mismatches(w.build()[1]), [('declared_not_changed', 'src/ghost.py')])

    def test_migration_undeclared(self):
        w = Workspace(self, files=('src/app.py', 'db/migrations/001_add.sql'))
        w.declare('db/migrations/001_add.sql')
        self.assertEqual(mismatches(w.build()[1]), [('migration_undeclared', 'db/migrations/001_add.sql')])

    def test_config_undeclared(self):
        w = Workspace(self, files=('src/app.py', 'config/app.toml'))
        w.declare('config/app.toml')
        self.assertEqual(mismatches(w.build()[1]), [('config_undeclared', 'config/app.toml')])

    def test_ui_undeclared(self):
        w = Workspace(self, files=('src/app.py', 'src/ui/Panel.tsx'))
        w.declare('src/ui/Panel.tsx')
        self.assertEqual(mismatches(w.build()[1]), [('ui_undeclared', 'src/ui/Panel.tsx')])

    def test_ac_not_found(self):
        w = Workspace(self)
        w.write({'docs/specs/use-cases/UC-001.md': 'UC-001 AC-1\n'})
        w.edit_task(lambda t: t['result']['data_impact'].update(business_rules=[{'rule': 'r', 'ac': 'UC-999/AC-1'}]))
        self.assertEqual(mismatches(w.build()[1]), [('ac_not_found', 'UC-999/AC-1')])

    def test_no_git_skips_every_diff_rule(self):
        w = Workspace(self, git=False)
        w.declare('src/ghost.py')
        p, m = w.build()
        self.assertEqual((p.returncode, m['auto_limits'], mismatches(m)), (0, ['no_git', 'no_specs'], []))

    def test_unreadable_plan_exits_2(self):
        w = Workspace(self)
        p = run('--plan', str(w.root / 'docs/plan/nope'), '--workspace-root', str(w.root))
        self.assertEqual(p.returncode, 2)
        self.assertIn('cannot load', p.stderr)

    def test_markdown_has_the_16_headings_in_order(self):
        w = Workspace(self)
        w.declare('src/ghost.py')
        self.assertEqual(w.build()[0].returncode, 0)
        heads = [l[3:] for l in (w.plan / 'change-map.md').read_text(encoding='utf-8').splitlines() if l.startswith('## ')]
        self.assertEqual(heads, KEYS)

    def test_adhoc_record_has_one_task_named_by_its_slug(self):
        w = Workspace(self)
        rec = w.root / 'docs/reviews/adhoc/2026-10-27-demo-fix.md'
        rec.parent.mkdir(parents=True)
        shutil.copy(FIX / 'adhoc-record.md', rec)
        p = run('--adhoc', str(rec), '--workspace-root', str(w.root))
        m = json.loads((ephemeral_dir(w.root, '2026-10-27-demo-fix') / 'change-map.json').read_text(encoding='utf-8'))
        self.assertEqual((p.returncode, m['kind'], len(m['tasks']), m['tasks'][0]['id']), (0, 'adhoc', 1, 'demo-fix'))

    def test_old_plan_is_not_standard_and_has_no_record_missing(self):
        w = Workspace(self)
        old = w.root / 'docs/plan/demo-old'
        shutil.copytree(FIX / 'old-plan', old)
        p = run('--plan', str(old), '--workspace-root', str(w.root))
        m = json.loads((ephemeral_dir(w.root, 'demo-old') / 'change-map.json').read_text(encoding='utf-8'))
        self.assertEqual((p.returncode, m['standard']), (0, False))
        self.assertNotIn('record_missing', [c for c, _ in mismatches(m)])

    def test_path_with_spaces_and_unicode(self):
        name = 'src/tệp mới.py'   # scrub-allow: unicode file-name fixture
        w = Workspace(self, files=('src/app.py', name))
        w.declare(name)
        self.assertEqual(mismatches(w.build()[1]), [])

    def test_json_shape_is_contract_v1(self):
        m = Workspace(self).build()[1]
        self.assertEqual(sorted(m), ['auto_limits', 'generated_at', 'id', 'kind', 'schema_version', 'sections', 'standard', 'tasks', 'title'])
        t = m['tasks'][0]
        self.assertEqual(sorted(t), ['auto_limits', 'files_changed', 'has_result', 'id', 'run', 'sections', 'status', 'title'])
        self.assertEqual(t['run'], {'started_at': '2026-10-27T01:00:00Z', 'finished_at': '2026-10-27T01:05:00Z'})
        for s in (m['sections'], t['sections']):
            self.assertTrue(all(set(v) in ({'none'}, {'entries'}) for v in s.values()))
            self.assertTrue(all('entries' in s[k] for k in ('dependencies', 'tests', 'mismatch')))
        self.assertEqual({e['result'] for e in t['sections']['tests']['entries']}, {'pass', 'unknown'})

    def test_string_data_impact_and_run_do_not_crash(self):
        w = Workspace(self)

        def fn(t):
            t['result']['data_impact'] = 'none: x'
            t['result']['run'] = 'once'
            t['result']['files_changed'] = []
            t['result']['commits'] = []
        w.edit_task(fn)
        p, m = w.build()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(mismatches(m), [('record_missing', None)])
        self.assertEqual(m['tasks'][0]['files_changed'], [])

    def test_files_changed_dict_with_file_key(self):
        w = Workspace(self)
        w.edit_task(lambda t: t['result'].update(files_changed=[{'file': 'a.py', 'note': 'n'}], commits=[]))
        w.edit_task(lambda t: t['result']['data_impact'].update(code_changes=[]))
        p, m = w.build()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(m['tasks'][0]['files_changed'], ['a.py'])

    def test_shared_sha_wave_reports_each_undeclared_file_once(self):
        w = Workspace(self, files=('a.py', 'b.py', 'c.py', 'd.py'))
        w.set_declared('W1-T1', 'a.py')
        w.add_task('W1-T2', declared=['b.py'], listed=['b.py', 'c.py'], shas=[w.sha])
        p, m = w.build()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(task_mismatches(m, 'W1-T1'), [('changed_not_declared', 'd.py')])   # listed by no task: the first task of the group
        self.assertEqual(task_mismatches(m, 'W1-T2'), [('changed_not_declared', 'c.py')])   # listed in files[]: that task
        self.assertEqual(sorted(mismatches(m)), [('changed_not_declared', 'c.py'), ('changed_not_declared', 'd.py')])

    def test_adhoc_commits_and_the_auto_limits_order(self):
        w = Workspace(self, files=('src/app.py',))
        rec = w.root / 'docs/reviews/adhoc/2026-10-27-demo-fix.md'
        rec.parent.mkdir(parents=True)

        def limits(commits=None):
            text = (FIX / 'adhoc-record.md').read_text(encoding='utf-8')
            if commits is not None:
                text = text.replace('files_changed: ["src/app.py"]\n', 'files_changed: ["src/app.py"]\ncommits: ' + json.dumps(commits) + '\n')
            rec.write_text(text, encoding='utf-8')
            p = run('--adhoc', str(rec), '--workspace-root', str(w.root))
            self.assertEqual(p.returncode, 0, p.stderr)
            m = json.loads((ephemeral_dir(w.root, '2026-10-27-demo-fix') / 'change-map.json').read_text(encoding='utf-8'))
            self.assertEqual(m['tasks'][0]['auto_limits'], m['auto_limits'])
            return m
        m = limits()                                                                         # no commits key: the default []
        self.assertEqual((m['auto_limits'], mismatches(m)), (['no_commit', 'no_specs'], []))
        m = limits(['deadbeef1'])
        self.assertEqual((m['auto_limits'], mismatches(m)), (['commit_unknown', 'no_specs'], []))
        m = limits([w.sha])                                                                  # the commit is read: src/app.py is declared
        self.assertEqual((m['auto_limits'], mismatches(m)), (['no_specs'], []))
        m = limits([w.commit({'src/extra.py': 'y\n'})])
        self.assertEqual(mismatches(m), [('changed_not_declared', 'src/extra.py'), ('declared_not_changed', 'src/app.py')])
        self.assertEqual(Workspace(self, git=False).build()[1]['auto_limits'], ['no_git', 'no_specs'])   # no git root: no_git first, no other diff code

    def test_each_task_carries_its_own_auto_limits(self):
        w = Workspace(self)
        w.add_task('W1-T2', declared=['src/other.py'], shas=[])
        p, m = w.build()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(task_map(m, 'W1-T1')['auto_limits'], ['no_specs'])
        self.assertEqual(task_map(m, 'W1-T2')['auto_limits'], ['no_commit', 'no_specs'])
        self.assertEqual(m['auto_limits'], ['no_commit', 'no_specs'])
        self.assertEqual(task_mismatches(m, 'W1-T2'), [])                                    # no diff rule for the task with no commit
        w.edit_task(lambda t: t['result'].update(commits=['deadbeef1']), 'W1-T2')
        m = w.build()[1]
        self.assertEqual((task_map(m, 'W1-T1')['auto_limits'], task_map(m, 'W1-T2')['auto_limits']), (['no_specs'], ['commit_unknown', 'no_specs']))
        self.assertEqual(m['auto_limits'], ['commit_unknown', 'no_specs'])
        w.edit_task(lambda t: t.pop('result'), 'W1-T2')                                      # a task with no result is neither no_commit nor commit_unknown
        self.assertEqual(task_map(w.build()[1], 'W1-T2')['auto_limits'], ['no_specs'])

    def test_dependencies_come_from_parsed_manifests(self):
        pkg1 = json.dumps({'name': 'p', 'version': '1.0.0', 'scripts': {'test': 'a'}, 'dependencies': {'left-pad': '1.0.0'}})
        cargo1 = '[package]\nname = "p"\nversion = "0.1.0"\n\n[dependencies]\nserde = "1"\n'
        w = Workspace(self, files={'package.json': pkg1, 'Cargo.toml': cargo1, 'package-lock.json': '{}\n', 'src/app.py': 'x\n'})
        w.set_declared('W1-T1', 'package.json', 'Cargo.toml', 'package-lock.json', 'src/app.py')

        def deps(m):
            return {(e['file'], e['name'], e['change'], e['version']) for e in task_map(m, 'W1-T1')['sections']['dependencies']['entries']}
        self.assertEqual(deps(w.build()[1]), {('package.json', 'left-pad', 'added', '1.0.0'), ('Cargo.toml', 'serde', 'added', '1')})   # a root commit: all added
        pkg2 = json.dumps({'name': 'p', 'version': '1.0.1', 'scripts': {'test': 'a', 'build': 'vite build'}, 'dependencies': {'left-pad': '1.1.0', 'react': '18.0.0'}})
        sha2 = w.commit({'package.json': pkg2, 'Cargo.toml': cargo1.replace('0.1.0', '0.2.0'), 'package-lock.json': '{"x": 1}\n'})
        w.set_declared('W1-T1', 'package.json', 'Cargo.toml', 'package-lock.json', commits=[sha2])
        self.assertEqual(deps(w.build()[1]), {('package.json', 'left-pad', 'changed', '1.1.0'), ('package.json', 'react', 'added', '18.0.0')})
        sha3 = w.commit({'package-lock.json': '{"x": 2}\n'})                                # a lockfile-only commit has no entry
        w.set_declared('W1-T1', 'package-lock.json', commits=[sha3])
        self.assertEqual(deps(w.build()[1]), set())
        sha4 = w.commit({'package.json': '{broken', 'Cargo.toml': '[dependencies]\nserde = "2"\nanyhow = "1"\n'})   # one side does not parse: no entry for it
        w.set_declared('W1-T1', 'package.json', 'Cargo.toml', commits=[sha4])
        p, m = w.build()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(deps(m), {('Cargo.toml', 'serde', 'changed', '2'), ('Cargo.toml', 'anyhow', 'added', '1')})

    def test_declared_docs_plan_path_is_never_declared_not_changed(self):
        w = Workspace(self, files=('src/app.py', 'docs/plan/other/notes.md'))
        w.declare('docs/plan/other/notes.md', 'docs/plan/nowhere/never-committed.md')
        p, m = w.build()
        self.assertEqual((p.returncode, mismatches(m)), (0, []))

    def test_no_specs_skips_ac_not_found_and_ids_match_whole_tokens(self):
        w = Workspace(self)
        w.edit_task(lambda t: t['result']['data_impact'].update(business_rules=[{'rule': 'r', 'ac': 'UC-999/AC-1'}]))
        m = w.build()[1]
        self.assertEqual((mismatches(m), m['auto_limits']), ([], ['no_specs']))              # no spec folder: the check is skipped and says so
        w.write({'docs/specs/use-cases/UC-010.md': 'UC-010\nAC-12 the rule\n'})
        w.edit_task(lambda t: t['result']['data_impact'].update(business_rules=[{'rule': 'r', 'ac': 'UC-01/AC-1'}, {'rule': 'r', 'ac': 'UC-010/AC-12'}]))
        m = w.build()[1]
        self.assertEqual((mismatches(m), m['auto_limits']), ([('ac_not_found', 'UC-01/AC-1')], []))

    def test_string_verification_is_one_tests_entry(self):
        w = Workspace(self)
        w.edit_task(lambda t: t['result'].update(verification='pytest ok', ac_check='not a list'))
        p, m = w.build()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(task_map(m, 'W1-T1')['sections']['tests']['entries'], [{'source': 'verification', 'text': 'pytest ok', 'result': 'unknown'}])

    def test_absolute_and_repo_relative_declared_paths(self):
        w = Workspace(self)
        w.set_declared('W1-T1', str(w.root / 'src/app.py'))                                  # absolute under the root
        self.assertEqual(mismatches(w.build()[1]), [])
        w.set_declared('W1-T1', './src/app.py')                                              # leading ./
        self.assertEqual(mismatches(w.build()[1]), [])
        sub = Workspace(self, files=(), git=False)                                           # a root that is no repo, a child repo api/
        sha = sub.child_repo('api', {'src/a.py': 'x\n'})
        sub.set_declared('W1-T1', 'src/a.py', commits=[sha])                                 # repo-relative: matches api/src/a.py
        self.assertEqual(mismatches(sub.build()[1]), [])
        sub.set_declared('W1-T1', './api/src/a.py', commits=[sha])
        self.assertEqual(mismatches(sub.build()[1]), [])
        sub.set_declared('W1-T1', 'src/ghost.py', commits=[sha])                             # no folder resolves it: both ways
        self.assertEqual(mismatches(sub.build()[1]), [('changed_not_declared', 'api/src/a.py'), ('declared_not_changed', 'src/ghost.py')])

    def test_write_outputs_is_atomic(self):
        m = Workspace(self).build()[1]
        mod = load_module()
        out = Path(tempfile.mkdtemp(prefix='change-map-out-'))
        self.addCleanup(shutil.rmtree, out)
        target = out / 'change-map.json'
        target.write_text('old', encoding='utf-8')
        with mock.patch('os.replace', side_effect=OSError('boom')):
            with self.assertRaises(OSError):
                mod.write_outputs(m, str(target))
        self.assertEqual(target.read_text(encoding='utf-8'), 'old')
        self.assertEqual(sorted(p.name for p in out.iterdir()), ['change-map.json'])
        mod.write_outputs(m, str(target))
        self.assertEqual(json.loads(target.read_text(encoding='utf-8'))['schema_version'], 1)
        self.assertEqual(sorted(p.name for p in out.iterdir()), ['change-map.json', 'change-map.md'])

    def test_requirements_url_and_continuation_lines(self):  # FX-R2-RS N1
        mod = load_module()
        text = ('git+https://x.example/a.git#egg=liba\n'
                'git+https://x.example/b.git#egg=libb\n'
                'https://x.example/pkg-1.0.tar.gz\n'
                'requests==2.31.0 \\\n')
        self.assertEqual(mod.parse_deps('requirements.txt', text), {'liba': '', 'libb': '', 'requests': '==2.31.0'})



class LayoutTests(unittest.TestCase):
    """where change-map.py writes (change-map.md in the change folder, change-map.json under .cm-tmp), what it reads for AC lookups and what it ignores once docs live in docs/changes/"""

    def test_a_docs_changes_plan_gets_its_md_in_its_folder_and_json_in_cm_tmp(self):
        w = Workspace(self, where='docs/changes/demo-marked')
        p, m = w.build()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(m['kind'], 'plan')
        self.assertTrue((w.plan / 'change-map.md').is_file())
        self.assertFalse((w.plan / 'change-map.json').exists())
        self.assertTrue((ephemeral_dir(w.root, 'demo-marked') / 'change-map.json').is_file())
        self.assertFalse((w.root / 'docs/plan').exists())

    def test_a_second_run_rewrites_the_md_and_the_cm_tmp_json(self):
        w = Workspace(self, where='docs/changes/demo-marked')
        first = w.build()[1]
        second = w.build()[1]
        first.pop('generated_at')
        second.pop('generated_at')
        self.assertEqual(first, second)
        self.assertEqual(sorted(x.name for x in w.plan.iterdir() if x.name.startswith('change-map')), ['change-map.md'])
        self.assertEqual(sorted(x.name for x in ephemeral_dir(w.root, 'demo-marked').iterdir()), ['change-map.json'])
        self.assertFalse((w.root / 'docs/plan').exists())

    def test_a_fixed_set_plan_with_inline_tasks_builds_the_same_map(self):
        w = Workspace(self, where='docs/changes/demo-marked')
        task = yaml.safe_load((w.plan / 'tasks/W1/W1-T1.yaml').read_text(encoding='utf-8'))
        idx = yaml.safe_load((w.plan / 'plan.yaml').read_text(encoding='utf-8'))
        idx['tasks'] = [dict(task, wave='W1', depends_on=[])]
        shutil.rmtree(w.plan / 'tasks')
        (w.plan / 'plan.yaml').write_text(yaml.safe_dump(idx, allow_unicode=True, sort_keys=False), encoding='utf-8')
        p, m = w.build()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual((m['kind'], [t['id'] for t in m['tasks']], mismatches(m)), ('plan', ['W1-T1'], []))
        self.assertTrue((w.plan / 'change-map.md').is_file())

    def test_a_legacy_tasks_folder_plan_builds_a_clean_map(self):
        w = Workspace(self, where='docs/specs/changes/demo-marked')
        self.assertTrue((w.plan / 'tasks/W1/W1-T1.yaml').is_file())
        p, m = w.build()
        self.assertEqual((p.returncode, [t['id'] for t in m['tasks']], mismatches(m)), (0, ['W1-T1'], []))

    def test_read_specs_also_walks_docs_changes_specs(self):
        mod = load_module()
        root = Path(tempfile.mkdtemp(prefix='change-map-specs-'))
        self.addCleanup(shutil.rmtree, root)
        self.assertIsNone(mod.read_specs(str(root)))
        put = root / 'docs/changes/x/specs/uc/spec.md'
        put.parent.mkdir(parents=True)
        put.write_text('UC-9 AC-1\n', encoding='utf-8')
        self.assertEqual(mod.read_specs(str(root)), ['UC-9 AC-1\n'])

    def test_adhoc_map_goes_to_docs_changes_adhoc_date_slug(self):
        w = Workspace(self)
        rec = w.root / 'docs/changes/adhoc/2026-10-27-demo-fix/record.md'
        rec.parent.mkdir(parents=True)
        shutil.copy(FIX / 'adhoc-record.md', rec)
        p = run('--adhoc', str(rec), '--workspace-root', str(w.root))
        self.assertEqual(p.returncode, 0, p.stderr)
        folder = w.root / 'docs/changes/adhoc/2026-10-27-demo-fix'
        self.assertEqual(sorted(x.name for x in folder.iterdir()), ['change-map.md', 'record.md'])
        out = ephemeral_dir(w.root, '2026-10-27-demo-fix') / 'change-map.json'
        self.assertEqual(json.loads(out.read_text(encoding='utf-8'))['kind'], 'adhoc')

    def test_an_adhoc_record_without_a_date_exits_2_and_writes_nothing(self):
        w = Workspace(self)
        rec = w.root / 'docs/changes/adhoc/x/record.md'
        rec.parent.mkdir(parents=True)
        rec.write_text((FIX / 'adhoc-record.md').read_text(encoding='utf-8').replace('date: "2026-10-27"\n', ''), encoding='utf-8')
        p = run('--adhoc', str(rec), '--workspace-root', str(w.root))
        self.assertEqual(p.returncode, 2)
        self.assertIn('cannot load', p.stderr)
        self.assertEqual(sorted(x.name for x in rec.parent.iterdir()), ['record.md'])

    def test_a_legacy_plan_with_an_old_sidecar_gets_nothing_new_there(self):  # legacy is read, never written
        w = Workspace(self, where='docs/specs/changes/demo-marked')
        old = w.root / 'docs/plan/demo-marked'
        old.mkdir(parents=True)
        p = run('--plan', str(w.plan), '--workspace-root', str(w.root))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(list(old.iterdir()), [])
        self.assertTrue((w.plan / 'change-map.md').is_file())
        self.assertFalse((w.plan / 'change-map.json').exists())
        self.assertTrue((ephemeral_dir(w.root, 'demo-marked') / 'change-map.json').is_file())

    def test_a_legacy_plan_without_a_sidecar_gets_its_md_in_its_plan_folder(self):
        w = Workspace(self, where='docs/specs/changes/demo-marked')
        p, m = w.build()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue((w.plan / 'change-map.md').is_file())
        self.assertFalse((w.plan / 'change-map.json').exists())
        self.assertFalse((w.root / 'docs/plan').exists())

    def test_change_folder_files_are_not_code_changes_and_a_back_root_warns_once(self):
        w = Workspace(self, files=('src/app.py', 'docs/changes/MIGRATION-MAP.tsv', 'docs/changes/x/notes.md', 'docs/brainstorm/y.md'))
        p, m = w.build()
        self.assertEqual((p.returncode, mismatches(m)), (0, []))
        self.assertEqual(p.stderr.count('WARN'), 1)
        self.assertIn('docs/plan', p.stderr)

    def test_no_warn_without_a_migration_map(self):
        p = Workspace(self).build()[0]
        self.assertEqual((p.returncode, p.stderr), (0, ''))


if __name__ == '__main__':
    unittest.main()
