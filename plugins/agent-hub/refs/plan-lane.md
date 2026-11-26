# Plan lane
<Owner: agents/brainstorm.md>
<Read when: brainstorm writes or amends a plan (`mode=plan-write`, `spec-convert`), a worker reads one task, main thread checks or stamps a plan, or a change closes>

---

The plan of an L3 change is an OpenSpec change folder plus one Vietnamese document. Brainstorm writes it; machines check it; the user approves it at the plan gate (`refs/gates.md`). No reviewer reads a plan, and no second copy of any file exists.

## Where the files live

Every file below sits in the change folder `openspec/changes/<change>/`; OpenSpec ignores the extra files (`plan.vi.md`, `approval.md`, `errors.yaml`, `questions.md`, `review.md`, `reviews/`, `design.yaml`, `diagrams/`). `openspec new change <change>` creates `.openspec.yaml` (and at times a `README.md`); a change with no behaviour delta sets `skip_specs: true` in `.openspec.yaml`, every other change holds at least one delta. Every `openspec` command runs with `OPENSPEC_TELEMETRY=0` in its environment. Code keeps each location in one named constant in `scripts/plan_paths.py`; this section is the only place text states them, and every other file points here.

| File | Language | Writer | Holds |
|---|---|---|---|
| `proposal.md` | English | brainstorm | `## Why`, `## What Changes`, `## Impact` (`templates/analysis/proposal-template.md`) |
| `design.md` | English | brainstorm | `## Context`, `## Goals / Non-Goals`, `## Decisions`, `## Risks / Trade-offs` (`templates/analysis/design-template.md`) |
| `tasks.md` | English | brainstorm; implement ticks boxes | the tasks (§ tasks.md shape) |
| `specs/<capability>/spec.md` | English | brainstorm | the spec delta (`templates/spec/spec-delta-template.md`) |
| `plan.vi.md` | Vietnamese | brainstorm | the plan the user reads (§ plan.vi.md) |
| `approval.md` | English | main thread, by `agent-hub stamp plan` | stamp and the user's words |
| `errors.yaml`, `questions.md`, `review.md`, `reviews/annex-<n>.md` | English | per `refs/roles/brainstorm/error-batch.md`, `refs/roles/brainstorm/intake.md`, the reviewer and test, main thread | rounds, open questions, review rounds, second-opinion annexes |
| `design.yaml` | English | brainstorm | machine record |
| `diagrams/<n>-<slug>.html` | Vietnamese labels | brainstorm; implement at closeout | the flow drawing (`refs/diagram.md`) |

Outside the change folder: live specs `openspec/specs/<capability>/spec.md`; glossary `openspec/glossary.md`; spec debt `openspec/_debt.md`; the scope list `openspec/scope.md` (§ Spec debt names its use). A workspace without `openspec/` keeps `docs/glossary.md` and `docs/spec-debt.md`.

Living files are edited in place. Never add a `.bak`, a version copy or an `amendment_*` block.

## tasks.md shape

Start from `templates/plan/tasks-template.md`. Group tasks under `## Wave <n>`. Each task is one checkbox line followed by four indented lines:

```
- [ ] 1.2 <title>
  Files: <comma-separated exact paths>
  Covers: <comma-separated scenario names, or none>
  Done when: <the observable acceptance>
  Test: <layer: unit | integration | contract | e2e | security | script>
```

- Task id = `<wave>.<n>`. Use `Covers: none` only for a task with no behaviour (config, docs).
- `Test:` names one or more of those layers, comma-separated; which layers a task needs: `refs/roles/test/cases.md § Layers by what the task touches`.
- `Files:` is the scope: implement edits no other file (`refs/roles/implement/sources.md`).
- Put nothing else in `tasks.md`. Before/after code, step lists and test cases are not plan content: implement and test derive them from the task and the scenarios.
- The pass-2 `flows:` and a bug's `causal_chain[]` and `affected_surfaces[]` live in the machine record `design.yaml` (`refs/roles/brainstorm/modes.md § plan-write`), read by test and reviewer.
- OpenSpec does not parse the four keys; `agent-hub check plan` does.
- One concern per task; at most 5 files; two tasks naming one file go in different waves.
- A task whose `Covers:` is not `none` names scenarios that exist in a delta under `specs/` or in the live specs.

## plan.vi.md

This file is Vietnamese and richer than `tasks.md`; it is not a mirror of it. The user reads it at the plan gate, so write it to be understood without the other files. Start from `templates/plan/plan.vi-template.md`.

One block per task, headed `### <n>.<m> <tiêu đề>`, in the task-id order of `tasks.md`. Each block holds: what will be done and why, before and after in words, the files touched, how it is tested (each `acceptance[]` example of the task in words: given, when, then), the risks, what stays out of scope. Each block ends with the heading `#### Dữ liệu và màn hình bị ảnh hưởng`, listing tables, columns, stored files, API fields and screens the task changes; write `Không có` when none.

Use the project glossary's terms. Keep field names, endpoints, statuses and file names in English.

Above the first task block, one line `Bản vẽ: <path>`, `Bản vẽ: không có luồng thay đổi — <lý do>` or `Bản vẽ: bỏ qua — <lý do>` (`refs/diagram.md`).

## Checks before the gate

Machines only; nobody reads the plan before they pass. Brainstorm runs one command before returning the plan (`refs/roles/brainstorm/modes.md`), and main thread runs it again before asking the gate:

`agent-hub check plan <change-dir>`

It runs `openspec validate <change> --strict` when the `openspec` binary is on PATH (otherwise it prints `openspec: not installed, validate skipped (owed)` and goes on), then five checks:

1. every task has `Files:`, `Covers:`, `Done when:` and `Test:`;
2. every `Covers:` scenario exists in the deltas or the live specs;
3. every task id appears in `plan.vi.md` and no id there is missing from `tasks.md`;
4. the approval stamp is current: before the gate an absent stamp prints `PENDING 4 not stamped yet (pending)` and a stale one `PENDING 4 stamp <old> is stale (now <new>): re-approval pending`, and neither fails; with `--stamped` (main thread before each wave; the last implement spawn in closeout step 2) an absent or stale stamp fails;
5. every task block of `plan.vi.md` holds the `#### Dữ liệu và màn hình bị ảnh hưởng` heading.

A FAIL goes back to brainstorm, which fixes the named file and runs the command again. Never edit a check to pass. The section closes with the command `agent-hub check plan <change-dir>` and its pass line `plan-check: 4/4 passed, stamp pending` before the gate (`plan-check: 5/5 passed` once stamped), exit 0.

## Approval stamp

Scope only. After the user's `Approve` at the plan gate, main thread runs `agent-hub stamp plan <change-dir> --words <file>` with the user's words saved verbatim in the file. The stamp is the first 12 hex of a sha256 over the sorted `(task id, Files)` pairs and the bytes of `specs/**` under the change, sorted by path. `approval.md` holds `stamp: <12 hex>` and the user's words under `## User's words`.

Rewording `design.md` or `plan.vi.md` keeps the stamp valid. A new or removed task, a changed `Files:` list or a changed delta breaks it: the plan returns to the gate, and an `Approve` there is stamped again with the user's new words; `approval.md` keeps each earlier stamp and its words under `## Earlier approvals`. Hedged words are no approval (`refs/gates.md`).

## Close

At closeout, after the user's `Approve` at the final gate and never before (`refs/closeout.md` step 4), main thread runs `openspec archive <change> --yes` once, and only when every task box in `tasks.md` is ticked (`openspec list --json`: `completedTasks == totalTasks`), because `--yes` does not check it and the command needs `--yes` to run non-interactively. It merges the deltas into `openspec/specs/` and moves the folder, extra files included, to `openspec/changes/archive/<YYYY-MM-DD>-<change>/`; a change name cannot be archived twice on one day. Archive does not commit. Fix rounds write into the change folder until then. After archiving, nothing in the archive is edited.

## Old open plans

This version reads no plan of the old format (the single yaml plan, its per-task yaml, its language mirror). When work resumes on such a change, brainstorm writes it anew in this format from the request, the old `proposal.md` and `design.md` as background, and the code as it is. The user approves it at the plan gate. Nothing is converted; the old folder stays as history.

## Spec debt

One file, `openspec/_debt.md`: a hotfix that applied a business rule the spec does not state logs one line there; brainstorm repays it. Entry shape and the 24-hour rule: `rules/SDD.md § 10.2`. A repaid line is ticked only after the user confirms the rule; closeout step 4 checks it (`refs/closeout.md`).

## Additions from other packs

Slice vertically across waves, so each wave ends testable end to end; inside one wave tasks stay file-disjoint.

<!-- vendored:begin id=as-n10 src=addyosmani/agent-skills@39b723ceebf81474d0557c1fecd01eddab585563:skills/planning-and-task-breakdown/SKILL.md#L57-L77 licence=MIT -->
### Step 3: Slice Vertically

Instead of building all the database, then all the API, then all the UI — build one complete feature path at a time:

**Bad (horizontal slicing):**
```
Task 1: Build entire database schema
Task 2: Build all API endpoints
Task 3: Build all UI components
Task 4: Connect everything
```

**Good (vertical slicing):**
```
Task 1: User can create an account (schema + API + UI for registration)
Task 2: User can log in (auth schema + API + UI for login)
Task 3: User can create a task (task schema + API + UI for creation)
Task 4: User can view task list (query + API + UI for list view)
```

Each vertical slice delivers working, testable functionality.
<!-- vendored:end id=as-n10 -->
