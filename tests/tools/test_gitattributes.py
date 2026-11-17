"""The root .gitattributes: text is LF everywhere, byte-pinned trees are never converted (git check-attr)."""
import shutil
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def attrs(path):
    out = subprocess.run(['git', '-C', str(REPO), 'check-attr', 'text', 'eol', '--', path], capture_output=True, text=True, check=True).stdout
    return {line.split(': ')[1]: line.split(': ')[2] for line in out.splitlines()}


@unittest.skipIf(shutil.which('git') is None, 'git missing')
class GitAttributes(unittest.TestCase):
    def test_text_files_are_lf(self):
        got = attrs('plugins/agent-hub/agents/test.md')
        self.assertEqual((got['text'], got['eol']), ('auto', 'lf'))

    def test_byte_pinned_trees_are_not_converted(self):
        for path in ('plugins/agent-hub/store/x/text.md', 'plugins/agent-hub/refs/vendored/teach.md', 'tools/upstream/x.txt'):
            self.assertEqual(attrs(path)['text'], 'unset', path)


if __name__ == '__main__':
    unittest.main()
