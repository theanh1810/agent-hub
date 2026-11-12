"""Tests for plugins/agent-hub-local-services/hooks/docker_preflight.py. Each case feeds {"tool_input": {"command": <cmd>}} on stdin and asserts the exit code and stderr."""
import json, os, stat, subprocess, sys, tempfile, unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / 'plugins' / 'agent-hub-local-services'
HOOK = PLUGIN / 'hooks' / 'docker_preflight.py'
INFRA = '/opt/shared-infra'
POINTER = 'refs/local-services.md'


def preflight(cmd, env=None, inspect_image=None, cwd=None, infra=INFRA, fake_script=None, with_docker=True, raw_stdin=None):
    """-> (exit code, stderr). Runs the hook with python; infra sets the infra_dir option (None: unset);
    fake_script replaces the fake docker's body; with_docker False leaves docker off PATH; inspect_image puts a fake `docker` first on PATH that answers
    `docker inspect --format ... <name>` with that image (None: the fake exits 1). cwd sets both the stdin JSON 'cwd' key
    and the hook process's working directory."""
    e = dict(os.environ)
    e.pop('CLAUDE_DOCKER_PREFLIGHT', None)
    e.pop('CLAUDE_PLUGIN_OPTION_INFRA_DIR', None)
    if infra is not None:
        e['CLAUDE_PLUGIN_OPTION_INFRA_DIR'] = infra
    e['CLAUDE_PLUGIN_ROOT'] = str(PLUGIN)
    e.pop('PYTHONPATH', None)  # the hook must find its own vendored PyYAML
    e.update(env or {})
    with tempfile.TemporaryDirectory() as d:
        fake = Path(d) / 'docker'
        if fake_script is not None:
            fake.write_text(fake_script)
        elif inspect_image is None:
            fake.write_text('#!/bin/sh\nexit 1\n')
        else:
            fake.write_text('#!/bin/sh\necho "%s"\n' % inspect_image)
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        e['PATH'] = (d + os.pathsep + e.get('PATH', '')) if with_docker else d + os.sep + 'none'
        if not with_docker:
            fake.unlink()
        payload = {'tool_input': {'command': cmd}}
        if cwd is not None:
            payload['cwd'] = str(cwd)
        p = subprocess.run([sys.executable, str(HOOK)], input=raw_stdin if raw_stdin is not None else json.dumps(payload),
                           capture_output=True, text=True, env=e, cwd=str(cwd) if cwd is not None else None)
    return p.returncode, p.stderr


class PreflightTest(unittest.TestCase):
    def check(self, cmd, want, **kw):
        rc, err = preflight(cmd, **kw)
        self.assertEqual(rc, want, '%s -> %s %r' % (cmd, rc, err))
        if want == 2:
            self.assertIn(POINTER, err)
            self.assertEqual(len(err.strip().splitlines()), 1)
        return err

    def test_run_table(self):
        for cmd, want in [
            ('docker run -d --name x -p 5799:5432 postgres:16', 2),
            ('docker run -d -p 127.0.0.1:3000:3000 node:20', 0),
            ('docker run -d -p 3000:3000 node:20', 2),
            ('docker run -d -p 0.0.0.0:3000:3000 node:20', 2),
            ('docker run -d --name shared-redis -p 127.0.0.1:6379:6379 redis:7-alpine', 0),
            ('docker run -d --name other-redis redis:7', 2),
            ('docker run -d postgres:16', 2),
            ('docker create --name m axllent/mailpit', 2),
            ('rtk docker run -d postgres:16', 2),
        ]:
            self.check(cmd, want)

    def test_seaweedfs_and_minio(self):
        self.check('docker run --name s3x chrislusf/seaweedfs', 2)
        self.check('docker run --name shared-s3 minio/minio', 2)
        self.check('docker run --name shared-s3 chrislusf/seaweedfs:3.80', 0)

    def test_own_vendored_yaml_parses_without_pythonpath(self):  # no PYTHONPATH: the plugin's own lib/yaml parses the compose file
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'compose.yaml'
            f.write_text('services:\n  db:\n    image: postgres:16\n')
            self.check('docker compose -f %s up -d' % f, 2)

    def test_compose(self):
        self.check('docker compose -f %s/postgres/compose.yaml up -d' % INFRA, 0)
        self.check('docker compose -f /tmp/x/deploy/app/docker-compose.yml up -d', 0)
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'compose.yaml'
            f.write_text('services:\n  r:\n    image: redis:7-alpine\n    ports:\n      - "6379:6379"\n')
            self.check('docker compose -f %s up -d' % f, 2)
            f.write_text('services:\n  r:\n    image: redis:7-alpine\n    container_name: shared-redis\n    ports:\n      - "127.0.0.1:6379:6379"\n')
            self.check('docker compose -f %s up -d' % f, 0)
            f.write_text('services:\n  s:\n    image: minio/minio\n    container_name: shared-minio\n')
            self.check('docker-compose -f %s up -d' % f, 2)
            f.write_text('services:\n  a:\n    image: node:20\n    ports:\n      - "3000:3000"\n')
            self.check('docker compose -f %s up -d' % f, 2)
            self.check('docker compose -f %s down' % f, 0)

    def test_kill_switch(self):
        self.check('docker run -d postgres:16', 0, env={'CLAUDE_DOCKER_PREFLIGHT': 'off'})
        self.check('CLAUDE_DOCKER_PREFLIGHT=off docker run -d postgres:16', 0)

    def test_unparseable(self):
        for cmd in ['docker run -d "unbalanced', 'docker compose -f /nonexistent/compose.yaml up -d']:
            rc, err = preflight(cmd)
            self.assertEqual(rc, 0, cmd)
            self.assertEqual(len(err.strip().splitlines()), 1, err)
            self.assertIn('could not parse', err)

    def test_non_docker_fast(self):
        rc, err = preflight('ls -la')
        self.assertEqual((rc, err), (0, ''))

    def test_start_stop(self):
        self.check('docker start shared-s3', 0)
        self.check('docker stop shared-s3', 0)
        self.check('docker start shared-redis', 0)
        self.check('docker stop foo', 0)
        self.check('docker rm foo', 0)

    def test_start_other_inspects(self):
        self.check('docker start foo', 2, inspect_image='chrislusf/seaweedfs:3.80')
        self.check('docker start foo', 2, inspect_image='minio/minio')
        self.check('docker start foo', 0, inspect_image='node:20')
        rc, err = preflight('docker start foo')
        self.assertEqual(rc, 0)
        self.assertEqual(len(err.strip().splitlines()), 1)
        self.assertIn('could not parse', err)

    def _dirs(self, d):
        d = Path(d)
        P, N = d / 'p', d / 'n'
        P.mkdir(); N.mkdir()
        (P / 'compose.yaml').write_text('services:\n  db:\n    image: postgres:16\n    ports:\n      - "5432:5432"\n')
        (N / 'compose.yaml').write_text('services:\n  web:\n    image: nginx:1.27\n    ports:\n      - "127.0.0.1:8080:80"\n')
        return P, N

    def test_f1a_cd_into_bad_dir(self):
        with tempfile.TemporaryDirectory() as d:
            P, N = self._dirs(d)
            err = self.check('cd %s && docker compose up -d' % P, 2, cwd=N)
            self.assertIn('compose service db defines its own postgres', err)

    def test_f1b_cd_into_good_dir(self):
        with tempfile.TemporaryDirectory() as d:
            P, N = self._dirs(d)
            self.assertEqual(preflight('cd %s && docker compose up -d web' % N, cwd=P), (0, ''))

    def test_f1c_tilde_infra_path(self):
        self.assertEqual(preflight('docker compose -f ~/infra/redis/compose.yaml up -d --wait',
                                   env={'HOME': '/opt/h'}, infra='/opt/h/infra'), (0, ''))

    def test_f1d_home_relative_paths(self):
        with tempfile.TemporaryDirectory() as d:
            H = Path(d) / 'h'
            (H / 'proj').mkdir(parents=True)
            (H / 'proj' / 'compose.yml').write_text('services:\n  db:\n    image: postgres:16\n    ports:\n      - "5432:5432"\n')
            for cmd in ('docker compose -f ~/proj/compose.yml up -d', 'docker compose --project-directory ~/proj up -d'):
                err = self.check(cmd, 2, env={'HOME': str(H)})
                self.assertIn('compose service db defines its own postgres', err)

    def test_f1e_cd_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            P, N = self._dirs(d)
            rc, err = preflight('cd "$(mktemp -d)" && docker compose up -d', cwd=P)
            self.assertEqual(rc, 0, err)
            self.assertEqual(err.strip(), 'docker-preflight: could not parse (working directory unknown after cd); allowed')

    def test_f2a_bundled_publish(self):
        self.check('docker run -dp 5432:5432 postgres:16', 2)
        self.check('docker run -dp 127.0.0.1:8080:80 nginx', 0)

    def test_f2b_container_subcommand(self):
        self.check('docker container run -d -p 5432:5432 postgres:16', 2)
        self.check('docker container create --name y redis:7', 2)
        self.check('docker container start foo', 2, inspect_image='minio/minio')
        self.check('docker container start shared-s3', 0)

    def test_f2c_network_alias(self):
        self.check('docker run --network-alias db -p 8080:80 nginx', 2)
        self.check('docker run --network-alias db --name z postgres:16', 2)

    def test_f2d_publish_all(self):
        for cmd in ('docker run -d -P nginx', 'docker run -dP nginx', 'docker run --publish-all nginx'):
            err = self.check(cmd, 2)
            self.assertIn('publish-all binds every exposed port on 0.0.0.0', err)

    def test_f2e_host_network(self):
        msg = 'host networking exposes every container port on all host interfaces'
        for cmd in ('docker run --network host nginx', 'docker run --net=host nginx'):
            self.assertIn(msg, self.check(cmd, 2))
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'compose.yaml'
            f.write_text('services:\n  a:\n    image: node:20\n    network_mode: host\n')
            self.assertIn(msg, self.check('docker compose -f %s up -d' % f, 2))

    def test_f2f_sudo(self):
        for cmd in ('sudo docker run -d postgres:16', 'sudo -E docker run -d postgres:16'):
            self.assertIn('a second postgres container (unnamed) is not allowed', self.check(cmd, 2))

    def test_f2g_image_aliases(self):
        self.assertIn('a second postgres container (x) is not allowed',
                      self.check('docker run -d --name x bitnami/postgresql', 2))
        self.check('docker run -d --name shared-postgres bitnami/postgresql:16', 0)

    def test_f2h_unknown_flag(self):
        rc, err = preflight('docker run --frobnicate x nginx')
        self.assertEqual(rc, 0)
        self.assertEqual(err.strip(), 'docker-preflight: could not parse (unknown flag --frobnicate); allowed')

    def test_infra_unset_only_publish_rule(self):
        self.check('docker run -d postgres:16', 0, infra=None)
        self.check('docker run -d --name other-redis redis:7', 0, infra=None)
        self.check('docker run -d -p 0.0.0.0:3000:3000 node:20', 2, infra=None)
        self.check('docker run -d -p 3000:3000 node:20', 2, infra=None)
        self.check('docker run -d -p 127.0.0.1:3000:3000 node:20', 0, infra=None)
        self.check('docker start foo', 0, infra=None, inspect_image='minio/minio')

    def test_docker_missing(self):
        self.assertEqual(preflight('docker run -d -p 3000:3000 node:20', with_docker=False), (0, ''))

    def test_inspect_timeout(self):
        import time
        t0 = time.time()
        rc, err = preflight('docker start foo', fake_script='#!/bin/sh\nsleep 30\n')
        self.assertEqual(rc, 0)
        self.assertLess(time.time() - t0, 15)
        self.assertIn('could not parse', err)

    def test_malformed_stdin(self):
        for raw in ('not json', '', '[1, 2]', '{"tool_input": 5}'):
            rc, err = preflight('x', raw_stdin=raw)
            self.assertEqual(rc, 0, raw)

    def test_hooks_json(self):
        h = json.load(open(PLUGIN / 'hooks' / 'hooks.json'))['hooks']['PreToolUse'][0]
        self.assertEqual(h['matcher'], 'Bash')
        self.assertIn('docker_preflight.py', h['hooks'][0]['command'])

    def test_manifest(self):
        m = json.load(open(PLUGIN / '.claude-plugin' / 'plugin.json'))
        self.assertEqual(m['name'], 'agent-hub-local-services')
        self.assertEqual(m['dependencies'], ['agent-hub'])
        self.assertEqual(m['userConfig']['infra_dir']['type'], 'directory')


if __name__ == '__main__':
    unittest.main()
