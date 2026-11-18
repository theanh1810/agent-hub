# Close the task (HARD)
<Owner: agents/implement.md § References>
<Read when: Workflow step 1 (a change's first spawn: its branch) and step 8 (closing a task)>

---

Order at each task's close: freeze the snapshot, tick the task, then commit (a commit first leaves `base` equal to `tip`: an empty review diff). Simplify runs once per run (§ Simplify).

## Simplify (once per run)

Implement runs the bundled `simplify` skill through the Skill tool once per run, limited to what it changed.
- **Small job (L2):** before reporting done, on the run's diff only.
- **Planned job (L3):** one implement pass (`mode=simplify`) after the last wave, over the whole run's change.
- Only inside `files_allowed[]`; re-run the tests after. Not run on the fast lane, a hotfix or a diff with no code file.
- A subagent that cannot invoke the skill skips it and reports `simplify: skipped, <reason>` in `## Risks`.

## Shortcuts

A deliberate shortcut gets a one-line comment stating the current limit and the upgrade path, in the repo's own TODO convention; `shortcut:` where the repo has none. At close list the run's shortcuts with `git grep` of that marker, in the handoff's `## Changes / Plan`.

## Commit

Author is the configured git/GitLab user (`gitlab.user`, or `~/.claude/gitlab-user.txt`); Claude appears only in the `Co-Authored-By:` footer. None configured: `needs_user_input`, never the default identity.

```bash
git -c user.name="$GIT_USER_NAME" -c user.email="$GIT_USER_EMAIL" commit ...
```

```
<type>(<scope>): <imperative summary>     # ≤72 chars, no trailing period, no emoji

<one bullet per logical change, each led by [area/file]: action>
<name the exact symbol, route, or class>

Refs: <change> / <task_id> / <ticket_id if any>

Co-Authored-By: Claude <noreply@anthropic.com>
```

- `type` ∈ `feat, fix, refactor, hotfix, chore, docs, test, perf, ci, build`; scope is the module; imperative present tense.
- The subject states intent and stands alone ("fix mail Reply-To header", never "Fix bug", "Phase 1", "Update code"), with `[<task_id>]` leading it. The body says why, admits what is weak, carries no `TODO`, and any confirmed bug hypothesis.
- **One local commit per task**, after its close steps pass; nothing is pushed. A fix or conflict-resolution commit after merge review is its own small commit.

## Branch

- Never commit to `main` or `develop`.
- A change has one branch: its first `implement` spawn creates `feat/<change>` off the target before any edit; every task commits there. Without a change folder: a feature branch and a local commit when the user asks.
- Push, MR and branch integration belong to `devops` on the user's word; never merge or review it.

## Write the result

At the task's start write `date -u +%Y-%m-%dT%H:%M:%SZ` to `.cm-tmp/{task_id}/run-started-at` unless it exists; `## Validation` takes start and finish from it and the clock.

- **Tick** the task's checkbox in `tasks.md` only when its `Done when:` is met by a command whose real exit code you read; otherwise leave it open and say why in `## Risks`. This is the only plan file a task edits. `plan.vi.md`, `design.md` and the spec deltas stay brainstorm's; only the closeout's drawing step rewrites `diagrams/`.
- **Handoff** carries the result: files changed with a note each, commands run with exit codes and counts (red and green phases for a TDD task), deviations, the shortcut list, and per meaningful change what, where (`file:line`), before, after, the mechanism, what the user sees or what else is touched, and the cost paid (never empty).
- A bug fix or hotfix with no change folder: write the adhoc record from `templates/adhoc/adhoc-record-template.md` (path: `refs/artifact-layout.md` § Where writing is allowed); that one record is exempt from `binding_scope`.
- **Closure invariant.** Return `completed` only when every task is ticked or carries its reason and the handoff states the commit.

## Closeout (closeout task only)

Closeout timing, owner and inline case: `refs/closeout.md` (top, and § End of a run); once per spawn.

1. **Reindex.** `refs/closeout.md` step 1, inside each sub-repo this run changed, never once at `{workspace_root}`.
2. **Diff is the planned diff.** Compare `detect_changes` with the union of the `Files:` of the tasks. A path no task named goes into `closeout.diff_matches_plan: false` with the path listed, never silently accepted. A diff touching a rule file also records `closeout.ruleset_gate` (`refs/closeout.md`). Then the rest of `refs/closeout.md` step 2, in its order: `agent-hub secret-scan {plan_dir}/`, in L3 `agent-hub check plan <change-dir> --stamped`, and last the review packet.
3. **Tasks are ticked.** Re-read `tasks.md`: each finished task is ticked, its commit in the handoff. A gap is reported.
4. **Spec** when `spec_required: true`: `refs/closeout.md` step 4; implement writes nothing under `openspec/`.
5. **claude-mem, then cleanup.** `mcp__plugin_claude-mem_mcp-search__search` first; a near duplicate is not saved again, a changed fact is a new save beginning `supersedes #<old id>: <reason>`. At most three new entries, only a test-confirmed root cause, a reusable pattern with `file:line`, or a pitfall that cost a real error loop. `memory: []` with a reason is correct.

Before step 5, the drawing step of `refs/diagram.md` (L3: confirm or update; L2: draw). Then the `closeout` block in the handoff, with `ruleset_gate` and `diagram`.

## Cleanup

`rm -rf {workspace_root}/.cm-tmp/{task_id}`; every sweep beyond that runs in the `after_approve` spawn (in L1, at closeout step 5; `refs/closeout.md § End of a run`). Then `git status --short` in each sub-repo this task changed: remove or gitignore every `??` line this task created outside its `Files:` (a planned new file is `git add -N`, intent-to-add, shown ` A`). With no git, `~/.claude-backups/{plan_id}/{task_id}/` stays: the review packet diffs against it, and the `after_approve` spawn deletes it (in L1, closeout step 5).

## Freeze for review

After its checks and before commit, a task freezes a snapshot its review reads while the next task runs, handed to main as `snapshot: {base, tip}`. A snapshot holds its own task alone.

- **Git tree.** a temporary copy of the index (`GIT_INDEX_FILE`), `git add -A -- <Files paths>`, `git write-tree` prints `tip`. `base` is `git rev-parse HEAD^{tree}`, or for a fix the reviewed task's last `tip`.
- **No git** (`~/.claude`). `cp -c` each file to `~/.claude-backups/{plan_id}/{task_id}/tip/<path>` (a fix to `tip-fix<k>/`); `base` is the task's pre-edit backup in `~/.claude-backups/{plan_id}/{task_id}/`, or for a fix the last `tip`.

## One spawn, one wave

One spawn runs every implement task of a wave, in order; each task is frozen, ticked and committed before the next starts. `binding_scope` is one object for the spawn; each task edits only its own `Files:`.

- A task whose intake fails, or that needs a file outside its `Files:`, stops the spawn there with `needs_revision` and `done_task_ids[]`.
- Context past the budget of `refs/context-policy.md` stops it at the next task boundary with `in_progress`, `done_task_ids[]` and `remaining_task_ids[]`.
- An approved plan runs straight through, never asking "continue?" between tasks.
