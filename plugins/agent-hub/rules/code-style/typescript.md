---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.mts"
  - "**/*.cts"
---
# TypeScript

Mechanics only. Comments: `_discipline.md` §5. Naming, function shape, structure: `agents/implement.md`. The repo's `docs/CODE-STYLE.md` overrides anything here. Everything in `javascript.md` about async, errors, equality and mutation applies unless contradicted below.

**Check `tsconfig.json` first.** `strict`, `strictNullChecks` and `noImplicitAny` change what correct code looks like; writing for the wrong setting compiles but lies.

---

## Types

- **`any` is a stop.** Unknown type → `unknown`, narrowed. An `any` that survives into a commit needs a one-line comment saying what blocked the real type.
- **No `as` to silence the compiler**: a cast carries its reason; `as unknown as T` needs a much better one.
- **Do not annotate what is inferred** (`const n: number = 1`). Annotate what forms a contract: exported function parameters and return types, public class members.
- **Prefer a union of literals to a bare `string`** where the set is known (`'pending' | 'settled'`).
- `interface` for an object shape others implement or extend; `type` for unions, intersections and function shapes. Pick one for plain object shapes and hold it; follow the repo.
- Non-null `!` claims the value exists: use a guard clause, and where `!` is right say why.

## Nullability

With `strictNullChecks`, `T | undefined` and `T | null` differ deliberately. Do not widen a return type to make a call site compile; fix the call site.

## Imports and exports

Order: node builtins → external → internal aliases (`@/...`) → relative, a blank line between groups. Type-only imports use `import type`. Prefer named exports: a default export is renamed at every call site.

## Framework shape (NestJS and similar DI frameworks)

- One decorated class per file: controller, service, module, guard, DTO each in its own file — the framework's rule, so `_discipline.md` §1 defers to it.
- A controller validates and delegates; business logic in a controller is a layer violation.
- Inject through the constructor; `new` on an injectable defeats the container and the tests.
- DTOs carry the validation decorators; the service trusts what it receives and says so.
- Names follow the framework: `OrderService`, `OrderController`, `CreateOrderDto`, `order.service.ts`; no parallel convention.

## Tests

- Location: `code-style/README.md` § Test layout — `tests/unit/` mirroring `src/`, or the repo's recorded layout.
- Type the mocks: an `any` mock lets a test keep passing after the real signature changes.
- Where the task has an AC, the test name carries both ids — `UC-042 / AC-2` per `SDD.md` §5.

## Formatter

Where `.prettierrc` exists it owns whitespace, quotes, semicolons and line width; do not argue with it or hand-format against it. Run it on the files the task touched, never across the repo.
