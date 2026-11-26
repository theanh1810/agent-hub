#!/usr/bin/env python3
"""rule-slice.py <file>[#<heading>]: print one section of a rule file (agent-hub rule <file>#<heading>).

<file> is relative to the plugin root (rules/SDD.md, refs/turn-budget.md). With #<heading>, prints from the heading
line whose text equals <heading> to the next heading of the same or a higher level. Without it, prints the file
with any YAML frontmatter removed. The moment hooks call slice_text(), so an injected text and a hand-read slice
are the same bytes.

Exit codes: 0 printed · 2 usage error, file not found under the plugin root, or heading absent.
"""
import os
import re
import sys

HEADING = re.compile(r"(#{1,6}) +(.*?)\s*$")


class NoSlice(Exception):
    """The file or the heading does not resolve; the message says which."""


def plugin_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def slice_text(root, spec):
    """Text of `file` or `file#heading` under root. NoSlice when the file is outside root, missing, or the heading is absent."""
    rel, _, heading = spec.partition("#")
    base = os.path.realpath(root)
    path = os.path.realpath(os.path.join(base, rel))
    if not rel or not path.startswith(base + os.sep) or not os.path.isfile(path):
        raise NoSlice("no rule file %r under the plugin root" % rel)
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end > 0:
            text = text[end + 5:].lstrip("\n")
    if not heading:
        return text.rstrip("\n") + "\n"
    lines, start, level, fenced = text.split("\n"), None, 0, False
    for number, line in enumerate(lines):
        if line.startswith("```"):
            fenced = not fenced
        found = None if fenced else HEADING.match(line)
        if not found:
            continue
        if start is None and found.group(2) == heading.strip():
            start, level = number, len(found.group(1))
        elif start is not None and len(found.group(1)) <= level:
            return "\n".join(lines[start:number]).rstrip("\n") + "\n"
    if start is None:
        raise NoSlice("no heading %r in %s" % (heading, rel))
    return "\n".join(lines[start:]).rstrip("\n") + "\n"


def main(argv):
    if len(argv) != 1 or argv[0] in ("-h", "--help"):
        print("usage: agent-hub rule <file>[#<heading>]", file=sys.stdout if argv else sys.stderr)
        return 0 if argv else 2
    try:
        sys.stdout.write(slice_text(plugin_root(), argv[0]))
    except NoSlice as exc:
        print("agent-hub rule: %s" % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
