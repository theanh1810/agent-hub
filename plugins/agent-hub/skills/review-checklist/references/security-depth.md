# security depth
<Owner: skills/review-checklist/SKILL.md>
<Read when: a diff touches a security class `security.md` and `security-surfaces.md` do not spell out: headers, CORS, uploads, rate limits, privacy, dependencies, a leaked secret, or the OWASP lists>

---

Read with `skills/review-checklist/references/security.md`; a finding still needs the trust boundary, the actor and the resource it names. Every number below is a pointer: read it from the project's `docs/thresholds.yaml`, else `templates/thresholds/thresholds.yaml` (`refs/thresholds.md`); a number over an unapproved group is advisory, never failing. Sources: addy security-checklist.md:21-248, security-and-hardening SKILL.md:21-216, hardening-patterns.md:7-324, security-auditor.md:10-106.

## Threat model first

- Map the trust boundaries (requests, uploads, webhooks, third-party APIs, model output, local values a foreign process can write) and the assets (credentials, PII, payment data, admin actions, money movement). <!-- scrub-allow: generic security term, not a personal name -->
- Run STRIDE per boundary: spoofing, tampering, repudiation, information disclosure, denial of service, elevation of privilege. Write the abuse case beside the use case.

## Authentication and sessions

- Passwords hashed with bcrypt, scrypt or argon2; the bcrypt cost floor is `security_auth.bcrypt_cost_min`.
- Login rate limit `security_auth.login_attempts_max`; reset-token lifetime `security_auth.reset_token_lifetime_max`, single use.
- Session cookie `httpOnly`, `secure`, `sameSite`; a session expiry set; a JWT validated for signature, expiry and issuer; an API key scoped to the least it needs.
- Account lockout and MFA for sensitive operations are recommendations, not findings alone.

## Authorization

- Every protected endpoint checks authentication; every resource access checks ownership or role (the IDOR check), an admin endpoint checks the admin role. <!-- scrub-allow: generic security term, not a personal name -->

## Input and uploads

- Validate with an allowlist and a schema at the boundary: lengths, ranges, formats; a parameterized query; framework output encoding; a redirect target checked against an allowlist.
- Upload: restrict the type by content (magic bytes, not the extension), limit the size, store outside the web root; never trust a client-sent MIME type.
- SSRF: a server-side fetch of a user-given URL uses an allowlist and blocks private and reserved addresses, after DNS resolution.
- A destructive operation on a derived path (delete, move, overwrite): resolve symlinks first, compare against an allowlisted root, require a depth below it, read the ownership evidence. A marker file in the tree is self-attestation; the expected owner must come from authenticated state, and returning a path still leaves a check-then-use race an untrusted process can win.

## Headers and CORS

- Expect a content security policy, `Strict-Transport-Security` with `includeSubDomains` and at least `security_headers.hsts_max_age`, `X-Content-Type-Options: nosniff`, a framing denial, a referrer policy and a restrictive permissions policy; the legacy XSS filter header off.
- CORS: an explicit origin list from configuration; a wildcard origin, alone or with credentials, is a finding on an authenticated API.
- Fix what the header blocks and keep the header on; disabling it "for convenience" is never the fix (`security.md`, never disable a control).

## Errors, logs and rate limits

- A production error body is generic: no stack, query or internal message. Mask or drop sensitive fields; they never appear in a response or a log.
- A general API rate limit and a stricter one on auth. Counters held in process memory are per instance; behind more than one process the limit needs a shared store.

## Privacy

- Personal data is classified when the field is added (non-personal, personal, sensitive: health, finance, location, biometrics, government ID, minors), collected for a stated purpose and minimised.
- A retention limit and a working deletion path reaching backups, caches and indexes; export and delete requests supported where the law requires; third-party sharing with consent and a processing agreement.

## Secrets

- `.env`, `.env.local`, keys and certificates ignored by git; `.env.example` holds placeholders only; grep the staged diff before commit.
- A secret that reached a remote is compromised: rotate (revoke and reissue) first, then purge history. Deleting the line or rewriting history alone is not a fix.

## Dependencies and supply chain

- Locate the installation boundary first (the workspace root, else the nearest project owning manifest and dependency graph); the lockfile, the package manager and CI must agree there, and one authoritative lockfile is committed and never rewritten by CI.
- Audit triage by reachability across runtime, build, test and deploy paths: critical or high and reachable is fixed now; unreachable or dev-only is tracked; a deferral carries a reason and a review date. Forced remediation (`npm audit fix --force` or an equivalent) is never automatic: preview, read changelogs, test each upgrade.
- Lifecycle scripts: never discover them by running an ordinary install first. Bootstrap with scripts disabled or a documented default-deny policy, inspect the script source and package version, approve the narrowest set, commit the policy, then run a clean frozen install. Package-manager defaults change: verify against the pinned client's current documentation.
- A new dependency is reviewed for ownership, maintenance, release age, provenance, transitive graph and typosquatting. A lockfile diff is read, never hand-edited. Upgrades go one dependency at a time, changelog read, suite green before and after.
- A command that contacts a registry is a `devops` step with approval, never one the reviewer runs itself.

## OWASP Top 10

| Class | What to look for in a diff |
|---|---|
| Broken access control (IDOR, SSRF share it) | a route without an ownership or role check; a fetch of a user-given URL |
| Cryptographic failures | plain HTTP, weak hashing, a secret in code |
| Injection | a query, shell or template built from input |
| Insecure design | no threat model; a boundary assumed trusted |
| Security misconfiguration | a missing header, a broad permission, a default credential |
| Vulnerable components | an unaudited or unpinned dependency |
| Authentication failures | no rate limit, weak session handling |
| Data integrity failures | an unverified update, dependency or artifact |
| Logging failures | a security event unlogged, a secret logged |
| SSRF | see above: allowlist and private-address block |

## OWASP Top 10 for LLM applications

| ID | Check |
|---|---|
| LLM01 prompt injection | permissions enforced in code, the system prompt is not a boundary |
| LLM02 sensitive disclosure | secrets and PII kept out of prompts; outputs filtered |
| LLM03 supply chain | models, datasets and plugins vetted like dependencies |
| LLM04 data and model poisoning | trusted sources, integrity checked, fine-tuning and RAG data vetted |
| LLM05 improper output handling | model output validated, parameterized, encoded before any sink |
| LLM06 excessive agency | tool scope bounded; destructive actions confirmed |
| LLM07 system prompt leakage | no secret in the prompt |
| LLM08 vector and embedding weakness | RAG embeddings partitioned per tenant; documents validated before indexing |
| LLM09 misinformation | grounded answers with citations; a human on critical claims |
| LLM10 unbounded consumption | token, request and recursion limits |
