#!/usr/bin/env python3
"""Build and validate native Codex profiles/skills from the complete local Claude workflow."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tomllib

PLUGIN = Path(__file__).resolve().parents[1]


def find_ruleset():
    """The core plugin folder (it holds agents/): env, repo layout, then the plugin cache layout; else None."""
    env = os.environ.get('AGENT_HUB_RULESET')
    cache = PLUGIN.parent.parent / 'agent-hub'
    candidates = [Path(env).expanduser().resolve()] if env else []
    candidates += [PLUGIN.parent / 'agent-hub', cache / PLUGIN.name]
    for c in candidates:
        if (c / 'agents').is_dir():
            return c.resolve()
    versions = [d for d in cache.glob('*') if (d / 'agents').is_dir()] if cache.is_dir() else []
    return versions[0].resolve() if len(versions) == 1 else None


# Ruleset root: the core plugin that holds agents/, refs/, skills/, commands/.
SOURCE = find_ruleset()
if SOURCE and (SOURCE / 'lib').is_dir():
    sys.path.insert(0, str(SOURCE / 'lib'))
try:
    import yaml  # noqa: E402
except ImportError:  # no core plugin and no system PyYAML: main() reports the missing core plugin
    yaml = None

PLUGIN_KEY = 'plugin/'


def locate(name):
    """Resolve a manifest source key: 'plugin/...' lives in this plugin, the rest in the ruleset."""
    return PLUGIN / name[len(PLUGIN_KEY):] if name.startswith(PLUGIN_KEY) else SOURCE / name
COMPAT = '~/.codex/claude-compat'
TEXT_SUFFIXES = {'.md', '.yaml', '.yml', '.json', '.toml', '.txt'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_frontmatter(text):
    if not text.startswith('---\n'):
        return {}, text
    parts = text.split('---', 2)
    data = yaml.safe_load(parts[1])
    if not isinstance(data, dict):
        raise ValueError('frontmatter must be a mapping')
    return data, parts[2].lstrip('\n')


def translate(text):
    # Paths change; project ids, code, decisions and user quotations do not.
    home = str(Path.home())
    return text.replace('~/.claude/', COMPAT + '/').replace(
        home + '/.claude/', home + '/.codex/claude-compat/')


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def adapter(kind, bootstrap=()):
    skills = ', '.join(f'{COMPAT}/skills/{s}/SKILL.md' for s in bootstrap)
    return (f'# Native Codex {kind}\n\n'
            f'Read `{COMPAT}/runtime.md` first; that contract overrides Claude-runtime '
            'wording below. All relative rule/reference paths resolve from '
            f'`{COMPAT}/`. Preserve original plan ids and user decisions. '
            'Use actual host APIs, configured role profiles and inherited OpenAI model.\n\n'
            + (f'Explicit bootstrap skills, if not already loaded: {skills}.\n\n' if skills else ''))


def copy_skill(source, dest, name=None):
    shutil.copytree(source, dest, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
    for p in dest.rglob('*'):
        if p.is_file() and p.suffix in TEXT_SUFFIXES:
            try:
                text = p.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                continue
            if p.name == 'SKILL.md':
                fm, body = split_frontmatter(text)
                if name and p.parent == dest:
                    fm['name'] = name
                manual = fm.pop('disable-model-invocation', False)
                source_only = {key: fm.pop(key) for key in ['user-invocable', 'argument-hint'] if key in fm}
                if source_only:
                    fm.setdefault('metadata', {})['claude-source-options'] = json.dumps(source_only, ensure_ascii=False)
                if manual:
                    write(p.parent / 'agents/openai.yaml', 'policy:\n  allow_implicit_invocation: false\n')
                text = '---\n' + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + '---\n\n' + adapter('skill') + body
            p.write_text(translate(text), encoding='utf-8')


def build(out):
    out = out.expanduser().resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('build output must be empty; no existing files overwritten')
    if out == SOURCE or SOURCE in out.parents:
        raise ValueError('stage must be outside the source ruleset')
    out.mkdir(parents=True, exist_ok=True)
    inputs = {}
    agents = []
    skill_names = []
    duplicates = {}
    library = out / 'claude-compat'
    for name in ['CLAUDE.md', 'FLOW.md', 'SDD.md', 'UI_RULES.md', 'RTK.md', 'SPEC-DEVIATIONS.md']:
        p = SOURCE / name
        if p.is_file():
            write(library / name, translate(p.read_text()))
            inputs[str(p.relative_to(SOURCE))] = sha(p)
    for name in ['refs', 'agents']:
        for p in sorted((SOURCE / name).rglob('*.md')):
            write(library / p.relative_to(SOURCE), translate(p.read_text()))
            inputs[str(p.relative_to(SOURCE))] = sha(p)
    write(library / 'runtime.md', (PLUGIN / 'templates/codex-work/runtime.md').read_text())
    for name in ['templates/codex-work/runtime.md', 'scripts/codex-convert.py', 'scripts/codex-install.py',
                 'templates/codex-work/AGENTS.md', 'templates/codex-work/workflow-hook.py']:
        inputs[PLUGIN_KEY + name] = sha(PLUGIN / name)
    for p in sorted((SOURCE / 'agents').glob('*.md')):
        fm, body = split_frontmatter(p.read_text())
        name = fm['name']
        if not re.fullmatch(r'[a-z][a-z0-9-]*', name):
            raise ValueError(f'invalid agent name: {name}')
        developer = adapter('agent', fm.get('skills', [])) + translate(body)
        fields = {'name': name, 'description': fm['description'],
                  'model_reasoning_effort': fm.get('effort', 'medium'),
                  'developer_instructions': developer}
        if fields['model_reasoning_effort'] not in {'none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra'}:
            raise ValueError(f'unsupported effort: {name}')
        write(out / 'agents' / (name + '.toml'), '\n'.join(k + ' = ' + json.dumps(v, ensure_ascii=False) for k, v in fields.items()) + '\n')
        agents.append({'name': name, 'source': str(p.relative_to(SOURCE)),
                       'source_model': fm.get('model'), 'source_max_turns': fm.get('maxTurns'),
                       'source_tools': fm.get('tools'), 'effort': fields['model_reasoning_effort']})
    for p in sorted((SOURCE / 'skills').glob('*/SKILL.md')):
        fm, _ = split_frontmatter(p.read_text())
        name = fm['name']
        copy_skill(p.parent, out / 'skills' / name)
        skill_names.append(name)
        for resource in p.parent.rglob('*'):
            if resource.is_file() and '__pycache__' not in resource.parts:
                inputs[str(resource.relative_to(SOURCE))] = sha(resource)
    synced = {}
    for p in sorted((SOURCE / 'skills/synced').rglob('SKILL.md')):
        fm, _ = split_frontmatter(p.read_text())
        synced.setdefault(fm['name'], []).append(p)
    for name, paths in synced.items():
        # Keep both export origins in provenance, expose one namespaced skill.
        chosen = max(paths, key=lambda p: (p.stat().st_mtime_ns, str(p)))
        alias = 'claude-synced-' + name
        copy_skill(chosen.parent, out / 'skills' / alias, alias)
        skill_names.append(alias)
        duplicates[name] = {'sources': [str(p.relative_to(SOURCE)) for p in paths],
                            'selected': str(chosen.relative_to(SOURCE)), 'native_name': alias}
        for origin in paths:
            for resource in origin.parent.rglob('*'):
                if resource.is_file() and '__pycache__' not in resource.parts:
                    inputs[str(resource.relative_to(SOURCE))] = sha(resource)
    for p in sorted((SOURCE / 'commands').glob('*.md')):
        fm, body = split_frontmatter(p.read_text())
        name = 'source-command-' + p.stem
        metadata = {'name': name, 'description': fm.get('description', f'Run the migrated {p.stem} command.')}
        write(out / 'skills' / name / 'SKILL.md', '---\n' + yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True) + '---\n\n' + adapter('command skill') + translate(body))
        skill_names.append(name)
        inputs[str(p.relative_to(SOURCE))] = sha(p)
    for p in (SOURCE / 'commands/refs').glob('*.md'):
        write(library / p.relative_to(SOURCE), translate(p.read_text()))
        inputs[str(p.relative_to(SOURCE))] = sha(p)
    launcher = PLUGIN / 'templates/chatgpt-desktop/claude-workflow'
    copy_skill(launcher, out / 'skills/claude-workflow')
    skill_names.append('claude-workflow')
    for resource in launcher.rglob('*'):
        if resource.is_file():
            inputs[PLUGIN_KEY + str(resource.relative_to(PLUGIN))] = sha(resource)
    # Scripts/templates retain exact tested implementation instead of being rewritten.
    shared = [n for n in ['scripts', 'templates', 'code-style', 'rules', 'tools', 'docs'] if (SOURCE / n).is_dir()]
    for name in shared:
        (library / name).symlink_to(SOURCE / name, target_is_directory=True)
    (library / 'skills').symlink_to(Path.home() / '.agents/skills', target_is_directory=True)
    for folder in [n for n in shared if n in ('scripts', 'templates', 'code-style', 'rules')]:
        for resource in (SOURCE / folder).rglob('*'):
            if resource.is_file() and '__pycache__' not in resource.parts and resource.suffix != '.pyc':
                inputs[str(resource.relative_to(SOURCE))] = sha(resource)
    output_hashes = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file() and not p.is_symlink()}
    support_links = {str(p.relative_to(out)): str(p.readlink()) for p in out.rglob('*') if p.is_symlink()}
    manifest = {'schema': 1, 'source': str(SOURCE), 'agents': agents,
                'skills': sorted(skill_names), 'synced_deduplication': duplicates,
                'source_hashes': inputs, 'shared_support': shared,
                'output_hashes': output_hashes, 'support_links': support_links,
                'runtime_limits': ['maxTurns not enforced', 'tool allowlist instruction-only',
                                   'WorktreeCreate/Remove use native lifecycle', 'statusLine uses native UI',
                                   'hooks require normal trust review']}
    write(out / 'manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    validate(out)
    print(f'Built {len(agents)} native agent profiles and {len(skill_names)} skills; preserved ids and original decisions')


def validate(out):
    m = json.loads((out / 'manifest.json').read_text())
    stale = [name for name, expected in m['source_hashes'].items() if not locate(name).is_file() or sha(locate(name)) != expected]
    if stale:
        raise ValueError(f'source drift: {stale}')
    changed = [name for name, expected in m['output_hashes'].items()
               if not (out / name).is_file() or (out / name).is_symlink() or sha(out / name) != expected]
    changed += [name for name, expected in m['support_links'].items()
                if not (out / name).is_symlink() or str((out / name).readlink()) != expected]
    if changed:
        raise ValueError(f'converted content/link drift: {changed}')
    for item in m['agents']:
        data = tomllib.loads((out / 'agents' / (item['name'] + '.toml')).read_text())
        if data['name'] != item['name'] or data['model_reasoning_effort'] != item['effort'] or 'model' in data:
            raise ValueError(f'agent configuration mismatch: {item["name"]}')
        if '~/.Codex' in data['developer_instructions'] or 'Codex-openspec-pilot' in data['developer_instructions']:
            raise ValueError('unsafe generic name/path translation')
    for name in m['skills']:
        fm, _ = split_frontmatter((out / 'skills' / name / 'SKILL.md').read_text())
        if fm.get('name') != name or not fm.get('description'):
            raise ValueError(f'invalid skill: {name}')
    print(f'Validated {len(m["agents"])} agents, {len(m["skills"])} skills, {len(m["source_hashes"])} source hashes')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['build', 'validate'])
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    if SOURCE is None:
        print('agent-hub-codex: cannot find the agent-hub core plugin; set AGENT_HUB_RULESET to its folder',
              file=sys.stderr)
        return 2
    try:
        (build if a.action == 'build' else validate)(a.out.expanduser().resolve())
    except (ValueError, OSError, KeyError, yaml.YAMLError, tomllib.TOMLDecodeError) as exc:
        print(f'codex-convert: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
