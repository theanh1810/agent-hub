# Workflows — the per-class pipeline table
<Owner: agents/orchestrator.md § Workflow>
<Read when: Workflow step 2, picking the pipeline for the class step 1 chose>

---

Notation: `[main:<agent>]` = main thread spawns it. `→` sequential, `||` parallel (written `\|\|` inside a cell). After a wave main thread re-invokes orchestrator only on a trigger (`refs/roles/orchestrator/routing-contract.md`).

**This table is the routing source of truth.** `tools/check ruleset (package repo only)` reads the `| Class | Pipeline |` table under this file's `# Workflows` heading; renaming either empties the check.

| Class | Pipeline |
|---|---|
| `simple` | `[main:implement]` → `[main:reviewer mode=independent]` \|\| `[main:test]` |
| `problem-solving` | `[main:brainstorm]` → `recommend_scan[]` → `[main:scout mode=scan x N]` parallel → `[main:brainstorm]` re-synthesize with `scout_results_refs[]`. Pure investigation, no file edit |
| `bug` (small) | `[main:brainstorm]` → `[main:implement]` → `[main:reviewer mode=independent]` \|\| `[main:test]` → **final gate** → after `Approve`: on the user's word `[main:devops]` pushes the branch and opens the MR; the user merges |
| `bug` (system-structure impact) | `[main:brainstorm]` → **design gate** (if visual change) → `[main:designer]` → **approval gate** → `[main:brainstorm mode=change-design]` → `[main:planner]` → `[main:reviewer mode=critique]` (plan critique) → `[main:implement]` (one spawn per wave) → `[main:reviewer mode=independent]` \|\| `[main:test]` → **final gate** |
| `hotfix` | `[main:brainstorm]` (minimal, no gate) → `[main:implement]` (minimal patch) → `[main:reviewer mode=independent]` \|\| `[main:test]` (smoke) → `[main:devops]` (if deploy) |
| `feature` (small ≤6 files) | `[main:brainstorm]` → **design gate** (if FE) → `[main:designer]` → `[main:brainstorm]` (design-followup) → `[main:implement]` → `[main:reviewer mode=independent]` \|\| `[main:test]` → **final gate** → after `Approve`: on the user's word `[main:devops]` pushes the branch and opens the MR. No planner, no approval gate |
| `feature` (>6 files / cross-module) | `[main:brainstorm]` → design gate (if FE) → `[main:designer]` → `[main:brainstorm]` (design-followup) → **approval gate** → `[main:brainstorm mode=change-design]` → `[main:planner]` → `[main:reviewer mode=critique]` (plan critique) → `[main:implement]` (one spawn per wave) → `[main:reviewer mode=independent]` \|\| `[main:test]` → **final gate** |
| `medium` (multi-file behaviour, no new surface) | `[main:brainstorm]` → **design gate** (if user-visible) → `[main:designer]` → `[main:implement]` → `[main:reviewer mode=independent]` \|\| `[main:test]` → **final gate** → after `Approve`: on the user's word `[main:devops]` pushes the branch and opens the MR. No approval gate and no planner unless brainstorm raises `approval_required` |
| `infra` | `[main:brainstorm]` (if non-trivial) → `[main:devops]` → `[main:reviewer mode=security]` (opt) → `[main:test]` (smoke, **only when the run changed application code**; a deploy of existing commits is verified by devops's own health check and log read) |
| `complex` / `refactor` | `[main:brainstorm]` → design gate (if FE) → `[main:designer]` → **approval gate** → `[main:brainstorm mode=change-design]` → `[main:planner]` → `[main:reviewer mode=critique]` (plan critique) → `[main:implement]` (one spawn per wave) → `[main:reviewer mode=independent]` \|\| `[main:test]` → **final gate** → `[main:devops]` (opt) |
| `docs` (a documentation diff) | `[main:implement]` → `[main:reviewer mode=independent]` \|\| `[main:test]`. Planner and reviewer may not write a `.md` outside their own outputs, so `implement` is the only executor; a review exemption is decided on the real diff (`refs/roles/orchestrator/edge-cases.md`) |
| `plan-only` (no diff) | `[main:brainstorm]` (runs `change-design` inline) → `[main:planner]` → `[main:reviewer mode=critique]` (plan critique), or `[main:reviewer]` |

## Key rules

- **A blocking status preempts the table order.** `awaiting_user_choice` or `needs_user_input` stops every spawn until answered, so approval can resolve before the designer wave; `needs_design` only adds a wave. On a `feature` (>6 files) approval follows design-followup: until the brief exists the candidate is not fully described.
- **Every `bug` and `hotfix` starts at `brainstorm`** (root cause, `refs/roles/brainstorm/modes.md`), with a scout wave when the trace is wide; `implement` applies the analysed fix only. "Under time pressure (emergencies make guessing tempting)" a hotfix still has a cause before a patch.
- **Implement still red after three attempts** returns `needs_revision` / `root_cause_unconfirmed`, back to `brainstorm`. "DON'T attempt Fix #4 without architectural discussion."
- **Hotfix and refactor spec/test rules** (no spec step and `spec_debt_pending`; characterization wave 1): `refs/roles/orchestrator/spec-routing.md`.
- **Server work goes to `devops`** whatever the class; `implement` needing a deploy returns `needs_devops`, never runs it.
- **UI-touching work always includes `test`** (`testing-e2e` skill).
- **Sensitive diffs get a security review too.** When the changed paths or the diff text match the patterns of `skills/review-checklist/references/security.md` § Automatic trigger, main thread spawns `[main:reviewer mode=security]` in parallel with `mode=independent` and `test`, over the same frozen state; a miss adds nothing. Fail-open: a pattern error counts as a match.
- **After a run's last `implement`**, one code review and `test` run in parallel over one frozen state; UI, flow and spec compliance are `test`'s. Red results go to one brainstorm error-batch (`refs/roles/orchestrator/gates.md`).
- `simple` and `docs` rows, and a Simple devops op, are spawned by main thread directly (CLAUDE.md routing table); the rows do not change.
- A process skill (how to work) runs before an implementation skill.

## Stage to skill

| Stage | Skill or route |
|---|---|
| unclear what is wanted | clarify with the user (brainstorm intake) |
| new feature | the `feature` rows of the table above |
| a spec exists, needs tasks | planner (`planning-dag` skill) |
| implementing | `implementation-tdd` skill |
| something broke | brainstorm root cause, then implement |
| UI fix | `testing-e2e` skill |
| review, commit, CI, release | reviewer, the commit example template, devops |
