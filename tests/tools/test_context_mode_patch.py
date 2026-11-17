"""Tests for tools/context-mode-patch.py: every case runs on a temp copy, never on the installed package."""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REAL_PACKAGE = Path("/opt/homebrew/lib/node_modules/context-mode")
NODE = shutil.which("node")


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, REPO / "tools" / file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


patch = load("context_mode_patch", "context-mode-patch.py")
package = load("package_tool_cmp", "package.py")

# A synthetic hook.mjs: the real anchors, with stubs for the symbols they use.
FIXTURE_HOOK = (
    'const Ur=4096,y={kind:"allow"};'
    "function Pe(e){return e.agentId!==void 0&&e.agentId!==\"\"}"
    "function TE(e){return false}function SE(e,t,n){return false}function Ae(e){return true}"
    "function va(){return 1}function fl(e){return {kind:\"deny\",reason:\"plain\"}}"
    "function ku(e,t){return false}function Wo(){return null}function Cu(){return null}"
    "function Bo(){return \"B\"}function kr(e,t){return true}\n"
    + patch.GUARDS["a_post_tool_replace_decision"][0]
    + 'return {kind:"replace",output:"REPLACED"}}'
    + patch.GUARDS["b1_subagent_pretool_deny_branch"][0]
    + "i=_E(e,t,s,r)}return i}"
    + patch.GUARDS["b2_subagent_run_mjs_rewrite"][0]
    + 'return {kind:"deny",rewritten:s}}\n'
    + "export {bE,pE,_E};\n"
)
FIXTURE_HOOKS_JSON = (
    '{\n  "hooks": {\n    "PostToolUse": [{"hooks": [{"command": "node \\"${CLAUDE_PLUGIN_ROOT}/hook.mjs\\" --agent claude-code", "type": "command"}]}],\n'
    '    "SessionStart": [{"hooks": [{"command": "node \\"${CLAUDE_PLUGIN_ROOT}/hook.mjs\\" --agent claude-code", "type": "command"}]}]\n  }\n}\n'
)
FIXTURE_PLUGIN_JSON = (
    '{\n  "hooks": "./hooks/claude-code.json",\n  "mcpServers": {\n    "context-mode": {\n'
    '      "args": ["${CLAUDE_PLUGIN_ROOT}/server.mjs", "--agent", "claude-code"],\n      "command": "node"\n    }\n  },\n'
    '  "name": "context-mode",\n  "version": "2.1.10"\n}\n'
)
FIXTURE_PACKAGE_JSON = '{"name": "context-mode", "version": "2.1.10"}\n'


def run(*argv):
    """Run main() in-process; return (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = patch.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def snapshot(pkg):
    return {p.relative_to(pkg).as_posix(): p.read_bytes() for p in Path(pkg).rglob("*") if p.is_file()}


class FixtureCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="w2t16-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.pkg = self.tmp / "pkg"
        self.backups = str(self.tmp / "backups")
        self.write("hook.mjs", FIXTURE_HOOK)
        self.write("hooks/claude-code.json", FIXTURE_HOOKS_JSON)
        self.write(".claude-plugin/plugin.json", FIXTURE_PLUGIN_JSON)
        self.write("package.json", FIXTURE_PACKAGE_JSON)
        fake_node = self.tmp / "node"
        fake_node.write_text("#!/bin/sh\n")
        os.chmod(fake_node, 0o755)
        saved_pin = patch.NODE_PIN
        patch.NODE_PIN = str(fake_node)
        self.addCleanup(setattr, patch, "NODE_PIN", saved_pin)
        saved = (patch.HOOK_SHA256, patch.HOOKS_JSON_SHA256)
        patch.HOOK_SHA256 = patch.sha256(FIXTURE_HOOK.encode())
        patch.HOOKS_JSON_SHA256 = patch.sha256(FIXTURE_HOOKS_JSON.encode())
        self.addCleanup(lambda: (setattr(patch, "HOOK_SHA256", saved[0]), setattr(patch, "HOOKS_JSON_SHA256", saved[1])))

    def write(self, rel, text):
        p = self.pkg / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def cmd(self, name, pkg=None):
        return run(name, "--package", str(pkg or self.pkg), "--backup-root", self.backups)


class ApplyCheckTest(FixtureCase):
    def test_apply_then_check_then_reapply_is_stable(self):  # AC-1
        self.assertEqual(self.cmd("check")[0], 1)
        self.assertEqual(self.cmd("apply")[0], 0)
        self.assertEqual(self.cmd("check")[0], 0)
        before = snapshot(self.pkg)
        self.assertEqual(self.cmd("apply")[0], 0)
        self.assertEqual(snapshot(self.pkg), before)
        hooks = json.loads((self.pkg / "hooks/claude-code.json").read_text())
        for ev in hooks["hooks"].values():
            for entry in ev:
                for h in entry["hooks"]:
                    self.assertTrue(h["command"].startswith(patch.NODE_PIN + " "))
        plugin = json.loads((self.pkg / ".claude-plugin/plugin.json").read_text())
        self.assertEqual(plugin["mcpServers"]["context-mode"]["command"], patch.NODE_PIN)
        self.assertEqual(plugin["mcpServers"]["context-mode"]["args"][0], "${CLAUDE_PLUGIN_ROOT}/server.mjs")

    def test_check_fails_when_a_pin_is_removed(self):  # AC-1, DC-36
        self.cmd("apply")
        for rel, old, new in (
            ("hooks/claude-code.json", patch.NODE_PIN, "node"),
            (".claude-plugin/plugin.json", patch.NODE_PIN, "node"),
        ):
            p = self.pkg / rel
            good = p.read_text()
            p.write_text(good.replace(old, new))
            code, _, err = self.cmd("check")
            self.assertNotEqual(code, 0, rel)
            self.assertIn(rel, err)
            p.write_text(good)
        self.assertEqual(self.cmd("check")[0], 0)

    def test_half_patched_package_is_finished_by_one_apply(self):  # AC-1, R8-6
        self.cmd("apply")
        for rel, old in (("hooks/claude-code.json", patch.NODE_PIN), (".claude-plugin/plugin.json", patch.NODE_PIN)):
            p = self.pkg / rel
            p.write_text(p.read_text().replace(old, "node"))
        self.write("hooks/claude-code.json", FIXTURE_HOOKS_JSON)
        self.assertNotEqual(self.cmd("check")[0], 0)
        self.assertEqual(self.cmd("apply")[0], 0)
        self.assertEqual(self.cmd("check")[0], 0)

    def test_package_dir_copy_keeps_its_own_backups(self):  # AC-1, R8-1
        other = self.tmp / "plugin-copy"
        shutil.copytree(self.pkg, other)
        self.assertEqual(self.cmd("apply", other)[0], 0)
        self.assertEqual(self.cmd("check", other)[0], 0)
        self.assertNotEqual(self.cmd("check")[0], 0)
        dirs = os.listdir(self.backups)
        self.assertEqual(len(dirs), 1)
        self.assertRegex(dirs[0], r"^2\.1\.10-[0-9a-f]{8}$")

    def test_hook_diff_is_only_the_guards_and_marker(self):
        self.cmd("apply")
        text = (self.pkg / "hook.mjs").read_text()
        self.assertEqual(text.count(patch.MARKER), 1)
        for _, guard in patch.GUARDS.values():
            self.assertEqual(text.count(guard), 1)


class RefuseTest(FixtureCase):
    def assert_refused_untouched(self):
        before = snapshot(self.pkg)
        self.assertEqual(self.cmd("apply")[0], 2)
        self.assertEqual(snapshot(self.pkg), before)
        self.assertFalse(os.path.exists(self.backups))

    def test_other_version(self):  # AC-2
        self.write("package.json", '{"version": "2.1.11"}\n')
        self.assert_refused_untouched()

    def test_other_hook_hash(self):  # AC-2
        self.write("hook.mjs", FIXTURE_HOOK + "// drift\n")
        self.assert_refused_untouched()

    def test_manifest_neither_original_nor_patched_writes_nothing(self):  # AC-2, R8-6
        self.write("hooks/claude-code.json", FIXTURE_HOOKS_JSON.replace("node \\\"", "/usr/bin/node \\\"", 1))
        self.assert_refused_untouched()

    def test_plugin_json_unknown_command(self):  # AC-2
        self.write(".claude-plugin/plugin.json", FIXTURE_PLUGIN_JSON.replace('"command": "node"', '"command": "bun"'))
        self.assert_refused_untouched()

    def test_anchor_missing_in_matching_hash(self):  # AC-2
        broken = FIXTURE_HOOK.replace("function _E(", "function _X(")
        self.write("hook.mjs", broken)
        patch.HOOK_SHA256 = patch.sha256(broken.encode())
        self.assert_refused_untouched()


class RevertTest(FixtureCase):
    def test_revert_restores_bytes(self):  # AC-3
        before = snapshot(self.pkg)
        self.cmd("apply")
        self.assertNotEqual(snapshot(self.pkg), before)
        self.assertEqual(self.cmd("revert")[0], 0)
        self.assertEqual(snapshot(self.pkg), before)

    def test_revert_without_backup_is_refused(self):
        self.assertEqual(self.cmd("revert")[0], 2)

    def test_revert_on_other_version_is_refused(self):
        self.cmd("apply")
        self.write("package.json", '{"name": "context-mode", "version": "2.1.11"}\n')
        before = snapshot(self.pkg)
        self.assertEqual(self.cmd("revert")[0], 2)
        self.assertEqual(snapshot(self.pkg), before)

    def test_revert_on_unpatched_target_is_refused(self):
        original = snapshot(self.pkg)["hook.mjs"]
        self.cmd("apply")
        (self.pkg / "hook.mjs").write_bytes(original)
        before = snapshot(self.pkg)
        self.assertEqual(self.cmd("revert")[0], 2)
        self.assertEqual(snapshot(self.pkg), before)

    def test_revert_with_non_original_backup_is_refused(self):
        self.cmd("apply")
        bdir = patch.backup_dir(str(self.pkg), self.backups)
        with open(os.path.join(bdir, "hook.mjs"), "ab") as f:
            f.write(b"x")
        before = snapshot(self.pkg)
        self.assertEqual(self.cmd("revert")[0], 2)
        self.assertEqual(snapshot(self.pkg), before)

    def test_mode_is_kept(self):
        os.chmod(self.pkg / "hook.mjs", 0o755)
        self.cmd("apply")
        self.assertEqual(os.stat(self.pkg / "hook.mjs").st_mode & 0o777, 0o755)


@unittest.skipUnless(NODE, "node is needed to run the patched hook")
class NodePinTest(FixtureCase):
    def test_apply_refuses_when_node_pin_missing(self):
        patch.NODE_PIN = str(self.tmp / "no-such-node")
        before = snapshot(self.pkg)
        code, _, err = self.cmd("apply")
        self.assertEqual(code, 2)
        self.assertIn("no-such-node", err)
        self.assertEqual(snapshot(self.pkg), before)

    def test_check_fails_when_node_pin_not_executable(self):
        self.cmd("apply")
        os.chmod(self.tmp / "node", 0o644)
        code, _, err = self.cmd("check")
        self.assertEqual(code, 1)
        self.assertIn(str(self.tmp / "node"), err)


class DecisionTableTest(FixtureCase):
    """AC-4: run the patched fixture's own functions under node."""

    def decide(self, fn, event):
        driver = self.tmp / "drive.mjs"
        driver.write_text(
            'import * as m from "%s";\n' % (self.pkg / "hook.mjs").as_uri()
            + "const e=%s;\n" % json.dumps(event)
            + "const t={nativeTools:{shell:[]}};\n"
            + {
                "post": "const r=await m.bE(e,t,{},{},e.tool,{bytes:9000,keep:false},0);",
                "pre": "const r=await m.pE(e,t,{worktree:1},{});",
            }[fn]
            + "console.log(JSON.stringify(r));\n"
        )
        out = subprocess.run([NODE, str(driver)], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def event(self, tool="Bash", agent_id=None, agent_type=None):
        e = {"tool": {"name": tool, "canonicalName": tool, "input": {"command": "curl x"}}}
        if agent_id is not None:
            e["agentId"] = agent_id
        if agent_type is not None:
            e["agentType"] = agent_type
        return e

    def test_before_patch_everything_is_replaced(self):
        self.cmd("apply")
        self.cmd("revert")
        self.assertEqual(self.decide("post", self.event(agent_id="a1"))["kind"], "replace")

    def test_patched_table(self):
        self.cmd("apply")
        cases = [
            ("gitnexus call", self.event(tool="mcp__gitnexus__query"), "allow"),
            ("agent-hub agent", self.event(agent_id="a1", agent_type="agent-hub:scout"), "allow"),
            ("codex rescue", self.event(agent_id="a2", agent_type="codex:codex-rescue"), "allow"),
            ("builtin Explore", self.event(agent_id="a3", agent_type="Explore"), "allow"),
            ("agent_id without type", self.event(agent_id="a4"), "allow"),
            ("main thread", self.event(), "replace"),
            ("agent_type alone, no agent_id", self.event(agent_type="Explore"), "replace"),
            ("empty agent_id", self.event(agent_id=""), "replace"),
        ]
        for label, ev, kind in cases:
            self.assertEqual(self.decide("post", ev)["kind"], kind, label)

    def test_pretool_paths(self):
        self.cmd("apply")
        self.assertEqual(self.decide("pre", self.event(agent_id="a1", agent_type="Explore"))["kind"], "allow")
        self.assertEqual(self.decide("pre", self.event())["kind"], "deny")


@unittest.skipUnless(REAL_PACKAGE.is_dir(), "installed context-mode is needed")
class RealCopyTest(unittest.TestCase):
    """Read the installed package only to copy it; the copy is patched and reverted."""

    def test_recorded_hashes_on_a_copy(self):
        tmp = Path(tempfile.mkdtemp(prefix="w2t16-real-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        pkg = tmp / "pkg"
        for rel in patch.TARGETS + (patch.PACKAGE_JSON,):
            (pkg / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REAL_PACKAGE / rel, pkg / rel)
        before = snapshot(pkg)
        if patch.package_version(str(pkg)) != patch.VERSION or any(
            patch.state_of(rel, (pkg / rel).read_bytes()) != "original" for rel in patch.TARGETS
        ):
            self.skipTest("installed package is not the pristine 2.1.10 (already patched or upgraded)")
        backups = str(tmp / "backups")
        self.assertEqual(run("apply", "--package", str(pkg), "--backup-root", backups)[0], 0)
        self.assertEqual(run("check", "--package", str(pkg), "--backup-root", backups)[0], 0)
        self.assertEqual(run("revert", "--package", str(pkg), "--backup-root", backups)[0], 0)
        self.assertEqual(snapshot(pkg), before)


class ReleaseTreeTest(unittest.TestCase):
    def test_tools_dir_is_not_in_the_release(self):  # AC-5, R8-3
        base = tempfile.mkdtemp(prefix="w2t16-rel-")
        self.addCleanup(shutil.rmtree, base, True)
        out = os.path.join(base, "release")
        code, msg = package.build(repo=str(REPO), out=out, validate=False)
        self.assertEqual(code, 0, msg)
        paths = [os.path.relpath(os.path.join(d, x), out) for d, ds, fs in os.walk(out) for x in ds + fs]
        self.assertTrue(paths)
        self.assertEqual([p for p in paths if p == "tools" or p.startswith("tools/")], [])


if __name__ == "__main__":
    unittest.main()
