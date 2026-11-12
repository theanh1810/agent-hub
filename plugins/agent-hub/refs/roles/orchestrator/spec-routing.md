# Spec layer routing (SDD) — what orchestrator does with a spec status
<Owner: agents/orchestrator.md § Spec layer routing>
<Read when: `spec_required` must be set or raised, or a worker returned a spec status: `blocked_needs_spec`, `spec_required_misclassified`, `spec_drift`, `bug_spec_class`>

---

Rules: `rules/SDD.md`. Orchestrator neither reads nor writes spec; it only routes.

- **Initial value from the class:** `true` for `feature | medium | complex | refactor` and a `bug` touching a shared symbol, contract, route, schema or socket; `false` for `simple | problem-solving | hotfix | infra | docs | error-batch`. Pass it to every worker in the wave with its source.
- **Three nets raise it** (the initial value is a guess): brainstorm after its dependency trace, implement on the real diff, reviewer on the final diff. `spec_required_escalated_from` (brainstorm) or `spec_required_escalation: true` (implement) sets `true` for every remaining wave. Raise only, never lower.
- **implement `blocked_needs_spec`** (bare or with `spec_required_escalation: true`) → empty `next_spawns[]`, note `spec_gate_pending`, `summary_owner: main_thread`. Main asks with `spec_question` and options → `[brainstorm]` `mode=clarify-followup` writes the AC → only then re-emit `[implement]`. The only branch for that status.
- **Reviewer `spec_required_misclassified`** → no route: empty `next_spawns[]`, note `spec_misclassified_pending`; the user chooses outside SDD scope (merge) or a real business rule (→ brainstorm).
- **Reviewer `spec_drift`** is not an implement defect by default: empty `next_spawns[]`, note `spec_drift_pending`; the user adds the AC (→ brainstorm) or has the code changed to match (→ implement). A business decision, never orchestrator's.
- **brainstorm `bug_spec_class: B`** with no user answer → a clarify gate, no downstream spawn.
- **No `docs/specs/` and the class needs one** → `[brainstorm]` `mode=reverse-engineer` first, never planner or implement in that wave.
- **`hotfix`** keeps its fast pipeline, no spec step; after devops `needs_followup: true`, note `spec_debt_pending`, so the next pass spawns `[brainstorm]` `mode=spec-debt`.
- **`refactor`:** wave 1 is `[main:test]` `characterization` before `[main:implement]`, unless brainstorm confirms those tests exist.
- A spec written by brainstorm has no stop of its own: it is approved at the plan gate with the plan.
