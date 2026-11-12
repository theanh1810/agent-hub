"""Tests for scripts/secret-scan.py: one fixture per pattern, the HAR and JSON forms, the placeholder exemption,
the allow file read from the scanned directory, the exit codes, and that no output line carries a secret character.
Fixtures are joined at run time so this file holds no secret-shaped literal."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'plugins' / 'agent-hub' / 'scripts' / 'secret-scan.py'
BODY = 'Qw7Er5Ty3Ui1Op9As2Df4Gh6'   # a value body with no word of any pattern name in it

# (pattern name, fixed prefix the pattern defines, secret body after the prefix, line template)
HIGH = (
    ('github-token', 'gh' + 'p_', BODY, '{v}'),
    ('github-token', 'gh' + 'u_', BODY, '{v}'),
    ('sk-api-key', 'sk' + '-', BODY, '{v}'),
    ('aws-access-key', 'AK' + 'IA', 'Q7W5E3R1T9Y7U5I3', '{v}'),
    ('jwt', 'ey' + 'J', 'hbGciOiJIUzI1.eyJzdWIiOiIxMjM0.SflKxwRJSMeKKF2Q', '{v}'),
    ('private-key', '-----BEGIN RSA PRIV' + 'ATE KEY-----', '', '{v}'),
    ('slack-webhook', 'hooks.slack.com/services/', 'T01ABCDEF/B02GHIJKL/Qw7Er5Ty3Ui1Op9', 'https://{v}'),   # scrub-allow: public webhook host the detector must match
    ('discord-webhook', 'discord.com/api/webhooks/', '123456789/Qw7Er5Ty3Ui1Op9As2Df', 'https://{v}'),   # scrub-allow: public webhook host the detector must match
    ('slack-token', 'xo' + 'xb-', '123456789012-Qw7Er5Ty3Ui1', '{v}'),
    ('gitlab-token', 'glp' + 'at-', 'Qw7Er5Ty3Ui1Op9As2Df4Gh6', '{v}'),
    ('stripe-key', 'sk_' + 'live_', 'Qw7Er5Ty3Ui1Op9As2', '{v}'),
    ('stripe-key', 'sk_' + 'test_', 'Qw7Er5Ty3Ui1Op9As2', '{v}'),
    ('google-api-key', 'AI' + 'za', 'Qw7Er5Ty3Ui1Op9As2Df4Gh6Jk8Lz0Xc-Vq', '{v}'),
)
# (name, line holding BODY as the value) for the low-confidence patterns
LOW = (
    ('bearer-token', 'Authorization: Bearer ' + BODY),
    ('cookie-value', 'Cookie: sid=' + BODY),
    ('connection-password', 'postgres://app:' + BODY + '@db.internal/main'),
    ('generic-assignment', 'API_KEY=' + BODY),
    ('generic-assignment', 'API_KEY: ' + BODY),
    ('generic-assignment', '"password": "' + BODY + '"'),
    ('generic-assignment', "'secret': '" + BODY + "'"),
)
HAR = (
    ('bearer-token', '{"name":"Authorization","va' + 'lue":"Bearer ' + BODY + '"}'),
    ('cookie-value', '{"name":"Cookie","va' + 'lue":"sid=' + BODY + '"}'),
    ('cookie-value', '{"name":"Set-Cookie","va' + 'lue":"sid=' + BODY + '; Path=/"}'),
    (None, '{"name":"PRIVATE-TOKEN","va' + 'lue":"' + BODY + '"}'),
    (None, '{"name":"X-Api-Key","va' + 'lue":"' + BODY + '"}'),
)


def scan(*args):
    p = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


class Scratch:
    def __init__(self, case):
        self.tmp = tempfile.TemporaryDirectory(prefix='secret-scan-')
        case.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def write(self, rel, text, mode='w'):
        p = self.dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, mode) as f:
            f.write(text)
        return p


def leaked(out, body):
    """a 4-character window of the secret body found in the output"""
    return [body[i:i + 4] for i in range(len(body) - 3) if body[i:i + 4] in out]


class PatternTests(unittest.TestCase):
    def test_every_high_confidence_pattern_hits_and_prints_no_body(self):
        for name, prefix, body, template in HIGH:
            with self.subTest(pattern=name, prefix=prefix):
                s = Scratch(self)
                s.write('a.txt', 'note ' + template.format(v=prefix + body) + '\n')
                rc, out, _ = scan(s.dir)
                self.assertEqual(rc, 1, out)
                self.assertEqual(len(out.strip().splitlines()), 1, out)
                self.assertIn(f'a.txt:1: ', out)
                self.assertEqual(leaked(out, body), [], out)

    def test_every_low_confidence_pattern_hits_and_prints_no_character(self):
        for name, line in LOW:
            with self.subTest(pattern=name, line=line[:14]):
                s = Scratch(self)
                s.write('a.txt', line + '\n')
                rc, out, _ = scan(s.dir)
                self.assertEqual(rc, 1, out)
                self.assertIn(name, out)
                self.assertEqual(leaked(out, BODY), [], out)

    def test_har_name_value_form_hits_and_prints_no_character(self):
        for name, line in HAR:
            with self.subTest(header=line[:28]):
                s = Scratch(self)
                s.write('a.har', line + '\n')
                rc, out, _ = scan(s.dir)
                self.assertEqual(rc, 1, out)
                if name:
                    self.assertIn(name, out)
                self.assertEqual(leaked(out, BODY), [], out)

    def test_json_password_value_hits(self):
        s = Scratch(self)
        s.write('a.json', '{"password": "' + BODY + '"}\n')
        rc, out, _ = scan(s.dir)
        self.assertEqual(rc, 1, out)
        self.assertIn('generic-assignment', out)

    def test_two_hits_in_one_run_print_two_lines_and_no_character(self):
        s = Scratch(self)
        s.write('a.txt', 'xo' + 'xb-123456789012-Qw7Er5Ty3Ui1\nAPI_KEY=' + BODY + '\n')
        rc, out, _ = scan(s.dir)
        self.assertEqual(rc, 1)
        self.assertEqual(len(out.strip().splitlines()), 2, out)
        self.assertEqual(leaked(out, BODY), [], out)


class PlaceholderTests(unittest.TestCase):
    def test_placeholder_values_on_low_confidence_patterns_are_skipped(self):
        for line in ('TOKEN=<your-token>', 'TOKEN=placeholder', 'API_KEY=changeme-value', 'PASSWORD={env_password_here}',
                     'Authorization: Bearer example-token-value'):
            with self.subTest(line=line):
                s = Scratch(self)
                s.write('a.txt', line + '\n')
                rc, out, _ = scan(s.dir)
                self.assertEqual((rc, out), (0, ''))

    def test_high_confidence_token_with_the_word_example_still_hits(self):
        s = Scratch(self)
        s.write('a.txt', 'gh' + 'p_example' + BODY + '\n')
        rc, out, _ = scan(s.dir)
        self.assertEqual(rc, 1, out)

    def test_masked_high_confidence_token_is_skipped(self):
        s = Scratch(self)
        s.write('a.txt', 'gh' + 'p_' + 'x' * 24 + '\n')
        self.assertEqual(scan(s.dir)[0], 0)


class AllowFileTests(unittest.TestCase):
    def test_allow_file_in_the_scanned_directory_marks_a_hit_allowed(self):
        s = Scratch(self)
        s.write('sub/b.txt', 'ok\nAPI_KEY=' + BODY + '\n')
        s.write('.secret-scan-allow', '# fixture\nsub/b.txt:2\n')
        rc, out, _ = scan(s.dir)
        self.assertEqual(rc, 0, out)
        self.assertIn('allowed', out)
        self.assertEqual(leaked(out, BODY), [], out)

    def test_an_entry_for_another_line_allows_nothing(self):
        s = Scratch(self)
        s.write('b.txt', 'ok\nAPI_KEY=' + BODY + '\n')
        s.write('.secret-scan-allow', 'b.txt:1\n')
        rc, out, _ = scan(s.dir)
        self.assertEqual(rc, 1, out)
        self.assertNotIn('allowed', out)

    def test_scanning_one_file_reads_the_allow_file_of_its_folder(self):
        s = Scratch(self)
        f = s.write('b.txt', 'API_KEY=' + BODY + '\n')
        s.write('.secret-scan-allow', 'b.txt:1\n')
        rc, out, _ = scan(f)
        self.assertEqual(rc, 0, out)
        self.assertIn('allowed', out)

    def test_the_allow_file_is_not_scanned_itself(self):
        s = Scratch(self)
        s.write('.secret-scan-allow', 'API_KEY=' + BODY + '\n')
        self.assertEqual(scan(s.dir)[0], 0)


class ExitCodeTests(unittest.TestCase):
    def test_clean_directory_exits_0_and_prints_nothing(self):
        s = Scratch(self)
        s.write('a.txt', 'nothing secret here\n')
        self.assertEqual(scan(s.dir)[:2], (0, ''))

    def test_binary_file_is_skipped(self):
        s = Scratch(self)
        s.write('bin.dat', b'a\0b gh' + b'p_' + BODY.encode() + b'\n', mode='wb')
        self.assertEqual(scan(s.dir)[:2], (0, ''))

    def test_missing_path_exits_2_and_names_it(self):
        s = Scratch(self)
        rc, out, err = scan(s.dir / 'missing')
        self.assertEqual(rc, 2)
        self.assertEqual(out, '')
        self.assertIn(str(s.dir / 'missing'), err)

    def test_one_missing_path_does_not_stop_the_others(self):
        s = Scratch(self)
        s.write('a.txt', 'API_KEY=' + BODY + '\n')
        rc, out, err = scan(s.dir / 'missing', s.dir)
        self.assertEqual(rc, 2)
        self.assertIn('a.txt:1:', out)
        self.assertIn('missing', err)

    def test_no_argument_is_a_usage_error(self):
        self.assertEqual(scan()[0], 2)


if __name__ == '__main__':
    unittest.main()
