#!/usr/bin/env python3
"""Resolve stable UC/AC ids against live specs and only the current change's deltas."""
from pathlib import Path
import re

REF = re.compile(r'\bUC-\d+/AC-\d+\b')
HEADING = re.compile(r'^### Requirement:\s*(UC-\d+/AC-\d+)\b', re.M)
AC_HEADING = re.compile(r'^#{2,6}\s+(?:\*\*)?(AC-\d+)\b', re.M)


def catalog(root, plan_dir):
    """Return id -> paths, including tombstones (which cannot satisfy an active AC)."""
    root, plan = Path(root), Path(plan_dir)
    spec_root = root / 'docs/specs'
    result = {}
    for p in sorted((spec_root / 'use-cases').glob('**/UC-*.md')):
        if '_legacy' in p.parts:
            continue
        uc = re.match(r'UC-\d+', p.name)
        if not uc:
            continue
        text = p.read_text(encoding='utf-8')
        for match in AC_HEADING.finditer(text):
            end = re.search(r'^#{1,3}\s', text[match.end():], re.M)
            block = text[match.start():match.end() + end.start() if end else len(text)]
            retired = re.search(r'^\s*(?:\*\*)?(?:retired|no longer applies)(?:\*\*)?\s*$', block, re.I | re.M)
            retired = retired or re.search(r'^\s*(?:\*\*)?(?:ngừng áp dụng|ngừng dùng)(?:\*\*)?\s*$', block, re.I | re.M)  # scrub-allow: legacy UC heading read when present
            retired = retired or re.search(r'^#{2,6}\s+AC-\d+.*(?:retired|no longer applies)', block, re.I | re.M)
            retired = retired or re.search(r'^#{2,6}\s+AC-\d+.*(?:ngừng áp dụng|ngừng dùng)', block, re.I | re.M)  # scrub-allow: legacy UC heading read when present
            if not retired:
                result.setdefault(f'{uc.group()}/{match.group(1)}', []).append(str(p))
    # No unrelated change may supply an id missing from the current change.
    for p in sorted((plan / 'specs').glob('**/spec.md')):
        text, operation = p.read_text(encoding='utf-8'), None
        for line in text.splitlines():
            if line.startswith('## '):
                operation = line[3:].strip()
            match = HEADING.match(line)
            if match:
                ref = match.group(1)
                if operation == 'REMOVED Requirements':
                    result.pop(ref, None)
                elif operation in ('ADDED Requirements', 'MODIFIED Requirements'):
                    result[ref] = [str(p)]
    for p in sorted((plan / 'deltas').glob('**/UC-*.md')):
        uc = re.match(r'UC-\d+', p.name)
        if not uc:
            continue
        text = p.read_text(encoding='utf-8')
        for match in AC_HEADING.finditer(text):
            section = list(re.finditer(r'^##\s+(.+)$', text[:match.start()], re.M))
            if section and section[-1].group(1).strip() in ('Added ACs', 'Changed ACs', 'Acceptance criteria'):
                result[f'{uc.group()}/{match.group(1)}'] = [str(p)]
            elif section and section[-1].group(1).strip() in ('AC thêm', 'AC sửa', 'Điều kiện nghiệm thu'):  # scrub-allow: legacy UC heading read when present
                result[f'{uc.group()}/{match.group(1)}'] = [str(p)]
        removed = re.search(r'^## Removed ACs\s*\n(.*?)(?=^## |\Z)', text, re.M | re.S)
        removed = removed or re.search(r'^## AC bỏ\s*\n(.*?)(?=^## |\Z)', text, re.M | re.S)  # scrub-allow: legacy UC heading read when present
        if removed:
            for ac in re.findall(r'^-\s+(AC-\d+)\b', removed.group(1), re.M):
                result.pop(f'{uc.group()}/{ac}', None)
    return result


def missing_references(tasks, root, plan_dir):
    refs = catalog(root, plan_dir)
    bad = []
    for task in tasks:
        for ac in task.get('acceptance_criteria') or []:
            for ref in REF.findall(str(ac).partition('→')[2]):
                paths = refs.get(ref, [])
                if not paths:
                    bad.append(f"{task['id']}: {ref} absent from live spec and this change's delta")
                elif len(paths) != 1:
                    bad.append(f"{task['id']}: {ref} has multiple authoritative sources {paths}")
                if ref.split('/')[0] not in (task.get('covers_uc') or []):
                    bad.append(f"{task['id']}: {ref} names a UC outside covers_uc")
    return bad
