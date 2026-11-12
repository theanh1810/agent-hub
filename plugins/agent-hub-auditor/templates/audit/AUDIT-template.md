<!-- Report template for agents/auditor.md. Write the report in the user's reply language.
     Output goes to {workspace_root}/docs/audits/{YYYY-MM-DD}.md, one file per day.
     The root is the workspace root, not a sub-repo root. -->

# Fleet audit report — {YYYY-MM-DD}

**Time window:** {from} → {to}
**Sources scanned:** {N plan dirs}, {N error files}, {N MRs}, {N mem0 entries}, {N session logs}
**Total tasks run:** {N} | **Completed:** {N} ({completion_rate}%) | **Failed:** {N} | **Rework:** {N} ({rework_rate}%)

---

## 1. Scorecard per agent

| Agent | Tasks | Done | Fail | Done% | Rework | Loop | Latency avg | Tools/task | Note |
|---|---|---|---|---|---|---|---|---|---|
| orchestrator | ... | ... | ... | ...% | ... | ... | ... | ... | {status} |
| brainstorm | ... | ... | ... | ...% | ... | ... | ... | ... | ... |
| ...

## 1a. By tier and run_mode

> Group each spawn by `tier` (L0-L4) and `run_mode` (`refs/effort-routing.md § Calibration data`). A spawn with no recorded `tier` (every spawn before effort routing existed) is left out of 1a, NOT folded into L2 by the fallback, and still counts in section 1. A tier with no runs prints `N/A`, NOT `0%`.

| Tier | Run mode | Tasks | Done% | Loop | Tools/task | Latency avg | Token | Reviewer returned on first pass |
|---|---|---|---|---|---|---|---|---|
| L0 | normal | ... | ...% or N/A | ... | ... | ... | ... | ...% or N/A |
| ...

## 1b. SDD metrics

> Omit this section if the workspace has no `docs/specs/`. Write: "Project has not adopted SDD."
> No adoption date in `specs/README.md` → print `N/A` for the whole table, NOT `0%`.

**Adoption date:** {sdd_adopted} · scope: {full | partial: list modules} · measurement window: {from} → {to}

| Metric | Value | Denominator | Threshold | Status | What it says |
|---|---|---|---|---|---|
| Spec Coverage | {x}% or N/A | {n} active UC | ≥90% greenfield / ≥70% hot module | 🟢🟠🔴 | {1 sentence} |
| AC Coverage | {x}% or N/A | {n} AC of implemented UC | ≥80% | | {missing test: n · not measurable: n} |
| Regen Success Rate | {x}% or N/A | {n} spec_required tasks | ≥70% | | {suspect unclear spec OR wrong test + plan_id} |
| Trace Ratio | {x}% or N/A | {n} commits after the adoption date | ≥60% | | {which commits lack a UC ID} |

> An AC "not measurable" has a test that carries no `UC-XXX / AC-N` label. It is not a missing test.
> Above 30%, run one pass that labels test names; do not write more tests.

### `spec_required` misclassification
| Signal | Count | Total | Rate | Threshold | Reading |
|---|---|---|---|---|---|
| Escalated by brainstorm (net 1) | | | | >30% 🟠 | |
| Caught by reviewer (net 3) | | | | >10% 🟠 | |
| Silent net (both = 0 for ≥3 days) | | | | 🟠 | {suspect the net is not running} |

### Overdue spec debt
| Logged on | Kind | Incident | Patched in | UC to update | Days overdue |
|---|---|---|---|---|---|

## 2. Top patterns

### 2.1 Recurring user corrections (≥3 times makes a pattern)
| Pattern | Subject | Preceding agent | Times in period | Cumulative total | Example plan_id |
|---|---|---|---|---|---|
| "redo this button's UI" | ui-button-fix | implement | 5 | 7 | plan-XXX |
| ...

A row marked `not yet accumulated` in the Cumulative total column means mem0 was unavailable at run time; the next auditor run applies that row exactly once.

### 2.2 Unreasonable failures
| plan_id | task_id | Symptom | Why unreasonable | Recommendation |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

### 2.3 Scope leakage
| plan_id | Agent | File outside binding_scope | Reason |
|---|---|---|---|
| ... | implement | src/x.ts | no justification |

### 2.4 Reviewer rubber-stamp
| MR | Verdict | Dead code count | Reuse miss | Note |
|---|---|---|---|---|
| ... | pass | 3 | 2 | reviewer ignored findings |

### 2.5 Test coverage gaps
| plan_id | Endpoint | L3 observed | L4 binding | Missing |
|---|---|---|---|---|
| ... | POST /api/x | no | no | L3+L4 |

## 3. Trend (7-day)

| Metric | D-7 | D-6 | ... | today | Direction |
|---|---|---|---|---|---|
| completion_rate | 82% | 85% | ... | 78% | ↓ |
| rework_rate | 15% | 12% | ... | 22% | ↑ red |
| avg_latency_sec (brainstorm) | ... | ... | ... | ... | ... |

## 4. Specific recommendations

| # | Problem | Agent / Skill / File | Proposed action | Severity |
|---|---|---|---|---|
| 1 | implement leaked scope in plan-XXX | implement.md scope-binding section | Raise a file:line warning when leaving the shortlist | high |
| 2 | reviewer passed with dead code | review-checklist merge | Require citing dead_code_count >0 = needs_changes | medium |
| ... | ... | ... | ... | ... |

## 5. Positive highlights

- {Good pattern 1, not only criticism}
- {Good pattern 2}

## 6. Open questions (the user decides)

- {Question 1; if the trend stays red, escalate}
