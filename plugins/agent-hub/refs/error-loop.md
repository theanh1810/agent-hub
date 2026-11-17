# Error-loop control — the cycle, the counter, the cap
<Owner: rules/core.md § Routing; main thread runs the loop>
<Read when: test, reviewer or build failed, or the loop counter is at the cap>

---

## The cycle

Main thread sends every failure to brainstorm first (step 1) and never routes one straight back to `implement`.

1. `[main:brainstorm mode=error-batch]` records every red result of one review-and-test pass verbatim as one round in `{plan_dir}/errors.yaml` and analyses it in the same pass (`refs/roles/brainstorm/error-batch.md`). `reviewer` and `test` write no `errors.yaml`; brainstorm is the only writer and counter holder.
2. One `[main:implement]` fix-round spawn works from the round's `fix_list[]`, `closeout` re-run at its end.
3. `[main:reviewer mode=independent]` `||` `[main:test]` over the fix, one message: the fix round's diff-only file and the previous independent review file for the reviewer (`refs/gates.md`, Final gate, steps 1-2), part (a) in full and part (b) per `refs/roles/test/retest-scope.md`.

Part (a) is always whole on the new build. Main thread passes `rerun_test_case_ids` (cases that owned the failing errors) so the report says which turned green; they never narrow part (a). Part (a) also includes every `added_cases[]` case of the fix entries of earlier rounds.

## The counter

- `meta.error_loop_count` heads `{plan_dir}/errors.yaml` (or `docs/errors/{session_id}.yaml` with no plan): a YAML scalar before the rounds, 0 when absent, written only by brainstorm `mode=error-batch`. Main thread reads `meta:` (`cap_summary` included) and never writes it.
- A different signature in a later round belongs to that round; a round counts as 1.
- Resets only on the user's explicit "reset error loop".

## What does not count

- A user's `Request changes` at the final gate: a round with `source: user-final-gate`, fixed through the same cycle, at most once per plan and diff-only (`refs/gates.md`, Final gate, step 5).
- A yellow round (only 🟡 left): it opens no fix round.
- A checkpoint fix round (build, check, fix, check, stop on an unexpectedly broken test): bounded by implement's three-fail rule.
- Items a previous run deferred or blocked (`deferred_errors[]`, `accepted_partial` tests): priority input of a new run, a **new pass**, not a loop of the old plan.
- A turn-cap resume (`refs/turn-budget.md`).

## The cap

**HARD cap = 2 loops per `plan_id`.** Loop 2 still red → brainstorm `mode=error-batch` returns `cap_reached: true` on the third red round and main thread raises `needs_user_decision` (`refs/gates.md`) with all four, from `meta.cap_summary` and `errors.yaml`:

- `attempts[]`: one line per loop: believed cause, what changed, what the error became. A cause changing each loop means the diagnosis was never right; the same cause twice means the fix sat in the wrong place.
- `converging: true|false`: error count falling, signature narrowing? A non-converging loop will not on a third pass.
- `suspected_root`: `file:line` the evidence points to, with confidence even when low.
- `architecture_signals[]`: which of these hold, each with its evidence: each fix reveals a new problem in a different place · a fix needs a large refactor · the pattern is fundamentally unsound (obra systematic-debugging SKILL.md:198-212). When at least one holds, the text of the `needs_user_decision` question also asks "is the design wrong?"; it is text, not a fifth option, and the four options and the cap of 2 are unchanged.
- `options[]`: four at counter 2: **roll back** to the pre-fix state · **accept partial** · **one extra fix round** following `errors.yaml`, only with the user's consent, at most once, never touching the original plan, counted as loop 3 · **widen scope** beyond `binding_scope` (the commonest cause of a stuck loop is a fix never allowed to touch the file owning the bug).

Main thread surfaces these with `AskUserQuestion`; it neither picks one nor re-spawns `agent-hub:implement`. Three failed attempts is an architectural problem. A fourth loop never opens: widen scope is the extra round with a wider `files[]`, so the two are one choice used at most once, and at counter 3 `options[]` hold only roll back and accept partial.

**Accepting partial is not done.** Recorded as `test incomplete: accepting remaining failures` with every red `test_case_id`, in the test report with `status: accepted_partial`, at closeout and under `Risk` in the final response; never reported as test done.

| Rationalization | Reality |
|---|---|
| "One more loop will fix it" | Three fails is architecture; stop at 2 and ask |
| "A different signature resets the count" | The round counts as 1; only the user's reset zeroes it |
| "Route the red test straight to implement" | Record, error-batch, then implement |

## Additions from other packs

The round cap of `## The cap` in this file wins over the number in the block below.

<!-- vendored:begin id=as-n8 src=addyosmani/agent-skills@39b723ceebf81474d0557c1fecd01eddab585563:skills/doubt-driven-development/SKILL.md#L183-L193 licence=MIT -->
### Step 5: STOP — Bounded loop, not recursion

Stop when:

- Next iteration returns only trivial or already-considered findings, **or**
- 3 cycles completed (escalate to user, don't grind a fourth alone), **or**
- User explicitly says "ship it"

If after 3 cycles the reviewer still surfaces substantive issues, the artifact may not be ready. Surface this to the user — three unresolved cycles is information about the artifact, not a reason to keep looping.

If 3 cycles is "obviously insufficient" because the artifact is large: the artifact is too big — return to Step 2 and decompose. Do not lift the bound.
<!-- vendored:end id=as-n8 -->
