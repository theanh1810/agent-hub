# Agent flow: overview

Describes **the running system**; each rule names the file that defines it. Updated: 2026-10-26

---

## 1. The system on one page

```
                    ┌─────────────┐
   user prompt ────▶│ main thread │  ─── routes, never does the work
                    └──────┬──────┘
                           │ Agent(orchestrator)
                    ┌──────▼──────┐
                    │orchestrator │  pure router · 0 tool calls
                    └──────┬──────┘
                           │ returns next_spawns[] or wave_plan[] (JSON)
                           │ main thread reads the JSON, then spawns
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   ┌─────────┐      ┌──────────┐       ┌──────────┐
   │ brainstorm │─────▶│ designer │──────▶│ planner  │
   └────┬────┘      └──────────┘       └────┬─────┘
        │ 3 gates                            │ the plan files
        │ clarify·design·approval            │
        ▼                                    ▼
   [ask user]                          [plan gate: ask user]
                                             │
                    ┌────────────────────────┘
                    ▼
              ┌───────────┐    ┌──────────┐    ┌──────┐    ┌────────┐
              │ implement │───▶│ reviewer │───▶│ test │───▶│ devops │
              └───────────┘    └──────────┘    └──────┘    └───┬────┘
                    ▲                │              │          │
                    └────────────────┴──────────────┘          │
                       error loop, at most 2 rounds            │
                       (via brainstorm mode=error-batch)          ▼
                                                        ┌──────────────┐
                                                        │  CLOSEOUT    │ implement
                                                        │  5 steps, §21  │ always the last wave
                                                        └──────────────┘

   auditor: run by hand with /audit, read-only, not part of the flow
```

**Five overarching rules** (`CLAUDE.md` §0.1, §4, §20, §21):

1. **Every prompt is handled by an agent**; the main thread routes and does no work itself. Exception: a prompt that says `skip orchestrator` / `just do X` / `do it directly`, or the same words in the reply language.
2. **Anything touching a server is `devops`'s**, whatever the class.
3. **After the run's last `implement` spawn, `reviewer` and `test` run once, in parallel.**
4. **A run with a diff ends with closeout**: reindex, match the diff, match the result, sync the spec, mem0 and cleanup.
5. **When a task finishes, the agent that ran it writes its `result` at once**, not deferred to closeout (`CLAUDE.md` §20).

**User decisions of 2026-10-26**:

- **Fast lane through `implement`**: at most **5 files**, the four conditions of `CLAUDE.md` §0.1.
- **A small feature (up to 6 files)** skips the plan: no planner, no plan gate (`refs/roles/orchestrator/workflows.md` § Workflows).
- **At the end of each plan `devops` itself** pushes the branch, opens the PR/MR, integrates and cleans up the worktree it created (`skills/devops-deploy/references/integration.md`); `implement` only commits locally, once per wave.
- **Context limit 400k tokens**, one standard in place of 75% and 150k (`refs/context-policy.md`).
- **Detailed review reports go in `{plan_dir}/review.md`**, one section per round; with no plan, `docs/changes/adhoc/{YYYY-MM-DD}-{slug}/`; `INDEX.md` and image baselines go under `docs/reviews/`.

---

## 2. The agents: who does what

| Agent | Model | Owns | Files it may write |
|---|---|---|---|
| `orchestrator` | sonnet | Classify and emit routing JSON, nothing else | only violation lines in `errors.yaml` |
| `brainstorm` | opus | The **only** pre-plan worker: intake, clarify, GitNexus scoping, candidates, approval gate. Hands every search or read to scout through `recommend_scan[]` and opens only the lines scout points to. Sole owner of `specs/` | `{plan_dir}/proposal.md` + `design.md` + `design.yaml`, or `docs/brainstorm/{slug}.yaml` before an id exists (at `{workspace_root}`) · `specs/**` (in the sub-repo) |
| `scout` | sonnet | Read-only search of one sub-question (`mode=scan`), returns JSON; spawned only when brainstorm returns `recommend_scan[]`; proposes and edits nothing | only `.cm-tmp/{task_id}/` |
| `designer` | sonnet | FE/UI design brief: catalog pattern, primitives from `UI_RULES.md` | `{plan_dir}/design/{slug}/DESIGN.md` |
| `planner` | sonnet | Details `change_design` into the plan: before/after, steps, waves, test cases; changes neither scope nor criteria | `plan.yaml` (tasks inline) + `plan.<lang>.md` |
| `implement` | sonnet | The **only** agent that edits production code; follows the steps brainstorm analysed and never root-causes | code + `result` inline in `plan.yaml` (the mirror keeps the status and the `Result` block) + `docs/changes/adhoc/` |
| `reviewer` | opus | Task review, blind independent review of each wave, gating, merge | `{plan_dir}/review.md` + `INDEX.md` |
| `test` | sonnet | E2E browser/mobile, `script`, visual, a11y; the plan's cases plus 5-10 exploratory cases. **Strictly read-only** | only its own evidence + its section of `review.md` |
| `devops` | opus | Everything that leaves the local working directory | its decision records · `{plan_dir}/logs/` · `SERVER-INFO.md` |
| `auditor` | sonnet | Fleet scorecard, read-only | exactly one file, `docs/audits/{YYYY-MM-DD}.md` |

**Single-role shortcut** (`CLAUDE.md` §0.1): `user → main thread → owning agent`, not through orchestrator; every `implement` run is still followed by `reviewer`. Orchestrator takes only a new request that needs two or more roles, or a plan.

**Agent file frame** (identical in all 10): `Role (+ Language) → Sources → Evidence → Workflow → [own sections] → Input → Output → Ask, do not guess → Forbidden → Artifact layout`.

---

## 3. Pipeline by task type

**The routing table lives in `refs/roles/orchestrator/workflows.md` § Workflows, and only there**; this section does not copy it, not even shortened (a copy drifted from its source for 24 tasks, and no check could catch it because the two sides share no string; `agents/orchestrator.md § Reviewer after implement`).

---

## 4. The five gates

Each gate is fired by one agent and asked by the main thread; **inferring past one is forbidden** (`CLAUDE.md` §0.2). Recon is no longer a gate: brainstorm Phase 3 hands it to scout through `recommend_scan[]`; if one round still cannot build the shortlist it returns `needs_user_input`.

The five gates (who fires, when): `refs/workflow-routing.md` § Workflow Routing, the **Gates** paragraph; the status each gate returns: `CLAUDE.md` §2.1 table A.

**Design / logic boundary**: the Design gate decides *whether* to spawn `agent-hub:designer`; which side a part of an FE task falls on is decided by **who sets what the user sees** (`designer`) versus **who makes it run** (`implement`), not by file extension.

| Case | Goes to |
|---|---|
| New FE screen · layout change · design-system migration · web+mobile parity (`CLAUDE.md` §4) | **designer** (then implement writes the code) |
| Copy fix of at most 2 strings · internal component state logic (even inside `.tsx`) · a CSS bug with no design decision | **implement** |
| Design-system token change | **designer** decides, **implement** edits the file (designer does not edit production code) |
| An API shape that decides what the screen shows | **designer states** the constraint, **brainstorm fixes** the API shape (`mode=change-design`; `agents/designer.md` § Forbidden) |
| `test` verifies browser/visual | **test**: verifies, does not design (`CLAUDE.md` §9) |

**Permission mode changes no gate**: in every mode there are only two gates, the plan gate (asked once before wave 1) and the final gate (once after review and test of the whole run; `implement` is called once per wave, with no stop between waves). `settings.json` currently has `defaultMode: "auto"`.

**SDD gates** (`SDD.md` §10): a UC with no acceptance criteria means no code · a type-B bug not yet asked of the user means no code · `spec_drift` means no merge · a plan closed without running `spec-sync` is not Done.

---

## 5. Contract between agents: which field flows where

```
brainstorm ──────────────────────────────────────────────▶ planner
  recommended_candidate ────────────▶ recommended_approach
  root_cause_or_mechanism ──────────▶ root_cause / objective
  binding_scope.files_allowed[] ────▶ CEILING of the union of files[].path over every task record (refs/plan-files.md)
  binding_scope.files_forbidden[] ──▶ no task may name them
  change_design.plan ───────────────▶ plan.yaml with every task inline: files, logic, AC kept as given; planner writes steps, waves, test cases
  needs_devops ─────────────────────▶ the devops wave change_design already has (planner checks, adds none)
  spec_required, uc_ids[], ac_ids[] ▶ covers_uc, covers_acceptance
  bug_spec_class: B ────────────────▶ does NOT proceed, waits for the user
  design_brief_ref ─────────────────▶ every UI task
  open_questions[] ─────────────────▶ assumptions[] or user_questions[]

planner ──────────────────────────────────────────────▶ implement / test / reviewer / devops
  what · files[] · solution · acceptance_criteria ───▶ implement builds exactly that
  test_cases[] ─────────────────────────────────────▶ test runs exactly that list
  acceptance_criteria · review_checkpoint ──────────▶ reviewer grades against them
  wave devops · rollback_strategy ──────────────────▶ devops deploys exactly that

implement ────────────────────────────────────────────▶ reviewer
  pattern_reference: file:line ─────────────────────▶ reviewer re-reads it to verify
  spec_delta[] ─────────────────────────────────────▶ brainstorm writes it back into the UC at spec-sync
  spec_required_escalation ─────────────────────────▶ orchestrator raises it for every remaining wave
  plan_written_back ────────────────────────────────▶ false + completed = main thread rejects

test ─────────────────────────────────────────────────▶ brainstorm (when red)
  errors.yaml verbatim ─────────────────────────────▶ brainstorm mode=error-batch
  run_report_path ──────────────────────────────────▶ ONE file collecting every error, so one round runs
  ac_coverage[] ────────────────────────────────────▶ brainstorm fills the coverage table in the UC
  missing_test_cases[] ─────────────────────────────▶ planner writes the extra cases from the AC; a missing AC goes to brainstorm change-design first
```

**Shared handoff** (`CLAUDE.md` §11): `understanding` · `files` · `changes` · `validation` · `risks` · `next_step`; a missing field means reviewer blocks with `handoff_incomplete`.

---

## 6. Error loop

The fix round (brainstorm `mode=error-batch`, one `implement` spawn, then review and test again), the round cap and the choices at the cap: `agents/orchestrator.md` § Error-loop control and `CLAUDE.md` §2.1, the `needs_user_decision` row.

`errors.yaml` is **never compressed** by RTK or Caveman: it must stay byte-exact so brainstorm can root-cause from it.

---

## 6b. Closeout: how a run ends (`CLAUDE.md` §21)

The five steps, the mem0 limit, the `closeout` block in the handoff, who catches errors: `refs/closeout.md § Closeout`. Who writes a task's `result` and when, with the plan write lock: `refs/closeout.md § Who writes it, and when`. Where closeout sits for each run shape: `agents/orchestrator.md § Closeout is the last wave`. Step 4 and the `spec_delta` rule when the user has not confirmed: `agents/brainstorm.md § Closeout step 4`; `ac_coverage[]`: `agents/test.md § Read-only`; `deployed_sha` and deploy evidence: `agents/devops.md § Closeout`.

---

## 6c. Context window management: who, which stage, when to compress

The shared limit is **400k tokens**. The stage table, the budget per task class and the self-check after compressing: `refs/context-policy.md § Context window`. The never-compress list: `skills/context-compression/SKILL.md § Hard rules`.

---

## 7. Evidence standard: what each agent must prove

Each agent's evidence standard lives in that agent's own file (`agents/<agent>.md` and the `refs/roles/<agent>/` files it points to), the only place that defines it.

**§12 for the final answer**: every number carries its source; "checked carefully", "runs fine" and "per best practice" are forbidden; another agent's result is **not evidence** until cross-checked.

---

## 8. Where files may be written

The root `{workspace_root}`, the four exceptions that write under another root, the rule to copy out of the tree before editing, the cleanup gate: `refs/artifact-layout.md § Artifact Layout & Cleanup`. Anything not in the table may not be created.

The block below mirrors the §19.1 table; `tools/check ruleset (package repo only)::artifact_rows_agree` compares each row, both the path and the who-writes column.

```
{plan_dir}/plan.yaml + plan.<lang>.md            planner·implement·devops·test·reviewer  nothing else; a legacy plan also keeps tasks/{wave}/{task_id}.yaml, read only; {plan_dir} per `refs/plan-files.md § Where a plan lives`; living file, edited in place, no copies; planner writes the plan, then the owner of each task writes that task (§20)
{plan_dir}/errors.yaml                       any  byte-exact, never compressed
{plan_dir}/review.md                         reviewer·test  one `## Round {n} · {kind}` section per round (conformance, independent, explore, critique); earlier rounds kept
{plan_dir}/evidence/                         reviewer·test  only when test images must outlive the run; AT MOST 3 files per task
{plan_dir}/change-map.md                     implement  regenerated after each task result
.cm-tmp/{plan_id}/                           implement·devops  EPHEMERAL: change-map JSON, review packets and fetched server logs, deleted at closeout
docs/reviews/baselines/{repo}-{route_slug}/{viewport}.png test  updated only after a green run
docs/reviews/INDEX.md                        reviewer·implement  one line per review: reviewer when there is no plan, the plan's wave_commit spawn for that wave
docs/changes/adhoc/{YYYY-MM-DD}-{slug}/record.md implement·reviewer·test  the §20 record when there is no plan; test adds an exploratory-case section
docs/changes/adhoc/{YYYY-MM-DD}-{slug}/independent.md reviewer  independent review when there is no plan; separate file
docs/changes/adhoc/{YYYY-MM-DD}-{slug}/assets/ reviewer·test  AT MOST 3 files, the adhoc form of the evidence row
docs/changes/MIGRATION-MAP.tsv               devops  PERMANENT: one line per file `agent-hub docs-migrate` moved, old path and new path; only that script edits it
docs/adr/ <!-- scrub-allow: product path -->   devops  decision records, with the workspace
docs/devops/                                 devops     the whole folder: SERVER-INFO.md and the files it points to
{plan_dir}/proposal.md + design.md           brainstorm  change files (`refs/change-files.md`) in the change folder beside the plan files; living files
{plan_dir}/design.yaml                       brainstorm  machine-readable record (`agents/brainstorm.md` § Artifact layout), moved from docs/brainstorm/{slug}.yaml when change-design issues an id
docs/brainstorm/{slug}.yaml                  brainstorm  inbox for work with no change id yet: the record, docs/brainstorm/{slug}/ for attachments, docs/brainstorm/rejected-requests.md for declined requests
{plan_dir}/design/{slug}/DESIGN.md           designer  EXACTLY 1 file; with no change id yet, docs/brainstorm/{slug}/design/DESIGN.md
{plan_dir}/design/{slug}/assets/             designer  reference images DESIGN.md quotes, beside it
~/.claude/docs/design-library/{lib}/         designer·implement  GLOBAL, not copied per product
docs/audits/{YYYY-MM-DD}.md                  auditor    1 file per day
docs/errors/{session_id}.yaml                any  only when there is no plan_id
docs/deferred-backlog.md                     implement  written only by the wave_commit spawn; same workspace; each `deferred_errors[]` entry of the plan adds one line on `Approve`, never rewritten; the user later picks entries for a new plan
{sub_repo}/docs/CODE-STYLE.md                /codestyle·brainstorm·implement  in the sub-repo, style source #1 (§15)
docs/specs/                                  brainstorm  the product's behaviour spec; a change's delta `specs/<context>/spec.md` lives in the change folder (`refs/change-files.md`)
~/.claude/logs/                              any  GLOBAL, accumulating logs; the §19.3 cleanup gate does NOT delete them
templates/thresholds/thresholds.yaml  implement  GLOBAL, the shared file of every vendor number, grouped, each number with its source (`refs/thresholds.md`)
docs/thresholds.yaml                         implement  the project's copy: closeout writes it when absent, approved groups get stamped; edited in place
.cm-tmp/{task_id}/                           any  EPHEMERAL, deleted when the task closes
~/.claude-backups/{task_id}/                 any  GLOBAL, outside every workspace; copy made before editing (§19.2)
```

A legacy plan folder may still hold `tasks/`, `reviews/`, `change-map.json` or `plan.vi.md`: readers read them, no rule writes a new one (`refs/plan-files.md § Run files`).

---

## 9. Language

Which file carries which language, field by field: `CLAUDE.md § Language` and `agents/planner.md § Language`. File names and the rule on unaccented names: `refs/artifact-layout.md § Naming and content`.

---

## 10. Spec layer (SDD)

Change files (English) are written by brainstorm; `plan.<lang>.md` is the one file in the reply language: `refs/change-files.md`. Who owes which artifact, the gates, the three-tier net that only raises and never lowers: `SDD.md § Spec Layer`. Switching by class, bug A/B, hotfix spec debt, the trigger list: `SDD.md § Playbook per task type` and `SDD.md § Against misclassification`.

---

## 11. Test depth by `thinking_mode`

Test depth by `thinking_mode`: `refs/roles/test/depth-by-thinking-mode.md` § The table; the 8 stages of a test case: `refs/roles/test/journey.md`; the path patterns that force `extended`: `agents/test.md` § Paths that force extended.

---

## 12. Infrastructure: MCP, skills, hooks, templates

**MCP** (`~/.claude.json`, documented in `list-mcp.md`): `gitnexus` ✅ 13 tools · `mcp_gitlab` ✅ ~120 · `mcp_mem0` ✅ 10 (3 delete tools are under `ask`) · `mcp_figma` ✅ 2 · `designmd` ⚠️ not loaded · `kindly-web-search` ❌ dead (`uv`/`uvx` missing; `winget install --id=astral-sh.uv -e` or remove the entry). Playwright and Context7 are **plugins** (`mcp__plugin_<plugin>_<server>__`). **12 skills** load by frontmatter; a skill holds the **procedure**, an agent holds the **rules**.

**Hooks** (`settings.json`): `SessionStart` (orchestrator-first directive) · `PreToolUse` Bash → only `rtk hook claude` · `WorktreeCreate/Remove`.

**Templates** (read when writing a file, never rebuilt from memory): `templates/plan/` · `spec/` · `analysis/` · `design/` · `test/` · `audit/` · `commit/` · `SERVER-INFO.md`.

The bootstrap-cost measurement of 2026-08-31 is stale.

---

## 13. Still open

**e.** The spec branch is untested (bug types A/B, `spec-sync`, `_debt.md`, the three-tier net). **g.** 12 skills not reviewed (language, tool names since Playwright/Context7 became plugins, overlap with the agent files). **h.** `~/.claude` has no git: a config change has no rollback point beyond the file content.
