# task (compliance)

- The task aligns with the PRD's features, decisions, state machines and error codes. All `acceptance_criteria` are met; declared files exist.
- A test file the diff **adds**, as `code-style/README.md` § Test layout defines one, sits where that section puts it in this repo; anywhere else is a finding. A test file the diff only edits never is.
- An old repo's first `tests/` file comes with the runner config widened, not replaced, and the handoff quoting both test-list counts and an empty `comm -23`.
- A task of a plan that edits only the `~/.claude` ruleset: run `tools/check ruleset (package repo only)`, compare each `files[]` path against its pre-edit backup, and re-run two of the task's test cases (an `edge` one first when there is one), not every case.
- The implementer's report is an unverified claim; a plan-mandated flaw is still filed, labelled "plan-mandated" (`refs/roles/reviewer/finding-bar.md` § Standard, plan and spec).
- On `scope: plan` every check above runs per task id into that task's part of the `## Round {n} · conformance` section of `{plan_dir}/review.md`; the ruleset line runs `check-ruleset` once per run and re-runs two cases per task.
- On `scope: plan` also run the eight dimensions once over the plan's change, not per task; the dimension and `review_deep_paths` rule is the `Eight dimensions` bullet of `skills/review-checklist/references/independent.md`.
