# Read-only — why each temptation is forbidden

<Owner: agents/test.md § Read-only. Change nothing (HARD)>
<Read when: something in the run looks like it wants fixing, seeding, restarting or tidying.>

---

| Rationalization | Reality |
|---|---|
| "One obviously wrong selector or one-line bug, I'll fix it" | The run then proves the fixed code; the failure to report is gone |
| "Restart the service, clear the cache, re-run the migration" | A broken environment is the finding; repairing it hides that production would break the same way |
| "Seed or edit data so the case passes" | The case failed for a reason; changed data measures a different system |
| "Edit the test, fixture or config to stop the flake" | A flake is a finding (`failure_type: flaky`), not a chore |
| "Touch the plan, spec or source to make the run pass" | They belong to planner, brainstorm, implement |
| "Tidy leftover files" | It cannot tell a user's file from an orphan; list them in `orphan_artifacts[]` |
| "Fix the infrastructure, it is quick" | Return `needs_devops: true` |

Red flags: any `Edit`/`Write` outside the allowed list in `agents/test.md`, any service command, any "fixed it and re-ran".

Hand the change to its owner: code → `implement` · environment → `devops` · plan or cases → `brainstorm` · spec → `brainstorm`. Return the matching status and say what needs doing.

**Exceptions, both narrow.**
- Step 1's suite may write the database the repo declares for tests alone, never one shared with development or production; none declared → the step does not run (`refs/roles/test/two-pass.md § Step 1 and the database`).
- A bug repro case may be written and run on a copy under `.cm-tmp/{task_id}/repro/`; the real tree is never touched (`refs/roles/test/repro.md`); a `repro_request` from brainstorm is that case, run read-only as a `mode=script` command with its output returned verbatim.
- A mutation run: copy the files under test and their tests into `.cm-tmp/{task_id}/mutation/`, apply one mutation at a time to the copy, run the suite against the copy, report each surviving mutant as a finding, and delete the copy before returning; the working tree is never edited (Q-D11-a).
