# security surfaces

Read with `skills/review-checklist/references/security.md`, for the surfaces the diff touches. Each bullet is a check, not a verdict; a finding still needs the bar of security.md.

## Identity and credentials

- **Credential lifecycle**: walk issue, store, send, use, refresh, revoke, against the normal path, error, retry, stale and account switch. List every entry point to one identity and every path to the same sensitive operation (UI, API, batch, recovery, resume): the effective policy is the weakest parallel path.
- **Tokens**: verify signature, then the server-pinned algorithm, issuer, audience, expiry. A token valid for another service is rejected. `kid` / `jku` / `x5u` are untrusted key selectors.
- **Session and CSRF**: every state-changing action on a cookie needs a token or an Origin check. Rotate the session on login, permission change and MFA completion. Sessions and refresh tokens die on logout, password change and revocation.
- **OAuth/OIDC**: `state` bound to the session, PKCE, nonce, binding to the chosen IdP; compare the first-callback path, retry, deep link and account linking.
- **Recovery and account linking** are often the weakest channel: random token bound to person and action, expiring, single-use, cancelling old tokens and sessions. Linking needs the current session and proof of owning the new identity. Enrolling, replacing or disabling an MFA factor needs recent authentication.
- **API keys**: scope and environment match the server record and request parameters cannot override them; tell public keys from secret ones; never in a URL, bundle or log.

## Data and tenants

- **Isolation**: a tenant field on a record is not isolation. Check every read and write path (list, count, bulk, background job, import, admin, legacy); cache keys, file paths and unique keys missing the tenant; a signed URL bound to operation, object, audience and expiry. <!-- scrub-allow: generic security term, not a personal name -->
- **Derived copies** (search, cache, analytics, log, export, backup, preview) can drift from the original's ACL and retention. Soft delete and revocation must reach sessions, caches, jobs and indexes; restore must not bring old permission back; a backfill migration must not default tenant or ACL.
- **Export, backup, import, search**: an export may hold data above the requester's rights (others', soft-deleted, secret); import and restore must not bypass authentication; search, filter, sort, errors and timing can reveal existence; a draft can leak via search, RSS or sitemap.
- Host, `X-Forwarded-*`, `Origin`, `Referer` and a redirect target are trust decisions: who can send them, does the proxy strip the client's copy; a cache key missing an input, or a private page cached as static.

## Client surfaces

- **Browser**: needs a controllable source and an executing sink. `postMessage` checks the exact origin, not a substring; WebSocket upgrade checks Origin; CORS reflecting an origin with credentials; a service-worker cache not tied to an account; browser storage surviving logout or account switch; a state-changing action in a frame needs anti-clickjacking; a redirect target blocks `javascript:` / `data:`.
- **Mobile**: a deep link or callback bound to the current session and single-use; a webview bridge checks origin at call time and after every navigation, with an allowed-method list; an exported component checked on the merged manifest; data surviving logout, profile switch or device restore; a pending action displays exactly what it will do.

## Messaging, load and logic

- **Messages and RPC**: "internal" is not authentication; envelope and body identity must match; the auth gate covers streams, health and transition paths; duplicate, out-of-order, ack-before-commit; a dead-letter queue exposing data; a message claiming to be an admin event needs a source signature. <!-- scrub-allow: generic security term, not a personal name -->
- **Resource exhaustion**: table input to resource (earliest limit, work before authentication, fan-out, shared memory, who cleans up). Limits accumulate, not only per item; cancellation must propagate to every layer; retries use jitter and a cap; a poison record blocking the head of a queue; backtracking regex, decompression bombs.
- **Business logic**: skipping a step, going backward, replaying a finished flow; a mid-flow failure that does not undo the earlier step; two concurrent operations (double spend, double approve); negative, zero, overflow, type coercion; timestamps and timezone drift; the safe posture when config is missing, a flag is off, a dependency is dead, or mid-migration.

## AI and LLM features

- Model output never reaches `eval`, SQL, shell, `innerHTML` or a file path. A system prompt is not a security boundary. Tool permissions are bounded and destructive actions need confirmation; token and recursion caps exist.
- Content person A writes (a RAG document, issue, email) into person B's context is an indirect-injection path; long-term memory written from low-trust content is poisoned; tool descriptions and MCP metadata never grant permission; a sub-agent gets minimum permission.
- **Approval** binds to the normalized tool name, all parameters, the requester, the destination and an expiry. A retry or session resume must not grant a changed or duplicated action. The tool re-checks the requester's permission on the exact resource instead of using a broad service credential. A schema with the right shape is not authorization. A loop of authorized actions needs a per-request budget, cancellation and idempotency.
