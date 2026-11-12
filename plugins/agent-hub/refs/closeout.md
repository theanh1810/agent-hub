# Recording a change, and closeout

Tier 3 of `CLAUDE.md` §20 and §21 — the rules live here; `CLAUDE.md` keeps one pointer line per section.
Read when: a task finishes, and again when the run that produced a diff ends.

---

# 20. Recording What a Change Did (HARD)

Every code change leaves a readable trace, **including when there is no plan**.

| Kind of work | Recorded in |
|---|---|
| A task inside a plan | that task's `result`, in its task record only (its entry in `plan.yaml`; a legacy split plan keeps it in the task file, `refs/plan-files.md § Two formats`); a mirror, when the plan has one, carries `status` and the `Result` block of § The result in the mirror |
| A fix with no plan | the adhoc record, the adhoc row of `refs/artifact-layout.md § Where writing is allowed` |
| Any diff ≥50 lines | plus the §16 review section in `review.md` (`refs/review-trail.md`) |

## Who writes it, and when

**Bookkeeping split**: a run's errors are recorded batched by brainstorm (`mode=error-batch`, `refs/roles/brainstorm/error-batch.md`). A task's `result` is written by the agent that ran it (implement, devops, test or reviewer) into its own task record the moment it finishes, so an interruption loses at most the mirror. The `wave_commit` spawn of implement (after the user's final gate) is bookkeeping only, no push: it adds `result.commits` and `status: done` to every task of the plan's waves, rebuilds each wave's block of `plan.<lang>.md` (when the plan has one) from the task records in one locked pass, and appends the plan's rows to `docs/reviews/INDEX.md` (`refs/roles/implement/close-task.md` § Wave commit). Push, PR/MR and branch integration are devops's at the plan's end (`skills/devops-deploy/references/integration.md`). An implement fix-round spawn appends only to the `result.deviations` of the task its `fix_list` entry names; an entry naming no task goes to the closeout task's `result.changes[]` with all eight fields and its `errors.yaml` entry id. `plan.<lang>.md` is rebuilt after the task records, so an interruption leaves it claiming **less** than the truth. `test` and `reviewer` are read-only for **production code**, not plan files.

**The write protocol, stated here only.** Every write to `plan.<lang>.md` or a task record: take `.cm-tmp/plan-writeback.lock` via `os.mkdir` with sleep retries → re-read `plan.<lang>.md` and the whole file holding the task record **fresh inside the lock** (all of `plan.yaml`; in a legacy split plan the one task file, never its index, `refs/plan-files.md § Writing status and result`) → temp file plus `os.replace` → `yaml.safe_load` → **raw `sed -n` read-back of the edited block with both boundary lines** → `os.rmdir` in `finally`. A task finding the lock held **waits and retries**; skipping the write is never the answer.

## What every meaningful change answers

Not "fixed bug X". Six questions:

1. **What changed**: the file plus the function or line.
2. **The old code**: the actual excerpt, short.
3. **The new code**: the excerpt.
4. **What the change does**: how the new mechanism works and differs, not the diff retold.
5. **Impact**: what the user sees differently, what else is touched, whether a migration, restart or re-login is needed.
6. **Benefit and cost**: the concrete gain and **the price paid**. An empty cost means the trade-off was not thought through.

Fields in `result.changes[]`: `what` · `where` · `before` · `after` · `explanation` · `impact` · `benefit` · `cost`. In a task with `steps[]`, a step done as planned is one entry of `step: n` plus `explanation` · `impact` · `benefit` · `cost` (before/after are the step's); a deviating step or a fix outside the plan carries all eight. Same fields in both artifacts; language: in the plan's yaml `agents/planner.md` § Language, in a `docs/changes/adhoc/` record the reply language. `before` and `after` stay verbatim code. Worked shape: `templates/plan/task-template.yaml`.

Fields in `result.ac_check[]`, one entry per `acceptance_criteria[]` item, never omitted: `ac` (`AC-n`) · `met` · `evidence` (`file:line`, `file:a-b` of a line the task changed inside its `files[]`, or an `evidence_path`) · `tc_ids` (the task's test cases whose `covers_acceptance` names this AC) · `note` (one or two sentences; language per `agents/planner.md` § Language). `met: true` needs ≥1 `evidence` item and, per `tc_id`, a `result.commands[]` row with that `tc_id` and `exit: 0`; an AC no case covers carries `tc_ids: []` and `evidence` alone. `met: false` keeps the task at `reviewing` with the `note` naming what is missing. Entries come from the cases' exits, never from intent, in the same locked write as the rest of `result`.

## Data impact

The record of a change also holds its run window and its data impact, the part a script reads: `agent-hub change-map` turns them into `{plan_dir}/change-map.md` and a throwaway `change-map.json` under `.cm-tmp/{plan_id}/`, or for an adhoc change `change-map.md` beside its record in `docs/changes/adhoc/{YYYY-MM-DD}-{slug}/` and the JSON under `.cm-tmp/{YYYY-MM-DD}-{slug}/` (`refs/plan-files.md § Run files`). A task `result` carries both blocks; a change with no plan carries them in the front matter of its adhoc record; the fast lane is not exempt.

**`result.run`** is `{started_at, finished_at}`, ISO 8601 UTC with seconds. Implement writes `date -u +%Y-%m-%dT%H:%M:%SZ` into `.cm-tmp/{task_id}/run-started-at` at task start unless that file exists, so a resumed task keeps its first start, and takes `finished_at` at the result write (`refs/roles/implement/close-task.md` § Run window).

**`result.data_impact`** holds the 13 declared keys below, in this order, every one present. A value is a list of entries, or the string `none: <one-line reason>`; `where` is `file:line`.

| Key | Entry |
|---|---|
| `purpose` | one string per entry: what the change does |
| `flow` | `{step, where}` |
| `ui` | `{screen, change, where}` |
| `endpoints` | `{kind: http\|tauri\|socket\|cli, name, change: added\|changed\|removed, where, request_fields, response_fields}` |
| `db_schema` | `{table, columns, change, migration, rollback}` |
| `data_reads` | `{source, where, fields}` |
| `data_writes` | `{target, where, fields, api_fields}` |
| `business_rules` | `{rule, ac}` |
| `access` | `{surface, who, where}` |
| `events_jobs` | `{kind, name, where}` |
| `config` | `{key, file, meaning, default}` |
| `code_changes` | `{file, symbol, before, after}`, behaviour in words, never code text |
| `risk_rollback` | one object `{risks: [string], rollback: string}` |

Every path in `files_changed` and `code_changes[].file` is relative to {workspace_root}, a sub-repo path carrying its folder (`api/src/a.py`).

Three more keys of the change map are derived, never declared: `dependencies`, `tests` and `mismatch`. `agent-hub change-map` fills them from git, `result.ac_check`, `result.verification` and a cross-check of the declaration against the diff. The map of record is the one the `wave_commit` spawn regenerates after writing `done` and the SHAs (`refs/roles/implement/close-task.md` § Wave commit); the per-task run gives an interim view.

When a check cannot run, the map says so in `auto_limits` instead of reading clean: `no_git` (no git root), `no_commit` (a task with a result has no commit), `commit_unknown` (a commit no root knows), `no_specs` (no `docs/specs/use-cases`, `docs/changes` or `docs/specs/changes`); each task carries its own list and the change's list is their union; a task with `no_commit` or `commit_unknown` gets no diff rule.

**Language**: free-text values are written in the reply language (with diacritics where it has them), the one exception to the English yaml of `agents/planner.md` § Language; keys, the `none:` prefix, enum values, paths, symbols and commands stay verbatim.

**A mismatch warns and never blocks**: `agent-hub change-map` exits 0 whatever it finds, and a non-zero exit goes into `result.deviations`. `plan-verify` shows a mismatch as a WARN and fails only a done task, in a plan marked `validation_strategy.change_record_standard: 1`, that lacks `run` or a key; an unmarked plan predates the rule and is skipped.

## Rules

**Quote the code, do not describe it** (too long → `file:line`); one entry per meaningful change, a bulk rename one entry. Reviewer: a missing `cost`, or a description with neither before/after nor its `step`, is `category: result_write_back`, 🟠; every `result.ac_check[]` entry is checked against the diff and `result.commands[]` (`refs/roles/reviewer/taxonomy.md`, `result_write_back` and `prd_compliance`).

# 21. Closeout — every flow ends the same way (HARD)

A run with a diff is **not finished when the code works**: five artefacts went stale the moment it landed (GitNexus graph, plan record, spec, mem0, temp directory), and stale ones do not fail loudly.

**Owner**: the last agent to touch code or infrastructure. With a plan, the `closeout` task in the final wave (`agents/planner.md`); without one, whichever agent made the change, inline, before it returns.

## The five steps, in this order

| # | Step | Command / target | Why the order |
|---|---|---|---|
| 1 | **Reindex GitNexus** | `mcp__gitnexus__detect_changes(scope='unstaged')`, then `gitnexus analyze --force --skip-skills --index-only` in the repo root; cross-repo → `mcp__gitnexus__group_sync`. A diff touching only `~/.claude` records `n/a - ~/.claude is never indexed (skills/gitnexus-flow Rule 2)` | Everything below cites symbols; reindex first |
| 2 | **Verify the diff is the planned diff** | `detect_changes` vs the union of `files[].path` over every task record; `unplanned_paths` = changed paths minus those minus `baseline.dirty_paths` of implement's result (a baseline path that changed further is still reported). Also `agent-hub secret-scan {plan_dir}/` and over the session's `docs/errors/` entries: exit 1 blocks closeout until redacted; the exit is recorded as `secret_scan`. A diff touching a rule file (any file `tools/check ruleset (package repo only)` reads, `docs/changes/` records included) also runs `tools/check ruleset (package repo only)`: its last line is `ruleset_gate`, else `n/a - no rule file in the diff`; anything but N/N means not done. On a `~/.claude` ruleset plan, closeout re-runs only that and the `verification` lines of each task fixed after its review. In a plan under the final review gate, the `closeout` task's last command is `agent-hub review-packet {plan_dir} --round {round} --diff-only-out .cm-tmp/{plan_id}-r{round}-independent/diff-r{round}.md` (`refs/roles/orchestrator/gates.md` § Final review gate, step 1); a fix round's re-run adds `--base-dir ~/.claude-backups/{plan_id}/fix-r{round}/`, the copies the fix-round spawn took of its `fix_list[].files[]` before editing: exit 1 (a NO BASE or not-run row) goes to the reviewers, exit 2 fails closeout | A file no task named is scope creep or an unrecorded decision |
| 3 | **Verify the result is in the plan** | every task at `done` or `accepted_partial` carries a non-empty `result` in its task record and, in a git tree, its wave's SHA in `result.commits`, plus, when the plan has a mirror, a `status` and its `Result` block there (§20); an `accepted_partial` test task (`refs/roles/orchestrator/error-loop.md` step 4) does not stop the plan closing. A gap → write it now and report it | Closeout checks rather than writes; `status: done` over an empty `result` is the 🔴 below |
| 4 | **Sync the spec** | write back every `spec_delta[]` into the UC, bump `## History`, fill `### Test mapping` from test's `ac_coverage[]`, tick any repaid `specs/_debt.md` line; a plan in `docs/changes/` is closed by brainstorm per `SDD.md` § 3.1, which archives its folder to `docs/changes/archive/{YYYY-MM-DD}-{plan_id}/` | After step 3, so it can cite the recorded task ids |
| 5 | **Update memory, then clean up** | save only what §6 calls durable to mem0 (below) and to the project memory file per `skills/context-memory` § Save trigger (in `~/.claude`, the harness auto-memory dir `projects/<slug>/memory/`, one fact per file plus its `MEMORY.md` index line; that write keeps its permission prompt on purpose); drop the run's own task database with `task-db.sh drop <project> <task>` (`refs/local-postgres.md`); then the §19.3 cleanup gate and its *Closeout sweep* and *Worktree and litter sweep* of every `.cm-tmp/{task_id}` of the plan, unasked; a run with no plan is swept after its gate | Memory last, so it records what shipped, not what was attempted |

Steps 1-3 run on **every** run with a diff; step 4 when `spec_required: true`; step 5's memory half only on a durable outcome, its cleanup half always. With a plan, step 3 also closes the Definition of Done section of `plan.<lang>.md`: the seven Definition of Done boxes below, with one box per entry of `requirements[]` (ticked when every task naming it in `covers_requirements` is `done` with its cases passed) nested under item 2 and one per condition of `validation_strategy.final` nested under item 3, never another source (`templates/plan/plan.lang-template.md`); a box a recorded `result` or verification line proves becomes `- [x]`, and under each box left `- [ ]` one indented line says why. A change counts as done only when the Definition of Done below holds.

**Definition of Done**:

1. every task is `done` or `accepted_partial` with a note;
2. every AC has evidence;
3. the planned tests are green;
4. no 🔴/🟠 finding is open;
5. every 🟡 finding is in the ledger (`deferred_errors[]` of `errors.yaml`);
6. the closeout steps are done;
7. the user approved at the final gate.

The bar also asks, for the change it closes: migrations, config and feature flags are accounted for; backward compatibility is kept or the break named; observability (logs, metrics, alerts) is in place where the change needs it; the rollback is stated. The bar is fixed under deadline: a due date removes no item.

Who ticks: closeout step 3 ticks 1, 2 and 6; the final gate preview shows 3-5 from the last pass and `close_check` (`refs/roles/orchestrator/gates.md` § Final review gate, step 4); the `wave_commit` spawn writes 3-5 and 7 (`refs/roles/implement/close-task.md` § Wave commit).

## What goes into mem0 at closeout, and what does not

`add_memory` at most **three** entries per run; more means transient detail is being saved as durable fact. A closeout change to a counted entry (increment, `draft`, `stage`, `promoted_to`) is an `update_memory` resending the whole metadata and does not count toward the cap (`skills/context-memory/references/dedup.md` § Lesson counter).

Save: a root cause **confirmed by a regression test failing before the fix (`red_before_fix`) and passing after**, with `file:line` · a reusable pattern, named, with `file:line` · a pitfall that cost a real error loop, error verbatim · an architecture decision the user approved at a gate · a confirmed flake and its workaround · a counted lesson, at count 1 as a candidate (`dedup.md` § Lesson counter). Never save: a guessed root cause · the diff, file list or task summary · anything already in plan files or `errors.yaml` · secrets, tokens, credentials, customer data, raw logs · a one-off or "might be useful later" (except a counted candidate).

**Search before saving.** `mcp__mcp_mem0__search_memories` on the subject first; a near duplicate is **updated**, not added (1370 transient entries once piled up). Format: `skills/context-memory/SKILL.md`.

**Agent memory.** A lesson that helps one role do its job goes to that agent's memory, at most once per run, at closeout: `skills/context-memory/SKILL.md` § Save trigger.

**Count a lesson, pick up, promote** (`dedup.md` § Lesson counter). One search for `recurring_pitfall` entries at `stage: candidate` with `count` ≥3 and no `declined` date newer than their last `seen` picks up what the auditor raised; each is promoted by scope and reader:

| Scope | Reader | Written to | Asked first |
|---|---|---|---|
| `project` | main thread | one line in the workspace's harness auto-memory (`~/.claude/projects/<slug>/memory/`: a topic file plus its index line); the permission prompt stays | no agent question |
| `project` | a role | one line under `## Conventions` of `{workspace_root}/.claude/MEMORY.md` | no |
| `fleet` | any | nothing written; closeout drafts one line for a refs or skill file the reader role already loads, stores it on the entry (`stage: awaiting_approval`, `draft`), lists `promote? <subject>` in the block's `mem0` value and says so in the handoff next step | yes: main thread asks (`refs/final-response.md`) |

A promoted entry gets `stage: pattern` and `promoted_to`; a promoted line is a memory fact with its count and sources: cite it as a fact, never as policy (`CLAUDE.md` §0.3).

## Verification and enforcement

Closeout is **not done** until the handoff carries every field, with evidence:

```yaml
closeout:
  reindex:        "detect_changes: 7 symbols in 4 files | gitnexus analyze exit 0"  # or "n/a - ~/.claude is never indexed (skills/gitnexus-flow Rule 2)"
  diff_matches_plan: true        # false → list the unplanned paths
  ruleset_gate:   "28/28 checks passed"  # last line of the gate, or "n/a - no rule file in the diff"
  secret_scan:    "exit 0"       # step 2; exit 1 blocks closeout until redacted
  plan_written_back: true        # every done task, both files (§20)
  spec_synced:    "UC-042/AC-3 updated, History bumped"  # or "n/a — spec_required false"
  mem0:           ["<slug>", "promote? <subject>"]       # or [] with a reason
  memory_file:    ["<path written>"]                      # or [] with a reason
  cleanup:        "swept 5 .cm-tmp folders (41 MB) | kept .cm-tmp/W2-T3 (test needs_user_input) | kept 2 at docs/changes/P-14/evidence/ | worktrees: removed 3 (2.1 GB, 1 pinned), kept 1 (uncommitted:2)"
```

- **Reviewer**: a missing or false field (a `ruleset_gate` short of N/N included) is `category: closeout_incomplete`, 🟠; `plan_written_back: false` beside `status: done` is 🔴.
- **Cannot verify**: the reviewer lists what the diff could not prove; each item is resolved or named under `Risk` before the task is `done`.
- **Main thread** refuses a §12 final reporting a completed diff with no `closeout` block.
- **Auditor** counts `closeout_complete / runs_with_a_diff` per window; below 0.8 → red flag `closeout_skipped`.

**No hook reindexes.** The gitnexus hooks (`postpush-reindex.cjs` among them) were removed from `settings.json`; step 1 is the only reindex, apart from the stale-index refresh in `skills/gitnexus-flow` § Stale index.

## The result in the mirror

When the plan has a mirror (`plan.<lang>.md`, `refs/plan-files.md § Run files`), it shows a finished task's result as one `Result` block per task whose `result` is not null, rendered in the reply language: the labels below are the English names, and the mirror translates them. Every row reads a field of `result`.

| Id | Label | From `result` | Shown | Rendering |
|---|---|---|---|---|
| C1 | `What was done` | `summary` | always | one short paragraph |
| C2 | `Real changes` | `changes[]`: `what`, `where`, `impact`, `benefit`, `cost` | logic task | one line per entry, `before` and `after` quoted verbatim; an entry of `step: n` takes them from `steps[n]`; an empty list reads `result.changes: []` |
| C3 | `Against the plan` | `deviations`, and every step with `done: false` | always | `as planned` when there is neither |
| C4 | `Criteria met` | `ac_check[]`: `met`, `evidence`, `tc_ids` | always | one line per AC, `evidence` verbatim |
| C5 | `Tests run` | `commands[]`: command, `exit`, `tc_id` | always | a case not run names who runs it and when |
| C6 | `Left over` | `deviations`, `specs/_debt.md` ids, review finding ids | when present | one line each |
| C7 | `Commit` | `commits` | always | `commits: []` on a tree with no git |

The block is written whole each time a wave is rebuilt (§ Who writes it, and when), never by hand, so it and the task record cannot disagree. Prose is in the reply language (`agents/planner.md` § Language); ids, paths, commands, shas, AC and test-case ids and `file:line` evidence stay verbatim.
