#!/usr/bin/env python3
"""Scrub gate: list every personal trace in the package, one `path:line class excerpt` per finding.
The private class prints [redacted]; private words inside other excerpts are masked the same way.

Repo mode scans exactly what `git add -A` would commit (git ls-files -co --exclude-standard);
--root DIR scans every file under DIR instead. Exit 0 clean, 1 findings, 2 gate misuse.
A line carrying the marker named in scrub_patterns.yaml is never reported."""
import argparse
import fnmatch
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
DEFAULT_PRIVATE = Path.home() / ".config" / "agent-hub" / "scrub-private.txt"
MAX_EXCERPT = 60
REDACTED = "[redacted]"
COMMENT = re.compile(r"(?:^|(?<=\s))#.*")


class GateError(Exception):
    """A misuse the caller must fix: exit 2."""


def load_patterns(path):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return {
        "classes": [(name, re.compile(rx)) for name, rx in (data.get("classes") or {}).items()],
        "marker": data.get("marker") or "scrub-allow:",
        "comment_classes": [(name, re.compile(rx)) for name, rx in (data.get("comment_classes") or {}).items()],
        "comment_paths": list(data.get("comment_paths") or []),
        "allow_text": [re.compile(rx) for rx in data.get("allow_text") or []],
        "allow_paths": list(data.get("allow_paths") or []),
        "allow_binary_paths": list(data.get("allow_binary_paths") or []),
    }


def load_private(path):
    """Return (patterns, status). status: ok | missing | draft | empty. Patterns read even when draft."""
    p = Path(path)
    if not p.is_file():
        return [], "missing"
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    first = next((ln for ln in lines if ln.strip()), "")
    draft = re.search(r"\bDRAFT\b", first) is not None
    pats = []
    for n, raw in enumerate(lines, 1):
        text = raw.strip()
        if not text or text.startswith("#"):
            continue
        try:
            rx = re.compile(text[3:] if text.startswith("re:") else re.escape(text), re.IGNORECASE)
        except re.error as e:
            raise GateError(f"{p}:{n}: invalid regex at position {e.pos}")
        pats.append(("private", rx))
    status = "draft" if draft else ("empty" if not pats else "ok")
    return pats, status


def file_set(repo, root):
    if root is not None:
        out = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d != ".git")
            for fn in sorted(filenames):
                out.append(Path(dirpath, fn).relative_to(root).as_posix())
        return Path(root), out
    r = subprocess.run(["git", "-C", str(repo), "ls-files", "-z", "-co", "--exclude-standard"],
                       capture_output=True)
    if r.returncode != 0:
        raise GateError(f"git ls-files failed in {repo}: {r.stderr.decode(errors='replace').strip()}")
    rels = sorted({x.decode("utf-8", "surrogateescape") for x in r.stdout.split(b"\0") if x})
    return Path(repo), [x for x in rels if x != ".git" and not x.startswith(".git/")]


def matches_any(rel, globs):
    return any(fnmatch.fnmatch(rel, g) for g in globs)


def excerpt(text):
    text = text.strip()
    return text if len(text) <= MAX_EXCERPT else text[:MAX_EXCERPT] + "..."


def redact(text, private):
    for _, rx in private:
        text = rx.sub(REDACTED, text)
    return text


def scan_file(base, rel, pats, private, allow_literals):
    findings = []
    path = base / rel
    if matches_any(rel, pats["allow_paths"]) or not path.is_file() or path.is_symlink():
        return findings
    raw = path.read_bytes()
    if not raw:
        return findings
    if b"\0" in raw[:8192]:
        if not matches_any(rel, pats["allow_binary_paths"]):
            findings.append((rel, 1, "binary_unscanned", "binary file"))
        return findings
    comments = pats["comment_classes"] if matches_any(rel, pats["comment_paths"]) else []
    for n, line in enumerate(raw.decode("utf-8", "replace").splitlines(), 1):
        if pats["marker"] in line:
            continue
        for rx in pats["allow_text"]:
            line = rx.sub(lambda m: " " * len(m.group(0)), line)
        for name, rx in pats["classes"] + private:
            for m in rx.finditer(line):
                if name == "private" and m.group(0).lower() in allow_literals:
                    continue
                shown = REDACTED if name == "private" else excerpt(redact(m.group(0), private))
                findings.append((rel, n, name, shown))
        comment = COMMENT.search(line) if comments else None
        for name, rx in comments if comment else []:
            for m in rx.finditer(comment.group(0)):
                findings.append((rel, n, name, excerpt(redact(m.group(0), private))))
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="Scrub gate for the agent-hub package")
    ap.add_argument("--private", default=str(DEFAULT_PRIVATE), help="private pattern file (never committed)")
    ap.add_argument("--require-private", action="store_true",
                    help="gate mode: a missing, empty or DRAFT private file exits 2 before any scan")
    ap.add_argument("--root", help="scan every file under DIR instead of the repo file set")
    ap.add_argument("--repo", default=str(HERE.parent), help="repo to scan in repo mode")
    ap.add_argument("--patterns", default=str(HERE / "scrub_patterns.yaml"))
    ap.add_argument("--allow-literal", action="append", default=[], metavar="VALUE",
                    help="do not report private-class hits of exactly VALUE (repeatable)")
    a = ap.parse_args(argv)
    try:
        private, status = load_private(a.private)
        if a.require_private and status != "ok":
            reason = {"missing": "file is missing", "empty": "file has no pattern line",
                      "draft": "file still carries the DRAFT line"}[status]
            raise GateError(f"private file {a.private}: {reason}")
        if status == "missing":
            print(f"warning: private file {a.private} is missing; private class not applied", file=sys.stderr)
        elif status == "draft":
            print(f"warning: private file {a.private} still carries the DRAFT line", file=sys.stderr)
        pats = load_patterns(a.patterns)
        base, rels = file_set(a.repo, a.root)
    except GateError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    literals = {v.lower() for v in a.allow_literal}
    findings = []
    for rel in rels:
        findings += scan_file(base, rel, pats, private, literals)
    findings.sort(key=lambda f: (f[0], f[1], f[2]))
    for rel, n, cls, text in findings:
        print(f"{rel}:{n} {cls} {text}")
    counts = Counter(f[2] for f in findings)
    print(f"findings: {len(findings)} in {len({f[0] for f in findings})} files; scanned: {len(rels)}")
    if counts:
        print("classes: " + " ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
