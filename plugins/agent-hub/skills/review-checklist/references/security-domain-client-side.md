# security domain client side
<Owner: skills/review-checklist/SKILL.md>
<Read when: a diff touches browser code, an extension, a webview page, a service worker, cross-window messages or client-side storage>

---

Browser surfaces that `skills/review-checklist/references/security-surfaces.md` already lists (message origin checks, upgrade origin checks, credentialed cross-origin trust, worker cache per account, storage after logout, anti-framing, redirect schemes) are not repeated here; base checks sit in `skills/review-checklist/references/security-depth.md`. Grading: `refs/roles/reviewer/finding-bar.md` § Confidence and severity, under `skills/review-checklist/references/security.md` § What is a finding settling what qualifies, and this file adds none. For the native half of a webview bridge read `skills/review-checklist/references/security-domain-desktop-mobile.md`; for server-side session and callback rules read `skills/review-checklist/references/security-domain-web-auth.md`.

## When to use

Trust decisions or untrusted rendering happen in the browser: single-page apps, extensions, embedded webviews, service workers and offline apps. Some sources never reach the server: the URL fragment, `window.name`, cross-window messages and earlier cached content.

## Core discipline

- A candidate needs a controllable source and an executing or disclosing sink; name both and show attacker-influenced data reaching the sink.
- The effect must reach a victim's session, another origin or shared persistence; injecting into oneself, or disclosing the attacker's own data, is not a finding.
- Framework escaping, same-origin policy, page policy headers, worker scope and opener isolation defaults are real controls; verify them before assigning impact.
- Browser storage is shared by origin and can persist past a login: name who writes, who reads and which account, tenant or worker lifecycle clears each record.
- Renderer, extension permission, deployed header or browser-version behavior the repository does not show is `needs_validation`.

## DOM and object-state classes

- **DOM-based script injection**: follow location fields, referrer, `window.name`, message data, storage and document state into HTML-writing or string-evaluating sinks, executable URLs, jQuery HTML helpers and framework escape hatches. Interpolation the framework escapes is not a finding.
- **DOM clobbering**: injected `id` or `name` attributes shadow a global, form property, configuration object or initialization flag the code later trusts. Needs both a markup path that keeps the attribute and a security-relevant use of the shadowed value.
- **Prototype pollution with a gadget**: an attacker-chosen key reaches a recursive write (deep merge, path assignment) and alters prototype state, and a reachable gadget then reads the polluted property to change authorization, execution, navigation or rendering. Plain parsing, a shallow copy, or pollution with no gadget is not enough.

## Messaging and network classes

- **Send-side message leakage**: sensitive data posted with a wildcard target origin reaches an unintended embedder; where several frames share an origin, receivers also check the expected source window, not only the origin.

## Service-worker and storage classes

- **Worker registration and scope takeover**: attacker-influenced content becomes the registered script, a path gets an over-wide allowed scope, or imports change on update with no integrity control. Check final script URL, MIME type, origin, scope and who controls every imported script; an ordinary same-origin worker with its intended scope is not a defect.
- **Worker cache keyed without identity**: personalized responses cached with no account, tenant, authorization state or request mode in the key, then served after a switch or logout. Read fetch routing, cache names, navigation fallbacks, cleanup, and whether offline or error paths return another user's earlier response.
- **Stale authorization in storage**: tokens, private responses, drafts or decisions left in any browser store become readable by another account or a less-trusted same-origin component, or keep working after revocation. A token merely being stored is not a finding; name a realistic reader with less authority.
- **Cross-context broadcast confusion**: storage events, broadcast channels and shared workers carry identity or commands between tabs with no binding to the current session. Check account switch, private versus public windows, tenant change, and stale tabs overwriting newer auth state.

## Cross-site leak classes

- **State oracles**: an attacker page tells protected cross-origin state apart through load or error events, frame state, redirect behavior, timing, cache state or response size while the browser attaches the victim's credentials. Needs one concrete secret-bearing predicate, such as whether a private object, role or account exists; generic timing variance or public availability is not a finding.
- **Window and opener disclosure**: a cross-origin window's permitted metadata or navigation result reveals protected state, or a retained opener or named window lets an attacker page steer a privileged navigation. Check opener isolation policy, frame protection, exact origin and whether the observable state is confidential.

## UI-redress and navigation classes

- **Navigation confusion by a client source**: a client-controlled redirect with no scheme and destination policy. Reverse tabnabbing applies only where code explicitly keeps the opener, opens windows without isolation, or supports a browser lacking the implicit default.

## Universal moves

- Start at the sinks (DOM writes, navigation, workers, message handlers, storage) and trace backward to browser-only and server-controlled sources; record the browser policy that should stop each path.
- Account switch, logout, worker update, offline fallback and stale-tab behavior need a browser run against a local test origin with dummy accounts; a reviewer without one marks the candidate `needs_validation` and names that local run, never production users or shared origins.
- For state oracles list only predicates proved by source and local behavior, then name the response header or rendering change that removes the oracle.

## Validation rules

1. Cite source, sink, browser policy, affected origin or session, and the observable mutation or disclosure.
2. Pollution needs the recursive write plus a security-relevant gadget; clobbering needs surviving markup plus use of the shadowed value.
3. Worker and storage candidates prove lifecycle reachability: an attacker-controlled write or cache entry must reach a different account, tenant or later authorization state.
4. Messaging and cross-site candidates show the exact origin or source validation and the protected state exposed, and confirm that page policy, opener isolation and cookie policy do not already block it.
5. `confirmed` needs a full client path and bounded local evidence; `needs_validation` names the deployed header, extension permission, browser version or renderer behavior an owner must check.
