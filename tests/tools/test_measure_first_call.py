import json, os, subprocess, sys, tempfile, unittest
SCRIPT = os.path.join(os.path.dirname(__file__), '..', '..', 'tools', 'measure', 'first_call.py')

class FirstCallTest(unittest.TestCase):
    def test_runs_on_synthetic_logs(self):
        with tempfile.TemporaryDirectory() as d:
            sub = os.path.join(d, 'proj', 'sess', 'subagents')
            os.makedirs(sub)
            json.dump({'agentType': 'agent-hub:scout'}, open(os.path.join(sub, 'a1.meta.json'), 'w'))
            with open(os.path.join(sub, 'a1.jsonl'), 'w') as f:
                f.write(json.dumps({'type': 'assistant', 'requestId': 'r1', 'message': {'model': 'claude-sonnet-x', 'usage': {'input_tokens': 10, 'cache_creation_input_tokens': 90, 'cache_read_input_tokens': 900}}}) + '\n')
            out = os.path.join(d, 'out.txt')
            r = subprocess.run([sys.executable, '-B', '-I', SCRIPT, '--logs', d, '--days', '36500', '--out', out], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            txt = open(out).read()
            self.assertIn('agent-hub:scout', txt)
            self.assertIn('1000', txt)

    def test_help(self):
        self.assertEqual(subprocess.run([sys.executable, '-B', '-I', SCRIPT, '--help'], capture_output=True).returncode, 0)
