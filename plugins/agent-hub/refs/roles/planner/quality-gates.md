# Quality gates — the rows tier 2 does not carry

<Owner: agents/planner.md § Quality gates>
<Read when: Workflow step 6, before emitting any file. Tier 2 carries the four gates that bound a task; these bound the plan around it.>

---

| Gate | Holds when |
|---|---|
| Coverage | every `requirements[]` entry maps to ≥1 task through `covers_requirements`, and every task but `closeout` names ≥1 (`agent-hub check plan` trace); every task has `acceptance_criteria`, `verification` and non-empty `test_cases` (`closeout` alone `[]`); every non-exempt task has, per kind its rows in `refs/roles/planner/test-cases.md § Kinds by task type` name, ≥1 case or a `case_kind_waivers` entry with `file:line`; every screen task covers each `screen_states` state in each theme with a case, or waives it with `file:line` (`refs/roles/planner/test-cases.md § Screen states`); a plan with a non-exempt implement task (`§ Exemptions`) carries one test task, `refs/roles/planner/dag.md § Cross-task journey`; every `change_design.business_rules[]` entry has, in each task its `task_ids` names, ≥1 case `polarity: valid` and ≥1 `polarity: violating` citing it in `rule_ref`, the violating set holding an API-direct case when the task changes a route or handler (`§ Business rules`); every contract has a producer and ≥1 consumer task |
| Spec | `spec_required: true` → every task carries `covers_uc`, every `covers_acceptance` is `UC-XXX/AC-N` naming one that exists in the live UC or the change's delta and that the task's criterion names after `→`; a refactor carries a characterization test in wave 1 |
| Design brief | with `design_brief_ref` in the input, every UI task carries it; without, the plan is invalid |
| Devops | a `devops` wave appears whenever brainstorm set `needs_devops`, rollback named |
| Thresholds | every threshold group the plan's checks read and the project's `docs/thresholds.yaml` has not approved is listed in `plan.<lang>.md` for the user to approve at the plan gate (`refs/thresholds.md`) |
| Scope | every row of `refs/roles/planner/bind-to-analysis.md` holds; the union of `files[].path` over all task records is a subset of `binding_scope.files_allowed[]` and meets `files_forbidden[]` nowhere |
| Self-contained task | every task record carries `steps[]` written from the live files, each `done: false`, an `expect` opening `exit N` or `rc=N` on every `run` step, every `before` occurring once when applied in wave order; no `solution` or `files[].why` matches `change_design\.`; every `acceptance_criteria` line starts `AC-n:`; no `verification` line repeats a `test_cases[].steps` line |

`agent-hub check plan {plan_dir}` measures every row a script can (task keys, file ceiling, review checkpoint, `AC-n:` and prefixed coverage, requirement trace, step shape, waves and `depends_on`, scope, anchors, mirror, `logic_task_fields`); its last line goes into the handoff; the rest are read.
