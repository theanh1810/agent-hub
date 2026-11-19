# Exploratory cases — part (b) of a test run

<Owner: agents/test.md § Workflow>
<Read when: Workflow step 5, once part (a)'s cases have all run.>

---

Two parts — the plan/spec cases, then 5-10 special cases test predicts; a red exploratory case becomes a bug to fix when it is a crash, data loss, security hole or access block; any other failed one goes to the plan's ledger.

## When

Every run that tests a change: the plan-scope run of the final review gate (`refs/gates.md`), and a run with no plan. Inside an error loop it invents nothing: beside part (a), it re-runs the exploratory cases of the run that went red as `refs/roles/test/retest-scope.md` states (only the major ones), so the loop measures one fixed list.

## Choosing 5-10

5 to 10, aimed at what the change reaches and part (a) does not; fewer than 5 only when the change has fewer distinct surfaces, and the run says so.
- A boundary (empty, one, many, the limit, one past it, column limit); malformed or hostile input; an order or repeat (twice, out of order, interrupted); an environment the cases assume away (missing file, no network, other locale).
- A caller `mcp__gitnexus__context` names; a sibling path from the `affected_surfaces[]` of brainstorm's record (`design.yaml`, else `docs/brainstorm/{slug}.yaml`).
- A mutation case when the task touches logic and the repo has a unit test command: mutate the changed functions on the copy `refs/roles/test/read-only.md` describes and report surviving mutants.
- 1000 random inputs for a "sometimes wrong" bug; the same input on the old and the new build; the worst accepted case, not a typical vector.
- One check does not guard its siblings: on finding a bug, check the parallel paths (other callers, roles, feature flags, compatibility paths) with the same source-to-sink shape. For each data-analysis boundary tabulate: accepted kinds, who allocates, who uses, flow, cleanup.
- A violation probe per business rule of the touched surface (`refs/business-rule-testing.md § Violation probes`): every rule of a touched screen, API or flow has a valid and a violating case; rule sources are only a UC AC, the user's dated words or a recorded decision; an unrecorded rule is asked, never guessed.

## The oracle

Every case names where its expected result comes from: a `file:line` of the changed code or rule, a scenario name, or a general invariant (no crash or traceback, non-zero exit on bad input, nothing written outside the run's evidence, no secret in output). No oracle, no run. An expected result only an unstated business rule could supply is never red: a violation probe of that kind is `suspected` (§ Results); any other such case is a question in `missing_test_cases[]` (`rules/core.md § Ask, never guess`).

## Mode `script`

A case is a shell command. A case that changes a file runs on a copy under `.cm-tmp/{task_id}/`, never on the tree (`refs/roles/test/read-only.md`).

## Results

- **Red, major** (a crash, data loss, security hole or access block): listed verbatim in the report and the `## Round {n} · explore` section of `{plan_dir}/review.md`; brainstorm `mode=error-batch` records it in `errors.yaml` with `source: test-explore` (`refs/roles/brainstorm/error-batch.md`). Gate `RED`; it enters the error loop and counts toward the cap of 2 (`refs/error-loop.md`).
- **Red, minor** (any other failure): listed verbatim with `severity: minor` in the report and the `## Round {n} · explore` section of `{plan_dir}/review.md`; brainstorm `mode=error-batch` records it into `deferred_errors[]` (the ledger). Gate unchanged; it opens no fix round and is outside the cap.
- **Green**: recorded, nothing more.
- **Suspected** (`refs/business-rule-testing.md § Suspected-defect report`): not red, not in `errors.yaml`, outside the loop cap; listed under `## Suspected defect, needs confirmation`; the run returns `needs_user_input`, one question per case, options `Is a defect` · `Allowed`; the answer becomes the case's standard.
- All of these go in `exploratory_cases[]` and the `## Round {n} · explore` section of `{plan_dir}/review.md` (images that must outlive the run go to `{plan_dir}/evidence/`), in Vietnamese; with no plan, a `## Exploratory cases` section of the adhoc record. The user does not approve them first; a case worth keeping is proposed in `missing_test_cases[]`.
