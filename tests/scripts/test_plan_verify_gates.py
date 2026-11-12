"""Tests for the plan gates of scripts/plan-verify.py: the approval stamp and fingerprint, template placeholders,
layers, ac_check results and affected surfaces. Each case builds a tiny plan in a temp workspace and runs the CLI on it."""
import copy
import datetime
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

PLUGIN = Path(__file__).resolve().parents[2] / 'plugins' / 'agent-hub'
SCRIPTS = PLUGIN / 'scripts'
SCRIPT = SCRIPTS / 'plan-verify.py'
HOME = PLUGIN
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('plan_verify', SCRIPT)
PV = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PV)
LINE = re.compile(r'^(PASS|FAIL|WARN)  (\w+)\s+(.*)$')
WORDS = 'user: approve the fixture plan, verbatim'


def put(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def dump(path, data):
    put(path, yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def base_task():
    return {
        'id': 'T1', 'title': 'Count the retries per request', 'what': 'Count retries.', 'purpose': 'Retries are invisible.',
        'files': [{'path': 'src/app.py', 'change': 'edit', 'why': 'the counter lives here'}],
        'solution': 'Add a counter to the request loop.',
        'steps': [{'n': 1, 'file': 'src/app.py', 'action': 'edit', 'anchor': 'the loop', 'before': 'x = 1', 'after': 'x = 2',
                   'expect': None, 'why': 'count', 'done': False}],
        'status': 'pending', 'blocker': None, 'covers_uc': None,
        'acceptance_criteria': ['AC-1: the counter increments', 'AC-2: the counter resets'],
        'test_cases': [{'id': 'TC-T1-1', 'covers_acceptance': 'T1/AC-1', 'layer': 'integration'},
                       {'id': 'TC-T1-2', 'covers_acceptance': 'T1/AC-2', 'layer': 'integration'}],
        'subtasks': [], 'result': None,
    }


class Fixture:
    """root/<where> (default docs/plan/demo) with one task T1 in wave W1; the CLI runs with --root on the temp workspace"""

    def __init__(self, case, plan_extra=None, task_extra=None, where='docs/plan/demo'):
        self.tmp = tempfile.TemporaryDirectory(prefix='pv-gates-')
        case.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.plan = self.root / where
        index = {'plan_id': 'demo', 'objective': 'A fixture plan for the gate tests', 'waves': [{'id': 'W1', 'name': 'one'}],
                 'tasks': [{'id': 'T1', 'wave': 'W1', 'file': 'tasks/W1/T1.yaml', 'depends_on': []}]}
        index.update(plan_extra or {})
        dump(self.plan / 'plan.yaml', index)
        task = base_task()
        task.update(task_extra or {})
        dump(self.plan / 'tasks/W1/T1.yaml', task)

    def edit_task(self, fn):
        p = self.plan / 'tasks/W1/T1.yaml'
        t = yaml.safe_load(p.read_text(encoding='utf-8'))
        fn(t)
        dump(p, t)

    def verify(self, *extra):
        p = subprocess.run([sys.executable, str(SCRIPT), str(self.plan), '--root', str(self.root), *extra],
                           capture_output=True, text=True, env=dict(os.environ, PLAN_VERIFY_SKIP_MIRROR=os.environ.get('PLAN_VERIFY_SKIP_MIRROR', '1')))
        found = {}
        for line in p.stdout.splitlines():
            m = LINE.match(line)
            if m:
                found[m.group(2)] = (m.group(1), m.group(3))
        return p.returncode, found, p.stdout

    def approve(self, words=WORDS):
        return self.verify('--approve', words)

    def approval(self):
        return yaml.safe_load((self.plan / 'plan.yaml').read_text(encoding='utf-8'))['approval']


class ApprovalTests(unittest.TestCase):
    def test_approve_then_edit_fails(self):
        f = Fixture(self)
        _, got, _ = f.approve()
        self.assertEqual(got['approval'][0], 'PASS')
        self.assertIn('approved, fingerprint', got['approval'][1])
        f.edit_task(lambda t: t.update(solution='A different approach to the loop.'))
        _, got, _ = f.verify()
        self.assertEqual(got['approval'][0], 'FAIL')
        self.assertIn('changed after approval', got['approval'][1])

    def test_exec_only_edit_keeps_fingerprint(self):
        f = Fixture(self)
        f.approve()
        before = f.approval()['fingerprint']

        def run_it(t):
            t['status'] = 'reviewing'
            t['blocker'] = None
            t['steps'][0]['done'] = True
            t['result'] = {'summary': 'done', 'commands': [], 'ac_check': []}
        f.edit_task(run_it)
        _, got, _ = f.verify()
        self.assertEqual(got['approval'][0], 'PASS')
        self.assertIn('approved', got['approval'][1])
        self.assertEqual(f.approval()['fingerprint'], before)

    def test_no_approval_block_passes(self):
        _, got, _ = Fixture(self).verify()
        self.assertEqual(got['approval'], ('PASS', 'no approval block: not yet approved'))

    def test_approval_block_without_fingerprint_fails(self):
        f = Fixture(self)
        with open(f.plan / 'plan.yaml', 'a', encoding='utf-8') as fh:
            fh.write('approval:\n  by: "someone"\n')
        _, got, _ = f.verify()
        self.assertEqual(got['approval'][0], 'FAIL')
        self.assertIn('no fingerprint', got['approval'][1])

    def test_empty_words_are_refused(self):
        rc, _, out = Fixture(self).approve('   ')
        self.assertEqual(rc, 2)
        self.assertIn('plan-verify:', out)

    def test_stamp_writes_at_beside_the_other_keys(self):
        f = Fixture(self)
        PV.stamp_approval(str(f.plan), WORDS)
        ap = f.approval()
        self.assertTrue({'by', 'fingerprint', 'spec_fingerprint', 'at'} <= set(ap), sorted(ap))
        self.assertEqual(ap['by'], WORDS)
        self.assertIsNone(ap['spec_fingerprint'])
        at = datetime.datetime.fromisoformat(str(ap['at']))
        self.assertIsNotNone(at.utcoffset(), 'approval.at carries a UTC offset')
        self.assertLess(abs((datetime.datetime.now(datetime.timezone.utc) - at).total_seconds()), 120)

    def test_stamp_goes_through_os_replace_and_leaves_no_stray_file(self):
        f = Fixture(self)
        with mock.patch.object(PV.os, 'replace', wraps=os.replace) as rep:
            PV.stamp_approval(str(f.plan), WORDS)
        self.assertEqual(rep.call_count, 1)
        self.assertEqual(os.fspath(rep.call_args[0][1]), str(f.plan / 'plan.yaml'))
        self.assertEqual(sorted(p.name for p in f.plan.iterdir()), ['plan.yaml', 'tasks'])

    def test_stamping_twice_replaces_the_block(self):
        f = Fixture(self)
        PV.stamp_approval(str(f.plan), WORDS)
        first = str(f.approval()['at'])
        PV.stamp_approval(str(f.plan), 'user: approve again, verbatim')
        text = (f.plan / 'plan.yaml').read_text(encoding='utf-8')
        self.assertEqual(len(re.findall(r'^approval:', text, re.M)), 1)
        self.assertEqual(f.approval()['by'], 'user: approve again, verbatim')
        self.assertGreaterEqual(str(f.approval()['at']), first)
        self.assertEqual(f.verify()[1]['approval'][0], 'PASS')


class SpecFingerprintTests(unittest.TestCase):
    def fixture(self, uc='UC-901'):
        f = Fixture(self, task_extra={'covers_uc': [uc]})
        put(f.root / 'docs/specs/use-cases/demo/UC-901-demo.md', '# UC-901 Demo\n\n## AC-1\nGiven a request, then it is counted.\n')
        return f

    def test_uc_edit_before_the_last_wave_fails_naming_the_path(self):
        f = self.fixture()
        f.approve()
        self.assertIsInstance(f.approval()['spec_fingerprint'], str)
        put(f.root / 'docs/specs/use-cases/demo/UC-901-demo.md', '# UC-901 Demo\n\n## AC-1\nGiven a request, then it is counted twice.\n')
        _, got, _ = f.verify()
        self.assertEqual(got['approval'][0], 'FAIL')
        self.assertIn('UC-901-demo.md', got['approval'][1])

    def test_uc_edit_after_the_last_wave_passes(self):
        f = self.fixture()
        f.approve()
        put(f.root / 'docs/specs/use-cases/demo/UC-901-demo.md', '# UC-901 Demo\n\n## AC-1\nGiven a request, then it is counted twice.\n')
        f.edit_task(lambda t: t.update(status='reviewing'))
        _, got, _ = f.verify()
        self.assertEqual(got['approval'][0], 'PASS')
        self.assertIn('spec part not checked', got['approval'][1])

    def test_uc_edit_while_a_task_is_back_at_re_implement_fails(self):
        f = self.fixture()
        f.approve()
        put(f.root / 'docs/specs/use-cases/demo/UC-901-demo.md', '# UC-901 Demo\n\n## AC-1\nGiven a request, then it is counted twice.\n')
        f.edit_task(lambda t: t.update(status='re_implement'))
        _, got, _ = f.verify()
        self.assertEqual(got['approval'][0], 'FAIL')
        self.assertIn('UC-901-demo.md', got['approval'][1])

    def test_uc_id_with_no_file_does_not_raise(self):
        f = Fixture(self, task_extra={'covers_uc': ['UC-999']})
        _, got, _ = f.approve()
        self.assertEqual(got['approval'][0], 'PASS')
        self.assertNotIn('raised', got['approval'][1])


class PlaceholderTests(unittest.TestCase):
    TASK_TEMPLATE = yaml.safe_load((HOME / 'templates/plan/task-template.yaml').read_text(encoding='utf-8'))

    def test_task_title_copied_from_the_template_fails(self):
        f = Fixture(self, task_extra={'title': self.TASK_TEMPLATE['title']})
        _, got, _ = f.verify()
        self.assertEqual(got['placeholders'][0], 'FAIL')
        self.assertIn('T1 title', got['placeholders'][1])
        self.assertIn('templates/plan/task-template.yaml', got['placeholders'][1])

    def test_own_text_passes(self):
        self.assertEqual(Fixture(self).verify()[1]['placeholders'][0], 'PASS')

    def design_text(self, extra_line):
        tpl = (HOME / 'templates/analysis/design-template.md').read_text(encoding='utf-8').splitlines()
        heads = [l for l in tpl if l.startswith('## ')]
        return '# Design: demo\n\n' + '\n'.join(f'{h}\n{extra_line if i == 0 else "Our own words for this section."}\n' for i, h in enumerate(heads))

    def template_body_line(self):
        tpl = (HOME / 'templates/analysis/design-template.md').read_text(encoding='utf-8').splitlines()
        return next(l for l in tpl if l.strip() and not l.startswith('#'))

    def test_design_md_with_a_template_line_fails_naming_file_and_line(self):
        f = Fixture(self)
        put(f.root / 'docs/analysis/demo/design.md', self.design_text(self.template_body_line()))  # scrub-allow: fixture
        _, got, _ = f.verify()
        self.assertEqual(got['placeholders'][0], 'FAIL')
        self.assertRegex(got['placeholders'][1], r'design\.md:\d+')

    def test_design_md_with_only_headings_and_own_text_passes(self):
        f = Fixture(self)
        put(f.root / 'docs/analysis/demo/design.md', self.design_text('Our own words for the first section.'))  # scrub-allow: fixture
        self.assertEqual(f.verify()[1]['placeholders'][0], 'PASS')

    def result_guide(self):
        tpl = (HOME / 'templates/plan/plan.lang-template.md').read_text(encoding='utf-8').splitlines()
        start = next(i for i, l in enumerate(tpl) if l.startswith('<!-- **Result** —'))  # scrub-allow: fixture
        return tpl[start:next(i for i, l in enumerate(tpl) if '**Commit**' in l) + 1]

    def test_the_result_guide_copied_from_the_template_passes(self):
        f = Fixture(self)
        put(f.plan / 'plan.en.md', '# demo\n\n' + '\n'.join(self.result_guide()) + '\n')
        self.assertEqual(f.verify()[1]['placeholders'][0], 'PASS')

    def test_a_template_line_beside_the_guide_still_fails_naming_it(self):
        f = Fixture(self)
        guide = self.result_guide()
        tpl = (HOME / 'templates/plan/plan.lang-template.md').read_text(encoding='utf-8').splitlines()
        line = next(l for l in tpl if not l.lstrip().startswith('<!--') and PV.PLACEHOLDER.search(l))
        put(f.plan / 'plan.en.md', '# demo\n\n' + '\n'.join(guide + [line]) + '\n')
        got = f.verify()[1]['placeholders']
        self.assertEqual(got[0], 'FAIL')
        self.assertIn(f'plan.en.md:{len(guide) + 3}', got[1])


class LayersTests(unittest.TestCase):
    def layers_fixture(self, touches, cases, waivers=None):
        return Fixture(self, plan_extra={'test_schema': 'layers'},
                       task_extra={'touches': touches, 'layer_waivers': waivers or [],
                                   'test_cases': [{'id': f'TC-T1-{i}', 'covers_acceptance': 'T1/AC-1', 'layer': c}
                                                  for i, c in enumerate(cases, 1)]})

    def test_a_touch_with_no_case_of_its_layer_fails(self):
        _, got, _ = self.layers_fixture(['logic'], ['integration']).verify()
        self.assertEqual(got['layers'][0], 'FAIL')
        self.assertIn('touches logic needs a unit case', got['layers'][1])

    def test_the_layer_case_makes_it_pass(self):
        self.assertEqual(self.layers_fixture(['logic'], ['unit']).verify()[1]['layers'][0], 'PASS')

    def test_a_waiver_with_a_file_line_makes_it_pass(self):
        w = [{'layer': 'unit', 'reason': 'no pure logic here', 'evidence': 'src/app.py:3'}]
        self.assertEqual(self.layers_fixture(['logic'], ['integration'], w).verify()[1]['layers'][0], 'PASS')

    def test_a_waiver_without_a_file_line_fails(self):
        w = [{'layer': 'unit', 'reason': 'no pure logic here', 'evidence': 'somewhere'}]
        self.assertEqual(self.layers_fixture(['logic'], ['integration'], w).verify()[1]['layers'][0], 'FAIL')

    def test_a_case_still_carrying_type_fails(self):
        f = self.layers_fixture(['logic'], ['unit'])
        f.edit_task(lambda t: t['test_cases'][0].update(type='api'))
        _, got, _ = f.verify()
        self.assertEqual(got['layers'][0], 'FAIL')
        self.assertIn('carries type', got['layers'][1])

    def test_empty_touches_on_a_code_task_fails(self):
        _, got, _ = self.layers_fixture([], ['unit']).verify()
        self.assertEqual(got['layers'][0], 'FAIL')
        self.assertIn('touches is empty', got['layers'][1])

    def test_a_plan_without_test_schema_skips(self):
        self.assertIn('skipped', Fixture(self).verify()[1]['layers'][1])


class AcResultsTests(unittest.TestCase):
    def finished(self, entries, commands=None):
        cmds = [{'cmd': 'true', 'exit': 0, 'evidence_path': 'e', 'tc_id': 'TC-T1-1'},
                {'cmd': 'true', 'exit': 0, 'evidence_path': 'e', 'tc_id': 'TC-T1-2'}] if commands is None else commands
        return Fixture(self, plan_extra={'validation_strategy': {'ac_check_from': 'W1'}},
                       task_extra={'status': 'reviewing', 'result': {'summary': 's', 'commands': cmds, 'ac_check': entries}})

    @staticmethod
    def entry(ac, tc, met=True, evidence=('src/app.py:1',)):
        return {'ac': ac, 'met': met, 'evidence': list(evidence), 'tc_ids': [tc], 'note': 'n'}

    def test_a_complete_result_passes(self):
        f = self.finished([self.entry('AC-1', 'TC-T1-1'), self.entry('AC-2', 'TC-T1-2')])
        self.assertEqual(f.verify()[1]['ac_results'][0], 'PASS')

    def test_a_missing_ac_fails_naming_task_and_ac(self):
        _, got, _ = self.finished([self.entry('AC-1', 'TC-T1-1')]).verify()
        self.assertEqual(got['ac_results'][0], 'FAIL')
        self.assertIn('T1 AC-2: 0 ac_check entries, want exactly 1', got['ac_results'][1])

    def test_a_duplicate_ac_fails(self):
        _, got, _ = self.finished([self.entry('AC-1', 'TC-T1-1'), self.entry('AC-1', 'TC-T1-1'), self.entry('AC-2', 'TC-T1-2')]).verify()
        self.assertEqual(got['ac_results'][0], 'FAIL')
        self.assertIn('T1 AC-1: 2 ac_check entries, want exactly 1', got['ac_results'][1])

    def test_met_true_with_no_evidence_fails(self):
        _, got, _ = self.finished([self.entry('AC-1', 'TC-T1-1', evidence=()), self.entry('AC-2', 'TC-T1-2')]).verify()
        self.assertEqual(got['ac_results'][0], 'FAIL')
        self.assertIn('met true with no evidence', got['ac_results'][1])

    def test_a_non_zero_exit_row_fails(self):
        cmds = [{'cmd': 'true', 'exit': 1, 'evidence_path': 'e', 'tc_id': 'TC-T1-1'},
                {'cmd': 'true', 'exit': 0, 'evidence_path': 'e', 'tc_id': 'TC-T1-2'}]
        _, got, _ = self.finished([self.entry('AC-1', 'TC-T1-1'), self.entry('AC-2', 'TC-T1-2')], cmds).verify()
        self.assertEqual(got['ac_results'][0], 'FAIL')
        self.assertIn('non-zero exit', got['ac_results'][1])

    def test_a_red_row_then_a_green_row_passes(self):
        cmds = [{'cmd': 'true', 'exit': 1, 'evidence_path': 'e', 'tc_id': 'TC-T1-1'},
                {'cmd': 'true', 'exit': 0, 'evidence_path': 'e', 'tc_id': 'TC-T1-1'},
                {'cmd': 'true', 'exit': 0, 'evidence_path': 'e', 'tc_id': 'TC-T1-2'}]
        _, got, _ = self.finished([self.entry('AC-1', 'TC-T1-1'), self.entry('AC-2', 'TC-T1-2')], cmds).verify()
        self.assertEqual(got['ac_results'][0], 'PASS')

    def test_a_green_row_then_a_red_row_fails(self):
        cmds = [{'cmd': 'true', 'exit': 0, 'evidence_path': 'e', 'tc_id': 'TC-T1-1'},
                {'cmd': 'true', 'exit': 1, 'evidence_path': 'e', 'tc_id': 'TC-T1-1'},
                {'cmd': 'true', 'exit': 0, 'evidence_path': 'e', 'tc_id': 'TC-T1-2'}]
        _, got, _ = self.finished([self.entry('AC-1', 'TC-T1-1'), self.entry('AC-2', 'TC-T1-2')], cmds).verify()
        self.assertEqual(got['ac_results'][0], 'FAIL')
        self.assertIn('non-zero exit', got['ac_results'][1])

    def test_a_plan_without_ac_check_from_skips(self):
        f = Fixture(self, task_extra={'status': 'reviewing', 'result': {'summary': 's'}})
        self.assertIn('skipped', f.verify()[1]['ac_results'][1])


class SurfacesTests(unittest.TestCase):
    def test_unknown_task_id_fails(self):
        f = Fixture(self, plan_extra={'affected_surfaces': [{'id': 'S1', 'task_ids': ['T9']}]})
        _, got, _ = f.verify()
        self.assertEqual(got['surfaces'][0], 'FAIL')
        self.assertIn('T9', got['surfaces'][1])

    def test_no_task_and_no_reason_warns_and_passes(self):
        f = Fixture(self, plan_extra={'affected_surfaces': [{'id': 'S1', 'task_ids': []}]})
        _, got, _ = f.verify()
        self.assertEqual(got['surfaces'][0], 'PASS')
        self.assertIn('WARN', got['surfaces'][1])

    def test_n_a_string_passes_and_absence_skips(self):
        self.assertEqual(Fixture(self, plan_extra={'affected_surfaces': 'N/A: ruleset change'}).verify()[1]['surfaces'][0], 'PASS')
        self.assertIn('skipped', Fixture(self).verify()[1]['surfaces'][1])


class LogicTaskFieldsTests(unittest.TestCase):
    def check(self, **over):
        task = {'touches': ['logic'],
                'before_after': [{'aspect': 'retries', 'before': 'not counted', 'after': 'counted per request'}],
                'logic': ['1. count each retry'],
                'approach': {'chosen': 'a counter', 'why': 'cheapest', 'cost': 'one more field'},
                'alternatives_rejected': [{'option': 'a log scan', 'why_not': 'too slow'}]}
        task.update(over)
        return Fixture(self, task_extra=task).verify()[1]['logic_task_fields']

    def test_a_filled_logic_task_passes(self):
        self.assertEqual(self.check()[0], 'PASS')

    def test_missing_approach_cost_fails_naming_it(self):
        got = self.check(approach={'chosen': 'a counter', 'why': 'cheapest'})
        self.assertEqual(got[0], 'FAIL')
        self.assertIn('T1:approach.cost', got[1])

    def test_empty_alternatives_fails(self):
        got = self.check(alternatives_rejected=[])
        self.assertEqual(got[0], 'FAIL')
        self.assertIn('T1:alternatives_rejected', got[1])

    def test_none_because_passes(self):
        self.assertEqual(self.check(alternatives_rejected=[{'none_because': 'no other way reads the counter'}])[0], 'PASS')

    def test_a_shape_only_task_needs_none_of_the_keys(self):
        got = Fixture(self, task_extra={'touches': ['shape'], 'before_after': []}).verify()[1]['logic_task_fields']
        self.assertEqual(got[0], 'PASS')

    def test_a_closeout_task_is_exempt(self):
        got = Fixture(self, task_extra={'touches': ['logic'], 'owner': 'implement', 'before_after': []}).verify()[1]['logic_task_fields']
        self.assertEqual(got[0], 'PASS')

    def test_a_rule_with_an_empty_ac_fails_naming_it(self):
        got = self.check(user_visible_rules=[{'rule': 'a user sees X', 'ac': ''}])
        self.assertEqual(got[0], 'FAIL')
        self.assertIn('T1:user_visible_rules[0]', got[1])

    def test_a_plan_older_than_the_standard_is_skipped(self):
        got = Fixture(self, task_extra={'touches': ['logic']}).verify()[1]['logic_task_fields']
        self.assertEqual(got[0], 'PASS')
        self.assertIn('skipped: plan predates the task standard', got[1])

    def test_record_tasks_carrying_the_keys_open_the_gate(self):
        f = Fixture(self, task_extra={'touches': ['logic']})
        dump(f.root / 'docs/analysis/demo.yaml', {'plan_id': 'demo', 'change_design': {'plan': {'tasks': [  # scrub-allow: fixture
            {'id': 'T1', 'before_after': [{'aspect': 'a', 'before': 'b', 'after': 'c'}]}]}}})
        got = f.verify()[1]['logic_task_fields']
        self.assertEqual(got[0], 'FAIL')
        for key in ('T1:before_after', 'T1:logic', 'T1:approach.chosen', 'T1:alternatives_rejected'):
            self.assertIn(key, got[1])

    def design_line(self, extra):
        tmp = tempfile.TemporaryDirectory(prefix='pv-design-')
        self.addCleanup(tmp.cleanup)
        rec = Path(tmp.name) / 'docs/analysis/demo.yaml'  # scrub-allow: fixture
        dump(rec, {'plan_id': 'demo', 'change_design': {'plan': {'tasks': [dict(id='T1', touches=['logic'], **extra)]}}})
        out = subprocess.run([sys.executable, str(SCRIPT), str(rec), '--root', tmp.name], capture_output=True, text=True,
                             env=dict(os.environ, PLAN_VERIFY_SKIP_MIRROR=os.environ.get('PLAN_VERIFY_SKIP_MIRROR', '1'))).stdout
        return next(m.group(1, 3) for m in map(LINE.match, out.splitlines()) if m and m.group(2) == 'logic_task_fields')

    def test_a_design_record_is_always_checked(self):
        filled = {'before_after': [{'aspect': 'a', 'before': 'b', 'after': 'c'}], 'logic': ['1. one step'],
                  'approach': {'chosen': 'x', 'why': 'y', 'cost': 'z'}, 'alternatives_rejected': [{'none_because': 'nothing else reads it'}]}
        self.assertEqual(self.design_line({})[0], 'FAIL')
        self.assertEqual(self.design_line(filled)[0], 'PASS')

    def test_touches_that_is_not_a_list_fails_naming_it(self):
        rc, got, _ = Fixture(self, task_extra={'touches': 'logic', 'before_after': []}).verify()
        self.assertEqual(rc, 1)
        self.assertEqual(got['logic_task_fields'][0], 'FAIL')
        self.assertIn('T1:touches', got['logic_task_fields'][1])
        self.assertNotIn('raised', got['logic_task_fields'][1])

    def test_user_visible_rules_that_is_not_a_list_fails_without_a_traceback(self):
        for bad in ('x', 5):
            rc, got, out = Fixture(self, task_extra={'user_visible_rules': bad}).verify()
            self.assertEqual(rc, 1)
            self.assertEqual(got['logic_task_fields'][0], 'FAIL')
            self.assertIn('T1:user_visible_rules', got['logic_task_fields'][1])
            self.assertNotIn('raised', got['logic_task_fields'][1])
            self.assertNotIn('Traceback', out)

    def test_malformed_values_fail_without_crashing(self):
        got = self.check(before_after='none', logic=[''], approach='a counter', alternatives_rejected=[{'option': 'x'}])
        self.assertEqual(got[0], 'FAIL')
        for key in ('T1:before_after', 'T1:logic', 'T1:approach.chosen', 'T1:alternatives_rejected'):
            self.assertIn(key, got[1])


DI_KEYS = ('purpose', 'flow', 'ui', 'endpoints', 'db_schema', 'data_reads', 'data_writes', 'business_rules', 'access', 'events_jobs',
           'config', 'code_changes', 'risk_rollback')


class DataImpactTests(unittest.TestCase):
    """chk_data_impact: skip a plan without the marker, FAIL a done task without the record, WARN on a mismatch without blocking"""
    MARK = {'validation_strategy': {'change_record_standard': 1}}

    @staticmethod
    def done(drop=None, run=True):
        di = {k: 'none: không đổi' for k in DI_KEYS}  # scrub-allow: fixture
        di['flow'] = [{'step': 'tăng bộ đếm', 'where': 'src/app.py:1'}]  # scrub-allow: fixture
        di['risk_rollback'] = {'risks': [], 'rollback': 'git revert'}
        di.pop(drop, None)
        res = {'summary': 's', 'data_impact': di}
        if run:
            res['run'] = {'started_at': '2026-10-27T01:00:00Z', 'finished_at': '2026-10-27T01:05:00Z'}
        return {'status': 'done', 'result': res}

    def test_a_plan_without_the_marker_skips(self):
        got = Fixture(self, task_extra=self.done(drop='ui')).verify()[1]['data_impact']
        self.assertEqual(got[0], 'PASS')
        self.assertTrue(got[1].startswith('skipped: plan predates the change-record standard'))

    def test_a_missing_key_fails_naming_task_and_key(self):
        rc, got, _ = Fixture(self, plan_extra=self.MARK, task_extra=self.done(drop='ui')).verify()
        self.assertEqual((rc, got['data_impact'][0]), (1, 'FAIL'))
        self.assertIn('T1', got['data_impact'][1])
        self.assertIn("'ui'", got['data_impact'][1])

    def test_a_missing_run_window_fails(self):
        got = Fixture(self, plan_extra=self.MARK, task_extra=self.done(run=False)).verify()[1]['data_impact']
        self.assertEqual(got[0], 'FAIL')
        self.assertIn('run.started_at', got[1])

    def test_none_strings_lists_and_the_risk_object_pass(self):
        got = Fixture(self, plan_extra=self.MARK, task_extra=self.done()).verify()[1]['data_impact']
        self.assertEqual(got[0], 'PASS')

    def test_a_legacy_change_map_json_with_a_mismatch_warns_without_changing_the_exit(self):  # legacy read: a json beside the plan is still read
        f = Fixture(self, plan_extra=self.MARK, task_extra=self.done())
        rc0 = f.verify()[0]
        put(f.plan / 'change-map.json', '{"sections": {"mismatch": {"entries": [{"code": "record_missing", "task_id": "T1"}]}}}')
        rc1, got, out = f.verify()
        self.assertEqual((got['data_impact'][0], rc1), ('WARN', rc0))
        self.assertTrue(out.rstrip().endswith(', 1 warnings'))

    def test_the_summary_is_unchanged_without_a_warning(self):
        out = Fixture(self, plan_extra=self.MARK, task_extra=self.done()).verify()[2]
        self.assertRegex(out.rstrip().splitlines()[-1], r'^\d+/\d+ checks passed$')

    @staticmethod
    def committed(case, declared):
        """a Fixture whose workspace is a git repo with one commit of src/app.py; the done task carries that sha and declares `declared`"""
        f = Fixture(case, plan_extra=DataImpactTests.MARK, task_extra=DataImpactTests.done(), where='docs/changes/demo')
        git = ['git', '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false', '-C', str(f.root)]
        subprocess.run(['git', 'init', '-q', str(f.root)], check=True)
        put(f.root / 'src/app.py', 'x = 1\n')
        subprocess.run([*git, 'add', 'src/app.py'], check=True)
        subprocess.run([*git, 'commit', '-q', '-m', 'c'], check=True)
        sha = subprocess.run([*git, 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()

        def fn(t):
            t['result'].update(commits=[sha], files_changed=[{'path': p, 'note': 'n'} for p in declared])
            t['result']['data_impact']['code_changes'] = 'none: n'
        f.edit_task(fn)
        return f

    def test_a_missing_json_computes_the_map_in_memory_and_passes_when_the_declaration_matches(self):  # no json in the change folder
        f = self.committed(self, ['src/app.py'])
        rc, got, _ = f.verify()
        self.assertEqual(got['data_impact'][0], 'PASS')
        self.assertFalse((f.plan / 'change-map.json').exists())

    def test_a_missing_json_computes_the_map_in_memory_and_warns_on_a_declared_unchanged_file(self):  # the WARN-versus-PASS shift
        f = self.committed(self, ['src/app.py', 'src/ghost.py'])
        rc0 = self.committed(self, ['src/app.py']).verify()[0]
        rc1, got, out = f.verify()
        self.assertEqual((got['data_impact'][0], rc1), ('WARN', rc0))
        self.assertIn('src/ghost.py', got['data_impact'][1])
        self.assertFalse((f.plan / 'change-map.json').exists())

    def test_a_corrupt_legacy_change_map_json_warns_without_changing_the_exit(self):  # legacy read
        f = Fixture(self, plan_extra=self.MARK, task_extra=self.done())
        rc0 = f.verify()[0]
        put(f.plan / 'change-map.json', '{"sections": {"mismatch": {"entr')
        rc1, got, out = f.verify()
        self.assertEqual((got['data_impact'][0], rc1), ('WARN', rc0))
        self.assertIn('change-map.json unreadable', got['data_impact'][1])
        self.assertTrue(out.rstrip().endswith(', 1 warnings'))

    def test_design_mode_skips(self):
        ok, msg = PV.chk_data_impact({'mode': 'design'})
        self.assertTrue(ok)
        self.assertTrue(msg.startswith('skipped'))
        self.assertIn(PV.chk_data_impact, PV.CHECKS)


class CloseCriteriaTests(unittest.TestCase):
    """chk_close: opt-in by meta.close_criteria: 1 in errors.yaml; one valid and one violating case per rule (RULE-1 to RULE-5)"""

    @staticmethod
    def entry(eid, severity='major'):
        e = {'id': eid, 'source': 'reviewer-independent', 'text': 'finding'}
        if severity is not None:
            e['severity'] = severity
        return e

    @staticmethod
    def led(eid, **kw):
        d = {'id': eid, 'severity': 'minor', 'source': 'reviewer-independent', 'location': 'a.md:1', 'reason': 'minor', 'round': 1}
        d.update(kw)
        return d

    @staticmethod
    def rnd(n, entries=(), deferred=(), source='review-test', verdict='red'):
        return {'round': n, 'round_source': source, 'verdict': verdict, 'entries': list(entries),
                'analysis': {'groups': [], 'fix_list': [], 'deferred_errors': list(deferred)}}

    def close(self, rounds, loops=1, marker=1, task_extra=None):
        f = Fixture(self, task_extra=task_extra)
        meta = {'error_loop_count': loops}
        if marker is not None:
            meta['close_criteria'] = marker
        dump(f.plan / 'errors.yaml', {'meta': meta, 'errors': rounds})
        return f.verify()[1]['close']

    def test_no_errors_yaml_passes(self):
        got = Fixture(self).verify()[1]['close']
        self.assertEqual(got[0], 'PASS')
        self.assertIn('no errors.yaml', got[1])

    def test_no_marker_skips_even_with_an_untagged_entry(self):
        got = self.close([self.rnd(1, [self.entry('E1-1', None)])], marker=None)
        self.assertEqual(got[0], 'PASS')
        self.assertTrue(got[1].startswith('skipped'))

    def test_tagged_entries_pass_and_an_untagged_one_fails_naming_its_id(self):
        ok = self.close([self.rnd(1, [self.entry('E1-1', 'minor')], [self.led('E1-1')], verdict='yellow')])
        self.assertEqual(ok[0], 'PASS')
        bad = self.close([self.rnd(1, [self.entry('E1-1', None)])])
        self.assertEqual(bad[0], 'FAIL')
        self.assertIn('E1-1: severity', bad[1])

    def test_a_minor_outside_its_round_ledger_fails(self):
        got = self.close([self.rnd(1, [self.entry('E1-1', 'minor')], [], verdict='yellow')])
        self.assertEqual(got[0], 'FAIL')
        self.assertIn('E1-1: not in ledger', got[1])

    def test_a_ledger_severity_outside_the_enum_fails(self):
        got = self.close([self.rnd(1, [self.entry('E1-1', 'minor')], [self.led('E1-1', severity='whatever')], verdict='yellow')])
        self.assertEqual(got[0], 'FAIL')
        self.assertIn('E1-1: ledger severity', got[1])

    def test_a_major_fixed_by_a_later_green_round_passes_and_an_open_one_fails(self):
        ok = self.close([self.rnd(1, [self.entry('E1-1')]), self.rnd(2, verdict='green')])
        self.assertEqual(ok[0], 'PASS')
        self.assertIn('0 open', ok[1])
        bad = self.close([self.rnd(1, [self.entry('E1-1')])])
        self.assertEqual(bad[0], 'FAIL')
        self.assertIn('open E1-1', bad[1])

    def test_an_open_critical_fails_and_a_deferred_major_is_not_open(self):
        self.assertIn('open E1-1', self.close([self.rnd(1, [self.entry('E1-1', 'critical')])])[1])
        held = self.close([self.rnd(1, [self.entry('E1-1')], [self.led('E1-1', severity='major')])])
        self.assertEqual(held[0], 'PASS')

    def test_an_open_major_under_an_accepted_partial_task_warns(self):
        got = self.close([self.rnd(1, [self.entry('E1-1')])], task_extra={'status': 'accepted_partial'})
        self.assertEqual(got[0], 'WARN')
        self.assertIn('E1-1', got[1])

    def test_checkpoint_and_plan_gap_rounds_are_not_the_last_pass(self):
        got = self.close([self.rnd(1, verdict='green'), self.rnd(2, [self.entry('E2-1')], source='checkpoint')])
        self.assertEqual(got[0], 'PASS')

    def test_a_complete_ledger_entry_passes_and_one_without_location_fails(self):
        ok = self.close([self.rnd(1, [self.entry('E1-1', 'minor')], [self.led('E1-1')], verdict='yellow')])
        self.assertEqual(ok[0], 'PASS')
        self.assertIn('1 deferred', ok[1])
        bad = self.close([self.rnd(1, [self.entry('E1-1', 'minor')], [self.led('E1-1', location='')], verdict='yellow')])
        self.assertEqual(bad[0], 'FAIL')
        self.assertIn('E1-1: location', bad[1])

    def test_loop_count_three_passes_and_four_fails(self):
        rounds = [self.rnd(1, verdict='green')]
        self.assertEqual(self.close(rounds, loops=3)[0], 'PASS')
        bad = self.close(rounds, loops=4)
        self.assertEqual(bad[0], 'FAIL')
        self.assertIn('error_loop_count 4', bad[1])

    def test_one_user_final_gate_round_passes_and_two_fail(self):
        one = [self.rnd(1, [self.entry('E1-1')], source='user-final-gate'), self.rnd(2, verdict='green')]
        self.assertEqual(self.close(one)[0], 'PASS')
        two = [self.rnd(1, [self.entry('E1-1')], source='user-final-gate'), self.rnd(2, [self.entry('E2-1')], source='user-final-gate'),
               self.rnd(3, verdict='green')]
        bad = self.close(two)
        self.assertEqual(bad[0], 'FAIL')
        self.assertIn('user-final-gate rounds 2', bad[1])

    def test_design_mode_skips_and_the_check_is_registered(self):
        ok, msg = PV.chk_close({'mode': 'design'})
        self.assertTrue(ok)
        self.assertTrue(msg.startswith('skipped'))
        self.assertIn(PV.chk_close, PV.CHECKS)


class DecisionChecklistTests(unittest.TestCase):
    """chk_decision_checklist: a design record needs every area with a decided, sourced entry; a plan checks its record and skips an older one"""
    AREAS = ('copy', 'screen_states', 'check_reach', 'out_of_scope', 'business_rules', 'irreversible', 'dependency')

    def entries(self, drop=None):
        return [{'id': f'DC-{i}', 'area': a, 'item': f'the {a} of the fixture', 'decision': 'settled', 'source': 'Q1'}  # scrub-allow: fixture
                for i, a in enumerate(self.AREAS, 1) if a != drop]

    def record(self, checklist):
        rec = {'plan_id': 'demo', 'user_decisions_verbatim': [{'id': 'Q1', 'answer': 'yes'}],  # scrub-allow: fixture
               'change_design': {'plan': {'tasks': [{'id': 'T1', 'touches': ['logic']}]}}}
        if checklist is not None:
            rec['change_design']['decision_checklist'] = checklist
        return rec

    def design_line(self, checklist):
        tmp = tempfile.TemporaryDirectory(prefix='pv-design-')
        self.addCleanup(tmp.cleanup)
        rec = Path(tmp.name) / 'docs/analysis/demo.yaml'  # scrub-allow: fixture
        dump(rec, self.record(checklist))
        out = subprocess.run([sys.executable, str(SCRIPT), str(rec), '--root', tmp.name], capture_output=True, text=True).stdout
        return next(m.group(1, 3) for m in map(LINE.match, out.splitlines()) if m and m.group(2) == 'decision_checklist')

    def plan_line(self, checklist):
        f = Fixture(self)
        dump(f.root / 'docs/analysis/demo.yaml', self.record(checklist))  # scrub-allow: fixture
        return f.verify()[1]['decision_checklist']

    def test_all_seven_areas_pass_in_both_modes(self):
        self.assertEqual(self.design_line(self.entries())[0], 'PASS')
        self.assertEqual(self.plan_line(self.entries())[0], 'PASS')
        self.assertIn(PV.chk_decision_checklist, PV.CHECKS)

    def test_a_missing_area_fails_naming_it(self):
        got = self.design_line(self.entries(drop='screen_states'))
        self.assertEqual(got[0], 'FAIL')
        self.assertIn('screen_states', got[1])

    def test_an_empty_decision_fails_naming_the_entry(self):
        dc = self.entries()
        dc[2]['decision'] = ' '
        got = self.design_line(dc)
        self.assertEqual(got[0], 'FAIL')
        self.assertIn('DC-3:decision', got[1])

    def test_an_unknown_question_id_fails_and_a_none_decision_passes(self):
        dc = self.entries()
        dc[0]['source'] = 'Q99'  # scrub-allow: fixture
        got = self.design_line(dc)
        self.assertEqual(got[0], 'FAIL')
        self.assertIn('DC-1:source', got[1])
        dc[0]['decision'] = 'none: no user-visible string'
        self.assertEqual(self.design_line(dc)[0], 'PASS')

    def test_an_absent_checklist_fails_a_design_and_skips_a_plan(self):
        self.assertEqual(self.design_line(None)[0], 'FAIL')
        got = self.plan_line(None)
        self.assertEqual(got[0], 'PASS')
        self.assertTrue(got[1].startswith('skipped'))


class ScreenStatesTests(unittest.TestCase):
    """chk_screen_states (FAIL) and chk_duplicate_cases (WARN): both gated by validation_strategy.state_case_standard: 1"""
    MARK = {'validation_strategy': {'state_case_standard': 1}}
    STATES = ('loading', 'empty', 'error', 'fallback', 'success', 'disabled')

    def task(self, skip=None, waivers=None, extra=None, states=None):
        cases = [{'id': f'TC-T1-{i}', 'covers_acceptance': 'T1/AC-1', 'layer': 'e2e', 'states': [s], 'themes': ['light', 'dark']}
                 for i, s in enumerate(self.STATES, 1) if s != skip]
        return {'touches': ['screen'], 'screen_states': {'states': list(states or self.STATES), 'themes': ['light', 'dark']},
                'test_cases': cases + (extra or []), 'state_waivers': waivers or []}

    def got(self, task, mark=True):
        return Fixture(self, plan_extra=self.MARK if mark else None, task_extra=task).verify()[1]

    def test_full_coverage_passes_and_distinct_states_do_not_warn(self):
        got = self.got(self.task())
        self.assertEqual((got['screen_states'][0], got['duplicate_cases'][0]), ('PASS', 'PASS'))
        self.assertIn(PV.chk_screen_states, PV.CHECKS)
        self.assertIn(PV.chk_duplicate_cases, PV.CHECKS)

    def test_a_missing_dark_error_case_fails_naming_it(self):
        t = self.task()
        t['test_cases'][2]['themes'] = ['light']
        got = self.got(t)['screen_states']
        self.assertEqual(got[0], 'FAIL')
        self.assertIn('T1: state error has no case in theme dark', got[1])

    def test_a_waiver_needs_a_reason_and_a_file_line(self):
        bad = self.got(self.task(skip='disabled', waivers=[{'state': 'disabled', 'reason': 'no control', 'evidence': 'none'}]))['screen_states']
        self.assertEqual(bad[0], 'FAIL')
        self.assertIn('lacks a reason or a file:line evidence', bad[1])
        good = self.got(self.task(skip='disabled', waivers=[{'state': 'disabled', 'reason': 'no control', 'evidence': 'src/app.py:3'}]))
        self.assertEqual(good['screen_states'][0], 'PASS')

    def test_a_base_state_missing_from_screen_states_fails(self):
        got = self.got(self.task(states=[s for s in self.STATES if s != 'fallback']))['screen_states']
        self.assertEqual(got[0], 'FAIL')
        self.assertIn('T1: screen_states lacks fallback', got[1])

    def test_an_unmarked_plan_skips_both_checks(self):
        got = self.got(self.task(skip='error'), mark=False)
        for name in ('screen_states', 'duplicate_cases'):
            self.assertEqual(got[name][0], 'PASS')
            self.assertTrue(got[name][1].startswith('skipped'))

    def test_two_cases_on_one_ac_layer_and_state_warn_naming_both(self):
        dup = {'id': 'TC-T1-9', 'covers_acceptance': 'T1/AC-1', 'layer': 'e2e', 'states': ['error'], 'themes': ['light']}
        got = self.got(self.task(extra=[dup]))['duplicate_cases']
        self.assertEqual(got[0], 'WARN')
        self.assertIn('TC-T1-3', got[1])
        self.assertIn('TC-T1-9', got[1])

    def test_cases_without_states_do_not_warn(self):
        plain = [{'id': f'TC-T1-{i}', 'covers_acceptance': 'T1/AC-1', 'layer': 'unit'} for i in (7, 8)]
        self.assertEqual(self.got(self.task(extra=plain))['duplicate_cases'][0], 'PASS')

    def test_a_shared_ac_and_state_warn_across_ac_sets(self):
        wide = {'id': 'TC-T1-9', 'covers_acceptance': ['T1/AC-1', 'T1/AC-2'], 'layer': 'e2e', 'states': ['error'], 'themes': ['light']}
        got = self.got(self.task(extra=[wide]))['duplicate_cases']
        self.assertEqual(got[0], 'WARN')
        self.assertIn('TC-T1-3 and TC-T1-9', got[1])


class WorkspaceRootTests(unittest.TestCase):
    def test_plan_dir_outside_docs_exits_2_naming_it(self):
        tmp = tempfile.TemporaryDirectory(prefix='pv-gates-')
        self.addCleanup(tmp.cleanup)
        plan = Path(tmp.name) / 'elsewhere/demo'
        put(plan / 'plan.yaml', 'plan_id: demo\nwaves: []\ntasks: []\n')
        p = subprocess.run([sys.executable, str(SCRIPT), str(plan)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        self.assertIn('is not inside a docs/ folder', p.stdout)


class ExternalStepFileTests(unittest.TestCase):
    def setUp(self):
        out = tempfile.TemporaryDirectory(prefix='pv-ext-')
        self.addCleanup(out.cleanup)
        self.out = Path(out.name)
        self.ext = self.out / 'x.py'
        put(self.ext, 'x = 1\n')

    def fixture(self, path, allowed, before='x = 1', record=True):
        f = Fixture(self)
        path = str(path)

        def aim(t):
            t['files'][0]['path'] = path
            t['steps'][0]['file'] = path
            t['steps'][0]['before'] = before
        f.edit_task(aim)
        if record:
            dump(f.root / 'docs/analysis/demo.yaml', {'plan_id': 'demo', 'binding_scope': {'files_allowed': allowed}})  # scrub-allow: fixture
        return f

    def test_listed_absolute_path_passes_shape_and_anchors(self):
        f = self.fixture(self.ext, [str(self.ext)])
        _, found, _ = f.verify()
        self.assertEqual(found['steps_shape'][0], 'PASS', found['steps_shape'])
        self.assertEqual(found['anchors'][0], 'PASS', found['anchors'])

    def test_unlisted_absolute_path_fails_both(self):
        f = self.fixture(self.ext, ['src/app.py'])
        _, found, _ = f.verify()
        self.assertEqual(found['steps_shape'][0], 'FAIL')
        self.assertIn('is absolute', found['steps_shape'][1])
        self.assertEqual(found['anchors'][0], 'FAIL')
        self.assertIn('escapes the root', found['anchors'][1])

    def test_listed_path_with_missing_before_fails_anchor(self):
        f = self.fixture(self.ext, [str(self.ext)], before='y = 9')
        _, found, _ = f.verify()
        self.assertEqual(found['anchors'][0], 'FAIL')
        self.assertIn('before occurs 0 times', found['anchors'][1])

    def test_listed_path_with_dotdot_fails(self):
        odd = f'{self.out}/sub/../x.py'
        f = self.fixture(odd, [odd])
        _, found, _ = f.verify()
        self.assertEqual(found['steps_shape'][0], 'FAIL')
        self.assertEqual(found['anchors'][0], 'FAIL')

    def test_listing_only_the_parent_directory_fails(self):
        f = self.fixture(self.ext, [f'{self.out}/'])
        _, found, _ = f.verify()
        self.assertEqual(found['steps_shape'][0], 'FAIL')
        self.assertEqual(found['anchors'][0], 'FAIL')

    def test_tilde_path_listed_resolves_under_home(self):
        put(self.out / 'f.txt', 'x = 1\n')
        f = self.fixture('~/f.txt', ['~/f.txt'])
        env = dict(os.environ, HOME=str(self.out), PLAN_VERIFY_SKIP_MIRROR='1')
        p = subprocess.run([sys.executable, str(SCRIPT), str(f.plan), '--root', str(f.root)], capture_output=True, text=True, env=env)
        found = {m.group(2): (m.group(1), m.group(3)) for m in map(LINE.match, p.stdout.splitlines()) if m}
        self.assertEqual(found['steps_shape'][0], 'PASS', found['steps_shape'])
        self.assertEqual(found['anchors'][0], 'PASS', found['anchors'])

    def test_clone_leaves_the_external_file_unchanged(self):
        f = self.fixture(self.ext, [str(self.ext)])
        clone = self.out / 'clone'
        _, found, _ = f.verify('--clone', str(clone))
        self.assertEqual(found['anchors'][0], 'PASS', found['anchors'])
        self.assertIn('1 external in memory', found['anchors'][1])
        self.assertEqual(self.ext.read_text(encoding='utf-8'), 'x = 1\n')

    def test_listed_absolute_path_inside_root_fails(self):
        f = Fixture(self)
        put(f.root / 'src/app.py', 'x = 1\n')
        absf = str(Path(os.path.realpath(f.root)) / 'src/app.py')

        def aim(t):
            s2 = copy.deepcopy(t['steps'][0])
            s2.update(n=2, file=absf, before='x = 1', after='x = 3')
            t['steps'] = [t['steps'][0], s2]
            t['files'] = [t['files'][0], {'path': absf, 'change': 'edit', 'why': 'same file, absolute'}]
        f.edit_task(aim)
        dump(f.root / 'docs/analysis/demo.yaml', {'plan_id': 'demo', 'binding_scope': {'files_allowed': ['src/app.py', absf]}})  # scrub-allow: fixture
        _, found, _ = f.verify()
        self.assertEqual(found['steps_shape'][0], 'FAIL', found['steps_shape'])
        self.assertIn('is absolute', found['steps_shape'][1])
        self.assertNotIn('external in memory', found['anchors'][1])

    def test_case_variant_spelling_of_root_inside_root_fails(self):
        f = Fixture(self)
        put(f.root / 'src/app.py', 'x = 1\n')
        absf = str(Path(os.path.realpath(f.root)) / 'src/app.py')
        variant = absf.upper()
        if variant == absf or not os.path.exists(variant):
            self.skipTest('filesystem is case-sensitive')

        def aim(t):
            s2 = copy.deepcopy(t['steps'][0])
            s2.update(n=2, file=variant, before='x = 1', after='x = 3')
            t['steps'] = [t['steps'][0], s2]
            t['files'] = [t['files'][0], {'path': variant, 'change': 'edit', 'why': 'same file, case variant'}]
        f.edit_task(aim)
        dump(f.root / 'docs/analysis/demo.yaml', {'plan_id': 'demo', 'binding_scope': {'files_allowed': ['src/app.py', variant]}})  # scrub-allow: fixture
        _, found, _ = f.verify()
        self.assertEqual(found['steps_shape'][0], 'FAIL', found['steps_shape'])
        self.assertIn('is absolute', found['steps_shape'][1])
        self.assertNotIn('external in memory', found['anchors'][1])
        _, found, _ = f.verify('--clone', str(f.root.parent / 'clone_variant'))
        self.assertNotIn('external in memory', found['anchors'][1])

    def test_without_a_record_it_fails_as_before(self):
        f = self.fixture(self.ext, [], record=False)
        _, found, _ = f.verify()
        self.assertEqual(found['steps_shape'][0], 'FAIL')
        self.assertEqual(found['anchors'][0], 'FAIL')


class MirrorSwitchTests(unittest.TestCase):
    """PLAN_VERIFY_SKIP_MIRROR=1 skips chk_mirror; unset or any other value, chk_mirror runs no subprocess"""

    def mirror(self, value):
        env = {k: v for k, v in os.environ.items() if k != 'PLAN_VERIFY_SKIP_MIRROR'}
        if value is not None:
            env['PLAN_VERIFY_SKIP_MIRROR'] = value
        done = subprocess.CompletedProcess([], 0, 'PASS  plan_steps_shape stub\n', '')
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(PV.subprocess, 'run', return_value=done) as run:
            ok, msg = PV.chk_mirror({'mode': 'plan', 'plan_dir': '/nonexistent/docs/plan/demo'})
        return ok, msg, run.call_count

    def test_unset_spawns_no_ruleset_check(self):
        ok, msg, calls = self.mirror(None)
        self.assertEqual((ok, calls), (True, 0))
        self.assertIn('no ruleset run', msg)

    def test_a_value_other_than_1_spawns_nothing(self):
        self.assertEqual(self.mirror('0')[2], 0)

    def test_1_skips_without_spawning(self):
        ok, msg, calls = self.mirror('1')
        self.assertEqual((ok, calls), (True, 0))
        self.assertIn('PLAN_VERIFY_SKIP_MIRROR', msg)


class ChangeFolderTests(unittest.TestCase):
    """plan-verify finds errors.yaml, change-map.json, the record and the change files in docs/changes/{id}/, keeps the old
    docs/plan/{id}/ sidecar of a docs/specs/changes plan, and fails a migrated workspace that grows a legacy root again"""
    OPEN_CRITICAL = {'meta': {'error_loop_count': 1, 'close_criteria': 1}, 'errors': [{
        'round': 1, 'round_source': 'review-test', 'verdict': 'red',
        'entries': [{'id': 'E1-1', 'source': 'reviewer-independent', 'text': 'finding', 'severity': 'critical'}],
        'analysis': {'groups': [], 'fix_list': [], 'deferred_errors': []}}]}
    CLEAN = {'meta': {'error_loop_count': 1, 'close_criteria': 1}, 'errors': []}
    MAP = 'old_path\tnew_path\taction\n'

    def design_check(self, name, setup):
        """design mode on root/docs/analysis/demo.yaml after setup(root); -> (state, message) of the check `name`"""  # scrub-allow: fixture
        tmp = tempfile.TemporaryDirectory(prefix='pv-layout-')
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        dump(root / 'docs/analysis/demo.yaml', {'plan_id': 'demo', 'change_design': {'plan': {'tasks': [{'id': 'T1', 'touches': ['logic']}]}}})  # scrub-allow: fixture
        setup(root)
        out = subprocess.run([sys.executable, str(SCRIPT), str(root / 'docs/analysis/demo.yaml'), '--root', str(root)], capture_output=True,  # scrub-allow: fixture
                             text=True, env=dict(os.environ, PLAN_VERIFY_SKIP_MIRROR=os.environ.get('PLAN_VERIFY_SKIP_MIRROR', '1'))).stdout
        return next(m.group(1, 3) for m in map(LINE.match, out.splitlines()) if m and m.group(2) == name)

    def test_an_open_critical_in_docs_changes_fails_close(self):
        f = Fixture(self, where='docs/changes/demo')
        dump(f.plan / 'errors.yaml', self.OPEN_CRITICAL)
        state, msg = f.verify()[1]['close']
        self.assertEqual(state, 'FAIL')
        self.assertIn('open E1-1', msg)

    def test_the_old_sidecar_of_a_docs_specs_changes_plan_is_still_read(self):
        f = Fixture(self, plan_extra=DataImpactTests.MARK, task_extra=DataImpactTests.done(), where='docs/specs/changes/demo')
        dump(f.root / 'docs/plan/demo/errors.yaml', self.OPEN_CRITICAL)
        put(f.root / 'docs/plan/demo/change-map.json', '{"sections": {"mismatch": {"entries": [{"code": "record_missing", "task_id": "T1"}]}}}')
        found = f.verify()[1]
        self.assertEqual(found['close'][0], 'FAIL')
        self.assertIn('open E1-1', found['close'][1])
        self.assertEqual(found['data_impact'][0], 'WARN')
        self.assertIn('1 mismatches', found['data_impact'][1])

    def test_the_plan_folder_wins_over_a_stale_sidecar(self):
        f = Fixture(self, where='docs/changes/demo')
        dump(f.plan / 'errors.yaml', self.CLEAN)
        dump(f.root / 'docs/plan/demo/errors.yaml', self.OPEN_CRITICAL)
        self.assertEqual(f.verify()[1]['close'][0], 'PASS')

    def test_design_mode_checks_the_change_files_in_docs_changes(self):
        state, msg = self.design_check('spec_delta', lambda root: put(root / 'docs/changes/demo/design.md', '# Design: demo\n\n## Nothing\nx\n'))
        self.assertEqual(state, 'FAIL')
        self.assertIn("design.md: heading '## ", msg)

    def test_design_mode_without_a_changes_folder_keeps_the_legacy_change_files(self):
        state, msg = self.design_check('spec_delta', lambda root: put(root / 'docs/analysis/demo/design.md', '# Design: demo\n\n## Nothing\nx\n'))  # scrub-allow: fixture
        self.assertEqual(state, 'FAIL')
        self.assertIn("design.md: heading '## ", msg)

    def test_a_reappeared_legacy_root_fails_naming_it(self):
        f = Fixture(self, where='docs/changes/demo')
        put(f.root / 'docs/changes/MIGRATION-MAP.tsv', self.MAP)
        (f.root / 'docs/plan').mkdir()
        state, msg = f.verify()[1]['legacy_roots']
        self.assertEqual(state, 'FAIL')
        self.assertIn('docs/plan', msg)

    def test_no_map_or_no_legacy_root_passes(self):
        self.assertEqual(Fixture(self).verify()[1]['legacy_roots'][0], 'PASS')            # docs/plan exists, no MIGRATION-MAP.tsv
        f = Fixture(self, where='docs/changes/demo')
        put(f.root / 'docs/changes/MIGRATION-MAP.tsv', self.MAP)
        self.assertEqual(f.verify()[1]['legacy_roots'][0], 'PASS')                        # migrated, no legacy root back
        self.assertIn(PV.chk_legacy_roots, PV.CHECKS)


class FixedSetTests(unittest.TestCase):
    """the fixed run-file set (a plan.yaml holding its tasks inline) next to the legacy tasks/ layout"""

    @staticmethod
    def inline(case, break_id=False):
        """root/docs/changes/demo with one task written inline in plan.yaml and no tasks/ folder"""
        tmp = tempfile.TemporaryDirectory(prefix='pv-fixed-')
        case.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        task = dict(base_task(), wave='W1', depends_on=[])
        if break_id:
            del task['id']
        dump(root / 'docs/changes/demo/plan.yaml', {'plan_id': 'demo', 'objective': 'A fixed-set fixture', 'waves': [{'id': 'W1', 'name': 'one'}],
                                                    'tasks': [task]})
        return root, root / 'docs/changes/demo'

    @staticmethod
    def run_cli(root, plan):
        p = subprocess.run([sys.executable, str(SCRIPT), str(plan), '--root', str(root)], capture_output=True, text=True,
                           env=dict(os.environ, PLAN_VERIFY_SKIP_MIRROR='1'))
        return p.returncode, {m.group(2): (m.group(1), m.group(3)) for m in map(LINE.match, p.stdout.splitlines()) if m}

    def test_an_inline_task_plan_loads_and_passes_the_shape_checks(self):  # fixed set
        root, plan = self.inline(self)
        _, got = self.run_cli(root, plan)
        self.assertFalse((plan / 'tasks').exists())
        for name in ('dag', 'steps_shape', 'placeholders'):
            self.assertEqual(got[name][0], 'PASS', got[name])

    def test_a_tasks_folder_plan_gives_the_same_shape_results(self):  # legacy parity
        root, plan = self.inline(self)
        _, inline = self.run_cli(root, plan)
        f = Fixture(self, where='docs/changes/demo')
        self.assertTrue((f.plan / 'tasks/W1/T1.yaml').is_file())
        split = f.verify()[1]
        for name in ('dag', 'steps_shape', 'placeholders'):
            self.assertEqual(split[name][0], inline[name][0], name)

    def test_an_inline_task_without_an_id_fails(self):
        root, plan = self.inline(self, break_id=True)
        rc, got = self.run_cli(root, plan)
        self.assertEqual((rc, got['dag'][0]), (1, 'FAIL'))


class MirrorGateTests(unittest.TestCase):
    """chk_mirror, in process with PLAN_VERIFY_SKIP_MIRROR unset, still fails a stale mirror"""

    def plan(self, mirror=None, done=False):
        tmp = tempfile.TemporaryDirectory(prefix='pv-mirror-')
        self.addCleanup(tmp.cleanup)
        folder = Path(tmp.name) / 'docs/changes/demo'
        keys = list(PV.load_yaml(PV.TEMPLATE)['steps'][0])
        step = {k: 'x' for k in keys}
        step.update(n=1, action='edit', done=done, expect=None)
        task = {'id': 'T1', 'steps': [step], 'wave': 'W1', 'depends_on': []}
        dump(folder / 'plan.yaml', {'plan_id': 'demo', 'tasks': [task]})
        if mirror is not None:
            put(folder / 'plan.en.md', mirror)
        return {'mode': 'plan', 'plan_dir': str(folder), 'tasks': [task]}

    @staticmethod
    def check(ctx):
        env = {k: v for k, v in os.environ.items() if k != 'PLAN_VERIFY_SKIP_MIRROR'}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(PV.subprocess, 'run') as run:
            ok, msg = PV.chk_mirror(ctx)
        run.assert_not_called()
        return ok, msg

    def test_a_clean_mirror_passes(self):
        self.assertTrue(self.check(self.plan('### 1. T1 \xb7 Count\n- [ ] 1.1 edit\n'))[0])

    def test_a_mirror_without_a_task_heading_fails(self):
        ok, msg = self.check(self.plan('# Plan\n'))
        self.assertFalse(ok)
        self.assertIn("no '### n. T1", msg)

    def test_a_tick_on_a_step_that_is_not_done_fails(self):
        ok, msg = self.check(self.plan('### 1. T1 \xb7 Count\n- [x] 1.1 edit\n', done=False))
        self.assertFalse(ok)
        self.assertIn('is ticked but step 1 of T1 is not done', msg)

    def test_a_tick_on_a_done_step_passes(self):
        self.assertTrue(self.check(self.plan('### 1. T1 \xb7 Count\n- [x] 1.1 edit\n', done=True))[0])

    def test_no_mirror_file_passes_and_says_skipped(self):
        ok, msg = self.check(self.plan(None))
        self.assertTrue(ok)
        self.assertIn('skipped: no mirror', msg)


if __name__ == '__main__':
    unittest.main()
