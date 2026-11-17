# Review trail

<Owner: rules/core.md § Load when, row "learning mode on">
<Read when: writing a review, tagging its severities, or appending `## What was learned`; `agents/reviewer.md` points here too, and neither copies any of it>

# Trigger and location

A run's reviews all go into one file, `{plan_dir}/review.md` (`refs/artifact-layout.md § Where writing is allowed`): every review round is one section, appended and never rewritten, so earlier rounds stay. A section is headed `## Round {n} · {kind}` with `{kind}` one of `task {task_id}` (a task whose diff is ≥50 lines), `independent` (reviewer) or `explore` (test: exploratory cases green and red, waivers, `accepted_not_run[]`); `independent` and `explore` are written once per error-loop round. A second opinion's result is saved beside the file as `reviews/annex-<n>.md` (`refs/gates.md`). The reviewer writes in the reply language and main thread surfaces the path in the final. A `task` section drops "pattern reference" and "why this approach" in the independent layer, which never saw them. Cited images and logs go to `{plan_dir}/evidence/`; `INDEX.md` and visual baselines stay under `docs/reviews/`. Without a plan the review goes in `docs/changes/adhoc/{YYYY-MM-DD}-{slug}/`.

**No plan** → no separate review file: reviewer appends a `## Review` section to the task's own adhoc record, after implement's six answers (path: the adhoc row of `refs/artifact-layout.md § Where writing is allowed`). The independent review is the exception: it writes `docs/changes/adhoc/{YYYY-MM-DD}-{slug}/independent.md` as its own file beside the record and never opens that record.

# Structure

A `task` section holds: diff summary · pattern reference · what changed · why this approach · risk areas the user should check · test coverage · **What was learned**.

An `independent` section **opens with its verdict**, then follows the deep review spec's order, under these headings (rendered in the reply language): `1 Verdict`: BLOCK | CONDITIONAL | READY FOR HUMAN APPROVAL (= blocking | needs_changes | pass) · `2 Scope and files viewed` · `3 Requirement trace and gaps` (what it could infer, blind to the plan) · `4 Findings by severity` · `5 Evidence and how to reproduce` · `6 Missing test cases` · `7 Architecture and maintainability` · `8 Residual risks and unchecked assumptions`; then `## What was learned`.

# Severity tags, learning mode, and the dashboard

**Severity tags (HARD)**: `🔴 critical` blocks merge · `🟠 major` fix before merge · `🟡 minor` nice to have · `💡 learn` educational, never blocking. The deep review spec maps onto them: P0 = 🔴, P1 = 🟠, P2 and P3 = 🟡; 💡 stays outside the findings. A finding with no concrete case is a **hypothesis**, at most 🟡; a leaked secret is never downgraded.

**Learning mode.** With `learning: true`, every agent appends `## What was learned`: 1-3 bullets in the reply language explaining a concept, pattern or API used, with a source link, for a mid-level developer. Default off. `learning_focus: <topic>` goes deep on one subject; the method is `refs/vendored/teach.md`.

**Dashboard.** `docs/reviews/INDEX.md`, one appended row per review: date · plan · task · severity counts · link. A run of `🟠` means quality is slipping.
