# Routing decision contract — shape choice, spawn fields, emission rules
<Owner: agents/orchestrator.md § Output>
<Read when: filling either routing shape; deriving `spec_required`, `thinking_mode`, a gate-pending note (`plan_gate_pending`, `final_gate_pending`) or a `workflow` variant value>

---

## Single-wave vs Full-DAG (HARD)

First matching line wins; never weigh two lines.

| # | Condition | Shape |
|---|---|---|
| 1 | A gate is pending — clarify, approval, design or plan review | **single-wave** |
| 2 | An error-loop fix cycle | **single-wave** |
| 3 | `{plan_dir}/plan.yaml` exists and is approved | **full-DAG** |
| 4 | A brainstorm run returned with `binding_scope` set | **full-DAG** |
| 5 | Anything else, including a pipeline that looks obvious end to end | **single-wave** |

Line 5 is the conservative tie-break: a DAG emitted before brainstorm bounds the scope guesses which files exist and every later wave inherits the guess; one extra orchestrator call costs one sonnet call.

Full-DAG emits every remaining wave once; main runs them in dependency order without re-invoking.

**Re-invoke only on:** test/build/lint failure (error loop) · a brainstorm gate status · reviewer `blocking` or `needs_changes` · a mid-run user change (recorded as pending, the plan continues) or `plan_change_required` (`brainstorm mode=error-batch`), never `planner`.

## Routing rules for brainstorm and scout

- `brainstorm` is the only pre-plan worker; `scan` is `scout`'s only mode. Brainstorm reads no source beyond lines a scout result cites.
- A non-empty `recommend_scan[]` → `scout mode=scan`, one per entry, then `brainstorm` again with `scout_results_refs[]`: the only way `scout` is spawned. Each scout brief copies `sub_question`, `file_shortlist[]`, `out_of_scope[]`, `patterns[]`, `doc_sources[]`, `scan_round` from the entry; `task_id` is brainstorm's; `analysis_ref` the resolved brainstorm machine record; `prior_scan_refs[]` the earlier rounds' `scout_results_refs[]`. The entry's `objective` is brainstorm-side, not sent.
- `scout` REQUIRES `sub_question` + `file_shortlist[]` + `out_of_scope[]` + `analysis_ref` (a docs-only scan: `file_shortlist: []` and non-empty `doc_sources[]`). Missing any → invalid spawn; route through a full brainstorm run first.
- Run the synthesising brainstorm in a later wave than the scan wave; a scan wave never shares a wave with it.
- `brainstorm` runs before `planner` for non-trivial work: it writes the `change_design`; planner details it and sends back one it cannot detail.
- `designer` only after brainstorm `needs_design`, in its own wave, then `brainstorm mode=design-followup`. FE/UI only.

## Skill routing

- User instructions outrank skills, and skills outrank default behaviour; skip a skill's process only when the user says so.
- A skill triggers on a clear match only; a suggestion skill speaks up only on a strong intent match, and a hedged match stays silent.
- A heavy interactive skill (interview, critique, standard-setting) never runs where no human can answer (CI, schedule, loop); report the block and the skipped step.
- A full pre-release review issues all specialist agent calls in one turn, in parallel; main thread merges them into a go/no-go with a rollback plan.

## Workflow values

`bug (small)`, `feature (small ≤6 files)` and `plan-only` are row spellings of `bug`, `feature` and `docs`, not classes; emitting the bare class is always correct. `tools/check ruleset (package repo only)` fails when a routing row's class is not a legal `workflow` value.

## Rules

### Spawn fields

- `agent`, `model`, `effort`, `tier` come from `refs/effort-routing.md` at the spawn's tier; main passes `model` to `Agent(model)` and spawns `agent` as written. No tier → L2. A cell outside the matrix is blocked, except the devops-low spawn that file admits.
- `spec_required` is on **every** spawn with `spec_required_source`; derive from the class (`refs/roles/orchestrator/spec-routing.md`), **raise only, never lower**; an escalation applies to every remaining wave.
- `thinking_mode` is required for `brainstorm | planner | test`: `simple|hotfix|bug → quick`; `feature|medium|infra → standard`; `complex|refactor → extended`; a user cue ("analyse carefully", "think deeply", "deep analysis", "test thoroughly"; the same words in the reply language count) forces `extended`; `test` on payment, auth, permissions, money or legal flows is `extended` whatever the class. For `test` it sets how deep each case goes, never which run. Other agents: `null`.
- `depends_on` orders spawns; empty means parallel ("Dispatch one agent per independent problem domain."). A plan wave is one `implement` spawn carrying that wave's `task_ids[]`; waves chain by `depends_on`. With no plan, implement, test and devops spawns run one at a time.
- No parallel split when failures are related, need the whole system in view, or edit the same file or resource: investigate together first.
- `brief` content: `refs/roles/orchestrator/dispatch.md`.

### Gate-pending notes and summary

- `next_spawns[]` empty and no gate pending → orchestrator writes the Vietnamese final summary; with a gate note or `run_mode: ultracode_offer`, `post_spawn.summary_owner: main_thread` and main asks.
- brainstorm `needs_user_input` → empty `next_spawns[]`, note `clarify_gate_pending`; after answers re-emit `[brainstorm]` `mode=clarify-followup` + `user_answers[]`.
- brainstorm `awaiting_user_choice` → empty, note `approval_gate_pending`; the pick returns as `chosen_candidate_id`, next `brainstorm mode=change-design`, then `planner`.
- brainstorm `needs_design` → `[designer]` with `design_brief_request{}`, then `[brainstorm]` `mode=design-followup` + `design_brief_ref`.
- `plan_gate_pending: true` after planner returns: main runs the plan-review gate before any `implement`. `final_gate_pending: true` once the review-and-test pass is green or partial-accepted: the final gate runs before any `wave_commit` spawn (`refs/roles/orchestrator/gates.md`).
- A spawn ending on a turn cap or watchdog hang is resumed per `refs/turn-budget.md`, never re-run, never an error loop.
