"""Shared helpers for agent-hub hooks: stdlib only, never raises into a hook exit."""
import json
import os
import re
import sys
from pathlib import Path

_LANG_RE = re.compile(r"[a-z]{2,3}(-[A-Za-z]{2,4})?")


def plugin_root():
    """Plugin root with the CLAUDE_PLUGIN_ROOT env first, else the parent of hooks/."""
    env = os.environ.get("CLAUDE_PLUGIN_ROOT", "").strip()
    return Path(env) if env else Path(__file__).resolve().parent.parent


def utf8_stdio():
    """Reconfigure stdin, stdout and stderr to UTF-8 so a non-UTF-8 locale never breaks hook JSON."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        fn = getattr(stream, "reconfigure", None)
        if fn:
            try:
                fn(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def worktree_name(raw):
    """A safe single-segment worktree name from raw (slashes become dashes), or None when unsafe."""
    s = (raw or "").strip().replace("/", "-").replace("\\", "-")
    if not s or s.startswith(".") or ".." in s or not re.fullmatch(r"[\w.-]+", s):
        return None
    return s


def read_stdin_json():
    """Parse the hook stdin as a JSON object; malformed or empty input gives {} and one stderr line."""
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError) as exc:
        sys.stderr.write("agent-hub hook: cannot read stdin: %s\n" % exc)
        return {}
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except ValueError as exc:
        sys.stderr.write("agent-hub hook: malformed stdin JSON: %s\n" % exc)
        return {}
    return data if isinstance(data, dict) else {}


def option_env(name, default=None):
    """Value of CLAUDE_PLUGIN_OPTION_<NAME>, or default when unset or empty."""
    val = os.environ.get("CLAUDE_PLUGIN_OPTION_" + name.upper(), "").strip()
    return val or default


def reply_language(arg=None):
    """--lang value, then CLAUDE_PLUGIN_OPTION_REPLY_LANGUAGE, then en; each only when it is a language code.

    A literal ${user_config...} token never matches, so an unsubstituted token falls through.
    """
    for cand in (arg, option_env("reply_language")):
        if cand and _LANG_RE.fullmatch(cand.strip()):
            return cand.strip()
    return "en"


def envelope(event, context=None, system_message=None):
    """One hook JSON envelope as a string."""
    out = {}
    if context is not None:
        out["hookSpecificOutput"] = {"hookEventName": event, "additionalContext": context}
    if system_message:
        out["systemMessage"] = system_message
    return json.dumps(out, ensure_ascii=False)


def emit(event, context=None, system_message=None):
    sys.stdout.write(envelope(event, context, system_message) + "\n")
