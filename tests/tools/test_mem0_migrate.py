"""Tests for tools/mem0-to-claude-mem.py: the plan mapping, the seeds, byte-exact text, and the idempotent post.
Run: python3 -I -m unittest discover -s tests/tools -p 'test_mem0_migrate.py'  (from the repo root; the file loads nothing from the repo)."""
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / 'tools' / 'mem0-to-claude-mem.py'
VI_TEXT = 'Không đổi chữ Việt: thử nghiệm ✓\nhai dòng'  # scrub-allow: fixture byte-exact


def run(*args):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, encoding='utf-8', timeout=60)


def memory(mem_id, text, **metadata):
    return {'id': mem_id, 'memory': text, 'metadata': metadata, 'categories': [], 'created_at': '2026-11-01', 'updated_at': '2026-11-01'}


class Worker(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])).decode('utf-8'))
        self.server.bodies.append(body)
        bad = body.get('title') in self.server.fail_titles
        self.send_response(500 if bad else 200)
        self.end_headers()
        self.wfile.write(b'worker said no' if bad else b'{}')

    def log_message(self, *args):
        pass


class Case(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.root = Path(self._td.name)
        self.out = self.root / 'out'
        self.srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Worker)
        self.srv.bodies, self.srv.fail_titles = [], set()
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)

    def plan(self, memories):
        export = self.root / 'export.json'
        export.write_text(json.dumps(memories, ensure_ascii=False), encoding='utf-8')
        return run('plan', '--export', str(export), '--out', str(self.out))

    def payloads(self):
        return [json.loads(line) for line in (self.out / 'payloads.jsonl').read_text(encoding='utf-8').split('\n') if line]

    def seeds(self):
        return json.loads((self.out / 'lesson-seeds.json').read_text(encoding='utf-8'))['lessons']

    def evidence(self, endpoint='default'):
        if endpoint == 'default':
            endpoint = {'method': 'POST', 'path': '/api/memory/save', 'body_fields': ['project', 'title', 'text', 'metadata']}
        path = self.root / 'claude-mem.yaml'
        path.write_text(yaml.safe_dump({'worker': {'port': self.srv.server_port, 'base_url': 'http://127.0.0.1:%d' % self.srv.server_port,
                                                   'save_endpoint': endpoint, 'delete_endpoint': None, 'count_endpoint': None}}), encoding='utf-8')
        return path

    def post(self, evidence=None):
        return run('post', '--payloads', str(self.out / 'payloads.jsonl'), '--done', str(self.out / 'done.log'),
                   '--evidence', str(evidence or self.evidence()))


class PlanTest(Case):
    def test_project_mapping_and_title(self):
        res = self.plan([memory('a', 'fleet lesson', project='fleet', subject='s-fleet'),
                         memory('b', 'global scope', project='acme', scope='global', subject='s-global'),
                         memory('c', 'no project at all'),
                         memory('d', 'x' * 100, project='acme-fe')])
        self.assertEqual(res.returncode, 0)
        self.assertEqual(json.loads(res.stdout), {'payloads': 4, 'seeds': 0, 'seed_inputs': 0, 'unparsed_seen': [], 'out': str(self.out)})
        got = self.payloads()
        self.assertEqual([p['project'] for p in got], ['global', 'global', 'global', 'acme-fe'])
        self.assertEqual([p['title'] for p in got], ['s-fleet', 's-global', 'no project at all', 'x' * 60])
        self.assertEqual([p['metadata']['mem0_id'] for p in got], ['a', 'b', 'c', 'd'])
        self.assertEqual(got[3]['metadata']['project'], 'acme-fe')

    def test_recurring_pitfall_seeds(self):
        seen = [{'date': '2026-10-01', 'ref': 'r1'}, {'date': '2026-10-02', 'ref': 'r2'}, {'date': '2026-10-03', 'ref': 'r3'}]
        res = self.plan([memory('a', 'no count', project='fleet', type='recurring_pitfall', subject='trap-a', scope='fleet', reader='main'),
                         memory('b', 'counted', project='acme', type='recurring_pitfall', subject='trap-b', count=3, seen=seen, stage='pattern'),
                         memory('c', 'not a pitfall', project='acme', type='architecture_decision', subject='arch-c')])
        self.assertEqual(json.loads(res.stdout)['seeds'], 2)
        first, second = self.seeds()
        self.assertEqual((first['project'], first['subject'], first['count'], first['seen'], first['stage']), ('global', 'trap-a', 2, [], 'candidate'))
        self.assertEqual((first['scope'], first['reader']), ('fleet', 'main'))
        self.assertEqual((second['project'], second['count'], second['seen'], second['stage']), ('acme', 3, seen, 'promoted'))

    def test_live_shape_seen_strings_and_string_count(self):
        res = self.plan([memory('69db', 'live', project='acme', type='recurring_pitfall', subject='trap-live',
                                seen=['date.2026-11-05', 'ref.docs/x.yaml'], count='1')])
        self.assertEqual(json.loads(res.stdout)['unparsed_seen'], [])
        (got,) = self.seeds()
        self.assertEqual((got['count'], got['seen']), (1, [{'date': '2026-11-05', 'ref': 'docs/x.yaml'}]))
        ledger_cfg = self.root / 'cfg'
        seed = subprocess.run([sys.executable, str(REPO / 'plugins' / 'agent-hub' / 'bin' / 'agent-hub'), 'lesson', 'seed', '--json', str(self.out / 'lesson-seeds.json')],
                              capture_output=True, text=True, env=dict(os.environ, CLAUDE_CONFIG_DIR=str(ledger_cfg)), timeout=60)
        self.assertEqual(seed.returncode, 0, seed.stderr)

    def test_duplicate_subjects_merge_into_one_seed(self):
        res = self.plan([memory('a', 'one', project='acme', type='recurring_pitfall', subject='dup', count=1, seen=[{'date': '2026-10-02', 'ref': 'r2'}]),
                         memory('b', 'two', project='acme', type='recurring_pitfall', subject='dup', count='4', seen=['date.2026-10-01', 'ref.r1']),
                         memory('c', 'three', project='acme', type='recurring_pitfall', subject='other', count=1)])
        out = json.loads(res.stdout)
        self.assertEqual((out['seeds'], out['seed_inputs']), (2, 3))
        dup = [s for s in self.seeds() if s['subject'] == 'dup'][0]
        self.assertEqual([x['ref'] for x in dup['seen']], ['r1', 'r2'])
        self.assertEqual(dup['count'], 4)

    def test_stage_mapping_and_unparsed_items(self):
        res = self.plan([memory('s1', 'x', project='acme', type='recurring_pitfall', subject='s-cand', stage='candidate'),
                         memory('s2', 'x', project='acme', type='recurring_pitfall', subject='s-wait', stage='awaiting_approval'),
                         memory('s3', 'x', project='acme', type='recurring_pitfall', subject='s-pat', stage='pattern'),
                         memory('s4', 'x', project='acme', type='recurring_pitfall', subject='s-bad', seen=['date.2026-11-05', 7, 'plain'], count='many')])
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(json.loads(res.stdout)['unparsed_seen'], ['s4'])
        by = {s['subject']: s for s in self.seeds()}
        self.assertEqual([by[k]['stage'] for k in ('s-cand', 's-wait', 's-pat')], ['candidate', 'candidate', 'promoted'])
        self.assertEqual((by['s-bad']['count'], by['s-bad']['seen']), (2, []))

    def test_text_bytes_equal_the_export(self):
        self.plan([memory('a', VI_TEXT, project='acme', subject='vi'), memory('b', 'plain', project='acme')])
        self.assertEqual([p['text'].encode('utf-8') for p in self.payloads()], [VI_TEXT.encode('utf-8'), b'plain'])

    def test_rows_without_user_id_map_like_any_other(self):
        rows = [dict(memory('u', 'with user', project='acme', subject='su'), user_id='mem0-mcp'),
                dict(memory('g', 'agent row', project='acme', subject='sg'), agent_id='codex'),
                dict(memory('s', 'session row', project='acme', subject='ss'), session_id='s1')]
        res = self.plan(rows)
        self.assertEqual((res.returncode, json.loads(res.stdout)['payloads']), (0, 3))
        self.assertEqual([p['metadata']['mem0_id'] for p in self.payloads()], ['u', 'g', 's'])

    def test_export_that_is_not_an_array_exits_2_and_writes_nothing(self):
        export = self.root / 'export.json'
        export.write_text('{"id": "a"}', encoding='utf-8')
        res = run('plan', '--export', str(export), '--out', str(self.out))
        self.assertEqual(res.returncode, 2)
        self.assertFalse(self.out.exists())


class PostTest(Case):
    def test_done_log_skips_and_resumes(self):
        self.plan([memory('a', 'one', project='acme', subject='t1'), memory('b', 'two', project='acme', subject='t2')])
        self.out.joinpath('done.log').write_text('a\n', encoding='utf-8')
        res = self.post()
        self.assertEqual((res.returncode, json.loads(res.stdout)), (0, {'posted': 1, 'skipped': 1}))
        self.assertEqual([b['title'] for b in self.srv.bodies], ['t2'])
        self.assertEqual((self.out / 'done.log').read_text(encoding='utf-8'), 'a\nb\n')
        again = self.post()
        self.assertEqual(json.loads(again.stdout), {'posted': 0, 'skipped': 2})
        self.assertEqual(len(self.srv.bodies), 1)

    def test_posted_text_equals_the_export_text(self):
        self.plan([memory('a', VI_TEXT, project='acme', subject='vi')])
        self.assertEqual(self.post().returncode, 0)
        self.assertEqual(self.srv.bodies[0]['text'].encode('utf-8'), VI_TEXT.encode('utf-8'))
        self.assertEqual(self.srv.bodies[0]['metadata']['mem0_id'], 'a')

    def test_fields_the_worker_does_not_accept_fold_into_the_text(self):
        self.plan([memory('a', 'body', project='acme', subject='t1')])
        res = self.post(self.evidence({'method': 'POST', 'path': '/save', 'body_fields': ['project', 'title', 'text']}))
        self.assertEqual(res.returncode, 0)
        sent = self.srv.bodies[0]
        self.assertEqual(set(sent), {'project', 'title', 'text'})
        self.assertTrue(sent['text'].startswith('body\nmeta: '))
        self.assertEqual(json.loads(sent['text'].split('\nmeta: ', 1)[1])['metadata']['mem0_id'], 'a')

    def test_no_save_endpoint_exits_3_and_posts_nothing(self):
        self.plan([memory('a', 'one', project='acme', subject='t1')])
        res = self.post(self.evidence(None))
        self.assertEqual(res.returncode, 3)
        self.assertIn('feed the JSONL through the save tool', res.stderr)
        self.assertEqual(self.srv.bodies, [])
        self.assertFalse((self.out / 'done.log').exists())

    def test_first_non_2xx_stops_with_exit_1_and_keeps_the_done_log(self):
        self.plan([memory('a', 'one', project='acme', subject='t1'), memory('b', 'two', project='acme', subject='t2'),
                   memory('c', 'three', project='acme', subject='t3')])
        self.srv.fail_titles = {'t2'}
        res = self.post()
        self.assertEqual(res.returncode, 1)
        self.assertIn('worker said no', res.stderr)
        self.assertEqual((self.out / 'done.log').read_text(encoding='utf-8'), 'a\n')
        self.assertEqual([b['title'] for b in self.srv.bodies], ['t1', 't2'])


if __name__ == '__main__':
    unittest.main()
