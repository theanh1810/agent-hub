# Review trail

Tier 3 of `CLAUDE.md` §16 — the review artifact: when it is written, where it lives, and what it contains.
Read when: writing a review, tagging its severities, or appending `## What was learned` — `agents/reviewer.md` points here too, and neither copies any of it.

# Trigger and location

A plan's reviews all go into one file, `{plan_dir}/review.md` (`refs/plan-files.md § Run files`): every review round is one section, appended and never rewritten, so earlier rounds stay. A section is headed `## Round {n} · {kind}` with `{kind}` one of `task {task_id}` (a task whose diff is ≥50 lines), `conformance` and `independent` (reviewer), `explore` (test, exploratory cases, green and red) or `critique` (the plan critique, before the approval gate); a batch-flow plan writes `conformance`, `independent` and `explore` once per error-loop round. The reviewer writes in the reply language and main thread surfaces the path in the §12 final. A `task` section drops "pattern reference" and "why this approach" in the independent layer, which never saw them. Cited images and logs go to `{plan_dir}/evidence/` (`refs/artifact-layout.md § Where writing is allowed`); `INDEX.md` and visual baselines stay under `docs/reviews/`. Without a `plan_id` the review goes in `docs/changes/adhoc/{YYYY-MM-DD}-{slug}/`.

A legacy plan keeps the review files it has (`reviews/{task_id}.md`, `{wave_id}-independent.md`, `{wave_id}-explore.md`, `conformance-r{n}.md`, `independent-r{n}.md`, `explore-r{n}.md`, `critique-r{n}.md`); readers read them and nothing writes a new one (`refs/plan-files.md § Legacy layouts`).

**No plan** → no separate review file: reviewer appends a `## Review` section to the task's own adhoc record, after implement's six answers (path: the adhoc row of `refs/artifact-layout.md § Where writing is allowed`). The independent review is the exception: it writes `docs/changes/adhoc/{YYYY-MM-DD}-{slug}/independent.md` as its own file beside the record and never opens that record.

# Structure

A `task` section holds: diff summary · pattern reference · what changed · why this approach · risk areas the user should check · test coverage · **What was learned**.

A plan-scope section (`conformance`, `independent`) **opens with its verdict**, then follows the deep review spec's order, under these headings (rendered in the reply language): `1 Verdict`: BLOCK | CONDITIONAL | READY FOR HUMAN APPROVAL (= blocking | needs_changes | pass) · `2 Scope and files viewed` · `3 Requirement trace and gaps` (independent: what it could infer, blind to the plan) · `4 Findings by severity` · `5 Evidence and how to reproduce` · `6 Missing test cases` · `7 Architecture and maintainability` · `8 Residual risks and unchecked assumptions`; then `## Change explanation` (conformance only) and `## What was learned`.

# Severity tags, learning mode, and the dashboard

**Severity tags (HARD)**: `🔴 critical` blocks merge · `🟠 major` fix before merge · `🟡 minor` nice to have · `💡 learn` educational, never blocking. The deep review spec maps onto them: P0 = 🔴, P1 = 🟠, P2 and P3 = 🟡; 💡 stays outside the findings. A finding with no concrete case is a **hypothesis**, at most 🟡; a leaked secret is never downgraded.

**Learning mode.** With `learning: true`, every agent appends `## What was learned`: 1-3 bullets in the reply language explaining a concept, pattern or API used, with a source link, for a mid-level developer. Default off, except the conformance review of a batch-flow plan. `learning_focus: <topic>` goes deep on one subject.

**Per-AC table (`### AC check`).** A `conformance` section carries, in each task's part and before `## Change explanation`, a table in the reply language: one row per acceptance criterion, five columns — `AC` | `Met?` (`yes` / `no` / `unclear`) | `Evidence` (`file:line`) | `Case + exit code` | `Note` (one plain sentence). The verdict is the reviewer's own, reached after opening the evidence; where it differs from `result.ac_check` the row names the finding id. A task with no `ac_check` is still judged from the diff and case exits. Round ≥1 lists only the tasks the fix round touched, pointing at the earlier round for the rest.

**Explanation of changes (`## Change explanation`).** The conformance review of a batch-flow plan writes this into its `review.md` section, in the reply language, from the review packet (`agent-hub review-packet`, built under `.cm-tmp/{plan_id}/`). For each `validation_strategy.review_deep_paths` entry, hunk by hunk: the hunk header; `On intent?` (`yes` or `no`, citing the task id and AC served, or the intent missed); `Clean?` (`yes` or `no`, with the reason: `extra line`, `duplication`, `unclear name`, `magic number`); `What and why` (2-4 plain sentences: what goes in, what happens, what comes out — enough to fix it by hand). A pure move or rename takes one line. Every other path gets 2-4 lines: what changed and why, with its task id. Round ≥1 explains only paths the fix round changed.

**Dashboard.** `docs/reviews/INDEX.md`, one appended row per review: date · plan · task · severity counts · link. A run of `🟠` means quality is slipping.
