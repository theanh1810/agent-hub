# Shared engineering workflow

For repository engineering tasks, use the `claude-workflow` skill when available. Its local
source is `templates/chatgpt-desktop/claude-workflow/SKILL.md`; read that entry point
and only its relevant references. It adapts the user's `.claude` workflow to this host.

Follow system/developer instructions, applicable project instructions, current user intent,
and actual tool permissions first. Keep existing authorization and approved decisions across
turns. Preserve the configured model and effort; Claude model names are not host settings.

Use Brainstorm → Planner → Implement → Review → Test responsibilities where appropriate, as
phases in the same task unless delegation is explicitly authorized and available. Use only the agents, review, memory tools, hooks, slash commands and test results the host really provides; do not
invent them.

Behavior specs own intent; execution YAML owns tasks/results. Reuse canonical artifacts and
validators in `~/.claude`; avoid copying the entire ruleset into each project. Communicate in
Vietnamese, preserve the plan's English YAML and Vietnamese mirror, and report actual checks
and meaningful limitations. General conversation and unrelated document work do not need
this engineering workflow.
