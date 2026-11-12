"""SessionEnd / SessionStart hook (matcher clear): carry the first ## section of the last reply across /clear.

Usage: clear_handoff.py end|start (hook JSON on stdin). Always exits 0; stdout only on start.
"""
import os
import sys
import tempfile
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json  # noqa: E402

import _common  # noqa: E402
from _common import read_stdin_json  # noqa: E402

MAX_BYTES = 4 * 1024 * 1024
MAX_CHARS = 1500
FRESH_SECONDS = 120
WAIT_SECONDS = 3.0
INTRO = ("LAST TASK (before /clear): summary of the previous session's final answer; "
         "full detail lives in the plan/analysis files it names and in project memory:")


def last_assistant_text(path):
    """Text of the last assistant message that has text, from the tail of the transcript JSONL."""
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        start = max(0, size - MAX_BYTES)
        f.seek(start)
        lines = f.read().decode("utf-8", "replace").split("\n")
    if start > 0:
        lines = lines[1:]
    for line in reversed(lines):
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if not isinstance(obj, dict) or obj.get("type") != "assistant":
            continue
        content = (obj.get("message") or {}).get("content")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = "\n".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
        else:
            continue
        if text.strip():
            return text
    return ""


def first_section(text):
    """Body of the first '## ' section of text (heading line excluded), capped at MAX_CHARS; None when absent or empty."""
    rows = text.split("\n")
    for i, row in enumerate(rows):
        if row.startswith("## "):
            body = []
            for nxt in rows[i + 1:]:
                if nxt.startswith("## "):
                    break
                body.append(nxt)
            out = "\n".join(body).strip()
            if not out:
                return None
            if len(out) > MAX_CHARS:
                cut = out[:MAX_CHARS]
                if "\n" in cut:
                    cut = cut.rsplit("\n", 1)[0]
                out = cut.rstrip() + "…"
            return out
    return None


def read_saved(path):
    if time.time() - os.stat(path).st_mtime > FRESH_SECONDS:
        return False
    with open(path, encoding="utf-8") as f:
        return f.readline().startswith("source_session: ")


def do_end(data, d, saved):
    if data.get("reason") != "clear":
        return
    summary = first_section(last_assistant_text(data["transcript_path"]))
    if not summary:
        return
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".last-task.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("source_session: %s\ncaptured_at: %s\n\n%s\n" % (data.get("session_id", ""), stamp, summary))
        os.replace(tmp, saved)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def do_start(data, d, saved):
    if data.get("source") != "clear":
        return
    summary = ""
    claim = os.path.join(d, ".last-task.claim." + str(data.get("session_id", "")))
    deadline = time.time() + WAIT_SECONDS
    while True:
        try:
            if os.path.isfile(saved) and read_saved(saved):
                os.rename(saved, claim)
                try:
                    with open(claim, encoding="utf-8") as f:
                        summary = "\n".join(f.read().split("\n")[3:]).strip()
                finally:
                    os.remove(claim)
                break
        except FileNotFoundError:
            pass
        if time.time() >= deadline:
            break
        time.sleep(0.2)
    if summary:
        sys.stdout.write(INTRO + "\n" + summary + "\n")


def main(argv):
    try:
        mode = argv[1] if len(argv) > 1 else ""
        data = read_stdin_json()
        tpath = data.get("transcript_path") or ""
        if not tpath:
            return 0
        d = os.path.dirname(tpath)
        saved = os.path.join(d, "last-task.md")
        if mode == "end":
            if os.path.isfile(tpath):
                do_end(data, d, saved)
        elif mode == "start":
            do_start(data, d, saved)
    except Exception as exc:  # a hook never fails the session
        sys.stderr.write("clear-handoff: %s\n" % exc)
    return 0


if __name__ == "__main__":
    _common.utf8_stdio()
    sys.exit(main(sys.argv))
