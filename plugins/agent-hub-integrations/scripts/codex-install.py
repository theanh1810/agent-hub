#!/usr/bin/env python3
"""Install a validated conversion; replace only artifacts owned by this conversion/import."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import sys

PLUGIN = Path(__file__).resolve().parents[1]


def load_converter():
    s = importlib.util.spec_from_file_location('codex_convert', PLUGIN / 'scripts/codex-convert.py')
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def install(stage, codex, skills, imported):
    converter = load_converter()
    converter.validate(stage)
    manifest = json.loads((stage / 'manifest.json').read_text())
    owned = {}
    if imported:
        data = json.loads(imported.read_text())
        for group in data.get('completion', {}).get('itemTypeResults', []):
            owned[group['itemType']] = {s['target'] for s in group.get('successes', [])}
    destination = codex / 'claude-workflow'
    prior_manifest = json.loads((destination / 'manifest.json').read_text()) if (destination / 'manifest.json').is_file() else {}
    native_links = [(codex / 'agents' / (a['name'] + '.toml'), destination / 'agents' / (a['name'] + '.toml'),
                     a['name'] in owned.get('SUBAGENTS', set())) for a in manifest['agents']]
    native_links += [(skills / n, destination / 'skills' / n,
                     n in owned.get('SKILLS', set()) or n in owned.get('COMMANDS', set())
                     or (n == 'claude-workflow' and (skills / n).is_symlink()
                         and (skills / n).resolve() == PLUGIN / 'templates/chatgpt-desktop/claude-workflow')) for n in manifest['skills']]
    native_links.append((codex / 'claude-compat', destination / 'claude-compat', False))
    for target, link, may_replace in native_links:
        if target.is_symlink() and target.resolve() == link.resolve():
            continue
        if (target.exists() or target.is_symlink()) and not may_replace:
            raise ValueError(f'unowned destination exists; no changes made: {target}')
    if destination.exists() and not (destination / 'manifest.json').is_file():
        raise ValueError('existing conversion is not managed; no changes made')
    global_path = codex / 'AGENTS.md'
    native_global = (PLUGIN / 'templates/codex-work/AGENTS.md').read_text()
    previous_global = (PLUGIN / 'templates/chatgpt-desktop/AGENTS.md').read_text()
    global_is_managed = global_path.is_file() and converter.sha(global_path) == prior_manifest.get('source_hashes', {}).get('plugin/templates/codex-work/AGENTS.md')
    if global_path.is_symlink() or (global_path.exists() and not global_is_managed and global_path.read_text() not in {native_global, previous_global}):
        raise ValueError('global instructions differ; merge required before install')
    hook_script = codex / 'hooks/workflow-hook.py'
    source_hook = PLUGIN / 'templates/codex-work/workflow-hook.py'
    old_hook_hash = prior_manifest.get('source_hashes', {}).get('plugin/templates/codex-work/workflow-hook.py')
    if hook_script.is_symlink() or (hook_script.exists() and converter.sha(hook_script) not in {converter.sha(source_hook), old_hook_hash}):
        raise ValueError('unowned or modified hook implementation; no changes made')
    hook_path = codex / 'hooks.json'
    hooks = json.loads(hook_path.read_text()) if hook_path.is_file() else {'hooks': {}}
    hook_command = 'python3 ' + str(codex / 'hooks/workflow-hook.py')
    for event in ['SessionStart', 'SubagentStart', 'UserPromptSubmit', 'PreToolUse']:
        existing = hooks.setdefault('hooks', {}).get(event, [])
        preserved = []
        expected_import = {'SessionStart': ['bash', str(codex / 'hooks/session-start-orchestrator.sh')],
                           'UserPromptSubmit': ['bash', str(codex / 'hooks/orchestrator-route-reminder.sh')],
                           'PreToolUse': ['rtk', 'hook', 'claude']}.get(event)
        for row in existing:
            remaining = []
            for handler in row.get('hooks', []):
                command = handler.get('command', '')
                ours = command == hook_command and bool(prior_manifest)
                try:
                    native_import = event in owned.get('HOOKS', set()) and expected_import == shlex.split(command)
                except ValueError:
                    native_import = False
                if not ours and not native_import:
                    remaining.append(handler)
            if remaining:
                preserved.append(dict(row, hooks=remaining))
        group = {'hooks': [{'type': 'command', 'command': hook_command, 'timeout': 10}]}
        if event == 'PreToolUse':
            group['matcher'] = 'Bash'
        hooks['hooks'][event] = preserved + [group]
    codex.mkdir(parents=True, exist_ok=True)
    skills.mkdir(parents=True, exist_ok=True)
    prepared = codex / f'.claude-workflow-stage-{os.getpid()}'
    prior = codex / f'.claude-workflow-prior-{os.getpid()}'
    if prepared.exists() or prior.exists():
        raise ValueError('installation scratch collision')
    shutil.copytree(stage, prepared, symlinks=True)
    if destination.exists():
        os.replace(destination, prior)
    os.replace(prepared, destination)
    for target, link, _ in native_links:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
        target.symlink_to(link, target_is_directory=link.is_dir())
    write_atomic(global_path, native_global)
    (codex / 'hooks').mkdir(exist_ok=True)
    write_atomic(codex / 'hooks/workflow-hook.py', (PLUGIN / 'templates/codex-work/workflow-hook.py').read_text())
    write_atomic(hook_path, json.dumps(hooks, indent=2) + '\n')
    # Remove only importer-created duplicate exports/helper commands, after canonical copies exist.
    for name in ['synced', 'source-command-refs-spec-init', 'source-command-refs-spec-check']:
        if name in owned.get('SKILLS', set()) or name in owned.get('COMMANDS', set()):
            p = skills / name
            if p.is_symlink():
                p.unlink()
            elif p.is_dir():
                shutil.rmtree(p)
    converter.validate(destination)
    if global_path.read_text() != native_global:
        raise ValueError('global instructions readback mismatch')
    for target, link, _ in native_links:
        if target.resolve() != link.resolve():
            raise ValueError(f'link readback mismatch: {target}')
    if prior.exists():
        shutil.rmtree(prior)
    print(f'Installed {len(manifest["agents"])} native profiles, {len(manifest["skills"])} skills and 4 hook events')
    print('Global instructions and all managed links verified; hook trust remains the normal host gate')


def write_atomic(path, content):
    temp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    try:
        temp.write_text(content)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', type=Path, required=True)
    p.add_argument('--codex-root', type=Path, default=Path.home() / '.codex')
    p.add_argument('--skills-root', type=Path, default=Path.home() / '.agents/skills')
    p.add_argument('--import-result', type=Path)
    a = p.parse_args()
    try:
        install(a.stage.resolve(), a.codex_root.expanduser().resolve(), a.skills_root.expanduser().resolve(), a.import_result)
    except (ValueError, OSError, KeyError) as exc:
        print(f'codex-install: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
