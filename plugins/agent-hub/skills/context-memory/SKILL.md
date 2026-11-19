---
name: context-memory
description: Use when an agent must recall prior project decisions or validated root causes, record a durable outcome at closeout, or decide whether a fact belongs in claude-mem or the project memory file. Gives the answer on which store holds a fact and what a closeout saves. Triggers on "remember", "recall", "save lesson", "claude-mem", "prior decision", "what was decided about".
user-invocable: false
allowed-tools:
  - Read
  - Grep
  - Glob
  - mcp__plugin_claude-mem_mcp-search__search
  - mcp__plugin_claude-mem_mcp-search__timeline
  - mcp__plugin_claude-mem_mcp-search__get_observations
  - mcp__plugin_claude-mem_mcp-search__save_memory
model: inherit
---

# Context Memory

The session is working memory and dies with it. Two stores outlive it and are not interchangeable:

- **claude-mem**: facts true in any project.
- **the project memory file**: what is true about one workspace (server, deploy command, approved decisions, recent work).

Which store, never-store list, claude-mem read, shape and types: `skills/context-memory/references/format.md`, read before the first read or write. Dedup, lesson counter, timing: `skills/context-memory/references/dedup.md`, read before any claude-mem save.

## When to use

At bootstrap (recall), at closeout (save a durable outcome), and whenever a fact needs a home.

## Route a fact

1. Useful in a different repo a month from now? claude-mem. Only here: the project memory file.
2. Cannot finish "this is still true after the plan is archived"? It is not memory; it is a task outcome in the change folder.
3. Task outcome: the change folder (`tasks.md`, `reviews/`). Test evidence: `{plan_dir}/evidence/` (only when images must outlive the run). Both die with the plan.
4. A lesson that helps only one role do its job (a mistake it repeats, a check that caught an error, a search order that worked): that agent's memory. User and architecture decisions stay in claude-mem or the project memory file; one project's facts in the project memory file; tool and environment traps in skill `## Gotchas`; a lesson several roles need in claude-mem. The never-store list below applies to agent memory.

## Project memory file

An agent in a fresh session recalls the workspace without re-asking. It never leaves the workspace; claude-mem never holds what belongs here.

### Discovery order — the only statement of it

The project-local file wins; the global cache is a fallback, never a source. Stop at the first hit:

1. Walk from `cwd` up to `{workspace_root}` (`CODE_ROOT` plus one segment, `refs/artifact-layout.md` § Where the workspace root is); take the nearest of `<dir>/.claude/MEMORY.md` (primary) or `<dir>/docs/memory/PROJECT-MEM.md` (committed for team sharing). The walk does not stop at a repository boundary.
2. Found: use it. `project_slug` = git remote name, else repo dirname.
3. Nothing on the walk: read `~/.claude/memory/projects/<project_slug>/PROJECT-MEM.md`. It is stale by definition: check that any file it cites still exists and fix the entry on drift.
4. Nothing at all: create `{workspace_root}/.claude/MEMORY.md` on the first durable save and add one line to `~/.claude/memory/MEMORY.md`.

Monorepo: a sub-project's `.claude/MEMORY.md` and the workspace file both load, nearest first; nearest wins on conflict. A file the harness already put in context is not read again; in `~/.claude` the walk is skipped (harness auto-memory is loaded).

### Global registry

`~/.claude/memory/MEMORY.md` is an index only: one line per project (`- <slug> · path: <abs root> · last_seen: <date>`), no project facts, never a fallback. Append the line the first time a project's memory file is written.

### Save trigger

Copy the skeleton from `${CLAUDE_PLUGIN_ROOT}/templates/memory/PROJECT-MEM-template.md`. Every run with a durable outcome updates the file it read at closeout, into the matching section:

| Outcome | Section | Write mode |
|---|---|---|
| fix, feature or refactor validated | `## Recent changes` | append, keep the 10 newest |
| devops deploy, SSH access, log fetch | `## Operational` (and keep the `docs/devops/SERVER-INFO.md` pointer in `## Project files index` current) | update in place on drift |
| architectural decision surfaced | `## Decisions` | append dated; a change adds a new dated claim marking the old one superseded, never overwrites |
| reviewer accepted a recurring rule | `## Conventions` | append |

Decision notes are a ledger: every claim carries a date, a claim about code carries commit and repo, and "currently" or "now" never appears without one. Operational notes describe the present and are updated in place.

**Agent memory.** At most one agent-memory write per run, at closeout, from a verified lesson: read the agent's `MEMORY.md`, edit the line with the same meaning or append one short dated line, and merge entries near 200 lines or 25KB. Language: new project memory entries and agent memory are written in English, the user's words verbatim in quotes with the date; an old entry is translated when edited; the main session's auto memory follows the reply language.

## Keeping notes alive

- **Ingest**: when something durable is learned, update every page it touches and the index.
- **Look up**: read the index before deciding.
- **Sweep** (periodic): find contradictions, orphan pages and claims a newer source overtook.

## Glossary

Keep project terms in one shared glossary (one per context) that test names and UI labels follow. A contradicting term is raised at once; an ambiguous one gets a proposed canonical name; a claim about code behaviour is checked against the code; a settled term is written immediately; no implementation detail.
The method is `refs/vendored/domain-modeling.md`; the file is the project glossary of `refs/artifact-layout.md` (`openspec/glossary.md`, else `docs/glossary.md`), format `refs/vendored/glossary-format.md`.
> "Your glossary defines 'cancellation' as X, but you seem to mean Y. Which is it?"

## Rejected requests

A declined feature request goes to `docs/brainstorm/rejected-requests.md`, one section per concept, appended on repeat; brainstorm reads it before proposing.

## Key rules

- claude-mem is not a source of truth: cross-check with the graph and a file read before relying on it.
- Never delete claude-mem without the user's explicit request (devops, worker DELETE /api/observation/:id for that exact id; no agent deletes on its own, R33); a wrong memory is corrected by a new save stating `supersedes #<old id>` and the reason, not acted on.
- claude-mem down: the lesson is not counted and the closeout block says so.
- Cross-project reference material lives in `~/.claude/memory/global/`, not as per-fact memories.

## Red flags

| Thought | Reality |
|---|---|
| "Save the plan path to claude-mem" | The plan is archived, the memory outlives it, the link dies. |
| "A second memory is safer" | Search first; the same project + type + subject is an update. |
| "This is true today, so record it" | Without a date it reads as permanent truth next month. |
