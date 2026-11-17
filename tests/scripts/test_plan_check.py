"""Tests for scripts/plan-check.py: the five checks of the plan lane and the approval stamp."""
import contextlib
import importlib.util
import io
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / 'plugins' / 'agent-hub'
SCRIPT = PLUGIN / 'scripts' / 'plan-check.py'
spec = importlib.util.spec_from_file_location('plan_check', SCRIPT)
PC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PC)   # a hyphenated file name: loaded by path

SPEC = """## ADDED Requirements

### Requirement: Login
The system SHALL sign a user in.

#### Scenario: Valid login
- **WHEN** the user sends a right password
- **THEN** a session starts
"""
TASKS = """# Tasks: demo

## Wave 1

- [ ] 1.1 Add login
  Files: src/a.py, src/b.py
  Covers: Valid login
  Done when: login works
  Test: unit, pytest tests/test_a.py

- [ ] 1.2 Add docs
  Files: docs/x.md
  Covers: none
  Done when: docs exist
  Test: none
"""
PLAN_VI = """# Kế hoạch: demo

### 1.1 Thêm đăng nhập

#### Việc làm và lý do

Thêm đăng nhập.

#### Dữ liệu và màn hình bị ảnh hưởng

Bảng users.

### 1.2 Thêm tài liệu

#### Dữ liệu và màn hình bị ảnh hưởng

Không có
"""


def put(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


class Case(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='plan-check-')
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.change = self.root / 'openspec/changes/demo'
        put(self.change / 'specs/auth/spec.md', SPEC)
        put(self.change / 'tasks.md', TASKS)
        put(self.change / 'plan.vi.md', PLAN_VI)
        put(self.change / 'design.md', 'Design prose.\n')
        words = self.root / 'words.txt'
        put(words, 'duyệt kế hoạch này\n')
        self.stamp()

    def stamp(self):
        self.assertEqual(PC.main(['stamp', str(self.change), '--words', str(self.root / 'words.txt')]), 0)

    def failed(self, stamped=False):
        """-> the numbers of the checks that fail (a pending check is not a failure)"""
        return [n for n, ok, _ in PC.run_checks(self.change, stamped=stamped) if ok is False]


class CheckTests(Case):
    def test_good_folder_passes_all_five(self):
        self.assertEqual(self.failed(), [])
        self.assertEqual(PC.main([str(self.change)]), 0)

    def test_missing_key_fails_check_1(self):
        put(self.change / 'tasks.md', TASKS.replace('  Test: unit, pytest tests/test_a.py\n', ''))
        self.assertEqual(self.failed(), [1, 4])   # the stamp is not computed while check 1 fails

    def test_unknown_scenario_fails_check_2(self):
        put(self.change / 'tasks.md', TASKS.replace('Covers: Valid login', 'Covers: Valid login, Ghost scenario'))
        self.assertIn(2, self.failed())

    def test_live_spec_scenario_counts(self):
        put(self.root / 'openspec/specs/pay/spec.md', '#### Scenario: Paid\n')
        put(self.change / 'tasks.md', TASKS.replace('Covers: Valid login', 'Covers: Paid'))
        self.assertNotIn(2, self.failed())

    def test_id_only_in_tasks_fails_check_3(self):
        put(self.change / 'plan.vi.md', PLAN_VI.split('### 1.2')[0])
        self.assertIn(3, self.failed())

    def test_id_only_in_plan_vi_fails_check_3(self):
        put(self.change / 'plan.vi.md', PLAN_VI + '\n### 9.9 Thừa\n\n#### Dữ liệu và màn hình bị ảnh hưởng\n\nKhông có\n')
        self.assertIn(3, self.failed())

    def test_added_file_path_makes_the_stamp_stale(self):
        put(self.change / 'tasks.md', TASKS.replace('Files: docs/x.md', 'Files: docs/x.md, docs/y.md'))
        self.assertEqual(self.failed(stamped=True), [4])

    def test_missing_stamp_fails_check_4_when_stamped_is_required(self):
        (self.change / 'approval.md').unlink()
        self.assertEqual(self.failed(stamped=True), [4])

    def test_missing_stamp_is_pending_before_the_gate(self):
        (self.change / 'approval.md').unlink()
        self.assertEqual(self.failed(), [])
        self.assertEqual([r for r in PC.run_checks(self.change) if r[0] == 4], [(4, None, 'not stamped yet (pending)')])
        self.assertEqual(PC.main([str(self.change)]), 0)

    def test_missing_stamp_with_flag_exits_1(self):
        (self.change / 'approval.md').unlink()
        self.assertEqual(PC.main([str(self.change), '--stamped']), 1)

    def test_stale_stamp_is_pending_before_the_gate_and_fails_when_stamped(self):
        put(self.change / 'tasks.md', TASKS.replace('Files: docs/x.md', 'Files: docs/x.md, docs/y.md'))
        self.assertEqual(self.failed(), [])
        detail = [r for r in PC.run_checks(self.change) if r[0] == 4][0]
        self.assertIsNone(detail[1])
        self.assertTrue(detail[2].startswith('stamp ') and detail[2].endswith(': re-approval pending'), detail)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(PC.main([str(self.change)]), 0)
        self.assertEqual(out.getvalue().splitlines()[-1], 'plan-check: 4/4 passed, stamp pending')
        self.assertEqual(self.failed(stamped=True), [4])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(PC.main([str(self.change), '--stamped']), 1)

    def test_stale_stamp_with_another_failure_exits_1(self):
        put(self.change / 'tasks.md', TASKS.replace('Files: docs/x.md', 'Files: docs/x.md, docs/y.md')
            .replace('Covers: Valid login', 'Covers: Valid login, Ghost scenario'))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(PC.main([str(self.change)]), 1)
        self.assertEqual(out.getvalue().splitlines()[-1], 'plan-check: 3/5 passed')

    def test_restamp_keeps_earlier_words(self):
        words_a = (self.root / 'words.txt').read_text(encoding='utf-8').strip()
        old = PC.STAMP_LINE.search((self.change / 'approval.md').read_text(encoding='utf-8')).group(1)
        put(self.change / 'tasks.md', TASKS.replace('Files: docs/x.md', 'Files: docs/x.md, docs/y.md'))
        put(self.root / 'words2.txt', 'duyệt lại bản đã sửa\n')
        self.assertEqual(PC.main(['stamp', str(self.change), '--words', str(self.root / 'words2.txt')]), 0)
        text = (self.change / 'approval.md').read_text(encoding='utf-8')
        self.assertEqual(re.findall(r'(?m)^stamp:.*$', text), [f'stamp: {PC.compute_stamp(self.change)}'])
        self.assertIn('## Earlier approvals', text)
        self.assertIn(f'### earlier stamp {old}', text)
        self.assertIn(words_a, text)
        self.assertIn('duyệt lại bản đã sửa', text.split('## Earlier approvals')[0])
        self.assertEqual(PC.main([str(self.change), '--stamped']), 0)

    def test_second_restamp_keeps_both_earlier_blocks(self):
        first = PC.STAMP_LINE.search((self.change / 'approval.md').read_text(encoding='utf-8')).group(1)
        put(self.change / 'tasks.md', TASKS.replace('Files: docs/x.md', 'Files: docs/x.md, docs/y.md'))
        put(self.root / 'w2.txt', 'hai\n')
        self.assertEqual(PC.main(['stamp', str(self.change), '--words', str(self.root / 'w2.txt')]), 0)
        second = PC.STAMP_LINE.search((self.change / 'approval.md').read_text(encoding='utf-8')).group(1)
        put(self.change / 'tasks.md', TASKS.replace('Files: docs/x.md', 'Files: docs/x.md, docs/z.md'))
        put(self.root / 'w3.txt', 'ba\n')
        self.assertEqual(PC.main(['stamp', str(self.change), '--words', str(self.root / 'w3.txt')]), 0)
        text = (self.change / 'approval.md').read_text(encoding='utf-8')
        self.assertEqual(len(re.findall(r'(?m)^stamp:', text)), 1)
        self.assertLess(text.index(f'### earlier stamp {second}'), text.index(f'### earlier stamp {first}'))
        self.assertIn('duyệt kế hoạch này', text)

    def test_changed_spec_makes_the_stamp_stale(self):
        put(self.change / 'specs/auth/spec.md', SPEC + '\n#### Scenario: Another\n')
        self.assertEqual(self.failed(stamped=True), [4])

    def test_rewording_prose_keeps_the_stamp_current(self):
        put(self.change / 'design.md', 'Other design words.\n')
        put(self.change / 'plan.vi.md', PLAN_VI.replace('Thêm đăng nhập.', 'Viết lại câu khác.'))
        self.assertEqual(self.failed(), [])

    def test_block_without_the_data_heading_fails_check_5(self):
        put(self.change / 'plan.vi.md', PLAN_VI.replace('#### Dữ liệu và màn hình bị ảnh hưởng\n\nBảng users.\n', 'Bảng users.\n'))
        self.assertEqual(self.failed(), [5])

    def test_duplicate_task_id_fails_check_1_and_names_the_id(self):
        put(self.change / 'tasks.md', TASKS + "\n- [ ] 1.2 Again\n  Files: docs/z.md\n  Covers: none\n  Done when: x\n  Test: none\n")
        res = {n: (ok, d) for n, ok, d in PC.run_checks(self.change)}
        self.assertIs(res[1][0], False)
        self.assertIn('duplicate task id 1.2', res[1][1])

    def test_duplicate_task_id_keeps_the_stamp_uncomputed(self):
        put(self.change / 'tasks.md', TASKS + "\n- [ ] 1.2 Again\n  Files: docs/z.md\n  Covers: none\n  Done when: x\n  Test: none\n")
        res = {n: (ok, d) for n, ok, d in PC.run_checks(self.change)}
        self.assertIs(res[4][0], False)
        self.assertIn('not computed', res[4][1])
        self.assertEqual(PC.main(['stamp', str(self.change), '--words', str(self.root / 'words.txt')]), 1)

    def test_task_line_before_any_wave_fails_check_1(self):
        put(self.change / 'tasks.md', TASKS.replace('## Wave 1\n', ''))
        res = {n: (ok, d) for n, ok, d in PC.run_checks(self.change)}
        self.assertIs(res[1][0], False)
        self.assertIn('1.1', res[1][1])
        self.assertIn('outside', res[1][1])

    def test_task_under_a_malformed_wave_heading_fails_check_1(self):
        for bad in ('## Wave', '### Wave 1', '## Wave one', '## Notes'):
            put(self.change / 'tasks.md', TASKS.replace('## Wave 1', bad))
            self.assertIn(1, self.failed(), bad)

    def test_wave_heading_with_a_title_is_accepted(self):
        put(self.change / 'tasks.md', TASKS.replace('## Wave 1', '## Wave 1: login'))
        self.assertNotIn(1, self.failed())

    def test_duplicate_block_in_plan_vi_fails_check_3(self):
        put(self.change / 'plan.vi.md', PLAN_VI + '\n### 1.2 Lặp\n\nKhông có dữ liệu\n')
        res = {n: (ok, d) for n, ok, d in PC.run_checks(self.change)}
        self.assertIs(res[3][0], False)
        self.assertIn('duplicate task id 1.2 in plan.vi.md', res[3][1])

    def test_prose_mentioning_the_heading_does_not_satisfy_check_5(self):
        put(self.change / 'plan.vi.md', PLAN_VI.replace('#### Dữ liệu và màn hình bị ảnh hưởng\n\nBảng users.\n',
                                                         'Xem mục #### Dữ liệu và màn hình bị ảnh hưởng ở dưới.\n'))
        self.assertEqual(self.failed(), [5])

    def test_deeper_heading_does_not_satisfy_check_5(self):
        put(self.change / 'plan.vi.md', PLAN_VI.replace('#### Dữ liệu', '##### Dữ liệu', 1))
        self.assertEqual(self.failed(), [5])

    def test_nfd_heading_satisfies_check_5(self):
        import unicodedata
        put(self.change / 'plan.vi.md', unicodedata.normalize('NFD', PLAN_VI))
        self.assertNotIn(5, self.failed())

    def test_cli_last_line_and_exit_code(self):
        run = lambda: subprocess.run([sys.executable, str(SCRIPT), str(self.change)], capture_output=True, text=True)
        ok = run()
        self.assertEqual((ok.returncode, ok.stdout.splitlines()[-1]), (0, 'plan-check: 5/5 passed'))
        (self.change / 'approval.md').unlink()
        bad = run()
        self.assertEqual((bad.returncode, bad.stdout.splitlines()[-1]), (0, 'plan-check: 4/4 passed, stamp pending'))
        bad = subprocess.run([sys.executable, str(SCRIPT), str(self.change), '--stamped'], capture_output=True, text=True)
        self.assertEqual((bad.returncode, bad.stdout.splitlines()[-1]), (1, 'plan-check: 4/5 passed'))

    def test_stamp_file_holds_the_words_verbatim(self):
        text = (self.change / 'approval.md').read_text(encoding='utf-8')
        self.assertRegex(text, r'(?m)^stamp: [0-9a-f]{12}$')
        self.assertIn("## User's words\n\nduyệt kế hoạch này", text)


class TemplateTests(unittest.TestCase):
    def test_filled_templates_pass_all_five(self):
        tmp = tempfile.TemporaryDirectory(prefix='plan-check-')
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name).resolve()
        change = root / 'openspec/changes/demo'
        fill = lambda s: re.sub(r'\{\{[^}]*\}\}', lambda m: {
            '{{scenario name}}': 'Valid login', '{{path one}}': 'src/a.py', '{{path two}}': 'src/b.py'}.get(m.group(0), 'x'), s)
        put(change / 'specs/auth/spec.md', SPEC)
        put(change / 'tasks.md', fill((PLUGIN / 'templates/plan/tasks-template.md').read_text(encoding='utf-8')))
        put(change / 'plan.vi.md', fill((PLUGIN / 'templates/plan/plan.vi-template.md').read_text(encoding='utf-8')))
        put(root / 'w.txt', 'duyệt\n')
        self.assertEqual(PC.main(['stamp', str(change), '--words', str(root / 'w.txt')]), 0)
        self.assertEqual([n for n, ok, _ in PC.run_checks(change) if not ok], [])


if __name__ == '__main__':
    unittest.main()
