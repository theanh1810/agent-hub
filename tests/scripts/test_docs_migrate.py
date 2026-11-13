"""Tests for scripts/docs-migrate.py: the dry run's lists, its refusals, and its stat-only handling of archives and test-evidence."""
import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / 'plugins' / 'agent-hub' / 'scripts' / 'docs-migrate.py'
spec = importlib.util.spec_from_file_location('docs_migrate', SCRIPT)
DM = importlib.util.module_from_spec(spec)
spec.loader.exec_module(DM)   # a hyphenated file name: loaded by path, as test_review_packet.py does


def put(root, rel, text='x\n', mtime=None, mode=None):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')
    if mtime is not None:
        os.utime(p, (mtime, mtime))
    if mode is not None:
        os.chmod(p, mode)
    return p


def base_tree(ws):
    """one file per mapping rule of the target layout (docs/changes/<id>/, docs/brainstorm/, docs/changes/adhoc/)"""
    put(ws, 'docs/plan/alpha/plan.yaml', 'plan_id: alpha\ntasks:\n- {id: T1, file: tasks/W1/T1.yaml}\n')   # whole legacy plan
    put(ws, 'docs/plan/alpha/tasks/W1/T1.yaml', 'id: T1\n')
    put(ws, 'docs/plan/alpha/plan.vi.md', '# alpha\n')
    put(ws, 'docs/plan/beta/errors.yaml', 'meta: {}\n')                # sidecar of the active change beta
    put(ws, 'docs/plan/gamma/errors.yaml', 'meta: {}\n')               # sidecar of the archived change gamma
    put(ws, 'docs/specs/changes/beta/plan.yaml', 'plan_id: beta\n')
    put(ws, 'docs/specs/changes/beta/proposal.md', '# beta\n')
    put(ws, 'docs/specs/changes/archive/2026-01-02-gamma/plan.yaml', 'plan_id: gamma\n')
    put(ws, 'docs/analysis/beta.yaml', 'plan_id: beta\n')              # strong key: plan_id in the id set scrub-allow: legacy path fixture
    put(ws, 'docs/analysis/beta-followup.yaml', 'slug: beta-followup\n')   # prefix only: weak scrub-allow: legacy path fixture
    put(ws, 'docs/analysis/delta.yaml', 'plan_id: delta\n')            # strong key, no change folder scrub-allow: legacy path fixture
    put(ws, 'docs/analysis/rejected-requests.md', '# r\n')   # scrub-allow: legacy path fixture
    put(ws, 'docs/design/beta-ui/DESIGN.md', '# D\nPlan: beta\n')     # DESIGN.md plan row names an id
    put(ws, 'docs/design/lonely/DESIGN.md', '# D\n')                   # no key
    put(ws, 'docs/reviews/beta/independent-r1.md')                      # folder name equals an id
    put(ws, 'docs/reviews/adhoc/2026-01-03-repo-fix.md')
    put(ws, 'docs/adhoc/note.md')
    put(ws, 'docs/reviews/INDEX.md')                                    # unchanged
    put(ws, 'docs/errors/s1.yaml')                                      # unchanged
    put(ws, 'docs/specs/README.md')                                     # unchanged (live layer)
    put(ws, 'docs/requietment/ba.docx')                                 # never listed


EXPECTED = {
    'docs/plan/alpha/plan.yaml': ('docs/changes/alpha/plan.yaml', 'move'),
    'docs/plan/alpha/tasks/W1/T1.yaml': ('docs/changes/alpha/tasks/W1/T1.yaml', 'move'),
    'docs/plan/alpha/plan.vi.md': ('docs/changes/alpha/plan.vi.md', 'move'),
    'docs/plan/beta/errors.yaml': ('docs/changes/beta/errors.yaml', 'merge'),
    'docs/plan/gamma/errors.yaml': ('docs/changes/archive/2026-01-02-gamma/errors.yaml', 'merge'),
    'docs/specs/changes/beta/plan.yaml': ('docs/changes/beta/plan.yaml', 'move'),
    'docs/specs/changes/beta/proposal.md': ('docs/changes/beta/proposal.md', 'move'),
    'docs/specs/changes/archive/2026-01-02-gamma/plan.yaml': ('docs/changes/archive/2026-01-02-gamma/plan.yaml', 'move'),
    'docs/analysis/beta.yaml': ('docs/changes/beta/beta.yaml', 'move'),   # scrub-allow: legacy path fixture
    'docs/analysis/beta-followup.yaml': ('docs/brainstorm/beta-followup.yaml', 'move'),   # scrub-allow: legacy path fixture
    'docs/analysis/delta.yaml': ('docs/changes/delta/delta.yaml', 'move'),   # scrub-allow: legacy path fixture
    'docs/analysis/rejected-requests.md': ('docs/brainstorm/rejected-requests.md', 'move'),   # scrub-allow: legacy path fixture
    'docs/design/beta-ui/DESIGN.md': ('docs/changes/beta/design/beta-ui/DESIGN.md', 'move'),
    'docs/design/lonely/DESIGN.md': ('docs/brainstorm/lonely/design/DESIGN.md', 'move'),
    'docs/reviews/beta/independent-r1.md': ('docs/changes/beta/reviews/independent-r1.md', 'move'),
    'docs/reviews/adhoc/2026-01-03-repo-fix.md': ('docs/changes/adhoc/2026-01-03-repo-fix.md', 'move'),
    'docs/adhoc/note.md': ('docs/changes/adhoc/note.md', 'move'),
}


def prune_tree(ws):
    """the six U8 categories inside docs/plan/alpha and docs/specs/changes/beta (needs base_tree)"""
    put(ws, 'docs/plan/alpha/amend-1.md')
    put(ws, 'docs/plan/alpha/plan.full.yaml.bak')
    put(ws, 'docs/plan/alpha/evidence/x.txt')
    put(ws, 'docs/plan/alpha/validation/y.txt')
    put(ws, 'docs/specs/changes/beta/results.md')
    put(ws, 'docs/plan/alpha/plan.vi.md', 'a.png\na.png\nb.png\n')   # a.png cited on 2 lines, b.png on 1
    a = 'docs/plan/alpha/reviews/assets'
    for rel, t in (('W1-T1/a.png', 100), ('W1-T1/b.png', 200), ('W1-T1/c.png', 300), ('W1-T1/d.png', 400),
                   ('W1-T1/e.png', 50), ('W1-T1/sub/f.png', 500), ('W1-T2/g.png', 1), ('W1-T2/h.png', 2), ('W1-T2/i.png', 3),
                   ('loose.png', 4)):
        put(ws, f'{a}/{rel}', 'png', mtime=t)


def stat_tree(ws):
    """stat-only roots (files chmod 000, so any open raises) and .cm-tmp entries"""
    put(ws, 'docs/archives/a.bin', '12345', mode=0)
    put(ws, 'docs/archives/sub/b.bin', '123', mode=0)
    put(ws, 'docs/test-evidence/e.png', '1234567', mode=0)
    put(ws, '.cm-tmp/old1/x', '12')
    put(ws, '.cm-tmp/local-e2e-stack/y', '1234')


def snapshot(root):
    """{relative path: (sha256, mtime_ns)} of every readable file under root"""
    out = {}
    for dp, _, fs in os.walk(root):
        for f in fs:
            p = Path(dp) / f
            out[str(p.relative_to(root))] = (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
    return out


def listing(root):
    """{relative path: size} by os.lstat only: usable where files are chmod 000"""
    return {str(Path(dp, f).relative_to(root)): os.lstat(Path(dp, f)).st_size for dp, _, fs in os.walk(root) for f in fs}


def tsv(path):
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    head = lines[0].split('\t')
    return [dict(zip(head, l.split('\t'))) for l in lines[1:]]


class DryRunCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='docs-migrate-')
        self.addCleanup(self.tmp.cleanup)
        self.ws, self.out = Path(self.tmp.name) / 'ws', Path(self.tmp.name) / 'out'
        base_tree(self.ws)

    def run_dm(self, *extra):
        return DM.main(['--workspace', str(self.ws), '--out', str(self.out), *extra])


class MappingTests(DryRunCase):
    def test_dry_run_writes_the_map_and_leaves_the_workspace_byte_identical(self):
        """every rule of the layout yields its EXPECTED row; manifest before == after; exit 0; weak.tsv holds only beta-followup; ids.txt lists the id set sorted, one per line"""
        before = snapshot(self.ws)
        self.assertEqual(self.run_dm('--dry-run'), 0)
        self.assertEqual(snapshot(self.ws), before)
        rows = tsv(self.out / 'migration-map.tsv')
        self.assertEqual({r['old']: (r['new'], r['action']) for r in rows}, EXPECTED)
        self.assertEqual(list(rows[0]), ['old', 'new', 'action', 'key', 'strength'])
        self.assertEqual(tsv(self.out / 'stops.tsv'), [])
        weak = tsv(self.out / 'weak.tsv')
        self.assertEqual([(w['path'], w['candidate_ids']) for w in weak], [('docs/analysis/beta-followup.yaml', 'beta')])   # scrub-allow: legacy path fixture
        s = json.loads((self.out / 'summary.json').read_text(encoding='utf-8'))
        self.assertEqual(s['actions']['merge']['files'], 2)
        self.assertEqual(s['actions']['move']['files'], len(EXPECTED) - 2)
        self.assertEqual((self.out / 'ids.txt').read_text(encoding='utf-8'), 'alpha\nbeta\ndelta\ngamma\n')

    def test_unchanged_roots_and_requietment_get_no_row(self):
        """docs/errors, docs/specs/README.md, docs/reviews/INDEX.md and docs/requietment are neither mapped nor listed"""
        self.run_dm()
        olds = [r['old'] for r in tsv(self.out / 'migration-map.tsv')]
        self.assertFalse([o for o in olds if o.startswith(('docs/errors', 'docs/specs/README', 'docs/reviews/INDEX', 'docs/requietment'))])

    def test_strong_key_without_change_folder_weak_prefix_and_flat_adhoc(self):
        """delta.yaml -> docs/changes/delta/ (no plan.yaml); beta-followup.yaml -> docs/brainstorm/ and weak.tsv; both adhoc files land flat with unchanged names"""
        self.run_dm()
        m = {r['old']: r['new'] for r in tsv(self.out / 'migration-map.tsv')}
        self.assertEqual(m['docs/analysis/delta.yaml'], 'docs/changes/delta/delta.yaml')   # scrub-allow: legacy path fixture
        self.assertEqual(m['docs/analysis/beta-followup.yaml'], 'docs/brainstorm/beta-followup.yaml')   # scrub-allow: legacy path fixture
        self.assertEqual(m['docs/reviews/adhoc/2026-01-03-repo-fix.md'], 'docs/changes/adhoc/2026-01-03-repo-fix.md')
        self.assertEqual(m['docs/adhoc/note.md'], 'docs/changes/adhoc/note.md')

    def test_archived_change_sidecars_go_to_its_archive_folder(self):
        """an archived id's strong-key files (record-id, folder-name, design, reviews) land beside its archived plan.yaml, never in a second docs/changes/<id>/ folder; key and strength stay"""
        put(self.ws, 'docs/specs/changes/archive/epsilon/plan.yaml', 'plan_id: epsilon\n')   # date-less archive (date-less shape)
        put(self.ws, 'docs/analysis/epsilon.yaml', 'plan_id: epsilon\n')   # scrub-allow: legacy path fixture
        put(self.ws, 'docs/analysis/epsilon/ANALYSIS.md')   # scrub-allow: legacy path fixture
        put(self.ws, 'docs/reviews/epsilon/CLOSEOUT.md')
        put(self.ws, 'docs/analysis/gamma.yaml', 'plan_id: gamma\n')                          # dated archive (demo-app shape) scrub-allow: legacy path fixture
        put(self.ws, 'docs/design/gamma-ui/DESIGN.md', '# D\nPlan: gamma\n')
        self.run_dm()
        rows = {r['old']: r for r in tsv(self.out / 'migration-map.tsv')}
        want = {'docs/analysis/epsilon.yaml': ('docs/changes/archive/epsilon/epsilon.yaml', 'record-id'),   # scrub-allow: legacy path fixture
                'docs/analysis/epsilon/ANALYSIS.md': ('docs/changes/archive/epsilon/ANALYSIS.md', 'folder-name'),   # scrub-allow: legacy path fixture
                'docs/reviews/epsilon/CLOSEOUT.md': ('docs/changes/archive/epsilon/reviews/CLOSEOUT.md', 'folder-name'),
                'docs/analysis/gamma.yaml': ('docs/changes/archive/2026-01-02-gamma/gamma.yaml', 'record-id'),   # scrub-allow: legacy path fixture
                'docs/design/gamma-ui/DESIGN.md': ('docs/changes/archive/2026-01-02-gamma/design/gamma-ui/DESIGN.md', 'design-row')}
        for old, (new, key) in want.items():
            self.assertEqual((rows[old]['new'], rows[old]['key'], rows[old]['strength'], rows[old]['action']), (new, key, 'strong', 'move'), old)
        self.assertFalse([r['new'] for r in rows.values() if r['new'].startswith(('docs/changes/epsilon/', 'docs/changes/gamma/'))])
        for old, (new, action) in EXPECTED.items():
            self.assertEqual((rows[old]['new'], rows[old]['action']), (new, action), old)

    def test_archive_twin_helper_returns_every_match(self):
        """the twin of an id is the folder named <id> or <YYYY-MM-DD>-<id>: 0 matches -> [], 2 matches -> both, a longer name never matches"""
        self.assertEqual(DM.archive_twin(['2026-01-02-gamma'], 'delta'), [])
        self.assertEqual(DM.archive_twin(['zeta', '2026-01-05-zeta', '2026-01-05-zeta-v2'], 'zeta'), ['zeta', '2026-01-05-zeta'])


class StopTests(unittest.TestCase):
    def setUp(self):
        keep = {'demo-app': ('docs/qa/history.log', 'docs/qa/runs', 'docs/INSTALL.windows.md'),
                'demo-field': ('docs/design/WF04_EXTERNAL_REFERENCE.md', 'docs/demo-0710'),
                'demo-notes': ('docs/notes-board',)}   # the shipped KEEP_IN_PLACE is empty: a project lists its own
        p = mock.patch.dict(DM.KEEP_IN_PLACE, keep)
        p.start()
        self.addCleanup(p.stop)

    def fresh(self, name='ws'):
        tmp = tempfile.TemporaryDirectory(prefix='docs-migrate-')
        self.addCleanup(tmp.cleanup)
        ws, out = Path(tmp.name) / name, Path(tmp.name) / 'out'
        base_tree(ws)
        return ws, out

    def stops(self, ws, out, *extra):
        code = DM.main(['--workspace', str(ws), '--out', str(out), *extra])
        return code, tsv(out / 'stops.tsv')

    def test_collisions_stop_with_exit_1_and_move_nothing(self):
        """two sources to one target, two sources differing only in letter case, and a target already on disk compared casefolded each add a stops.tsv row and exit 1"""
        cases = {
            'two-sources': ('docs/specs/changes/beta/errors.yaml', 'x'),     # and docs/plan/beta/errors.yaml -> docs/changes/beta/errors.yaml
            'two-sources ': ('docs/specs/changes/beta/Errors.yaml', 'x'),    # target differs from the other only in case
            'target-exists': ('docs/changes/beta/PLAN.YAML', 'x'),           # exists on disk; plan.yaml maps to the same casefolded path
        }
        for stop, (rel, text) in cases.items():
            with self.subTest(stop=stop):
                ws, out = self.fresh()
                put(ws, rel, text)
                before = snapshot(ws)
                code, rows = self.stops(ws, out)
                self.assertEqual(code, 1)
                self.assertIn(stop.strip(), [r['stop'] for r in rows])
                self.assertEqual(snapshot(ws), before)

    def test_archive_twin_with_two_matches_stops(self):
        """a sidecar whose id has docs/specs/changes/archive/zeta and archive/2026-01-05-zeta stops with 'archive-twin' naming the sidecar path"""
        ws, out = self.fresh()
        put(ws, 'docs/plan/zeta/errors.yaml')
        put(ws, 'docs/specs/changes/archive/zeta/plan.yaml', 'plan_id: zeta\n')
        put(ws, 'docs/specs/changes/archive/2026-01-05-zeta/plan.yaml', 'plan_id: zeta\n')
        code, rows = self.stops(ws, out)
        self.assertEqual(code, 1)
        self.assertIn(('docs/plan/zeta/errors.yaml', 'archive-twin'), [(r['path'], r['stop']) for r in rows])

    def test_unmapped_entry_stops_with_no_rule(self):
        """a file kind no rule covers (docs/mystery/z.txt) is a stop 'no-rule', never a guessed target"""
        ws, out = self.fresh()
        put(ws, 'docs/mystery/z.txt')
        code, rows = self.stops(ws, out)
        self.assertEqual(code, 1)
        self.assertIn(('docs/mystery/z.txt', 'no-rule'), [(r['path'], r['stop']) for r in rows])

    def test_keep_in_place_list_is_kept_with_no_stop(self):
        """U20-U23: the listed long-lived paths of workspace 'demo-app' (and the two other neutral workspace names) are kept in place, no stop, no move or merge row, workspace untouched"""
        ws, out = self.fresh('demo-app')
        put(ws, 'docs/plan/demo-app-refocus-followup/plan.yaml', 'plan_id: demo-app-refocus-followup\n')
        kept = ['docs/qa/history.log', 'docs/qa/runs/demo-app-refocus-followup.md', 'docs/INSTALL.windows.md']
        for rel in kept:
            put(ws, rel)
        before = snapshot(ws)
        code, rows = self.stops(ws, out, '--profile', 'move-only')
        self.assertEqual(code, 0)
        self.assertEqual(rows, [])
        moved = {r['old'] for r in tsv(out / 'migration-map.tsv') if r['action'] in ('move', 'merge')}
        for rel in kept:
            self.assertNotIn(rel, moved)
        self.assertEqual(snapshot(ws), before)
        for name, rels in (('demo-field', ['docs/design/WF04_EXTERNAL_REFERENCE.md', 'docs/demo-0710/a.md']),
                           ('demo-notes', ['docs/notes-board/README.md'])):
            ws2, out2 = self.fresh(name)
            for rel in rels:
                put(ws2, rel)
            code, rows = self.stops(ws2, out2, '--profile', 'move-only')
            self.assertEqual((code, rows), (0, []))

    def test_unlisted_neighbour_of_a_kept_path_still_stops(self):
        """U23: docs/qa-old, docs/demo-0711, docs/design/OTHER.md and docs/install.md are not in the list: each stops 'no-rule', exit 1"""
        ws, out = self.fresh('demo-app')
        unlisted = ['docs/qa-old/x.md', 'docs/demo-0711/x.md', 'docs/design/OTHER.md', 'docs/install.md']
        for rel in unlisted:
            put(ws, rel)
        code, rows = self.stops(ws, out)
        self.assertEqual(code, 1)
        got = {(r['path'], r['stop']) for r in rows}
        for rel in unlisted:
            self.assertIn((rel, 'no-rule'), got)

    def test_listed_path_in_an_unlisted_workspace_still_stops(self):
        """U23: the list is per workspace name: docs/qa/x.md in a workspace named 'other' stops 'no-rule', exit 1"""
        ws, out = self.fresh('other')
        put(ws, 'docs/qa/x.md')
        code, rows = self.stops(ws, out)
        self.assertEqual(code, 1)
        self.assertIn(('docs/qa/x.md', 'no-rule'), [(r['path'], r['stop']) for r in rows])

    def test_prune_candidate_named_by_a_task_file_value_or_under_tasks_stops(self):
        """results.md named by plan.yaml tasks[].file, and evidence/x.txt lying under tasks/W1/, each stop 'prune-protected' (profile prune)"""
        for name, files in (('named', {'docs/plan/alpha/plan.yaml': 'plan_id: alpha\ntasks:\n- {id: T1, file: results.md}\n',
                                       'docs/plan/alpha/results.md': 'x'}),
                            ('under-tasks', {'docs/plan/alpha/tasks/W1/evidence/x.txt': 'x'})):
            with self.subTest(name=name):
                ws, out = self.fresh()
                for rel, text in files.items():
                    put(ws, rel, text)
                code, rows = self.stops(ws, out, '--profile', 'prune')
                self.assertEqual(code, 1)
                self.assertIn('prune-protected', [r['stop'] for r in rows])


class ProfileTests(DryRunCase):
    def test_move_only_writes_no_prune_or_delete_list(self):
        """--profile move-only (the default) writes neither prune-list.tsv nor delete-list.tsv even where prune candidates exist"""
        prune_tree(self.ws)
        self.assertEqual(self.run_dm('--profile', 'move-only'), 0)
        self.assertFalse((self.out / 'prune-list.tsv').exists())
        self.assertFalse((self.out / 'delete-list.tsv').exists())

    def test_prune_profile_lists_the_six_categories_and_keeps_the_top_3_images(self):
        """amend, bak, evidence, validation, results and image rows; in W1-T1 keep a.png (2 citations), b.png (1), sub/f.png (newest uncited, mtime 500); prune d.png, c.png, e.png; W1-T2 (3 images) and assets/loose.png untouched"""
        prune_tree(self.ws)
        self.assertEqual(self.run_dm('--profile', 'prune'), 0)
        rows = tsv(self.out / 'prune-list.tsv')
        self.assertEqual(list(rows[0]), ['category', 'path', 'files', 'bytes', 'citations', 'in_backup'])
        got = {r['path']: r['category'] for r in rows}
        a = 'docs/plan/alpha/reviews/assets/W1-T1'
        self.assertEqual(got, {
            'docs/plan/alpha/amend-1.md': 'amend', 'docs/plan/alpha/plan.full.yaml.bak': 'bak',
            'docs/plan/alpha/evidence/x.txt': 'evidence', 'docs/plan/alpha/validation/y.txt': 'validation',
            'docs/specs/changes/beta/results.md': 'results',
            f'{a}/d.png': 'image', f'{a}/c.png': 'image', f'{a}/e.png': 'image'})
        self.assertEqual({r['in_backup'] for r in rows}, {'yes'})

    def test_image_groups_count_subfolders_and_rank_cited_first(self):
        """the group is the first path segment under assets/ counted recursively; citations are the lines of the change's .md/.yaml files naming the basename"""
        prune_tree(self.ws)
        self.run_dm('--profile', 'prune')
        cited = {Path(r['path']).name: r['citations'] for r in tsv(self.out / 'prune-list.tsv') if r['category'] == 'image'}
        self.assertEqual(cited, {'d.png': '0', 'c.png': '0', 'e.png': '0'})

    def test_stat_only_roots_are_counted_by_lstat_and_never_opened(self):
        """docs/archives (a.bin 5 B, sub/b.bin 3 B) and docs/test-evidence (e.png 7 B) are chmod 000; the run exits 0 and reports files and bytes; .cm-tmp/local-e2e-stack is not on the delete list"""
        stat_tree(self.ws)
        self.addCleanup(lambda: [os.chmod(p, 0o600) for p in self.ws.rglob('*.*') if p.is_file()])
        self.assertEqual(self.run_dm('--profile', 'prune', '--keep', 'local-e2e-stack'), 0)
        rows = {r['path']: (r['category'], r['files'], r['bytes']) for r in tsv(self.out / 'delete-list.tsv')}
        self.assertEqual(rows, {'docs/archives': ('archives', '2', '8'), 'docs/test-evidence': ('test-evidence', '1', '7'),
                                '.cm-tmp/old1': ('cm-tmp', '1', '2')})
        s = json.loads((self.out / 'summary.json').read_text(encoding='utf-8'))
        self.assertEqual(s['stat_only']['docs/archives'], {'files': 2, 'bytes': 8})
        self.assertNotIn('docs/archives/a.bin', {r['old'] for r in tsv(self.out / 'migration-map.tsv')})


class RefusalTests(DryRunCase):
    def test_out_inside_docs_or_cm_tmp_is_refused_with_exit_2(self):
        """--out under <ws>/docs or <ws>/.cm-tmp exits 2, creates nothing, and leaves the workspace byte-identical"""
        before = snapshot(self.ws)
        for out in (self.ws / 'docs/out', self.ws / '.cm-tmp/out'):
            with self.subTest(out=str(out)):
                code = DM.main(['--workspace', str(self.ws), '--out', str(out)])
                self.assertEqual(code, 2)
                self.assertFalse(out.exists())
        self.assertEqual(snapshot(self.ws), before)


import contextlib
import io
import subprocess
import sys

FAKE_LOCATE = """import glob, json, os, sys
ws, pid = sys.argv[2], sys.argv[3]
hits = sorted(set(glob.glob(ws + '/docs/**/' + pid + '/plan.yaml', recursive=True)
                  + glob.glob(ws + '/docs/**/????-??-??-' + pid + '/plan.yaml', recursive=True)))
if len(hits) != 1:
    print('plan-locate: %s: expected one plan, found %d: %s' % (pid, len(hits), hits), file=sys.stderr)
    sys.exit(1)
d = os.path.dirname(hits[0])
if os.environ.get('FAKE_LOCATE_DIFF') and os.path.realpath(os.environ.get('FAKE_LOCATE_DIFF_ROOT', ws)) == os.path.realpath(ws):
    d = ws + '/docs/other'
rec = [p for p in (d + '/design.yaml', d + '/' + pid + '.yaml', ws + '/docs/analysis/' + pid + '.yaml') if os.path.isfile(p)]   # scrub-allow: legacy path fixture
print(json.dumps({'plan_id': pid, 'plan_dir': d, 'analysis_ref': rec[0] if rec else None}))
"""
IDS = ('alpha', 'beta', 'gamma', 'delta')   # the id set of base_tree: folder names, archive date stripped, and analysis plan_id values


def record_verdicts(ws, locate, dest, ids=IDS):
    """what the T3 loop does: run plan-locate per id, strip the workspace prefix, write verdicts.tsv"""
    rows = ['id\tstatus\tplan_dir\tanalysis_ref\terror']
    for i in ids:
        p = subprocess.run([*locate.split(), '--workspace', str(ws), i], capture_output=True, text=True)
        if p.returncode == 0:
            j = json.loads(p.stdout)
            rows.append('\t'.join([i, 'ok', j['plan_dir'].replace(str(ws) + os.sep, '').replace(str(ws) + '/', '').replace(os.sep, '/'), (j['analysis_ref'] or '').replace(str(ws) + os.sep, '').replace(str(ws) + '/', '').replace(os.sep, '/'), '']))
        else:
            rows.append('\t'.join([i, 'error', '', '', p.stderr.strip().split('plan-locate: ', 1)[1].replace(str(ws) + os.sep, '').replace(str(ws) + '/', '').replace(os.sep, '/')]))
    Path(dest).write_text('\n'.join(rows) + '\n', encoding='utf-8')


class MoveCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='docs-migrate-')
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name).resolve()   # the real plan-locate prints resolved paths (macOS /var -> /private/var)
        self.ws, self.out, self.v = base / 'ws', base / 'out', base / 'verdicts.tsv'
        self.fake = base / 'fake_locate.py'
        self.fake.write_text(FAKE_LOCATE, encoding='utf-8')
        self.locate = f'{sys.executable} {self.fake}'
        base_tree(self.ws)
        self.extra_tree()
        record_verdicts(self.ws, self.locate, self.v, self.IDS)

    IDS = IDS

    def extra_tree(self):
        pass

    def dm(self, *argv, stderr=False):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = DM.main(['--workspace', str(self.ws), '--out', str(self.out), *argv])
        return (code, err.getvalue()) if stderr else code

    def apply(self, *extra, **kw):
        return self.dm('--apply', '--locate', self.locate, '--verdicts', str(self.v), *extra, **kw)


class ApplyTests(MoveCase):
    def test_apply_moves_every_row_with_sha256_and_mtime_kept(self):
        """each EXPECTED old file is gone and its new file has the same sha256 and mtime_ns; MIGRATION-MAP.tsv (old_path, new_path, action) lists moved|merged rows; emptied legacy roots are removed, docs/reviews/INDEX.md and docs/specs/README.md stay; exit 0"""
        os.utime(self.ws / 'docs/plan/alpha/plan.vi.md', (1000, 1000))
        before = snapshot(self.ws)
        self.assertEqual(self.apply(), 0)
        after = snapshot(self.ws)
        for old, (new, _) in EXPECTED.items():
            self.assertNotIn(old, after)
            self.assertEqual(after[new], before[old])
        rows = tsv(self.ws / 'docs/changes/MIGRATION-MAP.tsv')
        self.assertEqual(list(rows[0]), ['old_path', 'new_path', 'action'])
        self.assertEqual({r['old_path']: (r['new_path'], r['action']) for r in rows},
                         {o: (n, 'merged' if a == 'merge' else 'moved') for o, (n, a) in EXPECTED.items()})
        for gone in ('docs/plan', 'docs/analysis', 'docs/design', 'docs/specs/changes', 'docs/adhoc', 'docs/reviews/adhoc'):
            self.assertFalse((self.ws / gone).exists(), gone)
        self.assertTrue((self.ws / 'docs/reviews/INDEX.md').exists())
        self.assertTrue((self.ws / 'docs/specs/README.md').exists())

    def test_second_apply_moves_nothing_and_exits_0(self):
        """retry: a second --apply exits 0 and leaves the tree, manifest-before.tsv and MIGRATION-MAP.tsv byte-identical"""
        self.assertEqual(self.apply(), 0)
        tree = snapshot(self.ws)
        mb = (self.out / 'manifest-before.tsv').read_bytes()
        self.assertEqual(self.apply(), 0)
        self.assertEqual(snapshot(self.ws), tree)
        self.assertEqual((self.out / 'manifest-before.tsv').read_bytes(), mb)

    def test_verdict_differing_after_the_move_exits_1_and_writes_no_map(self):
        """partial failure: FAKE_LOCATE_DIFF_ROOT names the real workspace, so the pre-flight shadow tree passes and only the post-move plan_dir differs: --apply exits 1 naming alpha; the files stay moved, manifest-before.tsv exists, MIGRATION-MAP.tsv is not written and docs/plan is not removed"""
        os.environ['FAKE_LOCATE_DIFF'] = '1'
        os.environ['FAKE_LOCATE_DIFF_ROOT'] = str(self.ws)
        self.addCleanup(os.environ.pop, 'FAKE_LOCATE_DIFF', None)
        self.addCleanup(os.environ.pop, 'FAKE_LOCATE_DIFF_ROOT', None)
        code, err = self.apply(stderr=True)
        self.assertEqual(code, 1)
        self.assertIn('alpha', err)
        self.assertTrue((self.ws / 'docs/changes/alpha/plan.yaml').exists())
        self.assertTrue((self.out / 'manifest-before.tsv').exists())
        self.assertFalse((self.ws / 'docs/changes/MIGRATION-MAP.tsv').exists())
        self.assertTrue((self.ws / 'docs/plan').exists())

    def test_preflight_refuses_before_any_rename_when_a_verdict_would_change(self):
        """a verdict that differs on the shadow tree exits 2 naming the id with 'nothing moved'; the workspace is byte-identical, no manifest-before.tsv and no .preflight-shadow is left"""
        os.environ['FAKE_LOCATE_DIFF'] = '1'
        self.addCleanup(os.environ.pop, 'FAKE_LOCATE_DIFF', None)
        before = snapshot(self.ws)
        code, err = self.apply(stderr=True)
        self.assertEqual(code, 2)
        self.assertIn('preflight: verdict differs: alpha', err)
        self.assertIn('nothing moved', err)
        self.assertEqual(snapshot(self.ws), before)
        self.assertFalse((self.out / 'manifest-before.tsv').exists())
        self.assertFalse((self.out / '.preflight-shadow').exists())

    def refused(self, verdicts):
        before = snapshot(self.ws)
        code, err = self.dm('--apply', '--locate', self.locate, '--verdicts', str(verdicts), stderr=True)
        self.assertEqual(code, 2)
        self.assertEqual(snapshot(self.ws), before)
        self.assertFalse((self.out / 'manifest-before.tsv').exists())
        return err

    def test_missing_verdicts_file_refuses_before_any_rename(self):
        """a --verdicts path that is not a file exits 2 naming the path; nothing is moved and no manifest-before.tsv is written"""
        absent = Path(self.tmp.name) / 'absent.tsv'
        self.assertIn(str(absent), self.refused(absent))

    def test_malformed_verdicts_refuse_before_any_rename(self):
        """a verdicts file with a row holding an unquoted newline exits 2 before the first rename"""
        bad = Path(self.tmp.name) / 'bad.tsv'
        bad.write_text(self.v.read_text(encoding='utf-8') + 'zeta\terror\t\t\tline one\nline two\n', encoding='utf-8')
        self.refused(bad)

    def test_verdicts_missing_an_id_refuse_before_any_rename(self):
        """a verdicts file without the row of 'delta' exits 2 naming delta before the first rename"""
        short = Path(self.tmp.name) / 'short.tsv'
        lines = self.v.read_text(encoding='utf-8').splitlines(keepends=True)
        short.write_text(''.join(l for l in lines if not l.startswith('delta\t')), encoding='utf-8')
        self.assertIn('delta', self.refused(short))

    def test_error_verdicts_compare_without_their_path_lists(self):
        """an error row stays the same error when only the bracketed paths change, and differs when the count changes"""
        old = {'id': 'd', 'status': 'error', 'plan_dir': '', 'analysis_ref': '', 'error': "d: expected one plan, found 2: ['docs/plan/d/plan.yaml', 'docs/specs/changes/d/plan.yaml']"}
        same = dict(old, error="d: expected one plan, found 2: ['docs/changes/d/plan.yaml', 'docs/changes/archive/d/plan.yaml']")
        other = dict(old, error="d: expected one plan, found 1: ['docs/changes/d/plan.yaml']")
        self.assertTrue(DM.verdict_matches(old, same, lambda p: None))
        self.assertFalse(DM.verdict_matches(old, other, lambda p: None))


class ArchivedRecordTests(MoveCase):
    """the real plan-locate gives the same verdicts after --apply for archived changes (epsilon date-less, gamma dated, zeta two records)"""
    IDS = IDS + ('epsilon', 'zeta')

    def setUp(self):
        self.locate_real = f'{sys.executable} {Path(DM.__file__).with_name("plan-locate.py")}'
        super().setUp()
        record_verdicts(self.ws, self.locate_real, self.v, self.IDS)
        self.locate = self.locate_real

    def extra_tree(self):
        put(self.ws, 'docs/specs/changes/archive/epsilon/plan.yaml', 'plan_id: epsilon\n')
        put(self.ws, 'docs/analysis/epsilon.yaml', 'plan_id: epsilon\n')   # scrub-allow: legacy path fixture
        put(self.ws, 'docs/analysis/epsilon/ANALYSIS.md')   # scrub-allow: legacy path fixture
        put(self.ws, 'docs/reviews/epsilon/CLOSEOUT.md')
        put(self.ws, 'docs/analysis/gamma.yaml', 'plan_id: gamma\n')   # scrub-allow: legacy path fixture
        put(self.ws, 'docs/design/gamma-ui/DESIGN.md', '# D\nPlan: gamma\n')
        put(self.ws, 'docs/specs/changes/archive/2026-01-03-zeta/plan.yaml', 'plan_id: zeta\n')
        put(self.ws, 'docs/specs/changes/archive/2026-01-03-zeta/design.yaml', 'plan_id: zeta\n')
        put(self.ws, 'docs/analysis/zeta.yaml', 'plan_id: zeta\n')   # scrub-allow: legacy path fixture

    def test_archived_records_keep_their_verdict_through_apply(self):
        code, err = self.dm('--apply', '--locate', self.locate_real, '--verdicts', str(self.v), stderr=True)
        self.assertEqual((code, err), (0, ''))
        self.assertTrue((self.ws / 'docs/changes/MIGRATION-MAP.tsv').is_file())
        after = {i: DM.run_locate(self.locate_real, self.ws, i) for i in self.IDS}
        for i in ('epsilon', 'gamma'):
            self.assertEqual(after[i]['status'], 'ok', i)
        self.assertTrue(after['epsilon']['analysis_ref'].startswith('docs/changes/archive/epsilon/'))
        self.assertTrue(after['gamma']['analysis_ref'].startswith('docs/changes/archive/2026-01-02-gamma/'))
        self.assertEqual(after['zeta']['status'], 'error')
        self.assertIn('multiple machine records', after['zeta']['error'])

    def test_apply_without_locate_needs_no_python3_on_path(self):
        """no --locate: the default runs plan-locate.py beside the script with the running interpreter, so an empty PATH changes nothing"""
        empty = Path(self.tmp.name) / 'empty-path'
        empty.mkdir()
        with mock.patch.dict(os.environ, {'PATH': str(empty)}):
            code, err = self.dm('--apply', '--verdicts', str(self.v), stderr=True)
        self.assertEqual((code, err), (0, ''))
        self.assertTrue((self.ws / 'docs/changes/MIGRATION-MAP.tsv').is_file())


class VerifyTests(MoveCase):
    def moved(self):
        self.assertEqual(self.apply(), 0)

    def test_verify_names_the_path_of_a_tampered_byte(self):
        """one byte of docs/changes/alpha/plan.yaml flipped after the move -> --verify --locate skip exits 1 and names that path"""
        self.moved()
        p = self.ws / 'docs/changes/alpha/plan.yaml'
        p.write_bytes(b'X' + p.read_bytes()[1:])
        code, err = self.dm('--verify', '--locate', 'skip', stderr=True)
        self.assertEqual(code, 1)
        self.assertIn('docs/changes/alpha/plan.yaml', err)

    def test_verify_names_the_id_whose_plan_yaml_count_changed(self):
        """docs/changes/beta/plan.yaml removed after the move -> --verify exits 1 and names beta"""
        self.moved()
        (self.ws / 'docs/changes/beta/plan.yaml').unlink()
        code, err = self.dm('--verify', '--locate', 'skip', stderr=True)
        self.assertEqual(code, 1)
        self.assertIn('beta', err)


class DeleteCase(MoveCase):
    def extra_tree(self):
        prune_tree(self.ws)
        stat_tree(self.ws)
        put(self.ws, 'docs/reviews/baselines/r-desktop/x.png', 'png')
        put(self.ws, 'other/x.txt')

    def setUp(self):
        super().setUp()
        self.addCleanup(lambda: [os.chmod(p, 0o600) for p in self.ws.rglob('*.*') if p.is_file()])
        self.assertEqual(self.apply('--profile', 'prune', '--keep', 'local-e2e-stack'), 0)
        self.approved = Path(self.tmp.name) / 'approved.tsv'
        self.write_approved([])

    def live_rows(self):
        out2 = Path(self.tmp.name) / 'out2'
        self.assertEqual(DM.main(['--workspace', str(self.ws), '--out', str(out2), '--profile', 'prune', '--keep', 'local-e2e-stack']), 0)
        return [r for f in ('prune-list.tsv', 'delete-list.tsv') for r in tsv(out2 / f)]

    def pick(self, prune):
        """the path of the first live prune row (prune=True) or delete row (prune=False)"""
        return next(r for r in self.live_rows() if (r['category'] in DM.PRUNE_CATEGORIES) == prune)['path']

    def write_approved(self, extra, drop=None, alter=None, empty=False):
        """drop: a live path left out; alter: a live path whose files and bytes are changed; empty: header only"""
        rows = [] if empty else [dict(r, files='999999', bytes='999999') if r['path'] == alter else r
                                 for r in self.live_rows() if r['path'] != drop] + extra
        lines = ['category\tpath\tfiles\tbytes'] + ['\t'.join([r['category'], r['path'], r['files'], r['bytes']]) for r in rows]
        self.approved.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    def delete(self, stderr=True):
        return self.dm('--delete', str(self.approved), '--profile', 'prune', '--keep', 'local-e2e-stack', stderr=stderr)


@unittest.skipIf(os.name == 'nt', 'docs-migrate --delete is refused on Windows')
class DeleteTests(DeleteCase):
    def test_delete_refuses_and_removes_nothing(self):
        """an empty list, a row whose files or bytes differ from its live row (a prune row and a delete row alike, DC-57), an extra row absent from the live list, and rows outside docs/ and .cm-tmp, under docs/requietment, under the live docs/specs layer, under docs/reviews/baselines, or naming the --keep entry, each exit 1 naming the path and leave the tree unchanged"""
        cases = {'empty': ('empty', None), 'differs-prune': ('alter', self.pick(True)), 'differs-delete': ('alter', self.pick(False)),
                 'absent': ('delete', '.cm-tmp/not-in-the-live-list'), 'outside': ('other', 'other/x.txt'),
                 'requietment': ('prune', 'docs/requietment/ba.docx'), 'specs': ('prune', 'docs/specs/README.md'),
                 'baselines': ('prune', 'docs/reviews/baselines/r-desktop/x.png'), 'keep': ('delete', '.cm-tmp/local-e2e-stack')}
        for name, (cat, path) in cases.items():
            with self.subTest(name=name):
                before = listing(self.ws)
                if cat == 'empty':
                    self.write_approved([], empty=True)
                elif cat == 'alter':
                    self.write_approved([], alter=path)
                else:
                    self.write_approved([{'category': cat, 'path': path, 'files': '1', 'bytes': '1'}])
                code, err = self.delete()
                self.assertEqual(code, 1)
                if path:
                    self.assertIn(path, err)
                self.assertEqual(listing(self.ws), before)

    def test_a_list_missing_one_live_row_deletes_the_rest_and_marks_kept_by_user(self):
        """a list with the live row docs/archives left out exits 0, removes every other approved path (docs/test-evidence, .cm-tmp/old1, the pruned files), leaves docs/archives on disk, and its pending-delete map row reads kept-by-user; no pending-delete row is left"""
        self.write_approved([], drop='docs/archives')
        self.assertEqual(self.delete()[0], 0)
        self.assertTrue((self.ws / 'docs/archives').is_dir())
        for gone in ('docs/test-evidence', '.cm-tmp/old1', 'docs/changes/alpha/amend-1.md'):
            self.assertFalse((self.ws / gone).exists(), gone)
        rows = {r['old_path']: r for r in tsv(self.ws / 'docs/changes/MIGRATION-MAP.tsv')}
        self.assertNotIn('pending-delete', {r['action'] for r in rows.values()})
        self.assertEqual((rows['docs/archives/']['new_path'], rows['docs/archives/']['action']), ('-', 'kept-by-user'))
        self.assertEqual(rows['docs/test-evidence/']['action'], 'deleted-not-backed-up')
        self.assertEqual(rows['docs/plan/alpha/amend-1.md']['action'], 'pruned-in-backup')

    def test_open_file_under_a_target_stops_the_delete(self):
        """a child process holding .cm-tmp/old1/x open makes `lsof +D` report it; --delete exits 1 and every approved path still exists"""
        child = subprocess.Popen([sys.executable, '-c', 'import sys, time; f = open(sys.argv[1]); print("ready", flush=True); time.sleep(60)',
                                  str(self.ws / '.cm-tmp/old1/x')], stdout=subprocess.PIPE, text=True)
        self.addCleanup(child.kill)
        child.stdout.readline()
        self.write_approved([])
        before = listing(self.ws)
        code, _ = self.delete()
        self.assertEqual(code, 1)
        self.assertEqual(listing(self.ws), before)

    def test_delete_removes_exactly_the_approved_list_and_reverifies(self):
        """after --delete exit 0 on the full live list: docs/test-evidence, docs/archives, .cm-tmp/old1 and the pruned files are gone, .cm-tmp/local-e2e-stack/y stays; manifest-after.tsv == manifest-before.tsv minus the pruned paths (mapped through the move); no pending-delete row is left (pruned-in-backup for files, deleted-not-backed-up for the two folder lines)"""
        self.write_approved([])
        pruned = {r['path'] for r in tsv(self.approved) if r['category'] in DM.PRUNE_CATEGORIES}
        self.assertEqual(self.delete()[0], 0)
        for gone in ('docs/test-evidence', 'docs/archives', '.cm-tmp/old1', 'docs/changes/alpha/amend-1.md'):
            self.assertFalse((self.ws / gone).exists(), gone)
        self.assertTrue((self.ws / '.cm-tmp/local-e2e-stack/y').exists())
        before = {r['path']: r['sha256'] for r in tsv(self.out / 'manifest-before.tsv')}
        after = {r['path']: r['sha256'] for r in tsv(self.out / 'manifest-after.tsv')}

        def to_new(p):
            if p in EXPECTED:
                return EXPECTED[p][0]
            for old, new in (('docs/plan/alpha/', 'docs/changes/alpha/'), ('docs/specs/changes/beta/', 'docs/changes/beta/')):
                if p.startswith(old):
                    return new + p[len(old):]
            return p
        self.assertEqual(after, {to_new(p): h for p, h in before.items() if to_new(p) not in pruned})
        rows = {r['old_path']: r for r in tsv(self.ws / 'docs/changes/MIGRATION-MAP.tsv')}
        self.assertNotIn('pending-delete', {r['action'] for r in rows.values()})
        self.assertEqual(rows['docs/plan/alpha/amend-1.md']['action'], 'pruned-in-backup')
        self.assertEqual((rows['docs/archives/']['new_path'], rows['docs/archives/']['action']), ('-', 'deleted-not-backed-up'))
        self.assertEqual(rows['docs/test-evidence/']['action'], 'deleted-not-backed-up')

    def test_cm_tmp_is_removed_only_when_it_ends_empty(self):
        """edge: with --keep local-e2e-stack .cm-tmp remains; a workspace whose only .cm-tmp entry is approved loses .cm-tmp itself"""
        self.write_approved([])
        self.assertEqual(self.delete()[0], 0)
        self.assertTrue((self.ws / '.cm-tmp').is_dir())
        tmp = tempfile.TemporaryDirectory(prefix='docs-migrate-')
        self.addCleanup(tmp.cleanup)
        ws, out = Path(tmp.name) / 'ws', Path(tmp.name) / 'out'
        base_tree(ws)
        put(ws, '.cm-tmp/old1/x', '12')
        self.assertEqual(DM.main(['--workspace', str(ws), '--out', str(out), '--apply', '--locate', 'skip', '--profile', 'prune']), 0)
        appr = Path(tmp.name) / 'a.tsv'
        rows = tsv(out / 'delete-list.tsv')
        appr.write_text('category\tpath\tfiles\tbytes\n' + ''.join('\t'.join([r['category'], r['path'], r['files'], r['bytes']]) + '\n' for r in rows), encoding='utf-8')
        self.assertEqual(DM.main(['--workspace', str(ws), '--out', str(out), '--delete', str(appr), '--profile', 'prune']), 0)
        self.assertFalse((ws / '.cm-tmp').exists())

import contextlib
import hashlib
import io
import tarfile


class VerifyTarTests(unittest.TestCase):
    """--verify-tar streams a fixture tar against a manifest and extracts nothing"""

    FILES = {'docs/a.md': b'alpha\n', 'docs/plan/p/plan.yaml': b'plan_id: p\n'}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='docs-migrate-')
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        (self.d / 'ws').mkdir()
        self.manifest = self.d / 'manifest-before.tsv'
        rows = ['path\tbytes\tsha256'] + [f'{p}\t{len(b)}\t{hashlib.sha256(b).hexdigest()}' for p, b in self.FILES.items()]
        self.manifest.write_text('\n'.join(rows) + '\n', encoding='utf-8')

    def tar(self, members):
        path = self.d / 'backup.tar.gz'
        with tarfile.open(path, 'w:gz') as tf:
            for name, data in members.items():
                ti = tarfile.TarInfo(name)
                ti.size = len(data)
                tf.addfile(ti, io.BytesIO(data))
        return path

    def run_verify(self, tar):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = DM.main(['--workspace', str(self.d / 'ws'), '--out', str(self.d / 'out'), '--verify-tar', str(tar), '--manifest', str(self.manifest)])
        return code, err.getvalue()

    def test_faithful_tar_exits_0_and_marks_every_row_yes(self):
        """happy: every manifest row is a member with equal bytes and sha256; tar-verify.tsv lands beside the manifest; nothing is extracted"""
        tar = self.tar(self.FILES)
        before = {p.name for p in self.d.rglob('*')}
        code, _ = self.run_verify(tar)
        self.assertEqual(code, 0)
        rows = tsv(self.d / 'tar-verify.tsv')
        self.assertEqual({r['path'] for r in rows}, set(self.FILES))
        self.assertTrue(all((r['in_tar'], r['bytes_equal'], r['sha256_equal']) == ('yes', 'yes', 'yes') for r in rows))
        self.assertEqual({p.name for p in self.d.rglob('*')} - before, {'tar-verify.tsv'})

    def test_missing_member_and_changed_byte_exit_1_naming_the_path(self):
        """error: a member absent from the tar, and a member with one changed byte of the same length, each exit 1 and name the path"""
        code, err = self.run_verify(self.tar({'docs/plan/p/plan.yaml': self.FILES['docs/plan/p/plan.yaml']}))
        self.assertEqual(code, 1)
        self.assertIn('docs/a.md', err)
        self.assertEqual({r['path']: r['in_tar'] for r in tsv(self.d / 'tar-verify.tsv')}['docs/a.md'], 'no')
        code, err = self.run_verify(self.tar(dict(self.FILES, **{'docs/a.md': b'alphX\n'})))
        self.assertEqual(code, 1)
        self.assertIn('docs/a.md', err)
        row = {r['path']: r for r in tsv(self.d / 'tar-verify.tsv')}['docs/a.md']
        self.assertEqual((row['bytes_equal'], row['sha256_equal']), ('yes', 'no'))

    def test_member_under_docs_archives_exits_1_before_any_content_is_opened(self):
        """security, U9: a member named under docs/archives/ exits 1 naming it and writes no tar-verify.tsv"""
        code, err = self.run_verify(self.tar(dict(self.FILES, **{'docs/archives/x': b'secret\n'})))
        self.assertEqual(code, 1)
        self.assertIn('docs/archives/x', err)
        self.assertFalse((self.d / 'tar-verify.tsv').exists())


@unittest.skipUnless(os.name == 'nt', 'Windows-only: docs-migrate --delete refusal')
class WindowsDeleteRefusalTests(unittest.TestCase):
    def test_delete_is_refused_on_windows_and_nothing_is_read_or_removed(self):
        """TC-W-2: --delete on Windows exits 1 with exactly the refusal line on stderr and nothing on stdout; every workspace file keeps its sha256 and mtime_ns, the approved list is byte-identical, and --out is never created"""
        tmp = tempfile.TemporaryDirectory(prefix='docs-migrate-win-')
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name).resolve()
        ws, out, approved = base / 'ws', base / 'out', base / 'approved.tsv'
        base_tree(ws)
        prune_tree(ws)
        approved.write_text('category\tpath\tfiles\tbytes\nprune\tdocs/plan/alpha/amend-1.md\t1\t2\n', encoding='utf-8')   # never parsed: the guard runs first
        before, listed = snapshot(ws), approved.read_bytes()
        err, std = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(std):
            code = DM.main(['--workspace', str(ws), '--out', str(out), '--delete', str(approved), '--profile', 'prune'])
        self.assertEqual(code, 1)
        self.assertEqual(err.getvalue(), 'docs-migrate: lsof-based open-file check unavailable on Windows; nothing was removed\n')
        self.assertEqual(std.getvalue(), '')
        self.assertEqual(snapshot(ws), before)
        self.assertEqual(approved.read_bytes(), listed)
        self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
