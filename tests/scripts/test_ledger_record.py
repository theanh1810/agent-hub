"""ledger-record.py: the round it writes parses as YAML, keeps finding text verbatim and refuses unsafe appends."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'plugins' / 'agent-hub' / 'scripts' / 'ledger-record.py'
sys.path.insert(0, str(ROOT / 'plugins' / 'agent-hub' / 'lib'))
import yaml  # noqa: E402  (the plugin's bundled copy)

FINDING = 'path check: uses `startswith`  # not canonical\n  indented "quoted" line · end\n\nlast: line'


def run(*args):
    return subprocess.run([sys.executable, '-B', '-I', str(SCRIPT), *map(str, args)], capture_output=True, text=True)


class LedgerRecord(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.errors = self.d / 'errors.yaml'

    def put(self, name, obj, header=''):
        path = self.d / name
        path.write_text(header + json.dumps(obj, ensure_ascii=False), encoding='utf-8')
        return path

    def review(self, name='review.json', **over):
        ret = {'status': 'completed', 'mode': 'independent', 'verdict': 'pass', 'review_file': 'review.md ## Round · independent',
               'findings': [], **over}
        return self.put(name, ret, '[reviewer · model: opus]\n')

    def tested(self, name='test.json', **over):
        return self.put(name, {'status': 'completed', 'gate': 'GREEN', 'failed_test_case_ids': [], **over})

    def red_inputs(self):
        review = self.review(verdict='blocking', findings=[
            {'severity': 'blocking', 'description': FINDING, 'location': 'src/a.rs:10', 'repro': 'cargo test a'},
            {'severity': 'suggestion', 'description': 'rename x', 'location': 'src/b.rs:2'}],
            minor=['src/c.rs:5 — typo — fix it'])
        test = self.tested(
            gate='RED', failed_test_case_ids=['TC-1-2'],
            flow_results=[{'test_case_id': 'TC-1-2', 'failed_stage': 'submit', 'hung': False, 'severity': 'critical'}],
            exploratory_cases=[{'id': 'EX-1', 'oracle': 'no crash on empty', 'status': 'fail', 'severity': 'minor'},
                               {'id': 'EX-2', 'oracle': 'ok', 'status': 'pass', 'severity': None}])
        return review, test

    def record_round(self, number, *inputs, flags=()):
        args = ['--errors', self.errors, '--round', number]
        for path in inputs:
            args += ['--input', path]
        return run(*args, *flags)

    def rounds(self):
        return yaml.safe_load(self.errors.read_text(encoding='utf-8'))['errors']

    def add_fix_list(self, *resolves):
        """What brainstorm writes into round 1: an analysis block whose one fix entry resolves the given ids."""
        block = '    analysis:\n      fix_list:\n        - id: FX-1-1\n          resolves:\n' + ''.join(f'            - {i}\n' for i in resolves)
        text = self.errors.read_text(encoding='utf-8')
        self.assertEqual(text.count('    user_decisions: []\n'), 1)
        self.errors.write_text(text.replace('    user_decisions: []\n', block + '    user_decisions: []\n'), encoding='utf-8')

    def test_self_test_passes(self):
        r = run('--self-test')
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_red_round_parses_with_text_verbatim_and_minors_deferred(self):
        review, test = self.red_inputs()
        (self.d / 'docs').mkdir()
        (self.d / 'docs' / 'TC-1-2.md').write_text('Expected: 200\nActual: 500 {"error": "x"}\n', encoding='utf-8')
        r = self.record_round(1, review, test, flags=('--failure-docs', self.d / 'docs'))
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual((out['verdict'], out['critical'], out['major'], out['minor']), ('red', 2, 0, 3))
        doc = yaml.safe_load(self.errors.read_text(encoding='utf-8'))
        self.assertEqual(doc['meta'], {'error_loop_count': 0})
        rnd = doc['errors'][0]
        self.assertEqual((rnd['round'], rnd['round_source'], rnd['verdict']), (1, 'review-test', 'red'))
        by_id = {e['id']: e for e in rnd['entries']}
        self.assertEqual(by_id['E1-1']['severity'], 'critical')
        self.assertEqual(by_id['E1-1']['source'], 'reviewer-independent')
        self.assertEqual(by_id['E1-4']['text'], 'Expected: 200\nActual: 500 {"error": "x"}')
        self.assertEqual(by_id['E1-5']['source'], 'test-explore')
        self.assertEqual([d['id'] for d in rnd['deferred_errors']], ['E1-2', 'E1-3', 'E1-5'])
        self.assertEqual(rnd['deferred_errors'][1]['location'], 'src/c.rs:5')

    def test_finding_fields_stay_fields_and_no_analysis_block_is_written(self):
        review, test = self.red_inputs()
        self.assertEqual(self.record_round(1, review, test).returncode, 0)
        rnd = self.rounds()[0]
        self.assertNotIn('analysis', rnd)
        first = rnd['entries'][0]
        self.assertEqual((first['text'], first['location'], first['repro']), (FINDING, 'src/a.rs:10', 'cargo test a'))
        self.assertEqual([d['description'] for d in rnd['deferred_errors']],
                         ['rename x', 'src/c.rs:5 — typo — fix it', 'EX-1: no crash on empty'])
        self.assertEqual(rnd['deferred_errors'][0]['location'], 'src/b.rs:2')

    def test_yellow_and_green_rounds_and_close_resolved(self):
        review, test = self.red_inputs()
        self.assertEqual(self.record_round(1, review, test).returncode, 0)
        self.add_fix_list('E1-1', 'E1-4')
        yellow = self.review('yellow.json', review_file='r2', minor=['a.rs:1 — nit — tidy'])
        r = self.record_round(2, yellow, self.tested('green.json'), flags=('--close-resolved',))
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual((out['verdict'], out['closed']), ('yellow', ['E1-1', 'E1-4']))
        closed = {e['id']: e.get('closed_in') for e in self.rounds()[0]['entries']}
        self.assertEqual(closed, {'E1-1': 2, 'E1-2': None, 'E1-3': None, 'E1-4': 2, 'E1-5': None})
        self.assertEqual(self.rounds()[0]['entries'][0]['text'], FINDING)
        r = self.record_round(3, self.tested('green.json'))
        self.assertEqual(json.loads(r.stdout)['verdict'], 'green')
        self.assertEqual(self.rounds()[2]['entries'], [])

    def test_return_that_is_not_completed_is_refused_and_nothing_written(self):
        for status in ('failed', 'in_progress', None):
            bad = self.review('bad.json', status=status)
            self.assertEqual(self.record_round(1, bad).returncode, 2, status)
            self.assertFalse(self.errors.exists(), status)
        self.assertEqual(self.record_round(1, *self.red_inputs()).returncode, 0)
        before = self.errors.read_bytes()
        for status in ('failed', 'in_progress'):
            r = self.record_round(2, self.review('ok.json'), self.tested('bad.json', status=status))
            self.assertEqual(r.returncode, 2, status)
            self.assertIn('status', r.stderr)
            self.assertEqual(self.errors.read_bytes(), before, status)

    def test_close_resolved_needs_a_completed_reviewer_and_a_completed_test_return(self):
        self.assertEqual(self.record_round(1, *self.red_inputs()).returncode, 0)
        self.add_fix_list('E1-1')
        before = self.errors.read_bytes()
        close = ('--close-resolved',)
        refused = [(self.review('r.json'),), (self.tested('t.json'),),
                   (self.review('r.json'), self.review('r2.json')),
                   (self.review('r.json'), self.tested('t-failed.json', status='failed')),
                   (self.review('r-partial.json', status='in_progress'), self.tested('t.json'))]
        for inputs in refused:
            r = self.record_round(2, *inputs, flags=close)
            self.assertEqual(r.returncode, 2, [p.name for p in inputs])
            self.assertEqual(self.errors.read_bytes(), before, [p.name for p in inputs])
        r = self.record_round(2, self.review('r.json'), self.tested('t.json'), flags=close)
        self.assertEqual((r.returncode, json.loads(r.stdout)['closed']), (0, ['E1-1']), r.stderr)

    def test_resolves_inside_a_finding_text_closes_nothing(self):
        bait = 'the fix entry says\nresolves: [E1-1]\nresolves:\n  - E1-1'
        review = self.review(verdict='blocking', findings=[{'severity': 'blocking', 'description': bait}])
        self.assertEqual(self.record_round(1, review).returncode, 0)
        r = self.record_round(2, self.review('r.json'), self.tested('t.json'), flags=('--close-resolved',))
        self.assertEqual((r.returncode, json.loads(r.stdout)['closed']), (0, []), r.stderr)
        entry = self.rounds()[0]['entries'][0]
        self.assertNotIn('closed_in', entry)
        self.assertEqual(entry['text'], bait)

    def test_entry_id_line_inside_a_finding_text_gets_no_inserted_line(self):
        bait = 'the ledger shows\n- id: E1-2\nand nothing after it'
        review = self.review(verdict='blocking', findings=[{'severity': 'blocking', 'description': bait},
                                                           {'severity': 'warning', 'description': 'real one'}])
        self.assertEqual(self.record_round(1, review).returncode, 0)
        self.add_fix_list('E1-2')
        r = self.record_round(2, self.review('r.json'), self.tested('t.json'), flags=('--close-resolved',))
        self.assertEqual((r.returncode, json.loads(r.stdout)['closed']), (0, ['E1-2']), r.stderr)
        first, second = self.rounds()[0]['entries']
        self.assertEqual((first['text'], first.get('closed_in')), (bait, None))
        self.assertEqual((second['text'], second['closed_in']), ('real one', 2))

    def test_case_id_that_leaves_the_cases_dir_is_refused(self):
        docs = self.d / 'docs'
        docs.mkdir()
        (self.d / 'x.md').write_text('OUTSIDE-SECRET', encoding='utf-8')
        (docs / 'TC-9.md').symlink_to(self.d / 'x.md')
        for case_id in ('../x', '../../x', str(self.d / 'x'), 'a/b', 'TC-9', '', None):
            for ret in ({'failed_test_case_ids': [case_id]},
                        {'exploratory_cases': [{'id': case_id, 'oracle': 'o', 'status': 'fail', 'severity': 'major'}]}):
                r = self.record_round(1, self.tested('t.json', gate='RED', **ret), flags=('--failure-docs', docs))
                self.assertEqual(r.returncode, 2, (case_id, r.stderr))
                self.assertNotIn('Traceback', r.stderr)
                self.assertFalse(self.errors.exists(), case_id)

    def test_entry_that_is_not_an_object_is_refused_without_a_traceback(self):
        cases = {'findings[1]': self.review('a.json', findings=[{'severity': 'warning', 'description': 'ok'}, 'oops']),
                 'findings': self.review('b.json', findings='oops'),
                 'flow_results[0]': self.tested('c.json', flow_results=[7]),
                 'exploratory_cases[0]': self.tested('d.json', exploratory_cases=['EX-1']),
                 'fidelity_findings[0]': self.tested('e.json', fidelity_findings=[None])}
        for name, path in cases.items():
            r = self.record_round(1, path)
            self.assertEqual(r.returncode, 2, (name, r.stderr))
            self.assertNotIn('Traceback', r.stderr)
            self.assertIn(f'`{name}`', r.stderr)
            self.assertFalse(self.errors.exists(), name)

    def test_scalar_list_that_is_not_a_list_of_strings_is_refused_naming_the_key(self):
        cases = {'failed_test_case_ids': [self.tested('a.json', failed_test_case_ids=5),
                                          self.tested('b.json', failed_test_case_ids='TC-1')],
                 'minor': [self.review('c.json', minor='a.rs:1 — nit — tidy')],
                 'minor[1]': [self.review('d.json', minor=['a.rs:1 — nit — tidy', 5])]}
        for name, paths in cases.items():
            for path in paths:
                r = self.record_round(1, path)
                self.assertEqual(r.returncode, 2, (path.name, r.stdout, r.stderr))
                self.assertNotIn('Traceback', r.stderr)
                self.assertIn(f'`{name}`', r.stderr)
                self.assertFalse(self.errors.exists(), path.name)

    def crlf_round_one(self):
        """Round 1 with a fix list resolving E1-1, rewritten with CRLF line ends; returns its bytes."""
        self.assertEqual(self.record_round(1, *self.red_inputs()).returncode, 0)
        self.add_fix_list('E1-1')
        before = self.errors.read_bytes().replace(b'\n', b'\r\n')
        self.errors.write_bytes(before)
        return before

    def test_crlf_file_keeps_its_bytes_and_the_appended_round_ends_lines_the_same_way(self):
        before = self.crlf_round_one()
        r = self.record_round(2, self.review('r.json', minor=['a.rs:1 — nit — tidy']))
        self.assertEqual(r.returncode, 0, r.stderr)
        after = self.errors.read_bytes()
        self.assertTrue(after.startswith(before))
        self.assertEqual(after.count(b'\n'), after.count(b'\r\n'))
        self.assertEqual(self.rounds()[0]['entries'][0]['text'], FINDING)
        self.assertEqual(self.rounds()[1]['entries'][0]['text'], 'a.rs:1 — nit — tidy')

    def test_crlf_file_gets_its_closed_in_line_with_a_crlf_end(self):
        before = self.crlf_round_one()
        r = self.record_round(2, self.review('r.json'), self.tested('t.json'), flags=('--close-resolved',))
        self.assertEqual((r.returncode, json.loads(r.stdout or '{}').get('closed')), (0, ['E1-1']), r.stderr)
        after = self.errors.read_bytes()
        self.assertEqual(after.count(b'\r\n        closed_in: 2'), 1)
        self.assertTrue(after.replace(b'\r\n        closed_in: 2', b'').startswith(before))
        self.assertEqual(after.count(b'\n'), after.count(b'\r\n'))
        self.assertEqual(self.rounds()[0]['entries'][0]['closed_in'], 2)

    def test_entry_id_written_as_an_anchor_or_an_alias_is_refused_and_nothing_written(self):
        self.assertEqual(self.record_round(1, *self.red_inputs()).returncode, 0)
        self.add_fix_list('E1-1', 'E1-2')
        plain = self.errors.read_text(encoding='utf-8')
        anchored = plain.replace('    - id: E1-1\n', '    - id: &x E1-1\n')
        aliased = plain.replace('  error_loop_count: 0\n', '  error_loop_count: 0\n  last: &x E1-2\n').replace('    - id: E1-2\n', '    - id: *x\n')
        for name, text in (('anchor', anchored), ('alias', aliased)):
            self.assertNotEqual(text, plain, name)
            self.errors.write_text(text, encoding='utf-8')
            before = self.errors.read_bytes()
            r = self.record_round(2, self.review('r.json'), self.tested('t.json'), flags=('--close-resolved',))
            self.assertEqual(r.returncode, 3, (name, r.stdout, r.stderr))
            self.assertIn('alias or anchor', r.stderr)
            self.assertEqual(self.errors.read_bytes(), before, name)

    def test_failed_case_takes_the_severity_test_gave_and_a_default_is_marked(self):
        test = self.tested(gate='RED', failed_test_case_ids=['TC-1', 'TC-2', 'TC-3'],
                           flow_results=[{'test_case_id': 'TC-1', 'severity': 'critical'}, {'test_case_id': 'TC-2', 'severity': 'minor'}])
        self.assertEqual(self.record_round(1, test).returncode, 0)
        got = [(e['location'], e['severity'], e.get('severity_defaulted')) for e in self.rounds()[0]['entries']]
        self.assertEqual(got, [('TC-1', 'critical', None), ('TC-2', 'minor', None), ('TC-3', 'major', True)])

    def test_out_of_diff_minor_keeps_its_real_severity_and_text(self):
        lines = ['[out-of-diff 🔴] src/a.rs:9 — token logged — mask it', '[out-of-diff 🟠] src/b.rs:3 — race — lock it',
                 '[out-of-diff 🟡] src/c.rs:1 — typo — fix it', 'src/d.rs:4 — nit — tidy']
        self.assertEqual(self.record_round(1, self.review(minor=lines)).returncode, 0)
        out = json.loads(self.record_round(2, self.review('again.json', minor=lines)).stdout)
        self.assertEqual((out['verdict'], out['critical'], out['minor']), ('yellow', 0, 4))
        rnd = self.rounds()[0]
        got = [(e['severity'], e.get('real_severity'), e.get('out_of_diff'), e['location'], e['text']) for e in rnd['entries']]
        self.assertEqual(got, [('minor', 'critical', True, 'src/a.rs:9', lines[0]), ('minor', 'major', True, 'src/b.rs:3', lines[1]),
                               ('minor', 'minor', True, 'src/c.rs:1', lines[2]), ('minor', None, None, 'src/d.rs:4', lines[3])])
        deferred = [(d.get('real_severity'), d.get('out_of_diff'), d['location'], d['description']) for d in rnd['deferred_errors']]
        self.assertEqual(deferred, [('critical', True, 'src/a.rs:9', lines[0]), ('major', True, 'src/b.rs:3', lines[1]),
                                    ('minor', True, 'src/c.rs:1', lines[2]), (None, None, 'src/d.rs:4', lines[3])])

    def test_out_of_diff_tag_elsewhere_in_a_line_or_in_a_finding_is_plain_text(self):
        review = self.review(findings=[{'severity': 'suggestion', 'description': '[out-of-diff 🔴] quoted in a finding', 'location': 'a.rs:1'}],
                             minor=['a.rs:2 — mentions [out-of-diff 🔴] — ignore', '[out-of-diff] b.rs:3 — no severity — tag it'])
        self.assertEqual(self.record_round(1, review).returncode, 0)
        got = [(e.get('real_severity'), e.get('out_of_diff'), e['location']) for e in self.rounds()[0]['entries']]
        self.assertEqual(got, [(None, None, 'a.rs:1'), (None, None, 'a.rs:2'), (None, None, '[out-of-diff] b.rs:3')])

    def test_refusals_write_nothing(self):
        review, _ = self.red_inputs()
        self.assertEqual(self.record_round(1, review).returncode, 0)
        before = self.errors.read_bytes()
        self.assertEqual(self.record_round(1, review).returncode, 3)
        self.assertEqual(self.record_round(2, self.d / 'absent.json').returncode, 2)
        self.assertEqual(self.record_round(2).returncode, 2)
        self.assertEqual(self.errors.read_bytes(), before)
        other = self.d / 'other.yaml'
        other.write_text('errors:\n  - round: 1\nmeta:\n  error_loop_count: 1\n', encoding='utf-8')
        self.assertEqual(run('--errors', other, '--round', 2, '--input', review).returncode, 3)
        self.assertEqual(sorted(p.name for p in self.d.iterdir() if p.name.startswith('.ledger-')), [])

    def test_a_return_saved_verbatim_is_read_from_its_last_fenced_json_block(self):
        obj = {'status': 'completed', 'mode': 'independent', 'verdict': 'blocking', 'review_file': 'review.md ## Round 1 · independent',
               'findings': [{'severity': 'blocking', 'description': 'unchecked path', 'location': 'src/a.py:3'}]}
        report = ('[reviewer · model: opus]\n## Understanding\nreview of {plan_dir} round 1\n## Files\n- src/a.py\n'
                  '## Changes / Plan\n```json\n{"example": true}\n```\n## Validation\nnone\n## Risks\n- none\n## Next Step\nfix\n'
                  '```json\n' + json.dumps(obj, indent=2) + '\n```\n')
        path = self.d / 'review-return.md'
        path.write_text(report, encoding='utf-8')
        res = self.record_round(1, path)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(json.loads(res.stdout)['critical'], 1)
        self.assertIn('unchecked path', self.errors.read_text(encoding='utf-8'))

    def test_a_fenced_block_holding_no_object_is_refused(self):
        path = self.d / 'bad-return.md'
        path.write_text('[test · model: sonnet]\n## Next Step\n```json\nnot json\n```\n', encoding='utf-8')
        self.assertEqual(self.record_round(1, path).returncode, 2)
        self.assertFalse(self.errors.exists())

    def fenced_return(self, name, label, body):
        path = self.d / name
        path.write_text('[test · model: sonnet]\n## Understanding\nreview of {plan_dir} round 1\n## Next Step\nfix\n'
                        f'```{label}\n{body}\n```\n', encoding='utf-8')
        return path

    def test_a_jsonc_fenced_return_is_read_past_a_brace_in_the_prose(self):
        path = self.fenced_return('jsonc-return.md', 'jsonc', json.dumps({'status': 'completed', 'gate': 'GREEN'}, indent=2))
        res = self.record_round(1, path)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(json.loads(res.stdout)['verdict'], 'green')

    def test_an_upper_case_fence_label_is_read(self):
        for label in ('JSONC', 'JSON'):
            with self.subTest(label=label):
                self.errors.unlink(missing_ok=True)
                path = self.fenced_return(f'{label}.md', label, json.dumps({'status': 'completed', 'gate': 'GREEN'}))
                res = self.record_round(1, path)
                self.assertEqual(res.returncode, 0, res.stderr)

    def test_a_jsonc_block_with_a_comment_is_refused_naming_the_block(self):
        path = self.fenced_return('commented.md', 'jsonc', '{ "status": "completed",  // copied from the schema\n  "gate": "GREEN" }')
        res = self.record_round(1, path)
        self.assertEqual(res.returncode, 2)
        self.assertIn('fenced block at line 6 is not valid JSON', res.stderr)
        self.assertFalse(self.errors.exists())


if __name__ == '__main__':
    unittest.main()
