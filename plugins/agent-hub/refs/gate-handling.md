# Gate handling

Tier 3 of `rules/core.md` §2.1 — the tables of every blocking `status` a worker can return and what main thread does, then the booleans that add a wave; core keeps one pointer.
Read when: a worker returns a `status` or a `needs_*` flag, before acting on it.

**A. Blocking `status` — spawn nothing else until resolved.** Every blocking value any agent can return is listed; `completed` and devops's `in_progress` block nothing. A blocking status with no row is a bug in this table, not licence to improvise.

| Status | Returned by | Main thread does |
|---|---|---|
| `needs_user_input` | brainstorm · designer · devops · implement · planner · reviewer · test | `AskUserQuestion` with `user_questions[]` → re-spawn `mode=clarify-followup` + `user_answers[]` |
| `awaiting_user_choice` | brainstorm | surface `candidates[]` + `recommended_candidate` → re-invoke orchestrator with `chosen_candidate_id`; it routes to `brainstorm mode=change-design`, then `planner` |
| `needs_design` | brainstorm | spawn `agent-hub:designer` → re-spawn brainstorm `mode=design-followup` |
| `needs_more_context` | designer | hand over the named artifact (analysis ref, AC, screenshot) → re-spawn designer; never let it proceed on a guess |
| `needs_revision` | brainstorm · devops · implement · planner · reviewer · scout · test | the input was wrong, not the agent's work. `reason` names the artifact: a step (`step_anchor_mismatch`, `plan_internal_conflict`, `plan_missing_test_cases`) → `brainstorm mode=error-batch`, `round_source: plan-gap`; `devops_op_not_simple` → re-spawn base `devops` on opus without `devops_op_class`; plan scope or logic before the plan gate → `brainstorm mode=change-design`, then `planner`; after approval `plan_change_required` → `brainstorm mode=error-batch` (`refs/roles/brainstorm/error-batch.md`), a mid-run user change → pending for the final gate; an approved plan never returns to `planner`; analysis → `brainstorm` (`change_design_missing` / `change_design_incomplete` → `mode=change-design`, amending only the named task and field); scan brief → `brainstorm`; design brief → `designer`. Route to **the agent that produced that artifact**; never re-spawn the reporter with the same input |
| `in_progress` | brainstorm · designer · implement · planner · reviewer · test | unfinished work, a turn cap not a verdict. Resume from the checkpoint ≤2 times, each with `done` grown, else ask the user. `brainstorm` with `effort_rise_requested: true`: re-spawn one rung up per `refs/effort-routing.md` § Picking the cell step 6, `effort_rises` + 1, same mode, ≤2 rises, then `AskUserQuestion`. `test`: `task_id`, `resume: true`, `remaining_test_case_ids[]`. `implement`: its `remaining_task_ids[]`, same wave. Nothing downstream until it returns. Not an error loop (`refs/turn-budget.md`) |
| `blocked_needs_spec` | implement | a business rule exists in no AC. Spawn `agent-hub:brainstorm` to draft the AC (it asks the user); no code until it exists. Exception: `hotfix` records `specs/_debt.md` and continues (SDD §10.2) |
| `needs_design_clarification` | designer · implement | the pixel/behaviour loop hit its cap of 2. Spawn `agent-hub:designer` with the exact question; if it already answered once, ask the user; a third pass is forbidden |
| `needs_approval` | devops | surface the change, blast radius and named rollback path via `AskUserQuestion`; re-spawn devops **only** on approval, which never carries to the next step |
| `needs_user_decision` | orchestrator | error-loop cap reached (brainstorm's error-batch returned `cap_reached: true`, `refs/roles/brainstorm/error-batch.md`; `agents/orchestrator.md` § Error-loop control). Surface `errors.yaml` + `fix_list` history with options at counter 2: roll back · accept partial · one extra fix round by the user's consent · widen scope (that same extra round with a wider `files[]`); at counter 3 only roll back · accept partial. **A third loop only by consent, never a fourth**. After the final gate's one `Request changes` round turns red: roll back that round · accept partial · a new plan |
| `failed` | any | no blind retry. Report the agent's stated reason under `Risk` and ask; a retry needs a changed input |

**B. Booleans — these add a wave, they do not stop one.** Several can be true at once.

| Flag | Set by | Effect |
|---|---|---|
| `needs_devops` | brainstorm · designer · implement · planner · test | one `devops` wave for that step (a read-only log fetch included), then re-spawn the asking agent with devops's output **verbatim** (`test` with `resume: true` when it stopped on 3 hung cases) |
| `needs_design` | brainstorm | a `designer` wave before `planner` |
| `needs_followup` | orchestrator | re-invoke orchestrator after this wave instead of emitting the §12 final |
| `approval_required` | brainstorm | the approval gate is on for this task |
| `recommend_scan[]` non-empty | brainstorm | one scout wave, one scout per entry, then re-spawn brainstorm with `scout_results_refs[]` |
| `needs_repro` | brainstorm | one `test` wave `mode=script` running `repro_request`, then re-spawn brainstorm with its output **verbatim** |
| `codex_second_opinion[]` non-empty | reviewer | one `codex:codex-rescue` spawn by main thread when Codex is ready (each run passes the permission prompt; declined or unready never blocks), then the same reviewer re-spawned with `codex_opinions[]` verbatim |
| `codex_review_request` non-null | reviewer `mode=independent`, round 0 only | one read-only `codex:codex-rescue` spawn by main thread with the file at `brief_path` as its prompt (each run passes the permission prompt; a declined prompt or unready Codex never blocks), then the same reviewer re-spawned with `codex_review_opinion` verbatim or `codex_review_skipped: <reason>`; only that re-spawn's verdict is routed (`agents/reviewer.md` § Codex diff review) |

Reviewer's `verdict` (`pass` · `needs_changes` · `blocking`) is a separate vocabulary, not a status. `needs_changes` and `blocking` go to one `brainstorm` error-batch, never straight to `implement`; they leave the MR open and never reach this table.
