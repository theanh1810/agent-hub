"""Regression tests for UC/AC id resolution and the plan-verify checks that read it."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PLUGIN = Path(__file__).resolve().parents[2] / 'plugins' / 'agent-hub'
SCRIPTS = PLUGIN / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from spec_refs import missing_references


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


VERIFY = module('plan_verify', SCRIPTS / 'plan-verify.py')
LOCATE = module('plan_locate', SCRIPTS / 'plan-locate.py')


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def criterion(ref='UC-001/AC-1'):
    return {'id': 'W1-T1', 'covers_uc': ['UC-001'],
            'acceptance_criteria': [f'AC-1: The approved behavior holds → {ref}']}


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='spec-refs-')
        self.root = Path(self.tmp.name)
        self.plan = self.root / 'docs/specs/changes/demo'

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_real_target_rejected(self):
        self.assertTrue(missing_references([criterion()], self.root, self.plan))

    def test_mention_is_not_definition(self):
        write(self.root / 'docs/specs/use-cases/auth/UC-001-auth.md', 'History mentions AC-1.\n')
        self.assertTrue(missing_references([criterion()], self.root, self.plan))

    def test_legacy_live_and_current_delta(self):
        live = self.root / 'docs/specs/use-cases/auth/UC-001-auth.md'
        write(live, '# Use case\n## Điều kiện nghiệm thu\n### AC-1: Allowed\nThe expected behavior.\n')  # scrub-allow: fixture
        self.assertEqual([], missing_references([criterion()], self.root, self.plan))
        write(self.plan / 'deltas/auth/UC-001-auth.md', '## AC thêm\n### AC-2: New behavior\nExpected.\n')  # scrub-allow: fixture
        self.assertEqual([], missing_references([criterion('UC-001/AC-2')], self.root, self.plan))
        write(self.plan / 'deltas/auth/UC-001-auth.md', '## AC bỏ\n- AC-1 — retired\n')  # scrub-allow: fixture
        self.assertTrue(missing_references([criterion()], self.root, self.plan))

    def test_unrelated_change_cannot_supply_target(self):
        write(self.root / 'docs/specs/changes/other/deltas/auth/UC-001-auth.md', '## AC thêm\n### AC-1: Allowed\n')  # scrub-allow: fixture
        self.assertTrue(missing_references([criterion()], self.root, self.plan))

    def test_legacy_unconfirmed_and_retired_are_rejected(self):
        write(self.root / 'docs/specs/use-cases/_legacy/UC-001-auth.md', '### AC-1: Allowed\n')
        self.assertTrue(missing_references([criterion()], self.root, self.plan))
        write(self.root / 'docs/specs/use-cases/auth/UC-001-auth.md', '### AC-1: Allowed\nngừng áp dụng\n')  # scrub-allow: fixture
        self.assertTrue(missing_references([criterion()], self.root, self.plan))

    def test_requirement_delta_in_the_plan_folder_supplies_and_removed_rejects(self):
        write(self.root / 'docs/specs/use-cases/auth/UC-001-auth.md', '### AC-1: Allowed\n')
        delta = self.plan / 'specs/auth/spec.md'
        write(delta, '## MODIFIED Requirements\n### Requirement: UC-001/AC-1 - Allowed\n')
        self.assertEqual([], missing_references([criterion()], self.root, self.plan))
        write(delta, '## ADDED Requirements\n### Requirement: UC-001/AC-2 - New behavior\n')
        self.assertEqual([], missing_references([criterion('UC-001/AC-2')], self.root, self.plan))
        write(delta, '## REMOVED Requirements\n### Requirement: UC-001/AC-1 - Allowed\n')
        self.assertTrue(missing_references([criterion()], self.root, self.plan))


class MirrorTests(unittest.TestCase):
    """chk_mirror fails closed, in process on a temp plan folder: an unreadable mirror and a mirror ticking a step the task lacks
    fail, a clean mirror passes"""

    def ctx(self):
        tmp = tempfile.TemporaryDirectory(prefix='plan-mirror-')
        self.addCleanup(tmp.cleanup)
        folder = Path(tmp.name) / 'docs/changes/demo'
        folder.mkdir(parents=True)
        step = {k: 'x' for k in VERIFY.load_yaml(VERIFY.TEMPLATE)['steps'][0]}
        step.update(n=1, action='edit', done=False, expect=None)
        return folder, {'mode': 'plan', 'plan_dir': str(folder), 'tasks': [{'id': 'T1', 'steps': [step]}]}

    @staticmethod
    def check(ctx):
        env = {k: v for k, v in os.environ.items() if k != 'PLAN_VERIFY_SKIP_MIRROR'}
        with patch.dict(os.environ, env, clear=True):
            return VERIFY.chk_mirror(ctx)

    def test_clean_mirror_passes(self):
        folder, ctx = self.ctx()
        write(folder / 'plan.en.md', '### 1. T1 \xb7 Count\n- [ ] 1.1 edit\n')
        self.assertTrue(self.check(ctx)[0])

    def test_unreadable_mirror_fails_closed(self):
        folder, ctx = self.ctx()
        (folder / 'plan.en.md').mkdir()   # a directory where the mirror file should be
        ok, msg = self.check(ctx)
        self.assertFalse(ok)
        self.assertIn('unreadable', msg)

    def test_non_utf8_mirror_fails_closed(self):
        folder, ctx = self.ctx()
        (folder / 'plan.en.md').write_bytes(b'### 1. T1 \xb7 Count\n\xff\xfe\n')
        ok, msg = self.check(ctx)
        self.assertFalse(ok)
        self.assertIn('unreadable', msg)

    def test_mirror_ticking_a_step_the_task_lacks_fails(self):
        folder, ctx = self.ctx()
        write(folder / 'plan.en.md', '### 1. T1 \xb7 Count\n- [ ] 1.1 edit\n- [ ] 1.2 extra\n')
        ok, msg = self.check(ctx)
        self.assertFalse(ok)
        self.assertIn('T1', msg)


class LoadTests(unittest.TestCase):
    def test_load_plan_yaml_without_change_design_names_folder(self):
        with tempfile.TemporaryDirectory(prefix='plan-verify-') as tmp:
            path = Path(tmp) / 'plan.yaml'
            path.write_text('plan_id: demo\ntasks: []\n')
            with self.assertRaises(ValueError) as ctx:
                VERIFY.load(str(path), None)
            self.assertIn('plan folder', str(ctx.exception))


class LocateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='plan-locate-')
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_dated_archive_found(self):
        write(self.root / 'docs/specs/changes/archive/2026-10-13-demo/plan.yaml', 'plan_id: demo\n')
        found = LOCATE.locate(self.root, 'demo')
        self.assertTrue(found['plan_dir'].endswith('archive/2026-10-13-demo'))
        self.assertEqual(found['plan_dir'], found['change_dir'])

    def test_legacy_archive_found(self):
        write(self.root / 'docs/specs/changes/archive/demo/plan.yaml', 'plan_id: demo\n')
        self.assertTrue(LOCATE.locate(self.root, 'demo')['plan_dir'].endswith('archive/demo'))

    def test_plan_outside_specs_changes_has_no_change_dir(self):
        write(self.root / 'docs/plan/demo/plan.yaml', 'plan_id: demo\n')
        self.assertIsNone(LOCATE.locate(self.root, 'demo')['change_dir'])

    def test_same_id_in_plan_and_archive_stops_resolution(self):
        write(self.root / 'docs/plan/demo/plan.yaml', 'plan_id: demo\n')
        write(self.root / 'docs/specs/changes/archive/2026-10-13-demo/plan.yaml', 'plan_id: demo\n')
        with self.assertRaisesRegex(ValueError, 'found 2'):
            LOCATE.locate(self.root, 'demo')


class SpecDeltaTests(unittest.TestCase):
    GOOD = ('## Purpose\nAuthorization fixture.\n\n## ADDED Requirements\n### Requirement: UC-001/AC-1 - Allowed\n'
            'The system SHALL allow the approved login.\n\n#### Scenario: Approved login\n'
            '- **WHEN** a user logs in\n- **THEN** access is granted\n')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='spec-delta-')
        self.root = Path(self.tmp.name)
        self.plan = self.root / 'docs/specs/changes/demo'
        self.ctx = {'root': str(self.root), 'plan_dir': str(self.plan), 'plan_id': 'demo', 'mode': 'plan'}

    def tearDown(self):
        self.tmp.cleanup()

    def spec(self, text):
        write(self.plan / 'specs/auth/spec.md', text)
        return VERIFY.chk_spec_delta(self.ctx)

    def test_good_delta_passes(self):
        self.assertTrue(self.spec(self.GOOD)[0])

    def test_requirement_without_scenario_fails_naming_the_id(self):
        ok, why = self.spec(self.GOOD.split('#### Scenario:')[0])
        self.assertFalse(ok)
        self.assertIn('UC-001/AC-1', why)

    def test_spaced_id_fails(self):
        ok, why = self.spec(self.GOOD.replace('UC-001/AC-1', 'UC-001 / AC-1'))
        self.assertFalse(ok)
        self.assertIn('UC-001 / AC-1', why)

    def test_removed_without_reason_fails_naming_the_id(self):
        ok, why = self.spec('## REMOVED Requirements\n### Requirement: UC-001/AC-2 - Retired\n**Migration**: none\n')
        self.assertFalse(ok)
        self.assertIn('UC-001/AC-2: REMOVED without Reason', why)

    def test_plan_without_change_files_skips(self):
        self.ctx['plan_dir'] = str(self.root / 'docs/plan/demo')
        ok, why = VERIFY.chk_spec_delta(self.ctx)
        self.assertTrue(ok)
        self.assertIn('skipped', why)

    def test_proposal_missing_a_template_heading_fails(self):
        write(self.plan / 'proposal.md', '# Proposal: demo\n\n## Why\nx\n\n## What Changes\nx\n\n## Capabilities\nx\n')
        ok, why = VERIFY.chk_spec_delta(self.ctx)
        self.assertFalse(ok)
        self.assertIn("'## Impact' is missing", why)


if __name__ == '__main__':
    unittest.main(verbosity=2)
