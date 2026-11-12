# critique (challenge)

Scopes: `plan` | `code` | `architecture`.

- **Plan**: first run `agent-hub check plan {plan_dir}` (or on the `docs/brainstorm/{slug}.yaml` it was designed from) with the `--ceiling-exception` its record names, never `--clone`. Each FAIL line is a finding whose rule is that check's gate: its row in `agents/planner.md` § Quality gates, the `refs/roles/planner/quality-gates.md` row that table points to, `refs/roles/planner/dag.md` for `dag`, or `agents/planner.md` § Pre-write validation row 8 for `mirror`; its last line goes into the `## Round {n} · critique` section of `{plan_dir}/review.md`. Then decomposition atomicity, real vs assumed deps, parallelism, missing edge cases.
  Beyond plan-verify, the plan critique checks: scope against the analysis, acceptance criteria observable, the test plan sized to the change, each risk with a rollback, and the decisions only the user can make (Q-D05-1-a).
- **Code**: silent failures, edge cases (empty/null/concurrent), over-engineering, naming.
- **Architecture**: simplest approach, coupling, future-proofing waste.

Every finding names the rule it breaks and offers an alternative; a preference that breaks no named rule is not filed at all (`agents/reviewer.md` Evidence paragraph and § Forbidden). A plan gets one critique before its approval gate (`refs/roles/orchestrator/workflows.md`); no in-flight critique of work in progress (user, 2026-10-26).
