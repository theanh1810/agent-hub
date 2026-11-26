#!/usr/bin/env python3
"""cache_index.py <SubagentStart|PreToolUse>: put the research cache index in front of an agent before it searches.

SubagentStart: for agent-hub:scout and agent-hub:brainstorm, every spawn.
PreToolUse (web and docs tools): for every other caller, the main thread included, once per spawn.
Advisory only. Always exits 0: any failure, a missing cache directory or an empty index ends with no output.
"""
import importlib.util
import os
import sys

if sys.version_info < (3, 11):  # the doctor hook reports it; stay silent here
    sys.exit(0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

AT_START = ("scout", "brainstorm")   # these get the index when they start, before any call


def load_cache_module(_common):
    path = _common.plugin_root() / "scripts" / "research-cache.py"
    spec = importlib.util.spec_from_file_location("research_cache", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv):
    import _common  # inside the guarded call: a broken install must end in silence, not a traceback
    import _state
    _common.utf8_stdio()
    event = argv[0] if argv else ""
    payload = _common.read_stdin_json()
    if event not in ("SubagentStart", "PreToolUse") or _state.switched_off():
        return
    role = _state.agent_role(payload)
    if (event == "SubagentStart") != (role in AT_START):
        return
    cache = load_cache_module(_common)
    root = cache.cache_dir()
    if not cache.is_real_dir(root):
        return
    text = cache.serve_text(root, cache.today(), event == "SubagentStart" and role == "scout")
    if not text:
        return
    if event == "PreToolUse":
        if not _state.claim_once(payload, "research-cache"):
            return
        _state.prune_sometimes()
    _common.emit(event, text)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception:
        pass  # advisory: a fault here must leave the spawn or the tool call untouched
    sys.exit(0)
