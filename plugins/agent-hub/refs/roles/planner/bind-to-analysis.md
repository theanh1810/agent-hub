# Bind to the analysis

<Owner: agents/planner.md § References>
<Read when: Workflow step 2, `analysis_ref` non-null. With no analysis handoff § Gates has already sent the task back.>

---

**The plan executes brainstorm's approved decision; it never re-opens it.** Every field below flows through; detail (waves, steps, cases) is planner's, decisions are not.

| From the analysis | Into the plan | Rule |
|---|---|---|
| `change_design.chosen_candidate` | `recommended_approach` | settled, decomposition included |
| `change_design.plan` | the plan files per `refs/plan-files.md`; `plan.<lang>.md` renders it | keys copied verbatim; each task's `files[]`, `solution`, `before_after`, `logic`, `approach`, `alternatives_rejected`, `user_visible_rules`, `risks`, `acceptance_criteria`, `depends_on` unchanged; planner adds waves, `steps[]`, `test_cases[]`, `verification`, `plan_metrics` |
| a task's `test_plan` | its `test_cases[]` | ≥1 case per line, of the layers and kinds it names; the key itself is not copied |
| `root_cause_or_mechanism` | `root_cause` (lite) · `objective` + `tldr` (full) | carried with its `file:line` |
| `binding_scope.files_allowed[]` / `symbols_allowed[]` | union of `files[].path` over every task record | a **ceiling**: fewer files, never more |
| `binding_scope.files_forbidden[]` | — | no task names one |
| `needs_devops: true` | the `devops` wave `change_design` carries, with rollback | checked, not added; missing is `needs_revision`, `change_design_incomplete`; never absorbed into an implement task |
| `spec_required`, `uc_ids[]`, `ac_ids[]` | `covers_uc`, `covers_acceptance` | each AC id resolves in the live UC or the change's spec delta; mint none |
| `bug_spec_class: B` | — | rule unsettled; do not plan on a guess |
| `design_brief_ref` | every UI task | pattern, screens, tokens stay in `DESIGN.md`; the task carries the ref, never a copy |
| `open_questions[]` | `assumptions[]` or `user_questions[]` | never vanishes unmentioned |
| project-wide constraints (minimum versions, dependency limits, naming and copy rules, platforms) | `confirmed_values`, once, spec values verbatim with `file:line` | every task inherits them: "Every task's requirements implicitly include this section." |

**Deviating is not planner's call.** A task that cannot be detailed as written (missing field, over the ceiling, unbacked edge, logic its files do not bear out) is `needs_revision`, `reason: change_design_incomplete`, naming task and field.

**Thin analysis.** Missing `change_design`, `binding_scope` or root cause → row 1 of the Gates of `agents/planner.md`. Report the gap through that row for brainstorm to supply, and never fill it from production source.

| Rationalization | Reality |
|---|---|
| "My approach is cleaner than the approved one" | The user approved brainstorm's; deviations stay empty. |
| "One extra file makes this simpler" | The file list is a ceiling; ask brainstorm. |
