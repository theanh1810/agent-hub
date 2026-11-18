# Modes — reading, plan-write, error-batch, spec modes, root cause
<Owner: agents/brainstorm.md>
<Read when: `mode` is anything but `fresh` or `clarify-followup`; a scan brief or a cited-line read starts in any mode; a bug is to be root-caused (§ Root cause)>

---

The mode list and each mode's one-line meaning are in `agents/brainstorm.md`; this file holds, per mode, what it is given, what it writes and what it returns. The plan files are stated in `refs/plan-lane.md`, the spec form in `rules/SDD.md`: this file points there and does not restate them.

## Reading

Scout does every search and every read of source for brainstorm (`refs/roles/brainstorm/research.md`). Brainstorm keeps what it reasons with: GitNexus `query` filtered to the shortlist, `context`, `impact`, `api_impact`; a claude-mem search narrowed to the focus area; its own records, the specs and the plan; scout's notes.

- Its one read of source is a confirmation of a line a scout result cites: at most 5 reads of 40 lines a run, before a root cause or design decision rests on them.
- A cited line not saying what the result claims is a scout defect: a narrower `recommend_scan[]` at `scan_round`+1, never a wider read.
- Forbidden: Bash grep or find, a read no scout result cites, an unfiltered `route_map`, web search, Context7, external fetch. Ask scout through `recommend_scan[]` instead.

## plan-write

**When.** The user picked a candidate (`chosen_candidate_id`), or the route is L3 with no approval gate, or the user chose `Edit plan` at the plan gate. Never for a lane that has no plan (`refs/lanes.md`).

**Inputs.** The cited root cause, the chosen candidate with its scores, `binding_scope`, `user_decisions_verbatim[]`, the glossary, the live specs the change touches, and the scout results.

**Writes** (files and shapes: `refs/plan-lane.md`): `proposal.md`, `design.md`, `tasks.md`, the spec deltas, `plan.vi.md`, the flow drawing (`refs/diagram.md`), and the machine record `design.yaml`. When it assigns the change id, it moves the inbox record `docs/brainstorm/{slug}.yaml` and the files of `docs/brainstorm/{slug}/` into the change folder, one `mv` each, content unchanged. The record holds `flows:` (also written into `plan.vi.md`), `causal_chain[]` and `affected_surfaces[]`; test and reviewer read them there (`refs/roles/test/two-pass.md`).

**Decides, never leaves to implement:**
- task split: vertical slices through every layer, sized by `refs/plan-lane.md § tasks.md shape`; each wave edge backed by an `impact` result; independent subsystems are one plan in parts, never several plans;
- every `Files:` traces to a user requirement; unrelated dead code is noted, never included;
- every scenario a task covers, and a business rule paired valid and violating (`refs/business-rule-testing.md`);
- the decisions a user must make: copy, screen states, how far a check reaches, what is out of scope, anything irreversible, any dependency (`rules/core.md`, the must-ask list). A decision needing a user fact is a clarify question first, written to `user_decisions_verbatim[]` before it is relied on;
- the contract and migration decisions, the module boundaries, the test seams, each recorded in `design.md ## Decisions`;
- the pass-2 flows, written as `flows:` in `design.yaml` and in `plan.vi.md`: one per business flow of each requirement a user-facing task covers, or one `script` flow when no task reaches a user (`refs/roles/test/two-pass.md`).

**Test plan.** Name the test layer per task in `Test:` by `refs/roles/test/cases.md § Layers by what the task touches`; no two cases on the same scenario, layer and state; a bug's first case is the failing reproduction.

**Before returning:** run `agent-hub check plan <change-dir>` and clear every FAIL, then put its last line in the handoff as `plan_check` (`refs/plan-lane.md § Checks before the gate`).

**Amendments.** Edit only the changed tasks, in place, and name their ids in the handoff. Living files are never copied (`refs/plan-lane.md § Where the files live`).

**Returns.** `completed` with `plan_check`; `needs_user_input` when a user fact is missing; `needs_design` for a new screen, flow or component (`refs/lanes.md`).

## `error-batch`

Records and analyses one red round in one pass; `errors.yaml` is the fix contract. Triage of every review finding and every annex is the same pass. Inputs, entry shapes, counter and cap: `refs/roles/brainstorm/error-batch.md`. Returns `completed`, or `needs_user_input` on an out-of-plan fix.

## spec-convert

**When.** Work starts on a project with `docs/specs/**` and no `openspec/specs/`. **Inputs.** The approved UCs and BRs of the modules in scope. **Writes.** the init command of `rules/SDD.md § 3`, then each converted spec by hand with the mapping there (no bulk tool) as an ADDED delta in the change folder (path: `rules/SDD.md § 3`), never into the live `openspec/specs/`; `agent-hub check plan` must pass. **Returns.** `completed` with the converted specs listed for the plan gate, where the user approves them with the plan (the stamp hashes them); `openspec archive <change> --yes`, run by main thread after the final `Approve`, merges them into `openspec/specs/`, and on Cancel the change folder is discarded; `docs/specs/**` is not touched.

## reverse-engineer, spec-debt, spec-init, spec-scope

The write side of `commands/spec.md`: detection and `AskUserQuestion` already ran on main thread, so none of these re-detects or re-asks; a missing input returns `needs_user_input`. Procedure and inputs: `refs/roles/brainstorm/spec-layer.md`.

| Mode | When | Returns |
|---|---|---|
| `reverse-engineer` | `/spec reverse <module>`; a touched module has no spec | `needs_user_input` (the user verifies) |
| `spec-debt` | `/spec debt`; `spec_debt_pending` | `needs_user_input` with the lines needing an answer |
| `spec-init` | `/spec init`, after the user answered | `completed` |
| `spec-scope` | `/spec scope` step 5 | `completed` |

## Root cause

The procedure is `refs/roles/brainstorm/root-cause.md`; read it before a bug is rooted. A bug is rooted by brainstorm, never by implement; implement's `root_cause_unconfirmed` comes back here.
