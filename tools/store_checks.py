"""The four store checks of the ruleset checker (blueprint 3.4). Each takes the store dir (holding catalog.yaml and
one folder per entry) and returns a list of problem strings: empty is green. The checker imports and prints them.
No network, no write."""
import hashlib
import os
import re
from pathlib import Path

import yaml

EXEC_EXT = {".sh", ".js", ".mjs", ".cjs", ".ts", ".py"}
OWNED_HEAD = "<!-- owned"   # first line of a main file whose row has side effects
LICENCE_OK = re.compile(r"^(MIT|Apache-2\.0|ISC|BSD(-[0-9]-Clause)?)$")


def _rows(store):
    data = yaml.safe_load((Path(store) / "catalog.yaml").read_text(encoding="utf-8")) or []
    return data["entries"] if isinstance(data, dict) else data


def store_pinned(store):
    """sha256 of every listed file equals the catalog."""
    bad = []
    for r in _rows(store):
        for f in r.get("files") or []:
            p = Path(store) / r["id"] / f["path"]
            if not p.is_file():
                bad.append(f"{r['id']}: missing {f['path']}")
            elif hashlib.sha256(p.read_bytes()).hexdigest() != f.get("sha256"):
                bad.append(f"{r['id']}: sha256 differs for {f['path']}")
    return bad


def store_no_exec(store):
    """No .sh .js .mjs .cjs .ts .py file and no exec bit anywhere in the store."""
    bad = []
    for p in sorted(Path(store).rglob("*")):
        if p.is_file() and (p.suffix in EXEC_EXT or os.stat(p).st_mode & 0o111):
            bad.append(f"{p.relative_to(store)}: executable or script file")
    return bad


def store_guard_present(store):
    """A row whose side_effects is not none has a guard, and its main file starts with an owned head."""
    bad = []
    for r in _rows(store):
        if str(r.get("side_effects") or "none") == "none":
            continue
        if not r.get("guard"):
            bad.append(f"{r['id']}: side_effects without guard")
            continue
        files = r.get("files") or []
        main = Path(store) / r["id"] / files[0]["path"] if files else None
        first = main.read_text(encoding="utf-8").splitlines()[:1] if main and main.is_file() else []
        if not first or not first[0].startswith(OWNED_HEAD):
            bad.append(f"{r['id']}: main file does not start with an owned head")
    return bad


def store_licensed(store, notices):
    """A ready row has a licence from the allowlist and its notice line appears in THIRD_PARTY_NOTICES.md."""
    text = Path(notices).read_text(encoding="utf-8") if Path(notices).is_file() else ""
    bad = []
    for r in _rows(store):
        if r.get("status") != "ready":
            continue
        if not LICENCE_OK.match(str(r.get("licence") or "")):
            bad.append(f"{r['id']}: licence {r.get('licence')!r} not allowed")
        elif not r.get("notice") or r["notice"] not in text:
            bad.append(f"{r['id']}: notice line not in {Path(notices).name}")
    return bad
