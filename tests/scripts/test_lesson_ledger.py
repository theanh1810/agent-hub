"""Tests for scripts/lesson-ledger.py and its `agent-hub lesson` dispatch: sightings, the lock, a corrupt ledger, seed, decline."""
import datetime
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / 'plugins' / 'agent-hub'
SCRIPT = PLUGIN / 'scripts' / 'lesson-ledger.py'
BIN = PLUGIN / 'bin' / 'agent-hub'
SIGHT = ['sight', '--project', 'p', '--type', 't', '--subject', 's']


def env_for(cfg):
    env = dict(os.environ)
    env['CLAUDE_CONFIG_DIR'] = str(cfg)
    return env


def run(cfg, *args, script=SCRIPT):
    return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, env=env_for(cfg), timeout=60)


class LessonLedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Path(self.tmp.name)
        self.ledger = self.cfg / 'memory' / 'global' / 'lessons.yaml'

    def tearDown(self):
        self.tmp.cleanup()

    def sight(self, ref, date='2026-11-15'):
        return run(self.cfg, *SIGHT, '--ref', ref, '--date', date)

    def test_sightings_count_by_ref(self):
        first = json.loads(self.sight('r1').stdout)
        self.assertEqual(first, {'count': 1, 'stage': 'candidate', 'new': True, 'counted': True})
        self.assertEqual(json.loads(self.sight('r2').stdout)['count'], 2)
        before = self.ledger.read_bytes()
        again = json.loads(self.sight('r2', '2026-11-16').stdout)
        self.assertEqual((again['count'], again['counted']), (2, False))
        self.assertEqual(self.ledger.read_bytes(), before)
        self.assertEqual(oct(self.ledger.stat().st_mode & 0o777), '0o600')

    def test_two_processes_both_land(self):
        procs = [subprocess.Popen([sys.executable, str(SCRIPT), *SIGHT, '--ref', r, '--date', '2026-11-15'], env=env_for(self.cfg),
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for r in ('a', 'b')]
        for p in procs:
            p.communicate(timeout=60)
            self.assertEqual(p.returncode, 0)
        shown = json.loads(run(self.cfg, 'show').stdout)
        self.assertEqual(shown[0]['count'], 2)

    def test_corrupt_ledger_is_never_overwritten(self):
        self.ledger.parent.mkdir(parents=True)
        seed = self.cfg / 'seed.json'
        seed.write_text('{"lessons": []}', encoding='utf-8')
        for content in ('lessons: [\n', '- a\n', 'lessons: 3\n', ''):
            self.ledger.write_text(content, encoding='utf-8')
            before = self.ledger.read_bytes()
            for args in (['sight', '--project', 'p', '--type', 't', '--subject', 's', '--ref', 'r', '--date', 'd'],
                         ['promote', '--project', 'p', '--type', 't', '--subject', 's'],
                         ['decline', '--project', 'p', '--type', 't', '--subject', 's', '--date', 'd'],
                         ['seed', '--json', str(seed)]):
                res = run(self.cfg, *args)
                self.assertEqual(res.returncode, 2, (content, args))
                self.assertEqual(self.ledger.read_bytes(), before)

    def test_dispatcher_lists_lesson(self):
        self.sight('r1')
        shown = subprocess.run([sys.executable, str(BIN), 'lesson', 'show'], capture_output=True, text=True, env=env_for(self.cfg), timeout=60)
        self.assertEqual(shown.returncode, 0)
        self.assertEqual(json.loads(shown.stdout)[0]['subject'], 's')
        helped = subprocess.run([sys.executable, str(BIN), '--help'], capture_output=True, text=True, env=env_for(self.cfg), timeout=60)
        self.assertIn('lesson', helped.stdout)

    def test_seed_merges_seen_and_never_lowers_count(self):
        seed = self.cfg / 'seed.json'
        entry = {'project': 'p', 'type': 't', 'subject': 's'}
        seed.write_text(json.dumps({'lessons': [dict(entry, count=3, seen=[{'date': 'd1', 'ref': 'a'}])]}), encoding='utf-8')
        self.assertEqual(run(self.cfg, 'seed', '--json', str(seed)).returncode, 0)
        seed.write_text(json.dumps({'lessons': [dict(entry, count=1, seen=[{'date': 'd1', 'ref': 'a'}, {'date': 'd2', 'ref': 'b'}])]}), encoding='utf-8')
        self.assertEqual(run(self.cfg, 'seed', '--json', str(seed)).returncode, 0)
        got = json.loads(run(self.cfg, 'show').stdout)[0]
        self.assertEqual(got['count'], 3)
        self.assertEqual([s['ref'] for s in got['seen']], ['a', 'b'])

    def test_seed_bad_input_exits_2_before_any_write(self):
        seed = self.cfg / 'seed.json'
        entry = {'project': 'p', 'type': 't', 'subject': 's', 'count': 1, 'seen': []}
        for content in ('[]', '{"lessons": 3}', 'not json', json.dumps({'lessons': [entry, {'project': 'p', 'type': 't'}]})):
            seed.write_text(content, encoding='utf-8')
            res = run(self.cfg, 'seed', '--json', str(seed))
            self.assertEqual(res.returncode, 2, content)
            self.assertFalse(self.ledger.exists())

    def test_missing_ledger_is_created_as_empty_lessons(self):
        seed = self.cfg / 'seed.json'
        seed.write_text('{"lessons": []}', encoding='utf-8')
        self.assertEqual(run(self.cfg, 'seed', '--json', str(seed)).returncode, 0)
        self.assertEqual(self.ledger.read_text(encoding='utf-8').strip(), 'lessons: []')
        self.assertEqual(json.loads(run(self.cfg, 'show').stdout), [])


    def test_seed_rejects_other_shapes_and_leaves_ledger_alone(self):
        self.sight('r1')
        before = self.ledger.read_bytes()
        seed = self.cfg / 'seed.json'
        entry = {'project': 'p', 'type': 't', 'subject': 's'}
        bad = [dict(entry, count=1, seen=['date.2026-11-15', 'ref.abc']),
               dict(entry, count='3', seen=[{'date': 'd', 'ref': 'a'}]),
               dict(entry, count=True, seen=[]),
               dict(entry, count=1, seen=[{'date': 'd', 'ref': ''}]),
               dict(entry, count=1, seen=[], stage='done')]
        for e in bad:
            seed.write_text(json.dumps({'lessons': [e]}), encoding='utf-8')
            res = run(self.cfg, 'seed', '--json', str(seed))
            self.assertEqual(res.returncode, 2, e)
            self.assertIn('p/t/s', res.stderr)
            self.assertNotIn('Traceback', res.stderr)
            self.assertEqual(self.ledger.read_bytes(), before)

    def test_seed_merges_duplicate_keys_in_one_file(self):
        seed = self.cfg / 'seed.json'
        entry = {'project': 'p', 'type': 't', 'subject': 's'}
        seed.write_text(json.dumps({'lessons': [
            dict(entry, count=2, seen=[{'date': 'd1', 'ref': 'a'}]),
            dict(entry, count=1, stage='promoted', seen=[{'date': 'd1', 'ref': 'a'}, {'date': None, 'ref': 'b'}])]}), encoding='utf-8')
        res = run(self.cfg, 'seed', '--json', str(seed))
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(json.loads(res.stdout), {'seeded': 2, 'merged': 1, 'entries': 1})
        got = json.loads(run(self.cfg, 'show').stdout)
        self.assertEqual(len(got), 1)
        self.assertEqual((got[0]['count'], got[0]['stage']), (2, 'promoted'))
        self.assertEqual([x['ref'] for x in got[0]['seen']], ['a', 'b'])

    def decline(self, *extra):
        return run(self.cfg, 'decline', '--project', 'p', '--type', 't', '--subject', 's', *extra)

    def shown(self):
        return json.loads(run(self.cfg, 'show').stdout)[0]

    def test_decline_is_idempotent_and_a_new_ref_clears_it(self):
        self.sight('r1')
        self.sight('r2')
        self.assertEqual(json.loads(self.decline('--date', '2026-11-16').stdout), {'declined': '2026-11-16', 'changed': True})
        got = self.shown()
        self.assertEqual((got['declined'], got['stage'], got['count'], [s['ref'] for s in got['seen']]),
                         ('2026-11-16', 'candidate', 2, ['r1', 'r2']))
        before = self.ledger.read_bytes()
        self.assertEqual(json.loads(self.decline('--date', '2026-11-16').stdout), {'declined': '2026-11-16', 'changed': False})
        self.assertEqual(self.ledger.read_bytes(), before)
        self.assertEqual(json.loads(self.decline('--date', '2026-11-17').stdout), {'declined': '2026-11-17', 'changed': True})
        self.sight('r2', '2026-11-18')
        self.assertEqual(self.shown()['declined'], '2026-11-17')
        self.sight('r3', '2026-11-19')
        got = self.shown()
        self.assertNotIn('declined', got)
        self.assertEqual((got['count'], got['stage']), (3, 'candidate'))

    def test_decline_defaults_to_the_local_date(self):
        self.sight('r1')
        out = json.loads(self.decline().stdout)
        self.assertEqual(out, {'declined': datetime.date.today().isoformat(), 'changed': True})

    def test_decline_a_missing_or_promoted_entry_exits_2(self):
        res = self.decline('--date', '2026-11-16')
        self.assertEqual(res.returncode, 2)
        self.assertFalse(self.ledger.exists())
        self.sight('r1')
        self.assertEqual(run(self.cfg, 'promote', '--project', 'p', '--type', 't', '--subject', 's').returncode, 0)
        before = self.ledger.read_bytes()
        res = self.decline('--date', '2026-11-16')
        self.assertEqual(res.returncode, 2)
        self.assertNotIn('Traceback', res.stderr)
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_seed_keeps_declined_and_ignores_a_declined_key(self):
        self.sight('r1')
        self.decline('--date', '2026-11-16')
        seed = self.cfg / 'seed.json'
        entry = {'project': 'p', 'type': 't', 'subject': 's', 'count': 5, 'seen': [{'date': 'd', 'ref': 'a'}], 'declined': '2030-01-01'}
        other = dict(entry, subject='s2')
        seed.write_text(json.dumps({'lessons': [entry, other]}), encoding='utf-8')
        self.assertEqual(run(self.cfg, 'seed', '--json', str(seed)).returncode, 0)
        got = {e['subject']: e for e in json.loads(run(self.cfg, 'show').stdout)}
        self.assertEqual(got['s']['declined'], '2026-11-16')
        self.assertNotIn('declined', got['s2'])


if __name__ == '__main__':
    unittest.main()
