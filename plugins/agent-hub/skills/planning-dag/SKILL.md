---
name: planning-dag
description: Use when brainstorm's change_design must be detailed into the English plan.yaml with its tasks inline and the reply-language plan.<lang>.md mirror — a multi-step coordinated plan for a feature, complex or cross-system change, or high-risk bug. Gives the plan files, and mirror a plan gate reads. Triggers on "create plan", "plan this", "DAG", "wave", "plan options".
user-invocable: false
allowed-tools:
  - Read
  - Grep
  - Glob
model: inherit
---

# Planning (DAG)

Brainstorm decides decomposition, scope, contracts, risks in `change_design`; planner details it (waves, steps, test cases) and runs `agent-hub check plan`. Every hard rule: `agents/planner.md`.

## When to use

- **Full plan:** new feature, complex multi-module bug, API/socket/DB change, cross-repo contract change, high-risk infra or release.
- **Lite plan:** only when `change_design.plan` carries the lite keys (brainstorm checked the Templates conditions of `agents/planner.md`); planner never re-chooses. A hotfix is that row, not a skip row.
- **No plan:** a direct command answer, a trivial one-file edit, an explanation; routing decides before planner is spawned.

## Output

Per `refs/plan-files.md § Run files`:

```text
{plan_dir}/plan.yaml                  # English: plan-level keys, waves, every task inline with its status and result; source of truth for AI
{plan_dir}/plan.<lang>.md             # reply language, human explanation; only when that is not English
```

`{workspace_root}` is `CODE_ROOT` plus one segment, never inside a sub-repo; paths stay flat, so the repo name becomes a `plan_id` prefix (`CLAUDE.md` §19.0).

With `spec_required: true`: `covers_uc` on every task, each criterion restating a spec AC ends `→ UC-XXX/AC-N` naming an existing id; the `closeout` task runs the spec sync.

## Steps

1. Read `change_design`; every task needs files, solution, criteria, `test_plan`, else `needs_revision`.
2. Map files, layer waves (`refs/roles/planner/dag.md`): vertical slices by default.
3. Per task: read each file, write `steps[]` from the live text, then test cases (`refs/roles/planner/test-cases.md`) and `verification`.
4. Write the plan file and its mirror from the templates; the mirror section by section, most unknowns first, summary last, listing per section the options to keep, cut or merge with a short reason; edit by replacing small passages, never reprinting; finally read the whole for surplus and contradiction.
5. Self-check; run `agent-hub check plan` until every line is PASS (§ Verification).

## Required `plan.yaml` sections

`templates/plan/plan-template.yaml` is the authority on top-level keys and order; no count is repeated here.

`validation_strategy` also carries brainstorm's review keys from `change_design.plan.validation_strategy`: copy `review_deep_paths` verbatim. For each checkpoint `{after_task_ids, reason, expected_red}` write `after_wave` (the wave of the last of those tasks) and `task_ids` (every task of that wave); copy `reason` and `expected_red` verbatim. An `expected_red` whose `owner_task` is not in a later wave than `after_wave` returns `needs_revision` to brainstorm, `reason: change_design_incomplete`.

## Required `plan.<lang>.md` sections

`templates/plan/plan.lang-template.md`, or `plan.lang-lite-template.md`. Organised by wave, a block per task. Carries overview, wave status, proposal, design, fixed values, what the user must do, the file tree once done; a logic task shows what changes, why, before/after, logic, approach chosen and rejected, checks, new rules, risks, steps; an ordinary task only what, why, checks, steps. Every item comes from a task key and adds no fact. The end: main risks, how to test, how to roll back, Done criteria from requirements and end conditions. Both files agree on wave count, task ids, statuses, criteria, case ids.

## Task schema

`templates/plan/task-template.yaml` is the authority (reading it is HARD, `agents/planner.md`); shapes and defaults come from it. `wave` and `depends_on` live in the task's index entry (`refs/plan-files.md`). The whole key set:

`id` · `title` · `what` · `purpose` · `out_of_scope` · `files` · `solution` · `before_after` · `logic` · `approach` · `steps` · `interfaces` ·
`pattern_refs` · `alternatives_rejected` · `user_visible_rules` · `risks` · `agent` · `tier` · `status` · `blocker` ·
`design_brief_ref` · `covers_uc` · `covers_requirements` · `est_diff_lines` · `review_checkpoint` ·
`acceptance_criteria` · `test_cases` · `case_kind_waivers` · `screen_states` · `state_waivers` · `touches` · `layer_waivers` · `verification` · `subtasks` · `result`

- `files` is `[{path, change, why}]`, never a count.
- `out_of_scope` lists what the task deliberately leaves alone, one line each (matt triage AGENT-BRIEF.md:35-68); `review_checkpoint.focus[]` and `validation_strategy.review_deep_paths` name the failure modes no test covers (obra writing-plans SKILL.md:52-90).
- `steps` is planner's, `{n, file, action, anchor, before, after, expect, why}` plus `done: false`, enough to execute from the task entry alone. `solution` stays one paragraph and, like `files[].why`, never points into `docs/brainstorm/`.
- `interfaces` is `{consumes, produces}`; `pattern_refs` is `file:line — what to copy`.
- `before_after` is `[{aspect, before, after}]`, behaviour the user sees, never code; `logic` numbered strings; `approach` `{chosen, why, cost}`; `alternatives_rejected` `[{option, why_not}]` or `[{none_because}]`, mandatory on a logic task (`refs/plan-files.md`); `user_visible_rules` `[{rule, ac}]`, `ac` never empty; `risks` strings. Brainstorm writes these five; planner copies them.
- `subtasks` takes `[]` (omitted differs). `covers_uc` is null where no UC is covered. `covers_requirements` names ≥1 id of `requirements[]` on every task but closeout. Every test case carries `covers_acceptance`, `{task_id}/AC-n` or the `UC-XXX/AC-N` its criterion names after `→`.
- `verification` is on every task. `design_brief_ref` is the only path by which implement receives `DESIGN.md`; null on a UI task builds blind.
- `closeout` names its executor with `owner`, never `agent`.
- On a `test_schema: layers` plan every case carries `layer` in place of `type`, and the task `touches` and `layer_waivers` (`refs/roles/planner/test-cases.md`).
- **No key outside the template** (`agents/planner.md` rule 7).

## Wave rules

One home: `refs/roles/planner/dag.md`.

## Agent assignment

| Work | Agent | Takes from the plan |
|---|---|---|
| code edit, feature, bug, refactor | `implement` | `what` · `files[]` · `solution` · `steps[]` · `acceptance_criteria`; applies the steps in order, nothing more |
| read-only investigation, root cause | `brainstorm` | — |
| test author and run, E2E, visual, a11y, API | `test` | `test_cases[]` · `acceptance_criteria`; part (a) runs these, part (b) adds 5-10 exploratory cases |
| review, security, contracts, docs and design critique | `reviewer` | `acceptance_criteria` · `review_checkpoint` |
| infra, CI/CD, deploy, release, runtime config | `devops` | the `devops` wave, `rollback_strategy` |

## Verification

Checklist before emitting; each item has evidence:

- [ ] Every `requirements[]` entry maps to ≥1 task via `covers_requirements`; every task but closeout names ≥1; with `spec_required: true` every task has `covers_uc`.
- [ ] Every task has `acceptance_criteria` and `verification`.
- [ ] Every contract has `producer_task` and a consumer task.
- [ ] High-risk items carry mitigation and rollback; complex plans carry 2-3 variants with trade-offs.
- [ ] `plan.yaml` and `plan.<lang>.md` agree (`refs/plan-files.md`).
- [ ] GitNexus, mem0 or Context7 needed but absent → limitation in the risks.
- [ ] A UI task with user-visible criteria has a paired `test` task (`testing-e2e`).
- [ ] `agent-hub check plan {plan_dir}` ends with every line PASS.

## Gotchas

- An edit that adds or drops a frontmatter line moves the pins below it, so the task that makes the edit carries the pin fixes (recorded 2026-10-06).

## Red flags

Rationalization table, planning and execution: `skills/planning-dag/references/rationalizations.md`, read when a step tempts a shortcut.
