# Spec layer procedure — bug class A or B, raise-only, closeout inputs
<Owner: agents/brainstorm.md § References>
<Read when: `spec_required` is true, the class is a bug, a `/spec` command routed a write here, or closeout handed back `spec_delta[]` / `ac_coverage[]`>

---

Change files: `refs/change-files.md`; templates `templates/spec/`; rules `rules/SDD.md`. **Brainstorm classifies; the SDD.md class playbook decides what that class owes** (artifact, when due, who writes it); none of it is repeated here.

## Bug A or B

Decided in Phase 4, after the root cause.
- Spec clear and the code differs → **A**: fix the code, regression test on the existing AC, spec untouched.
- Spec ambiguous, silent or absent, or the rule unsettled → **B**: a clarify gate (`needs_user_input` asking what the rule should be), write the AC, then route. Never fix with a self-chosen rule. A hotfix is not blocked by spec writing.

## Raise only

`spec_required` at task start is a guess from the class. After Phase 4 raise it when the impact set touches a shared symbol, contract, route, schema, socket event or an SDD.md escalation pattern; record `spec_required_escalated_from` + `escalation_reason`. Never lower it.

## A module outside `modules_in_scope[]`

Neither add it nor skip spec silently. Ask once per module: bring into scope · work without spec · record the debt; write the choice into "Not yet specified" in `specs/README.md`. A hotfix always takes the debt option.

## Closeout inputs (step 4)

`implement` runs `closeout` but may not edit `specs/`; it hands brainstorm these and brainstorm writes:

| Input | From | What brainstorm writes |
|---|---|---|
| `spec_delta[]` | implement | the rule in the UC's own voice as a new or amended AC; bump `## History` with date and why |
| the delta at `docs/changes/{plan_id}/specs/<context>/spec.md` (a change opened before 2026-10-13 keeps `deltas/`) | brainstorm's `change-design` | merge it and archive the folder (order in `rules/SDD.md`) |
| `ac_coverage[]` | test | fill `### Test mapping`; an AC with no test stays visibly empty |
| `spec_required_escalation` | implement or reviewer | when the run needed a spec it lacked, say so in `## History`; never back-date the UC |
| repaid `specs/_debt.md` lines | implement's hotfix log | tick only after the user confirms the rule |

A `spec_delta` stating an unconfirmed business rule is not written: `needs_user_input` with that one question; closeout waits.
