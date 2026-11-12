---
name: agent-bootstrap
description: Use when an agent starts a task and must decide which durable context (project memory, mem0, code graph, library docs) to load. Gives the short list of sources worth loading for that task and the ones to skip. Triggers on "bootstrap agent", "load context for task", "start subagent", "agent kickoff".
user-invocable: false
allowed-tools:
  - Read
  - Grep
  - Glob
  - mcp__mcp_mem0__search_memories
  - mcp__plugin_context7_context7__resolve-library-id
  - mcp__plugin_context7_context7__query-docs
  - mcp__gitnexus__impact
  - mcp__gitnexus__api_impact
  - Bash(npm ci)
  - Bash(rtk pnpm install --frozen-lockfile)
  - Bash(yarn install --immutable)
model: inherit
---

# Agent Bootstrap

Load only what reduces real uncertainty. Light by default.

## When to use

Every role at the start of a task, once, before the first tool call that is not a read of the brief.

## Order of steps

1. **Skip what is loaded.** `CLAUDE.md`, the role's own `agents/<role>.md` and its frontmatter `skills:` are in context; `refs/*.md` is read only when the task reaches that rule. Rule files, on the brief's fields:
   - `${CLAUDE_PLUGIN_ROOT}/rules/SDD.md` and `${CLAUDE_PLUGIN_ROOT}/rules/UI_RULES.md` on the conditions of `CLAUDE.md` §18.
   - `${CLAUDE_PLUGIN_ROOT}/rules/code-style/_discipline.md` plus `<language>.md` per language in `binding_scope`, when the task edits code. These files also load by their `paths:` globs; this read is the fallback.
2. **Judging or measuring a rule sentence: re-read it from disk** (`sed -n` that section) before quoting, counting or filing a finding against it; the eager snapshot ages while a plan edits those files. Reviewer, auditor and any role adjudicating a rule.
3. **Parse the task**: objective, target area (UI / backend / DB / mobile / infra / docs / cross-system), risk.
4. **Project memory**: the file `skills/context-memory/SKILL.md` § Discovery order returns, read once, so settled facts (server, deploy command, approved decisions) are not asked again.
5. **mem0** (`mcp__mcp_mem0__search_memories`) only when durable cross-project context likely matters; narrow, by repo and objective keywords.
6. **Code graph** (`skills/gitnexus-flow/SKILL.md`) before reading files, only when dependency or impact risk is real; inside `binding_scope` when brainstorm gave one.
7. **Library docs** (`mcp__plugin_context7_context7__resolve-library-id`, then `query-docs`) only when library behaviour is genuinely unclear.
8. **File reads** targeted, at most 200 lines per chunk, inside `binding_scope.files_allowed[]` when set.

## Skip table

| Task | Skip |
|---|---|
| one-file edit | mem0, graph, library docs |
| docs-only | graph, library docs |
| hotfix | full mem0 search (minimal recall only) |
| reviewer `mode=independent` | mem0, and the memory file's `## Decisions` and `## Recent changes` |
| explanation / Q&A | everything except the file the user pointed to |

## Key rules

- **Blast radius before saving any exported or shared symbol**: `skills/gitnexus-flow/SKILL.md` steps 4-5.
- A subagent uses the skills its agent file names and runs no per-reply skill check.
- Closeout saves to mem0 only a durable, validated outcome (confirmed root cause, accepted decision, reusable pattern, deploy lesson); shape and dedup in `skills/context-memory/SKILL.md`. Never secrets, raw logs, transient traces, source dumps or unproven guesses.
- After a durable outcome (merge, validated fix, deploy, approved decision) update the project memory file per `skills/context-memory/SKILL.md` § Save trigger.
- Session notes stay in the scratchpad and die with the session.
- A stale graph is refreshed by whoever hit it: `skills/gitnexus-flow/SKILL.md` § Stale index.
- Context has two budgets: window load and human attention. A must-have document behind a weakly worded pointer is a variance bug: fix the pointer's opening words first, then consider embedding.
- Isolated work in a worktree: `node_modules` is cloned by the create hook; when the hook printed `node_modules not cloned`, run the repo's lockfile install (`npm ci`, `pnpm install --frozen-lockfile`, `yarn install --immutable`) and never copy `.next` or other build output in; run the baseline tests first; a red baseline is reported and asked about. Never implement on `main` without the user's yes.

## Gotchas

- Under the RTK hook `wc -l < file` prints 0 and `diff` can call differing files identical: count and compare with `python3 -I` (`RTK.md` rows `wc` and `diff`; recorded 2026-09-07, 2026-09-21).
- The scratchpad is shared by parallel agents: prefix script names with the task id (recorded 2026-10-01).
- Never delete by glob in the scratchpad: delete only your own prefixed files by exact name (recorded 2026-10-05).

## Red flags

| Thought | Reality |
|---|---|
| "Load everything, to be safe" | Each extra source costs window and rarely reduces uncertainty. |
| "I remember the rule" | A rule you are about to judge is re-read from disk. |
| "impact ran, so the route is covered" | `impact` takes a symbol, `api_impact` a route; run the one that fits. |
