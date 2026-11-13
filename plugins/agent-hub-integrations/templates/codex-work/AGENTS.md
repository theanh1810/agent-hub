# Native Claude workflow for Codex Work

The user has requested the complete Claude engineering workflow in local Work/Codex.
For engineering requests, use the installed fleet of native profiles in `~/.codex/agents/`
and migrated skills under `~/.agents/skills/`. Main coordinates role workers in dependency
order; workers never nested-spawn. Use the real available spawn/wait/resume APIs. Explicit
host restrictions on delegation take precedence and any sequential fallback is disclosed.

First read `~/.codex/claude-compat/runtime.md`, then the relevant parts of
`~/.codex/claude-compat/CLAUDE.md` and its lazy references. Relative rule-library paths
resolve from `~/.codex/claude-compat/`, never the product repository. The runtime contract
overrides Claude-specific API names, models, hooks, eager loading, turn caps and estimates.
System/developer rules, applicable project rules, current user intent and real permissions
take precedence. Authorization and approved choices persist across turns.

Use native orchestrator, brainstorm, scout, designer, planner, implement, reviewer, test,
devops and auditor profiles, including the appropriate configured effort variants.
Models inherit the parent OpenAI selection. Name the inherited OpenAI model when known; do not pass Claude model names or fabricate
model traces. Load a profile's bootstrap skills explicitly when not already loaded.

Specs/current approved deltas own behavior, Brainstorm owns scope/decomposition, execution
YAML owns task state/results, and mirror/checklist are derived. Preserve plan ids, AC ids,
artifact paths, lock/writeback, gates, independent-review isolation, verification and
closeout from the source workflow. Run actual checks and report unavailable capabilities.

Use `claude-workflow` as the entry skill. Migrated command skills are
`source-command-spec`, `source-command-audit` and `source-command-codestyle`.
Work uses its supported skill selector;
these are not an assertion that Claude slash commands execute identically.

Reply in Vietnamese, keep plan YAML English and the human mirror Vietnamese. General
conversation does not need the engineering fleet. Hooks use Codex's normal trust review;
never bypass it, broaden permissions or fabricate a successful connector/test result.
