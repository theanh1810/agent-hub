---
name: review-checklist
description: Use when the reviewer agent audits code, PRD or task compliance, security or contracts, a wave's integration, design or docs, a merge request, or a wave's change blind to its plan. Gives findings that each name their rule, location and fix. Triggers on "review", "audit", "security check", "design review", "PRD compliance".
user-invocable: false
allowed-tools:
  - Read
  - Grep
  - Glob
  - mcp__gitnexus__impact
  - mcp__gitnexus__api_impact
  - mcp__gitnexus__route_map
  - mcp__gitnexus__detect_changes
  - mcp__gitnexus__query
  - mcp__mcp_gitlab__get_merge_request
  - mcp__mcp_gitlab__get_merge_request_diffs
  - mcp__mcp_gitlab__list_merge_request_changed_files
  - mcp__mcp_gitlab__get_merge_request_conflicts
  - mcp__mcp_gitlab__list_commits
  - Bash(rtk git fetch origin *)
  - Bash(rtk lint *)
  - Bash(rtk test *)
  - Bash(tools/check ruleset (package repo only))
model: inherit
---

# Review Checklist

Read-only in every mode; findings go to `implement`, and a code review files findings only (`skills/review-checklist/references/independent.md`). Finding bar, severity and report shape: `agents/reviewer.md` and `refs/roles/reviewer/finding-bar.md`; this skill holds the per-mode checks.

## Modes

`security` | `wave` | `task` | `critique` | `design` | `docs` | `merge` | `independent`. The spawn brief names the mode: read that mode's file before the first finding, no other mode's. Every mode runs the universal checklist below, then `refs/roles/reviewer/taxonomy.md`.

| Mode | Read | It holds |
|---|---|---|
| security | `skills/review-checklist/references/security.md`, then `skills/review-checklist/references/security-surfaces.md` for the surfaces the diff touches, `security-depth.md` for depth by domain and `security-audit.md` for the audit method of a candidate (same folder) | depth by surface, finding bar, threat model, safe execution, coverage ledger; per-surface checks |
| wave | `skills/review-checklist/references/wave.md` | lint, typecheck, build, tests, `detect_changes`, contracts |
| task | `skills/review-checklist/references/task.md` | PRD and `acceptance_criteria` compliance |
| critique | `skills/review-checklist/references/critique.md` | the three scopes, the rule every finding names |
| design | `skills/review-checklist/references/design.md`, `skills/review-checklist/references/performance.md` | tokens, a11y, responsive, mobile, performance hints |
| docs | `skills/review-checklist/references/docs.md` | what a docs review proposes and cites |
| merge | `skills/review-checklist/references/merge.md`, `skills/review-checklist/references/performance.md` | Phase A (devops opens the MR), Phase B (reviewer pulls and reviews, step 4 the diff scan), Severity, Forbidden, Config |
| independent | `skills/review-checklist/references/independent.md` | what the second layer reads, judges and never opens |

## Universal checklist

- Acceptance-criteria coverage from the task record (`refs/plan-files.md`): every mode but `independent`, which sees neither task record nor spec.
- **Spec** (`spec_required: true`): read the UC **before** the code. For every block of business logic ask "which spec does this rule come from?"; unanswerable means no merge. Category `spec_drift` (`refs/roles/reviewer/taxonomy.md` § `spec_drift`); a spec silent on a behaviour is "spec missing", asked of the user.
- **Spec debt** (the window carries a `hotfix` commit): `specs/_debt.md` must have a line for it, ticked once over 24 hours old; else `spec_debt_missing` 🟠. Every pass.
- **Security**: secrets/PII, authz, input validation, OWASP Top 10; `mcp__mcp_gitlab__*` or grep for secret scans on staged files.
- **Contract**: `mcp__gitnexus__api_impact` + `mcp__gitnexus__route_map`.
- Edge cases, error paths, idempotency. Over-engineering, dead code, a debt comment or `TODO` without owner **and** ticket.
- **Test quality** (real assertions, no flake), each a finding with its rule:
  - Phantom test: runs the code but asserts nothing its acceptance criterion needs; compare asserts with `covers_acceptance`.
  - Mocked data source: an integration case mocking its data source (`refs/roles/planner/test-cases.md` § Lessons that bind every plan, row 2).
  - Catch-and-swallow: an error caught and dropped or turned into success.
  - Scope drift: a changed path outside the task's `files[]`.
  - Self-repeating test (expectation computed by the code under test); implementation-coupled test that breaks on refactor; a "change detector" that goes red only when a decision changes.
- **Bug review** (problem_class bug or hotfix): three checks, each a finding when it fails; reviewer reads and runs, never edits code or inverts a predicate (the red run is implement's):
  - Every `affected_surfaces` entry of kind `sibling_path` and every `impact` d=1 caller is listed as checked or unchecked, each checked one with the `file:line` read; an unchecked one is named, never dropped. A "no regressions" without this list is an absence claim and is dropped.
  - At least one claim of the implementer's handoff ("fixed", "no regressions", "only X changed") is stated with how the reviewer tried to break it and what it found.
  - `result.red_before_fix` exists and names the same test as the green run in `result.commands[]`; absent or different is a finding.

### Rationalization → Reality

| Rationalization | Reality |
|---|---|
| "The code looks clean, skim the spec" | Opening code first is how business rules get missed |
| "It is probably a bug, file it" | No concrete case, no finding; a guess is `hypothesis`, at most 🟡 |
| "The author explained why, lower the severity" | A stated rationale never downgrades a finding |
| "Plan says so, so it is fine" | The plan does not grade itself: file it labelled "plan-mandated" |
| "I will fix this tiny thing myself" | Reviewer never edits; file it for implement |

## Closeout

Routed by lifetime (`skills/context-memory/SKILL.md`): a finding pattern recurring in **any** repo goes to **mem0** (`type: recurring_pitfall`, dedup by `{project, type, subject}`); a convention true only in **this** workspace to the project memory file `## Conventions` (that skill's § Discovery order). Keep the entry to the pattern and its subject, and never put a path in mem0.

## Gotchas

- A pin check that strips indent before comparing can show 0 off while the pins are shifted: compare the raw bytes of a copy (recorded 2026-10-01).

## Anti-patterns

`agents/reviewer.md` § Forbidden is the full list. Two procedural additions: missing PRD compliance verification (`prd_compliance`, task mode) · a vague critique with no alternative (critique mode).
