# Wave checkpoint — a script-only run after a risky wave

<Owner: agents/test.md § Inputs>
<Read when: the spawn input carries `checkpoint` (mode `script`, `task_id` null).>

---

A check right after the waves a plan calls risky, with no reviewer spawn. It is a test spawn because main thread runs no command (`rules/core.md § Routing`).

**Input.** `checkpoint: {after_wave, task_ids, expected_red: [{check, owner_task, reason}]}`, copied by main thread from the checkpoint `design.md` names (`refs/gates.md § Gate procedures`, Final gate step 1); `plan_ref` names the change folder `openspec/changes/<change>/`. Here `{wave_id}` reads as `after_wave`.

## Procedure

1. From `{workspace_root}` run `python3 tools/check.py ruleset` (agent-hub repo only) only when the diff touches `~/.claude` (as `refs/closeout.md` step 2), and `agent-hub check plan {plan_dir}` once each.
2. Run the cases test derives for each task in `task_ids` (`refs/roles/test/cases.md § Writing a case`) as part (a) does (`two-pass.md`).
3. Record every command in `commands[]` as `{cmd, exit, evidence_path, tc_id}` (exit read from the shell; `tc_id` null for check-ruleset and `agent-hub check plan`). GREEN needs at least one executed command.
4. Put each command's output and a short `report.md` under `.cm-tmp/{plan_id}-{wave_id}-checkpoint/` (= `report_path`). RED keeps the folder (brainstorm `mode=error-batch` reads it); GREEN deletes it before returning.
5. No exploratory part, no second pass: one pass over the commands above.

## Gate

- **GREEN**: every command exits 0, or each red check is named in `expected_red[].check` (the name check-ruleset or `agent-hub check plan` prints after `FAIL`). A red test case is never excused by `expected_red`.
- **RED**: anything else. Return `gate: RED`, `commands[]`, `report_path` with each red line verbatim; main thread hands it to brainstorm `mode=error-batch` (source checkpoint), and the fix round does not count toward the error-loop cap (`refs/error-loop.md` § What does not count).

A checkpoint writes no review file, no baseline, and appends nothing to `errors.yaml`.
