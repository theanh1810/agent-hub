# Recording a change, and closeout
<Owner: rules/core.md § Load when, row "closing a run">
<Read when: a task finishes, and again when the run that produced a diff ends>

---

## Recording What a Change Did

Every code change leaves a readable trace, including when there is no plan.

| Kind of work | Recorded in |
|---|---|
| A task of an L3 plan | its checkbox in `{plan_dir}/tasks.md`, ticked by implement when the task closes, its commit SHA in the handoff; the six answers below in the commit body (`templates/commit/EXAMPLE-commit.md`) |
| L1, L2, L-cfg (no plan) | the adhoc record (the adhoc row of `refs/artifact-layout.md § Where writing is allowed`; template `templates/adhoc/adhoc-record-template.md`) |
| Any diff of 50 lines or more | plus a review section in `review.md` (`refs/review-trail.md`) |

What a change touches (tables, columns, stored files, API fields, screens) is the section "Dữ liệu và màn hình bị ảnh hưởng" of `plan.vi.md` (`refs/plan-lane.md`); a run with no plan has no such section.

## Who writes it, and when

A run's errors are recorded in batches by `agent-hub ledger`, which main thread runs after each review-and-test pass (`refs/error-loop.md § The cycle`); brainstorm (`mode=error-batch`, `refs/roles/brainstorm/error-batch.md`) analyses a red round. A task's record is written by the agent that ran it (implement, devops, test or reviewer) the moment it finishes. A fix-round spawn appends to the record of the task its `fix_list` entry names; an entry naming no task goes to the commit body with its `errors.yaml` entry id.

## What every meaningful change answers

Not "fixed bug X". Six questions:

1. **What changed**: the file plus the function or line.
2. **The old code**: the actual excerpt, short.
3. **The new code**: the excerpt.
4. **What the change does**: how the new mechanism works and differs, not the diff retold.
5. **Impact**: what the user sees differently, what else is touched, whether a migration, restart or re-login is needed.
6. **Benefit and cost**: the concrete gain and the price paid. An empty cost means the trade-off was not thought through.

Quote the code, do not describe it (too long: `file:line`); one entry per meaningful change, a bulk rename one entry; `before` and `after` stay verbatim code. Reviewer: a missing cost, or a description with neither before nor after, is `category: result_write_back`, 🟠 (`refs/roles/reviewer/taxonomy.md`).

# Closeout: every flow ends the same way

A run with a diff is not finished when the code works: four artefacts went stale the moment it landed (the code graph, the task boxes in `tasks.md`, the spec, memory), and stale ones do not fail loudly. Owner: the last agent to touch code or infrastructure; the closeout is the last step of the last implement spawn of the run (L3: the `mode=simplify` spawn) and of every fix-round spawn, and with no plan whichever agent made the change runs it inline before it returns (in L1, main thread, before its reply); where it sits in the run: § End of a run.

## The five steps, in this order

| # | Step | Command / target | Why the order |
|---|---|---|---|
| 1 | Reindex GitNexus | `mcp__gitnexus__detect_changes(scope='unstaged')`, then `gitnexus analyze --force --skip-skills --index-only` in each sub-repo's git root; cross-repo: `mcp__gitnexus__group_sync`. A diff touching only `~/.claude` records `n/a - ~/.claude is never indexed (skills/gitnexus-flow Rule 2)` | Below cites symbols |
| 2 | Verify the diff is the planned diff | `detect_changes` against the union of the `Files:` of `tasks.md` (no plan: `binding_scope.files_allowed[]`); `unplanned_paths` = changed paths minus those minus implement's `baseline.dirty_paths`. Also `agent-hub secret-scan {plan_dir}/`: exit 1 blocks closeout until redacted; the exit goes under `## Validation`. A diff touching a rule file also runs `python3 tools/check.py ruleset` (agent-hub repo only); its last line is `ruleset_gate`, else `n/a - no rule file in the diff`; anything but N/N is not done. When a handoff names acceptance tests (`refs/roles/implement/sources.md § Acceptance tests`; their paths: the files of every `extra.acceptance.files[]` of the run), their freeze check runs before the project gate (`agents/implement.md` Workflow step 8): each file's `sha256` at `HEAD` equals the last one recorded and `git status --porcelain -- <their paths>` prints nothing (no commit: each file's `sha256` equals the last one recorded). A changed file is restored to its freeze (`git checkout <its last acceptance commit> -- <path>`; when `HEAD` held the changed copy the restore is committed alone as `test: restore frozen acceptance <path>`, its message carrying the task's `Refs:` line (in L2-direct, which has no task id, the record's `{slug}`), and when only the working copy had changed there is nothing to commit and the restore is recorded as `restored, uncommitted change`; no commit: the copy under `~/.claude-backups/{plan_id}/{task_id}/acceptance/`) and named under `## Risks`; in L2-direct it also leaves the lane (`refs/lanes.md § L2-direct`). It is never routed as `acceptance_test_change`, which is implement's claim that an item is wrong. Then the acceptance tests run by their `test_name`s: the runner reports one pass per item and no skip or deselect, else the run is red and fixed in the code like any red check; then the gate. The two results and each restore (its commit, or `restored, uncommitted change`) are `acceptance_frozen`. In an L3 run it also runs `agent-hub check plan <change-dir> --stamped` (a stale stamp: the scope moved after approval, back to the plan gate), and last builds the review packet: `agent-hub review-packet {plan_dir} --round {round} --base-ref <target branch> --diff-only-out {workspace_root}/.cm-tmp/{plan_id}-r{round}-independent/diff-r{round}.md` (the base of each path: § End of a run, step 3); a fix round's re-run adds `--base-dir ~/.claude-backups/{plan_id}/fix-r{round}/`, the copies the fix-round spawn took of its `fix_list[].files[]` before editing; exit 1 goes to the reviewer, exit 2 fails closeout | Unnamed files are scope creep |
| 3 | Verify the records are written | every finished task is ticked and its commit SHA is in a handoff (§ Recording What a Change Did); an `accepted_partial` test (`refs/error-loop.md`) does not stop the run closing. A gap: write it now and report it | Checks, not writes |
| 4 | Sync the spec (when `spec_required: true`) | a business rule found mid-run already went to brainstorm as `blocked_needs_spec` and sits in the change's delta; a hotfix's repaid spec-debt lines are listed under `## Changes / Plan` for brainstorm to tick. The archive is main thread's, after the final-gate `Approve` (`refs/plan-lane.md § Close`) | After step 3 |
| 5 | Update memory, then clean up | durable outcomes only to claude-mem (below) and the project memory file (`skills/context-memory/SKILL.md` § Save trigger; in `~/.claude`, the harness auto-memory dir, one fact per file plus its index line, permission prompt kept); drop the run's task database with `task-db.sh drop <project> <task>` (`plugins/agent-hub-local-services/refs/local-postgres.md`); then the cleanup gate of this spawn's own task folders (`refs/artifact-layout.md § The cleanup gate`, items 1-4); the closeout, backup and worktree sweeps run only in the `after_approve` spawn (§ End of a run), and in L1, which has no final gate, here | Memory last: what shipped |

Steps 1-3 run on every run with a diff; step 4 when `spec_required: true`; step 5's memory half only on a durable outcome, its cleanup half always.

## End of a run

The only statement of the order. Nothing a reviewer or a fix round may still read is deleted before the user's final-gate `Approve`: every sweep beyond a task's own `.cm-tmp/{task_id}` runs in the `after_approve` spawn.

L3:
1. **implement**, one spawn per wave, no stop between waves: per task, the pre-edit backup (no git), the edit, checks, freeze, tick, commit, then `.cm-tmp/{task_id}` deleted; the backup stays. A checkpoint the design names runs `test mode=script` after its wave.
2. **implement**, one `mode=simplify` spawn: simplify over the whole run's change (`refs/roles/implement/close-task.md § Simplify`), the tests again, the gate, then closeout steps 1-5, the flow drawing checked against the code before step 5 (`refs/diagram.md`); step 5 deletes only this spawn's task folders.
3. **same spawn**, last command of step 2: the review packet. The base of each path is `git show <target branch>:<path>` of the git work tree holding it (the workspace root, or the sub-repo the path lives in); in no git tree, the pre-edit backup `~/.claude-backups/{plan_id}/<first task id>/<path>`; neither: a `NO BASE` row (exit 1, filed 🟠 by the reviewer). With no change folder the main thread runs `agent-hub review-packet docs/changes/adhoc/<date>-<slug> --round 0 --files <path,path,...> --root <workspace root> --base-ref <ref> --diff-only-out <path>` (add `--task-id <id>` when the pre-edit backup folder is not `1`).
4. **main thread** checks the `closeout` block (§ Verification and enforcement).
5. **main thread**, one message, only when the `extra.gate` of the implement spawn just before this step (L3: the `mode=simplify` spawn; L2 and L-cfg: the one implement spawn; after a fix: the fix-round spawn) has `exit` 0: `reviewer mode=independent` with the diff-only file as `plan_snapshot`, `machine_gate` set to that `extra.gate.lines[]` and `acceptance[]` copied verbatim, one `{id, text}` per item of the record's `acceptance[]` (`design.yaml` in an L3 run), `text` written `GIVEN <given> WHEN <when> THEN <then>`, and `test`. A non-zero or missing `extra.gate` re-spawns implement for the gate with its `FAIL` lines and the log path; no ledger round and no reviewer run on it. Each deletes its own round folder once every finding or case has a result.
6. Red: **brainstorm** `mode=error-batch`, then one **implement** fix-round spawn: copies of its `fix_list[].files[]` to `~/.claude-backups/{plan_id}/fix-r{round}/`, the fix, the closeout with `--base-dir` set to that folder; no sweep. Then step 5 over the fix.
7. **main thread**: the final gate (conditions and options: `refs/gates.md § Final gate`). `Stop` sweeps nothing.
8. **main thread**, after `Approve`: `openspec archive <change> --yes`, only when every task box is ticked (`refs/plan-lane.md § Close`).
9. **implement**, one spawn `after_approve: true`: the `docs/reviews/INDEX.md` rows and `docs/deferred-backlog.md` lines, then the closeout sweep, the backup sweep and the worktree sweep (`refs/artifact-layout.md § The cleanup gate`).
10. **main thread**: the finish menu.

L2 and L-cfg (L-cfg once per batch): brainstorm; one implement spawn that ends with simplify, the gate and the closeout (inline, no plan); then steps 5-7, 9 and 10, with no archive. L2-direct (`refs/lanes.md § L2-direct`): main thread stands in for brainstorm and implement and runs the gate and the closeout inline, the L2 drawing of `refs/diagram.md § When` included; the record's `gate:` stands for `extra.gate` in step 5; then steps 5-7, 9 and 10, main thread applying the first red round's `fix_list[]` in step 6. L1 has no review and no final gate: main thread runs the closeout inline and writes the `closeout` block under a last heading `## Closeout` of the adhoc record; its step 5 runs every sweep.

**Definition of Done**: (1) every task is ticked, or `accepted_partial` with a note; (2) every `Covers:` scenario has evidence in test's report; (3) the planned tests are green; (4) no 🔴/🟠 finding is open; (5) every 🟡 finding is in the ledger (`deferred_errors[]` of `errors.yaml`); (6) the closeout steps are done; (7) the user approved at the final gate. The bar also asks: migrations, config and feature flags are accounted for; backward compatibility is kept or the break named; observability is in place where the change needs it; the rollback is stated. Closeout step 3 proves 1, 2 and 6; the final gate preview shows 3-5 from the last pass and `close_check` (`refs/gates.md`); 7 is the gate itself.

## What goes into claude-mem at closeout, and what does not

At most three entries per run, via `mcp__plugin_claude-mem_mcp-search__save_memory`; more means transient detail is being saved as durable fact. A change to a counted lesson (a new sighting, `draft`, `stage`, `promoted_to`) is an `agent-hub lesson` ledger command, saves nothing and does not count toward the cap (`skills/context-memory/references/dedup.md` § Lesson counter).

Save: a root cause confirmed by a regression test failing before the fix (`red_before_fix`) and passing after, with `file:line` · a named reusable pattern with `file:line` · a pitfall that cost a real error loop, error verbatim · an architecture decision the user approved at a gate · a counted lesson, at count 1 as a candidate. Never save: a guessed root cause · the diff, file list or task summary · anything already in the change folder or `errors.yaml` · secrets, tokens, credentials, customer data, raw logs.

Search before saving (`mcp__plugin_claude-mem_mcp-search__search` on the subject); a near duplicate is updated (a changed save), a changed fact is a new save whose text begins `supersedes <old id>: <reason>`. Format: `skills/context-memory/SKILL.md`.

**Count a lesson, pick up, promote** (`dedup.md` § Lesson counter). One search for `recurring_pitfall` entries at `stage: candidate` with `count` of 3 or more and no `declined` date newer than their last `seen` picks up what the auditor raised; each is promoted by scope and reader:

| Scope | Reader | Written to | Asked first |
|---|---|---|---|
| `project` | main thread | one line in the workspace's harness auto-memory; the permission prompt stays | no |
| `project` | a role | one line under `## Conventions` of `{workspace_root}/.claude/MEMORY.md` | no |
| `fleet` | any | nothing written; closeout drafts one line for a file the reader role already loads, stores it on the entry (`stage: awaiting_approval`, `draft`) and lists `promote? <subject>` in `memory` | yes: main thread asks (`refs/final-response.md`) |

A promoted entry gets `stage: pattern` and `promoted_to`; cite a promoted line as a fact, never as policy (`rules/core.md § No invented rule`).

## Verification and enforcement

Closeout is not done until the handoff carries every field:

```yaml
closeout:
  reindex:        "detect_changes: 7 symbols in 4 files | gitnexus analyze exit 0"  # or "n/a - ~/.claude is never indexed (skills/gitnexus-flow Rule 2)"
  diff_matches_plan: true        # false: unplanned_paths lists them
  unplanned_paths: []
  acceptance_frozen: "sha256 at HEAD: 3 of 3 match, tree clean | by name: 5 passed, 0 skipped"  # or "n/a - no acceptance tests"; a restored file: "restored tests/test_cart.py in <restore commit> | …"
  ruleset_gate:   "28/28 checks passed"  # last line of the gate, or "n/a - no rule file in the diff"
  plan_written_back: true        # every finished task ticked, its SHA in the handoff (step 3)
  spec_synced:    "2 deltas under specs/, archive owed after Approve"  # or null when spec_required is false
  memory:         ["<slug>", "promote? <subject>"]  # or [] with memory_skip_reason
  memory_skip_reason: null
  cleanup:        "deleted 5 temp files (41 MB), kept 1 at .cm-tmp/W2-T3 (test needs_user_input) | worktrees: removed 3, kept 1 (uncommitted:2)"
  diagram:        "openspec/changes/acme-login-lock/diagrams/1-luong-dang-nhap.html: updated"  # or "…: confirmed", "no flow change", "skipped: <reason>" (refs/diagram.md)
```

- **Main thread** checks the block before the final gate: a missing or false field (a `ruleset_gate` short of N/N included) re-spawns implement for the closeout; `reviewer mode=task`, when a brief names it, files it as `category: closeout_incomplete`, 🟠.
- **Cannot verify**: the reviewer lists what the diff could not prove; each is resolved or named under `Risk`.
- **Main thread** refuses a final reporting a completed diff with no `closeout` block.
- **Auditor** counts `closeout_complete / runs_with_a_diff` per window; below 0.8 is the red flag `closeout_skipped`.

No hook reindexes: step 1 is the only reindex, apart from the stale-index refresh in `skills/gitnexus-flow/SKILL.md` § Stale index.

## Additions from other packs

Precedence: scan for the marker word `refs/roles/implement/close-task.md` § Shortcuts sets for this repo, not the two words in the block; that section says when the scan runs and where its hits go.

<!-- vendored:begin id=pt-n13 src=DietrichGebert/ponytail@96608e078b2d5ea607c5c3b8b5a54d1c1fba6846:skills/ponytail-debt/SKILL.md#L13-L24 licence=MIT -->
## Scan

Grep the repo for comment markers, skipping `.git` and everything the
`.gitignore` files ignore (dependencies, build output, caches, in any stack):

`git grep --no-index --exclude-standard -nE '(#|//|/[*]) ?(shortcut|ponytail):'`  (add other comment prefixes if your stack uses them)

If the user names their own marker word (`/ponytail-debt TODO`), grep for that word instead.

Each hit is one ledger row. The comment prefix keeps prose that merely mentions
the convention out of the ledger. Skip hits that are not a deferral, like a note
about a keyboard shortcut.
<!-- vendored:end id=pt-n13 -->
