import os, subprocess, sys, tempfile, unittest
SCRIPT = os.path.join(os.path.dirname(__file__), '..', '..', 'tools', 'measure', 'floors.py')

class FloorsTest(unittest.TestCase):
    def test_runs_on_synthetic_plugin(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'rules')); os.makedirs(os.path.join(d, 'agents')); os.makedirs(os.path.join(d, 'skills', 'sk'))
            open(os.path.join(d, 'rules', 'core.md'), 'w').write('# 0. Main\nmain only\n# 1. Shared\nshared\n')
            open(os.path.join(d, 'skills', 'sk', 'SKILL.md'), 'w').write('skill body')
            open(os.path.join(d, 'agents', 'scout.md'), 'w').write('---\nname: scout\nskills:\n  - sk\n---\nbody\n')
            out = os.path.join(d, 'out.txt')
            r = subprocess.run([sys.executable, '-B', '-I', SCRIPT, '--plugin-root', d, '--out', out], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            txt = open(out).read()
            self.assertIn('core.md', txt)
            self.assertIn('scout', txt)

    def test_subagent_view_of_the_real_core_drops_the_main_only_blocks(self):
        root = os.path.join(os.path.dirname(SCRIPT), '..', '..', 'plugins', 'agent-hub')
        sys.path.insert(0, os.path.join(root, 'hooks'))
        try:
            import rules_inject
        finally:
            sys.path.pop(0)
        core = open(os.path.join(root, 'rules', 'core.md'), encoding='utf-8').read()
        want = len(rules_inject.view_text(core, 'subagent').encode())
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'out.txt')
            r = subprocess.run([sys.executable, '-B', '-I', SCRIPT, '--plugin-root', root, '--out', out], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            first = open(out, encoding='utf-8').readline()
        self.assertIn(f'subagent view {want} B', first)
        self.assertLess(want, len(core.encode()))

    def test_help(self):
        self.assertEqual(subprocess.run([sys.executable, '-B', '-I', SCRIPT, '--help'], capture_output=True).returncode, 0)
