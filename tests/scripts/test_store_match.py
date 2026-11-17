"""Tests for scripts/store-match.py against small fake repos under fixtures/store_match and a fixture catalog."""
from pathlib import Path
import contextlib
import io
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / 'plugins' / 'agent-hub' / 'scripts' / 'store-match.py'
FX = Path(__file__).resolve().parent / 'fixtures' / 'store_match'
CATALOG = FX / 'catalog.yaml'


def match(repo, *extra):
    r = subprocess.run([sys.executable, '-I', str(SCRIPT), 'match', '--catalog', str(CATALOG), '--repo', str(FX / repo), *extra],
                       capture_output=True, text=True, env={'PYTHONDONTWRITEBYTECODE': '1'})
    return r


def ids(repo, *extra):
    r = match(repo, *extra)
    assert r.returncode == 0, r.stderr
    return [line.split(' · ')[0] for line in r.stdout.splitlines()]


class MatchTest(unittest.TestCase):
    def test_tsconfig_repo(self):
        self.assertEqual(ids('ts_repo'), ['typescript-pro'])

    def test_artisan_needs_laravel_dep(self):
        self.assertEqual(ids('laravel_repo'), ['laravel-specialist'])

    def test_antd_repo_prints_ready_only(self):
        self.assertEqual(ids('antd_repo'), ['ant-design', 'vue-expert'])

    def test_no_signal_prints_nothing(self):
        r = match('empty_repo')
        self.assertEqual((r.returncode, r.stdout), (0, ''))

    def test_manifest_that_is_not_a_json_object_is_skipped(self):
        for body in ('[]', '"text"', '3', 'null'):
            with tempfile.TemporaryDirectory(prefix='sm-') as d:
                (Path(d) / 'package.json').write_text(body, encoding='utf-8')
                (Path(d) / 'tsconfig.json').write_text('{}', encoding='utf-8')
                r = subprocess.run([sys.executable, '-I', str(SCRIPT), 'match', '--catalog', str(CATALOG), '--repo', d],
                                   capture_output=True, text=True, env={'PYTHONDONTWRITEBYTECODE': '1'})
                self.assertEqual(r.returncode, 0, (body, r.stderr))
                self.assertNotIn('Traceback', r.stderr)
                self.assertIn('typescript-pro', r.stdout)

    def test_missing_or_non_directory_repo_exits_2(self):
        with tempfile.TemporaryDirectory(prefix='sm-') as d:
            f = Path(d) / 'file.txt'
            f.write_text('x', encoding='utf-8')
            for p in (Path(d) / 'nope', f):
                r = subprocess.run([sys.executable, '-I', str(SCRIPT), 'match', '--catalog', str(CATALOG), '--repo', str(p)],
                                   capture_output=True, text=True, env={'PYTHONDONTWRITEBYTECODE': '1'})
                self.assertEqual((r.returncode, r.stdout), (2, ''))
                self.assertEqual(r.stderr.strip(), f'store match: {p} is not a directory')

    def test_header_signal(self):
        self.assertEqual(ids('wp_repo'), ['wordpress-pro'])

    def test_non_ready_never_printed(self):
        out = match('antd_repo').stdout + match('ts_repo').stdout
        for bad in ('ant-design-old', 'blocked-ts'):
            self.assertNotIn(bad, out)

    def test_task_only_row_never_matches(self):
        for repo in ('ts_repo', 'antd_repo', 'empty_repo'):
            self.assertNotIn('first-principles', ids(repo))

    def test_line_shape(self):
        line = match('ts_repo').stdout.splitlines()[0]
        self.assertEqual(line, 'typescript-pro · store/typescript-pro/text.md · writing or reviewing TypeScript')

    def test_files_uses_nearest_package_root(self):
        self.assertEqual(ids('mono_repo'), [])
        self.assertEqual(ids('mono_repo', '--files', 'packages/web/src/a.txt'), ['ant-design'])

    def test_role_filter(self):
        self.assertEqual(ids('antd_repo', '--role', 'designer'), ['ant-design'])

    def test_no_write(self):
        before = sorted(p for p in FX.rglob('*'))
        match('antd_repo')
        self.assertEqual(before, sorted(p for p in FX.rglob('*')))

    def test_list_shows_every_row_with_status(self):
        r = subprocess.run([sys.executable, '-I', str(SCRIPT), 'list', '--catalog', str(CATALOG)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn('ant-design-old · deferred · pin a sha', r.stdout)
        self.assertEqual(len(r.stdout.splitlines()), 9)


if __name__ == '__main__':
    unittest.main()
