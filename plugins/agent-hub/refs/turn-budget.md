# Turn budget — checkpoint and resume across a turn cap
<Owner: CLAUDE.md §2.1, table A, row `in_progress`>
<Read when: an agent starts work it may not finish in one segment; main thread sees a spawn end partial, with no status, or on a watchdog stop; auditor measures `cap_hit_rate`>

---

Caps follow score and pass mark. A turn is one API request; the cap counts per segment, and a SendMessage resume starts a fresh segment keeping the history.

## What a cap is

`maxTurns` in an agent file's frontmatter (values: the Turn caps table of `refs/effort-routing.md`; a spawn cannot pass another). At the cap Claude Code returns the output marked partial and main thread may resume it. A stop reading "no progress for 600s (stream watchdog did not recover)" is a hang, not a cap.

## The checkpoint

An agent cannot see its turn counter, so it rewrites its checkpoint at every phase boundary and at least every 10 turns; a cut costs at most 10 turns.

| Agent | Checkpoint |
|---|---|
| brainstorm | the `progress:` key of `docs/brainstorm/{slug}.yaml` |
| planner | `{workspace_root}/.cm-tmp/{plan_id}/progress.yaml` |
| test | `.cm-tmp/{task_id}/progress.yaml`, shaped by `refs/roles/test/resume.md` |
| every other agent | `{workspace_root}/.cm-tmp/{task_id}/progress.yaml` |

```yaml
progress:
  phase: string        # the agent's own workflow step
  done: [string]       # finished and written, by id where one exists
  remaining: [string]
  segment: 1
```

A resumed agent reads its checkpoint, skips `done`, starts at the first `remaining`. An agent stopping on its own before its work is done (read budget spent, a brief's limit) returns `status: in_progress` with `progress_path`; a capped spawn returns nothing and its checkpoint stands in.

## Main thread on a cap

1. A partial notice, or a spawn that ends with no status while its checkpoint lists `remaining`: SendMessage the same agent, "resume from <checkpoint>". The history stays.
2. At most 2 resumes per spawn, so 3 segments, each with `done` grown by at least one; no growth is stuck — ask the user with the checkpoint.
3. A third cap: ask the user.
4. A watchdog hang: the agent is gone. One fresh spawn of the same agent with `resume: true` and the checkpoint path; it counts as one resume.
5. Spawn nothing downstream until it returns a status other than `in_progress`. A resume is not an error loop: `meta.error_loop_count` is untouched (`refs/roles/orchestrator/error-loop.md`).

## Pass mark

Per role and tier, auditor measures `cap_hit_rate` (`agents/auditor.md`): first segments at the cap ≤5%, median resumes per spawn 0, stuck stops 0 or explained. Over 5% → raise that file's cap by 10; under 1% with p90 below half the cap → lower it by 10. Each change goes through brainstorm and the approval gate (`refs/effort-routing.md § Calibration data`).
