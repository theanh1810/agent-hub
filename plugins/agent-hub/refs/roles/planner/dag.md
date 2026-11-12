# DAG — waves, thinking mode, risk and variants

<Owner: agents/planner.md § References>
<Read when: Workflow step 4, `shape: full`. A lite plan is one wave with no variants or pre-mortem and never reads this. Brainstorm `mode=change-design` reads § Wave rules to join two tasks on one file by `depends_on`.>

---

## Wave layering

**Default: vertical slices** (user, 2026-10-26). Each slice cuts a narrow but COMPLETE path through every layer (schema, API, UI, test) and demos or checks itself; never finish one layer everywhere first. A slice may hold several tasks in one wave and mix data, logic and UI.

- **Make the change easy, then make the easy change:** a preparatory refactor goes first.
- **Exception:** a broad mechanical refactor (rename a column, change a shared symbol's type) is one pass; no vertical slice can be green alone.
- **Contract-first, parallel**, when front and back run side by side: slice 0 fixes the contract; the backend implements it with tests; the UI works on fake data shaped by it; the last slice joins and tests both ends.
- **Layered fallback**, only when the domain forces it, justified in `waves[].wave_rationale`: 1 contracts, types, schema · 2 data · 3 business logic · 4 surface · 5 tests and docs.
- **Revertible slices:** prefer additions easy to back out; touch old code minimally; never delete and replace in one change.
- **Risk first:** high-risk tasks early; a checkpoint every 2-3 tasks (tests green, build clean, main flow runs, a person looks).
- **Context fit:** each task fits one fresh implement context window.
- **Flags:** a risky slice ships behind a feature flag, its removal a later task. Rollout figures from outside repos are suggestions only (user, 2026-10-26).

## Wave rules

- Wave N depends only on waves < N; no cycles; fanout ≤2 prior waves.
- Two tasks touching one file go in **different waves**, joined by `depends_on`: a wave's tasks run in no fixed order, so each would anchor on text the other may change.
- A task every later wave needs is `is_prerequisite: true`; nothing downstream runs until its criteria pass.
- No single-task wave where safe parallelism exists.
- `test` runs after the implement wave it validates; `reviewer` gates security and contract handoffs; `devops` follows implement and test unless infra-first, appears when brainstorm reports need, with rollback, never folded into an implement task.
- `depends_on: [ALL]` means every other task; keep the sentinel, never expand it (an explicit list goes stale and closeout runs early).

## Thinking mode

| complexity | mode | behaviour |
|---|---|---|
| simple · bug · hotfix | `quick` | lite plan where its conditions hold, 1 wave, no variants, no pre-mortem, ≤1 pass |
| feature · medium · infra_docs | `standard` | DAG + 1 variant, top-3 risks, ≤1 revisit loop |
| complex | `extended` | `<thinking>` first (goal, constraints, DAG sketch, failure modes, variant trade-offs), 2-3 variants, full pre-mortem, `alternatives_rejected` on every task, ≤2 loops |

A user override beats the table.

## Risk and variants, by mode

Copied from brainstorm, never added by planner.

| Mode | Risk | Variants |
|---|---|---|
| `quick` | skipped | none |
| `standard` | the top three | one |
| `extended` | full pre-mortem: failure modes, mitigations, rollback, blast radius, assumptions, confidence | two or three (safest, balanced, larger), each with why not chosen |

A high-risk item carries mitigation and rollback; no rollback is a worry, not a plan entry. GitNexus, mem0 or Context7 unavailable → record it in `pre_mortem`. Verification strategy: commands per wave, a final command, a checkpoint running the test script after a wave with its expected red owned by a later wave's task. The plan's rollback names trigger and steps.

## Cross-task journey

Pass 2 of `refs/roles/test/two-pass.md` walks business flows no single task's cases walk (the integration pass of `CLAUDE.md` §9). Every plan with a non-exempt implement task (`refs/roles/planner/test-cases.md` § Exemptions) carries one test task:

| Field | Holds |
|---|---|
| `id` | `W{n}-T1`, the only task of its wave `W{n}` |
| `agent` | `test` |
| Wave position | after the reviewer wave over the last implement wave, before closeout (reviewer before test, closeout last) |
| `depends_on` | every implement task but closeout |
| `test_cases[]` | on a `test_schema: layers` plan: where a task reaches a user through a screen, one `e2e` case per business flow; an API-only change gets one `integration` case per route and one `contract` case per consumer; otherwise one `local_validation` case running the repo's test command. Each `scenario` names its source: a UC id plus one of its steps (`Main flow`, `Alternate flows` or `Decided exceptions`), or a flow brainstorm wrote in change-design; run as `refs/roles/test/journey.md` runs any case. Legacy plan: one `e2e` case per flow (`api` where reached through an API alone), otherwise one `script` case running the repo's test command |
| Kinds | `refs/roles/planner/test-cases.md` § Kinds applies as to any task: a case or a waiver per kind |
