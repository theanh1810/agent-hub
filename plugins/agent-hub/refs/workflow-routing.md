# Workflow routing

Tier 3 of `CLAUDE.md` §3, §4, §5 and §14 — the rules live here; `CLAUDE.md` keeps one pointer line per section.
Read when: classifying a request, choosing a pipeline, or sizing a plan — `orchestrator` and `planner`.

---

# 3. Task Classification

`simple` · `problem-solving` (investigation only) · `bug` · `hotfix` · `feature` · `medium` (multi-file behaviour, no new surface) · `complex` (cross-repo / API / socket / DB / architecture) · `refactor` (behaviour must not change — characterization tests first) · `infra` · `docs`.

Every class has a row in `refs/roles/orchestrator/workflows.md` § Workflows and is a legal value of the `workflow` field orchestrator emits; the three lists are checked against each other (`tools/check ruleset (package repo only)` → `routing_rows_are_legal_workflows`). Validation level follows the class (`CLAUDE.md` §9).

# 4. Workflow Routing

**The per-class pipeline table is `refs/roles/orchestrator/workflows.md` § Workflows, the single source.** Link to it where a pipeline is needed; never copy it.

Three routing rules govern everything:

- **Every prompt is handled by an agent** (§0.1).
- **Anything touching a server goes to `devops`** (SSH, deploy, rollback, `pm2`, `nginx`, `docker`/`kubectl` on a host, server logs, DNS, certificates, a migration against a deployed database), whatever the class. At each plan's end, branch integration, the pull request and worktree cleanup are devops's too.
- **After the run's last `implement` spawn, one code review (`reviewer` independent, blind to the plan) and `test` run once each, in parallel; UI, user flow and spec/task compliance are `test`'s.** The fast lane runs neither. Three exemptions: `skip_review: true` · docs-only with no code surface · a hotfix where the user said "ship without review". In `~/.claude`, docs-only covers only files under `docs/`, and a ≤3-line edit changing no rule's meaning is a `skip_review: true` case (`refs/roles/orchestrator/edge-cases.md`). Auditor measures the ratio: below 0.5 red flag, 0 with implement tasks a workflow break.

**Gates (HARD).** Each owned by the agent that fires it; procedure in `agents/orchestrator.md`.

| Gate | Fires when | Owner |
|---|---|---|
| Clarify | ambiguity, a missing constraint, a trade-off needing preference, unclear scope, an unconfirmed shared-symbol change | brainstorm |
| Design | a new FE screen / flow / component, a layout or visible-behaviour change, a design-system migration, cross-platform parity. Skipped for backend, infra, docs, CLI, a logic bug with no visual change, a copy-only edit ≤2 strings | brainstorm decides; `designer` runs (which side of an FE task designer owns and which implement owns: the boundary table in `FLOW.md` §4) |
| Approval | complex / refactor / architecture · a feature of more than 6 files or cross-module · a bug touching a shared symbol, contract, route, schema or socket | brainstorm |
| Plan review | planner returned. **Unconditional.** The spec is approved here, not at a stop of its own | main thread |
| Final | after the run's review-and-test pass is green, or accepted as partial at the cap; in every mode | main thread |

**An approved plan runs straight through**: these five gates and a blocking status are the only stops; no "shall I continue?" between tasks. The permission mode changes no gate: plan gate once before wave 1, final gate once after the review-and-test pass (`refs/roles/orchestrator/gates.md`). Override the plan gate only on an explicit "skip the plan approval", or the same words in the reply language.

**Thinking mode.** Orchestrator MUST pass it to `brainstorm`, `planner` and `test`. Auto-derive: `simple | hotfix | bug | docs → quick` · `feature | medium | infra → standard` · `complex | refactor | problem-solving → extended` (deliberate for `problem-solving`). A user cue ("analyse carefully", "test thoroughly", "deep analysis"), or the same words in the reply language, forces `extended`. For `test` the mode sets how deep each case is followed, never which cases run; path patterns in `agents/test.md` force `extended` for money, auth, permission and legal code.

| Agent | HIGH when | LOW when |
|---|---|---|
| orchestrator | never — routing is pattern matching | always |
| brainstorm | complex / refactor / architecture · ambiguous root cause · cross-system contract · candidates needing real weighing · `approval_required` | a typo · a 1-file edit · a lookup · an obvious bug with a repro · `error-batch` |
| designer | a flow ≥4 screens · design-system migration · web+mobile parity · patterns to weigh | reusing a pattern · a one-screen tweak · copy-only |
| planner | multi-wave with cross-wave deps · >3 parallel branches · contracts across agents · a hard rollback | `quick` mode · 1 wave · ≤2 tasks |
| implement | a novel algorithm · a contract change; a causal chain is brainstorm's | a mechanical change · an obvious patch · a post-error-batch fix list · an analysed step |
| reviewer | `security` on auth / payment / PII · `merge` >500 lines or a contract change · architecture critique | a docs proposal · a style-nit pass |
| test | ≥4 screens · money, auth, permissions, legal · web+mobile parity · a release candidate | smoke · verifying a hotfix · re-running `failed_test_case_ids` |
| devops | a production deploy · a DB migration · certificate rotation · incident root-cause | a container restart · a config dry-run |
| auditor | never — a scorecard counts what the artifacts already say | always |

High thinking costs ~3-5x latency and ~2-3x tokens. **Lower it** when the analysis or plan is complete, from error-loop pass 2 (three failures mean an architectural problem), or on "quick, please". **Raise it** when confidence is below 0.7 after pass 1, the approval gate carries real trade-offs, or on security, contract and architecture work. **Forbidden**: high thinking on a status check, read, grep, rename or lookup · defaulting to extended for everything · skipping depth the user asked for.

**Bug rules.** Start from the error, log or repro, not broad reading. `test` is mandatory when a bug touches UI, visual, mobile, API, socket or a route. Root cause is `brainstorm`'s, with `scout` through `recommend_scan[]` when the trace is wide (`refs/roles/brainstorm/modes.md` § Root cause); `implement` applies the analysed fix and diagnoses nothing.

**Stop the line.** An unexpected red test or broken build stops new feature work: keep the evidence, diagnose, fix the root cause, guard against a repeat, continue only after re-verifying. **The feedback loop**: do → check → fix → re-check; move on only when the check passes. Neither the loop nor a stop-the-line counts toward the error-loop cap; re-running a deferred or blocked item of the previous run is a new turn, not a loop.

## Fast lane

**Fast lane**. Main thread sends a request straight to `implement` only when all four hold: (1) it edits at most **5 files**; files a script regenerates from an edited file (`tools/effort-variants.py` variants) do not count; (2) the user's message already says what to change; (3) it holds nothing §0.2 says must be asked (business rule, end-user copy, deleting data, migration, production deploy, secret); (4) it changes no shared route, schema or contract. One in doubt → the normal route. Implement runs a light check (syntax or typecheck of the changed files) and appends one bypass record `pattern: fast-lane` (`refs/roles/orchestrator/gates.md` § Bypass record), then writes the adhoc record with `run` and `data_impact` and runs `agent-hub change-map --adhoc` on it (`refs/closeout.md` § Data impact). Main thread still edits nothing itself.

# 5. Planning Rules

**The plan owns execution; approved specs own behavior (HARD).** `implement` builds from `what`/`files[]`/`solution`, `test` runs `test_cases[]`, `reviewer` judges by `acceptance_criteria`, `devops` deploys the `devops` wave with its `rollback_strategy`, all from one plan; an AC resolves to the approved spec or the current delta, and a conflict returns to brainstorm rather than overriding the spec.

- `objective` is **one observable sentence**: what is different for the user. An unobservable goal cannot become an acceptance criterion.
- **Do exactly the task**: less and the plan lies about what shipped; more and the diff carries changes no reviewer expected.
- **An approved plan is not re-planned.** A change of mind before the plan gate goes through `Edit plan`; after it, the change waits for the final gate and a plan gap found mid-run is an error round (`refs/roles/brainstorm/error-batch.md`). A chat message is never authorisation to deviate, "while you're in there" included.
- A task in several steps states its short plan as "step → how to check it".

Required for `feature`, `complex`, cross-system work, a high-risk bug, a multi-file change. **One exemption, the routing table's**: a small `feature` of up to 6 files has no `planner` in `refs/roles/orchestrator/workflows.md` § Workflows and ships plan-less by design. Optional for simple, a one-file bug, docs, hotfix.

The plan files, laid out by `refs/plan-files.md` (a lite plan keeps the single-file shape):

```
{plan_dir}/plan.yaml                    # index — language: agents/planner.md § Language
{plan_dir}/tasks/{wave}/{task_id}.yaml  # one file per task, source of truth for that task
{plan_dir}/plan.<lang>.md                   # human mirror — same waves, ids, statuses
```

Every task carries `test_cases[]` with `covers_acceptance`. Schema, templates and pre-write validation: `agents/planner.md`.

# 14. Plan Granularity (HARD)

One task, one concern, no cap on its diff lines. Never schema, logic and UI as three unrelated chunks — but a **vertical slice** that cuts through the layers for one behaviour may mix them, and slicing vertically is the default way to split a wave. Files target ≤3, ceiling 5. Every task carries `review_checkpoint{focus[], estimate_min ≤5, risk_areas[]}`. The plan-review gate is unconditional, and so is the final review gate, in every mode.

A big feature ships as small slices behind a feature flag, each merged on its own; outside rollout figures (5-25-50-100%, watch 24-48 hours, remove the flag after 2 weeks) are suggestions, not rules.

Task size, wave structure and the forbidden list: `agents/planner.md`. Gate procedure: `agents/orchestrator.md`; planner supplies its data, does not restate it.
