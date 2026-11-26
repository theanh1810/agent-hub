# Gates
<Owner: rules/core.md § Routing>
<Read when: a worker returns a `status` or a `needs_*` flag, a gate is due, an approval stamp or the rulings ledger is written, or a gate is skipped>

---

**A. Blocking `status` — spawn nothing else until resolved.** Every blocking value an agent can return is listed; `completed` blocks nothing. A blocking status with no row is a bug in this table, not licence to improvise. A return's shape is checked when the subagent stops (`hooks/return_check.py`, at most two refusals). A return that arrives with the note "returned with N unfixed problems", and every return while the hooks are off, is saved to a file and checked with `agent-hub return-check <file>` before its `status` is routed; exit 1 re-spawns the same agent with the printed problems (`refs/roles/reviewer/taxonomy.md`, `handoff_incomplete`).

| Status | Returned by | Main thread does |
|---|---|---|
| `needs_user_input` | brainstorm · designer · devops · implement · reviewer · test | `AskUserQuestion` with `user_questions[]`, re-spawn the asker with `user_answers[]` (brainstorm: `mode=clarify-followup`) |
| `awaiting_user_choice` | brainstorm | surface `candidates[]` + `recommended_candidate`, re-spawn brainstorm with `chosen_candidate_id` (L3: `mode=plan-write`). With `spec_only: true` (`/spec new`): show `requirement_text`, ask "Add to the live specs?"; yes: `openspec archive spec-<name> --yes`; no: the folder stays a draft (`refs/roles/brainstorm/spec-layer.md § spec-only draft`) |
| `needs_design` | brainstorm | spawn designer, re-spawn brainstorm `mode=design-followup` |
| `needs_prototype` | brainstorm | implement `mode=prototype` in a throwaway worktree, re-spawn brainstorm with the result; once per change |
| `needs_more_context` | designer | hand over the named artifact, re-spawn; never let it proceed on a guess |
| `needs_revision` | brainstorm · devops · implement · reviewer · scout · test | the input was wrong: route by `reason` to the agent that produced the artifact, never back to the reporter. A plan gap (`plan_internal_conflict`, `task_schema_incomplete`) or, after approval, `plan_change_required`: `brainstorm mode=error-batch`; before the plan gate: `brainstorm mode=plan-write`. `acceptance_test_change` (implement holds an acceptance item wrong): `brainstorm mode=error-batch`, `round_source: plan-gap`, in every lane (no plan: the record's path in `context_hints[]`). `devops_op_not_simple`: devops on opus. A mid-run user change waits for the final gate |
| `in_progress` | brainstorm · designer · devops · implement · reviewer · test | a ceiling or turn-cap stop, not a verdict: resume it as `refs/turn-budget.md` states (§ The ceiling, § Main thread on a cap), which alone holds the resume count; brainstorm with `effort_rise_requested: true` goes one rung up (`refs/effort-routing.md`), at most 2 rises. Not an error loop |
| `blocked_needs_spec` | implement | a business rule exists in no scenario: brainstorm drafts it and asks the user; no code before. A hotfix records the spec-debt file and continues (`rules/SDD.md`) |
| `needs_design_clarification` | designer · implement | the loop hit its cap of 2: designer with the exact question, then the user; no third pass |
| `needs_approval` | devops | surface change, blast radius and rollback path; re-spawn only on approval, which never carries to the next step |
| `needs_user_decision` | main thread | the error-loop cap is reached (`refs/error-loop.md`) or reviewer and implement still disagree after one exchange: surface `errors.yaml` + `fix_list` history with the options of that file |
| `failed` | any | no blind retry: report the reason under `Risk` and ask; a retry needs a changed input |

**B. Booleans — these add a wave, they do not stop one.**

| Flag | Set by | Effect |
|---|---|---|
| `needs_devops` | brainstorm · designer · implement · test | one devops wave (a log fetch included), then re-spawn the asker with devops's output verbatim |
| `approval_required` | brainstorm | the approval gate is on for this task |
| `recommend_scan[]` non-empty | brainstorm | one scout per entry, an entry with `doc_sources[]` carrying `cache_refs[]` (`refs/research-cache.md § Before a research spawn`); each returned `cache_pending[]` file: `agent-hub cache promote <slug>`, its `Ruling:` line into the ledger; then re-spawn brainstorm with `scout_results_refs[]` |
| `needs_repro` | brainstorm | `test mode=script` runs `repro_request`, output passed back verbatim |
| `second_opinion_request[]` non-empty | reviewer, first pass | one spawn per entry, all in one message; annex path, triage and the skip record: `refs/roles/reviewer/second-opinion.md` |

Reviewer's `verdict` (`pass` · `needs_changes` · `blocking`) is a separate vocabulary: `needs_changes` and `blocking` go to one brainstorm error-batch, never straight to implement. Main thread runs `agent-hub ledger` on every review-and-test pass before that spawn (`refs/error-loop.md § The cycle`, step 1), then `agent-hub secret-scan <errors file>` on every round whatever its verdict, masking a hit fully and rescanning until exit 0: a yellow or green round spawns no brainstorm, so no later step scans it. A run with no plan puts its returns under `.cm-tmp/{change_id}/returns/`, the change id being the `<id>` of `docs/changes/<id>/` (L-cfg) or the `{YYYY-MM-DD}-{slug}` of its adhoc record (L2) (`refs/artifact-layout.md § Where writing is allowed`).

# Gate procedures

Each approval covers one step, never the next. Gates and irreversible actions are the only stops.

**Clarify.** Surface `user_questions[]`: at most 5, most important first (`refs/roles/brainstorm/intake.md`). **Approval.** Show `candidates[]` and wait for the pick; fires on `approval_required`: L3 work, and in L-cfg a structural change only; never for L1, L2, L-inv, `error-batch`.

**Plan gate (L3, always on).** After `agent-hub check plan openspec/changes/<change>` passes (it runs `openspec validate --strict` itself), ask "Plan ready — approve to start implement?" with the `plan.vi.md` overview, its `Bản vẽ:` line, and the first wave's tasks (a `spec-convert` result is approved here too). Options: `Approve & implement` (Recommended) | `Edit plan` | `View plan details` | `Cancel`, shown in the reply language. Approve: stamp, then wave 1. Edit: `brainstorm mode=plan-write` with the notes; a plan edited after the stamp comes back here: `agent-hub check plan` prints its stale stamp as `PENDING 4` and passes, main thread asks this gate again showing what changed since the stamp, and on `Approve` runs `agent-hub stamp plan` with the user's new words (the earlier words stay in `approval.md`). Before each implement wave main thread runs `agent-hub check plan <change-dir> --stamped`; short of 5/5 the plan returns to this gate; a user who runs unapproved gets a bypass entry `approval-gate`. Only the user's explicit "no plan approval needed" skips it. <!-- scrub-allow: pinned Vietnamese label -->

**Approval stamp.** `agent-hub stamp plan <change-dir> --words <file>`, the user's words saved verbatim in the file; what it hashes and what breaks it: `refs/plan-lane.md § Approval stamp`.

**Hedged approval is not approval** (`rules/core.md § Ask, never guess`): nothing is stamped or started; a second hedge is the same open gate. Plan, final and devops gates, every permission mode.

## Final gate

Once per run (L-cfg: per batch), after review and test. The steps before and after it, with their owners: `refs/closeout.md § End of a run`. Checkpoints: `refs/roles/test/checkpoint.md`; the review is `reviewer mode=independent` (blind, `skills/review-checklist/references/independent.md`) beside `test`; red (`needs_changes`, `blocking`, `gate: RED`) goes to `brainstorm mode=error-batch`; `cap_reached: true` is `needs_user_decision`. When the last round is green or yellow and `close_check` is PASS, ask once "<change> done — approve?" showing the diff summary, the flow drawing (`refs/diagram.md`) and test report per task, the reviewer's verdict and, apart, each annex finding with its triage result, the seven Definition of Done items (`refs/closeout.md`), the rulings list and `meta.pending_user_changes[]`. Options: `Approve` (Recommended) | `Request changes` | `View full diff` | `Stop`. `Request changes`: once per run, a round `source: user-final-gate` outside the cap, then a fix round and review and test over its diff (`refs/closeout.md § End of a run`, steps 6 and 5); red inside it: roll back that round, accept partial or a new plan. `Stop` saves state and sweeps nothing. After `Approve` and the `after_approve` spawn, a finish menu once: `Push and open a PR` (Recommended, devops) | `Merge locally` | `Keep the branch`; discarding needs the user to type `discard <branch>`. No skip condition.

**After Approve.** Task commits are local, never pushed (`refs/roles/implement/close-task.md § Commit`). After the final-gate `Approve` main thread runs `openspec archive <change> --yes` (L3), then spawns implement once with `after_approve: true` for bookkeeping only: one `docs/reviews/INDEX.md` row per review file of the run, each `deferred_errors[]` line appended to `docs/deferred-backlog.md`, then the closeout, backup and worktree sweeps (`refs/closeout.md § End of a run`, step 9; what each deletes: `refs/artifact-layout.md § The cleanup gate`). It edits no source and nothing under `openspec/`. Every run that reached a final gate gets it.

## Rulings ledger

Main thread appends every `Ruling:` line (format: `rules/core.md § Ask, never guess`), its own and each one a return carries, to `.cm-tmp/{plan_id}/rulings.md` as it writes or reads it, one line each, in order; the file outlives a compaction, the conversation does not. At the final gate it lists every line of that file in the reply, before any cleanup.

<!-- owned:begin id=sp-rulings-head -->
Upstream text (obra/superpowers, MIT):
<!-- owned:end id=sp-rulings-head -->
<!-- vendored:begin id=sp-rulings-list src=obra/superpowers@22f0b463e7a5e579904dd6211a520321035526f7:skills/subagent-driven-development/references/final-review.md#L35-L42 licence=MIT -->
Before you delete anything, collect every ledger line containing `Ruling:` —
preflight rulings, parked findings, breaker adjudications, all of them — into
your final message under "Rulings I made", in the order you made them, each
with what it costs if wrong. The list is exhaustive: if the ledger holds a
ruling, the list holds it. That list is the only place the decisions you
took on your human partner's behalf reach them — they read it and rework
whatever you got wrong. A ruling that dies with the workspace was a decision
made in secret.
<!-- vendored:end id=sp-rulings-list -->

## Bypass record

A gate that applies and is skipped (a review exemption of `refs/lanes.md`, or the user's words) makes main append one entry to the nearest `{plan_dir}/errors.yaml` (else `docs/errors/{session_id}.yaml`): `source: gate-bypass`, `pattern` (`review-layers` | `final-user-review` | `orchestrator-first` | `approval-gate` | `test-pass` | `fast-lane`), `when` (ISO date), `by` (the user's words verbatim, or the exemption id), `task_ids[]`, `wave` (or null). A gate that does not apply writes nothing; main thread appends `fast-lane` itself for an L1 edit, `by` naming the conditions met. Main thread doing a worker's work outside L1 and L2-direct (`refs/lanes.md`) appends `source: main-thread-violation`, `pattern: orchestrator-bypass` there too.
