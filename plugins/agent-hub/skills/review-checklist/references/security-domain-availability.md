# security domain availability
<Owner: skills/review-checklist/SKILL.md>
<Read when: a diff touches shared CPU, memory, disk, connections, worker slots, queues, quotas or paid external calls reachable by untrusted requests, messages, files, tenants or agent work>

---

The resource-exhaustion bullet of `skills/review-checklist/references/security-surfaces.md` (§ Messaging, load and logic) is the base: it already names accumulating limits, cancellation, retry jitter, poison records, backtracking and decompression. This file adds the classes beyond it. Base checks: `skills/review-checklist/references/security-depth.md`. Weight: `refs/roles/reviewer/finding-bar.md` § Confidence and severity, per `skills/review-checklist/references/security.md` § What is a finding governing what qualifies, and this file adds none. Memory-integrity defects are in `skills/review-checklist/references/security-domain-memory-binary.md`, broker delivery logic in `skills/review-checklist/references/security-domain-protocols.md`; a reachable fatal error belongs here for its shared impact even when the parser is covered there.

## When to use

Untrusted requests, messages, files, tenant state or agent work can consume CPU, memory, disk, connections, worker slots, paid APIs or queue capacity, or can deadlock or crash a shared service. The domain separates a vulnerability a reviewer can read from the source from a general performance issue. Validate by reading the source and with a bounded local run; a shared or running service is never stressed to validate.

## Core discipline

- Require an input-to-cost path, a missing effective bound and an effect on another user, a shared service, a safety function or operator-owned spend; self-limiting work in the requester's own process is not a service vulnerability.
- A missing rate limit is not enough: check body, message and file caps, concurrency, queues, deadlines, database constraints, upstream gateways and per-tenant quotas before calling a path unbounded.
- No stress, saturation or production test; use asymptotic analysis, small boundary fixtures, mocked paid calls, strict local resource limits and deterministic cancellation tests.
- State attacker cost, service work, persistence, scope and recovery: one bounded input with a superlinear or persistent shared effect differs materially from sustained volume.
- Upstream caps, deployed topology, autoscaling, paid quota or recovery behavior outside the repository are `needs_validation`.

## Computational amplification classes

- **Superlinear work on small input**: catastrophic backtracking, nested parsing, recursive validation, symbolic evaluation, graph traversal, template expansion or adversarial sort and hash behavior. Derive the accepted depth or cardinality and the complexity, then show a bounded growth curve locally.
- **Representation amplification**: compressed, sparse, nested, aliased or encoded input expands far past the checked transfer or file size. Verify limits after every expansion and across parser stages: archives, images, fonts, structured documents and protocol compression tables.
- **Query and downstream amplification**: a small request creates broad scans, pathological joins, fan-out, unbounded sort or aggregation, or many downstream calls because depth, filter cardinality, pagination or expansion fields are unbounded. Confirm that authorization does not deliberately allow the same resource scope.

## Resource accumulation classes

- **Unbounded buffering and cardinality**: bodies, out-of-order streams, uploads, sessions, unique cache keys, metric labels, log fields, subscriptions or pending jobs pile up without per-item and aggregate limits. Find cleanup and expiry on disconnect, timeout, cancellation and partial parse.
- **Handle and temporary-resource leaks**: malformed or canceled work skips cleanup and keeps sockets, files, database cursors, timers, subprocesses, temporary files or object references. Confirm the leak repeats across bounded local iterations and drains a shared pool.
- **Detached work after cancellation**: a client timeout, disconnect, canceled job or failed authorization returns control but leaves database, model, network or worker work running. Trace cancellation and deadline propagation through every layer.

## Quota and scheduling classes

- **Work before authentication**: expensive parsing, key lookup, cryptography, decompression or outbound requests happen before authentication and before the earliest size or rate gate. Compare the requester's minimal effort with the shared cost, and check upstream limits.
- **Quota accounting scope and reset**: accounting keyed on an attacker-influenceable IP, route, tenant, key prefix or task ID lets one principal's work escape its budget or spend another's allocation. Read integer overflow, distributed races, retries, reconnects and account switching.
- **Pool and priority starvation**: low-priority or attacker-controlled jobs hold shared locks, workers, database pools, event-loop turns or scheduler priority that unrelated users need. Require a path that bypasses queue or concurrency fairness, or keeps a slot past its deadline.

## Failure and recovery classes

- **Reachable fatal error or deadlock**: untrusted input reaches a `panic`, abort, fatal assertion, unhandled exception, process exit, lock cycle or infinite loop in a shared process. Confirm supervisor scope and whether one worker or the whole service becomes unavailable; a restarted isolated worker may lower impact but does not erase the defect.
- **Retry storms and fail-open amplification**: timeouts, dependency errors, partially processed messages or health-check failures trigger synchronized or unbounded retries with no jitter, ceiling, circuit breaking or deduplication. Verify that one bounded failure source can create persistent aggregate work.
- **Head-of-line blocking**: one malformed record or message fails repeatedly at the front of a shared queue, partition, startup scan, migration or recovery loop. Review skip and quarantine policy, offsets, and whether other tenants share the blocked unit.
- **Unsafe recovery**: a restart, restore, fallback or cleanup path rebuilds unbounded state, ignores current quotas, or restores the very input that fails again at once. Recovery correctness is part of availability.

## Universal moves

- Build an input-to-resource table: earliest accepted size or cardinality, work before authentication, downstream fan-out, persistence, shared pool, limit and cleanup owner, recovery.
- Compare aggregate limits with per-object limits: ten thousand valid one-byte items may slip under a per-message cap while exhausting tenant-wide or process-wide state.
- Validation runs only in an isolated fixture with strict CPU, memory and time limits and small growth points, with external and paid calls mocked, stopping once the missing bound or cancellation is observable; anything needing more is `needs_validation` naming that local check.

## Validation rules

1. Name the untrusted input, the requester's work, the amplification or retained resource, the shared blast radius and the recovery; a missing limit without a concrete shared effect is hardening.
2. Confirm that no source-visible upstream, parser, queue, tenant or framework bound prevents the path; an unknown deployed control is `needs_validation`.
3. Superlinear behavior establishes the accepted complexity and bounded local growth; leaks show repeatable retention after cleanup should have run; fatal paths identify process and supervisor isolation.
4. Prioritize by low requester work, unauthenticated reachability, cross-tenant scope, persistence and poor recovery, and never validate by causing the availability impact.
5. `confirmed` needs safe local proof and a meaningful shared effect; `needs_validation` names the upstream limit, topology, quota or recovery observation an owner must check.
