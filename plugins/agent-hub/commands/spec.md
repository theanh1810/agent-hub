---
description: "Use when working with the project's spec layer (SDD) at cwd: check status, create a UC or BR, reverse-engineer specs from legacy code, repay spec debt, measure coverage, view or widen the module scope, or set up docs/specs/."
---

# /spec — Spec-Driven Development layer

Change files: `refs/change-files.md`. Legacy rules: `${CLAUDE_PLUGIN_ROOT}/rules/SDD.md`. Templates: `${CLAUDE_PLUGIN_ROOT}/templates/spec/`.

**Paths.** `specs/` is `{workspace_root}/docs/specs/` (`SDD.md` §3), never cwd or a sub-repo. Shell blocks run with cwd = `{workspace_root}` and name `docs/specs/` in full. `docs/…` paths resolve from `{workspace_root}` (`CLAUDE.md` §19.0); `~/.claude/…` is global.

Syntax: `/spec [subcommand] [args]`; no subcommand runs `status`.

| Subcommand | What it does |
|---|---|
| `status` (default) | Spec status of the workspace cwd sits in |
| `new <name>` | New UC from the template, through the clarify gate with the user |
| `br <name>` | New Business Requirement |
| `reverse <module path>` | Reverse-engineer specs from legacy code |
| `debt` | Repay the spec debt in `specs/_debt.md` |
| `check` | Measure Spec Coverage, AC Coverage, Regen Success Rate, Trace Ratio |
| `scope` | View or widen `modules_in_scope[]`; Claude detects hot modules and asks, the user never types a path |
| `init` | Set up the adoption scope and `docs/specs/` |

## status

Main thread reads directly (no agent) and prints a compact table in the user's language, at most 25 lines:

1. Does `specs/` exist? No: suggest `/spec init`, stop.
2. UC count by status (`draft` / `approved` / `implemented` / `deprecated`) from each "Quick info" table.
3. UCs missing "Acceptance criteria" (not to be coded yet, `SDD.md` §6 HARD); UCs in `_legacy/` nobody confirmed.
4. `specs/_debt.md`: unticked lines and overdue lines.
5. Open `- [ ]` questions across UCs (first 10 lines).
6. Active change folders under `docs/changes/` and their spec deltas; artifact readiness and YAML task progress reported apart from verified coverage.

## new / br

`new` writes the approved requirement as an ADDED Requirement in the change's spec delta through brainstorm, never a second live UC; a spec-only request stops at its active delta. `br` keeps its existing path.

1. Read the matching template. 2. Spawn `Agent(subagent_type="agent-hub:brainstorm")` with `mode=fresh`, `spec_task: "create_uc"` (or `create_br`) and the user's description. 3. Brainstorm runs the clarify gate, main thread asks via `AskUserQuestion`, brainstorm writes into `specs/`. 4. Information for at least one "Acceptance criteria" entry missing: stop at draft and state exactly what is missing.

A spec states three boundary tiers: Always do / Ask first / Never do.

## reverse

Brownfield: spawn brainstorm `mode=reverse-engineer`, `scope: <path>`, scanning only the named module. Warn first: a spec reversed from code says what the code does, not whether it is right, so a confirmation step follows or a years-old bug is legitimised as a feature.

## debt

Spawn brainstorm `mode=spec-debt`: it reads `specs/_debt.md`, cross-checks the code, asks the user to confirm each rule, writes it into the UC and ticks the box.

## check

Main thread reads and counts (no agent). Procedure, script and output table: `refs/commands/spec-check.md`, read before running; never measure from memory.

## init

Detection and questions run on main thread; every write into `specs/` goes to brainstorm `mode=spec-init`. Steps and adoption-baseline block: `refs/commands/spec-init.md`, read before running. Phase 0, before specifying any module, is an approved capability map (module codes, dependency direction, build order).

## scope

Steps 1-4 run on main thread (read, detect, ask); step 5 writes `specs/README.md` and goes to brainstorm `mode=spec-scope`.

1. Read the YAML block at the top of `specs/README.md` (`scope`, `modules_in_scope[]`).
2. Re-detect hot modules with step 1 of `refs/commands/spec-init.md`, counting from `sdd_adopted` to now.
3. Print: module · in or out of scope · commits since `sdd_adopted`.
4. `AskUserQuestion`, `multiSelect: true`, options the out-of-scope modules with the most commits.
5. Write the picks into `modules_in_scope[]` and delete their lines from "Not yet specified".

A task touching an out-of-scope module makes brainstorm ask the user once (`agents/brainstorm.md` § Spec layer (SDD)), never silently add or skip.

## Output

Per `CLAUDE.md` §12; `status` and `check` print only the table.

```markdown
## Summary
{2-3 sentences: which subcommand ran, the main result}
## Files changed
- specs/... {only when a file was created or changed}
## Validation
{command run + the numbers read, or "read-only, nothing changed"}
## Risk
{1 sentence; for a metric that cannot be measured say why instead of reporting 0%}
## Blocker / Approval
{UC missing Acceptance criteria, open questions, overdue spec debt}
```

## Constitutional

- Write only inside `specs/` and the spec delta of the running change (`{workspace_root}/docs/changes/<id>/`, `refs/change-files.md`), and only brainstorm writes; everything else (the rest of `{workspace_root}/docs/changes/`, `tests/`, source) is read-only.
- Never invent an "Acceptance criteria" entry: a test latches onto a fabricated AC and it becomes a business rule nobody approved. Missing information leaves the UC at draft.
- Never change `modules_in_scope[]` on your own; a scope change goes through `AskUserQuestion`, and dropping a module records the reason in "Not yet specified" (narrowing flatters metrics while real coverage is unchanged).
- `check` never prints `0%` without an adoption baseline: print `N/A` with the reason.
- Cite `UC-ID` / `AC-ID` / `file:line` for every coverage claim.
