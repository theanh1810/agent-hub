# security domain supply chain
<Owner: skills/review-checklist/SKILL.md>
<Read when: a diff touches dependency resolution, CI workflows, build or release artifacts, signing, promotion, an updater or a plugin loader>

---

Dependency risk basics are in `skills/review-checklist/references/security-depth.md`; this file adds the trust handoffs from source to the artifact a user runs. Impact level: `refs/roles/reviewer/finding-bar.md` § Confidence and severity, via `skills/review-checklist/references/security.md` § What is a finding steering what qualifies, and this file adds none. For flaws inside a local binary loader read `skills/review-checklist/references/security-domain-memory-binary.md`; for runtime workload authority read `skills/review-checklist/references/security-domain-cloud.md`. A threat named below that `security-surfaces.md` already holds is not repeated.

## When to use

The target resolves dependencies, builds from untrusted contributions, runs CI, creates or signs release artifacts, promotes builds, loads plugins or updates deployed software. Split a large target into dependency resolution, CI isolation, artifact provenance, release authorization and updater or plugin trust.

## Core discipline

- A mutable or known-vulnerable dependency is not a finding alone; show who can influence resolution, which build consumes it and what execution or release boundary follows.
- Follow integrity across each handoff: source identity, resolved inputs, build worker, artifact identity, test result, signature or attestation, promotion and the update consumer.
- CI configuration is authorization code: establish which event triggered a workflow, whose code runs, which secrets and tokens exist, and what the job may publish or change.
- A checksum fetched from the same untrusted place as the artifact proves nothing independent; name the trusted root and the failure behavior.
- Branch protection, hosted-runner, registry, signing-service and production-promotion facts the repository does not show are `needs_validation`.

## Dependency and build-input classes

- **Namespace and source confusion**: resolver settings choose an unintended public or private namespace, fallback registry, mirror or source URL. Read package names, source priority, lockfile and checksum use, alternate build files, per-platform resolution, and first-time versus update behavior.
- **Mutable, unbound inputs**: builds consume branches, tags, unverified submodules, downloaded tools, generated assets, remote includes, floating CI actions or container tags that can change with no source review. Needs a lower-trust writer and a path into trusted output; reproducibility alone does not prove authenticity.
- **Generated-source provenance**: schemas, vendored archives, generated clients, localization, documentation examples or binary blobs yield shipped or executable content without the review and integrity gate source gets. Compare local regeneration with committed output and find who controls input and generator.
- **Build-context inclusion**: secrets, local configuration, repository metadata, fixtures or developer artifacts enter a package or image because context and ignore rules are wider than intended release inputs. Confirm the artifact exposes a real credential, private data or privileged configuration.

## CI and automation classes

- **Untrusted code in a privileged workflow**: a pull request, comment, fork, dependency update or external event runs contributor code with protected secrets, write tokens, deployment authority or a trusted runner. Compare trigger type, checkout ref, approval gate, environment protection and permission narrowing; do not assume host defaults the source does not state.
- **Command and expression confusion**: branch names, commit messages, issue fields, artifact names, matrix values or generated output reach shell commands, template expressions, paths or privileged inputs unvalidated.
- **Cache, artifact and workspace mixing**: a lower-trust job fills a cache, artifact, shared workspace or output that a higher-trust job later restores and runs or releases. Read cache keys and namespaces, producer identity, digest binding, retention, and whether promotion re-resolves by a mutable name.
- **Automation identity overreach**: jobs hold permissions wider than the operation, repository, environment or duration needs, and untrusted inputs pick the resource. Missing least privilege is hardening; require a reachable privileged action.

## Release and update classes

- **Substitution between build and promotion**: tests, review, signature and publication name a mutable tag, filename, channel or artifact ID instead of one immutable digest. Check every copy, repack, architecture merge and provenance step between build and release.
- **Release authorization and signing policy**: a release or signature accepted from the wrong workflow, repository, branch, environment, key role or threshold. Read identity claims inside attestations and confirm the consumer checks them, not merely that a signature is valid; rotation, expiry and revocation must fail closed where policy requires.
- **Update metadata and rollback**: an updater authenticates payload bytes but not version, product, platform, channel, target path, expiry or rollback state, or accepts metadata and payload from different authorized transactions. Verify atomic application and recovery; a signature call with no policy binding is incomplete.
- **Plugin trust expansion**: a package gains host authority beyond its declared scope, a lower-trust publisher takes over another's identity, or setup and update hooks run before authenticity and capability checks. Deliberately loading arbitrary same-user plugins is not a privilege boundary.

## Universal moves

- Walk backward from a released digest or applied update to every source, generated input, credential, worker, cache, test result and authorization decision.
- Compare untrusted and protected workflow events side by side; mark each persisted channel that crosses between them and require an immutable identity plus producer trust.
- Read the revoked-key, failed-download, missing-attestation, partial-platform-release, rollback and registry-outage paths; the failure policy is part of release integrity.

## Validation rules

1. Name the lower-trust actor, the controllable source, cache, artifact or metadata, the trusted consumer (job or updater) and the resulting unauthorized publication, code inclusion, secret disclosure or privileged run.
2. Prove artifact identity across the broken handoff: a different mutable name or unbound digest must reach a real consumer.
3. Package-manager, repository-host, registry and signing defaults are verified at the pinned version; an unknown hosted control is `needs_validation`.
4. Any check that publishes, or touches a real release or credential, is not run; `needs_validation` names the local check `test mode=script` would run with a harmless fixture repository, a dummy credential marker and a non-production namespace.
5. `confirmed` needs a source-visible handoff and a meaningful result; `needs_validation` names the branch, runner, registry, signing or deployment fact an owner must observe.
