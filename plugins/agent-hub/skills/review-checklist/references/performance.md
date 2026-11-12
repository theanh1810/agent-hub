# Performance review

Load when a diff touches a screen, bundle, query, cache or request path. Bands and budgets (Core Web Vitals bands, bundle, stylesheet, image, font, API latency) are read from group `web_perf` of `templates/thresholds/thresholds.yaml` (`refs/thresholds.md`); a value is a gate only after the project approved the group, otherwise it is a suggestion. Measure before and after: a finding without a measurement is a suggestion.

## Frontend
- **Images**: modern formats, `srcset` and `sizes`, explicit `width` and `height` (also on `<source>`), `loading="lazy"` and `decoding="async"` below the fold; the hero or LCP image uses `fetchpriority="high"` and is never lazy.
- **JavaScript**: bundle within the `web_perf` budget; routes and heavy features split by dynamic `import()`; tree shaking works (the dependency ships ESM and marks `sideEffects: false`); no blocking script in `<head>` (`defer` or `async`); heavy computation in a Web Worker.
- **Main thread (INP)**: long tasks are broken up with `scheduler.yield()` (or a `yieldToMain` helper inside loops); `requestIdleCallback` for deferrable work; analytics and logging leave the event handler so the response is not delayed; `React.memo`, `useMemo` and `useCallback` only where a profile shows the gain.
- **Layout stability (CLS)**: at most 0.1; reserve space for images, embeds and late-loading content.
- **Third parties**: `async` or `defer`, audited for size, a facade for heavy embeds such as chat widgets.
- **CSS**: critical CSS inlined or preloaded, nothing render-blocking for non-critical styles, no CSS-in-JS runtime in production.
- **Fonts**: few families and weights, WOFF2 only, self-hosted, LCP-critical fonts preloaded, `font-display: swap` (or `optional`), subset by `unicode-range`, variable fonts when many weights are needed, fallback metrics tuned with `size-adjust` to cut CLS, system stack considered first; total within the `web_perf` font budget.
- **Network**: long `max-age` with content hashes, `Cache-Control` on API responses, HTTP/2 or HTTP/3, `preconnect` for known origins, `fetchpriority` on critical non-image resources, no needless redirects.
- **Rendering**: no layout thrashing (batch reads, then writes), animate `transform` and `opacity`, virtualise long lists, `content-visibility: auto` with `contain-intrinsic-size` for off-screen sections, no `unload` handler and no `no-store` on HTML so back/forward cache stays available.
- **Re-renders (React)**: stable props, memo where the profile shows a cost, no inline object or function props on a hot child.
- **Measure**: field data first (CrUX or RUM), then the DevTools Performance panel on a throttled CPU or a mid-range device, Lighthouse, a bundle analyser; use the `web-vitals` attribution build to find the slow interaction.

## Backend
- **Queries**: no N+1 (eager load or join); list endpoints paginated and bounded, never an unbounded `SELECT`; slow-query logging on.
- **Plans**: capture `EXPLAIN ANALYZE` before the fix as the baseline; a sequential scan on a large table is understood (missing or unusable index, or not worth it); estimated and actual rows within an order of magnitude, else refresh statistics before touching indexes; a `Sort` a composite index could absorb; re-check after the change and revert an index that did not change the plan.
- **Indexes**: composite order is equality columns first, then range or sort; cover the filter and sort together; consider a covering index on hot reads; a partial index for a rare value; an expression index where the query applies a function; full-text or trigram for leading-wildcard search; measure write cost on write-heavy tables; drop unused and duplicate indexes.
- **Pools**: one pool per process; instances times pool size stays under the database connection limit; a connection timeout so exhaustion fails fast; find what holds connections (long transactions, a missing `await`, a leaked client) before resizing; a multiplexing proxy for serverless.
- **API**: latency within the `web_perf` API band; no heavy synchronous work in a handler; bulk operations instead of call loops; response compression; a CDN for static assets; a health-check endpoint.

## Caching
- Measure the call as expensive first; the read-to-write ratio justifies a cache.
- Pattern by need: cache-aside as the default; read-through to keep the load path in one place; write-through when a read must never see a stale write; write-behind only for write-heavy origins with a defended durability story.
- The key holds every input the response varies on (tenant, viewer, locale, permissions, flags); per-user data never sits under a key that does not identify the user.
- One invalidation strategy (TTL, event or tag, versioned keys), the staleness window written down, an eviction policy and a memory ceiling.
- Stampede protection on hot keys: coalesce in-flight loads, or `stale-while-revalidate`; negative results cached with a shorter TTL, origin errors never cached.
- Hit rate monitored; nothing cached whose staleness is a correctness bug (balances, permissions, stock at checkout).

## Anti-patterns to flag
N+1 queries, unbounded queries, missing or unread-plan indexes, a pool per request, a cache key missing the viewer, an unbounded cache, layout thrashing, unoptimised images, large bundles, a blocked main thread, leaked listeners, intervals and refs.
