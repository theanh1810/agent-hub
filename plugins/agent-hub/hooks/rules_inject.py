#!/usr/bin/env python3
"""rules_inject.py <event> <n> [--lang CODE]: print chunk n of rules/core.md: the main view on SessionStart, the subagent view on SubagentStart."""
import sys

if sys.version_info < (3, 11):  # the doctor hook reports it; stay silent here
    sys.exit(0)

import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common  # noqa: E402

MAX_CHARS = 9500  # under the 10,000-character additionalContext cap per chunk
MAX_CHUNKS = {"SessionStart": 2, "SubagentStart": 1}
VIEW_OF = {"SessionStart": "main", "SubagentStart": "subagent"}

DIRECT_DIRECTIVE = """SESSION DIRECTIVE - DIRECT MODE: started with AGENT_HUB_DIRECT=1. Standing instruction: work directly, no agents (the routing override). Do not spawn fleet agents, do not use the Workflow tool. Safety, the reply language and validation rules still apply."""

FENCE_LINE = re.compile(r"(?ms)^<!-- main-only:begin -->\n.*?^<!-- main-only:end -->\n")
FENCE_INLINE = re.compile(r"(?s)<!-- main-only:begin -->.*?<!-- main-only:end -->")
MARK_LINE = re.compile(r"(?m)^<!-- main-only:(?:begin|end) -->\n")
MARK_INLINE = re.compile(r"<!-- main-only:(?:begin|end) -->")


def view_text(text, view):
    """The main view keeps every row and drops the fence markers; the subagent view also drops each main-only block."""
    if view == "subagent":
        text = FENCE_INLINE.sub("", FENCE_LINE.sub("", text))
    return MARK_INLINE.sub("", MARK_LINE.sub("", text)) if view == "main" else re.sub(r"\n{3,}", "\n\n", text)


def split_sections(text):
    """Split at lines starting with '# ' or '## '; text before the first heading is its own section."""
    return [p for p in re.split(r"(?m)^(?=#{1,2} )", text) if p]


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


def render(core_text, root, lang, view):
    """The core as one string for a view ('main' or 'subagent'), placeholders filled."""
    return view_text(fill(core_text, root, lang), view)


def build_chunks(core_text, root, lang, view="main"):
    """Chunks of a view. Chunk 1 reserves room for the direct directive so every start shares boundaries."""
    reserve = len(DIRECT_DIRECTIVE) + 2
    return pack(split_sections(render(core_text, root, lang, view)), MAX_CHARS - reserve, MAX_CHARS)


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
    root = _common.plugin_root()
    try:
        core = (root / "rules" / "core.md").read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write("rules_inject: cannot read core.md: %s\n" % exc)
        return 0
    chunks = build_chunks(core, root.as_posix(), _common.reply_language(lang_arg), VIEW_OF[event])
    if n > len(chunks):
        return 0
    body = chunks[n - 1]
    if event == "SessionStart" and n == 1:
        direct = os.environ.get("AGENT_HUB_DIRECT") == "1"
        body = (DIRECT_DIRECTIVE + "\n\n" + body) if direct else body
    limit = MAX_CHUNKS[event]
    msg = "agent-hub: rules exceed %d hook chunks; some rules were not loaded" % limit if n == 1 and len(chunks) > limit else None
    _common.emit(event, body, msg)
    return 0


if __name__ == "__main__":
    _common.utf8_stdio()
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as exc:  # never a blocking exit
        sys.stderr.write("rules_inject: %s: %s\n" % (type(exc).__name__, exc))
        sys.exit(0)
