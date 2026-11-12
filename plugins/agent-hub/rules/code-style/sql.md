---
paths:
  - "**/*.sql"
---
# SQL, schemas, and migrations

Covers Prisma, Mongoose and hand-written SQL. Mechanics only. The repo's `docs/CODE-STYLE.md` overrides anything here.

**A schema change is never a routine edit.** `SDD.md` §11.1 forces `spec_required: true` on any diff touching `**/migrations/**`, `schema.prisma`, `*.sql`, or a model gaining or losing a column; the spec comes first.

---

## Naming

Follow the existing schema exactly (`device_field_configs` beside `DeviceFieldConfig` is two conventions). With no precedent: tables plural, columns `snake_case` in SQL and `camelCase` in Prisma/Mongoose models, booleans as predicates (`is_active`, `has_expired`), timestamps ending `_at`, foreign keys `<entity>_id`. Business names come from `specs/entities/`, never invented (`agents/implement.md` § Naming).

## Migrations (HARD)

- **Additive first.** Add the column nullable or with a default, backfill, switch the code, drop the old column in a **later** migration once nothing reads it. A rename is add + backfill + drop, never in place.
- **A destructive step needs the approval gate and a stated backup**: `DROP`, `TRUNCATE`, `NOT NULL` on an existing column, a type narrowing (`CLAUDE.md` §10).
- **Write the down-migration and say whether it restores data** ("down drops the column and its data is gone" is honest, an empty one is not).
- One concern per migration: schema change and backfill in one file cannot be rolled back independently.
- Never edit a migration that has run anywhere; write a new one.
- State the lock: an index build or column rewrite on a large table can block writes; say how long and whether it needs a window, or use the concurrent form.

## Queries

- **Always bind parameters.** String interpolation into SQL is an injection hole even from "our own code"; 🔴.
- **No N+1**: a query inside a loop over rows gets hoisted, joined or batched (precedent: `iot-platform-be` `src/services/dataProcessorService.js:1367-1375`, comment `H-02`).
- `SELECT` the columns you use; `SELECT *` breaks quietly when a column is added and moves needless bytes.
- Every query that can return many rows has a limit, or a documented reason it cannot.
- An index ships with the change that needs it, the reason (query, predicate) in the migration.
- Multi-statement writes that must all land run in a transaction; say the isolation level when it matters.

## Prisma

The schema is the source of truth (never hand-edit generated client code) · `select` or `include` explicitly · nested writes that must be atomic go in one `$transaction` · `$queryRaw` needs a reason and the tagged-template form so values are parameterised; `$queryRawUnsafe` is 🔴 unless the user approved it that turn · `strict` stays on.

## Mongoose

- The schema defines the shape; `strict` stays on, since a field written but not declared vanishes silently.
- Declare indexes on the schema, not by hand on the server, so they travel with the code.
- `lean()` for read-only paths: full documents carry unused change tracking.
- Mongo has no cross-collection transaction by default: two related writes are two failure modes; say which is left dangling if the second fails.

## Tests

- Test against a real engine; an in-memory fake accepts what the engine rejects, constraints and types especially.
- A migration is tested forward **and** back on a copy with representative rows.
- Where the change carries an AC, the test name carries `UC-XXX / AC-N` per `SDD.md` §5.
