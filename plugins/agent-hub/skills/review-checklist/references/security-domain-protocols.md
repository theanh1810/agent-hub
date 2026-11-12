# security domain protocols
<Owner: skills/review-checklist/SKILL.md>
<Read when: a diff touches gRPC, GraphQL transport, Thrift, Protobuf, a custom binary protocol, streaming RPC, webhooks, a broker, a queue, pub/sub or an event bus>

---

The identity, per-message and dead-letter bullets of `skills/review-checklist/references/security-surfaces.md` (§ Messaging, load and logic) are the base; this file keeps the rest. Base checks: `skills/review-checklist/references/security-depth.md`. Scale: `refs/roles/reviewer/finding-bar.md` § Confidence and severity, using `skills/review-checklist/references/security.md` § What is a finding guiding what qualifies, and this file adds none. It covers peer identity, logical interpretation, routing, replay, ordering and delivery. Parser memory safety is in `skills/review-checklist/references/security-domain-memory-binary.md`, HTTP framing in `skills/review-checklist/references/security-domain-web-auth.md`, availability effects in `skills/review-checklist/references/security-domain-availability.md`.

## When to use

The target uses RPC frameworks, GraphQL transports, custom binary protocols, streaming RPC, webhooks, brokers, queues, pub/sub or event buses. Split a large system by producer and consumer pair, external or internal peer role, synchronous RPC, streaming and asynchronous message path.

## Core discipline

- "Internal" is not authentication: name the peer identity at each hop and show how it becomes the application principal used for authorization.
- Schema validation proves message shape, not provenance, resource authority, ordering or safe values; follow decoded fields to policy and side effects.
- Broker guarantees and application guarantees differ; write down retry, ordering, acknowledgement, deduplication and transaction behavior before judging a state change.
- A parser disagreement needs two concrete consumers, schema versions or wire representations and one security-relevant divergent value.
- Broker access rules, mesh identity, topic attachment or compatibility behavior outside the repository are `needs_validation`.

## Framing, schema and interpretation classes

- **Boundary and canonicalization disagreement**: components differ on length, compression, duplicate fields, unknown fields, encoding, numeric width, normalization or envelope-versus-body precedence. Compare generated and hand-written parsers, gateways, language bindings and version converters, and confirm which principal, resource or operation changes after decoding.
- **Union, enum and default confusion**: unknown variants, missing discriminators, zero values, default privileges or compatibility mappings reach code that assumes a validated case. Read exhaustive dispatch, default branches, and how old consumers treat newly added fields.
- **Envelope and payload identity mismatch**: authorization uses trusted-looking routing or envelope metadata while the handler acts on a conflicting tenant, account, subject, object or sender in the body. Identify the authoritative source and ensure clients cannot override it.

## RPC identity and authorization classes

- **Interceptor and method-path inconsistency**: an authentication or authorization interceptor covers unary methods but not streams, reflection, health, gateway-transcoded paths, compatibility services or individual stream messages. Compare every registration and route for one operation.
- **Channel identity versus claimed principal**: mutual TLS, workload identity, bearer metadata, forwarded identity or broker credentials authenticate the channel, yet a caller-set field picks the user or tenant. Bind channel identity and claimed principal by deterministic policy.
- **Per-item and streaming gaps**: a stream, subscription, batch or bulk message is authorized once, then later items name other resources or continue after role, membership or token revocation. Re-check wherever scope can change and bind subscriptions to their original principal.
- **Reply-correlation confusion**: predictable, reused or cross-tenant correlation IDs let a response, webhook, cancellation or acknowledgment satisfy another caller's pending operation. Bind each outstanding request to authenticated peer, tenant, operation and lifecycle.

## Broker and queue isolation classes

- **Topic and subscription scope**: a publisher or subscriber can choose another tenant's topic, wildcard, consumer group, partition, reply queue or dead-letter route. Check broker-enforced rules where visible and application-side namespace construction; tenant text inside a payload is not isolation.
- **Failure-path disclosure**: messages sent to dead-letter queues, error topics, tracing or operator views carry secrets or cross-tenant payloads readable by a lower-trust consumer. Review policy and redaction on the failure path, not just normal delivery.
- **Untrusted producer treated as control plane**: a body that declares itself an admin event, provider callback, replication record or migration instruction with no independently authenticated producer and event type. Verify signature and source, account and audience binding before privileged handling. <!-- scrub-allow: generic security term, not a personal name -->

## Replay, ordering and transaction classes

- **Duplicate delivery**: retries or redelivery repeat a side effect because deduplication is absent, runs after the change, or uses a key that collides across tenants or operations. Confirm the broker's delivery model and which effect is not naturally idempotent.
- **Stale and out-of-order acceptance**: older state, revoked membership, canceled work or pre-step-up authorization arrives after newer state and overwrites it. Read sequence and version checks, tombstones, partition changes and restore or replay workflows.
- **Acknowledgment and commit order**: acknowledgment before durable commit loses security-relevant work; commit before an unreliable acknowledgment duplicates a change. Evaluate outbox and inbox behavior and failure recovery.
- **Partial multi-consumer transitions**: several consumers jointly implement one authorization or business transition, and retries or partial failure leave only some committed. Find the invariants that must become durable atomically, or compensate under current authorization.

## Universal moves

- Draw producer, transport, gateway, consumer and storage for each message family; at each hop record the authenticated peer, authoritative tenant and resource fields, validation and side effect.
- Feed one small fixture to every in-repository schema version or language binding, covering duplicate, missing, unknown, boundary, replayed and reordered messages, without generating load.
- Compare normal, retry, dead-letter, replay, migration, reflection, stream and gateway-transcoded routes: policy must survive a change of transport.

## Validation rules

1. Name the realistic producer or peer, the accepted message, the authenticated channel identity, the affected principal or resource and the unauthorized change or disclosure.
2. A disagreement claim cites both parsers or consumers and the divergent decoded value; safe rejection by either side prevents confirmation.
3. Replay and order claims establish the real delivery guarantees and reproduce the invariant failure on a bounded in-memory transport; a check against a running broker is `needs_validation`.
4. Authorization and isolation claims verify every interceptor, broker rule, gateway and consumer layer visible in source; an attachment outside the repository makes the candidate `needs_validation`.
5. `confirmed` needs the whole message lifecycle and an observed meaningful result; `needs_validation` names the broker, service identity, route or delivery fact required.
