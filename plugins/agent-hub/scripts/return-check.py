#!/usr/bin/env python3
"""return-check.py <file> [--agent <role>] [--cwd <dir>]: check a saved agent return against its shape (agent-hub return-check).

The shape is `rules/core.md § Handoff contract`: line 1 the header, six `##` sections in order, then one fenced
`json` block holding the agent's Output object; scout returns the header and the raw object. The status values
and the model word are read from `agents/<role>.md`, so that file stays the one statement of both.
hooks/return_check.py runs the same problems() on every agent-hub subagent's last message, with the model that
ran (read from the spawn's transcript).

A check that needs a file never blocks on a path it cannot find: a relative path is read under the payload cwd, a
subagent's shell resets to the session cwd while its work may sit in another repo, so a relative path that is not
there is unverifiable and passes; an absolute path is always checked.

Exit codes: 0 no problem · 1 problems (one per line, then a count line) · 2 usage error, unreadable file or an internal error.
"""
import json
import os
import re
import subprocess
import sys

ROLES = ("brainstorm", "designer", "devops", "implement", "reviewer", "scout", "test")
SECTIONS = ("## Understanding", "## Files", "## Changes / Plan", "## Validation", "## Risks", "## Next Step")
HANDOFF_KEYS = ("understanding", "files_touched_or_referenced", "changes_or_findings", "validation_done", "risks", "next_step")
HEADER = re.compile(r"\[([a-z-]+) · model: (haiku|sonnet|opus)\]")
JSON_OPEN = re.compile(r"(?i)```jsonc?[ \t]*\r?")   # the fence lines scripts/ledger-record.py reads
FENCE_CLOSE = re.compile(r"```[ \t]*\r?")
FAMILY = re.compile(r"haiku|sonnet|opus")
VERDICTS = ("pass", "needs_changes", "blocking")


def plugin_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def agent_facts(role, root=None):
    """(model word, [status values]) from agents/<role>.md; ('', []) when the file or the line is missing."""
    try:
        with open(os.path.join(root or plugin_root(), "agents", role + ".md"), encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return "", []
    model = re.search(r"(?m)^model:\s*(\w+)", text)
    output = text[text.find("\n# Output"):] if "\n# Output" in text else text
    status = re.search(r'"status":\s*"([a-z_|]+)"', output)
    return (model.group(1) if model else ""), (status.group(1).split("|") if status else [])


def transcript_facts(path):
    """The model word (haiku|sonnet|opus) of the last assistant message in the transcript tail; None for what cannot be read.
    Only `message.model` of a `type == "assistant"` entry counts, never a "model" a tool result happens to carry."""
    model = None
    try:
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            handle.seek(max(0, handle.tell() - 262144))
            tail = handle.read().decode("utf-8", "replace")
    except (OSError, TypeError):
        return None
    for line in tail.splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        message = entry.get("message") if isinstance(entry, dict) and entry.get("type") == "assistant" else None
        family = FAMILY.search(str(message.get("model") or "")) if isinstance(message, dict) else None
        if family:
            model = family.group(0)
    return model


def last_json_block(body):
    """Text of the last closed fenced json block of body, None when there is none; one linear pass (an unclosed fence costs nothing)."""
    lines, last, start = body.split("\n"), None, None
    for n, line in enumerate(lines):
        if start is None:
            start = n + 1 if JSON_OPEN.fullmatch(line) else None
        elif FENCE_CLOSE.fullmatch(line):
            last, start = "".join(text + "\n" for text in lines[start:n]), None
    return last


def secret_hits(paths):
    """First output line of secret-scan over paths when it reports a hit (exit 1), else ''; exit 2 (unreadable path, scan error) is no hit."""
    script = os.path.join(plugin_root(), "scripts", "secret-scan.py")
    try:
        res = subprocess.run([sys.executable, script, *paths], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return ""
    lines = (res.stdout or res.stderr).strip().splitlines()
    return (lines[0] if lines else "exit 1") if res.returncode == 1 else ""


def header_problems(line, role, model):
    found = HEADER.fullmatch(line.strip())
    want = "[%s · model: %s]" % (role, model or "<haiku|sonnet|opus>")
    if not found or found.group(1) != role or (model and found.group(2) != model):
        return ["line 1 must be exactly `%s`" % want]
    return []


def locate(path, cwd):
    """The path to check, or None when it cannot be checked: an absolute path as is, a relative one only where it exists under cwd."""
    if os.path.isabs(path):
        return path
    found = os.path.join(cwd, path) if cwd else ""
    return found if found and os.path.exists(found) else None


def review_path(named, cwd):
    """The regular file a `review_file` value names, or None when it cannot be checked. The value may carry a suffix
    (` ## Round 1`, `:12`, ` § Round 1`): when the whole path is not a file, retry up to the first space, `:` or `§`."""
    cited = named.split(" ## ")[0].strip()
    for candidate in (cited, re.split(r"[\s:§]", cited, maxsplit=1)[0]):
        path = locate(candidate, cwd) if candidate else None
        if path and os.path.isfile(path):
            return path
    return None


def run_folder(task_id, cwd):
    """The task's own `.cm-tmp/<task_id>` folder when its real path lies directly inside the real `<cwd>/.cm-tmp`, else None."""
    if not cwd or not isinstance(task_id, str) or not task_id or "/" in task_id or ".." in task_id:
        return None
    parent = os.path.join(os.path.realpath(cwd), ".cm-tmp")
    real = os.path.realpath(os.path.join(parent, task_id))
    return real if os.path.dirname(real) == parent and os.path.isdir(real) else None


def role_problems(role, obj, cwd):
    """Problems of a `completed` return that only its role's rules define."""
    out = []
    extra = obj.get("extra") if isinstance(obj.get("extra"), dict) else {}
    files = extra.get("files_modified")
    if role == "implement" and isinstance(files, int) and not isinstance(files, bool) and files > 0:
        if not re.match(r"\S+:\d+", str(obj.get("pattern_reference") or "")):
            out.append("`pattern_reference` must be the `file:line` of the neighbouring code you followed")
        commands = (extra.get("test_results") or {}).get("commands") if isinstance(extra.get("test_results"), dict) else None
        if not commands or not all(isinstance(c, dict) and c.get("cmd") and isinstance(c.get("exit"), int) for c in commands):
            out.append("`extra.test_results.commands[]` must list each test command run after the last edit, with `cmd` and integer `exit`")
    if role == "reviewer":
        if obj.get("verdict") not in VERDICTS:
            out.append("`verdict` must be one of `pass`, `needs_changes`, `blocking`")
        named = obj.get("review_file")   # null when the brief made the review read-only
        path = review_path(named, cwd) if isinstance(named, str) else None
        if path:
            try:
                with open(path, encoding="utf-8") as handle:
                    has_round = bool(re.search(r"(?m)^## Round \d+", handle.read()))
            except OSError:
                has_round = False
            if not has_round:
                out.append("`review_file` must name the review file you wrote, and that file must hold a `## Round {n} · {kind}` section")
    if role == "test":
        if obj.get("gate") not in ("GREEN", "RED"):
            out.append("`gate` must be `GREEN` or `RED`")
        commands = obj.get("commands")
        if not commands or not all(isinstance(c, dict) and c.get("cmd") and isinstance(c.get("exit"), int) and c.get("evidence_path") for c in commands):
            out.append("`commands[]` must list each command with `cmd`, integer `exit` and `evidence_path`")
        else:
            kept = []
            run_dir = run_folder(obj.get("task_id"), cwd)
            if run_dir:   # the task's own confined run folder, plus each cited regular file; never a folder shared with other runs
                kept.append(run_dir)
            for c in commands:
                cited = str(c["evidence_path"])
                path = locate(cited, cwd)
                if path and os.path.exists(path):
                    if os.path.isfile(path):
                        kept.append(path)
                elif os.path.isabs(cited) and not (obj.get("cleanup_done") is True and ".cm-tmp/" in cited.replace(os.sep, "/")):
                    out.append("`evidence_path` %s does not exist" % cited)
            hit = secret_hits(sorted(set(kept))) if kept else ""
            if hit:
                out.append("secret-scan found a secret in the evidence (%s): redact the value, then `agent-hub secret-scan <path>` until it exits 0" % hit)
    return out


def problems(text, role, cwd=None, model=None, root=None):
    """Every way `text` departs from the return shape of `role`; [] when it conforms."""
    file_model, statuses = agent_facts(role, root)
    lines = text.strip("\n").split("\n")
    out = header_problems(lines[0] if lines else "", role, model or file_model)
    body = "\n".join(lines[1:])
    if role == "scout":
        try:
            obj = json.loads(body)
        except ValueError as exc:
            return out + ["from line 2 the message must be one raw JSON object and nothing else (%s)" % str(exc)[:80]]
        if not isinstance(obj, dict):
            return out + ["from line 2 the message must be one raw JSON object"]
        handoff = obj.get("handoff")
        missing = [k for k in HANDOFF_KEYS if not isinstance(handoff, dict) or k not in handoff]
        if missing:
            out.append("`handoff` lacks: %s" % ", ".join(missing))
    else:
        at = -1
        for heading in SECTIONS:
            found = re.search(r"(?mi)^%s\b" % re.escape(heading), body[at + 1:])   # a prefix, so `## Changes / Plan (findings)` counts
            if not found:
                out.append("section `%s` is missing or out of order (the six, in order: %s)" % (heading, " · ".join(SECTIONS)))
                break
            at += 1 + found.start()
        block = last_json_block(body)
        if block is None:
            return out + ["after the six sections the message must end with one fenced ```json block holding your Output object"]
        try:
            obj = json.loads(block)
        except ValueError as exc:
            return out + ["the fenced json block does not parse as JSON (%s): no comments, no trailing commas" % str(exc)[:80]]
        if not isinstance(obj, dict):
            return out + ["the fenced json block must hold one object"]
    if statuses and obj.get("status") not in statuses:
        out.append("`status` must be one of: %s" % ", ".join(statuses))
    if obj.get("status") == "completed":
        out += role_problems(role, obj, cwd)
    return out


def run(argv):
    args, role, cwd = [], None, None
    i = 0
    while i < len(argv):
        if argv[i] in ("--agent", "--cwd") and i + 1 < len(argv):
            role, cwd = (argv[i + 1], cwd) if argv[i] == "--agent" else (role, argv[i + 1])
            i += 2
            continue
        args.append(argv[i])
        i += 1
    if len(args) != 1 or args[0] in ("-h", "--help"):
        print("usage: agent-hub return-check <file> [--agent <role>] [--cwd <dir>]", file=sys.stdout if args else sys.stderr)
        return 0 if args else 2
    try:
        with open(args[0], encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        print("agent-hub return-check: %s" % exc, file=sys.stderr)
        return 2
    if not role:
        found = HEADER.match(text.lstrip())
        role = found.group(1) if found else None
    if role not in ROLES:
        print("agent-hub return-check: no agent named on line 1; pass --agent <%s>" % " | ".join(ROLES), file=sys.stderr)
        return 2
    found = problems(text, role, cwd or os.getcwd())
    for line in found:
        print("- " + line)
    print("return-check: %s: %d problems" % (role, len(found)))
    return 1 if found else 0


def main(argv):
    try:
        return run(argv)
    except Exception as exc:   # exit 2 is the tool's own error, never 1 (problems found)
        print("agent-hub return-check: internal error: %s: %s" % (type(exc).__name__, str(exc)[:120]), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
