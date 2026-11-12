# Gate procedures — the five gates in full
<Owner: agents/orchestrator.md § Gates>
<Read when: a worker returns a gate status, Shape A carries `run_mode: ultracode_offer`, or a planner / implement wave needs the gate procedure>

---

An approved plan runs continuously: no "shall I continue?" between tasks ("Do not pause to check in with your human partner between tasks."). The only stops are the five gates or an irreversible action (CLAUDE.md destructive-action list). Each approval covers one step, never the next.

## Clarify gate (HARD)

brainstorm `needs_user_input` → main thread surfaces `user_questions[]` with `AskUserQuestion`, collects answers, re-spawns brainstorm `mode=clarify-followup` + `user_answers[]`. No downstream spawn until brainstorm returns another status. At most 5 questions per turn, most important first; a question stays open unless the user is stuck (`refs/roles/brainstorm/intake.md`).

## Approval gate (HARD)

brainstorm `awaiting_user_choice` → main shows `candidates[]` + `recommended_candidate`, waits for the pick, re-invokes orchestrator with `chosen_candidate_id`; next spawn `brainstorm mode=change-design`, then `planner`. Fires on `approval_required: true` only for: complex / refactor / architecture · a feature of >6 files or cross-module · a bug touching a shared or exported symbol, contract, route, schema or socket. Skipped for simple / hotfix / docs / a local single-file change / `error-batch`.

## Plan-review gate (HARD — always on when planner ran)

After planner returns the plan files (`refs/plan-files.md`), main calls `AskUserQuestion`:
- Question: "Plan ready — approve to start implement?"
- Preview: the `plan.<lang>.md` overview (waves, task count, per-task line estimate) + the first wave's tasks with `review_checkpoint.focus[]`. Add the findings of the reviewer's plan critique (`refs/roles/orchestrator/workflows.md`); a critique finding marked blocking sends the plan back to its producer before this question is asked (Q-D05-1-a).
- Options: `Approve & implement` (Recommended) | `Edit plan` | `View plan details` | `Cancel`. These are canonical names: main thread shows the labels and the question in the reply language (core §1) and maps the user's pick back to the canonical name.

`Approve & implement` → stamp first: `agent-hub check plan <plan_dir> --approve "<user words verbatim>"` (writes the plan's `approval {by, fingerprint}` for `chk_approval`), then the first implement wave. A plan edited after the stamp needs approval again. `Edit plan` → `brainstorm mode=change-design` with the user's notes, then `planner`. `Cancel` → halt. Implement `needs_revision` / `plan_not_approved` means the plan arrived unstamped: run this gate, never stamp without the user's words; a user who chooses to run unapproved gets a Bypass record entry `approval-gate`, copied into the implement brief.

## Hedged approval is not approval (HARD — plan, final and devops gates)

An approval counts only when the reply approves without a condition or doubt. A reply carrying a hedge is no approval: the gate stays closed, nothing is stamped, no wave, commit or deploy starts, and main asks **once more**, naming the doubt in that one question. Hedge examples: "ok but change the name first", "probably fine", "if the tests pass then fine", "maybe", "looks good, I think". The same holds in the reply language: a hedge phrase in any language is a hedge. A clean approval after the re-ask passes; a second hedge is a new answer to the same open gate, handled the same way, never counted as approval by default. This applies to `Approve & implement`, `Approve`, and a devops `needs_approval` gate alike.

This gate and the final gate are unconditional in every permission mode (`auto`, `bypassPermissions`, `default`); only the user's explicit "no plan approval needed" (or the same words in the reply language) in the original request overrides the plan gate.

## Final review gate (HARD — every permission mode, every flow)

Asked **once**, after the whole plan's review-and-test pass; the user is asked twice in a plan (plan gate, this). A task is every plan task whose agent is `implement`, `test` or `devops`, plus `closeout`; with no plan, every such spawn of the run.

1. **Run the waves.** One `implement` spawn per wave carrying every implement task in `task_ids[]`, `closeout` alone in the last wave's spawn; a `devops` task is its own spawn. No review or user stop between waves. After a wave named in `validation_strategy.checkpoints[].after_wave` returns with no `remaining_task_ids[]`, main spawns `agent-hub:test` `mode: script`, `task_id: null`, `checkpoint: {after_wave, task_ids, expected_red}` (`refs/roles/test/checkpoint.md`): no reviewer, no exploratory part, no user stop. Green, or red only on that checkpoint's `expected_red`, passes. Otherwise `brainstorm mode=error-batch` (source `checkpoint`) → one `implement` fix-round spawn without `closeout` re-run → the same checkpoint → next wave. This round does not count toward the cap of 2 (bounded by implement's three-fail rule); an `expected_red` still red after its `owner_task` ran is red. `in_progress` with `remaining_task_ids[]` is resumed before the next wave. The `closeout` task's last command builds the review packet (`agent-hub review-packet {plan_dir} --round {round} --diff-only-out .cm-tmp/{plan_id}-r{round}-independent/diff-r{round}.md`); a fix round's `closeout` re-run rebuilds it with `--base-dir ~/.claude-backups/{plan_id}/fix-r{round}/`, where the fix-round spawn copies every `fix_list[].files[]` path before its first edit, so the diff-only file holds that round's change only.
2. **Review and test, once, over the whole plan**, one message: `reviewer mode=independent` (`scope: plan`, `plan_snapshot`, the diff-only file from the frozen snapshots) over every implement task not exempt (`refs/roles/orchestrator/edge-cases.md`), and `test` with `task_id: null`, `round`, `plan_ref`, in the mode the change calls for (`script` with no screen): part (a) every plan case, part (b) 5-10 exploratory cases. `refs/effort-routing.md` may split test into two spawns. The independent brief carries **only** `plan_snapshot`, the changed paths, the review file path, on a pass after a fix round the previous independent review file (its own findings, for `refs/roles/reviewer/finding-bar.md` § Re-review and deferral), and on the round-0 re-spawn after a Codex diff review `codex_review_opinion` (Codex's findings only) or `codex_review_skipped` (`agents/reviewer.md` § Codex diff review): no plan or task path/id, acceptance criterion, test case, spec, analysis, handoff, other earlier verdict, `errors.yaml` or user request. `round` is `meta.error_loop_count`, 0 when absent. No implement task, or all exempt → no review; `test` still runs.
3. **A red result** (`needs_changes`, `blocking`, `gate: RED`) → `brainstorm mode=error-batch` with the three output paths. A pass whose only findings are 🟡 or minor exploratory failures, and every pass that follows a fix round, goes to `brainstorm mode=error-batch` too, which records it as a yellow or green round with no fix spawn. `cap_reached: false` with a non-empty `fix_list[]` → one `implement` fix-round spawn (`closeout` re-run at its end) → step 2 over the fix: the reviewer gets the fix round's diff-only file (`refs/roles/reviewer/finding-bar.md` § Re-review and deferral), test runs part (a) in full and part (b) per `refs/roles/test/retest-scope.md`. `cap_reached: true` → `needs_user_decision` (`refs/roles/orchestrator/error-loop.md`).
4. **Ask once** when the last round is green or yellow and error-batch's `close_check` is PASS, or a partial is accepted at the cap. Question "Plan {plan_id} done — approve?". Preview per task: diff summary (test report for a test task, change plus evidence for devops) + `focus[]` + `risk_areas[]`; then the sum of `estimate_min`, the code review verdict with findings, each exploratory case green or red, error rounds run, the seven Definition of Done items ticked (`refs/closeout.md`), the ledger (`deferred_errors[]`, one line each), `meta.pending_user_changes[]` verbatim, and `packet_path`. One approval covers the whole list. Options: `Approve` (Recommended) | `Request changes` | `View full diff` | `Stop plan`. With no plan the preview is the worker handoffs, the independent review writes `docs/changes/adhoc/{YYYY-MM-DD}-{slug}/independent.md`, and `Stop plan` reads `Stop`.
5. `Approve` → the wave commit, which also copies the ledger to `docs/deferred-backlog.md` (`refs/roles/implement/close-task.md` § Wave commit). `Request changes` → at most once per plan, pre-filled with `meta.pending_user_changes[]` (the user may answer that a pending change is a new request instead); record the user's notes verbatim as a round with `source: user-final-gate` (never toward the cap), then step 3's error-batch → fix round → step 2 over that fix's diff only (`refs/roles/test/retest-scope.md`) → this gate, asked again without that option and saying further change is a new plan. A red inside that round → `needs_user_decision` with roll back that round · accept partial · a new plan. `View full diff` → print the diff, re-ask. `Stop plan` → halt and save state; on resume this gate is asked again, nothing marked `done` or pushed before.
6. **Finish menu** (after an unhedged `Approve` and its wave commit, once; `refs/option-explanation.md`, labels and explain text shown in the reply language): `Push and open a PR` (Recommended; routed to `devops`, never run by implement) | `Merge locally into the base branch` | `Keep the branch`. Discarding the branch is not an option: it needs the user to type `discard <branch>` verbatim, and nothing else counts as that confirmation.

No skip condition: not `review_checkpoint.required: false`, not the permission mode, not "do it fast". The fast lane (CLAUDE.md) skips review and test, not this gate.

| Rationalization | Reality |
|---|---|
| "Stop after each wave to be safe" | One final gate per plan, nothing between waves |
| "Everything is green, skip the gate" | No skip condition in any mode |
| "Ask now, the review is still running" | Asking while a layer or test run is open, or a result is red outside an accepted partial, is a violation logged in `errors.yaml` |
| "Send the red result straight to implement" | Planner's record, then brainstorm's error-batch |

## Wave commit

In a plan no task commits alone. In a git tree each wave's `implement` spawn ends with one local commit per changed sub-repo (all the wave's tasks, never pushed); a fix-round spawn ends with one fix commit. After `Approve` main spawns `agent-hub:implement` once with `wave_commit: [<wave_id>, …]`, every wave, bookkeeping only (no push): write each commit SHA into `result.commits`, `status: done` into every task, rebuild each wave's `plan.<lang>.md` block from those records, append the plan's review rows to `docs/reviews/INDEX.md`, then cleanup-gate step 2 per task, the closeout sweep (`refs/roles/implement/close-task.md`), and `agent-hub worktree-sweep --apply --repo <each changed sub-repo> --orphans ~/.claude/worktrees` (pins unreachable commits, removes the wave's finished worktrees). At the plan's end main spawns `agent-hub:devops` to push the branch, open the PR/MR, integrate and clean its worktrees (`skills/devops-deploy/references/integration.md`).

- A tree with no git (`~/.claude`) commits nothing: the same spawn writes `done`, the blocks and rows, and clears the plan's backups and review snapshots.
- The last `wave_commit` spawn also runs the closeout sweep of `refs/artifact-layout.md` on the plan's ids.
- A run with no plan gets, after `Approve`, one `implement` spawn with `cmtmp_sweep: [<task_id>, …]` (every task plus `{session_id}-gate-test` and `{session_id}-gate-reviewer`): it sweeps and returns the cleanup line; push and MR only when the user asks, through `devops`, and the user merges by hand with no reviewer after. It is not a task: no review, no gate.

## Bypass record

A gate that applies and is skipped (by a review exemption, `refs/roles/orchestrator/edge-cases.md`, or the user's words) makes main append one entry to the nearest `{plan_dir}/errors.yaml` (else `docs/errors/{session_id}.yaml`):

```yaml
- source: gate-bypass
  pattern: review-layers      # review-layers | final-user-review | orchestrator-first | approval-gate | plan-review | test-pass | fast-lane
  when: 2026-10-13            # ISO date
  by: "the user's words, verbatim"   # or the exemption id
  task_ids: []                # the tasks the skipped gate covered
  wave: W2                    # or null
```

`review-layers` = the run's code review; `final-user-review` = the one user gate; `orchestrator-first` = CLAUDE.md routing; `plan-review` = planner and the plan gate skipped by the user's words; `test-pass` = the `test` spawn skipped by the user's words; `fast-lane` = CLAUDE.md fast lane, `implement` appends it itself, `by:` naming the conditions met. A gate that does not apply (a class on the Approval skip list) writes nothing. The record is a deterrent and a trace, not proof no other gate was skipped; auditor's `gate_bypasses` count is a floor.

## Design gate (HARD — FE/UI only)

brainstorm `needs_design` → spawn `agent-hub:designer` with `design_brief_request{}`; designer returns `design_brief_path`; main re-spawns brainstorm `mode=design-followup` + `design_brief_ref`. Skipped for backend / API / infra / docs / CLI / a logic bug with no visual change / a copy-only edit. Brainstorm owns the skip decision; orchestrator forwards `needs_design`.

## Ultracode offer (asks, never switches it on)

Shape A `run_mode: ultracode_offer`, read-only work only: `next_spawns[]` empty, note `ultracode_offer_pending`; main asks "This read-only work has {n} independent units. Run it with ultracode (dynamic workflow)?" with `Run the normal fleet pipeline` (Recommended) | `I will enable ultracode myself for this read-only work` (shown in the reply language). The first re-invokes orchestrator, routing `run_mode: normal`; the second stops, only the user types `ultracode`. Conditions: `refs/effort-routing.md`.
