---
description: "Use when working with the project's spec layer (SDD) at cwd: check status, add a requirement, reverse-engineer specs from legacy code, repay spec debt, measure coverage, view or widen the module scope, or set up openspec/."
---

# /spec — Spec-Driven Development layer

Spec form and rules: `${CLAUDE_PLUGIN_ROOT}/rules/SDD.md`. File locations: `refs/plan-lane.md § Where the files live`. Delta template: `${CLAUDE_PLUGIN_ROOT}/templates/spec/spec-delta-template.md`.

**Paths.** `openspec/` is `{workspace_root}/openspec/`, never cwd or a sub-repo. Shell blocks run with cwd = `{workspace_root}`. `~/.claude/…` is global.

Syntax: `/spec [subcommand] [args]`; no subcommand runs `status`.

| Subcommand | What it does |
|---|---|
| `status` (default) | Spec status of the workspace cwd sits in |
| `new <name>` | A new requirement with scenarios, through the clarify gate with the user |
| `reverse <module path>` | Reverse-engineer specs from legacy code |
| `debt` | Repay the spec debt in `openspec/_debt.md` |
| `check` | Measure scenario coverage (Tested / Missing test / Not measurable) and Trace Ratio |
| `scope` | View or widen `modules_in_scope[]`; Claude detects hot modules and asks, the user never types a path |
| `init` | Set up the adoption scope and `openspec/` |

## status

Main thread reads directly (no agent) and prints a compact table in the user's language, at most 25 lines:

1. Does `openspec/specs/` exist? No: suggest `/spec init`, stop.
2. Requirement count per capability; requirements with no scenario (not to be coded yet); `unverified` ones nobody confirmed.
3. `openspec/_debt.md`: unticked and overdue lines.
4. Open questions in `questions.md` of active changes (first 10 lines).
5. Active change folders under `openspec/changes/` and their deltas; task progress reported apart from verified coverage.

## new

Spawn `Agent(subagent_type="agent-hub:brainstorm")` with `spec_only: true`, a spec-only problem and the user's description; the flow is `refs/roles/brainstorm/spec-layer.md § spec-only draft`. Information for at least one scenario missing: stop at the draft and state exactly what is missing.

A spec states three boundary tiers: Always do / Ask first / Never do.

## reverse

Spawn brainstorm `mode=reverse-engineer`, `scope: <path>`, scanning only the named module. Warn first that the result stays unverified until the user confirms it (`rules/SDD.md § 8`).

## debt

Spawn brainstorm `mode=spec-debt`: it reads `openspec/_debt.md`, cross-checks the code, asks the user to confirm each rule, writes it into a delta and ticks the box.

## check

Main thread reads and counts (no agent). Procedure and output table: `refs/commands/spec-check.md`, read before running; never measure from memory.

## init

Detection and questions run on main thread; every write goes to brainstorm `mode=spec-init`. Steps and adoption block: `refs/commands/spec-init.md`, read before running.

## scope

Steps 1-4 run on main thread (read, detect, ask); step 5 goes to brainstorm `mode=spec-scope`.

1. Read the adoption block at the top of `openspec/scope.md` (`scope`, `modules_in_scope[]`).
2. Re-detect hot modules with step 1 of `refs/commands/spec-init.md`, counting from `sdd_adopted` to now.
3. Print: module · in or out of scope · commits since `sdd_adopted`.
4. `AskUserQuestion`, `multiSelect: true`, options the out-of-scope modules with the most commits.
5. Write the picks into `modules_in_scope[]` and delete their lines from "Not yet specified".

A task touching an out-of-scope module makes brainstorm ask the user once (`rules/SDD.md § 1`), never silently add or skip.

## Output

Per `refs/final-response.md`; `status` and `check` print only the table.

```markdown
## Summary
{2-3 sentences: which subcommand ran, the main result}
## Files changed
- openspec/... {only when a file was created or changed}
## Validation
{command run + the numbers read, or "read-only, nothing changed"}
## Risk
{1 sentence; for a metric that cannot be measured say why instead of reporting 0%}
## Blocker / Approval
{requirements with no scenario, open questions, overdue spec debt}
```

## Constitutional

- Write only inside `openspec/` and only through brainstorm; everything else (`tests/`, source) is read-only.
- Never invent a scenario: a test latches onto it and it becomes a business rule nobody approved. Missing information leaves the requirement at draft.
- Never change `modules_in_scope[]` on your own; a scope change goes through `AskUserQuestion`, and dropping a module records the reason in "Not yet specified".
- `check` never prints `0%` without an adoption baseline: print `N/A` with the reason.
- Cite the requirement and scenario names and `file:line` for every coverage claim.
