# Close the task (HARD)
<Owner: agents/implement.md § References>
<Read when: Workflow step 1, for item 1 of § Write the result into the plan (the `implementing` status) and, on a plan's first `implement` spawn, its branch (§ Wave commit), and Workflow step 8, closing the task: commit, branch and MR (a plan commits once per task, § Wave commit), the write-back, closeout on the run's last code-touching task, and cleanup.>

---

Order at close: freeze the snapshot for review, write the plan, then commit (a commit first leaves `base` equal to `tip` and the review an empty diff).

## Commit

Author is the configured git/GitLab user (project `gitlab.user`, or `~/.claude/gitlab-user.txt`); Claude appears only in the `Co-Authored-By:` footer. No configured user: `needs_user_input`, never the default git identity.

```bash
git -c user.name="$GIT_USER_NAME" -c user.email="$GIT_USER_EMAIL" commit ...
```

```
<type>(<scope>): <imperative summary>     # ≤72 chars, no trailing period, no emoji

<one bullet per logical change, each led by [area/file]: action>
<name the exact symbol, route, or class>

Refs: <plan_id> / <task_id> / <ticket_id if any>

Co-Authored-By: Claude <noreply@anthropic.com>
```

- `type` ∈ `feat, fix, refactor, hotfix, chore, docs, test, perf, ci, build`; scope is the module; imperative present tense.
- The subject states intent and stands alone: "fix mail Reply-To header", never "Fix bug", "Phase 1", "Update code". The body says why, admits what is weak about the approach, carries no `TODO` and any confirmed bug hypothesis. Example: `templates/commit/EXAMPLE-commit.md`.
- **One local commit per task**, made after the task's close steps pass, the task id in the subject (`[<task_id>]` leads the summary); one spawn still runs a whole wave, and nothing is pushed. § Wave commit says who writes the SHA and when. A fix or conflict-resolution commit after merge review is its own small commit.

## Branch and MR

- Never commit to `main` or `develop`; a hotfix is the exception only where the project's own process says so.
- Without a plan: a feature branch off the target and a local commit when the user asks. Push and MR (title and description from `what` / `purpose` / `solution`, labels and draft per project convention) go to `devops` on the user's word; never merge or review it.
- A plan has one branch (§ Wave commit); implement commits locally, never pushes. Push, PR/MR, branch integration and the base-branch question belong to `devops`, and so do worktrees it created for integration; implement's `wave_commit` spawn runs `agent-hub worktree-sweep --apply` for the plan's repos after each wave and the closeout task sweeps the rest (`refs/artifact-layout.md` § 19.3) (`agents/devops.md`, `skills/devops-deploy/references/integration.md`).

## Write the result into the plan

**The task record, the moment the task finishes**, not at closeout. It (`refs/plan-files.md § Two formats`) is the only plan file a task writes; `result` goes there only (the mirror carries `status` and the `Result` block of `refs/closeout.md § The result in the mirror`), and the `wave_commit` spawn rebuilds the mirror after the final gate, so it lags and never leads. Every write takes the plan-write lock (`CLAUDE.md` §20 § Who writes it, and when); a held lock is wait-and-retry, never a skipped write.

### Run window

At task start, before the first edit, write `date -u +%Y-%m-%dT%H:%M:%SZ` to `.cm-tmp/{task_id}/run-started-at` unless that file exists, so a resumed task keeps its first start. At the result write take `result.run.started_at` from that file and `finished_at` from the clock (`refs/closeout.md § Data impact`).

1. **`status`** in the task record: `implementing` while running; `testing` when handing to test; `blocked` with a `blocker`; `reviewing` at return with a full `result` and `steps[n].done: true` on each step done and verified (a `run` step only when its output shows its `expect`; an undone step stays `false`, reason in `result.deviations`), all in one locked write. `done` only from the `wave_commit` spawn after the final gate; `accepted_partial` on a test task only as `refs/roles/orchestrator/error-loop.md` step 4 states.
2. **`result`** at return: `summary` · `commits[]` · `files_changed[]` with a note per file · `entry_points[]` (UI entry down to backend, one line per chain) · `verification[]` (commands with real numbers; red and green phases for a TDD task) · `deviations` · `changes[]` · `run` and `data_impact` (`refs/closeout.md § Data impact`) · `ac_check[]` (one per acceptance criterion, shape in `refs/closeout.md § What every meaningful change answers`, written after the cases ran from `result.commands[]` exits and the changed lines, never from intent). After the result write run `agent-hub change-map --plan {plan_dir} --workspace-root {workspace_root}`, which regenerates the plan's change map; a non-zero exit is written to `result.deviations` and never blocks the task. The returned message stays short.
3. **`changes[]`** per meaningful change: a step done as planned is `step: n` plus the last four fields; anything else all eight (`refs/closeout.md § What every meaningful change answers`): `what` · `where` (`file:line`) · `before` · `after` · `explanation` (the mechanism, not the diff in words) · `impact` (what the user sees, what else is touched, any migration or restart) · `benefit` · **`cost`** (state the price paid; never empty).
4. **A bug fix or hotfix too.** No plan: write the adhoc record at the path `refs/artifact-layout.md § Where writing is allowed` gives, with the same six answers (`CLAUDE.md` §20), built from `templates/adhoc/adhoc-record-template.md` so it also carries `run` and `data_impact`, then run `agent-hub change-map --adhoc <that record> --workspace-root {workspace_root}`; a non-zero exit goes into the record's body and blocks nothing. That record's path is exempt from `binding_scope` (X45, 2026-09-24); the exemption covers this one record and nothing else.

**Closure invariant.** Return only when the task record says `reviewing`, `result` has an `ac_check` entry per acceptance criterion, and every step is `done: true` or `false` with its reason. Only the `wave_commit` spawn sets `done` (in a git tree with the wave's SHA in `result.commits`); `status: done` with `result: null` is a violation, and `completed` is never returned with the plan half-written.

## Closeout — on the closeout task only

The `closeout` task in the final wave and at the end of each fix-round spawn; with no plan, inline before returning. Once per spawn (`CLAUDE.md` §21).

1. **Reindex.** `mcp__gitnexus__detect_changes(scope='unstaged')`, then `gitnexus analyze`, both inside each sub-repo this run changed (loop over them), never once at `{workspace_root}` (usually not a git root, `CLAUDE.md` §19.3). Cross-repo: `mcp__gitnexus__group_sync`. First: steps 2-5 cite symbols. A diff touching only `~/.claude` records `n/a - ~/.claude is never indexed (skills/gitnexus-flow Rule 2)`.
2. **Diff is the planned diff.** Compare `detect_changes` with the union of `files[].path` over the task records. A path no task named goes into `closeout.diff_matches_plan: false` with the path listed, never silently accepted. A diff touching a rule file also records `closeout.ruleset_gate` (`refs/closeout.md` step 2).
3. **Result is in the plan.** Re-read the plan: every task at `done` or `accepted_partial` has a non-empty `result` in its record plus `status` and its `Result` block in the mirror, and in a git tree its wave's SHA in `result.commits`. A gap is written now and reported; a finished task lacking an `ac_check` entry is listed as `ac_check_gaps: [{task_id, ac}]`, never written for another task (you neither ran nor verified it).
4. **Sync the spec** when `spec_required: true`: hand brainstorm every `spec_delta[]` (it owns `specs/`, so no improvised wording), bump `## History`, fill `### Test mapping` from test's `ac_coverage[]`, tick repaid lines in `specs/_debt.md`; a plan in `docs/changes/` also hands brainstorm its close (`SDD.md` § 3.1).
5. **mem0, then cleanup.** `search_memories` first; a near duplicate is `update_memory`. At most three new entries, only what `CLAUDE.md` §21 calls durable (a test-confirmed root cause, a reusable pattern with `file:line`, a pitfall that cost a real error loop); never the diff, file list or what the plan holds. `mem0: []` with a reason is correct.

Then the `closeout` block in the handoff: five fields with evidence (§21) plus `ruleset_gate`. No hook reindexes: step 1 is the only reindex besides `skills/gitnexus-flow` § Stale index; cite one of those two, never a hook.

## Cleanup

`rm -rf {workspace_root}/.cm-tmp/{task_id}`; the `closeout` task also runs the *Closeout sweep* of `refs/artifact-layout.md` § The cleanup gate, unasked. Then `git status --short` in each sub-repo this task changed (not once at `{workspace_root}`): remove or gitignore every `??` line this task created outside its `files[]` (a planned new file is intent-to-add, ` A`, § Wave commit). Nothing at a sub-repo root or at `{workspace_root}` outside the §19.1 folders, nothing new under `docs/changes/**` beyond the plan's own files.

## Freeze for review

After its checks and before commit, branch, MR and plan write-back (`agents/implement.md` Workflow step 8), a task freezes a snapshot its review reads while the next task runs, handed to main as `snapshot: {base, tip}`. A wave's tasks share no file (`refs/roles/planner/dag.md` § Wave rules), so a snapshot holds its own task alone.

- **Git tree.** `I=$(mktemp); cp "$(git rev-parse --git-path index)" "$I"; GIT_INDEX_FILE="$I" git add -A -- <files[].path>; GIT_INDEX_FILE="$I" git write-tree; rm "$I"` prints `tip`, and the real index is untouched. `base` is `git rev-parse HEAD^{tree}`, or for a fix the reviewed task's last `tip`.
- **No git** (`~/.claude`). `cp -c` (APFS clone) each `files[].path` to `~/.claude-backups/{task_id}/tip/<path>` (a fix to `tip-fix<k>/`); `base` is the task's pre-edit backup in `~/.claude-backups/{task_id}/`, or for a fix the last `tip`. Both stay outside the tree (`refs/artifact-layout.md` §19.2) until the wave commit clears them.

## Wave commit

Each plan task commits locally when its close steps pass; the `wave_commit` spawn only records the SHAs.

- **Until then** the diff stays in the working tree; at step 8 run `git add -N -- <path>` per created file (intent-to-add) so § Cleanup reads it as ` A`, not litter. Its reviewer reads the § Freeze for review snapshot (`refs/roles/reviewer/sources.md`, the diff row), never the working tree.
- **After each task's close steps**: one local commit per sub-repo the task changed, holding that task alone, not pushed. A fix-round spawn ends with one fix commit . Subject as § Commit with the task id, `type` the one covering the diff; `Refs: <plan_id> / <wave_id> / <task_id>`.
- **After `Approve` at the final gate** (`refs/roles/orchestrator/gates.md` § Final review gate) main spawns `agent-hub:implement` with `wave_commit: [<wave_id>, ...]`, every wave of the plan. That spawn runs step 8 only (skips 1-7): under the plan-write lock it writes the SHA into `result.commits` and `status: done` into every task of the plan (the only two fields it writes in a task it did not run; the one exception is the closeout task's `result.deviations`, written when `agent-hub change-map` exits non-zero below), then runs `agent-hub change-map --plan {plan_dir} --workspace-root {workspace_root}` once, so the final map sees `done` and the SHAs, rebuilds each wave's block of `plan.<lang>.md` from the task records (status; `[x]`/`[ ]` per step from `steps[n].done`; each non-null `result`'s `Result` block rendered whole; AC boxes `[x]` where `result.ac_check` has `met: true`, else `[ ]` with one indented line why (the entry's `note` in Vietnamese, or `no ac_check entry`; evidence is copied verbatim only into C4 of the `Result` block, `agents/planner.md` § Language); each **Wave acceptance criteria** box ticked where a `result` or verification line proves it, else one line why), and appends one `docs/reviews/INDEX.md` row per review of the plan. It also ticks `## Done criteria` items 3-5 from the gate preview and item 7, and appends to `{workspace_root}/docs/deferred-backlog.md` one line per `deferred_errors[]` entry of every round of the plan's `errors.yaml`, `- {date} · {plan_id} · {id} · {severity} · {location} — {first line of the `text` of the `entries[]` item with that `id`, verbatim}`, creating the file with a `# Deferred backlog` heading when absent; no follow-up plan is created. It is the only writer of either in a plan (`refs/closeout.md` § Who writes it).
- **A fix the user asks for at the final gate** goes through a fix-round spawn (`refs/roles/orchestrator/gates.md` § Final review gate, step 5) before the `wave_commit` spawn. Nothing is `done` (and devops pushes nothing) before the final gate passes; a plan stopped by `Stop plan` meets that gate again on resume, then the **Wave commit** paragraph of `refs/roles/orchestrator/gates.md` applies.
- **One branch and one MR per plan** . The plan's first `implement` spawn creates `feat/<plan_id>` off the target at Workflow step 1 when absent, before any edit; every task works on it and implement only commits there. At the plan's end devops pushes it and opens the MR (title in § Commit's subject format from the plan's `objective`, description from its `tldr`, one line per wave `name`). History stays split by wave; a fix after merge review is its own commit (`skills/review-checklist/references/merge.md` Phase B step 8).
- **No git** (`~/.claude` since 2026-09-26): no branch, `commits: []`; the `wave_commit` spawn writes the same fields and runs `agent-hub change-map --plan` the same way, then runs `refs/artifact-layout.md` § The cleanup gate step 2 per task, clearing backups and snapshots. On either tree it also runs that gate's *Closeout sweep* on the plan's ids, the closeout review's own `.cm-tmp/{task_id}` included.
- A `cmtmp_sweep: [<task_id>, …]` spawn (a run with no plan, after its gate; **Wave commit** paragraph of `refs/roles/orchestrator/gates.md`) skips steps 1-7 and from step 8 runs only that sweep, then returns its `cleanup:` line.

## One spawn, one wave

One spawn runs every implement task of a wave, steps 1-8 per task in `task_ids[]` order; each task is frozen and its record written before the next starts. `binding_scope` is one object for the spawn; each task edits only its own `files[]`.

- A task whose intake fails, or that needs a file outside its `files[]`, stops the spawn at that task boundary with `needs_revision` and `done_task_ids[]`.
- Context past the budget of `refs/context-policy.md` stops it at the next task boundary with `in_progress`, `done_task_ids[]` and `remaining_task_ids[]`; main re-spawns it with the remaining ids in the same wave.
- An approved plan runs straight through: it stops only at the plan's gates, never to ask "continue?" between tasks.
