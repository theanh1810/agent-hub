#!/usr/bin/env python3
"""Codex event adapter: context hooks plus the existing RTK Bash rewrite protocol."""
import json
from pathlib import Path
import subprocess
import sys


def process(event):
    kind = event.get('hook_event_name', '')
    if kind in {'SessionStart', 'SubagentStart'}:
        text = ('Use the installed native Claude workflow fleet for engineering tasks: '
                'read ~/.codex/claude-compat/runtime.md before source role rules. '
                'Main dispatches configured role profiles in dependency order; workers never nested-spawn. '
                'Preserve existing user authorization, spec/plan ownership and actual verification. '
                'System/developer policy and real tool permissions take precedence.')
        return {'hookSpecificOutput': {'hookEventName': kind, 'additionalContext': text}}
    if kind == 'UserPromptSubmit':
        prompt = event.get('prompt', '').lower()
        if any(x in prompt for x in ['skip orchestrator', 'do it directly',
                                     'làm trực tiếp', 'không cần agent']):  # scrub-allow: reply-language phrases
            return {}
        if not any(x in prompt for x in ['fix', 'bug', 'build', 'implement', 'refactor', 'feature',
                                         'deploy', 'review', 'test', 'plan', 'audit', 'workflow', 'convert',
                                         'sửa', 'thêm',  # scrub-allow: reply-language keywords
                                         'kiểm tra', 'đánh giá', 'rà soát']):  # scrub-allow: reply-language keywords
            return {}
        return {'hookSpecificOutput': {'hookEventName': kind, 'additionalContext':
                'Follow the native workflow routing contract for this engineering request. '
                'Use actual Codex role profiles and host APIs; never execute Claude API names. '
                'Previously granted authorization persists. Canonical specs, task YAML and evidence own state.'}}
    if kind != 'PreToolUse' or event.get('tool_name') != 'Bash':
        return {}
    data = event.get('tool_input') or {}
    command = data.get('command', data.get('cmd'))
    if not isinstance(command, str) or not command:
        return {}
    rtk = Path('/opt/homebrew/bin/rtk')
    if not rtk.is_file():
        return {}
    payload = dict(event, tool_name='Bash', tool_input=dict(data, command=command))
    try:
        completed = subprocess.run([str(rtk), 'hook', 'claude'], input=json.dumps(payload),
                                   capture_output=True, text=True, timeout=5, check=False)
        if completed.returncode or not completed.stdout.strip():
            return {}
        output = json.loads(completed.stdout)
        specific = output.get('hookSpecificOutput', {})
        if specific.get('permissionDecision') != 'allow':
            return {}
        update = specific.get('updatedInput', {})
        if not isinstance(update.get('command'), str):
            return {}
        # Return only the documented rewrite fields. Parent sandbox/approvals still apply.
        return {'hookSpecificOutput': {'hookEventName': 'PreToolUse',
                'permissionDecision': 'allow', 'updatedInput': {'command': update['command']}}}
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, TypeError):
        return {}


if __name__ == '__main__':
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError('hook input must be a JSON object')
        print(json.dumps(process(payload)))
    except (ValueError, TypeError) as exc:
        print(f'workflow-hook: {exc}', file=sys.stderr)
        sys.exit(1)
