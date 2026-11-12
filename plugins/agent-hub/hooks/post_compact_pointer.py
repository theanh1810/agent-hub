"""SessionStart hook (matcher compact): after a compaction, point the session back at its own plan, analysis and change files, the files it edited and its last request.

Plain stdout only when source is "compact" and there is something to report, at most 2048 bytes. Writes nothing to disk. Always exits 0.
"""
import datetime
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common  # noqa: E402
from _common import read_stdin_json  # noqa: E402

MAX_BYTES = 8 * 1024 * 1024
MAX_PATHS = 3
MAX_EDITED = 10
MAX_REQUEST_CHARS = 200
MAX_OUT_BYTES = 2048
KEEP = ("/docs/changes/", "/docs/brainstorm/", "/docs/plan/", "/docs/analysis/", "/docs/specs/changes/")  # scrub-allow: legacy analysis path read
PATHRE = re.compile(r"[\w./~@+-]*docs/(?:changes|brainstorm|plan|analysis|specs/changes)/[^\s\"'`<>()\[\],;|]+")
FILE_TOOLS = ("Read", "Write", "Edit")
EDIT_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
NOT_REQUEST = ("<command-", "<local-command", "<system-reminder>")
INTRO = "POST-COMPACT: the summary above is lossy. Re-read these files this session worked on before continuing:"


def strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from strings(v)


def norm(p, cwd):
    p = os.path.expanduser(p.rstrip(".:"))
    return os.path.normpath(p if os.path.isabs(p) else os.path.join(cwd, p))


def request_text(obj, content):
    """First non-empty line of a real user request, else None."""
    if obj.get("type") != "user" or obj.get("isMeta") or obj.get("isCompactSummary"):
        return None
    if isinstance(content, list):
        if any(isinstance(c, dict) and c.get("type") == "tool_result" for c in content):
            return None
        texts = [c.get("text") for c in content if isinstance(c, dict) and c.get("type") == "text"]
        content = texts[0] if texts and isinstance(texts[0], str) else None
    if not isinstance(content, str) or content.lstrip().startswith(NOT_REQUEST):
        return None
    return next((ln.strip() for ln in content.splitlines() if ln.strip()), None)


def scan(path, cwd, wide, found, edited, req, seq):
    """One pass: docs paths into found, edited files into edited, newest request into req (wide only)."""
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        f.seek(max(0, size - MAX_BYTES))
        lines = f.read().decode("utf-8", "replace").split("\n")
    if size > MAX_BYTES:
        lines = lines[1:]
    for line in lines:
        seq += 1
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        content = (obj.get("message") or {}).get("content") if isinstance(obj.get("message"), dict) else None
        stamp = str(obj.get("timestamp") or "")
        if wide:
            text = request_text(obj, content)
            if text and (stamp, seq) >= req.get("key", ("", 0)):
                req["key"], req["text"] = (stamp, seq), text
        if not isinstance(content, list):
            continue
        for c in content:
            if not isinstance(c, dict) or c.get("type") != "tool_use" or not isinstance(c.get("input"), dict):
                continue
            inp = c["input"]
            name = c.get("name")
            for key in ("file_path", "notebook_path"):
                if name in EDIT_TOOLS and isinstance(inp.get(key), str):
                    p = norm(inp[key], cwd)
                    if os.path.isfile(p):
                        edited[p] = max(edited.get(p, ("", 0)), (stamp, seq))
            cands = []
            if name in FILE_TOOLS and isinstance(inp.get("file_path"), str):
                cands.append(inp["file_path"])
            if wide:
                for s in strings(inp):
                    cands.extend(PATHRE.findall(s))
            for p in cands:
                p = norm(p, cwd)
                if any(k in p for k in KEEP) and os.path.isfile(p):
                    found[p] = max(found.get(p, ("", 0)), (stamp, seq))
    return seq


def settled(d, limit, mt):
    """True when d already holds limit entries all newer than file mtime mt."""
    if len(d) < limit:
        return False
    try:
        kth = sorted(d.values(), reverse=True)[limit - 1][0]
        return mt + 1 < datetime.datetime.fromisoformat(kth.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return False


def collect(data):
    """(docs, edited, request): newest first; docs at most MAX_PATHS, edited at most MAX_EDITED."""
    tpath = data.get("transcript_path") or ""
    if data.get("source") != "compact" or not os.path.isfile(tpath):
        return [], [], ""
    cwd = data.get("cwd") or os.getcwd()
    found, edited, req, seq = {}, {}, {}, 0
    seq = scan(tpath, cwd, True, found, edited, req, seq)
    sub = os.path.join(os.path.dirname(tpath), str(data.get("session_id", "")), "subagents")
    files = []
    for p in glob.glob(os.path.join(sub, "agent-*.jsonl")):
        try:
            files.append((os.path.getmtime(p), p))
        except OSError:
            pass
    files.sort(reverse=True)
    for mt, p in files:
        if settled(found, MAX_PATHS, mt) and settled(edited, MAX_EDITED, mt):
            break
        seq = scan(p, cwd, False, found, edited, req, seq)
    docs = sorted(found, key=lambda p: found[p], reverse=True)[:MAX_PATHS]
    rest = [p for p in sorted(edited, key=lambda p: edited[p], reverse=True) if p not in docs]
    return docs, rest[:MAX_EDITED], req.get("text", "")


def render(docs, edited, request):
    """Output of at most MAX_OUT_BYTES: oldest edited paths go first, then the request is cut; docs stay."""
    if request:
        request = request[:MAX_REQUEST_CHARS] + ("\u2026" if len(request) > MAX_REQUEST_CHARS else "")
    edited = list(edited)

    def build(n, req):
        lines = [INTRO] + docs if docs else []
        if n:
            lines += ["Files edited this session, newest first:"] + edited[:n]
        if req:
            lines.append("Last request (first line): " + req)
        return "\n".join(lines) + "\n" if lines else ""

    n = len(edited)
    while n and len(build(n, request).encode("utf-8")) > MAX_OUT_BYTES:
        n -= 1
    while request and len(build(n, request).encode("utf-8")) > MAX_OUT_BYTES:
        request = request[:-2] + "\u2026"
        if len(request) <= 1:
            request = ""
    return build(n, request)


def main():
    try:
        out = render(*collect(read_stdin_json()))
        if out:
            sys.stdout.write(out)
    except Exception as exc:  # a hook never fails the session
        sys.stderr.write("post-compact-pointer: %s\n" % exc)
    return 0


if __name__ == "__main__":
    _common.utf8_stdio()
    sys.exit(main())
