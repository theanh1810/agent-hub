# security domain data lifecycle
<Owner: skills/review-checklist/SKILL.md>
<Read when: a diff touches tenant stores, derived copies (search, cache, analytics), object links, export or backup, restore, schema migration, deletion or revocation>

---

The isolation, derived-copy and export bullets of `skills/review-checklist/references/security-surfaces.md` (§ Data and tenants) are the base; this file keeps only what they lack and follows one data item through every copy and state change. Base checks: `skills/review-checklist/references/security-depth.md`. Seriousness: `refs/roles/reviewer/finding-bar.md` § Confidence and severity, by `skills/review-checklist/references/security.md` § What is a finding ruling what qualifies, and this file adds none. Provider-level storage policy is in `skills/review-checklist/references/security-domain-cloud.md`.

## When to use

The target stores multi-tenant or access-controlled data, derives search, index, cache or analytics copies, issues object links, exports or restores records, migrates schemas, or promises deletion, revocation or retention. Split a large target by primary store, cache and search, blob storage, analytics and logging, export and backup, deletion and revocation, and migration.

## Core discipline

- A tenant or owner field on a record is not isolation; find the query, key, path, policy or row-level control that enforces it on every read and write path.
- Sanitized primary data can turn unsafe in search, cache, analytics, export, previews, logs, replicas and backups, each with its own access and retention rules.
- Deletion and revocation are lifecycle contracts: check current, historical, cached, indexed, exported, restored and queued copies inside the product's stated boundary.
- A privacy or retention preference is not a vulnerability by itself; require an explicit access boundary or a deletion or revocation guarantee, plus an unauthorized reader or later operation.
- External storage policy, retention, CDN behavior, replica lag and backup access the repository does not show are `needs_validation`.

## Tenant and object isolation classes

- **Missing owner binding**: a read, update, delete, list, count or bulk query names an object without binding it to the authenticated tenant, or lets body fields supply that identity. Compare direct lookup, nested relationship, background, admin, import and legacy paths. <!-- scrub-allow: generic security term, not a personal name -->
- **Composite-key collision**: cache keys, object paths, database uniqueness, search document IDs, temporary files or deduplication keys omit tenant or environment, so two principals overwrite or fetch the same logical key even though the records have separate owners.
- **Policy and query disagreement**: row-level policy, ORM default scopes, authorization filters and raw or bypass clients apply different predicates. Check joins, aggregates, aliases, views, transactions, unscoped or service clients, and error paths where context is missing.
- **Blob reference overreach**: object keys, attachment IDs, version IDs, shared links or signed links permit operations or namespaces beyond the issuer's access, or persist after a change to the underlying access rule. Bind operation, exact object and version, audience, expiry and tenant.

## Derived data and disclosure classes

- **Index and cache drift**: a primary record's access rule or lifecycle changes without invalidating a searchable, cached, embedded, thumbnail, feed, preview or index copy. Validate filtering at retrieval time as well as at ingestion and invalidation.
- **Telemetry as an alternate reader**: private content or credentials flow into analytics, logs, traces or diagnostics with wider access, longer retention or tenant mixing. Confirm the data class and a realistic reader; field names, public identifiers and operator-only content under intended policy are not enough.
- **Aggregate oracles**: counts, filters, ordering, errors, unique constraints, timing or notification behavior reveal protected object or account state. Needs a concrete confidential predicate and an observable distinction, not general response variance.

## Export, backup, restore and migration classes

- **Export scope expansion**: a snapshot, portability package, report or backup holds other tenants, inaccessible fields, soft-deleted data, secret values or history above the requester's access. Check per-item authorization after selection and authorization to fetch the finished artifact.
- **Restore authority expansion**: import or restore skips owner, schema, access, uniqueness or validation rules, overwrites existing resources, or recreates records in a tenant the requester cannot write. Treat archive contents as untrusted and authorize the resulting operation instead of trusting earlier provenance.
- **Migration defaults**: old records lack tenant, access or lifecycle fields, incompatible IDs collide, or a partial rollout makes old and new readers apply different defaults. Read backfill, dual read and write, compatibility, rollback and resumed-migration paths.
- **Backup and replica scope drift**: keys, storage accounts, cross-region replicas, restore environments or support snapshots have a broader identity or tenant scope than primary data. Source confirms only in-repository policy; hosted access and retention are `needs_validation`.

## Deletion, revocation and lifecycle classes

- **Soft-delete bypass**: direct lookup, search, relation traversal, object link, background processor or restore ignores the lifecycle predicate and returns or acts on a deleted or revoked record. Check whether soft-deleted identifiers can be registered again before every reference is gone.
- **Stale authorization after change**: membership removal, access update, consent withdrawal, secret revocation or role downgrade fails to invalidate sessions, caches, subscriptions, jobs or materialized data that keep authorizing later operations.
- **Retention overrun by queued work**: deletion finishes in primary storage while queued processors, retries, exports, analytics or generated artifacts recreate or keep the data past the promised boundary. Look for idempotent deletion and tombstone propagation.
- **Restore reintroduces invalid state**: backup, undo, undelete or replica recovery brings back data, credentials, memberships or permissions current policy no longer allows. Re-authorize restored state and reapply lifecycle changes made after the snapshot.

## Universal moves

- Pick one protected record and draw its primary write, query, cache, index, event, export, backup, deletion and restore paths, marking principal and tenant at every edge.
- Compare two dummy tenants through the same local service methods, then repeat after an access change, deletion, account switch and restore; real user data is never used.
- Start at bypass clients, background jobs, migrations, global uniqueness and cache keys: they commonly omit the request-scoped identity interactive endpoints carry.

## Validation rules

1. Name the lower-trust principal, the protected data or state, the affected owner or tenant, the alternate copy or operation, and the unauthorized disclosure or change.
2. Cite both the intended source-of-truth policy and the path that omits or contradicts it, and confirm no other layer enforces the same tenant or lifecycle condition.
3. Cross-scope access or stale lifecycle behavior is shown with local dummy tenants and non-sensitive fixtures, stopping at the smallest observable record or operation.
4. When external cache, object storage, replicas, analytics, backup or retention policy is needed, the candidate is `needs_validation` with the owner-observed check stated.
5. `confirmed` needs complete lineage and a concrete boundary effect; `needs_validation` names the unresolved storage, access, invalidation, retention or restore fact.
