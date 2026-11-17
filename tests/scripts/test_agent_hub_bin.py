"""Tests for bin/agent-hub: `check plan` takes the folder from its arguments and always runs the five checks."""
import contextlib
import importlib.machinery
import importlib.util
import io
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PLUGIN = Path(__file__).resolve().parents[2] / 'plugins' / 'agent-hub'
loader = importlib.machinery.SourceFileLoader('agent_hub_bin', str(PLUGIN / 'bin' / 'agent-hub'))
spec = importlib.util.spec_from_loader('agent_hub_bin', loader)
BIN = importlib.util.module_from_spec(spec)
loader.exec_module(BIN)

TASKS = """# Tasks: demo

## Wave 1

- [ ] 1.1 Add login
  Files: src/a.py
  Covers: none
  Done when: login works
  Test: none
"""
PLAN_VI = "# Kế hoạch\n\n### 1.1 Thêm\n\n#### Dữ liệu và màn hình bị ảnh hưởng\n\nKhông có\n"  # scrub-allow: Vietnamese heading the check matches


class CheckPlanTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='agent-hub-bin-')
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.change = self.root / 'openspec/changes/demo'
        self.change.mkdir(parents=True)
        (self.change / 'tasks.md').write_text(TASKS, encoding='utf-8')
        (self.change / 'plan.vi.md').write_text(PLAN_VI, encoding='utf-8')
        self.bin = self.root / 'fakebin'
        self.bin.mkdir()
        self.args_file = self.root / 'openspec-args.txt'
        fake = self.bin / 'openspec'
        fake.write_text(f'#!/bin/sh\necho "$@" > "{self.args_file}"\nexit 1\n', encoding='utf-8')
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

    def run_check(self, argv):
        out = io.StringIO()
        env = {**os.environ, 'PATH': f'{self.bin}{os.pathsep}{os.environ["PATH"]}'}
        with mock.patch.dict(os.environ, env, clear=True), contextlib.redirect_stdout(out):
            code = BIN.check_plan(PLUGIN, argv)
        return code, out.getvalue()

    def test_flag_before_the_folder_is_not_taken_for_the_change_name(self):
        self.run_check(['--stamped', str(self.change)])
        self.assertEqual(self.args_file.read_text().split(), ['validate', 'demo', '--strict'])

    def test_a_failed_openspec_validate_still_prints_the_five_checks(self):
        code, out = self.run_check([str(self.change)])
        self.assertNotEqual(code, 0)
        self.assertIn('plan-check:', out)
        self.assertIn('PASS 1 ok', out)

    def test_no_folder_is_exit_2(self):
        self.assertEqual(self.run_check(['--stamped'])[0], 2)


if __name__ == '__main__':
    unittest.main()
