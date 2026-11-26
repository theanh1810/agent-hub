# Two passes — the order of a test run

<Owner: agents/test.md § Workflow>
<Read when: Workflow step 5; a run ending with a case or step not run.>

---

Test the code first, then each test case as a user would, then the user's business flows; all must pass before the run counts as done.

## The three steps

One run, in this order, one report, one gate. With a plan, the tasks in scope are those of `task_ids`; on a plan-scope run (`task_id: null`, `task_ids` empty) every task of `tasks.md`. The `flows:` run in step 3; where step 3 does not apply, the one `script` flow runs in step 1.

| Step | What runs | When red |
|---|---|---|
| 1 Code tests | the repo's own test command (read from its manifest per the `unit` row of `refs/roles/test/cases.md § Toolset per layer`) plus the tests implement wrote for every `unit`, `integration`, `contract` case and every custom `security` case. Test re-runs them and never rewrites one; a red one goes to implement | stop and report; steps 2-3 are `skip` |
| 2 Pass 1 | every `e2e` case (implement's Playwright spec first, then the eight stages of `refs/roles/test/journey.md`), the ZAP baseline scan of the `security` layer, every `script` case on the running local app | run step 3 anyway |
| 3 Pass 2 | the business flows of § Where the flows come from, each in one session, start to end (`refs/roles/test/journey.md § Cross-task journey`) | report once over steps 2-3 (`refs/roles/test/reporting.md § Error batching`) |

Step 1 is the independent run on the build that passed review; it does not replace implement's gate 6. Its failures go to `errors.yaml` per `reporting.md § Error batching` item 1, with the exit code. Part (b) (`refs/roles/test/explore.md`) runs after the last applicable step unless step 1 is red; its red cases join the same report.

## Which steps run

| The change | Steps |
|---|---|
| reaches a user: a screen, or an API a user calls | 1, 2, 3 |
| internal only: script, config, job no user calls, ruleset edit (mode `script`) | 1, 2 |
| a hotfix | 1, 2, and step 3 over the one main flow it fixed; a fix round does not widen step 3 |

A step that does not apply is `n/a` in `steps`, never `pass`.

Also report `layers: {unit, integration, contract, e2e, security, script}`, each `pass|fail|not_run|n/a`: any red case → `fail`; a case that did not run and none red → `not_run`; `n/a` only when no case in scope carries the layer; otherwise `pass`.

## Step 1 and the database

A suite whose config names a database runs only where the repo declares one for tests alone — a test env file, a test database URL distinct from development, a test profile, or a task database made with `task-db.sh` (`agent-hub-local-services: refs/local-postgres.md`). None declared → step 1 is `not_run`, reason `no_isolated_test_db`, and § Not run applies. A suite naming no database runs in step 1 alone. This is the one write beyond test's own record that `read-only.md` allows.

## Where the flows come from

With a plan: the `flows:` of `{plan_dir}/design.yaml` (mirrored in `plan.vi.md`), each naming its source scenario or the flow the user approved at the plan gate; flow id `FLOW-<n>`, n its position. No plan: the `flows:` in `docs/brainstorm/{slug}.yaml` (`refs/roles/brainstorm/modes.md § plan-write`). Neither → `needs_revision`, `reason: flows_missing`. Test never writes a flow; exploratory cases are not flows.

## Not run

A case or step that did not run (environment cannot produce it, or no isolated test database) blocks GREEN. A hung case is failed, not "not run".

1. While any planned case or major exploratory case is red, report the red ones first: `completed`, `gate: RED`, not-run ids in `not_run_test_case_ids[]`. Each fix round re-runs what `refs/roles/test/retest-scope.md` states, so the not-run question waits until nothing else is red.
2. When only not-run items remain, return `needs_user_input`: one question per missing environment (`refs/option-explanation.md § The user_questions block`), two options — provision it, or accept dropping exactly that case or step. Keep `.cm-tmp/{task_id}/`. Each option's `description` says in plain words what happens next; `## Next Step` names main thread's move per answer (R3-F2): provision → spawn `agent-hub:devops`, then re-spawn test with `resume: true` and `user_answers[]`; drop → re-spawn test with `resume: true` and `user_answers[]` naming the dropped ids.
3. An accepted drop goes into the `## Round {n} · explore` section of `{plan_dir}/review.md` as `accepted_not_run[]` of `{id, reason, user_answer, date}` (`id` the case id, or `code` for step 1, whose `steps` value is then `accepted_drop`); with no change folder, into `docs/errors/{session_id}.yaml`. The re-spawn runs again each `not_run` entry the user did not drop; every other result in `done` stands unless the build changed (`resume.md § Resuming` step 2).

## Done

GREEN: every applicable step ran or is an accepted drop, every case passed or is an accepted drop, at least one command ran in `commands[]`, and every exit is 0 read from the shell (full command, fresh).

After a fix: `refs/roles/test/retest-scope.md`. At the cap of two error loops: `refs/error-loop.md` step 4; accepting partial is recorded as `test incomplete: accepting remaining failures`, never as done.
