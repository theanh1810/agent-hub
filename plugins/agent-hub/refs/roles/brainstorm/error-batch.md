# Error batch — brainstorm mode=error-batch
<Owner: agents/brainstorm.md § References>
<Read when: brainstorm is spawned with mode=error-batch, after a review-and-test pass returned red, a checkpoint went red, a plan gap was found, or the user asked for a fix at the final gate>

---

Errors are handled as one batch: every error of a pass is recorded first, then analysed, then fixed, then reviewed and tested again as a whole. Brainstorm records the round and analyses it in one pass. Planner never records, and an approved plan is never amended: `errors.yaml` is the fix contract.

## Inputs

```jsonc
// mode=error-batch
{
  "mode": "error-batch", "plan_id": "string|null", "session_id": "string",   // errors.yaml sits in {plan_dir}/, or docs/errors/{session_id}.yaml with no plan
  "round": "number", "round_source": "review-test|checkpoint|plan-gap|user-final-gate|user-extra-round",
  "review_sections": ["review.md ## Round {n} · {kind}"], "test_report_paths": ["path"], "explore_paths": ["path"],
  "user_notes": "string|null",   // the final gate's `Request changes` text, verbatim
  "escalation_source": "auditor|null", "error_ids": ["E1-1"]   // only with escalation_source
}
```

## Procedure

1. **Read** only the files the inputs name and the `errors.yaml` being written; never a source file beyond the `files[]` a fix entry must name, the plan body or the diff.
2. **Record one round** under the plan-write lock (`refs/closeout.md` § Who writes it, and when) in `{plan_dir}/errors.yaml`, or `docs/errors/{session_id}.yaml`. Every red finding and case goes in verbatim, never translated or compressed (`CLAUDE.md` §11, Foreign; `skills/context-compression/SKILL.md` § Hard rules):

   ```yaml
   errors:
     - round: 2
       round_source: review-test
       verdict: red                # red | yellow | green: red while a critical or major entry is open, yellow when only minor entries remain, green with none
       entries:
         - id: E2-1                  # E<round>-<n>
           source: reviewer-task     # reviewer-task | reviewer-independent | test | test-explore | user-final-gate | implement | devops | checkpoint
           evidence: {plan_dir}/review.md ## Round 2 · conformance
           severity: major           # critical | major | minor, mapped below; an untagged finding is major
           task_id: W2-T3            # only when the source names one
           text: |
             <the finding or the failing case, verbatim>
       analysis: {groups: [], fix_list: [], deferred_errors: []}
       user_decisions: []
   ```

   `user_notes` becomes one entry, `source: user-final-gate`, verbatim.

   `severity` maps from the source: a reviewer `blocking`, `warning` or `suggestion`, and 🔴, 🟠 or 🟡, become `critical`, `major` or `minor`; a failed planned case is `major`, `critical` when its failure doc names a crash, data loss, security hole or access block; a `test-explore` case takes the severity test gave it; a fidelity finding, a `checkpoint` red line and a `user-final-gate` entry are `major`; an untagged finding is `major`.

   The first write of a new `errors.yaml` also sets `meta.close_criteria: 1`, the marker `agent-hub check plan` `close` reads. A pass that follows a fix round is always recorded, a clean one as a round with `entries: []` and `verdict: green`. Each fix round's report states, per finding, the command run and its output; the re-review reads only the fix diff and marks each finding ADDRESSED or NOT ADDRESSED (obra fix-loop.md:33-48).
3. **Scan.** `agent-hub secret-scan <errors file>`. A hit is masked fully (no character of its value kept) and the file rescanned until exit 0.
4. **Group** by root signature, one root cause per group (`refs/roles/brainstorm/modes.md` § Root cause), and carry over these rules:
   - A `minor` entry goes to `deferred_errors[]` as `{id, severity, source, location, reason, round}` (`id` is the entry's own id) and never into `fix_list[]`; only `critical` and `major` entries are grouped and fixed.
   - A `source: reviewer-independent` finding was filed blind to the plan: weigh it against the plan, spec and `user_decisions_verbatim[]` first. One contradicting an approved decision or an AC is not fixed: it goes to `deferred_errors[]` naming the decision, and main shows it at the final gate.
   - A red `source: test-explore` case is fixed like any failure when its oracle holds; one whose oracle misreads the code is deferred the same way.
   - A `user-final-gate` entry is the user's own instruction: fix it, or `needs_user_input` when ambiguous; never deferred.
   - `escalation_source: "auditor"` handles only the given `error_ids[]`, returns `auditor_escalation_acknowledged` + `escalation_ts`; what will not root-cause this pass goes to `deferred_errors[]`, never a loop.
   - **Verify each reviewer finding before it reaches `fix_list[]`.** Open the cited `file:line` and check its callers, guards and tests. Confirmed: it goes to `fix_list[]`. Ruled out: it goes to `dropped_findings[]` as `{id, reason, evidence}` (`evidence` is a `file:line`). Unclear: ask the user one question (step 6); never guess.
5. **Write the analysis** into the same round: `analysis: {groups[], fix_list[], deferred_errors[], dropped_findings[]}`, each group `{id, signature, error_ids[], root_cause, location, confidence}`, each `deferred_errors[]` entry `{id, severity, source, location, reason, round}` and each fix entry `{id: FX-<round>-<n>, resolves[], task_id|null, files[{path, why}], change, check, added_cases[], user_answer, risk}`. `task_id` is the task whose `files[]` holds the target, null when none does; `files[]` is every path the fix may touch. Entries of other writers (`main-thread-violation`, `orchestrator-violation`, `gate-bypass`, `planner-violation`) and `meta.pending_user_changes[]` stay untouched.
6. **Ask.** An entry whose `files[]` fall outside every task's `files[]`, that adds a test case, or that changes an AC, an expected result, user-visible copy or a business rule needs a user answer (`CLAUDE.md` §0.2): return `needs_user_input` with those questions, one decision each, and write the answers verbatim under the round's `user_decisions[]` before returning. The answer becomes the entry's `user_answer`; the plan files and the approval stamp stay untouched.
7. **Counter.** `meta.error_loop_count` heads the file (0 when absent), written only here. A round whose `verdict` is `yellow` or `green` changes no counter and returns `cap_reached: false` with an empty `fix_list[]`. A `review-test` round with a critical or major entry increments it while below 2 and returns `cap_reached: false`; `checkpoint`, `plan-gap` and `user-final-gate` rounds never change it. At 2 or above a `review-test` round does not increment it: `meta.cap_summary: {attempts[], converging, suspected_root}` is written (one `attempts` line per round, `converging` from the error counts, `suspected_root` the last root cause, verbatim) and `cap_reached` is true. A `user-extra-round` the user consented to at the cap sets the counter to 3 and is never followed by a fourth round; widen scope at the cap is that same round, recorded with `scope_widened: true` and its wider `files[]` asked under step 6. At 3 a red round returns `cap_reached: true` and the cap offers only roll back and accept partial. The counter resets only on the user's explicit reset.
8. **Return** `errors_path`, `round`, `error_count`, `counter`, `cap_reached`, `close_check` (the `close` line of `agent-hub check plan {plan_dir}`), the `fix_list` ids and the handoff (`agents/brainstorm.md` § Output).

## Output

```jsonc
// mode=error-batch
{
  "status": "completed|needs_user_input|needs_revision|failed", "errors_path": "{plan_dir}/errors.yaml", "round": 1, "error_count": 0,
  "counter": 0, "cap_reached": false,   // counter = meta.error_loop_count after this round
  "fix_list_ids": ["FX-1-1"], "deferred_errors": [], "close_check": "the close line of plan-verify",
  "handoff": { "understanding": "≤2 sentences", "files_touched_or_referenced": ["file:line"],
    "changes_or_findings": "≤3 sentences", "validation_done": "secret-scan exit 0", "risks": ["≤3"], "next_step": "1 sentence" }
}
```
