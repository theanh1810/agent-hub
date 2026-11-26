"""templates/gate/gate.sh: step_opt prints one SKIP line for a missing tool and passes; the path-trust rules match their
fixtures; the commented `paths` lines scan only changed source files outside the rule folder."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / 'plugins' / 'agent-hub' / 'templates' / 'gate'
MISSING = 'agent-hub-no-such-tool'
MARKER = 'if [ "$STEPS" -eq 0 ]'


class GateRepo:
    """A temp repo holding the template as scripts/gate.sh."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='gate-')
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name).resolve()
        self.log = self.repo / 'gate.log'

    def run_gate(self, *lines, path=None):
        """The template with `lines` placed before its no-step check, run from a temp repo (`path`: its PATH)."""
        text = (GATE / 'gate.sh').read_text(encoding='utf-8')
        self.assertIn(MARKER, text)
        script = self.repo / 'scripts' / 'gate.sh'
        script.parent.mkdir(exist_ok=True)
        script.write_text(text.replace(MARKER, '\n'.join(lines) + '\n' + MARKER, 1), encoding='utf-8')
        env = dict(os.environ, GATE_LOG=str(self.log))
        if path is not None:
            env['PATH'] = path
        return subprocess.run(['bash', str(script)], capture_output=True, text=True, env=env, timeout=60)


@unittest.skipIf(os.name == 'nt', 'bash on Windows runners may resolve to WSL; the template is exercised on POSIX hosts')
class StepOpt(GateRepo, unittest.TestCase):
    def test_missing_tool_prints_skip_and_passes(self):
        self.assertIsNone(shutil.which(MISSING))
        r = self.run_gate('step ok true', f'step_opt paths {MISSING} false')
        out = r.stdout.splitlines()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f'SKIP paths: {MISSING} not installed', out)
        self.assertIn(f'SKIP paths: {MISSING} not installed', self.log.read_text(encoding='utf-8'))
        self.assertEqual(out[-1], 'gate: 1 steps passed')

    def test_present_tool_runs_as_step(self):
        r = self.run_gate('step_opt paths sh false')
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertTrue(any(l.startswith('FAIL paths (exit 1)') for l in r.stdout.splitlines()), r.stdout)


@unittest.skipUnless(shutil.which('semgrep'), 'semgrep not installed')
class PathTrustRules(unittest.TestCase):
    def test_fixtures_match(self):
        rules = GATE / 'semgrep'
        r = subprocess.run(['semgrep', '--test', '--metrics', 'off', '--config', str(rules), str(rules / 'tests')],
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])


PATHS_LINES = ('# SRC=', '# if ! command -v semgrep', '#   PATHS_BASE=', '#   CHANGED=', '#   if [ -n "$CHANGED" ]', '# fi')


class PathsRepo(GateRepo):
    """A temp git repo on `main` with one commit and the rule folder at scripts/semgrep."""

    def setUp(self):
        super().setUp()
        self.git('init', '-q', '-b', 'main')
        self.git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--allow-empty', '-m', 'base')
        shutil.copytree(GATE / 'semgrep', self.repo / 'scripts' / 'semgrep')

    def git(self, *args):
        subprocess.run(['git', *args], cwd=self.repo, check=True, capture_output=True, timeout=60)

    def paths_lines(self, base='main'):
        text = (GATE / 'gate.sh').read_text(encoding='utf-8')
        lines = [l[2:].replace('origin/main', base) for l in text.splitlines() if l.startswith(PATHS_LINES)]
        self.assertEqual(len(lines), len(PATHS_LINES), lines)
        return lines


@unittest.skipIf(os.name == 'nt', 'bash on Windows runners may resolve to WSL; the template is exercised on POSIX hosts')
@unittest.skipUnless(shutil.which('semgrep') and shutil.which('git'), 'semgrep or git not installed')
class PathsStep(PathsRepo, unittest.TestCase):
    """The template's commented `paths` lines, uncommented, scan only changed source files outside the rule folder."""

    def test_scans_changed_source_outside_rule_folder(self):
        (self.repo / 'src').mkdir()
        (self.repo / 'src' / 'a.py').write_text('import sys\nopen(sys.argv[1])\n', encoding='utf-8')
        r = self.run_gate('step ok true', *self.paths_lines())
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertTrue(any(l.startswith('FAIL paths (exit 1)') for l in r.stdout.splitlines()), r.stdout)
        log = self.log.read_text(encoding='utf-8')
        self.assertIn('src/a.py', log)
        self.assertNotIn('scripts/semgrep/tests', log)

    def test_no_changed_source_runs_no_paths_step(self):
        (self.repo / 'README.md').write_text('x\n', encoding='utf-8')
        r = self.run_gate('step ok true', *self.paths_lines())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn('paths', r.stdout)


@unittest.skipIf(os.name == 'nt', 'bash on Windows runners may resolve to WSL; the template is exercised on POSIX hosts')
@unittest.skipUnless(shutil.which('git'), 'git not installed')
class PathsNoMergeBase(PathsRepo, unittest.TestCase):
    """With no merge base, the `paths` lines print the SKIP line when semgrep is missing and FAIL when it is present."""

    def path_without_semgrep(self):
        dirs = os.environ['PATH'].split(os.pathsep)
        return os.pathsep.join(d for d in dirs if not (Path(d) / 'semgrep').exists())

    def test_missing_semgrep_prints_skip(self):
        path = self.path_without_semgrep()
        self.assertIsNone(shutil.which('semgrep', path=path))
        r = self.run_gate('step ok true', *self.paths_lines(base='origin/main'), path=path)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('SKIP paths: semgrep not installed', r.stdout.splitlines())

    def test_present_semgrep_fails(self):
        stub = self.repo / 'stub-bin'
        stub.mkdir()
        (stub / 'semgrep').write_text('#!/bin/sh\nexit 0\n', encoding='utf-8')
        (stub / 'semgrep').chmod(0o755)
        path = str(stub) + os.pathsep + self.path_without_semgrep()
        r = self.run_gate('step ok true', *self.paths_lines(base='origin/main'), path=path)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn('FAIL paths: no merge base with origin/main', r.stdout.splitlines())


if __name__ == '__main__':
    unittest.main()
