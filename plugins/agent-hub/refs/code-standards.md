# Code standards

<Owner: rules/core.md § Four principles>
<Read when: writing or reviewing code: `implement` before the first edit, `reviewer` before the first finding>

---

# Coding Principles

The four principles of `rules/core.md`, applied to code. Hard rules for any code-writing agent. They bias toward caution over speed; for trivial tasks use judgment.

**A. Think first.** State assumptions. Uncertain → ask. Several readings → present them, do not pick. A simpler approach exists → say so. A multi-step task opens with a short plan, "step → how to check it". Push back when the request looks wrong or costlier than it needs; say why, then ask.

**B. Simplicity.** Minimum code that solves the problem; nothing speculative (no unrequested flexibility, no error handling for impossible cases). 200 lines that could be 50 get rewritten; prefer the boring, obvious solution unless rung 2 of the ladder in `refs/roles/implement/craft.md` § Priorities calls for more. Check: would a senior engineer call this overcomplicated? Yes → simplify.

**C. Surgical.** Every changed line traces to the request. Match the existing style. Unrelated dead code → mention, do not delete. Clean up orphans your own change created (unused imports, variables, functions); what was there before is only reported. Do not remove a comment you do not understand, or code that looks unused, without approval.

**D. Goal-driven.** Define success criteria, loop until verified. Turn the request into a verifiable goal:

| Request | Goal |
|---|---|
| "add validation" | write tests for invalid inputs, then make them pass |
| "fix the bug" | write a test that reproduces it, then make it pass |
| "refactor" | tests pass before and after |

Multi-step → a verify gate per step.

**WHAT and HOW.** The ladder in `refs/roles/implement/craft.md` picks the solution (WHAT); the code is written in the project's style, naming, framework and layers (HOW).

Working signals: no unrequested change in the diff, nothing rewritten for overcomplication, questions come before the code, not after a mistake.

**E. Comment rarely, and only where it matters.** The categories that justify a comment, the forbidden shapes and the rule that every comment in the diff is listed in the handoff are stated once in `rules/code-style/_discipline.md` §5; keep no copy. No count, no quota: a comment matching no category is a finding. A line needing a comment is usually a line to rewrite. Reviewer enforces via `category: code_comments`.

# Code Standards (HARD — implement)

Before writing ≥10 new lines, cite `Pattern reference: <file:line>` from a neighbouring file; naming, structure, error types and logging match those neighbours. Split a function by **job**, not by line count: 40 lines (ceiling 80) and cyclomatic 12 are warning flags, not cut-offs. A file the agent created that nears ~400 lines is split, saying which concern moved. A new dependency is a STOP and a user approval gate.

The priority ladder, naming and shape rules: `refs/roles/implement/craft.md` § Priorities, § Craft; the forbidden list: `agents/implement.md` § Forbidden. Enforcement: `agents/reviewer.md`.

**A written style, not a re-derived one.** `Pattern reference` alone let two sessions pick two neighbours in one module and produce two dialects. Before the first edit `implement` and `reviewer` read, in order (`implement` gets row 3 by hook at its first write in that language, `refs/roles/implement/sources.md` 5b):

| # | Source | When |
|---|---|---|
| 1 | `docs/CODE-STYLE.md` in the repo | whenever it exists — it wins over everything below |
| 2 | `rules/code-style/_discipline.md` | **always** — file budget, case coverage, length, scope, comments |
| 3 | `rules/code-style/<language>.md` | one per language in `binding_scope`, and no others |
| 4 | The neighbour cited in `Pattern reference` | always, as the local check |

`rules/code-style/README.md` § Precedence is the **only** statement of this ladder (the table is an extract; change the ladder there). It also covers 1 and 4 disagreeing and a repo with no `docs/CODE-STYLE.md` (generate or refresh with `/codestyle`). No style file → `_discipline.md` wins, and under `Risks` the handoff names the neighbour **not** followed and suggests `/codestyle`.

**Quality bar of the project.** When a project has no written quality bar (`rules/code-style/_discipline.md` § The quality floor), ask the user once while running it; where one exists, follow it and ask nothing.

**The handoff answers the five questions in `_discipline.md` § The check before the commit**: files created and why, cases covered and where, cases that cannot occur and why, estimated vs actual diff size, what was left out; §5 of that file adds a sixth, every comment in the diff with its `file:line` and category.

## Additions from other packs

The ladder orders choices inside an approved task; it never removes a requirement, a test or a never-cut line. Lines 41-42 of the block: mark a deferral as `refs/roles/implement/close-task.md` § Shortcuts says.

<!-- vendored:begin id=pt-n11 src=DietrichGebert/ponytail@96608e078b2d5ea607c5c3b8b5a54d1c1fba6846:skills/ponytail/SKILL.md#L23-L44 licence=MIT -->
## The smallest complete change

Take the first option that fully works:

1. Does it need to exist? Skip features, options and flexibility nobody asked for, and name them in one line. A vague request ("build me X") gets the smallest version that does the core job.
2. Already in this codebase (a helper, component, service, pattern)? Use it the way the surrounding code does.
3. Standard library or a platform feature? Use it, unless the project has its own. A house component beats a native widget.
4. An installed dependency? Use it. Never add a dependency for a few lines.
5. Can it be one line a reader gets at a glance? One line.
6. Otherwise: the minimum code that works.

- Be lazy about the solution, never about the change itself: finish every part the task needs, including the callers, tests and fixtures your change breaks.
- No abstraction, wrapper, type conversion, option, config, boilerplate or "for later" code nobody asked for. Keep values in the form the platform already gives you. Deletion beats addition. Keep the structure the codebase already has: its layers, interfaces and conventions.
- The shortest working diff wins, once you know everything it must touch. A one-liner that needs decoding is not short.
- Comment only the why the code cannot show, in one line.
- Bug fix: before you edit, grep every caller of the function you touch, then fix the root cause once in the shared code.
- Code you move or merge keeps its error handling and validation.
- Between options of equal size, take the one that is correct on edge cases.
- Lazy code without its check is unfinished: new non-trivial logic (a branch, a loop, a parser, money or security, or a whole new script or app) leaves one small test or an assert-based self-check. Trivial changes need none.
- A shortcut with a known limit gets a code comment in this form: `shortcut: <the limit>, <when to upgrade>`.

Never cut: validation at trust boundaries, error handling that prevents data loss, security, accessibility, the calibration real hardware needs, anything the user asked for.
<!-- vendored:end id=pt-n11 -->
