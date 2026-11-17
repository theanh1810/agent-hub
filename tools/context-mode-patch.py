#!/usr/bin/env python3
"""Local patch for the installed context-mode 2.1.10: apply | check | revert.

Adds an agent-hub passthrough guard to hook.mjs (gitnexus tools and every
subagent call skip the replace / deny / run.mjs-rewrite paths) and pins the
node binary in the two manifests that start node (hooks/claude-code.json and
.claude-plugin/plugin.json). It copies no context-mode code: it only inserts
short guard strings at recorded anchors and refuses on any hash drift.

Exit codes: 0 ok, 1 check failed or runtime error, 2 refused (version, hash or
unknown state; nothing was written). Apply refuses and check fails when the pinned node
is missing or not executable; revert refuses unless every target is patched and every
backup is the recorded original.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile

VERSION = "2.1.10"
NODE_PIN = "/opt/homebrew/opt/node@24/bin/node"
MARKER = "/* agent-hub-local-patch v1 */"
DEFAULT_PACKAGE = "/opt/homebrew/lib/node_modules/context-mode"
BACKUP_ROOT = os.path.expanduser("~/.claude-vendor/context-mode-patch")

HOOK = "hook.mjs"
HOOKS_JSON = "hooks/claude-code.json"
PLUGIN_JSON = ".claude-plugin/plugin.json"
PACKAGE_JSON = "package.json"
TARGETS = (HOOK, HOOKS_JSON, PLUGIN_JSON)

# Recorded in evidence/context-mode.yaml; plugin.json has no recorded hash
# (its state is structural: version plus a bare or pinned command).
HOOK_SHA256 = "c6fc2d936e2c73b8c5abc2e3718218dd1b0ea7542c5e7922b21a09da02bec888"
HOOKS_JSON_SHA256 = "676dd9cddc3bb4dbf163296cdd72aac521010fdf33ab80bd2641f647ae475dc1"

GITNEXUS = 'String({tool}.name??"").startsWith("mcp__gitnexus__")'
# id -> (anchor, guard inserted right after the function's opening brace).
# Pe(e) is hook.mjs's own "agentId is a non-empty string" test (evidence
# subagent_fields); y is its allow/passthrough result.
GUARDS = {
    "a_post_tool_replace_decision": (
        'async function bE(e,t,n,o,r,s,i){if(s.bytes<=Ur||TE(r)||SE(e,r,o)||s.keep===!0||!Ae(t))return y;',
        "if(" + GITNEXUS.format(tool="r") + "||Pe(e))return y;",
    ),
    "b1_subagent_pretool_deny_branch": (
        'async function pE(e,t,n,o){let r=va(n.worktree,e.agent),s=fl(e,t,r,n),i=s;if(s.kind==="deny"&&Pe(e)&&!ku(s.reason,t)){',
        "if(Pe(e)||(e.tool!==void 0&&" + GITNEXUS.format(tool="e.tool") + "))return y;",
    ),
    "b2_subagent_run_mjs_rewrite": (
        'function _E(e,t,n,o){let r=e.tool;if(r===void 0||!kr(r,t)||ku(n.reason,t))return n;let s=r.input.command;',
        "if(Pe(e))return n;",
    ),
}


class Refused(Exception):
    """Exit 2: nothing may be written."""


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read(pkg, rel):
    with open(os.path.join(pkg, rel), "rb") as f:
        return f.read()


def guarded_text(text):
    """Return text with the three guards inserted; raise Refused on a bad anchor."""
    for gid, (anchor, guard) in GUARDS.items():
        if text.count(anchor) != 1:
            raise Refused("anchor %s found %d times, expected 1" % (gid, text.count(anchor)))
        cut = anchor.index("){") + 2
        text = text.replace(anchor, anchor[:cut] + guard + anchor[cut:])
    return text + "\n" + MARKER + "\n"


def hook_state(data):
    if sha256(data) == HOOK_SHA256:
        return "original"
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return "unknown"
    if MARKER in text and all(g in text for _, g in GUARDS.values()):
        return "patched"
    return "unknown"


def commands(node):
    """Yield (parent, key) of every string 'command' entry in a parsed manifest."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "command" and isinstance(v, str):
                yield node, k
            else:
                yield from commands(v)
    elif isinstance(node, list):
        for v in node:
            yield from commands(v)


def pinned(cmd):
    return cmd == NODE_PIN or cmd.startswith(NODE_PIN + " ")


def bare(cmd):
    return cmd == "node" or cmd.startswith("node ")


def manifest_state(rel, data):
    try:
        doc = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return "unknown"
    if rel == HOOKS_JSON:
        cmds = [p[k] for p, k in commands(doc.get("hooks", {}))]
        if not cmds:
            return "unknown"
        if all(pinned(c) for c in cmds):
            return "patched"
        if sha256(data) == HOOKS_JSON_SHA256 and all(bare(c) for c in cmds):
            return "original"
        return "unknown"
    cmd = (doc.get("mcpServers", {}).get("context-mode", {}) or {}).get("command")
    if not isinstance(cmd, str):
        return "unknown"
    if pinned(cmd):
        return "patched"
    return "original" if bare(cmd) else "unknown"


def pin_text(data):
    """Pin the command strings by text edit so formatting stays byte-identical."""
    text = data.decode("utf-8")
    text, n = re.subn(r'("command"\s*:\s*")node(?=[ "])', lambda m: m.group(1) + NODE_PIN, text)
    if n == 0:
        raise Refused("no bare node command to pin")
    json.loads(text)
    return text.encode("utf-8")


def state_of(rel, data):
    return hook_state(data) if rel == HOOK else manifest_state(rel, data)


def package_version(pkg):
    try:
        return json.loads(read(pkg, PACKAGE_JSON).decode("utf-8")).get("version")
    except (OSError, ValueError):
        return None


def backup_dir(pkg, backup_root):
    real = os.path.realpath(pkg)
    if real == os.path.realpath(DEFAULT_PACKAGE):
        return os.path.join(backup_root, VERSION)
    return os.path.join(backup_root, "%s-%s" % (VERSION, sha256(real.encode("utf-8"))[:8]))


def atomic_write(path, data):
    mode = os.stat(path).st_mode & 0o7777
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".ahp-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def survey(pkg):
    """Refuse unless the version is right and every target is original or patched."""
    version = package_version(pkg)
    if version != VERSION:
        raise Refused("package.json version %r, expected %s" % (version, VERSION))
    states = {}
    for rel in TARGETS:
        try:
            data = read(pkg, rel)
        except OSError as e:
            raise Refused("cannot read %s: %s" % (rel, e))
        states[rel] = (state_of(rel, data), data)
        if states[rel][0] == "unknown":
            raise Refused("%s is neither the recorded original nor patched" % rel)
    return states


def require_node_pin():
    if not (os.path.isfile(NODE_PIN) and os.access(NODE_PIN, os.X_OK)):
        raise Refused("node pin %s is missing or not executable" % NODE_PIN)


def do_apply(pkg, backup_root):
    require_node_pin()
    states = survey(pkg)
    todo = {}
    for rel in TARGETS:
        state, data = states[rel]
        if state == "original":
            todo[rel] = guarded_text(data.decode("utf-8")).encode("utf-8") if rel == HOOK else pin_text(data)
    if not todo:
        print("already patched: nothing to do")
        return 0
    bdir = backup_dir(pkg, backup_root)
    for rel in todo:
        dest = os.path.join(bdir, rel)
        if not os.path.exists(dest):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(os.path.join(pkg, rel), dest)
    for rel in (HOOK, HOOKS_JSON, PLUGIN_JSON):  # hook.mjs first, manifests last
        if rel in todo:
            atomic_write(os.path.join(pkg, rel), todo[rel])
            print("patched " + rel)
    return 0


def do_check(pkg):
    errors = []
    if not (os.path.isfile(NODE_PIN) and os.access(NODE_PIN, os.X_OK)):
        errors.append("node pin %s is missing or not executable" % NODE_PIN)
    version = package_version(pkg)
    if version != VERSION:
        errors.append("package.json version %r, expected %s" % (version, VERSION))
    for rel in TARGETS:
        try:
            state = state_of(rel, read(pkg, rel))
        except OSError as e:
            errors.append("cannot read %s: %s" % (rel, e))
            continue
        if state != "patched":
            errors.append("%s is %s, expected patched" % (rel, state))
    for e in errors:
        print("check: " + e, file=sys.stderr)
    if not errors:
        print("check ok: guards present, node pinned to " + NODE_PIN)
    return 1 if errors else 0


def do_revert(pkg, backup_root):
    states = survey(pkg)
    unpatched = [rel for rel in TARGETS if states[rel][0] != "patched"]
    if unpatched:
        raise Refused("not patched, nothing to revert: " + ", ".join(unpatched))
    bdir = backup_dir(pkg, backup_root)
    missing = [rel for rel in TARGETS if not os.path.isfile(os.path.join(bdir, rel))]
    if missing:
        raise Refused("no backup in %s for %s" % (bdir, ", ".join(missing)))
    backups = {}
    for rel in TARGETS:
        with open(os.path.join(bdir, rel), "rb") as f:
            backups[rel] = f.read()
        if state_of(rel, backups[rel]) != "original":
            raise Refused("backup of %s is not the recorded original" % rel)
    for rel in TARGETS:
        atomic_write(os.path.join(pkg, rel), backups[rel])
        print("restored " + rel)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=("apply", "check", "revert"))
    ap.add_argument("--package", default=DEFAULT_PACKAGE, help="context-mode package directory")
    ap.add_argument("--backup-root", default=BACKUP_ROOT, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    try:
        if args.command == "apply":
            return do_apply(args.package, args.backup_root)
        if args.command == "check":
            return do_check(args.package)
        return do_revert(args.package, args.backup_root)
    except Refused as e:
        print("refused: %s" % e, file=sys.stderr)
        return 2
    except OSError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
