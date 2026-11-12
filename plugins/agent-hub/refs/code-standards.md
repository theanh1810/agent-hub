# Code standards

Tier 3 of `CLAUDE.md` §0.5 and §15 — the rules live here; `CLAUDE.md` keeps one pointer line per section.
Read when: writing or reviewing code — `implement` before the first edit, `reviewer` before the first finding.

---

# 0.5 Coding Principles

Hard rules for any code-writing agent. They bias toward caution over speed; for trivial tasks use judgment.

**A. Think first.** State assumptions. Uncertain → ask. Several readings → present them, do not pick. A simpler approach exists → say so. A multi-step task opens with a short plan, "step → how to check it". Push back when the request looks wrong or costlier than it needs; say why, then ask.

**B. Simplicity.** Minimum code that solves the problem; nothing speculative (no unrequested flexibility, no error handling for impossible cases). 200 lines that could be 50 get rewritten; prefer the boring, obvious solution unless a measurement, an acceptance criterion or known large data calls for an optimised algorithm (ladder rung 2, `refs/roles/implement/craft.md`). Check: would a senior engineer call this overcomplicated? Yes → simplify.

**C. Surgical.** Every changed line traces to the request. Match the existing style. Unrelated dead code → mention, do not delete. Clean up orphans your own change created (unused imports, variables, functions); what was there before is only reported. Do not remove a comment you do not understand, or code that looks unused, without approval.

**D. Goal-driven.** Define success criteria, loop until verified. Turn the request into a verifiable goal:

| Request | Goal |
|---|---|
| "add validation" | write tests for invalid inputs, then make them pass |
| "fix the bug" | write a test that reproduces it, then make it pass |
| "refactor" | tests pass before and after |

Multi-step → a verify gate per step.

**WHAT and HOW.** The ladder in `refs/roles/implement/craft.md` picks the solution (WHAT); the code is written in the project's style, naming, framework and layers (HOW, `CLAUDE.md` §8).

Working signals: no unrequested change in the diff, nothing rewritten for overcomplication, questions come before the code, not after a mistake.

**E. Comment rarely, and only where it matters (HARD).** The categories that justify a comment, the forbidden shapes and the rule that every comment in the diff is listed in the handoff are stated once in `rules/code-style/_discipline.md` §5; keep no copy. No count, no quota: a comment matching no category is a finding. A line needing a comment is usually a line to rewrite. Reviewer enforces via `category: code_comments`.

# 15. Code Standards (HARD — implement)

Before writing ≥10 new lines, cite `Pattern reference: <file:line>` from a neighbouring file; naming, structure, error types and logging match those neighbours. Split a function by **job**, not by line count: 40 lines (ceiling 80) and cyclomatic 12 are warning flags, not cut-offs. A file the agent created that nears ~400 lines is split, saying which concern moved. A new dependency is a STOP and a user approval gate.

The priority ladder, naming and shape rules and the forbidden list: `agents/implement.md` § Priorities, § Craft, § Forbidden. Enforcement: `agents/reviewer.md`.

**A written style, not a re-derived one (HARD).** `Pattern reference` alone let two sessions pick two neighbours in one module and produce two dialects. Before the first edit `implement` and `reviewer` read, in order:

| # | Source | When |
|---|---|---|
| 1 | `docs/CODE-STYLE.md` in the repo | whenever it exists — it wins over everything below |
| 2 | `rules/code-style/_discipline.md` | **always** — file budget, case coverage, length, scope, comments |
| 3 | `rules/code-style/<language>.md` | one per language in `binding_scope`, and no others |
| 4 | The neighbour cited in `Pattern reference` | always, as the local check |

`rules/code-style/README.md` § Precedence is the **only** statement of this ladder (the table is an extract; change the ladder there). It also covers 1 and 4 disagreeing and a repo with no `docs/CODE-STYLE.md` (generate or refresh with `/codestyle`). No style file → `_discipline.md` wins, and under `Risks` the handoff names the neighbour **not** followed and suggests `/codestyle`.

**Quality bar of the project.** When a project has no written quality bar (`rules/code-style/_discipline.md` § The quality floor), ask the user once while running it; where one exists, follow it and ask nothing.

**The handoff answers the five questions in `_discipline.md` § The check before the commit**: files created and why, cases covered and where, cases that cannot occur and why, estimated vs actual diff size, what was left out; §5 of that file adds a sixth, every comment in the diff with its `file:line` and category.
