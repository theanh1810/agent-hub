import json, os, subprocess, sys, tempfile, unittest
SCRIPT = os.path.join(os.path.dirname(__file__), '..', '..', 'tools', 'measure', 'tool_use.py')

class ToolUseTest(unittest.TestCase):
    def test_runs_on_synthetic_logs(self):
        with tempfile.TemporaryDirectory() as d:
            sub = os.path.join(d, 'proj', 'sess', 'subagents')
            os.makedirs(sub)
            json.dump({'agentType': 'agent-hub:implement-high'}, open(os.path.join(sub, 'a1.meta.json'), 'w'))
            blocks = [{'type': 'tool_use', 'name': 'Read', 'input': {}},
                      {'type': 'tool_use', 'name': 'mcp__gitnexus__impact', 'input': {}}]
            with open(os.path.join(sub, 'a1.jsonl'), 'w') as f:
                f.write(json.dumps({'type': 'assistant', 'message': {'content': blocks}}) + '\n')
            out = os.path.join(d, 'out.txt')
            r = subprocess.run([sys.executable, '-B', '-I', SCRIPT, '--logs', d, '--days', '36500', '--out', out], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            txt = open(out).read()
            self.assertIn('## implement: 1 runs, 2 tool calls', txt)
            self.assertIn('mcp__gitnexus 1', txt)

    def test_help(self):
        self.assertEqual(subprocess.run([sys.executable, '-B', '-I', SCRIPT, '--help'], capture_output=True).returncode, 0)
