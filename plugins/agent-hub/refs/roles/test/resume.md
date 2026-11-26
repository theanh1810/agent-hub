# Resume — one run across several spawns

<Owner: agents/test.md § Workflow step 5>
<Read when: every run with a `plan_id`, before the first case; every spawn with `resume: true`.>

---

Finish every case before stopping; stopping, deleting and restarting from the top is not acceptable. A run ends only when every case in scope has a result; a turn cap is not an end and starting over is not a resume. Other checkpoints and main thread's side of a cap: `refs/turn-budget.md`.

## The progress file

`{workspace_root}/.cm-tmp/{task_id}/progress.yaml`, rewritten after **every** case, before the next opens:

```yaml
task_id: W1-T1
plan_id: string
build: string   # build marker pre-flight read at segment 1 (Workflow step 3)
scope: [TC-W1-T1-1, TC-W1-T1-2]   # fixed at segment 1; a resume never re-derives it
segment: 1
step: pass_1   # code | pass_1 | pass_2; a done status may be not_run, run again after the user's answer unless dropped
done:
  - { id: TC-W1-T1-1, status: passed, hung: false, failure_doc_path: null }
current: { id: TC-W1-T1-2, segments_started: 1 }   # null between cases
consecutive_hung: 0
restarted_from: null   # { build, dropped } after a build change
```

The file also carries `next_step`, `commands`, `pending_commands`, `constraints` and `reason`, each shaped and filled as `refs/turn-budget.md § The checkpoint` states; a resume is bound by `constraints[]` exactly as by its brief.

## Returning before the list is done

At the ceiling (`refs/turn-budget.md § The ceiling`), stop at a case boundary and return `status: in_progress` with `remaining_test_case_ids[]` and `progress_path`. Run `browser_close` (step 7) but **not** step 8: `.cm-tmp/{task_id}/` is the run's memory.

## Resuming

On `resume: true`, or `resume: false` while `progress.yaml` exists (a run that never ended):

1. Read `progress.yaml`; its `scope` wins over any id list passed.
2. Re-run pre-flight. A build other than `build` means done cases judged another build: keep that `build` and the `done` count, delete `.cm-tmp/{task_id}/`, start a new run at segment 1 over the same `scope`, its first `progress.yaml` carrying `restarted_from: { build, dropped }` for the merged report.
3. Skip every id in `done`, except a `not_run` one (step 1 under id `code`) the user did not drop (`two-pass.md § Not run`). Start at `current` from its first step (browser state does not survive a spawn), else the next id in `scope`.
4. A case that began in 2 segments without finishing is `failed`, `hung: true`, reason `exceeds_segment`, and the run moves on.


## A hung step

Each step waits at most **30 seconds** for its expected state (`browser_wait_for` with a time bound; Detox or Maestro timeout on mobile). None → retry once. Still none → the case is `failed`, `hung: true`, later steps `skip`, evidence captured, run moves on.

`consecutive_hung` rises by one per hung case (`exceeds_segment` counts) and resets to 0 on any completed case. At **3**: `status: failed`, `failure_type: transient`, `needs_devops: true`, `remaining_test_case_ids[]` set, `progress.yaml` kept. After devops, main thread resumes with `resume: true`, never a fresh run.

## Ending

Only when every id in `scope` is in `done`: one merged report over every segment, naming `build` and any `restarted_from` (`reporting.md`), then the Evidence storage cleanup. That and a build change (§ Resuming step 2) are the only points `.cm-tmp/{task_id}/` is deleted; a `needs_user_input` over a case or step not run keeps it (`two-pass.md § Not run`).
