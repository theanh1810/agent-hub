# security domain cloud
<Owner: skills/review-checklist/SKILL.md>
<Read when: a diff touches cloud identity, infrastructure as code, containers, orchestration manifests, ingress, serverless or edge code, object storage or per-environment configuration>

---

Identity, tenant and secret-handling basics sit in `skills/review-checklist/references/security-surfaces.md` and `skills/review-checklist/references/security-depth.md`; this file adds the deployment layer. Priority: `refs/roles/reviewer/finding-bar.md` § Confidence and severity, from `skills/review-checklist/references/security.md` § What is a finding setting what qualifies, and this file adds none. Neighbouring domains: `skills/review-checklist/references/security-domain-supply-chain.md` (build and promotion), `skills/review-checklist/references/security-domain-web-auth.md` (proxy semantics) and `skills/review-checklist/references/security-domain-data-lifecycle.md` (tenant scope in stores).

## When to use

The repository defines cloud identity, infrastructure, containers, Kubernetes, a service mesh, serverless functions, edge workers, ingress, object storage, managed services or per-environment configuration. The question is whether each deployed component gets the intended identity, isolation, reachability, secrets and policy. Source states intent, not observed fact, so keep source-confirmed defects apart from deployment checks.

## Core discipline

- A manifest alone does not prove exposure: establish which environment consumes it, what defaults or overlays alter it and whether that path is active.
- Map each workload identity to specific operations and resources; broad policy is a finding only when lower-trust input can reach an unauthorized action.
- Ingress, proxies, mesh, metadata services and admission policy are real boundaries, but a control counts only when its configuration and attachment are visible.
- A reference to a secret is not disclosure; require a lower-trust reader, output, artifact, log path or unsafe fallback.
- Account policy, network attachment, runtime admission, hosted metadata and drift that need an owner's observation are `needs_validation`.

## Workload identity classes

- **Identity overreach**: a workload, pod, function, edge worker or node identity can act on tenants, accounts, resources or APIs beyond its role, and request or job input picks the target. Read policy conditions, resource patterns, service-account attachment, namespace mapping and fallback credentials.
- **Cross-account or cross-tenant role confusion**: role assumption, external IDs, token exchange, workload federation or resource policies accept identity claims not bound to the intended source account, audience, repository, namespace or workload. Establish both the trust policy and the caller-controlled claim.
- **Authorization delegated to cloud metadata**: the application trusts caller-supplied identity headers, tags, labels, account IDs or resource metadata without proof they came from the control plane or a trusted proxy. Cloud policy and application authorization are separate checks.

## Ingress, network and control-plane classes

- **Unexpected management reachability**: an ingress, service, listener, security group, balancer annotation, port mapping or bind address exposes an admin, debug, metrics, node, control-plane or internal API to a lower-trust network. Absent network controls alone are `needs_validation`; a repository-defined public route to a sensitive handler can be confirmed. <!-- scrub-allow: generic security term, not a personal name -->
- **Trusted-proxy and mesh bypass**: a backend takes forwarded identity, certificate subject or authorization metadata from peers other than the intended ingress or sidecar, or an alternate port, health path or legacy path skips the mesh. Verify header stripping, peer reachability and behavior when the proxy is absent.
- **Metadata and internal-service reachability**: a user-chosen URL, destination or protocol reaches instance or container metadata, control-plane sockets or internal APIs with workload credentials. URL parsing and redirect handling belong to the ordinary attack classes; here establish the deployed network, metadata version and identity boundaries.

## Container and orchestration classes

- **Host or control-plane capability exposure**: a lower-trust workload can pick privileged mode, capabilities, host namespaces, host paths, device mounts, runtime sockets or service-account tokens that cross into node or control-plane authority. An absent syscall filter or writable root filesystem is hardening unless a reachable operation crosses the boundary.
- **Admission and policy path inconsistency**: one deployment route enforces image identity, namespace, resource, secret or privilege policy while another controller, job, upgrade, restore or compatibility route does not. Confirm the alternate route and the resulting deployed object.
- **Label and namespace trust**: network, admission, secret or identity policy depends on labels, annotations, names or namespaces a less-trusted principal can set. Compare who controls selectors with what authority a match grants.

## Configuration and secret lifecycle classes

- **Control precedence drift**: development values, chart defaults, environment variables, flags, feature gates, sidecar injection or per-region overlays switch off authentication, transport security, tenant scoping or audit in a deployed environment. Render the final configuration for each maintained deployment, not just the base file.
- **Secrets across workload boundaries**: secrets reach logs, crash reports, process arguments, shared environment, broad volumes, build output, service discovery or read APIs open to another workload or tenant. Check secret type and authority; a public endpoint or key identifier is not a credential.
- **Renewal and outage fallback**: failure to mount, refresh, rotate or revoke a workload credential leaves a stale one active or lets the application accept a less-trusted identity mode. Read startup, readiness, reconnect and cached-client behavior.

## Managed storage, events and edge classes

- **Object and signed-link policy**: bucket or container policy, object keys, CDN origins or signed links fail to bind principal, operation, namespace, audience or expiry. Include list and version operations and write paths, not only reads.
- **Event-source identity**: a function or worker takes body fields as the source identity without validating the provider-signed envelope, subscription or topic, account, region and replay state. Compare push, pull, retry and dead-letter paths.
- **Edge and origin mismatch**: an edge or serverless runtime assumes a secret, API, filesystem, isolation level or tenant policy that differs from the origin runtime, and fallback to origin changes authority or caching. Confirm which setting selects each path.

## Universal moves

- Render every maintained environment and tabulate external port, workload identity, network peers, mounted secrets and cloud resources; each difference needs an owner or policy explanation.
- Follow a lower-trust request, object, label or event into cloud policy: which workload credential performs the final operation, and what condition should scope it.
- Compare normal deploy, migration, restore, node maintenance, failover and local or emulator paths, and read behavior when the mesh, admission, identity, secret or policy service is unavailable.

## Validation rules

1. Establish the active source path and the effective deployed object; otherwise `needs_validation` naming the rendered manifest or attachment an owner must show.
2. Name the lower-trust caller or workload, the cloud or application identity, the controllable selector, the affected resource and the unauthorized operation or disclosure.
3. Provider and orchestrator defaults are verified at the pinned version; do not assume a public address, reachable metadata service, permissive firewall or missing admission attachment.
4. Probing running endpoints or changing shared cloud resources is outside review and is `needs_validation`; the local checks `test mode=script` would run render templates, evaluate policy, or inspect namespaces in an isolated fixture with dummy identities.
5. `confirmed` needs an active source trace and a concrete boundary result; `needs_validation` names the exact deployed policy, identity attachment, overlay, network or drift observation required.
