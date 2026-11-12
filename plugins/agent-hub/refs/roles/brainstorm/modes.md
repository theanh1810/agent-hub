# Non-default modes — reading, change-design, error-batch, spec modes, root cause
<Owner: agents/brainstorm.md § References>
<Read when: `mode` is anything but `fresh` or `clarify-followup`; a Phase 3-4 scan brief or a cited-line read starts in any mode; a bug is to be root-caused (§ Root cause)>

---

## Reading — scout reads, brainstorm confirms (HARD)

Scout does every search and every read of source for brainstorm, at any size, external documents and recon included (`refs/roles/brainstorm/research.md`).

- Brainstorm keeps what it reasons with: GitNexus `query` filtered to the shortlist, `context` on an in-scope symbol, `impact`, `api_impact`; a mem0 search narrowed to the focus area; its own records (`docs/brainstorm/`, the change folder), `specs/` and the plan; scout's research notes.
- Its one read of source is a confirmation: lines a scout result cites, at most **5 reads of 40 lines a run**, before a root cause or design decision rests on them.
- A cited line not saying what the result claims is a scout defect: a narrower `recommend_scan[]` at `scan_round`+1, never a wider read.
- Forbidden: Bash grep or find, a read no scout result cites, an unfiltered `route_map`, web search, Context7 and external fetch (scout's `doc_sources[]`); request any of these from scout through `recommend_scan[]` instead.

| Rationalization | Reality |
|---|---|
| "One quick grep saves a round" | Scout runs every search; brainstorm opens only cited lines |
| "The cited line is close enough" | A scout defect; re-scan narrower |

## The modes not tabulated at tier 2

| Mode | Trigger | Does | Returns |
|---|---|---|---|
| `error-batch` | `errors_path` present | records and analyses one round, emits fix entries into `errors.yaml` (`refs/roles/brainstorm/error-batch.md`) | `completed`, or `needs_user_input` on an out-of-plan fix |
| `reverse-engineer` | no `specs/` for the touched module, class needs one | SDD.md's reverse-engineering procedure, that module only | `needs_user_input` |
| `spec-debt` | `spec_debt_pending` | reconcile unticked `specs/_debt.md` lines against code | `needs_user_input` |
| `spec-init` | `/spec init`, after the user answered | build the `docs/specs/` skeleton: four directories, `README.md`, `_debt.md`; no UC | `completed` |
| `spec-scope` | `/spec scope` step 5 | widen `modules_in_scope[]` in `specs/README.md` | `completed` |

## Input fields

| Field | What it obliges |
|---|---|
| `spec_task` | set → author a spec document, not an analysis: read the template, clarify what is unstated, write into `specs/`. Too little for one AC → leave the UC in draft and list what is missing. Never invent an AC (it becomes a test, then an unapproved business rule) |
| `scope` | `reverse-engineer` only: the one module path |
| `escalation_source` | `error-batch` only: `"auditor"` narrows the run to the given `error_ids[]` |
| `chosen_candidate_id` | `change-design` only: the id picked at the approval gate; null when no gate fired (the single recommended candidate is designed) |

## change-design

The chosen candidate down to files, the logic of each change and tasks. **Brainstorm thinks; planner details.** Brainstorm owns cause, candidates, trade-offs, scope, acceptance criteria, Done, risks and writes no before/after; planner writes exact before/after, steps, waves and test cases and changes neither scope nor an acceptance criterion.

**When.** Whenever the route is `planner` (`agents/brainstorm.md` § Workflow step 6); never for brainstorm → implement. Also when planner returns `needs_revision` with `change_design_missing` or `change_design_incomplete`: amend only the task and field named, re-run plan-verify.

**Where.** `change_design:` goes into the machine record, its English reading copy into `design.md` (`refs/change-files.md`): same task ids, decisions and template sections only, never a task status. Change-design writes `proposal.md`, `design.md` and the record into the change folder `docs/changes/{plan_id}/` (record as `design.yaml`, no second copy) and, when it assigns the id, moves the inbox record `docs/brainstorm/{slug}.yaml` to `docs/changes/{plan_id}/design.yaml` and the files of `docs/brainstorm/{slug}/` beside it, one `mv` each, content unchanged; every new or changed AC, flow step (`3`, `2a`), exception (`E3`) and rename goes into the spec delta `specs/<context>/spec.md` (`templates/spec/spec-delta-template.md`), a changed block whole beside its old text, never the live UC.

```yaml
change_design:
  chosen_candidate: C1
  decision_checklist: [{id: DC-n, area, item, decision, source}]   # every area of § Decision checklist; plan-verify fails a missing area
  plan:            # plan-template.yaml's top-level keys but waves, plan_metrics and context_budget_breakdown, which planner derives
    objective, tldr, research_confidence, non_goals, assumptions, confirmed_values, user_actions, target_layout, requirements, affected_surfaces,
    recommended_approach, approach_variants, pre_mortem, contracts, deviations_from_analysis: [], tasks,
    validation_strategy, rollback_strategy, context_budget
    tasks:         # per task, task-template.yaml's keys but steps, test_cases, case_kind_waivers, verification and result, plus `subtasks` (default `[]`) and:
      - depends_on: [task ids]   # every edge cited in wave_order_evidence; two tasks naming one file are joined
        test_plan: {types: [], kinds: [], cases: ["what one case proves"], why: "the rows of test-cases.md by task type, and any kind added"}
  wave_order_evidence: the impact result, or the reference, behind each depends_on edge
  business_rules: [{id: RULE-n, text, surface, source, task_ids}]   # refs/business-rule-testing.md; [] + business_rules_reason when no product rule is touched
```

**Design decisions brainstorm owns** (never planner's): API shape and contract (versioning, error format), idempotency key, migration both directions, the decision record for a hard-to-reverse choice (an ADR in the project's ADR folder), module boundaries (invariants, ordering, error kinds, configuration, not only signatures), test seams and patterns (layout in `code-style/README.md`).

**Task split.**
- Default **vertical slices** through every layer end to end (data, logic and UI may share a task); contract-first-then-parallel is a deliberate exception.
- ≤3 files target, 5 the ceiling; two tasks naming one file are joined by `depends_on`; every edge has evidence (an `impact` result).
- Several independent subsystems in one scope: **one plan in parts** (a part is a group of waves), never several plans.
- `files[]` is the scope: planner adds and drops none. Every file traces to a user requirement; unrelated dead code is noted, never included. "Every changed line should trace directly to the user's request."
- `solution` is the logic file by file (which section, symbol or row changes, how, why), precise enough that the before/after follows from reading the file, never the before/after text and, like `files[].why`, never a pointer into the analysis.
- Every task fills `before_after` (behaviour per aspect, never code text) and `out_of_scope` (what it leaves alone, one line each). A task whose `touches` hold `screen`, `logic`, `api` or `state` (a logic task) also fills `logic`, `approach {chosen, why, cost}` and `alternatives_rejected`. Every task fills `user_visible_rules` as `[{rule, ac}]` and `risks`. A rule with no AC is a Clarify question first; `agent-hub check plan` fails an empty `ac`.

**Decision checklist (HARD)**. Before returning, `change_design` carries `decision_checklist: [{id: DC-n, area, item, decision, source}]` with ≥1 entry for each of seven areas:
- `copy`: every user-visible string.
- `screen_states`: per screen, `loading`, `empty`, `error`, `fallback`, `success`, `disabled`, and `selected`, `hover`, `focus` and light/dark where they exist, with the behaviour of each.
- `check_reach`: how far each check reaches, e.g. which roots an a11y scan gates.
- `out_of_scope`: what is deferred.
- `business_rules`.
- `irreversible` and `dependency`: the two remaining must-ask items of `CLAUDE.md` §0.2.

Each entry has a `decision` and a `source`: the `id` of a `user_decisions_verbatim[]` entry (each entry a mapping `{id: Qn, date, question, answer}`, the key `agent-hub check plan` decision_checklist reads), or a decision starting `none:` with its reason. An empty decision is a Clarify question asked before `change-design` returns.

**Acceptance and Done.**
- Each `acceptance_criteria` line starts `AC-n:`; one restating a spec AC ends `→ UC-XXX/AC-N`.
- `requirements[]` lists only what the user asked, `{id: R-n, text, source}`, source a `UC-XXX/AC-N`, the user's dated words or the `id` (`Qn`) of a `user_decisions_verbatim[]` entry, never brainstorm's idea. Every task but closeout names what it delivers in `covers_requirements`. Done = `requirements[]` plus `validation_strategy.final`.
- `validation_strategy` also carries `review_deep_paths: [{path, section|null, reason}]` (paths whose defect breaks other agents or user data: scripts, hooks, gate rules, deletions; from `impact` and `pre_mortem`) and `checkpoints: [{after_task_ids, reason, expected_red: [{check, owner_task, reason}]}]` (after a wave changing or deleting many files; `expected_red` only when a later task owns that red check). Both required from complexity `medium`; an empty list carries a one-line reason. Planner copies both into `plan.yaml`.
- `test_plan` sizes cases by task type (`refs/roles/planner/test-cases.md`): types, kinds, one line per case saying what it proves, and why. A task reaching no screen plans no screen case; a bug's first case is the failing reproduction. States of a screen are rows of 1-2 table cases; each behaviour at the lowest layer that catches it; no two cases on the same AC, layer and state (`refs/roles/planner/test-cases.md` § Lean cases). Planner writes each case whole.
- `pre_mortem`: what may break besides the target, where it shows, the rollback.
- **Also check**: a `design.md` section listing input kinds the spec implies but nobody tests (boundary values, empty or duplicated input, permissions, concurrency); each becomes a case or a stated reason it needs none.
- `business_rules`: every rule of each screen, API or flow the change reaches, by category (`refs/business-rule-testing.md`), each with a source; a rule with no source is a Clarify question, one decision, written to `user_decisions_verbatim[]` before listing. Each task in a rule's `task_ids` plans its valid and its violating case.
- `affected_surfaces`: `[{id: AS-n, surface, kind: user_facing|sibling_path|writer, task_ids: [], reason: null}]` or `N/A: <reason>`: every screen, route or message reached and every other code path writing the same table or state (via `impact` or scout), each with a task or a reason. Whether an auxiliary signal (a hint, a fingerprint) fails open or closed is asked, never assumed. For a defence (gate, rate limit, block) ask false-positive tolerance, the runtime-changeable threshold and the kill switch; record in `confirmed_values`.
- `confirmed_values` and `user_actions` come from `user_decisions_verbatim[]`; `target_layout` from files a task creates, moves or deletes; `interfaces` and `pattern_refs` from files scout read in Phase 4 pass 3. `tier` is the higher of the plan's phase-2 tier and its own score (`refs/effort-routing.md`).
- Debug logging when a bug cannot be pinned to a line: propose it in the design (file, what to log, remove-when); implement adds it.
- No code before/after, step, wave, test case, `verification` line or Vietnamese step line: planner's.

| Rule | Home |
|---|---|
| task size, wave rules | `agents/planner.md` § Workflow step 3, `skills/planning-dag` |
| test plan: types and kinds by task type | `refs/roles/planner/test-cases.md` |
| new test file paths and runner config; an old repo with no recorded layout is named as such and implement asks on its first test | `code-style/README.md` |
| dependencies from `impact`, contract consumers from `api_impact` | `skills/gitnexus-flow` |

**Before returning**, run `agent-hub check plan <resolved-analysis-record>` and clear every FAIL (task keys, file ceiling, review checkpoint, `AC-n:`, coverage, requirement trace, `depends_on` graph, scope); a user-granted ceiling exception goes in as `--ceiling-exception <task_id>`. Its last line goes into the handoff as `plan_verify`. A decision needing a user fact is a gate, one decision per question.

**Amendments.** Edit only the changed tasks' `plan` entries in `change_design`, in place, name their ids in the handoff; planner re-details them. Re-run plan-verify.

**Living files.** One file per thing, edited in place. Only two keys grow: `user_decisions_verbatim[]` gains the user's words, `changelog[]` one line `YYYY-MM-DD — what changed (task ids)`. No `amendment_*` or `revision_*` block, patch, `.bak` or version copy of a plan or analysis file under `docs/` (scratch in the scratchpad or `.cm-tmp/{task_id}/`). Finished execution steps and results live only in the task file.

**Large analysis files.** Over 2 000 lines, never read whole: load with `yaml.safe_load` and print only the blocks to change, e.g. `python3 -c 'import sys,yaml;c=yaml.safe_load(open(sys.argv[1]))["change_design"];[print(yaml.safe_dump([t for t in c["plan"]["tasks"] if t["id"]==k],allow_unicode=True,sort_keys=False)) for k in sys.argv[2:]]' {plan_dir}/design.yaml <task_id>…`; write changed blocks back the same way.

**Pass-2 flows** (`refs/roles/test/two-pass.md`). A design with a non-exempt implement task names the flows of the test task planner writes (`refs/roles/planner/dag.md`), or one `script` case when no task reaches a user. A task whose change reaches a user (a screen, or an API a user calls) carries one case per business flow of each UC in `covers_uc`: the main flow, each alternate flow and each exception, plus the delta's `## Flow Changes` and `## Exception Changes`. A flow no UC states is written in the user's terms in `design.md`, approved with the plan; on the `implement` route it goes under `flows:` in the record. Test runs only flows the UC or the approved design states; test never invents one.

## `error-batch`

Records and analyses one round of `errors.yaml` in one pass; `errors.yaml` is the fix contract. Procedure, entry shapes, counter and cap: `refs/roles/brainstorm/error-batch.md`.

## reverse-engineer, spec-init, spec-scope, spec-debt

- **reverse-engineer:** `rules/SDD.md` procedure, one module only. A spec built from code says what the code does, not whether it is right: user verification is mandatory, never treated as approved.
- **spec-init and spec-scope** are writes only: `commands/spec.md` already ran detection and `AskUserQuestion`; neither re-detects or re-asks; a missing input → `needs_user_input`.
  - `spec-init` (`commands/spec.md` init steps 2, 4, 5, 6). Input: the answer to Question 1 (repo kind → `scope: full|partial`), modules chosen in Question 2 (→ `modules_in_scope[]`), detected hot modules with 6-month commit counts. Writes `specs/business-requirements/`, `specs/use-cases/`, `specs/entities/`, `specs/diagrams/`; `specs/README.md` from `templates/spec/README-template.md` (adoption block filled, an empty index table, the "no spec yet" list pre-filled with the hot modules the user did not choose and their commit counts); `specs/_debt.md` from `_debt-template.md`. No UC.
  - `spec-scope` (`commands/spec.md` scope step 5). Input: modules picked in step 4. Writes `specs/README.md` only: add them to `modules_in_scope[]`, delete their lines from the "no spec yet" list. Never touch `sdd_adopted` or `naming_convention_from` (moving the date rewrites every metric since). The user picks the modules; brainstorm never does (it sets the measurement denominator).
- **spec-debt:** reconcile unticked `specs/_debt.md` lines against code; tick one only after the user confirms the rule (`agents/brainstorm.md` § Closeout step 4). Returns `needs_user_input` with the lines needing an answer.

## Root cause

The procedure lives in `refs/roles/brainstorm/root-cause.md`; read it before a bug is rooted.
