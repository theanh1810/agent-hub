# Spec debt — the unticked lines, and the two signals that say a step was skipped

<Owner: agents/auditor.md § References>
<Read when: the workspace has a `docs/specs/_debt.md` file, or the window holds a `hotfix`-scoped commit or a closed plan with `spec_required: true` (`agents/auditor.md` § SDD metrics and § Gates).>

---

**HARD when `specs/_debt.md` exists.** Each unticked line:

- Overdue by more than 3 days → 🔴, its own table in the report, plus a `brainstorm_handoff[]` with `mode: spec-debt`.
- A line whose "rule confirmed by a person yet" field reads **no**, older than 7 days → 🔴 serious: the system runs on a rule nobody approved.

Two more signals:

- `spec_debt_missing`: a `hotfix`-scoped commit in the window with no matching `specs/_debt.md` line the same day (implement skipped the debt step).
- `spec_sync_skipped`: a closed plan with `spec_required: true` whose `closeout` task shows an empty or missing `spec_synced` (`CLAUDE.md` §21 step 4): the baseline drifted from the code.

A plan whose last wave has no `closeout` at all is the stronger finding: count it under `closeout_skipped`, not here.
