#!/usr/bin/env python3
"""PreToolUse(Bash) hook: ask before a destructive git command (port of git-guard.sh).

The command is tokenised with shlex, so quoted text, heredoc bodies and commit
messages never trigger it. A match returns permissionDecision "ask" with a reason;
no match or unparsable input exits 0 with no output.
"""
import json
import os
import re
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common  # noqa: E402
from _common import read_stdin_json  # noqa: E402

SEP = {";", "&&", "||", "|", "&", "|&", "(", ")", "{", "}", "\n"}
WRAP = {"sudo", "env", "command", "exec", "time", "nohup", "xargs"}
SHELLS = {"bash", "sh", "zsh", "dash"}
GOPT_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}

def split_lines(text):
    """Split on unquoted newlines; drop heredoc bodies and unquoted # comments; collect $( ) and backtick bodies.
    Returns (lines, subs). Quote state carries across newlines, so a quoted "<<X" never swallows later lines."""
    lines, subs = [], []
    cur, q, i, n = [], None, 0, len(text)
    tag, pending = None, []
    def flush():
        nonlocal cur, tag, pending
        line = "".join(cur); cur = []
        lines.append(line)
        if pending:
            tag, pending = pending[0], []
    while i < n:
        c = text[i]
        if tag is not None and not cur and q is None:
            j = text.find("\n", i)
            j = n if j < 0 else j
            if text[i:j].strip() == tag:
                tag = None
            i = j + 1
            continue
        if q == "'":
            cur.append(c)
            if c == "'":
                q = None
        elif c == "\\" and i + 1 < n:
            cur.append(c + text[i + 1]); i += 2; continue
        elif q == '"' and c == '"':
            q = None; cur.append(c)
        elif q is None and c in "'\"":
            q = c; cur.append(c)
        elif q is None and c == "#" and (not cur or cur[-1] in " \t;&|("):
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        elif c == "\n" and q is None:
            flush()
        elif q is None and text.startswith("<<", i) and not text.startswith("<<<", i) and re.match(r"<<-?\s*['\"]?\w+", text[i:]):
            m = re.match(r"<<-?\s*['\"]?(\w+)['\"]?", text[i:])
            pending.append(m.group(1)); cur.append(m.group(0)); i += len(m.group(0)); continue
        else:
            cur.append(c)
            if c == "$" and i + 1 < n and text[i + 1] == "(":
                d, j = 1, i + 2
                while j < n and d:
                    d += (text[j] == "(") - (text[j] == ")")
                    j += 1
                subs.append(text[i + 2:j - 1])
            elif c == "`":
                j = text.find("`", i + 1)
                if j > 0:
                    subs.append(text[i + 1:j])
        i += 1
    flush()
    return lines, subs

def segments(line):
    lex = shlex.shlex(line, posix=True, punctuation_chars=";&|(){}")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    seg, segs = [], []
    try:
        for t in lex:
            if t in SEP or re.fullmatch(r"[;&|(){}]+", t):
                segs.append(seg); seg = []
            else:
                seg.append(t)
    except ValueError:
        pass
    segs.append(seg)
    return [s for s in segs if s]

def check(args):
    """args: tokens after `git`. Returns a reason or None."""
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in GOPT_ARG else 1
    if i >= len(args):
        return None
    sub, rest = args[i], args[i + 1:]
    flags = [a for a in rest if a.startswith("-")]
    short = "".join(a[1:] for a in flags if not a.startswith("--"))
    if sub == "push" and (any(a == "--force" or a.startswith("--force-with-lease") for a in flags)
                          or "f" in short or any(a.startswith("+") for a in rest)):
        return "force push rewrites shared history"
    if sub == "reset" and "--hard" in flags:
        return "reset --hard discards uncommitted work"
    if sub == "clean" and ("--force" in flags or "f" in short):
        return "clean -f deletes untracked files for good"
    if sub == "branch" and ("D" in short or (("--force" in flags or "f" in short)
                                              and ("--delete" in flags or "d" in short))):
        return "branch -D deletes a branch even when unmerged"
    if sub == "checkout" and "." in rest:
        return "checkout . discards all working-tree changes"
    if sub == "restore" and "." in rest:
        staged = "--staged" in flags or "S" in short
        worktree = "--worktree" in flags or "W" in short
        if not staged or worktree:
            return "restore . discards all working-tree changes"
    return None

SUDO_ARG = {"-u", "-g", "-h", "-p", "-r", "-t", "-U", "-C", "-D", "-R"}

def scan(text, depth=0):
    if depth > 3:
        return None
    lines, subs = split_lines(text)
    for sub in subs:
        why = scan(sub, depth + 1)
        if why:
            return why
    for line in lines:
        for seg in segments(line):
            j = 0
            while j < len(seg):
                t = seg[j]
                if re.fullmatch(r"\w+=.*", t) or t in WRAP:
                    j += 1
                elif t.startswith("-") and j > 0:
                    j += 2 if (seg[0] == "sudo" or seg[j - 1] == "sudo" or seg[j - 1].startswith("-")) and t in SUDO_ARG else 1
                else:
                    break
            if j >= len(seg):
                continue
            prog = os.path.basename(seg[j])
            rest = seg[j + 1:]
            if prog == "git":
                why = check(rest)
            elif prog in SHELLS:
                k = next((x for x, a in enumerate(rest) if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", a)), None)
                why = scan(rest[k + 1], depth + 1) if k is not None and k + 1 < len(rest) else None
            elif prog == "eval":
                why = scan(" ".join(rest), depth + 1)
            else:
                why = None
            if why:
                return why
    return None


def ask_envelope(why):
    return json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": "agent-hub git guard: %s. Approve only if you meant to do this." % why,
    }}, ensure_ascii=False)


def main():
    data = read_stdin_json()
    tool_input = data.get("tool_input")
    cmd = tool_input.get("command") if isinstance(tool_input, dict) else ""
    if not isinstance(cmd, str) or not cmd:
        return 0
    try:
        why = scan(cmd)
    except Exception:
        return 0
    if why:
        sys.stdout.write(ask_envelope(why) + "\n")
    return 0


if __name__ == "__main__":
    _common.utf8_stdio()
    sys.exit(main())
