---
paths:
  - "**/*.js"
  - "**/*.jsx"
  - "**/*.mjs"
  - "**/*.cjs"
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.mts"
  - "**/*.cts"
  - "**/*.py"
  - "**/*.sql"
---
# Discipline — size, coverage, and scope

Language-agnostic; read on every code task. Five failures survive good naming and function shape; a floor stops the rest.

---

## 1. File budget

**A new file needs a reason a reader would accept**, stated in the handoff, one line per new file. "Keeping things organised" is not a reason.

| Situation | Do |
|---|---|
| The logic belongs to an existing module and is <100 lines | put it in that file |
| A file you made would pass ~400 lines, or gains a second unrelated concern | split it, and say which concern moved |
| The language or framework requires a file per unit (a route, a migration, a component) | follow the framework |
| A new layer (a port, an adapter, a use-case) the architecture already names | follow the architecture |

**Forbidden without being asked**: `utils.js` / `helpers.py` / `common.ts` as a home for one function · a `types` or `constants` file holding one symbol used in one place · an `index` that only re-exports one module · a wrapper whose body is one call to the thing it wraps · a config file for a value that never had a second value · a `README.md` inside a directory the task did not create.

**A function used by one caller lives next to that caller**; move it out on the second caller, not in anticipation. Report `files created: N` and justify each; a task creating more files than it changed reorganised instead of solving, so say so.

---

## 2. Case coverage

Walk the list and write an answer for each; "cannot happen here" takes one clause, silence is not an answer.

Every input:
- **empty** — empty string, array, object, zero rows
- **absent** — `null`, `undefined`, a missing key, a missing file
- **boundary** — at the threshold, one below, one above; if the spec says `> 80`, 80 is a test
- **wrong type or shape** — where a value crosses a boundary the type system does not police (request body, queue message, DB row, parsed file)
- **too large** — the 10,000-item list, the 1 MB string

Every operation:
- **runs twice** — the retry, the double click, the redelivered message; say whether it is idempotent
- **fails halfway** — what is left behind and who cleans it
- **runs concurrently with itself** — two workers, tabs or requests; say whether that is possible here before saying it is safe
- **the dependency is down or slow** — the timeout, and what the caller sees

Every output:
- **the error path** — the message a person reads, and whether it leaks anything internal
- **the empty result** — distinguished from the failure, not merged into it

Where a case cannot occur, say **why** (a type, a DB constraint, an upstream validation, `file:line`); "won't happen" without a reason becomes an incident. **Each case that can occur is a test or a stated non-goal**, not a comment or TODO.

---

## 3. Length — measured against what the task needs

Before writing, say what the smallest correct change looks like; after writing, compare.

- A diff **3 times larger** than the estimate needs a sentence on what was found (real, or scope that arrived unnoticed). 200 lines that could be 50 get rewritten.
- **Solve the stated problem at the stated generality.** A parameter, strategy hook or interface with one implementation answers a question nobody asked.
- **No configuration for a value that never varied**: inline it with a named constant.
- **No abstraction on first use**: two call sites are a coincidence, three a pattern.
- **Do not rebuild what the codebase has.** Grep before writing a helper; a second implementation drifts from the first.
- Prefer the boring, obvious solution; prefer deleting to adding (removing lines with tests green is the best outcome).

---

## 4. Scope

- Every changed line traces to the request or to something the request broke; a line tracing to neither is removed before the commit, however small.
- Formatting, renaming and reordering **outside** the touched functions stay out of the diff; they hide the real change.
- Clean up orphans your own change created (unused imports, variables, functions). Unrelated dead code and bugs are **reported** under `Risks` with `file:line`, not fixed. Do not delete a comment you do not understand, or code that looks unused, without approval.
- Editing a file outside `binding_scope` is `needs_revision`, not a judgement call.

---

## 5. Comments

A comment is justified one at a time, never budgeted. **Every comment in the diff is listed in the handoff** — one line each, with its `file:line` and the category below. A comment matching no category is a finding: rewrite it into one, or delete it.

**Plan ids stay out of code.** A plan id (a task id such as `W2-T7`, a plan task's own `AC-n`, a test case id, a question id `Q-…`, a finding or round id) never appears in a code comment, test name or test description: amend rounds renumber plan lines, so it soon points at nothing. Two exceptions: a spec id `UC-042 / AC-2` stays in test names (`SDD.md` §5 requires it; spec numbers are never renamed); a commit message may carry plan ids (closeout joins a commit to its task by id).

There is deliberately no count, ratio or cap: a comment quota produced comments written for the linter (`agents/reviewer.md` § Comment policy still flags a docstring added to fill one). Listing every comment cuts the unjustifiable ones without capping the earned ones. The target is short **and** complete.

**The categories.** A comment qualifies when it carries one of these. Stated only here; every other file points at this section:

- **A decision other code depends on** — an ordering, a nullability, a side effect a caller relies on.
- **Something dangerous to change** — a constant tied to a device or a protocol, a sequence that must not be reordered.
- **A business rule not derivable from the code** — cited as `UC-XXX / AC-N`.
- **The reason for a cast, a magic value, or a workaround** — with its source.
- **A non-obvious constraint** — *and the comment must say where it comes from*: which file, system or protocol. A constraint with no stated origin does not qualify; naming the origin is what separates a constraint from a guess.

**Forbidden, whatever the category**: restating the identifier · a dead-code marker · an author stamp · a changelog line · a `TODO` with no owner and no ticket; rename the identifier, delete the line, or name the owner and ticket instead.

**A line needing a comment is usually a line to rewrite**; try the rewrite first.

## The check before the commit

Answer in the handoff; skip none.

1. `files created: N` — and one line of justification each. Zero is a good answer.
2. Which of the §2 cases can occur here, and where each is covered (test id or `file:line`).
3. Which cases cannot occur, and why each is impossible.
4. Estimated smallest diff vs actual diff; if much larger, why.
5. What was deliberately left out, and why that is safe.

## The quality floor

**The floor needs nothing installed** and holds in every repo:
- no new line that switches off an error check (`@ts-ignore`, `eslint-disable`, `# noqa`);
- no fake "not implemented" body and no empty `catch`;
- no test removed, skipped or deleted without a stated reason;
- no secret in source;
- the standard file itself is never weakened to let a change pass.

**A project's quality bar is one file of numbers**, each paired with the command that produces its verdict and the reason; a number with no command is an aspiration. With no target yet, use a ratchet: record today's figure and forbid only worse (small tolerance); demanding 80% of a codebase at 62% teaches everyone to live with red. **Tightening is quiet; loosening is loud**: a change that lowers a threshold, drops a check or adds an exception is shown plainly for the user's approval. An exception has an owner, a reason and an expiry of at most one year.

**When a project has no written bar, ask the user once while running there; when one exists, follow it and skip the question**.

**Heavy checks stay out of the fast loop.** After each file, type check and lint; at the task's end, the tests related to the change; the full suite runs in CI. A gate switched off is worse than none. Gate the change, not the repo: coverage of the lines just changed is a number the agent can raise; whole-project coverage is inherited.
