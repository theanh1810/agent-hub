<!-- Planner writes every heading, label and sentence of this file in the reply language (plan.<lang>.md); the English text below is the template. Codes, paths, commands and ids stay as written. -->
# {Fix name}

| | |
|---|---|
| **Plan id** | {plan_id} |
| **Kind** | {small bug · hotfix} |
| **Goal** | {1-2 sentences: once fixed, what the user sees differently} |
| **Root cause** | {1-2 sentences, with `file:line`} |
| **Size** | {N files · ~M lines} |
| **Updated** | {YYYY-MM-DD, first version} · {YYYY-MM-DD, one line for each plan edit} |

---

## W1 — Fix and verify

**Wave acceptance criteria**

- [ ] {observable condition}

### 1. W1-T1 · {Title} — `pending`

<!-- Each item below comes from one key of the task file and adds no fact (refs/plan-files.md § Task sections of plan.<lang>.md). A logic task (`touches` holds screen, logic, api or state) shows every item from `What changes` to `Steps`; any other task shows `What changes`, `Why`, `How it is checked`, `Steps`, plus `New user-visible rules` and `Risks and open points` when the task file has data. -->
**What changes.** {from `what` and `files[].path`: what is changed, in which file}.

**Why.** {from `purpose`: the current problem, with a number or a symptom; the user's words if any}. {requirement id R-n and UC-XXX, from `covers_requirements` and `covers_uc`}

**Before / After** (from `before_after[]`; logic tasks only)

| Aspect | Before | After |
|---|---|---|
| {what the user sees or the data written} | {today} | {when done} |

**Changed logic** (from `logic[]`; logic tasks only)

1. {numbered step; a branch is written "if … then …"; a constant with its reason and source}

**Chosen approach and reason.** {from `approach.chosen`}. Why: {`approach.why`}. Given up: {`approach.cost`}. (logic tasks only)

**Rejected alternatives** (from `alternatives_rejected[]`; logic tasks only)

- {option B} — {why not}

**How it is checked**

Criteria: AC-1 {…}

| Id | Scenario | Expected | Layer | Kind |
|---|---|---|---|---|
| TC-W1-T1-1 | {reproduce exactly this bug} | {observable} | `{layer}` | `{kind}` |

Touches: `{logic · api · shape · screen · input · state}` (from `touches`). Layer waived: {layer} because {reason} — `{file:line}` (from `layer_waivers`; omit when none).

No `{kind}` case because {reason} — `{file:line}`.

Check: `{exact command}` — passes when {condition}.

**New user-visible rules** (from `user_visible_rules[]`; omit this item when none)

| Rule | AC holding it |
|---|---|
| {rule} | {UC-XXX/AC-N} |

**Risks and open points** (from `risks[]`; omit this item when none)

- {risk, with the `specs/_debt.md` id, open-question id or user decision}

**Steps**

<!-- Each line n.m is step steps[m] of the task in plan.yaml, written by planner from that step: file — behaviour change — why. Before/after code and commands live only in the task file. The wave commit rebuilds this block from the task file after the user approves the wave: `[x]` for a step with `done: true`, `[ ]` with `— not done: {reason}` for the rest, and the word `done`. -->
- [ ] 1.1 `src/...` — {what changes} — {why}

Review focus (≈{N} min): {the specific place to look at closely}
If it breaks, turn back: {mandatory for a hotfix. Example: `git revert <sha>` then `pm2 reload <app>`.}

<!-- **Result** — this block is built by the wave commit from the task's `result` in plan.yaml after the user approves the wave; planner does not write it and leaves the line below as a comment. Each task with a non-null `result` gets one block, rebuilt whole each time (refs/closeout.md § The result in the mirror). Text in the reply language; codes, paths, commands, shas, AC and TC ids, `file:line` evidence stay as written. -->
<!-- **Result** -->
<!-- - **What was done** — {from `summary`} -->
<!-- - **Real changes** — {from `changes[]`: what · where · impact · gain · cost; logic tasks only} -->
<!-- - **Against the plan** — {from `deviations` and steps with `done: false`; "as planned" when none} -->
<!-- - **Criteria met** — {from `ac_check[]`: AC-n · met or not · evidence · TC id} -->
<!-- - **Tests run** — {from `commands[]`: command · exit code · TC id} -->
<!-- - **Left over** — {from `deviations`, `specs/_debt.md` ids, review finding ids; omit when none} -->
<!-- - **Commit** — {from `commits`} -->

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
