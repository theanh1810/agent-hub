#!/usr/bin/env python3
"""rules_inject.py <event> <n> [--lang CODE]: print chunk n of rules/core.md for SessionStart or SubagentStart."""
import sys

if sys.version_info < (3, 11):  # the doctor hook reports it; stay silent here
    sys.exit(0)

import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common  # noqa: E402

MAX_CHARS = 9500
MAX_CHUNKS = 3
OVERFLOW_MSG = "agent-hub: rules exceed 3 hook chunks; some rules were not loaded"

ROUTING_DIRECTIVE = """SESSION DIRECTIVE - AGENT ROUTING (rules sections 0 and 0.1)
Main thread routes; it never does the work, and it is the only spawner. It answers directly only when nothing outside the conversation is touched.
Single-role work goes straight to its owner: typo/rename/comment -> implement | codebase question -> brainstorm | server status, health checks or logs -> devops (simple step -> devops-low) | review finding handed in -> implement then reviewer | approved plan task -> the agent its task file names.
New multi-role work or a plan -> orchestrator, which emits next_spawns[]; main spawns in dependency order. Only the user's words ('skip orchestrator', 'do it directly', 'just do X') skip routing; a short prompt never does.
Models: orchestrator, designer, planner, implement, scout, test sonnet | brainstorm, reviewer opus | devops opus (devops-low sonnet only for simple steps).
Anything touching a server goes to devops: ssh/scp/rsync, deploy, rollback, restart, pm2, systemd, nginx, remote docker/kubectl, server logs, DNS, certificates, host env or secrets, migrations on a deployed database.
A subagent sees none of this conversation: every brief stands alone with goal, acceptance, file:line, plan/design refs, binding_scope, spec_required and the verbatim output of each dependency. Never write 'as discussed'.
Every agent opens with [<agent> · model: <model>] and closes with the six-part handoff."""

DIRECT_DIRECTIVE = """SESSION DIRECTIVE - DIRECT MODE: started with AGENT_HUB_DIRECT=1. Standing instruction: work directly, no agents (the section 0.1 override). Do not spawn orchestrator or fleet agents, do not use the Workflow tool. Safety, the reply language and validation rules still apply."""


def split_sections(text):
    """Split at lines starting with '# ' (top-level headings); text before the first heading is its own section."""
    return [p for p in re.split(r"(?m)^(?=# )", text) if p]


def pack(sections, first_budget=MAX_CHARS, budget=MAX_CHARS):
    """Greedy-pack sections in order; a section is never split. Chunk 1 has first_budget."""
    chunks, cur = [], ""
    for sec in sections:
        limit = first_budget if not chunks else budget
        if cur and len(cur) + len(sec) > limit:
            chunks.append(cur)
            cur = ""
        cur += sec
    if cur:
        chunks.append(cur)
    return chunks


def fill(text, root, lang):
    return text.replace("{{AGENT_HUB_ROOT}}", str(root).replace("\\", "/")).replace("{{REPLY_LANGUAGE}}", lang)


def build_chunks(core_text, root, lang):
    """Chunks after substitution. Chunk 1 reserves room for the longer directive so every event shares boundaries."""
    reserve = max(len(ROUTING_DIRECTIVE), len(DIRECT_DIRECTIVE)) + 2
    return pack(split_sections(fill(core_text, root, lang)), MAX_CHARS - reserve, MAX_CHARS)


def parse_args(argv):
    lang_arg, pos, i = None, [], 0
    while i < len(argv):
        if argv[i] == "--lang":
            lang_arg = argv[i + 1] if i + 1 < len(argv) else None
            i += 2
            continue
        pos.append(argv[i])
        i += 1
    event = pos[0] if pos else ""
    n = int(pos[1]) if len(pos) > 1 and pos[1].isdigit() else 0
    return event, n, lang_arg


def main(argv):
    event, n, lang_arg = parse_args(argv)
    data = _common.read_stdin_json()
    if event not in ("SessionStart", "SubagentStart") or n < 1:
        sys.stderr.write("rules_inject: usage: rules_inject.py <SessionStart|SubagentStart> <n>\n")
        return 0
    if event == "SubagentStart" and str(data.get("agent_type", "")) == "agent-hub:scout":
        return 0
    root = _common.plugin_root()
    try:
        core = (root / "rules" / "core.md").read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write("rules_inject: cannot read core.md: %s\n" % exc)
        return 0
    chunks = build_chunks(core, root.as_posix(), _common.reply_language(lang_arg))
    if n > len(chunks):
        return 0
    body = chunks[n - 1]
    if event == "SessionStart" and n == 1:
        direct = os.environ.get("AGENT_HUB_DIRECT") == "1"
        body = (DIRECT_DIRECTIVE if direct else ROUTING_DIRECTIVE) + "\n\n" + body
    msg = OVERFLOW_MSG if n == 1 and len(chunks) > MAX_CHUNKS else None
    _common.emit(event, body, msg)
    return 0


if __name__ == "__main__":
    _common.utf8_stdio()
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as exc:  # never a blocking exit
        sys.stderr.write("rules_inject: %s: %s\n" % (type(exc).__name__, exc))
        sys.exit(0)
