# Spec layer procedure — bug class A or B, raise-only, spec modes, closeout inputs
<Owner: agents/brainstorm.md>
<Read when: `spec_required` is true, the class is a bug, a `/spec` command routed a write here, or test returned `ac_coverage[]` before archive>

---

The spec form, the class playbook, the escalation nets and the scope list are `rules/SDD.md`; the files and the close are `refs/plan-lane.md`; the delta shape is `templates/spec/spec-delta-template.md`. Brainstorm classifies; `rules/SDD.md § 10` decides what the class owes. None of it is repeated here.

## Bug A or B

Decided after the root cause (`rules/SDD.md § 10.1`). Spec clear and the code differs: A, fix the code, add a regression test on the existing scenario, leave the spec alone. Spec ambiguous, silent or absent: B, ask the user what the rule should be (`needs_user_input`), write the scenario into the delta, then route. Never fix with a self-chosen rule; a hotfix is not blocked by spec writing.

## Raise only

`spec_required` at task start is a guess. After the dependency trace raise it on a shared symbol, contract, route, schema, socket event or a `rules/SDD.md § 11.1` pattern; record `spec_required_escalated_from` and `escalation_reason`. Never lower it.

## A module outside `modules_in_scope[]`

Ask once per module: bring into scope · work without spec · record the debt. Write the choice into "Not yet specified" in `openspec/scope.md`. A hotfix takes the debt option.

## The spec modes

Detection and questions ran on main thread (`commands/spec.md`); these are writes only. A missing input returns `needs_user_input`. Paths: `refs/plan-lane.md § Where the files live`.

- **`reverse-engineer`** (input `scope`: one module path). Build glossary terms from the schema (`TODO: verify` on an opaque column), then requirements and scenarios from controllers, logs and the UI flow, in OpenSpec form, tagged unverified until the user confirms. Write only that module.
- **`spec-debt`.** Reconcile the unticked lines of `openspec/_debt.md` against the code; tick a line only after the user confirms the rule and it is written into a delta. Return the lines needing an answer.
- **`spec-init`** (input: repo kind → `scope: full|partial`, modules chosen → `modules_in_scope[]`, hot modules with 6-month commit counts). Run the init command of `rules/SDD.md § 3`; write `openspec/scope.md` with the adoption block and the "Not yet specified" list pre-filled with the hot modules not chosen; write an empty `openspec/_debt.md`. Create no requirement.
- **`spec-scope`** (input: modules picked). Edit `openspec/scope.md` only: add them to `modules_in_scope[]`, delete their lines from "Not yet specified". Never touch `sdd_adopted`: moving it rewrites every metric. The user picks modules; brainstorm never does, since the list sets the measurement denominator.

## Closeout inputs

Brainstorm writes from these returns:

| Input | From | What brainstorm writes |
|---|---|---|
| `blocked_needs_spec` + `spec_question` | implement (gates.md table A), after the user's answer | the rule as a requirement or scenario in a delta under the change |
| `ac_coverage[]` | test | the coverage note per scenario; one with no test stays visibly uncovered |
| `reason: spec_required_escalation` (implement) or `spec_required_misclassified` (reviewer) | implement or reviewer | a line in `design.md ## Decisions` saying the run needed a spec it lacked |
| repaid `_debt.md` lines | implement's handoff (`## Changes / Plan`), read in `mode=spec-debt` | tick only after the user confirms the rule |

A rule the user has not confirmed is not written: `needs_user_input` with that one question; closeout waits.

## spec-only draft

`/spec new <name>` spawns brainstorm with `spec_only: true`. Brainstorm writes `openspec/changes/spec-<name>/proposal.md` and the spec delta only: no `tasks.md`, no `plan.vi.md`, so `agent-hub check plan` does not run. It runs `openspec validate spec-<name> --strict`, and returns `awaiting_user_choice` with the requirement text. Main thread shows the requirement and asks "Add to the live specs?"; on yes main thread runs `openspec archive spec-<name> --yes`; on no the change folder stays as a draft.
