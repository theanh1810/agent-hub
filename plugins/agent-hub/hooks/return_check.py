#!/usr/bin/env python3
"""return_check.py (SubagentStop, agent-hub agents): refuse a final message that is not in the return shape.

Checks `last_assistant_message` with scripts/return-check.py. On a problem it exits 2 with one stderr line per
problem, which keeps the subagent running to fix its message. It does so at most `limits.max_blocks` times per spawn
(hooks/moments.json, the cap hooks/moment.py also reads): each
refusal claims a slot marker (hooks/_state.py take_block, one O_EXCL create each), so concurrent stop hooks of one
spawn can never be granted more. `stop_hook_active` claims the first slot, so a re-entry with no recorded refusal
counts as one. After that, or with AGENT_HUB_BLOCKS=0 / plugin option hook_blocks=off, the message goes through
and the hook says so once (systemMessage and additionalContext), so the unfixed problems are visible outside the
subagent. AGENT_HUB_MOMENTS=0 or plugin option moment_hooks=off turns the hook off.

A run that ended in a SubagentHandback tool call (the last assistant entry of `agent_transcript_path`) has already handed its
report over: the call's `message` is checked in place of `last_assistant_message`, and problems are only noted, never refused,
because a refusal after a handback is untested. An empty final message with no handback is let through silently.

Exit codes: 0 conforming, let through, off, or any failure of this hook (it fails open) · 2 refused, problems on stderr.
"""
import importlib.util
import json
import os
import sys

if sys.version_info < (3, 11):  # the doctor hook reports it; stay silent here
    sys.exit(0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common  # noqa: E402
import _state  # noqa: E402

POINT = "return"
HANDBACK = "SubagentHandback"


def max_blocks():
    """`limits.max_blocks` of hooks/moments.json: one cap for every blocking point (hooks/moment.py reads the same key)."""
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "moments.json"), encoding="utf-8") as handle:
        return int((json.load(handle).get("limits") or {}).get("max_blocks", 2))


def load_checker():
    spec = importlib.util.spec_from_file_location("return_check_script", _common.plugin_root() / "scripts" / "return-check.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def handback_message(path):
    """(True, the call's `message`) when the last assistant entry with text or a tool call in the transcript tail is a
    SubagentHandback call; (False, None) otherwise or when the tail cannot be read."""
    try:
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            handle.seek(max(0, handle.tell() - 262144))
            tail = handle.read().decode("utf-8", "replace")
    except (OSError, TypeError):
        return False, None
    handed, message = False, None
    for line in tail.splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        body = entry.get("message") if isinstance(entry, dict) and entry.get("type") == "assistant" else None
        content = body.get("content") if isinstance(body, dict) else None
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name") == HANDBACK:
                handed, message = True, (block.get("input") or {}).get("message")
            elif block.get("type") == "tool_use" or (block.get("type") == "text" and str(block.get("text") or "").strip()):
                handed, message = False, None
    return handed, message


def main():
    payload = _common.read_stdin_json()
    if _state.switched_off():
        return 0
    role = _state.agent_role(payload)
    text = payload.get("last_assistant_message")
    transcript = payload.get("agent_transcript_path")
    handed, message = handback_message(transcript)
    if handed and isinstance(message, str) and message.strip():
        text = message
    checker = load_checker()
    if role not in checker.ROLES or not isinstance(text, str) or not text.strip():
        return 0
    found = checker.problems(text, role, payload.get("cwd"), checker.transcript_facts(transcript), str(_common.plugin_root()))
    if not found:
        return 0
    if not handed and payload.get("stop_hook_active"):   # a re-entry: if no refusal of ours made slot 0 (state lost, another hook blocked), it counts as spent
        _state.claim(payload, "block-%s-0" % POINT)
    if not handed and not _state.blocks_off() and _state.take_block(payload, POINT, max_blocks()):
        sys.stderr.write("agent-hub return-check: your final message is not in the return shape of `rules/core.md § Handoff contract`. "
                         "Fix exactly these and send the whole message again:\n" + "".join("- %s\n" % line for line in found))
        return 2
    if _state.claim_once(payload, "warned-" + POINT):
        note = "agent-hub return-check: the %s agent returned with %d unfixed problems: %s" % (role, len(found), "; ".join(found))
        _common.emit("SubagentStop", note[:2000], note[:2000])
    return 0


if __name__ == "__main__":
    _common.utf8_stdio()
    try:
        code = main()
    except Exception:
        code = 0  # fail open: a fault here must never trap a subagent
    sys.exit(code)
