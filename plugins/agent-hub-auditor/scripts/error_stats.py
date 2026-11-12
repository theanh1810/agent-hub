#!/usr/bin/env python3
"""error_stats.py: aggregate docs/changes/*/errors.yaml and docs/plan/*/errors.yaml across the workspace roots under CODE_ROOT.

Port of error-stats.sh. Each immediate subdir of CODE_ROOT is one workspace root.
Usage: error_stats.py [CODE_ROOT] [--json] [--top N] [--recurring-threshold N] [--strict] [--help]
Exit codes: 0 ok, 1 CODE_ROOT invalid, 2 --strict without PyYAML, 3 arg parse error.
"""
import datetime
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

try:
    import yaml
    HAVE_YAML = True
except ImportError:
    yaml = None
    HAVE_YAML = False

USAGE = """error_stats.py: aggregate errors.yaml across the workspace roots under CODE_ROOT

Usage:
  error_stats.py [CODE_ROOT] [--json] [--top N] [--recurring-threshold N] [--strict] [--help]

Args:
  CODE_ROOT                  Root dir to scan. Resolution order: positional arg > $CODE_ROOT env > ~/Code.
                             Each immediate subdir is one workspace root, scanned for
                             docs/changes/*/errors.yaml and docs/plan/*/errors.yaml.
  --json                     Emit JSON (machine-readable).
  --top N                    Show top N global patterns (default 10).
  --recurring-threshold N    Project flagged "recurring" if total errors >= N (default 3).
  --strict                   Require PyYAML; exit 2 if missing. Without it a line-based
                             fallback scanner runs (best-effort).
  --help                     This help.

Env:
  CODE_ROOT                  Root dir if no positional arg given.
  NO_COLOR=1                 Disable ANSI colors. Auto-off when not a TTY or with --json.

Exit codes:
  0  ok (also when no errors found)
  1  CODE_ROOT invalid / not a directory
  2  --strict and PyYAML missing
  3  arg parse error
"""

PRUNE = {"node_modules", ".git", "dist", "build", ".next", "vendor"}
MAX_DEPTH = 8


def _width(s):
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in s)


def _truncate_display(s, max_width):
    if _width(s) <= max_width:
        return s
    w = 0
    out = []
    for ch in s:
        cw = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        if w + cw > max_width - 1:
            break
        out.append(ch)
        w += cw
    return "".join(out) + "…"


def derive_signature(item):
    """Pattern signature priority: pattern > source:task_id > screen:feature > unknown."""
    if isinstance(item, dict):
        if item.get("pattern"):
            return str(item["pattern"])
        src, tid = item.get("source"), item.get("task_id")
        if src or tid:
            return f"{src or '?'}:{tid or '?'}"
        scr, feat = item.get("screen"), item.get("feature")
        if scr or feat:
            return f"{scr or '?'}:{feat or '?'}"
    return "unknown"


def fallback_parse(path, warnings):
    """Best-effort line scanner: top-level 'errors:' or 'bugs:' list, each '- ' line a new item."""
    items, root_key, current, list_indent, non_blank = [], None, None, None, 0
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.rstrip("\n")
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                non_blank += 1
                m_root = re.match(r"^(errors|bugs)\s*:\s*(#.*)?$", line)
                if m_root and root_key is None:
                    root_key = m_root.group(1)
                    continue
                if root_key is None:
                    continue
                m_item = re.match(r"^(\s*)-\s*(.*)$", line)
                if m_item:
                    if current is not None:
                        items.append(current)
                    current = {}
                    list_indent = len(m_item.group(1))
                    rest = m_item.group(2)
                    if rest:
                        m_kv = re.match(r"^([A-Za-z0-9_]+)\s*:\s*(.*)$", rest)
                        if m_kv:
                            current[m_kv.group(1)] = m_kv.group(2).strip().strip('"').strip("'")
                    continue
                if current is not None:
                    m_kv = re.match(r"^(\s*)([A-Za-z0-9_]+)\s*:\s*(.*)$", line)
                    if m_kv and list_indent is not None and len(m_kv.group(1)) > list_indent:
                        current[m_kv.group(2)] = m_kv.group(3).strip().strip('"').strip("'")
        if current is not None:
            items.append(current)
    except OSError as e:
        warnings.append(f"{path}: read failed: {e}")
        return [], "unknown"
    if not items and non_blank > 0 and root_key is None:
        warnings.append(f"{path}: no errors:/bugs: root key detected; file may be malformed or use different schema")
    return items, root_key or "unknown"


def parse_yaml_file(path, warnings, use_yaml):
    """Return (items, root_key, parse_status)."""
    if use_yaml:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                for k in ("errors", "bugs"):
                    if isinstance(data.get(k), list):
                        return data[k], k, "yaml"
            return [], "unknown", "yaml"
        except (yaml.YAMLError, OSError, UnicodeDecodeError) as e:
            warnings.append(f"{path}: yaml parse failed ({e}); using fallback scanner")
            items, root = fallback_parse(path, warnings)
            return items, root, "fallback"
    items, root = fallback_parse(path, warnings)
    return items, root, "fallback"


def discover(code_root):
    """Sorted errors.yaml paths, same patterns and prunes as the shell find (-L, maxdepth 8)."""
    found = []
    base_depth = code_root.rstrip(os.sep).count(os.sep)
    for dirpath, dirnames, filenames in os.walk(code_root, followlinks=True):
        depth = dirpath.rstrip(os.sep).count(os.sep) - base_depth
        dirnames[:] = [d for d in dirnames if d not in PRUNE] if depth < MAX_DEPTH else []
        if "errors.yaml" not in filenames or depth + 1 > MAX_DEPTH:
            continue
        p = os.path.join(dirpath, "errors.yaml")
        if not os.path.isfile(p):
            continue
        norm = p.replace(os.sep, "/")
        if (re.search(r"/docs/plan/[^/]+/errors\.yaml$", norm)
                or re.search(r"/docs/changes/[^/]+/errors\.yaml$", norm)
                or re.search(r"/docs/changes/archive/[^/]+/errors\.yaml$", norm)):
            found.append(p)
    return sorted(found)


def project_and_plan(yaml_path, code_root):
    try:
        rel = os.path.relpath(yaml_path, code_root)
    except ValueError:
        rel = yaml_path
    project = rel.split(os.sep)[0]
    plan_id = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", os.path.basename(os.path.dirname(yaml_path)))
    return project, plan_id


def aggregate(code_root, yaml_paths, top_n, recur_threshold, use_yaml=None):
    """Return the stats dict (the --json shape, minus code_root/scanned_at)."""
    use_yaml = HAVE_YAML if use_yaml is None else (use_yaml and HAVE_YAML)
    warnings = []
    per_project = defaultdict(lambda: {"errors_count": 0, "patterns": Counter(), "severities": Counter(), "plans": set()})
    global_patterns = Counter()
    for p in yaml_paths:
        project, plan_id = project_and_plan(p, code_root)
        items, _root, _status = parse_yaml_file(p, warnings, use_yaml)
        bucket = per_project[project]
        bucket["plans"].add(plan_id)
        for item in items:
            sig = derive_signature(item)
            sev = (item.get("severity") if isinstance(item, dict) else None) or "n/a"
            bucket["errors_count"] += 1
            bucket["patterns"][sig] += 1
            bucket["severities"][sev] += 1
            global_patterns[sig] += 1
    per_project_out = []
    for proj, b in sorted(per_project.items(), key=lambda kv: (-kv[1]["errors_count"], kv[0])):
        top_pat, top_n_ = b["patterns"].most_common(1)[0] if b["patterns"] else ("-", 0)
        per_project_out.append({
            "project": proj, "errors_count": b["errors_count"], "plans_count": len(b["plans"]),
            "top_pattern": top_pat, "top_pattern_count": top_n_, "severities": dict(b["severities"]),
        })
    return {
        "files_count": len(yaml_paths),
        "projects_count": len(per_project),
        "total_errors": sum(b["errors_count"] for b in per_project.values()),
        "per_project": per_project_out,
        "top_patterns": [{"pattern": p, "count": n} for p, n in global_patterns.most_common(top_n)],
        "recurring_offenders": [
            {"project": e["project"], "errors_count": e["errors_count"], "top_pattern": e["top_pattern"]}
            for e in per_project_out if e["errors_count"] >= recur_threshold],
        "parse_warnings": warnings,
        "yaml_loader": "pyyaml" if use_yaml else "fallback",
    }


def render_text(code_root, scanned_at, stats, top_n, recur_threshold, use_color):
    def c(code, s):
        return f"\033[{code}m{s}\033[0m" if use_color else s
    bold, dim, red, yellow, green, cyan = (lambda s: c("1", s), lambda s: c("2", s), lambda s: c("31", s),
                                           lambda s: c("33", s), lambda s: c("32", s), lambda s: c("36", s))
    out = [bold("error-stats") + dim(f"  ({code_root})"),
           f"  scanned_at: {scanned_at}",
           f"  files: {stats['files_count']}  projects: {stats['projects_count']}  total_errors: {stats['total_errors']}",
           f"  yaml_loader: {stats['yaml_loader']}", ""]
    warnings = stats["parse_warnings"]
    if stats["total_errors"] == 0:
        out.append(green("No errors logged. Exit 0."))
        if warnings:
            out += ["", yellow("Parse warnings:")] + [f"  - {w}" for w in warnings]
        return "\n".join(out)
    out.append(bold("Per-project"))
    out.append(f"  {'PROJECT':<28} {'ERRORS':>7} {'PLANS':>6}  TOP PATTERN")
    for e in stats["per_project"]:
        pat_s = f"{e['top_pattern']} ({e['top_pattern_count']})" if e["top_pattern_count"] else "-"
        pat_s = _truncate_display(pat_s, 50)
        sev_s = " ".join(f"{k}={v}" for k, v in sorted(e["severities"].items()))
        line = f"  {e['project'][:28]:<28} {e['errors_count']:>7} {e['plans_count']:>6}  {pat_s}"
        if sev_s:
            line += dim(f"   [{sev_s}]")
        out.append(line)
    out += ["", bold(f"Top {top_n} patterns (global)")]
    if stats["top_patterns"]:
        for i, p in enumerate(stats["top_patterns"], 1):
            out.append(f"  {i:>2}. {p['count']:>4}  {cyan(p['pattern']):<60} {dim(chr(0x2588) * min(p['count'], 40))}")
    else:
        out.append("  (none)")
    out += ["", bold(f"Recurring offenders (>= {recur_threshold} errors)")]
    if stats["recurring_offenders"]:
        for r in stats["recurring_offenders"]:
            out.append(f"  {red(r['project']):<28} {r['errors_count']:>4}  {dim(r['top_pattern'])}")
    else:
        out.append("  (none)")
    out.append("")
    if warnings:
        out += [yellow("Parse warnings:")] + [f"  - {w}" for w in warnings] + [""]
    out += [dim("Hints:"), dim("  --json                       JSON for tooling"),
            dim("  --top N                      change top-N patterns"),
            dim("  --recurring-threshold N      change recurring cutoff")]
    return "\n".join(out)


def _positive(name, value):
    if not re.fullmatch(r"[0-9]+", value) or int(value) < 1:
        sys.stderr.write(f"{name} must be a positive integer (got: {value})\n")
        sys.exit(3)
    return int(value)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    json_mode, strict, top_n, recur, positional = False, False, 10, 3, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--json":
            json_mode = True
        elif a in ("--top", "--recurring-threshold"):
            if i + 1 >= len(argv):
                sys.stderr.write(f"Missing value for {a}\n" + USAGE)
                return 3
            v = _positive(a, argv[i + 1])
            if a == "--top":
                top_n = v
            else:
                recur = v
            i += 1
        elif a == "--strict":
            strict = True
        elif a in ("--help", "-h"):
            sys.stdout.write(USAGE)
            return 0
        elif a.startswith("--"):
            sys.stderr.write(f"Unknown flag: {a}\n" + USAGE)
            return 3
        elif positional is None:
            positional = a
        else:
            sys.stderr.write("Too many positional args\n")
            return 3
        i += 1
    root = positional or os.environ.get("CODE_ROOT") or os.path.join(os.path.expanduser("~"), "Code")
    root = os.path.expanduser(root)
    if os.path.isdir(root):
        root = os.path.abspath(root)
    else:
        sys.stderr.write(f"error: CODE_ROOT is not a directory: {root}\n")
        return 1
    if strict and not HAVE_YAML:
        sys.stderr.write("error: pyyaml required for --strict mode; install: pip3 install pyyaml\n")
        return 2
    scanned_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stats = aggregate(root, discover(root), top_n, recur)
    if json_mode:
        for e in stats["per_project"]:
            if e["top_pattern_count"] == 0:
                e["top_pattern"] = None
        out = {"code_root": root, "scanned_at": scanned_at, **stats}
        sys.stdout.write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        return 0
    use_color = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
    sys.stdout.write(render_text(root, scanned_at, stats, top_n, recur, use_color) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
