# Performance work and dependencies
<Owner: agents/implement.md § References>
<Read when: the task optimises performance, fixes a slowness, or adds, removes or bumps a dependency.>

---

## Performance work

> Measure before optimizing.

No evidence of a problem means no optimisation.

1. **Measure first**, with synthetic numbers and real user data. For a slowness bug take a baseline with a clock, profiler or query plan, then bisect to find it.
2. Find the actual bottleneck; change exactly one thing; measure again the same way; then guard against regression.
3. One change at a time so the result is attributable. Compare the gain to run-to-run noise (3% inside ±5% is not an improvement). Same conditions: never a cold cache against a warm one.
4. Unchanged, worse, or a failing test: revert. 'Neutral' is a revert, not a keep. An "optimisation" that drops work the product needs (a check, a cache of something that must be fresh) does not count.
5. Keep a ledger of every performance experiment, reverted ones too (idea, before and after, kept or reverted, why), so a dead idea is not retried.
6. Watch only what users feel (LCP, INP, p95 latency), not every number available.

**Where is it slow?** Initial load, interaction, after navigation, or backend. Backend: one endpoint slow, every endpoint slow, or intermittent.

- Every endpoint slow at once, time spent waiting for a connection, DB idle across sessions: suspect connection-pool exhaustion.
- A slow query is measured with `EXPLAIN ANALYZE`, never guessed as "add an index".
- Caching something already fast adds a network hop and a stale-data bug.

## Dependencies

> Every dependency is a liability.

- **New one: stop and ask** (`reason: new_dependency_approval`) with the name, what it replaces and its transitive count. First ask: can the existing stack do it · how heavy is it · is it maintained · known vulnerabilities · does the licence fit. Prefer the standard library. Never install before approval.
- **Bumping one is a real code change**: read the changelog, not only the version number; one package (or one small related group) per change; tests green before and after; read the lockfile diff and let the package manager rewrite it; never hand-edit a lockfile.
- A library's own helper beats a hand-rolled one. Catch errors as a chain from specific to general so retryable failures (429, 5xx, network) separate from non-retryable (400, 404); match on the error's type or code, never on an error message string.
