#!/usr/bin/env python3
"""Copy the shippable set from a fleet config dir into this repo by an explicit allowlist manifest.

    import_fleet.py                 copy every manifest row, then write import-lock.yaml
    import_fleet.py --check         hash each locked source now and list drifted ones

Exit codes: 0 ok, 1 missing source / copy failure / drift, 2 forbidden or malformed manifest row.
"""
import argparse
import fnmatch
import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

SKIP_NAMES = {"__pycache__", ".DS_Store"}
# A manifest can add forbidden entries but never remove these.
BUILTIN_FORBIDDEN = [
    ".claude.json", "settings*.json", "memory/", "agent-memory/", "projects/", "plugins/", "docs/",
    "*.jsonl", "backups",
]


class ManifestError(Exception):
    pass


class SourceError(Exception):
    pass


def norm(rel):
    rel = rel.replace("\\", "/")
    while rel.startswith("./"):
        rel = rel[2:]
    return rel


def forbidden_hit(rel, patterns):
    """Return the pattern that forbids rel, or None. Plain entries match from the root only
    (templates/memory is shippable); glob entries match the whole path or the basename."""
    rel = norm(rel)
    base = rel.rsplit("/", 1)[-1]
    for pat in patterns:
        if any(ch in pat for ch in "*?["):
            if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(base, pat):
                return pat
        else:
            p = pat.rstrip("/")
            if rel == p or rel.startswith(p + "/") or base == p:
                return pat
    return None


def load_manifest(path):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    forbidden = BUILTIN_FORBIDDEN + [str(x) for x in data.get("forbidden") or []]
    rows = data.get("rows") or []
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or "src" not in row or ("dst" in row) == ("drop" in row):
            raise ManifestError(f"row {i}: needs src and exactly one of dst or drop: {row!r}")
        src = norm(str(row["src"]))
        if src.startswith("/") or ".." in src.split("/"):
            raise ManifestError(f"row {i}: src {src!r} leaves the source root")
        hit = forbidden_hit(src, forbidden)
        if hit:
            raise ManifestError(f"row {i}: src {src!r} is under forbidden prefix {hit!r}")
        if "dst" in row:
            dst = norm(str(row["dst"]))
            if dst.startswith("/") or ".." in dst.split("/"):
                raise ManifestError(f"row {i}: dst {dst!r} leaves the repo")
    return forbidden, rows


def is_glob(s):
    return any(ch in s for ch in "*?[")


def expand_row(src_root, row):
    """Return [(rel_src, rel_to_row)] for one row. rel_to_row is the path under the row's dst folder
    (for a folder or glob row) or '' (single file row)."""
    src = norm(str(row["src"]))
    if is_glob(src):
        parent = src.rsplit("/", 1)[0] if "/" in src else ""
        out = []
        for p in sorted(src_root.glob(src)):
            if p.is_file() and not (SKIP_NAMES & set(p.relative_to(src_root).parts)):
                rel = p.relative_to(src_root).as_posix()
                out.append((rel, rel[len(parent) + 1:] if parent else rel))
        return out
    p = src_root / src
    if p.is_symlink():
        raise SourceError(f"{src}: symlinks are not copied")
    if p.is_file():
        return [(src, "")]
    if p.is_dir():
        out = []
        for dirpath, dirnames, filenames in os.walk(p, followlinks=False):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_NAMES)
            for fn in sorted(filenames):
                if fn in SKIP_NAMES:
                    continue
                fp = Path(dirpath) / fn
                if fp.is_symlink():
                    raise SourceError(f"{fp.relative_to(src_root).as_posix()}: symlinks are not copied")
                rel = fp.relative_to(src_root).as_posix()
                out.append((rel, rel[len(src) + 1:]))
        return out
    raise SourceError(f"{src}: source does not exist")


def plan(src_root, rows, forbidden):
    """Resolve the whole manifest to {rel_src: dst} plus the dropped set, before any copy.
    A drop row beats a copy row; among copy rows the longer src wins; equal length is an error."""
    claims = {}   # rel_src -> (specificity, row_index, dst)
    dropped = {}  # rel_src -> decision id
    for i, row in enumerate(rows):
        files = expand_row(src_root, row)
        if "drop" in row:
            for rel, _ in files:
                dropped[rel] = str(row["drop"])
            continue
        dst_base = norm(str(row["dst"])).rstrip("/")
        single = len(files) == 1 and files[0][1] == ""
        for rel, sub in files:
            hit = forbidden_hit(rel, forbidden)
            if hit:
                raise ManifestError(f"row {i}: expanded file {rel!r} is under forbidden prefix {hit!r}")
            dst = dst_base if single else f"{dst_base}/{sub}"
            spec = len(norm(str(row["src"])))
            old = claims.get(rel)
            if old and old[0] == spec and old[2] != dst:
                raise ManifestError(f"rows {old[1]} and {i} map {rel!r} with equal specificity")
            if not old or spec > old[0]:
                claims[rel] = (spec, i, dst)
    mapping = {rel: c[2] for rel, c in claims.items() if rel not in dropped}
    seen = {}
    for rel, dst in mapping.items():
        if dst in seen:
            raise ManifestError(f"{rel!r} and {seen[dst]!r} both map to {dst!r}")
        seen[dst] = rel
    return mapping, dropped


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_lock(lock_path, entries):
    text = yaml.safe_dump({"files": entries}, sort_keys=False, default_flow_style=False)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=lock_path.parent, prefix=".import-lock.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(tmp, 0o644)
        os.replace(tmp, lock_path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def do_import(src_root, repo, manifest, lock):
    try:
        forbidden, rows = load_manifest(manifest)
        mapping, dropped = plan(src_root, rows, forbidden)
    except ManifestError as e:
        print(f"manifest error: {e}", file=sys.stderr)
        return 2
    except SourceError as e:
        print(f"source error: {e}", file=sys.stderr)
        return 1
    entries = []
    try:
        for rel in sorted(mapping):
            dst = repo / mapping[rel]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_root / rel, dst)
            entries.append({"src": rel, "dst": mapping[rel], "sha256": sha256(src_root / rel)})
    except OSError as e:
        print(f"copy failed at {rel}: {e}; no lock written", file=sys.stderr)
        return 1
    write_lock(lock, entries)
    print(f"rows expanded: {len(entries)}; copied: {len(entries)}; dropped: {len(dropped)}; lock: {lock}")
    return 0


def do_check(src_root, lock):
    if not lock.is_file():
        print(f"no lock file: {lock}", file=sys.stderr)
        return 1
    entries = (yaml.safe_load(lock.read_text(encoding="utf-8")) or {}).get("files") or []
    drift = []
    for e in entries:
        p = src_root / e["src"]
        if not p.is_file():
            drift.append(f"{e['src']} (missing)")
        elif sha256(p) != e["sha256"]:
            drift.append(f"{e['src']} (changed)")
    for d in drift:
        print(f"drift: {d}")
    print(f"checked: {len(entries)}; drifted: {len(drift)}")
    return 1 if drift else 0


def main(argv=None):
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=str(Path.home() / ".claude"), help="source root (default ~/.claude)")
    ap.add_argument("--repo", default=str(here.parent), help="package repo root")
    ap.add_argument("--manifest", default=str(here / "manifest.yaml"))
    ap.add_argument("--lock", default=str(here / "import-lock.yaml"))
    ap.add_argument("--check", action="store_true", help="list sources changed since the import")
    a = ap.parse_args(argv)
    src_root, repo = Path(a.src), Path(a.repo)
    if a.check:
        return do_check(src_root, Path(a.lock))
    return do_import(src_root, repo, Path(a.manifest), Path(a.lock))


if __name__ == "__main__":
    sys.exit(main())
