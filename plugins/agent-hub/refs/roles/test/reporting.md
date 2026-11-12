# Reporting — the two output blocks, and error batching

<Owner: agents/test.md § Output discipline — failures only>
<Read when: writing the run's output — Workflow step 6.>

---

## Evidence — what a claim must carry (HARD)

- **A failure**: reproduction steps verbatim from the case, expected value verbatim, what actually happened. Quote both sides as written; never a paraphrase of either.
- **A network claim**: captured request and response, secrets stripped, plus the field diff (no body, no finding).
- **A console error**: the first error verbatim with its stack frame, uncompressed; never trimmed to fit a budget.
- **A visual claim**: screenshot path and the baseline compared against.
- **A pass**: the case id, nothing else.
- **An absence claim** ("no regressions"): the cases and commands it rests on, by id and command. No list, no claim.
- **A command run**: into `commands[]` with `cmd`, `exit`, `evidence_path`, `tc_id` (null for a check no case names). The exit is read from the shell (`; echo exit=$?`), never inferred. `secret_scan: exit 0` records the Scan row of `agents/test.md` § Evidence storage.
- **Impact**: the observed impact (wrong read, wrong write, hang, safe stop), never stronger than proved. A missing deciding fact (deployment, config, reachability) → "needs more verification" plus the smallest check.
- **Redaction**: secrets as `<REDACTED>` before quoting; auth headers keep only signal lines; too little left → say so and ask.
- **Never a diagnosis.** "POST /api/orders returned 500, likely backend route" is a scope hint; "the bug is in OrderService.create() because…" is brainstorm's.

## The green block

Eight lines, nothing more:

```
Status: GREEN
Plan: {plan_id}  Task: {task_id}
Test cases run: N  passed: N  failed: 0  steps: code, pass 1, pass 2 (n/a and accepted_drop named)
Commands: N run, all exit 0  (table: <run_dir>)
Coverage: AC=N/N  endpoints=N/N  bindings=N/N
Evidence: <run_dir>
Duration: Ns
passed_test_case_ids: [TC1, TC2, ...]
```

`spec_required: true` adds one line, `ac_coverage: UC-042 AC-1..AC-4 → 4/4 tested, 0 missing` (missing ACs by id). An accepted drop adds `accepted_not_run: [TC… | code] — <date of the user's answer>`. No per-case narrative for passes, no dumps, no inline screenshots. State which `thinking_mode` ran.

## The red block

Same header with `Status: RED`, `failed: M`, `failed_test_case_ids: [...]`, plus one failure report per failed case at `.cm-tmp/{task_id}/failure-docs/{test_case_id}.md` from `templates/test/FAILURE-report-template.md` (read it, never reproduce from memory). Each failure is listed verbatim with `test_case_id`, `evidence_path` and `failure_doc_path`, for planner to transcribe. `flow_results[]` carries **only** failed cases. The run report lists failing commands, one row each `| cmd | exit | evidence_path |`.

## Error batching (HARD)

Finish the whole run, then report once, across every resume segment (from `progress.yaml`). Never return on the first failure; a red step 1 is the one exception (`two-pass.md`). The loop is capped at two rounds, so a partial batch wastes one.

1. List every failure verbatim, never compressed. Brainstorm `mode=error-batch` records them into `{plan_dir}/errors.yaml` and root-causes them (`refs/roles/brainstorm/error-batch.md`). One entry per failed case, and a table case names its failing row (state and theme): `test_case_id`, failed stage, expected and actual, first console error, failing request and response, `failure_doc_path`, `evidence_path`.
   A plan path that does not exist (a migrated workspace) is resolved with `agent-hub locate --resolve PATH`, never guessed or recreated.
2. Write one run report, `.cm-tmp/{task_id}/failure-docs/RUN-REPORT.md`, the file the next agent opens first:

```markdown
# Test run — {task_id} · {YYYY-MM-DD HH:mm} · {N} failed of {M}

## Failures, grouped by what they look like
| Group | Cases | Stage | Symptom | Evidence |
|---|---|---|---|---|
| G1 | TC-3, TC-7 | 6 backend | POST /api/alerts → 500, same stack | failure-docs/TC-3.md |

## What each group shares
- **G1** — {common factor: same endpoint, payload shape, symbol in the trace}

## Order to fix
1. {G1 — blocks G2 and G4, fix first}

## Not reproducible
{cases that failed once and passed on re-run, with both outcomes}

## Environment at run time
{base_url · build marker or commit · browser chosen and why · anything unusual}
```

Group by **shared symptom**, not case order (grouping is observation; naming the bug is brainstorm's). Return `run_report_path`; main thread hands that one path to brainstorm.
