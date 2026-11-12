# Wave checkpoint — a script-only run after a risky wave

<Owner: agents/test.md § Inputs>
<Read when: the spawn input carries `checkpoint` (mode `script`, `task_id` null).>

---

A check right after the waves a plan calls risky, with no reviewer spawn. It is a test spawn because main thread runs no command (`CLAUDE.md` §0.1).

**Input.** `checkpoint: {after_wave, task_ids, expected_red: [{check, owner_task, reason}]}`, copied by main thread from the plan's `validation_strategy.checkpoints`; `plan_ref` names `{plan_dir}/plan.yaml`. Here `{wave_id}` reads as `after_wave`.

## Procedure

1. From `{workspace_root}` run `tools/check ruleset (package repo only)` only when the diff touches `~/.claude` (as `refs/closeout.md` step 2), and `agent-hub check plan {plan_dir}` once each.
2. Run every `test_cases[]` entry of each task in `task_ids` (each read per `refs/plan-files.md § Reading one task`) as part (a) does (`two-pass.md`).
3. Record every command in `commands[]` as `{cmd, exit, evidence_path, tc_id}` (exit read from the shell; `tc_id` null for check-ruleset and plan-verify). GREEN needs at least one executed command.
4. Put each command's output and a short `report.md` under `.cm-tmp/{plan_id}-{wave_id}-checkpoint/` (= `report_path`). RED keeps the folder (brainstorm `mode=error-batch` reads it); GREEN deletes it before returning.
5. No exploratory part, no second pass: one pass over the commands above.

## Gate

- **GREEN**: every command exits 0, or each red check is named in `expected_red[].check` (the name check-ruleset or plan-verify prints after `FAIL`). A red test case is never excused by `expected_red`.
- **RED**: anything else. Return `gate: RED`, `commands[]`, `report_path` with each red line verbatim; main thread hands it to brainstorm `mode=error-batch` (source checkpoint), and the fix round does not count toward the error-loop cap (`refs/roles/orchestrator/error-loop.md` § What does not count).

A checkpoint writes no review file, no baseline, no task `result`, and appends nothing to `errors.yaml`.
