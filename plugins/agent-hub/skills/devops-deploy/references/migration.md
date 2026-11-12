# Migration and deprecation

Load when a deploy replaces a system, API or library, removes a feature, or changes a database schema. Every deploy, migration run or removal in this file is a devops step that needs approval (`requires_approval: true`) and a rollback path, never a side effect of another step; stage sizes and rollback timings come from the rollout group (`refs/thresholds.md`).

## Decide first
Deprecate only when all of these are answered:
- The system no longer gives unique value.
- The consumers are counted, so the migration scope is known.
- A replacement exists and is proven in production; without one, build it first.
- The migration cost per consumer is known (automate it when trivial) and weighed against the cost of keeping the old system.

Advisory deprecation (warnings, docs, migration on the consumer's schedule) is the default. Compulsory (a removal date) only for a security problem, a blocker or an unsustainable cost, and then with migration tooling, docs and support. Plan the removal at design time: clean interfaces, flags and a small surface make a system removable later.

## Process
1. Build the replacement: it covers the critical use cases, has a migration guide, and has run in production.
2. Announce: status, replacement, removal date or "advisory", reason, and concrete migration steps.
3. Migrate consumers one at a time: list touchpoints, switch, verify behaviour with tests, remove the old reference, confirm no regression. The owner of the deprecated infrastructure does the migration or keeps it backward compatible; announcing and leaving consumers alone is not a migration (the churn rule).
4. Remove only at zero active use shown by metrics, logs or dependency analysis: the code, its tests, docs and config, then the deprecation notices.

## Patterns
- **Strangler**: old and new run in parallel and traffic moves in stages (stage sizes from group rollout) until the old system serves none; then remove it.
- **Adapter**: the old interface stays and delegates to the new implementation, so consumers migrate later.
- **Flag migration**: a flag switches consumers one at a time; the flag is removed after full rollout.

## Schema changes: expand, migrate, contract
Data cannot be rolled back by reverting a deploy, and during a rollout old and new code run together, so a column is never changed in place. Each phase is its own deploy, independently reversible:
1. **Expand**: add the new column nullable beside the old one.
2. **Dual-write**: the application writes both.
3. **Backfill**: copy existing rows in throttled batches, off the hot path, so no table lock.
4. **Switch reads** to the new column, keep dual-writing, let it bake.
5. **Contract**: stop writing the old column, then drop it in a separate, later deploy.

Rules:
- Additive steps (nullable column, new table, new index) are safe in any deploy; a drop or rename goes last, alone, after no code references the old shape.
- Every migration has a down path that was written and run before merge; one that cannot be reversed cannot be rolled back.
- Large indexes are built without blocking writes (for Postgres, `CREATE INDEX CONCURRENTLY`).
- A risky cutover sits behind a flag.
- Running a migration on a deployed database is a devops step with approval and a backup; implement only writes the migration files.

## Zombie code
Code with active consumers but no owner, failing tests and unpatched dependencies either gets an owner or gets a concrete deprecation plan; it does not stay in limbo.

## Red flags
A deprecation with no replacement, tooling or usage measurement · new features added to a deprecated system · code removed before zero use is verified · a schema change shipped in the same deploy as the code that needs it · a column renamed or dropped in place · a migration with no tested down path or a backfill that locks the table.

## Done when
The replacement is proven and covers the critical cases; a migration guide exists; every consumer is migrated (by metrics); old code, tests, docs, config and notices are gone; schema changes shipped in phases, both code versions were valid at each step, each migration has a tested down path, and the destructive step shipped in its own deploy.
