# security

Per-surface checks: `skills/review-checklist/references/security-surfaces.md`, for the surfaces the diff touches. Severity stays the four tags (`agents/reviewer.md` § Severity); this content adds to them. Depth by topic: `skills/review-checklist/references/security-depth.md`; method for an audit of a diff: `skills/review-checklist/references/security-audit.md`.

## Two ways to run

- **Guidance** (Q&A, a focused review): only the relevant part; no file.
- **Full audit**: only when the user says so or asks for a report; ambiguous: ask one question first. Loading this file does not authorize it or file creation.

## Automatic trigger (the one home of the pattern list)

A change gets the security review automatically when, case-insensitive, either list matches:

- Changed paths: `auth|login|logout|session|token|oauth|sso|password|credential|secret|permission|role|acl|payment|billing|invoice|checkout|stripe|paypal|wallet|refund|pii|gdpr|\.env`
- Diff text: `jwt|bcrypt|argon2|scrypt|hmac|api[_-]?key|private[_-]?key|card[_-]?number|iban|ssn|passport|set-cookie|csrf`

A match adds `reviewer mode=security`; a miss changes nothing. Fail-open: when the match itself errors, the security review runs.

## Depth and order

- Depth: `full` for auth, login and payments; `standard` for APIs and UI; `lightweight` for config and docs.
- Grep secrets, PII, SQLi and XSS BEFORE semantic search.
- Mobile vectors (when platforms detected): keychain/keystore, certificate pinning, jailbreak/root detection, deep-link validation, secure storage (no tokens in AsyncStorage), biometric auth, network security config (no `NSAllowsArbitraryLoads` / `usesCleartextTraffic` in prod), HTTPS-only.
- Threat model first: trust boundaries, assets to protect, STRIDE per boundary, abuse cases written beside use cases.

## What is a finding

- Report only a vulnerability that breaks a real trust boundary, with an affected actor and a concrete resource. A missing header, cookie flag, MFA or rate limit alone is not a finding (it needs an accepted bad request, cross-actor impact, authentication downgrade or credential exposure); self-harm is not a broken boundary.
- Each finding carries: what the changed code stores, what it protects, what it exposes, and the attacker's path; a trace from a low-privilege entry point to the harm, and the controls on the path (validation, authorization, normalization, lifecycle); evidence from source; a safe way to reproduce; a priority; and the smallest fix that is enough.
- Severity goes only to a confirmed finding, never above the impact proven. Secrets, PII and OWASP-critical stay 🔴 `critical`, never lowered; a finding with no reachable path keeps its severity and says so. A needs-more-validation candidate carries a severity capped at 🟡 minor (`refs/roles/reviewer/finding-bar.md`), and says where it is blocked and a non-destructive way to check. A rejected candidate is still recorded.
- Prompt injection alone is not a finding: it needs a boundary bug in code (authority, a trusted output, durable state, a sink).
- Never propose disabling a security control as the fix; name the narrower change that keeps it (addy security-auditor.md:57-65).

## Safe execution

- Read source read-only. Run the target's build or tests only in a sandbox: no outside network, an empty environment holding only allowed variables, a read-only target, CPU, memory and time limits, fake data and fake secrets.
- Never probe a live endpoint, an external service, shared infrastructure, a production identity or anyone else's data; never load-test a real process.
- Record the repro command, exact input and sandbox limits; never copy ambient environment, inherited variables or credentials into a result.
- Deployment config (proxy, identity provider, headers, broker ACLs, post-packaging manifest) is a real control: needed but not in the repo, do not guess; record the exact missing fact and how its owner can observe it.

## Verify independently

The reviewer runs its own refute-first pass: before filing a security candidate it re-reads the cited source from the entry point in a separate pass, tries to disprove it, then concludes confirmed, needs more validation, or rejected. A confirmed or needs-validation candidate that is not a secret or PII finding may also get a Codex second opinion: the reviewer returns `codex_second_opinion[]` (claim and `file:line` only), main thread spawns one `codex:codex-rescue` when Codex is ready, and the same reviewer is re-spawned with `codex_opinions[]`, re-reads the cited lines and merges. Codex never confirms alone and never raises a severity; when Codex is unavailable or its permission prompt is declined, the refute pass stands and `handoff.risks` says "Codex second opinion not run: <reason>" (user, 2026-11-05, Q-R7-C11).

## Full audit bookkeeping

- Keep a coverage ledger: what was viewed, what skipped, why. Prioritise unauthenticated surfaces and the places guarding the most valuable asset. Out of effort: mark "deferred" with the reason, never skip silently.
- A rerun carries old confirmations only when the relevant source is unchanged. A narrow run says it is partial coverage.

## Method

State a concrete invariant (untrusted subject, accepted value, the control that should stop it, the path after, smallest effect, fix plus regression test); stop a branch once settled. Try the sad paths: empty, 0, negative, maximum, duplicate, stale, revoked, out of order, concurrent. Look for variants with the same root cause. Another boundary seen: write "not covered" instead of spreading.

## Commonly missed

IDOR (one user reads another's resource) · SSRF (the server fetches a user-given URL) · webhook signatures · OAuth without PKCE/state · session cookie httpOnly/secure/sameSite · login rate limit · generic errors that leak no stack. Check literally: hardcoded passwords or keys, debug mode on in production, a sample account that works in production, unprotected `/debug` management-console routes `/health` `/metrics` `/env`, `.env` or `*.pem` in the repo and whether `.gitignore` covers secrets, pinned dependencies and CVEs, `eval`/`exec` on dynamic input, security `TODO`s, open redirects, stack traces returned.

Beyond the catalog: read the part that looks boring or half-finished, an API route the UI never calls, features that mix, git history with a security fix reverted, and tests that check NOTHING.
