# security audit
<Owner: skills/review-checklist/SKILL.md>
<Read when: the reviewer audits a security-relevant diff and needs the method for hunting, gating and recording a candidate; severity is not here>

---

Read with `skills/review-checklist/references/security.md`. This file is the method only: the four severity tags (`agents/reviewer.md` § Severity) and the cap on an unconfirmed candidate (`refs/roles/reviewer/finding-bar.md`) rule every candidate below. Everything here is read-only work on source; a check that needs a running target, a network or a tool the reviewer lacks becomes a candidate that needs validation, with the blocker named.

## Scope

- Review the changed code and the paths its guarantees depend on; a boundary met on the way that the diff does not touch is written as "not covered", never chased.
- A narrow review says it is partial coverage; it never implies the rest of the repository is clean.
- Deployment facts (proxy, identity provider, browser headers, broker rules, packaging) are real controls. Missing from the repo, they are neither assumed present nor absent: record the exact missing fact and who can observe it.

## Core principles

- Name a boundary and a result for every candidate: the lower-trust actor, the value or action it controls, the control that should stop it, the boundary crossed, and the resource or person affected. A missing best practice, a guessed deployment behaviour, a generic crash or harm to the actor itself is hardening at most.
- Static reading settles the source path. A claim that needs more than reading is `needs_validation`, not a stronger claim than the evidence shows.
- State only the impact the evidence shows; never present a crash as code execution, ordinary load as shared unavailability, or an action within the actor's own authority as privilege gain.
- Every confirmed finding names the invariant the code must hold and the narrowest change that holds it at the last trusted decision point; the review describes the change and never makes it.

## Hunting method

1. Follow each input through parsing, identity, authorization, normalization, stored state, derived copies and the final sink.
2. Read the sibling paths that produce the same effect (legacy, batch, retry, cancel, migrate, error) and compare their controls for equivalence, not only presence.
3. Compare what one component guarantees with what the next one assumes: truncation, type coercion, normalization, tenant scope, units.
4. Work from one concrete invariant at a time (the steps of `skills/review-checklist/references/security.md` § Method); stop a branch once the invariant is settled either way.
5. Try the sad paths where the interface accepts them: absent, empty, zero, negative, maximum, duplicate, mixed encoding, stale, revoked, reordered, concurrent, half-migrated, failed dependency, rolled back.
6. After a serious candidate, search the same root cause in its lexical, structural and logical variants; merge the same root cause into one record, and establish each variant's conditions and impact on its own.
7. In a chain, each step's output is a prerequisite: one not established is a blocker, never assumed.
8. Data safe when stored can be dangerous when used later (a field name used as a path, a slug as a file, a stored string as a URL, pattern or template): follow it to its second use.

## Candidate gate

A candidate is kept only when all hold:

1. A complete source trace with `file:line`, including the strongest control visible on the path.
2. For a confirmed claim: an observed or read result, a meaningful impact across the stated boundary, complete conditions and no visible layer that prevents it.
3. A fact outside the source that decides the outcome makes it `needs_validation`: name the exact blocker and a non-destructive check its owner can run. A candidate the source disproves is rejected, not parked there.
4. The same root cause keeps one stable fingerprint in every state (no line number, no agent, no verdict in it).
5. Nothing surviving the gate is a valid result: report it, never pad.

Severity is read from `skills/review-checklist/references/security.md` § What is a finding and `refs/roles/reviewer/finding-bar.md`; this method adds none.

## Verification pass

A second reader, who did not hunt the candidate, runs `skills/review-checklist/references/security.md` § Verify independently on every kept candidate before it is reported. The pass also checks that the stated fix enforces the invariant and does not merely move the trust.

## Finding record

- Kept candidate: title; fingerprint; state (confirmed, needs validation, rejected); lower-trust actor; intended behaviour; the root cause with `file:line`; conditions; the observed or read result; the impact; the fix and the regression case that would catch it.
- Needs validation: the same, with the unresolved fact, who can observe it and the non-destructive check, in place of the result.
- Rejected: the claim and the source evidence that refutes it, so it is not reopened without new evidence.
- Prose and any machine record agree; the review is written after the verification pass, never before.

## Smallest fix

- Name the invariant, the last trusted decision point and the narrowest change there, with a repository-relative path and a regression test.
- Prefer one enforcement at the shared point over a patch per caller.
- A fix that disables the control, widens trust or adds generic hardening with no path is not a fix.

## Attack classes

Pick the classes the diff can reach and split large diffs per subsystem. Ordinary classes, each a question about the path:

- **Injection**: trace untrusted input to every dangerous sink (query, shell, markup, template, path, redirect, deserializer, log, secondary store), including keys, field names and headers, and data stored first then used elsewhere.
- **Access control**: the right permission for the right resource by the right mechanism; a weaker path to the same state change; a body field that overrides a restriction; bulk, export and import paths that skip the per-item check.
- **Resource and file handling**: traversal through links, encodings and null bytes; SSRF through redirects and resolver tricks; unsafe archive extraction; temp files; check-then-use races.
- **Cryptography and secrets**: weak randomness, hardcoded or logged secrets, missing integrity checks, reused nonces, secret comparison timing, an error path that falls back to no crypto.
- **Business logic**: skipped or replayed steps, partial failure with no rollback, non-atomic check-then-act, negative or overflowing quantities, expiry edges, the posture when config is missing or a dependency is down.
- **Feature abuse and leakage**: export or backup above the caller's access, import that bypasses validation, search and sort as an existence oracle, differing errors for "missing" and "forbidden", preview or draft leakage, a user-set callback URL fetched by the server.
- **Chained trust**: scope growth after delegation, refresh or role change; stale state after revoke; undelete, restore and rollback skipping current authorization.
- **Wildcard**: the half-finished, experimental or fallback code, the API call the client never makes, mixed features, history with a reverted fix, what the tests leave unchecked.
- **Obvious things**: checked literally, one by one, as `security.md` § Commonly missed lists them, with the full path verified before any is reported.

Target types route to a domain file, read only for the matching diff:

| Diff touches | Read |
|---|---|
| model, prompt, tool-calling agent, MCP | `skills/review-checklist/references/security-domain-ai-llm.md` |
| shared CPU, memory, queue, quota, spend | `skills/review-checklist/references/security-domain-availability.md` |
| browser code, extension, storage, CORS, cross-window messages | `skills/review-checklist/references/security-domain-client-side.md` |
| IAM, infrastructure as code, containers, ingress | `skills/review-checklist/references/security-domain-cloud.md` |
| tenant stores, cache, export, backup, deletion, restore | `skills/review-checklist/references/security-domain-data-lifecycle.md` |
| native app, deep link, webview bridge, local daemon, IPC | `skills/review-checklist/references/security-domain-desktop-mobile.md` |
| native or unsafe code, parsers, FFI, binary loaders | `skills/review-checklist/references/security-domain-memory-binary.md` |
| gRPC, GraphQL transport, queue, broker, webhook, custom protocol | `skills/review-checklist/references/security-domain-protocols.md` |
| dependency resolution, CI, signing, updates, plugins | `skills/review-checklist/references/security-domain-supply-chain.md` |
| HTTP, sessions, CSRF, JWT, OAuth, SAML, MFA, account recovery | `skills/review-checklist/references/security-domain-web-auth.md` |

## Anti-patterns

1. A checklist deviation presented as a vulnerability.
2. Defense-in-depth advice with no reachable boundary violation.
3. A guess about provider, proxy, browser, identity or deployment behaviour that the source does not show.
4. Same-actor authority or self-harm treated as a cross-boundary result.
5. A runtime effect reported stronger than the one observed.
6. A candidate written as loose prose that cannot be deduplicated or verified.
7. Re-reporting an unchanged confirmed finding from an earlier review as new, or letting it anchor the hunt.
8. A severity given by the reviewer's feeling rather than by `security.md` and `finding-bar.md`.
