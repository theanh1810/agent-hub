# Turn budget — checkpoint and resume across a turn cap
<Owner: refs/gates.md, table A, row `in_progress`>
<Read when: an agent starts work it may not finish in one segment or nears the ceiling; main thread sees a spawn end partial, with no status, or on a watchdog stop; auditor measures `cap_hit_rate`>

---

Caps follow score and pass mark. A turn is one API request; the cap counts per segment, and a SendMessage resume starts a fresh segment keeping the history.

## What a cap is

`maxTurns` in an agent file's frontmatter (a spawn cannot pass another). At the cap Claude Code returns the output marked partial and main thread may resume it. A stop reading "no progress for 600s (stream watchdog did not recover)" is a hang, not a cap.

## The checkpoint

An agent cannot see its turn counter, so it rewrites its checkpoint at every phase boundary and at least every 10 turns; a cut costs at most 10 turns.

| Agent | Checkpoint |
|---|---|
| brainstorm (it also writes the plan; cap 80 turns) | the `progress:` key of `docs/brainstorm/{slug}.yaml` |
| test | `.cm-tmp/{task_id}/progress.yaml`, shaped by `refs/roles/test/resume.md` plus the keys `next_step`, `commands`, `pending_commands`, `constraints` and `reason` below |
| every other agent | `{workspace_root}/.cm-tmp/{task_id}/progress.yaml` |

```yaml
progress:
  phase: string        # the agent's own workflow step
  done: [string]       # finished and written, by id where one exists
  remaining: [string]
  segment: 1
  baseline: {head: string, dirty_paths: [string]}   # the restore point of the run, the shape `agents/implement.md` returns as `extra.baseline`; written by segment 1 and copied unchanged by every resume
  red_before_fix: {cmd: string, exit: 1, evidence_path: string}|null   # a bug task's regression test run on the unfixed code, the shape `agents/implement.md` returns; written by the segment that ran it, null for a non-bug task, copied unchanged by every later rewrite
  acceptance: {commit: string|null, files: [{path: string, sha256: string}], red: {cmd: string, exit: 1, evidence_path: string}}|null   # implement's `extra.acceptance` (`refs/roles/implement/sources.md § Acceptance tests`); written by the segment that recorded the acceptance run, null when no item applies, copied unchanged by every later rewrite
  tree:                # the working tree as this checkpoint leaves it
    head: string
    dirty_paths: [string]
    state: clean       # clean | mid_edit | tests_red (a tree both mid-edit and red is mid_edit)
    red_tests: [string]   # every test red at this point, by name, whatever `state` is; empty only when none is red
  constraints: [string]   # the task's limits, copied verbatim from the brief (a forbidden tool or command, a file not to touch)
  commands: [{cmd: string, exit: 0, evidence_path: string}]   # run in this segment; a resume repeats none that exited 0 unless the tree changed since
  pending_commands: [string]   # still to run, in order, runnable as written
  next_step: string    # the exact next action, runnable as written
  reason: string       # why the segment ended: soft_ceiling | hard_ceiling | read_budget | brief_limit
```

A resumed agent reads its checkpoint, skips `done`, starts at the first `remaining`, and is bound by `constraints[]` exactly as by its brief: a resume once ran a shell call its task forbade because the checkpoint did not carry the limit. An agent stopping on its own before its work is done (the ceiling below, read budget spent, a brief's limit) returns `status: in_progress` with `progress_path` and `reason`; a capped spawn returns nothing and its checkpoint stands in.

## The ceiling

The plugin counts a spawn's tool calls and tells it at each stop below (`hooks/moment.py`); with `moment_hooks` off, the spawn counts them itself from its first one. The count is the trigger it can observe; context size it cannot, so the harness guards that (§ The context backstop). Every call re-reads the whole context, so the calls past the ceiling cost the most.

- **Soft stop, 25 tool calls.** The agent finishes the unit it is in (implement: the task, to its commit; test: the case; reviewer: the round section; any other agent: the phase) and stops before starting the next one.
- **Hard stop, 40 tool calls.** The agent stops where it is, makes no further edit and records in `tree` what it leaves (its `state`, and `red_tests[]` whenever a test is red).

Two steps because a task that needs about 30 calls would never finish under one flat stop at 25, and `done`, counted per task id, would never grow.

At either stop the agent rewrites its checkpoint with every key filled and returns `status: in_progress` with `progress_path`, `reason` and what is left (`remaining_task_ids[]`; test: `remaining_test_case_ids[]`). A ceiling stop runs no gate: the gate of `refs/roles/implement/sources.md § Running the checks` runs only in the spawn that empties `remaining`.

Main thread continues a ceiling stop with one fresh spawn of the same agent carrying `resume: true` and the checkpoint path, since a SendMessage resume would carry the spent context along. A ceiling stop whose segment grew `done` stays outside the resume count of § Main thread on a cap; a hard stop that left `done` unchanged counts as one resume there, which bounds the hard-stop segments one task can take. A segment that ends with `done` not grown and `next_step` unchanged is stuck all the same. `maxTurns` stays above the ceiling as a backstop only, because a capped spawn hands back no report.

**Resuming from a ceiling stop.**
- The start check compares the tree with the checkpoint's `tree` in place of a clean tree: the same `head` and `dirty_paths[]` is the expected start, and a test named in `red_tests[]` is expected red. Any other dirty path, moved head or red test is `needs_user_input`.
- `baseline` stays the restore point of the whole run; a resume reports it unchanged and never replaces it with its own start.
- Reviewer and test continue the round section the earlier segment left half-written (`## Round {n} · {kind}`), appending to it; a new section is opened only for a new round.

**Loops as one command.** Three or more similar reads, greps or checks are written as one script or one shell command that prints only the summary (`refs/context-policy.md`, Think-in-code); each counts as a tool call otherwise, and this shape measured 37% fewer tokens.

## The context backstop

`autoCompactWindow` in the frontmatter of `agents/brainstorm.md`, `agents/implement.md`, `agents/reviewer.md` and `agents/test.md` makes Claude Code compact the spawn's history at that token count; the frontmatter is the only home of the number. The checkpoint on disk is what survives a compaction intact, so an agent that finds its earlier turns summarised re-reads its checkpoint before the next edit and continues from `next_step`.

## Main thread on a cap

1. A partial notice, or a spawn that ends with no status while its checkpoint lists `remaining`: SendMessage the same agent, "resume from <checkpoint>". The history stays.
2. At most 2 resumes per spawn, so 3 segments, each with `done` grown by at least one (for a ceiling hard stop a moved `next_step` counts as growth, § The ceiling); no growth is stuck — ask the user with the checkpoint.
3. A third cap: ask the user.
4. A watchdog hang: the agent is gone. One fresh spawn of the same agent with `resume: true` and the checkpoint path; it counts as one resume.
5. Spawn nothing downstream until it returns a status other than `in_progress`. A resume is not an error loop: `meta.error_loop_count` is untouched (`refs/error-loop.md`).

## Pass mark

Per role and tier, auditor measures `cap_hit_rate` (`agents/auditor.md`): first segments at the cap ≤5%, median resumes per spawn 0, stuck stops 0 or explained. Over 5% → raise that file's cap by 10; under 1% with p90 below half the cap → lower it by 10. Each change goes through brainstorm and the approval gate.
