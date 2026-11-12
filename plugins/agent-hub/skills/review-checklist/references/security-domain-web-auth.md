# security domain web auth
<Owner: skills/review-checklist/SKILL.md>
<Read when: a diff touches HTTP parsing, caching, cookies on a shared domain, SAML, step-up or passkey flows, or client-certificate identity>

---

Read after `skills/review-checklist/references/security-surfaces.md`, which already covers credential lifecycle, token verification, session and CSRF rules, OAuth and OIDC binding, recovery and linking, and API keys; the base checks of `skills/review-checklist/references/security-depth.md` apply unchanged. Order of concern: `refs/roles/reviewer/finding-bar.md` § Confidence and severity, through `skills/review-checklist/references/security.md` § What is a finding driving what qualifies, and this file adds none. Below are only the classes those files lack.

## When to use

The target parses HTTP itself, sits behind a proxy or cache, or implements SAML, step-up authentication, passkeys or client certificates. Ask whether the HTTP or identity layer can confuse which principal, request, assurance level or token an operation belongs to. Split a large target into framing and cache policy, browser authentication, federated identity, strong authentication, service credentials and session lifecycle. A service behind a managed proxy the repository does not show has little framing surface to confirm.

## Core discipline

- A framing or cache candidate needs two interpretations of the same request, response or key: name both components and the normalized value each one sees.
- A credential is complete only when its verification covers every binding its role needs: issuer, audience, origin, relying party, client, session, principal, resource, assurance, expiry and one-time state.
- A missing header, cookie flag, MFA prompt or rate limit is not a finding alone; it needs an accepted invalid request, a cross-principal effect, an assurance downgrade or a disclosed credential.
- A proxy chain, identity-provider policy, certificate trust or deployed auth mode the repository does not show is `needs_validation` with the missing fact named.

## HTTP framing and cache classes

- **Request desynchronization**: two hops disagree where one request ends. Read repeated length headers, transfer-coding handling, downgrade from a newer HTTP version, header-name normalization and CR/LF conversion; state which bytes each hop assigns to which request.
- **Cache poisoning by an unkeyed input**: a value that changes the cached body or a security header is missing from the cache key. Compare key construction with every response variant: forwarded host or scheme, chosen cookies, query normalization, language and device headers, authorization state.
- **Cache deception**: the edge treats a private dynamic path as a public static asset, or stores a response whose identity inputs are absent from policy. Compare edge cacheability with how the application parses suffixes and path parameters, and with the response's cache directives.
- **Response-header injection**: untrusted data reaches `Location`, `Set-Cookie` or a policy header with control characters or odd normalization. Check whether the framework already rejects it, and require a security-relevant change in the response.

## Cookie scope classes

- **Cookie scope and transport**: a sensitive cookie with an over-wide `Domain` or `Path`, an insecure transport leg, or a sibling cookie that another component picks first. A bare missing flag is a hardening note unless a less-trusted origin, network position or browser path can set or replace the credential.

## Federated identity classes

Settle the component's role first: redirect allowlisting and code issuance belong to the authorization server, not to a relying-party client; verification and binding defects belong to whoever consumes the artifact.

- **SAML signed-object binding**: the element whose signature was checked must be the element used for identity. Read unsigned fallback paths, XML parser configuration, canonicalization differences, validity windows, audience and recipient, request correlation and replay state.

## MFA, passkey and account-transition classes

- **Assurance downgrade at enrollment**: enrolling, replacing or disabling a factor, creating recovery codes or a trusted device, and fallback login each need the intended prior assurance; a valid first factor alone must not replace the second, and a disabled or stale factor must stop authorizing sessions.
- **Step-up binding**: a passed challenge raises the wrong session, account, tenant, action or request, or another route skips the assurance check. Bind the challenge to principal, session, target assurance, operation, expiry and one-time use, and compare UI, API, batch, recovery and resumed paths.
- **Passkey verification**: at registration bind challenge, relying-party ID, expected origin, credential, user handle, algorithm and required user verification to the initiating session; at login verify challenge, origin, credential membership and signature. Look for confusion between user handle and credential-to-account mapping. A signature-counter regression matters only if the product treats it as a clone signal.
- **Identity collision on linking**: adding a provider, passkey, email, phone or device needs a current session, proof of the new identity, any required step-up and callback state tied to the initiating account. Read unlink, relink and invite acceptance for verified-identifier and tenant collisions.

## Client-certificate classes

- **Peer and application identity confusion**: a process trusts certificate identity headers from any network peer, maps attacker-influenced subject text to an account, or accepts a certificate for the wrong trust domain, key usage, audience or validity policy. Behind a proxy that terminates the tunnel, confirm only that proxy can connect, that it strips incoming identity headers, and that the backend binds the cleaned identity.
- **Certificate lifecycle fallback**: an expired, revoked or failed-renewal certificate silently drops to bearer-only or anonymous operation, or pooled long-lived connections keep authorization after revocation. A fail-open branch in the repository is confirmable from source; revocation data held elsewhere is `needs_validation`.

## Universal moves

- Diff parser, proxy, router, cache and application normalization side by side, feeding identical bounded request fixtures to each in-repository component; sending traffic to a running deployment is outside review, so a check that needs one is `needs_validation` naming the local check `test mode=script` would run.
- For recovery and linking, draw the account before and after as a graph; every edge names the current principal, the proof of the new identity, the assurance required, the callback or session binding and the revocation effect.

## Validation rules

1. Framing and cache candidates name both components and the divergent parse or key, then show cross-request, cross-user or private-response impact from local fixtures.
2. Token, MFA, passkey, linking, recovery, key and certificate candidates cite the verification line and the missing binding, and show the server accepting the invalid credential or transition.
3. A CSRF-style candidate in this file names the ambient credential, the mutating route, the accepted cross-site request and the cookie policy; read-only actions and routes needing a non-ambient bearer token do not qualify.
4. Library defaults are verified at the pinned version; unknown version or configuration is `needs_validation`, never a lower-severity confirmed finding.
5. `confirmed` needs a full source trace and an observable unauthorized identity, state change or disclosure; `needs_validation` names the missing fact and the safe local or owner-run check.
