"""Tests for scripts/plan_paths.py and scripts/plan-locate.py: today's search order first (characterization), then the docs/changes roots."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / 'plugins' / 'agent-hub'
SCRIPTS = PLUGIN / 'scripts'
spec = importlib.util.spec_from_file_location('plan_locate', SCRIPTS / 'plan-locate.py')
PL = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PL)   # a hyphenated file name: loaded by path


def put(root, rel, text='x\n'):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')
    return p


def plan(root, folder, pid):
    put(root, f'{folder}/plan.yaml', f'plan_id: {pid}\n')


class RootCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='plan-paths-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()


class LegacyOrderTests(RootCase):
    """characterization: these pass on the unchanged code and stay green through the change"""

    def test_each_legacy_location_resolves_to_its_folder(self):
        """docs/plan/p1, docs/specs/changes/p2, docs/specs/changes/archive/p3 and archive/2026-01-02-p4 each resolve; change_dir is None for docs/plan and the folder itself under docs/specs/changes"""
        for folder, pid, is_change in (('docs/plan/p1', 'p1', False), ('docs/specs/changes/p2', 'p2', True),
                                       ('docs/specs/changes/archive/p3', 'p3', True), ('docs/specs/changes/archive/2026-01-02-p4', 'p4', True)):
            with self.subTest(folder=folder):
                plan(self.root, folder, pid)
                got = PL.locate(self.root, pid)
                self.assertEqual(got['plan_dir'], str(self.root / folder))
                self.assertEqual(got['plan_ref'], str(self.root / folder / 'plan.yaml'))
                self.assertEqual(got['change_dir'], str(self.root / folder) if is_change else None)
                self.assertIsNone(got['analysis_ref'])

    def test_zero_two_bad_id_and_mismatch_raise_as_today(self):
        """found 0 -> 'p5: expected one plan, found 0: []'; docs/plan/p6 plus docs/specs/changes/p6 -> 'found 2'; 'Bad_ID' -> 'plan id must be lowercase kebab-case'; plan_id other -> 'does not match'"""
        with self.assertRaisesRegex(ValueError, r'^p5: expected one plan, found 0: \[\]$'):
            PL.locate(self.root, 'p5')
        plan(self.root, 'docs/plan/p6', 'p6')
        plan(self.root, 'docs/specs/changes/p6', 'p6')
        with self.assertRaisesRegex(ValueError, r'^p6: expected one plan, found 2: '):
            PL.locate(self.root, 'p6')
        with self.assertRaisesRegex(ValueError, 'plan id must be lowercase kebab-case'):
            PL.locate(self.root, 'Bad_ID')
        plan(self.root, 'docs/plan/p7', 'other')
        with self.assertRaisesRegex(ValueError, 'plan_id does not match p7'):
            PL.locate(self.root, 'p7')

    def test_records_design_yaml_analysis_yaml_and_both(self):
        """design.yaml in the plan folder or docs/analysis/<id>.yaml is the analysis_ref (+ '#change_design' on change_design_ref); both present -> 'multiple machine records'"""  # scrub-allow: fixture
        plan(self.root, 'docs/specs/changes/r1', 'r1')
        put(self.root, 'docs/specs/changes/r1/design.yaml')
        got = PL.locate(self.root, 'r1')
        self.assertEqual(got['analysis_ref'], str(self.root / 'docs/specs/changes/r1/design.yaml'))
        self.assertEqual(got['change_design_ref'], got['analysis_ref'] + '#change_design')
        plan(self.root, 'docs/plan/r2', 'r2')
        put(self.root, 'docs/analysis/r2.yaml')  # scrub-allow: fixture
        self.assertEqual(PL.locate(self.root, 'r2')['analysis_ref'], str(self.root / 'docs/analysis/r2.yaml'))  # scrub-allow: fixture
        put(self.root, 'docs/specs/changes/r1/design.yaml')
        put(self.root, 'docs/analysis/r1.yaml')  # scrub-allow: fixture
        with self.assertRaisesRegex(ValueError, 'r1: multiple machine records'):
            PL.locate(self.root, 'r1')

    def test_cli_prints_json_and_exits_1_with_the_error_on_stderr(self):
        """plan-locate.py --workspace ROOT p1 prints the JSON and exits 0; an unknown id prints 'plan-locate: ...' on stderr and exits 1"""
        plan(self.root, 'docs/plan/c1', 'c1')
        ok = subprocess.run([sys.executable, str(SCRIPTS / 'plan-locate.py'), '--workspace', str(self.root), 'c1'], capture_output=True, text=True)
        self.assertEqual((ok.returncode, json.loads(ok.stdout)['plan_id']), (0, 'c1'))
        bad = subprocess.run([sys.executable, str(SCRIPTS / 'plan-locate.py'), '--workspace', str(self.root), 'nope'], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertTrue(bad.stderr.startswith('plan-locate: nope: expected one plan, found 0'))


spec = importlib.util.spec_from_file_location('plan_paths', SCRIPTS / 'plan_paths.py')
PP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PP)


def write_map(root, rows):
    put(root, 'docs/changes/MIGRATION-MAP.tsv', 'old_path\tnew_path\taction\n' + ''.join('\t'.join(r) + '\n' for r in rows))


class NewRootTests(RootCase):
    def test_plan_dir_searches_docs_changes_then_the_legacy_four(self):
        """docs/changes/n1, docs/changes/archive/n2, docs/changes/archive/2026-01-02-n3 and legacy docs/plan/n4 each resolve to their folder"""
        for folder, pid in (('docs/changes/n1', 'n1'), ('docs/changes/archive/n2', 'n2'),
                            ('docs/changes/archive/2026-01-02-n3', 'n3'), ('docs/plan/n4', 'n4')):
            with self.subTest(folder=folder):
                plan(self.root, folder, pid)
                self.assertEqual(PP.plan_dir(self.root, pid), self.root / folder)

    def test_two_folders_holding_plan_yaml_for_one_id_raise(self):
        """docs/changes/n5 and docs/plan/n5 both holding plan.yaml -> ValueError 'n5: expected one plan, found 2'"""
        plan(self.root, 'docs/changes/n5', 'n5')
        plan(self.root, 'docs/plan/n5', 'n5')
        with self.assertRaisesRegex(ValueError, r'^n5: expected one plan, found 2: '):
            PP.plan_dir(self.root, 'n5')

    def test_change_dir_returns_a_folder_without_plan_yaml(self):
        """docs/changes/n6/ holding only proposal.md: plan_dir raises 'found 0', change_dir returns the folder; an unknown id gives None"""
        put(self.root, 'docs/changes/n6/proposal.md')
        with self.assertRaisesRegex(ValueError, 'n6: expected one plan, found 0'):
            PP.plan_dir(self.root, 'n6')
        self.assertEqual(PP.change_dir(self.root, 'n6'), self.root / 'docs/changes/n6')
        self.assertIsNone(PP.change_dir(self.root, 'absent'))

    def test_locate_reports_change_dir_for_a_docs_changes_plan(self):
        """plan-locate on docs/changes/n8 returns change_dir equal to plan_dir"""
        plan(self.root, 'docs/changes/n8', 'n8')
        got = PL.locate(self.root, 'n8')
        self.assertEqual((got['plan_dir'], got['change_dir']), (str(self.root / 'docs/changes/n8'),) * 2)

    def test_record_order_design_yaml_id_yaml_analysis_brainstorm(self):
        """record() returns the one present of {plan_dir}/design.yaml, {plan_dir}/{id}.yaml, docs/analysis/{id}.yaml, docs/brainstorm/{id}.yaml, None when none"""  # scrub-allow: fixture
        folder = self.root / 'docs/changes/n7'
        plan(self.root, 'docs/changes/n7', 'n7')
        self.assertIsNone(PP.record(folder, self.root, 'n7'))
        for rel in ('docs/changes/n7/design.yaml', 'docs/changes/n7/n7.yaml', 'docs/analysis/n7.yaml', 'docs/brainstorm/n7.yaml'):  # scrub-allow: fixture
            with self.subTest(rel=rel):
                p = put(self.root, rel)
                self.assertEqual(PP.record(folder, self.root, 'n7'), p)
                p.unlink()

    def test_two_records_raise_as_today(self):
        """{plan_dir}/design.yaml plus docs/analysis/n9.yaml -> ValueError 'n9: multiple machine records'"""  # scrub-allow: fixture
        plan(self.root, 'docs/changes/n9', 'n9')
        put(self.root, 'docs/changes/n9/design.yaml')
        put(self.root, 'docs/analysis/n9.yaml')  # scrub-allow: fixture
        with self.assertRaisesRegex(ValueError, 'n9: multiple machine records'):
            PP.record(self.root / 'docs/changes/n9', self.root, 'n9')

    def test_resolve_exact_row_folder_prefix_and_longest_prefix(self):
        """an exact row -> its new_path; a file under a folder row -> new_path + the rest; the longest folder row wins; an absolute path under the root is made relative first"""
        write_map(self.root, [('docs/plan/a/plan.yaml', 'docs/changes/a/plan.yaml', 'moved'),
                              ('docs/plan/legacy/', 'docs/changes/legacy/', 'moved'),
                              ('docs/plan/legacy/sub/', 'docs/changes/elsewhere/', 'moved')])
        self.assertEqual(PP.resolve(self.root, 'docs/plan/a/plan.yaml'), 'docs/changes/a/plan.yaml')
        self.assertEqual(PP.resolve(self.root, str(self.root / 'docs/plan/a/plan.yaml')), 'docs/changes/a/plan.yaml')
        self.assertEqual(PP.resolve(self.root, 'docs/plan/legacy/x/f.md'), 'docs/changes/legacy/x/f.md')
        self.assertEqual(PP.resolve(self.root, 'docs/plan/legacy/sub/f.md'), 'docs/changes/elsewhere/f.md')

    def test_resolve_unmapped_deleted_and_no_map_give_none(self):
        """an unmapped path, a path under a folder whose new_path is '-' (deleted) and a workspace with no MIGRATION-MAP.tsv all give None"""
        self.assertIsNone(PP.resolve(self.root, 'docs/plan/a/plan.yaml'))
        write_map(self.root, [('docs/test-evidence/', '-', 'deleted-not-backed-up')])
        self.assertIsNone(PP.resolve(self.root, 'docs/plan/zzz/f.md'))
        self.assertIsNone(PP.resolve(self.root, 'docs/test-evidence/e.png'))

    def test_plan_locate_resolve_cli(self):
        """--resolve PATH prints the mapped path and exits 0 (an exact row and a file under a folder row); an unmapped path prints 'plan-locate: ...' on stderr and exits 1"""
        write_map(self.root, [('docs/plan/a/plan.yaml', 'docs/changes/a/plan.yaml', 'moved'), ('docs/plan/legacy/', 'docs/changes/legacy/', 'moved')])
        run = lambda p: subprocess.run([sys.executable, str(SCRIPTS / 'plan-locate.py'), '--workspace', str(self.root), '--resolve', p], capture_output=True, text=True)
        for old, new in (('docs/plan/a/plan.yaml', 'docs/changes/a/plan.yaml'), ('docs/plan/legacy/f.md', 'docs/changes/legacy/f.md')):
            r = run(old)
            self.assertEqual((r.returncode, r.stdout.strip()), (0, new))
        bad = run('docs/plan/zzz/f.md')
        self.assertEqual(bad.returncode, 1)
        self.assertTrue(bad.stderr.startswith('plan-locate: '))

    def test_legacy_roots_reappeared_needs_the_map(self):
        """with docs/changes/MIGRATION-MAP.tsv a recreated docs/plan and docs/reviews/adhoc are listed in the order docs/plan, docs/reviews/adhoc; without the map nothing is listed"""
        (self.root / 'docs/plan/x').mkdir(parents=True)
        (self.root / 'docs/reviews/adhoc').mkdir(parents=True)
        self.assertEqual(PP.legacy_roots_reappeared(self.root), [])
        write_map(self.root, [])
        self.assertEqual(PP.legacy_roots_reappeared(self.root), ['docs/plan', 'docs/reviews/adhoc'])

    def test_kept_files_under_a_legacy_root_are_not_a_reappearance(self):
        """in a workspace named example-workspace the 5 U20 files under docs/design are KEEP_IN_PLACE, so docs/design is not a reappeared root; one more file there is; the same 5 files in another workspace are"""
        kept = ('00_DESIGN_PIXEL_SOT_FINAL_v1.0.md', '01_SCREEN_MAP_WF01_WF03_FINAL_v1.0.md', 'DESIGN_TOKENS_v1.0.css',
                'SCREEN_CONTRACTS_WF01_WF03_v1.0.yaml', 'WF04_EXTERNAL_REFERENCE.md')
        field = self.root / 'example-workspace'
        other = self.root / 'other'
        for ws in (field, other):
            write_map(ws, [])
            for name in kept:
                put(ws, f'docs/design/{name}')
        with mock.patch.dict(PP.KEEP_IN_PLACE, {'example-workspace': tuple(f'docs/design/{n}' for n in kept)}):
            self.assertEqual(PP.legacy_roots_reappeared(field), [])
            self.assertEqual(PP.legacy_roots_reappeared(other), ['docs/design'])
            put(field, 'docs/design/x.md')
            self.assertEqual(PP.legacy_roots_reappeared(field), ['docs/design'])

    def test_sidecar_dir_is_docs_plan_only_for_a_specs_changes_plan_that_has_one(self):
        """a docs/specs/changes plan (archive included) whose docs/plan/{id}/ exists -> that folder; a docs/specs/changes plan without it, a docs/changes plan and a docs/plan plan -> plan_dir itself, even when docs/plan/{id}/ exists beside a docs/changes plan"""
        plan(self.root, 'docs/specs/changes/s1', 's1')
        (self.root / 'docs/plan/s1').mkdir(parents=True)
        self.assertEqual(PP.sidecar_dir(self.root, 's1'), self.root / 'docs/plan/s1')
        plan(self.root, 'docs/specs/changes/archive/2026-01-02-s5', 's5')
        (self.root / 'docs/plan/s5').mkdir(parents=True)
        self.assertEqual(PP.sidecar_dir(self.root, 's5'), self.root / 'docs/plan/s5')
        plan(self.root, 'docs/specs/changes/s2', 's2')
        self.assertEqual(PP.sidecar_dir(self.root, 's2'), self.root / 'docs/specs/changes/s2')
        plan(self.root, 'docs/changes/s3', 's3')
        (self.root / 'docs/plan/s3').mkdir(parents=True)
        self.assertEqual(PP.sidecar_dir(self.root, 's3'), self.root / 'docs/changes/s3')
        plan(self.root, 'docs/plan/s4', 's4')
        self.assertEqual(PP.sidecar_dir(self.root, 's4'), self.root / 'docs/plan/s4')
        self.assertFalse((self.root / 'docs/plan/s2').exists())


class FixedSetNamesTests(RootCase):
    """the fixed run-file names, the .cm-tmp folder of a plan and the two task layouts"""

    def test_the_fixed_names_and_the_ephemeral_folder(self):  # throwaway output has one home
        self.assertEqual((PP.CHANGE_MAP_MD, PP.REVIEW_FILE, PP.EVIDENCE_DIR, PP.EPHEMERAL_DIR),
                         ('change-map.md', 'review.md', 'evidence', '.cm-tmp'))
        self.assertEqual(PP.ephemeral_dir(self.root, 'demo'), self.root / '.cm-tmp' / 'demo')
        self.assertFalse((self.root / '.cm-tmp').exists())   # building the path creates nothing

    def test_inline_tasks_are_read_without_a_tasks_folder(self):
        folder = self.root / 'docs/changes/demo'
        folder.mkdir(parents=True)
        idx = {'tasks': [{'id': 'T1', 'title': 'one'}]}
        got = PP.tasks_of(folder, idx, lambda path: self.fail(f'read {path}'))
        self.assertEqual(got, [{'id': 'T1', 'title': 'one'}])
        got[0]['title'] = 'changed'
        self.assertEqual(idx['tasks'][0]['title'], 'one')   # a copy is returned

    def test_a_tasks_folder_plan_reads_its_task_files(self):
        folder = self.root / 'docs/specs/changes/demo'
        put(self.root, 'docs/specs/changes/demo/tasks/W1/T1.yaml')
        seen = []
        got = PP.tasks_of(folder, {'tasks': [{'id': 'T1', 'file': 'tasks/W1/T1.yaml'}]}, lambda path: seen.append(path) or {'id': 'T1'})
        self.assertEqual(got, [{'id': 'T1'}])
        self.assertEqual(seen, [str(folder / 'tasks/W1/T1.yaml')])


if __name__ == '__main__':
    unittest.main()
