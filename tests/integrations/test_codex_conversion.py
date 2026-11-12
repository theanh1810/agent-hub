"""Conversion invariants: preserve decisions, native profiles, drift and installation ownership."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / 'plugins/agent-hub-integrations'
RULESET = ROOT / 'plugins/agent-hub'


def module(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


CONVERT = module('converter', PLUGIN / 'scripts/codex-convert.py')
INSTALL = module('installer', PLUGIN / 'scripts/codex-install.py')
HOOK = module('workflow_hook', PLUGIN / 'templates/codex-work/workflow-hook.py')


class ConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='codex-conversion-tests-')
        cls.stage = Path(cls.temp.name) / 'stage'
        CONVERT.build(cls.stage)
        cls.manifest = json.loads((cls.stage / 'manifest.json').read_text())

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_original_ids_and_quotes_survive_translation(self):
        text = 'notes/example-pilot.yaml "claude stays" ~/.claude/rules/plan-files.md'  # scrub-allow: the path under test is the conversion input
        translated = CONVERT.translate(text)
        self.assertIn('example-pilot.yaml "claude stays"', translated)
        self.assertIn('~/.codex/claude-compat/rules/plan-files.md', translated)
        self.assertNotIn('~/.Codex', translated)

    def test_every_source_profile_preserves_effort_and_body(self):
        source = list((RULESET / 'agents').glob('*.md'))
        self.assertEqual(len(source), len(self.manifest['agents']))
        for p in source:
            fm, body = CONVERT.split_frontmatter(p.read_text())
            d = tomllib.loads((self.stage / 'agents' / (fm['name'] + '.toml')).read_text())
            self.assertEqual(fm['effort'], d['model_reasoning_effort'])
            self.assertNotIn('model', d)
            self.assertIn(CONVERT.translate(body), d['developer_instructions'])
            for skill in fm.get('skills', []):
                self.assertIn('/skills/' + skill + '/SKILL.md', d['developer_instructions'])

    def test_synced_exports_have_one_alias_per_unique_skill(self):
        names = self.manifest['skills']
        self.assertEqual(len(names), len(set(names)))
        self.assertNotIn('synced', names)
        for name, record in self.manifest['synced_deduplication'].items():
            self.assertEqual(1, names.count(record['native_name']))
            self.assertGreaterEqual(len(record['sources']), 1)

    def test_command_helpers_are_not_independent_commands(self):
        names = self.manifest['skills']
        self.assertIn('source-command-codestyle', names)
        self.assertNotIn('source-command-spec-init', names)
        self.assertNotIn('source-command-spec-check', names)
        self.assertTrue((self.stage / 'claude-compat/refs/commands/spec-init.md').is_file())

    def test_manual_orchestration_preserves_invocation_policy(self):
        with tempfile.TemporaryDirectory(prefix='codex-manual-') as temp:
            src = Path(temp) / 'src' / 'orchestrate'
            src.mkdir(parents=True)
            (src / 'SKILL.md').write_text('---\nname: orchestrate\ndescription: manual\ndisable-model-invocation: true\n---\nbody\n')
            folder = Path(temp) / 'out' / 'orchestrate'
            CONVERT.copy_skill(src, folder)
            d = yaml.safe_load((folder / 'agents/openai.yaml').read_text())
            self.assertFalse(d['policy']['allow_implicit_invocation'])
            fm, _ = CONVERT.split_frontmatter((folder / 'SKILL.md').read_text())
            self.assertNotIn('disable-model-invocation', fm)

    def test_missing_template_exits_nonzero(self):
        with tempfile.TemporaryDirectory(prefix='codex-missing-') as temp:
            plugin = Path(temp) / 'plugin'
            shutil.copytree(PLUGIN, plugin, ignore=shutil.ignore_patterns('__pycache__'))
            shutil.rmtree(plugin / 'templates/codex-work')
            proc = subprocess.run(['python3', str(plugin / 'scripts/codex-convert.py'), 'build', '--out', str(Path(temp) / 'out')],
                                  capture_output=True, text=True, env=dict(os.environ, AGENT_HUB_RULESET=str(RULESET)))
            self.assertNotEqual(0, proc.returncode)

    def test_source_drift_stops_validation(self):
        with tempfile.TemporaryDirectory(prefix='codex-drift-') as temp:
            p = Path(temp)
            data = dict(self.manifest)
            data['source_hashes'] = dict(data['source_hashes'])
            data['source_hashes']['CLAUDE.md'] = 'incorrect'
            (p / 'manifest.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'source drift'):
                CONVERT.validate(p)

    def test_install_and_reinstall_native_links(self):
        with tempfile.TemporaryDirectory(prefix='codex-install-') as temp:
            base = Path(temp); codex = base / 'codex'; skills = base / 'skills'
            INSTALL.install(self.stage, codex, skills, None)
            INSTALL.install(self.stage, codex, skills, None)
            for role in self.manifest['agents']:
                target = codex / 'agents' / (role['name'] + '.toml')
                self.assertTrue(target.is_symlink())
                self.assertEqual(role['name'], tomllib.loads(target.read_text())['name'])
            self.assertEqual(set(self.manifest['skills']), {p.name for p in skills.iterdir()})

    def test_unowned_skill_collision_stops_before_any_install(self):
        with tempfile.TemporaryDirectory(prefix='codex-collision-') as temp:
            base = Path(temp); codex = base / 'codex'; skills = base / 'skills'
            target = skills / self.manifest['skills'][0]
            target.mkdir(parents=True); (target / 'keep.txt').write_text('user content')
            with self.assertRaisesRegex(ValueError, 'unowned destination'):
                INSTALL.install(self.stage, codex, skills, None)
            self.assertEqual('user content', (target / 'keep.txt').read_text())
            self.assertFalse(codex.exists())

    def test_unrelated_hooks_survive_import_owned_event(self):
        with tempfile.TemporaryDirectory(prefix='codex-hooks-') as temp:
            base = Path(temp); codex = base / 'codex'; skills = base / 'skills'
            codex.mkdir()
            user = {'type': 'command', 'command': 'user-hook'}
            imported_hook = {'type': 'command', 'command': 'bash ' + str(codex / 'hooks/session-start-orchestrator.sh')}
            content = {'hooks': {'SessionStart': [{'matcher': '*', 'hooks': [imported_hook, user]}]}}
            (codex / 'hooks.json').write_text(json.dumps(content))
            result = base / 'import.json'
            result.write_text(json.dumps({'completion': {'itemTypeResults': [{'itemType': 'HOOKS', 'successes': [{'target': 'SessionStart'}]}]}}))
            INSTALL.install(self.stage, codex, skills, result)
            rows = json.loads((codex / 'hooks.json').read_text())['hooks']['SessionStart']
            self.assertEqual({'matcher': '*', 'hooks': [user]}, rows[0])
            self.assertEqual(2, len(rows))
            INSTALL.install(self.stage, codex, skills, None)
            self.assertEqual(rows, json.loads((codex / 'hooks.json').read_text())['hooks']['SessionStart'])

    def test_unowned_hook_file_stops_before_mutation(self):
        with tempfile.TemporaryDirectory(prefix='codex-hook-file-') as temp:
            base = Path(temp); codex = base / 'codex'; skills = base / 'skills'
            target = codex / 'hooks/workflow-hook.py'
            target.parent.mkdir(parents=True)
            target.write_text('user implementation')
            with self.assertRaisesRegex(ValueError, 'unowned or modified hook'):
                INSTALL.install(self.stage, codex, skills, None)
            self.assertEqual('user implementation', target.read_text())
            self.assertFalse((codex / 'claude-workflow').exists())

    def test_generated_content_and_links_cannot_drift(self):
        names = ['agents/planner.toml', 'skills/claude-workflow/SKILL.md', 'claude-compat/runtime.md', 'claude-compat/scripts']
        for name in names:
            with self.subTest(name=name), tempfile.TemporaryDirectory(prefix='codex-output-drift-') as temp:
                copied = Path(temp) / 'stage'
                shutil.copytree(self.stage, copied, symlinks=True)
                target = copied / name
                if target.is_symlink():
                    target.unlink(); target.symlink_to('/private/tmp')
                else:
                    target.write_text(target.read_text() + '\nchanged')
                with self.assertRaisesRegex(ValueError, 'content/link drift'):
                    CONVERT.validate(copied)


class HookTests(unittest.TestCase):
    def test_bootstrap_context_is_native(self):
        result = HOOK.process({'hook_event_name': 'SessionStart'})
        self.assertEqual('SessionStart', result['hookSpecificOutput']['hookEventName'])
        self.assertIn('~/.codex/claude-compat/runtime.md', result['hookSpecificOutput']['additionalContext'])
        self.assertNotIn('Agent(', result['hookSpecificOutput']['additionalContext'])

    def test_user_opt_out_is_respected(self):
        self.assertEqual({}, HOOK.process({'hook_event_name': 'UserPromptSubmit', 'prompt': 'do it directly, fix the bug'}))

    def test_non_shell_tool_cannot_be_rewritten(self):
        with patch.object(HOOK.subprocess, 'run') as run:
            self.assertEqual({}, HOOK.process({'hook_event_name': 'PreToolUse', 'tool_name': 'apply_patch', 'tool_input': {'command': 'x'}}))
            run.assert_not_called()

    def test_invalid_rtk_response_preserves_original_call(self):
        with patch.object(HOOK.subprocess, 'run') as run, patch.object(HOOK.Path, 'is_file', return_value=True):
            run.return_value.returncode = 0
            run.return_value.stdout = '{"hookSpecificOutput":{"permissionDecision":"deny"}}'
            self.assertEqual({}, HOOK.process({'hook_event_name': 'PreToolUse', 'tool_name': 'Bash', 'tool_input': {'command': 'git status'}}))

    def test_permission_decisions_are_never_upgraded(self):
        for decision in ['deny', 'ask', 'allow']:
            with self.subTest(decision=decision), patch.object(HOOK.subprocess, 'run') as run, patch.object(HOOK.Path, 'is_file', return_value=True):
                run.return_value.returncode = 0
                run.return_value.stdout = json.dumps({'hookSpecificOutput': {'permissionDecision': decision, 'updatedInput': {'command': 'rtk git status'}}})
                result = HOOK.process({'hook_event_name': 'PreToolUse', 'tool_name': 'Bash', 'tool_input': {'command': 'git status'}})
                if decision == 'allow':
                    self.assertEqual('rtk git status', result['hookSpecificOutput']['updatedInput']['command'])
                else:
                    self.assertEqual({}, result)


class InstalledLayout(unittest.TestCase):
    """The converter run from the plugin cache, with no PYTHONPATH and no AGENT_HUB_RULESET."""

    def run_convert(self, script, out):
        env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'AGENT_HUB_RULESET')}
        return subprocess.run([sys.executable, str(script), 'build', '--out', str(out)],
                              capture_output=True, text=True, env=env)

    def test_finds_core_plugin_beside_it_in_the_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            copy = tmp / 'cache/m/agent-hub-integrations/0.1.0'
            shutil.copytree(PLUGIN, copy)
            (tmp / 'cache/m/agent-hub').mkdir(parents=True)
            (tmp / 'cache/m/agent-hub/0.1.0').symlink_to(RULESET, target_is_directory=True)
            p = self.run_convert(copy / 'scripts/codex-convert.py', tmp / 'out')
            self.assertEqual(p.returncode, 0, p.stderr)

    def test_without_core_plugin_names_the_env_variable(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            copy = tmp / 'x/agent-hub-integrations/0.1.0'
            shutil.copytree(PLUGIN, copy)
            p = self.run_convert(copy / 'scripts/codex-convert.py', tmp / 'out')
            self.assertEqual(p.returncode, 2, p.stderr)
            self.assertIn('AGENT_HUB_RULESET', p.stderr)


if __name__ == '__main__':
    unittest.main()
