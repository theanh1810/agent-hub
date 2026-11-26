"""Per-spawn state for agent-hub hooks: one JSON file per (session, agent) in a private directory. Stdlib only.

Every function raises on trouble (OSError, ValueError); the calling hook wraps its whole body and exits 0,
so a fault here never blocks or changes a tool call.
"""
import json
import os
import re
import stat
import tempfile
import time

import _common

DIR_NAME = "agent-hub-moments"
SAFE_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")
MAIN_AGENT = "main"
STALE_AGE_S = 7 * 24 * 3600
PRUNE_ONE_CALL_IN = 50


def switched_off():
    """True when the user turned the moment hooks off: AGENT_HUB_MOMENTS=0, or plugin option moment_hooks=off."""
    return os.environ.get("AGENT_HUB_MOMENTS", "").strip() == "0" or (_common.option_env("moment_hooks", "on") or "").lower() == "off"


def blocks_off():
    """True when the user turned blocking off (AGENT_HUB_BLOCKS=0, or plugin option hook_blocks=off): a blocking point then only notes."""
    return os.environ.get("AGENT_HUB_BLOCKS", "").strip() == "0" or (_common.option_env("hook_blocks", "on") or "").lower() == "off"


def spawn_ids(payload):
    """(session id, agent id) of a hook payload; the main thread's agent id is `main`. ValueError when unusable."""
    session, agent = payload.get("session_id"), payload.get("agent_id", MAIN_AGENT)
    if not isinstance(session, str) or not isinstance(agent, str) or not SAFE_ID.fullmatch(session) or not SAFE_ID.fullmatch(agent):
        raise ValueError("no usable session or agent id")
    return session, agent


def agent_role(payload):
    """`implement` for agent_type `agent-hub:implement`; `main` for the main thread; '' for another plugin's agent."""
    kind = payload.get("agent_type")
    if "agent_id" not in payload and not kind:
        return MAIN_AGENT
    return kind.split(":", 1)[1] if isinstance(kind, str) and kind.startswith("agent-hub:") else ""


def state_dir():
    """The private state directory, created 0700. A directory another user owns or can write to is refused."""
    path = os.path.join(os.environ.get("AGENT_HUB_STATE_DIR") or tempfile.gettempdir(), DIR_NAME)
    os.makedirs(path, mode=0o700, exist_ok=True)
    info = os.lstat(path)
    if not stat.S_ISDIR(info.st_mode):
        raise OSError("state path is not a directory")
    if hasattr(os, "getuid") and (info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise OSError("state directory is not private")
    return path


def state_file(payload):
    session, agent = spawn_ids(payload)
    return os.path.join(state_dir(), "%s.%s.json" % (session, agent))


def load(path):
    """The spawn's state; an absent, corrupt or foreign-shaped file reads as empty."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save(path, state):
    """Replace the state file in one rename, so a reader never sees a partial write."""
    temp = "%s.%d.tmp" % (path, os.getpid())
    try:
        with os.fdopen(os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600), "w", encoding="utf-8") as handle:
            json.dump(state, handle, separators=(",", ":"))
        os.replace(temp, path)
    except OSError:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise


def claim_path(payload, name):
    """The marker file of claim `name` in this spawn. ValueError for an unusable id or name."""
    session, agent = spawn_ids(payload)
    if not SAFE_ID.fullmatch(name):
        raise ValueError("no usable claim name")
    return os.path.join(state_dir(), "%s.%s.%s" % (session, agent, name))


def claim(payload, name):
    """True for exactly one caller, ever, per (spawn, name): the winner of an O_EXCL create. Safe across concurrent processes."""
    path = claim_path(payload, name)
    try:
        os.close(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600))
    except FileExistsError:
        return False
    return True


def claimed(payload, name):
    """True once claim(payload, name) has been won in this spawn. Reads only: it never makes the marker."""
    return os.path.lexists(claim_path(payload, name))


def claim_once(payload, key):
    """True the first time `key` is asked about in this spawn, for one process only."""
    return claim(payload, "once-" + key)


# Callers arrive with hooks/moment.py and hooks/return_check.py.
def take_block(payload, point, limit=2):
    """True while `point` has blocked fewer than `limit` times in this spawn; each block claims one numbered slot, so
    concurrent processes never grant more than `limit`."""
    return any(claim(payload, "block-%s-%d" % (point, slot)) for slot in range(limit))


def prune_sometimes(path=None):
    """One call in PRUNE_ONE_CALL_IN deletes state files untouched for STALE_AGE_S."""
    if int.from_bytes(os.urandom(2), "big") % PRUNE_ONE_CALL_IN:
        return
    now = time.time()
    with os.scandir(path or state_dir()) as entries:
        for entry in entries:
            try:
                if entry.is_file(follow_symlinks=False) and now - entry.stat(follow_symlinks=False).st_mtime > STALE_AGE_S:
                    os.unlink(entry.path)
            except OSError:
                continue
