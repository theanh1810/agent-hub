---
paths:
  - "**/*.js"
  - "**/*.jsx"
  - "**/*.mjs"
  - "**/*.cjs"
---
# JavaScript (Node, CommonJS)

Mechanics only. Comments: `_discipline.md` §5. Naming, function shape, structure: `agents/implement.md`. Every rule is a fallback for when the codebase has no precedent (`rules/code-style/README.md` § Precedence); the repo's `docs/CODE-STYLE.md` overrides.

---

## Module system

**Match the file you are editing; never mix the two in one file.** Compare `grep -rl 'module.exports' src | wc -l` with `grep -rlE '^import ' src` before a new file.

```js
const path = require('path');                    // 1. node builtins
const dayjs = require('dayjs');                  // 2. external
const { redisSetNX } = require('../redis');      // 3. internal, relative
```

One blank line between groups, alphabetical inside. Destructure at the require for two or three symbols; keep the namespace for more. Export at the **bottom**, one statement (`module.exports = { evaluateThreshold, toFiniteOrNull };`), not scattered `module.exports.x = …`. No circular `require`/`import`; move the shared part into a third module.

## Async

- `async`/`await`, not `.then()` chains; mixing them in one function is a finding.
- Every `await` that can reject is inside a `try` or deliberately propagates, with the handler above it named in the handoff.
- Independent awaits run with `Promise.all`; sequential awaits in a loop are a choice, with the reason (rate limit, ordering, back-pressure) in a comment.
- Never `async` on a function with no `await`: it changes the return type for nothing.
- No floating promises: an intentionally un-awaited call gets `void` or `.catch(...)`.
- No `fs.*Sync`, `execSync` or `spawnSync` on a request or event-handler path (a CLI or startup code may).

## Errors

- Throw `Error` or a subclass, never a string or object literal.
- Wrap with context when crossing a boundary, keeping the original: ``throw new Error(`ingest failed for device ${id}`, { cause: err })``.
- Catch only what you can act on. `catch (e) {}` is forbidden; catch-log-rethrow needs a reason, since the caller logs it again.
- A custom error class exists once, in one place, exported; no second `ValidationError` in a second file.

## Equality, values, mutation

- `===` and `!==` always; `==` only for the deliberate `x == null`, commented.
- `??` for defaults, `?.` for traversal; `||` as a default is a bug for `0`, `''`, `false`.
- `const` by default, `let` when reassigned, `var` never.
- Do not mutate a parameter: return a new value, or take an explicit mutable target and name it so at the call site.
- Numbers from outside go through a finite check (`Number.isFinite(Number(v))`) before arithmetic; `parseInt` without a radix is a finding.

## Tests

- Location: `code-style/README.md` § Test layout — `src/services/x/y.js` → `tests/unit/services/x/y.test.js`, or the layout the repo's `docs/CODE-STYLE.md` records.
- `describe` names the unit; `it` states behaviour (`it('returns null when the value is empty')`, not `it('works')`). Where the task has an AC, the name carries both ids — `UC-042 / AC-2` per `SDD.md` §5.
- Assert behaviour, not how it was reached: a private call count breaks on every refactor and protects nothing.
- No network, real Redis or real Mongo in a unit test; find the repo's existing fakes before writing new ones.
- A test passes alone and in any order, with fake timers and without the developer's env vars.

## When the linter is not the guard

Check what the config enforces: `eslint:recommended` with a long `"off"` list (`no-unused-vars` among them) enforces almost nothing, so these rules, `docs/CODE-STYLE.md` and `reviewer` are the only guard. Never add or tighten a lint rule in an unrelated task: it reformats untouched files and buries the real diff.

## Running `node --test` (measured, 2026-09-01)

Pass a **quoted glob**, not a directory: `node --test 'test/*.test.js'` is right; `node --test test/` reports a phantom failure. Two traps:

- `node --test` colourises its summary, so the line begins with an escape sequence, not `ℹ`: `grep '^. pass 6'` fails on output saying `pass 6`. Match the substring, or strip colour.
- Piping a command *expected* to fail into `grep` breaks under `set -o pipefail`. Capture first (`OUT="$(cmd 2>&1 || true)"`), then match.
