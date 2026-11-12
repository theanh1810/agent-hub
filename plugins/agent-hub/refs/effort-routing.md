# Effort routing — the work score, the tier, and each spawn's model and effort
<Owner: agents/orchestrator.md § Output>
<Read when: scoring a request or a design; filling `task_score`, `tier`, `run_mode`, `model`, `effort` or a variant `agent` on a spawn; writing a task's `tier`; auditor grouping runs by tier>

---

Thresholds, coefficients, the matrix and the K3-before-K4 order are provisional: only § Calibration data changes them. The matrix stays a fixed table; a mid rung is reviewer's floor because the cheapest model often needs 2-3 times the turns on multi-step work.

## Score

Eight factors, 0-5 each, one line of evidence each; a value with none is an estimate and says so.

| Value | C Complexity | S Scope | R Risk | U Uncertainty |
|---|---|---|---|---|
| 0 | text, rename, typo | one line | almost no consequence | exactly what to change is known |
| 1 | simple logic, one file | one file | a small UI fault | almost sure |
| 2 | one module, clear logic | one module | a feature fault | a few files to read |
| 3 | several modules, state or async | several modules | temporary user or data impact; a fleet rule that changes agent behaviour | needs investigation |
| 4 | distributed, concurrency, performance | several services or repos | security, data consistency, production | several hypotheses |
| 5 | architecture, many failure modes | the whole system, many repos | data loss, money, downtime | cause unknown |

| Value | I Integration | D Data / state | O Operational | V Verification |
|---|---|---|---|---|
| 0 | none | stateless | the local tree only, `~/.claude` included | visible by eye |
| 1 | one internal service | UI state | app code through the normal pipeline | lint, typecheck, `tools/check ruleset (package repo only)` |
| 2 | DB or Redis | application state | build or staging config | unit test |
| 3 | DB + cache + queue | persistent DB | CI/CD, Dockerfile, deploy config | integration |
| 4 | several services + an external API | shared or distributed state | production infra, a customer host | concurrency or failure; or only a real agent run shows the behaviour |
| 5 | a distributed ecosystem | money, identity, permissions | DB failover, cluster, network | production-like or load |

O scores what the change touches, not whether it ships. A `~/.claude` rule change is O 0, usually R ≥ 3 and V 4 (`tools/check ruleset (package repo only)` proves consistency, not behaviour).

Score = C + S + U + I + V + 1.5·R + 1.25·D + 1.25·O, at most 45.

| Tier | L0 | L1 | L2 | L3 | L4 |
|---|---|---|---|---|---|
| Score | [0, 8) | [8, 19) | [19, 28) | [28, 36) | [36, 45] |

**Who scores.** Phase 1, orchestrator, from the request alone: Shape A `task_score` sets the tier of the first spawns. Phase 2, brainstorm, from `file_shortlist`, `impact` and the candidates' `risk` and `confidence`: writes `task_score` into `docs/brainstorm/{slug}.yaml`, returns `tier`, gives each `change_design` task the higher of that tier and its own; it only raises. `task_score`: `{phase: 1|2, factors: {C: {value, evidence}, S: …, V: …}, score, tier}`.

**The class always wins.** `refs/workflow-routing.md § Task Classification` picks the pipeline and every gate. Run every gate the class names at every tier; a tier never lowers a class and never switches a gate off.

## Ladder and matrix

| Rung | K0 | K1 | K2 | K3 | K4 | K5 | K6 | K7 |
|---|---|---|---|---|---|---|---|---|
| Model·effort | haiku | sonnet·low | sonnet·medium | sonnet·high | opus·medium | opus·high | opus·xhigh | opus·max |

The L2 column is every role's frontmatter, so a missing score changes nothing (§ Fallback); `tools/check ruleset (package repo only)` `effort_matrix_l2` holds it. "—" is a tier the role's pipeline never reaches.

| Role | L0 | L1 | L2 | L3 | L4 |
|---|---|---|---|---|---|
| orchestrator | sonnet·low | sonnet·low | sonnet·low | sonnet·low | sonnet·low |
| scout | sonnet·medium | sonnet·medium | sonnet·medium | sonnet·medium | sonnet·medium |
| planner | sonnet·low | sonnet·low | sonnet·low | sonnet·medium | sonnet·high |
| auditor | sonnet·low | sonnet·low | sonnet·low | sonnet·low | sonnet·low |
| brainstorm | — | opus·medium | opus·medium | opus·medium | opus·medium |
| brainstorm | — | opus·medium | opus·medium | opus·medium | opus·medium |
| designer | — | sonnet·low | sonnet·low | sonnet·medium | sonnet·high |
| implement | sonnet·low | sonnet·low | sonnet·low | sonnet·medium | sonnet·high |
| reviewer | opus·medium | opus·medium | opus·medium | opus·high | opus·xhigh |
| test | sonnet·low | sonnet·low | sonnet·low | sonnet·medium | sonnet·high |
| devops | opus·high | opus·high | opus·high | opus·high | opus·xhigh |

## Floors, ceilings, checkpoints

| Role | Floor | Ceiling | Why |
|---|---|---|---|
| devops | opus·high | opus·xhigh | HARD, never lowered, except § Simple devops |
| implement | sonnet·low | sonnet·high | sonnet at every tier, effort by tier, no opus cell, never xhigh or max |
| test | sonnet·low | sonnet·high | it observes; depth goes through `thinking_mode`; sonnet at every tier |
| brainstorm | opus·medium | opus·xhigh | starts opus·medium, one rung per unfinished return, at most 2 (§ Picking the cell); max only at a checkpoint |
| brainstorm | opus·medium | opus·xhigh | starts opus·medium, one rung per unfinished return, at most 2 (§ Picking the cell); max only at a checkpoint |
| reviewer | opus·medium | opus·xhigh | starts opus·medium, high at L3, xhigh at L4, max only at a checkpoint |
| designer | sonnet·low | sonnet·high | |

Scout runs sonnet·medium at every tier. **Checkpoint max, L4 only**: brainstorm in `mode=change-design` or a root-cause run with R = 5 or U = 5; reviewer in `mode=security`, `critique` or `merge`.

## Simple devops

User 2026-10-10. The one closed exception to the devops row: a spawn runs `Agent(subagent_type=agent-hub:devops, model=sonnet)` with `devops_op_class: simple` only when every step it carries is one of

1. a plain `git push` of a branch (never a force push), or opening a merge request;
2. start, stop, restart or status of an application service through pm2, systemd or docker, on a host listed in `docs/devops/SERVER-INFO.md`;
3. a read-only fetch of logs, health, process or disk state;

and none of the `needs_approval` rows of `agents/devops.md` § Gates holds, and no step changes a firewall, SSH, network, user or permission setting or restarts sshd or a firewall service. Any doubt → the devops row, on opus. Main thread or orchestrator sets `devops_op_class`; devops never sets it for itself, and returns `needs_revision` with `reason: devops_op_not_simple`, naming the step and running nothing, when a step is outside this list.

## Picking the cell

1. The role's cell at the tier.
2. `run_mode: ultrathink` → brainstorm, reviewer and designer one rung up, never past the ceiling.
3. A role whose `confidence` came back below 0.7 → one rung up on its next spawn, applied by main thread, never past the ceiling (brainstorm: step 6).
4. L4 and a checkpoint → K7.
5. Never below the floor. An error loop from round 2 changes no rung.
6. Brainstorm rise: it returns `in_progress` with `effort_rise_requested: true` on a stopped run (turn cap), a recommended candidate or root cause below 0.7 `confidence`, or the Phase 4 scan cap reached with evidence missing. The rise comes before any gate; the field rides only on `in_progress`, never on `awaiting_user_choice`, `needs_user_input`, `needs_design` or `needs_revision`, because a missing user fact or a needed designer is not unfinished analysis (`CLAUDE.md` §0.2). Main thread re-spawns one rung up (medium → high → xhigh) with `effort_rises` + 1, at most 2 rises per analysis (`plan_id`); the next such return asks the user (`AskUserQuestion`) instead. A rise stops at the ceiling and does not reset the scan-round cap.

## Run mode

`run_mode`, never `mode` (that word names a worker's mode and the Agent tool's permission mode).

| Value | When | Effect |
|---|---|---|
| `normal` | nothing below matches | the matrix |
| `ultrathink` | before the plan; U ≥ 4, or R ≥ 4 and C ≥ 4, or the user wrote "ultrathink", or "deep analysis"; never `hotfix` | § Picking the cell step 2; `thinking_mode: extended`; brainstorm breadth of the complex row |
| `ultracode_offer` | read-only work only: ≥6 independent units (scan targets, or tasks of one wave with empty `depends_on`), R ≤ 3 and O ≤ 2 | orchestrator spawns nothing; main thread asks (`refs/roles/orchestrator/gates.md`, Ultracode offer). Only the user can switch ultracode on |

Ultrathink is applied through the rung and `thinking_mode`, never the word (probe P3). Until probe P4 passes, a read-only ultracode run carries no matrix effort per agent.

## Overrides

An override needs its area named in the request or a factor's evidence line, matched on word boundaries (`token` in "design token" is not security), **and** its threshold.

| Area | Threshold | Adds |
|---|---|---|
| Security | R ≥ 3 or D ≥ 4 | R ≥ 4: one more `reviewer mode=security` spawn, at max on L4 |
| Data loss | D ≥ 3 | an irreversible migration carries `rollback_strategy`; brainstorm `change-design` at max on L4 |
| Distributed | C ≥ 4 or I ≥ 3 | at least one failure/duplicate/timeout `test_case`; test at sonnet·high |
| Production | O ≥ 3 | L4: devops opus·xhigh; never `ultracode_offer` |

## Fallback

- No `task_score`, one that does not parse, or a tier outside L0-L4 → L2: the base agent at its frontmatter model.
- A cell whose variant file is missing or rejected by Claude Code (F-9: `effort: max` in agent frontmatter) → that role's whole L2 cell, never a mix.
- Clamp to what the model supports: a model without the effort runs the highest it has; xhigh and max need thinking on. Either is written into the handoff.

## Variants

The Agent tool takes `model` but no effort (a skill's `effort:` did not reach a subagent's later turns, probe P2b), so each non-L2 effort is a variant agent, `agents/<role>-<effort>.md`, identical to its base but for `name`, `description`, `effort` and `maxTurns` (§ Turn caps). There are sixteen: `brainstorm-high` · `brainstorm-xhigh` · `brainstorm-max` · `designer-medium` · `designer-high` · `implement-medium` · `implement-high` · `planner-medium` · `planner-high` · `reviewer-high` · `reviewer-xhigh` · `reviewer-max` · `test-medium` · `test-high` · `devops-low` · `devops-xhigh`.

Variant files are rendered at package build (`tools/package.py`, via `tools/effort-variants.py`) from the base files. The base files are the only edited source; never edit a variant by hand. Every other check skips the variants.

## Turn caps

`maxTurns` is set per agent file (a spawn cannot pass it). `tools/effort-variants.py` writes each variant's `maxTurns` from this table at package build, and a base file is edited by hand. A cap moves only on `refs/turn-budget.md § Pass mark`.

| Agent file | maxTurns |
|---|---|
| orchestrator | 12 |
| scout | 25 |
| auditor | 45 |
| planner | 45 |
| planner-medium | 45 |
| planner-high | 45 |
| brainstorm | 60 |
| brainstorm-high | 60 |
| brainstorm-xhigh | 80 |
| brainstorm-max | 80 |
| designer | 30 |
| designer-medium | 30 |
| designer-high | 30 |
| implement | 70 |
| implement-medium | 70 |
| implement-high | 70 |
| reviewer | 50 |
| reviewer-high | 50 |
| reviewer-xhigh | 50 |
| reviewer-max | 50 |
| test | 60 |
| test-medium | 60 |
| test-high | 60 |
| devops | 45 |
| devops-low | 45 |
| devops-xhigh | 45 |

## Spawn fields

On every Shape A and Shape B spawn: `tier`; `model`, the cell's model, passed to `Agent(model)`; `effort`, the cell's effort; `agent`, the base role when the effort is its frontmatter's, else `<role>-<effort>`. Main thread runs `Agent(subagent_type=agent, model=model)` as written. A variant changes effort alone and copies its base's model, so `model` is the only way a cell's model reaches a spawn; no `<role>-<model>` file exists. The tier is the first of: the task record's `tier`; brainstorm's analysis-level `tier` (`task_score.tier` in `docs/brainstorm/{slug}.yaml`); Shape A's `task_score.tier`, only while no plan exists; L2 (§ Fallback).

## Calibration data

auditor groups its scorecard by `tier` and `run_mode`: `completion_rate`, `error_loop_count`, `tool_calls_per_task`, `avg_latency_sec`, token cost, share of tasks reviewer returned first pass; no runs prints `N/A`. Returned often → raise rungs or lower the threshold; never returned but costly → lower rungs. A change goes through brainstorm and the approval gate.
