<!-- Planner writes every heading, label and sentence of this file in the reply language (plan.<lang>.md); the English text below is the template. Codes, paths, commands and ids stay as written. -->
# {Plan name}

| | |
|---|---|
| **Plan id** | {plan_id} |
| **Goal** | {1-2 sentences: once done, what is different for the user} |
| **Current state** | {what is broken or missing, 1 sentence} |
| **Size** | {N waves · M large tasks · K subtasks} |
| **Updated** | {YYYY-MM-DD, first version} · {YYYY-MM-DD, one line for each plan edit, from the analysis `changelog`} |

## Overview

| Wave | Content | Status | Done |
|---|---|---|---|
| W1 | {wave name} | implementing | 2/3 |
| W2 | {wave name} | pending | 0/4 |

Status legend: `pending` · `implementing` · `testing` · `re_implement` · `re_testing` · `reviewing` · `done` · `blocked` · `accepted_partial` (not finished, defects accepted).

## Proposal

**Why** {the problem, with the user's words if any}
**Do** {scope, each point a short phrase}
**Not do** {from `non_goals`}
**Assumptions** {from `assumptions`, each point a short phrase}
**Approach** {one paragraph, from `recommended_approach`}

## Design

{One line per main decision, with the reason.} Details: {path of the change's design.md (refs/change-files.md); old plan: ANALYSIS.md section 10}.

| File | Task | Change |
|---|---|---|
| `src-tauri/src/plans_cmd.rs` | W1-T1 | create |

**Settled values** — {name}: {value} ({source}), from `confirmed_values`.
**What you must do yourself** — {action} ({when}), from `user_actions`.
**File tree when done** — from `target_layout`; omit this item when no file is created, moved or deleted.

---

## W1 — {Wave name}

{1-2 sentences: what this wave solves, and why it must go first.}

**Wave acceptance criteria** — from `waves[].acceptance_criteria`, one box each; the wave commit ticks a box that has a `result` or a verification line proving it, and for a box left empty adds an indented line saying why.

- [ ] {observable condition}

### 1. W1-T1 · {Large task title} — `implementing`

<!-- Each item below comes from one key of the task file and adds no fact (refs/plan-files.md § Task sections of plan.<lang>.md). A logic task (`touches` holds screen, logic, api or state) shows every item from `What changes` to `Steps`; any other task shows `What changes`, `Why`, `Out of scope`, `Before / After`, `How it is checked`, `Steps`, plus `New user-visible rules` and `Risks and open points` when the task file has data. -->
**What changes.** {from `what` and `files[].path`: what is changed, in which file}.

**Why.** {from `purpose`: the current problem, with a number or a symptom; the user's words if any}. {requirement id R-n and UC-XXX, from `covers_requirements` and `covers_uc`}

**Out of scope.** {from `out_of_scope[]`: one line per thing this task deliberately leaves alone; `None` when empty}

**Before / After** (from `before_after[]`; every task, read before the steps)

| Aspect | Before | After |
|---|---|---|
| {what the user sees or the data written} | {today} | {when done} |

**Changed logic** (from `logic[]`; logic tasks only)

1. {numbered step; a branch is written "if … then …"; a constant with its reason and source}

**Chosen approach and reason.** {from `approach.chosen`}. Why: {`approach.why`}. Given up: {`approach.cost`}. (logic tasks only)

**Rejected alternatives** (from `alternatives_rejected[]`; logic tasks only)

- {option B} — {why not}

**How it is checked**

<!-- Each criterion of the task is one box. The wave commit ticks `[x]` when the task's `result.ac_check` has `met: true` for that criterion; any other box stays `[ ]` with an indented line saying why (from that entry's `note`, or "no check entry"). A ticked box states status only; the evidence sits in the `Criteria met` item of the `Result` block. -->
Criteria:

- [ ] AC-1 {…}
- [ ] AC-2 {…}

| Id | Scenario | Expected | Layer | Kind |
|---|---|---|---|---|
| TC-W1-T1-1 | {scenario to check} | {observable} | `{layer}` | `{kind}` |

Touches: `{logic · api · shape · screen · input · state}` (from `touches`). Layer waived: {layer} because {reason} — `{file:line}` (from `layer_waivers`; omit when none).

No `{kind}` case because {reason} — `{file:line}`.

Check: the cases above and `verification` in the task file.

**New user-visible rules** (from `user_visible_rules[]`; omit this item when none)

| Rule | AC holding it |
|---|---|
| {rule} | {UC-XXX/AC-N} |

**Risks and open points** (from `risks[]`; omit this item when none)

- {risk, with the `specs/_debt.md` id, open-question id or user decision}

**Steps**

<!-- Each line n.m is step steps[m] of the task file, written by planner from that step: file — behaviour change — why. Before/after code and commands live only in the task file. The wave commit rebuilds this block from the task file after the user approves the wave: `[x]` for a step with `done: true`, `[ ]` with `— not done: {reason}` for the rest, and the word `done`. -->
- [ ] 1.1 `src-tauri/src/plans_cmd.rs` — create the IPC command listing plans — the renderer cannot read the disk
- [ ] 1.2 `src/features/plans/PlansTab.tsx` — replace the build-time frozen list with a per-project hook

Review focus (≈{N} min): {point 1} · {point 2}

#### 1a. W1-T1a · {Subtask title} — `done`
{1-2 sentences: what is done} — `path/to/file.rs`. Check: {command + expected result}.

<!-- **Result** — this block is built by the wave commit from the task file's `result` after the user approves the wave; planner does not write it and leaves the line below as a comment. Each task with a non-null `result` gets one block, rebuilt whole each time (refs/closeout.md § The result in the mirror). Text in the reply language; codes, paths, commands, shas, AC and TC ids, `file:line` evidence stay as written. -->
<!-- **Result** -->
<!-- - **What was done** — {from `summary`} -->
<!-- - **Real changes** — {from `changes[]`: what · where · impact · gain · cost; logic tasks only} -->
<!-- - **Against the plan** — {from `deviations` and steps with `done: false`; "as planned" when none} -->
<!-- - **Criteria met** — {from `ac_check[]`: AC-n · met or not · evidence · TC id} -->
<!-- - **Tests run** — {from `commands[]`: command · exit code · TC id} -->
<!-- - **Left over** — {from `deviations`, `specs/_debt.md` ids, review finding ids; omit when none} -->
<!-- - **Commit** — {from `commits`} -->

---

## Main risks

| Risk | Likelihood | If it happens | How to prevent | Rollback |
|---|---|---|---|---|

## How it is tested

{Concrete commands + what counts as passing. Do not write "test thoroughly".}

## How to roll back

When: {from `rollback_strategy.trigger`}

1. {one step per line, from `rollback_strategy.steps`}

## Done criteria

<!-- The seven Definition of Done items of refs/closeout.md, one box each. Each requirement of `requirements[]` gets one box (id R-n and `text`) indented under item 2; each condition of `validation_strategy.final` gets one box indented under item 3. Wave acceptance criteria sit in their wave section and are not copied here. Add no other criterion; closeout step 3 ticks items 1, 2, 6; the final gate shows items 3-5; the wave commit records items 3-5 and 7. -->
- [ ] 1. Every task is done or accepted as partial, with a note
- [ ] 2. Every AC has evidence
  - [ ] R-1 {requirement `text`}
- [ ] 3. The tests in the plan are all green
  - [ ] {one condition of `validation_strategy.final`}
- [ ] 4. No open 🔴/🟠 defect remains
- [ ] 5. Every 🟡 defect is in the debt ledger
- [ ] 6. The closeout steps are done
- [ ] 7. The user approved at the final gate
