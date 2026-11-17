"""Tests for plugins/agent-hub/hooks/format_on_edit.py: opt-in gate, local prettier, local eslint, fail open."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / 'plugins' / 'agent-hub' / 'hooks' / 'format_on_edit.py'


def run(payload, opt_in=True, raw=None):
    env = dict(os.environ)
    env.pop('AGENT_HUB_FORMAT_ON_EDIT', None)
    if opt_in:
        env['AGENT_HUB_FORMAT_ON_EDIT'] = '1'
    data = raw if raw is not None else json.dumps(payload)
    return subprocess.run([sys.executable, str(SCRIPT)], input=data, capture_output=True, text=True, env=env, timeout=30)


def fake_bin(root, name, body):
    d = Path(root) / 'node_modules' / '.bin'
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text('#!/bin/sh\n' + body, encoding='utf-8')
    p.chmod(p.stat().st_mode | stat.S_IXUSR)
    return p


class FormatOnEditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'package.json').write_text('{}', encoding='utf-8')
        self.src = self.root / 'a.ts'
        self.src.write_text('let  x=1\n', encoding='utf-8')
        self.payload = {'tool_name': 'Edit', 'tool_input': {'file_path': str(self.src)}}

    def tearDown(self):
        self.tmp.cleanup()

    def test_opt_out_runs_nothing(self):
        mark = self.root / 'called'
        fake_bin(self.root, 'prettier', 'touch "%s"\n' % mark)
        res = run(self.payload, opt_in=False)
        self.assertEqual((res.returncode, res.stdout, res.stderr), (0, '', ''))
        self.assertFalse(mark.exists())

    def test_local_prettier_rewrites_the_file(self):
        fake_bin(self.root, 'prettier', 'echo "$@" > "%s/args"\nprintf "let x = 1;\\n" > "$2"\n' % self.root)
        res = run(self.payload)
        self.assertEqual(res.returncode, 0)
        self.assertEqual(self.src.read_text(encoding='utf-8'), 'let x = 1;\n')
        self.assertIn('--write', (self.root / 'args').read_text(encoding='utf-8'))

    def test_eslint_findings_exit_2_with_at_most_20_lines(self):
        fake_bin(self.root, 'eslint', 'i=0; while [ $i -lt 30 ]; do echo "finding $i"; i=$((i+1)); done\nexit 1\n')
        res = run(self.payload)
        self.assertEqual(res.returncode, 2)
        self.assertEqual(len(res.stderr.strip().splitlines()), 20)

    def test_eslint_clean_exits_0(self):
        fake_bin(self.root, 'eslint', 'exit 0\n')
        res = run(self.payload)
        self.assertEqual((res.returncode, res.stderr), (0, ''))

    def test_no_tools_bad_stdin_missing_file_fail_open(self):
        for res in (run(self.payload), run(None, raw='not json'),
                    run({'tool_input': {'file_path': str(self.root / 'gone.ts')}}), run({'tool_input': {}})):
            self.assertEqual((res.returncode, res.stdout, res.stderr), (0, '', ''))


if __name__ == '__main__':
    unittest.main()
