#!/usr/bin/env python3
"""PreToolUse(Read|Bash) hook: refuse a whole-file read of a large file and point to ranged reads.

Denies a Read with no offset, limit or pages, or a Bash command that is a plain `cat <one file>`,
when the file is over the byte limit or the line limit. Everything else passes silently. The hook
stores nothing and writes nothing; any error passes (fail open).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common  # noqa: E402
from _common import option_env, read_stdin_json  # noqa: E402

DEFAULT_LINES = 200
DEFAULT_BYTES = 16384
EXEMPT_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".pdf", ".ipynb"}
SHELL_META = set("|;&<>`$(){}*?[]\n")
RANGE_KEYS = ("offset", "limit", "pages")


def setting(arg, env_name, default):
    """Argument first, else the plugin option env var, else the default (empty counts as unset)."""
    val = (arg or "").strip()
    return val or option_env(env_name, default)


def parse_args(argv):
    """--switch, --lines and --bytes as `--name value`; anything else is ignored."""
    return {argv[i][2:]: argv[i + 1] for i in range(len(argv) - 1) if argv[i] in ("--switch", "--lines", "--bytes")}


def positive_int(val, default):
    try:
        return max(int(str(val).strip()), 0) or default
    except ValueError:
        return default


def target_path(data):
    """The file a whole-file read would load, or None when the call is not one."""
    tool, inp = data.get("tool_name"), data.get("tool_input")
    if not isinstance(inp, dict):
        return None
    if tool == "Read":
        path = inp.get("file_path")
        if not isinstance(path, str) or not path or any(k in inp for k in RANGE_KEYS):
            return None
    elif tool == "Bash":
        cmd = inp.get("command")
        if not isinstance(cmd, str) or SHELL_META & set(cmd):
            return None
        import shlex  # only a cat-shaped command pays for the import
        parts = shlex.split(cmd)
        if len(parts) != 2 or parts[0] != "cat" or parts[1].startswith("-"):
            return None
        path = parts[1]
    else:
        return None
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        cwd = data.get("cwd")
        path = os.path.join(cwd if isinstance(cwd, str) and cwd else os.getcwd(), path)
    return path


def count_over(path, limit):
    """True when the file holds more than `limit` lines; reads 64 KiB chunks and stops early."""
    count, last = 0, b"\n"
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            count += chunk.count(b"\n")
            last = chunk[-1:]
            if count > limit:
                return True
    return count + (0 if last == b"\n" else 1) > limit


def hit(path, max_lines, max_bytes):
    """The limit a file exceeds as text, or None when it may be read whole."""
    if os.path.splitext(path)[1].lower() in EXEMPT_EXT or not os.path.isfile(path):
        return None
    if os.stat(path).st_size > max_bytes:
        return "%d bytes" % max_bytes
    if count_over(path, max_lines):
        return "%d lines" % max_lines
    return None


def reason(path, limit, max_lines, bash):
    fix = ("Use the Read tool with offset and limit (at most %d lines), or sed -n 'START,ENDp' on the file."
           if bash else "Re-read it with the Read tool, giving offset and limit (at most %d lines per call).")
    return ("read-guard: %s is over the whole-file read limit of %s. %s Search by symbol or text first to find "
            "the part you need (rules/core.md § 8). To turn this guard off, set the agent-hub plugin option "
            "read_guard to off.") % (path, limit, fix % max_lines)


def main():
    try:
        args = parse_args(sys.argv[1:])
        if setting(args.get("switch"), "read_guard", "on").lower() == "off":
            return 0
        data = read_stdin_json()
        path = target_path(data)
        if path is None:
            return 0
        max_lines = positive_int(setting(args.get("lines"), "read_guard_lines", ""), DEFAULT_LINES)
        max_bytes = positive_int(setting(args.get("bytes"), "read_guard_bytes", ""), DEFAULT_BYTES)
        limit = hit(path, max_lines, max_bytes)
        if limit:
            out = {"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason(path, limit, max_lines, data.get("tool_name") == "Bash"),
            }}
            sys.stdout.write(json.dumps(out) + "\n")
    except Exception as exc:  # a hook never fails the session
        sys.stderr.write("read-guard: %s\n" % exc)
    return 0


if __name__ == "__main__":
    _common.utf8_stdio()
    sys.exit(main())
