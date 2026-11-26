"""idle-report.py: per agent type, the model calls, cache writes and the cache rewritten after an idle gap."""
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / 'plugins' / 'agent-hub'
SCRIPT = PLUGIN / 'scripts' / 'idle-report.py'
PRIVATE = 'PRIVATE-TEXT-never-printed'


def run(*args):
    return subprocess.run([sys.executable, '-B', '-I', str(SCRIPT), *map(str, args)], capture_output=True, text=True, timeout=20)


def call(message_id, stamp, write=0, read=0, m5=None, h1=0, model='claude-test'):
    """One assistant line of a transcript; `m5` defaults to the whole write."""
    usage = {'cache_creation_input_tokens': write, 'cache_read_input_tokens': read, 'output_tokens': 1,
             'cache_creation': {'ephemeral_5m_input_tokens': write - h1 if m5 is None else m5,
                                'ephemeral_1h_input_tokens': h1}}
    return {'type': 'assistant', 'timestamp': stamp, 'cwd': '/' + PRIVATE,
            'message': {'id': message_id, 'model': model, 'usage': usage,
                        'content': [{'type': 'text', 'text': PRIVATE}]}}


class IdleReport(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='idle-report-')
        self.addCleanup(tmp.cleanup)
        self.d = Path(tmp.name).resolve()
        self.main = self.d / 'sess.jsonl'
        self.agents = self.d / 'sess' / 'subagents'

    def write(self, path, lines):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join((l if isinstance(l, str) else json.dumps(l)) + '\n' for l in lines), encoding='utf-8')

    def agent(self, agent_id, agent_type, lines):
        self.write(self.agents / f'agent-{agent_id}.jsonl', lines)
        if agent_type is not None:
            (self.agents / f'agent-{agent_id}.meta.json').write_text(json.dumps({'agentType': agent_type}), encoding='utf-8')

    def report(self, target=None):
        done = run(target or self.main, '--json')
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    def test_main_thread_calls_and_cache_writes_split_by_ttl(self):
        self.write(self.main, [call('m1', '2026-01-01T00:00:00.000Z', write=100, h1=40),
                               call('m2', '2026-01-01T00:01:00.000Z', write=10)])
        main = self.report()['groups']['main']
        self.assertEqual((main['calls'], main['cache_write'], main['cache_write_5m'], main['cache_write_1h']), (2, 110, 70, 40))

    def test_lines_sharing_a_message_id_count_as_one_call(self):
        self.write(self.main, [call('m1', '2026-01-01T00:00:00.000Z', write=100),
                               call('m1', '2026-01-01T00:00:01.000Z', write=100)])
        main = self.report()['groups']['main']
        self.assertEqual((main['calls'], main['cache_write']), (1, 100))

    def test_gaps_are_bucketed_with_the_tokens_of_the_message_after_the_gap(self):
        self.write(self.main, [call('m1', '2026-01-01T00:00:00Z', write=1),
                               call('m2', '2026-01-01T00:04:59Z', write=2, read=20),     # 4m59s
                               call('m3', '2026-01-01T00:09:59Z', write=3, read=30),     # 5m exactly
                               call('m4', '2026-01-01T01:09:59Z', write=4, read=40),     # 60m exactly
                               call('m5', '2026-01-01T03:09:59Z', write=5, read=50)])    # 120m
        gaps = self.report()['groups']['main']['gaps']
        self.assertEqual(gaps['lt_5m'], {'count': 1, 'cache_write': 2, 'cache_read': 20})
        self.assertEqual(gaps['5m_60m'], {'count': 2, 'cache_write': 7, 'cache_read': 70})
        self.assertEqual(gaps['gt_60m'], {'count': 1, 'cache_write': 5, 'cache_read': 50})

    def test_idle_hours_sum_only_gaps_of_five_minutes_or_more(self):
        self.write(self.main, [call('m1', '2026-01-01T00:00:00Z'), call('m2', '2026-01-01T00:04:00Z'),
                               call('m3', '2026-01-01T00:34:00Z'), call('m4', '2026-01-01T02:34:00Z')])
        self.assertEqual(self.report()['groups']['main']['idle_hours'], 2.5)

    def test_subagents_group_by_agent_type_and_gaps_never_span_two_agents(self):
        self.write(self.main, [call('m1', '2026-01-01T00:00:00Z', write=1)])
        self.agent('a1', 'scout', [call('s1', '2026-01-01T00:00:00Z', write=10), call('s2', '2026-01-01T00:01:00Z', write=10)])
        self.agent('a2', 'scout', [call('s3', '2026-01-01T05:00:00Z', write=10)])
        self.agent('a3', 'implement', [call('i1', '2026-01-01T00:00:00Z', write=7)])
        groups = self.report()['groups']
        self.assertEqual((groups['scout']['calls'], groups['scout']['cache_write'], groups['scout']['streams']), (3, 30, 2))
        self.assertEqual(groups['scout']['gaps']['gt_60m']['count'], 0)
        self.assertEqual(groups['implement']['calls'], 1)

    def test_an_agent_without_a_meta_file_is_grouped_as_unknown(self):
        self.write(self.main, [])
        self.agent('a1', None, [call('s1', '2026-01-01T00:00:00Z', write=10)])
        self.assertEqual(self.report()['groups']['unknown']['calls'], 1)

    def test_top_rewrites_are_the_ten_largest_after_a_gap_of_five_minutes_or_more(self):
        lines = [call('m0', '2026-01-01T00:00:00Z', write=999999)]
        lines += [call(f'm{n}', f'2026-01-01T{n:02d}:00:00Z', write=n * 100) for n in range(1, 13)]
        lines += [call('quick', '2026-01-01T12:01:00Z', write=888888)]
        self.write(self.main, lines)
        top = self.report()['top_rewrites']
        self.assertEqual([t['cache_write'] for t in top], [n * 100 for n in range(12, 2, -1)])
        self.assertEqual(top[0], {'agent_type': 'main', 'gap_minutes': 60.0, 'cache_write': 1200, 'timestamp': '2026-01-01T12:00:00Z'})

    def test_unparseable_and_non_assistant_lines_are_skipped(self):
        self.write(self.main, ['{not json', '[1, 2]', {'type': 'user', 'timestamp': '2026-01-01T00:00:00Z'},
                               {'type': 'assistant', 'timestamp': 'yesterday', 'message': {'id': 'x', 'usage': {}}},
                               {'type': 'assistant', 'timestamp': '2026-01-01T00:00:00Z', 'message': 'text'},
                               call('fake', '2026-01-01T00:00:00Z', model='<synthetic>'),
                               call('m1', '2026-01-01T00:00:00Z', write=5)])
        main = self.report()['groups']['main']
        self.assertEqual((main['calls'], main['cache_write']), (1, 5))

    def test_a_session_with_no_subagents_dir_reports_the_main_thread(self):
        self.write(self.main, [call('m1', '2026-01-01T00:00:00Z', write=5)])
        self.assertEqual(list(self.report()['groups']), ['main'])

    def test_the_session_dir_is_accepted_in_place_of_the_transcript(self):
        self.write(self.main, [call('m1', '2026-01-01T00:00:00Z', write=5)])
        self.agent('a1', 'scout', [call('s1', '2026-01-01T00:00:00Z', write=10)])
        self.assertEqual(self.report(self.d / 'sess'), self.report(self.main))

    def test_a_path_that_does_not_exist_is_exit_2(self):
        done = run(self.d / 'absent.jsonl')
        self.assertEqual(done.returncode, 2)
        self.assertEqual(done.stdout, '')

    def test_no_path_is_exit_2(self):
        self.assertEqual(run().returncode, 2)

    def test_a_fifo_is_exit_2_and_never_blocks(self):
        fifo = self.d / 'pipe.jsonl'
        os.mkfifo(fifo)
        done = run(fifo)
        self.assertEqual((done.returncode, done.stdout), (2, ''))

    def test_a_symlink_to_a_fifo_is_exit_2(self):
        os.mkfifo(self.d / 'pipe')
        (self.d / 'link.jsonl').symlink_to(self.d / 'pipe')
        self.assertEqual(run(self.d / 'link.jsonl').returncode, 2)

    def test_a_non_regular_stream_inside_the_subagents_dir_is_skipped(self):
        self.write(self.main, [call('m1', '2026-01-01T00:00:00Z', write=5)])
        self.agent('a1', 'scout', [call('s1', '2026-01-01T00:00:00Z', write=10)])
        os.mkfifo(self.agents / 'agent-pipe.jsonl')
        report = self.report(self.d / 'sess')
        self.assertEqual((report['groups']['scout']['streams'], report['total']['calls']), (1, 2))

    def test_a_fifo_meta_file_beside_a_direct_transcript_never_blocks(self):
        self.agent('a1', None, [call('s1', '2026-01-01T00:00:00Z', write=10)])
        os.mkfifo(self.agents / 'agent-a1.meta.json')
        report = self.report(self.agents / 'agent-a1.jsonl')
        self.assertEqual(list(report['groups']), ['agent-a1'])

    def test_a_fifo_meta_file_inside_a_session_directory_never_blocks(self):
        self.write(self.main, [call('m1', '2026-01-01T00:00:00Z', write=5)])
        self.agent('a1', None, [call('s1', '2026-01-01T00:00:00Z', write=10)])
        os.mkfifo(self.agents / 'agent-a1.meta.json')
        report = self.report(self.d / 'sess')
        self.assertEqual((report['groups']['unknown']['streams'], report['total']['calls']), (1, 2))

    def test_the_filesystem_root_is_exit_2_with_no_traceback(self):
        done = run('/')
        self.assertEqual((done.returncode, done.stdout), (2, ''))
        self.assertNotIn('Traceback', done.stderr)

    def test_a_z_suffix_is_read_where_fromisoformat_rejects_it(self):
        class OldDatetime(datetime):
            @classmethod
            def fromisoformat(cls, text):
                if text.endswith('Z'):
                    raise ValueError(text)
                return super().fromisoformat(text)
        loader = importlib.machinery.SourceFileLoader('idle_report_old', str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        module.datetime = OldDatetime
        self.write(self.main, [call('m1', '2026-01-01T00:00:00Z', write=5)])
        self.assertEqual(len(module.read_calls(self.main)), 1)

    def test_a_subagent_transcript_passed_directly_is_labelled_by_its_meta_file(self):
        self.agent('a1', 'scout', [call('s1', '2026-01-01T00:00:00Z', write=10)])
        self.assertEqual(list(self.report(self.agents / 'agent-a1.jsonl')['groups']), ['scout'])

    def test_a_subagent_transcript_without_meta_is_labelled_by_its_file_name(self):
        self.agent('a1', None, [call('s1', '2026-01-01T00:00:00Z', write=10)])
        self.assertEqual(list(self.report(self.agents / 'agent-a1.jsonl')['groups']), ['agent-a1'])

    def test_nothing_from_inside_the_transcript_but_agent_types_and_numbers_is_printed(self):
        self.write(self.main, [call('m1', '2026-01-01T00:00:00Z', write=5), call('m2', '2026-01-01T02:00:00Z', write=6)])
        self.agent('a1', 'scout', [call('s1', '2026-01-01T00:00:00Z', write=10)])
        for flags in ((), ('--json',)):
            done = run(self.main, *flags)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertNotIn(PRIVATE, done.stdout + done.stderr)
            self.assertNotIn(str(self.d), done.stdout + done.stderr)

    def test_the_text_table_names_each_group_and_the_largest_rewrite(self):
        self.write(self.main, [call('m1', '2026-01-01T00:00:00Z', write=5), call('m2', '2026-01-01T02:00:00Z', write=6000)])
        self.agent('a1', 'scout', [call('s1', '2026-01-01T00:00:00Z', write=10)])
        out = run(self.main).stdout
        for word in ('main', 'scout', 'total', '6,000', '2026-01-01T02:00:00Z', '120.0'):
            self.assertIn(word, out)

    def test_the_input_files_are_left_unchanged(self):
        self.write(self.main, [call('m1', '2026-01-01T00:00:00Z', write=5)])
        before = sorted((p.name, p.read_bytes()) for p in self.d.rglob('*') if p.is_file())
        run(self.main)
        self.assertEqual(sorted((p.name, p.read_bytes()) for p in self.d.rglob('*') if p.is_file()), before)

    def test_self_test_passes(self):
        self.assertEqual(run('--self-test').returncode, 0)

    def test_agent_hub_idle_runs_the_script(self):
        loader = importlib.machinery.SourceFileLoader('agent_hub_bin_idle', str(PLUGIN / 'bin' / 'agent-hub'))
        spec = importlib.util.spec_from_loader('agent_hub_bin_idle', loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        self.assertEqual(module.SUBCOMMANDS.get('idle'), 'idle-report.py')


if __name__ == '__main__':
    unittest.main()
