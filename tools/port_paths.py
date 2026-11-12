#!/usr/bin/env python3
"""Mechanical port of fleet paths, spawn names, script calls and citations (rules: tools/port_rules.yaml).

Walks plugins/ (or the given paths), applies the ordered rules per line, writes a file only when it
changed. --dry-run changes nothing and prints the same per-rule hit counts. Exit 0 ok, 2 misuse
(an explicit file of an unknown kind, an unreadable rule table). A line carrying the scrub-allow
marker and a frontmatter `name:` line are never touched."""
import argparse
import fnmatch
import os
import re
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
BODY_ROOT = "${CLAUDE_PLUGIN_ROOT}/"
BODY_RX = re.compile(r"(?:^|/)(?:agents/[^/]+\.md|commands/[^/]+\.md|skills/(?:.+/)?SKILL\.md)$")
REFERENCE_EXT = {".md", ".yaml", ".py"}
MARKER = "scrub-allow:"


class PortError(Exception):
    """A misuse the caller must fix: exit 2."""


def classify(rel):
    """Return 'body', 'reference', or None for a file kind the tool does not port."""
    rel = str(rel).replace(os.sep, "/")
    if BODY_RX.search(rel):
        return "body"
    return "reference" if Path(rel).suffix in REFERENCE_EXT else None


def load_skip(path):
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        raise PortError(f"rule table {path}: {e}")
    return list(data.get("skip") or [])


def load_rules(path):
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        raise PortError(f"rule table {path}: {e}")
    variables = data.get("vars") or {}
    rules = []
    for r in data.get("rules") or []:
        pattern = r["pattern"]
        for _ in range(2):  # a var may name another var
            for k, v in variables.items():
                pattern = pattern.replace("{" + k + "}", v)
        try:
            rules.append({"id": r["id"], "rx": re.compile(pattern), "replace": r["replace"]})
        except re.error as e:
            raise PortError(f"rule {r['id']}: invalid regex: {e}")
    return rules


def apply_rules(text, kind, rules):
    """Return (new_text, {rule id: hits}). A marked line and a frontmatter name: line stay as they are."""
    root = BODY_ROOT if kind == "body" else ""
    counts = {}
    out = []
    in_front = False
    for n, line in enumerate(text.splitlines(keepends=True)):
        if n == 0 and line.rstrip() == "---":
            in_front = True
        elif in_front and line.rstrip() == "---":
            in_front = False
        elif MARKER in line or (in_front and line.startswith("name:")):
            pass
        else:
            for r in rules:
                line, hits = r["rx"].subn(r["replace"].replace("{root}", root), line)
                if hits:
                    counts[r["id"]] = counts.get(r["id"], 0) + hits
            out.append(line)
            continue
        out.append(line)
    return "".join(out), counts


def write_atomic(path, text):
    mode = os.stat(path).st_mode & 0o7777
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".port-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def collect(paths, base):
    files = []
    for p in paths:
        p = Path(p)
        if p.is_dir():
            for dirpath, dirnames, filenames in os.walk(p):
                dirnames[:] = sorted(d for d in dirnames if d not in ("__pycache__", ".git"))
                files += [Path(dirpath, f) for f in sorted(filenames) if classify(f)]
        elif p.is_file():
            if classify(p.name) is None:
                raise PortError(f"{p}: unknown file kind (only .md, .yaml, .py are ported)")
            files.append(p)
        else:
            raise PortError(f"{p}: no such file or directory")
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description="Mechanical port of fleet paths and names")
    ap.add_argument("paths", nargs="*", help="files or folders (default: plugins/ of the repo)")
    ap.add_argument("--dry-run", action="store_true", help="write nothing; print the hit counts")
    ap.add_argument("--rules", default=str(HERE / "port_rules.yaml"))
    ap.add_argument("--verbose", action="store_true", help="list each changed file")
    a = ap.parse_args(argv)
    try:
        rules = load_rules(a.rules)
        skip = load_skip(a.rules)
        files = collect(a.paths or [REPO / "plugins"], REPO)
        totals = {r["id"]: 0 for r in rules}
        changed = []
        for f in files:
            rel = f.resolve().relative_to(REPO).as_posix() if f.resolve().is_relative_to(REPO) else f.as_posix()
            if any(fnmatch.fnmatch(rel, g) for g in skip):
                continue
            old = f.read_text(encoding="utf-8")
            new, counts = apply_rules(old, classify(rel), rules)
            for k, v in counts.items():
                totals[k] += v
            if new != old:
                changed.append(rel)
                if not a.dry_run:
                    write_atomic(f, new)
    except PortError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    for rid, hits in totals.items():
        print(f"{hits:5d}  {rid}")
    if a.verbose:
        for rel in changed:
            print(f"changed: {rel}")
    verb = "would change" if a.dry_run else "changed"
    print(f"total hits: {sum(totals.values())}; {verb} {len(changed)} of {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
