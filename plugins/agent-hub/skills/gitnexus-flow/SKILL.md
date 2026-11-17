---
name: gitnexus-flow
description: Use when an agent must find entry points, callers or callees, route or API impact, or validate task boundaries before editing shared code or planning across systems. Gives the callers, callees and blast radius of a symbol or route. Triggers on "before editing shared code", "api impact", "find caller", "route map", "graph query".
user-invocable: false
allowed-tools:
  - Read
  - Grep
  - Glob
  - mcp__gitnexus__list_repos
  - mcp__gitnexus__query
  - mcp__gitnexus__context
  - mcp__gitnexus__impact
  - mcp__gitnexus__api_impact
  - mcp__gitnexus__route_map
  - mcp__gitnexus__tool_map
  - mcp__gitnexus__detect_changes
  - Bash(gitnexus analyze --force --skip-skills --index-only)
model: inherit
---

# GitNexus Flow

The primary code graph. Use it before reading files when dependency or impact matters.

## When to use

Before changing a shared or exported symbol, a route or handler contract, or when a wave order or consumer list depends on the answer. Skip for a one-file edit with full context, an isolated docs change, or a config tweak the user already pinpointed.

## Steps

1. `mcp__gitnexus__list_repos`: confirm the repo is indexed.
2. `mcp__gitnexus__query`: intent-driven search; capture top entry points.
3. `mcp__gitnexus__context`: callers, callees, refs, module of a candidate symbol.
4. `mcp__gitnexus__impact` (`target` + `direction`): blast radius, risk level and affected symbols by depth (`d=1` breaks). Required whenever the answer decides wave order, a consumer list, or a change to a shared symbol.
5. `mcp__gitnexus__api_impact` (a `route`, or a handler `file`): required before changing a route or its handler contract; the only tool that lists route consumers, the response fields they read and the middleware guarding them.
6. `mcp__gitnexus__route_map` / `tool_map`: HTTP routes / MCP tool definitions.
7. `mcp__gitnexus__cypher`: only for graph queries the above cannot express.
8. `mcp__gitnexus__detect_changes(scope='unstaged')`: before commit or handoff, to confirm only planned files and symbols changed; put the result in the handoff.

Steps 4 and 5 answer different questions: `impact` takes a symbol, `api_impact` a route, and a shared symbol reached over a route needs both. This chain is stated here only; `agents/brainstorm.md` § Workflow points here.

Cross-repo groups: `group_list | group_sync` (the only group tools the server exposes).

## Inside `binding_scope`

- Symbols come from `symbols_allowed[]`; files opened after a query stay in `files_allowed[]`; `tools_allowed[]` / `tools_forbidden[]` decide which tools run.
- `api_impact` may inspect a related route or handler outside the edit scope: it is the contract gate, not research (`agents/implement.md` gate 4).
- `research_complete: true`: use the graph for the blast-radius check before saving, not to re-derive the cause.
- A result reaching a file outside `files_allowed[]` is a scope finding: stop, `needs_revision`, `reason: scope_extension_needed`. Widening is brainstorm's call.

## Bug fixes

Before fixing, grep every caller of the function about to be touched, then fix the root cause once in the shared code.

## Stale index

A graph missing recent files is refreshed by whoever hit it: an agent with `Bash` runs `gitnexus analyze --force --skip-skills --index-only` in the sub-repo's own git root, not `{workspace_root}` (usually not a git root); several sub-repos: loop over each; cross-repo: `mcp__gitnexus__group_sync`. `analyze` unavailable: grep or Glob and record the limitation in `Risks`. A conclusion from a stale graph is reported as stale. The same command is closeout step 1 (`refs/closeout.md`).

## Who calls it, and when reindex runs

| Caller | When | Command | Data |
|---|---|---|---|
| `brainstorm` | scope, Phase 5 | `query` → `context` → `impact`; `api_impact` over a route or contract | entry points, `d=1` blast radius → `file_shortlist`, `binding_scope.files_allowed[]` |
| `brainstorm` | `mode=plan-write` | `impact` on shared symbols; `api_impact` on routes | dependency edges → the plan's wave order evidence, contract consumers |
| `implement` | gate 4, before saving a shared symbol | `impact`; `api_impact` | what breaks at `d=1`; the route's consumers |
| `implement` | closeout step 1, after coding and review | `detect_changes(scope='unstaged')`, then `gitnexus analyze --force --skip-skills --index-only` per sub-repo; `group_sync` across repos | changed symbols; a fresh graph |
| `reviewer` | reviewing a diff | `impact` on shared symbols; `api_impact` on routes; `detect_changes` | who else breaks; only planned files changed |
| `test` | retest scope | `context` → `api_impact`; `route_map` | which cases the change reaches; the routes |
| `devops` | bootstrap | `detect_changes` | what is really deployed, against the plan |

## Key rules

1. GitNexus runs only in a project repo's git root, when coding needs related information.
2. Leave `~/.claude` out of GitNexus: it is never indexed and never gets `gitnexus analyze` (user, 2026-09-26: "what would it need inside claude, delete it").
3. Reindex is closeout step 1, after coding and review, plus § Stale index. No hook reindexes.

## Gotchas

- A `Class.method` lookup returns not found: pass the name with `-f <file>` or the uid (recorded 2026-09-28).
- `gitnexus analyze` is a no-op when HEAD is unchanged, so uncommitted edits need `--force` (recorded 2026-09-28).
- Without `--skip-skills`, 1.6.12 copies 6 skills into the repo (recorded 2026-09-28).
- Plain `analyze` rewrites the gitnexus section of a tracked AGENTS.md or CLAUDE.md: use `--index-only` (recorded 2026-09-28).
- An old MCP process on a new index fails with a database-version error: report it so the user reconnects with `/mcp` (recorded 2026-09-28).
- 1.6.12 misses gin routes under `router.Group`, so an empty `route_map` or `api_impact` is not proof of no consumers (recorded 2026-09-28).

## Red flags

| Thought | Reality |
|---|---|
| "The graph said nothing, so nothing breaks" | A stale graph says nothing; refresh or fall back to grep and say so. |
| "One query returned more files, so widen scope" | That is a scope finding, not a licence. |
