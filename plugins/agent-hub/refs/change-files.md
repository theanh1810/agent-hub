# Change files — what a brainstorm's change carries
<Owner: SDD.md § 3. Folder layout>
<Read when: writing, reading or closing a change's files; any pointer that names a change file, its location, its language, the AC id form or an archive name.>

---

Decisions carried out: the change files follow the OpenSpec file shape with the planner kept; all three are English for the agents to read, with one translated mirror file in the reply language; the OpenSpec bridge is deleted; the mirror is the planner's `plan.<lang>.md`.

## Files

| File | Writer | Language | Made from |
|---|---|---|---|
| `proposal.md` | brainstorm | English | `templates/analysis/proposal-template.md` |
| `design.md` | brainstorm | English | `templates/analysis/design-template.md` |
| `specs/<context>/spec.md`, the spec delta | brainstorm | English | `templates/spec/spec-delta-template.md` |
| the machine record | brainstorm | English | `design.yaml` in the change folder, `docs/brainstorm/{slug}.yaml` until `change-design` assigns the id (`refs/roles/brainstorm/modes.md § change-design`) |
| the plan files and `plan.<lang>.md` | planner | English; `plan.<lang>.md` in the reply language (`core.md` §1), absent for `en` | `refs/plan-files.md`, unchanged |

Location: the change folder `{plan_dir}` = `docs/changes/{plan_id}/`, in every workspace; a workspace with `docs/specs/` and `spec_required` adds `specs/<context>/spec.md` there, any other keeps `proposal.md` and `design.md` only (no `specs/`). Written when complexity is medium or higher, or `approval_required` is set (`agents/brainstorm.md § Artifact layout`). Read the template first, never write from memory.

## Order

1. propose — brainstorm, fresh: `proposal.md` and a `design.md` draft, shown at the approval gate.
2. design — brainstorm `mode=change-design`: `design.md` final, the spec deltas and `change_design`.
3. plan — planner.
4. apply — implement, review, test.
5. archive — brainstorm at closeout step 4 (`SDD.md §3.1`).

## Language

The three change files are English; `plan.<lang>.md` is the one file in the reply language (`core.md` §1), skipped for `en`; `user_questions[]` and what lands in the live UC at close are in the reply language (`SDD.md §3.1`).

## AC ids

One form: `UC-XXX/AC-N`, no spaces (readers still accept `UC-XXX / AC-N` in existing labels; new ones are unspaced).

## Validation

`agent-hub check plan` checks the change files with `chk_spec_delta` (the delta form of `templates/spec/spec-delta-template.md`) and `chk_placeholders` (template leftovers); no other validator runs on them.

## Archive

A closed change moves whole to `docs/changes/archive/{YYYY-MM-DD}-{plan_id}/`, dated when the archive runs; one already named `{plan_id}` keeps that name. Nothing in an archive is edited again.

## Legacy

- A change folder holding `deltas/` (the UC-delta form) closes by the legacy branch of `SDD.md §3.1`.
- A change folder still at `docs/specs/changes/{plan_id}/`, or its proposal and design in a legacy analysis folder, is read where it is and never recreated (`refs/plan-files.md § Legacy layouts`).
- Past legacy analysis files are history and are not migrated.
- No OpenSpec backend, command line or `docs/specs/openspec/` tree exists any more; a pointer to one is stale.
