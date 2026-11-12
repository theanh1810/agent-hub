# security domain ai llm
<Owner: skills/review-checklist/SKILL.md>
<Read when: a diff touches a model call, prompt assembly, retrieval, agent memory, a tool-calling loop, an MCP client or server, or code that acts on model output>

---

The base rules for model output, indirect injection, memory poisoning, approval binding and per-request budgets are in `skills/review-checklist/references/security-surfaces.md` (§ AI and LLM features); this file keeps the classes it lacks. Base checks: `skills/review-checklist/references/security-depth.md`. Ranking: `refs/roles/reviewer/finding-bar.md` § Confidence and severity, with `skills/review-checklist/references/security.md` § What is a finding deciding what qualifies, and this file adds none. Transport, access control, query building, filesystem use and output rendering stay ordinary boundaries; this file covers the model-specific delegation layer.

## When to use

A language model takes part in a trust-sensitive decision: assistants, retrieval pipelines, persistent agent memory, tool-calling loops, MCP servers and clients, code that builds prompts from untrusted input, or code that acts on model output. The flow that matters is untrusted content to model or memory to capability, authority or sink. Split a large target by retrieval, memory, tool dispatch, MCP and output handling.

## Core discipline

- Prompt injection alone is not a finding; require a code-level boundary failure: content reaching another principal's context, authority the requester lacks, data they cannot read, or a sink they cannot reach directly.
- Model output, memory, tool descriptions and MCP responses are untrusted input; point to the code that grants authority, trusts output, writes durable state or feeds a sink.
- A guardrail prompt is not a boundary; only deterministic checks, resource-scoped authorization, isolation, binding and constrained credentials count.
- State the attacker, affected principal, effective execution identity, resource, exact action, authority used and observable impact. A direct request to use the requester's own authority is not a delegation defect merely because a model carries it out.
- Authorization and action binding are separate controls: attacker content that causes an action under a victim's valid authority is an action-binding failure when the victim never intentionally requested or approved that exact action.
- A provider, deployment, model, renderer or identity behavior that cannot be observed locally makes the candidate `needs_validation`.

## Context, retrieval and memory classes

- **Context bleed across sessions or tenants**: history, embeddings, retrieval results or prompt caches keyed too broadly. Verify tenant and access filters inside the query itself and in every cache key; a tenant field stored on an object is not enforcement if another query, shared cache or batch path omits it.
- **Role and provenance confusion**: prompt assembly lets untrusted text pose as a system message, earlier turn, tool result, policy or memory record. Look for string concatenation, untyped history, caller-set role fields and serialization round trips that drop source labels; confirm the forged provenance changes a deterministic trust decision or reaches a meaningful capability.
- **Memory writers and readers**: for persistent memory, list who may create, update, merge and delete, its provenance and tenant scope, whether low-trust observations become durable instructions, and whether retrieval separates user preferences from tool policy. Memory a user saved intentionally and used only for that user's allowed requests is not a cross-boundary finding.

## Tool and action classes

- **Tool-argument injection**: model-produced arguments reach SQL, shell, file, URL-fetch or privileged APIs without handler-side validation. Treat the tool schema as input parsing and follow each field from decoded call to sink; structured output narrows shape but does not establish authorization, safe paths, safe URLs or query meaning.
- **Confused-deputy agency**: the agent uses a service identity or broad credential while the handler never re-checks the requester's permission on the named resource. Verify the effective identity and whether the caller could perform that exact operation through the normal product interface; a shared credential with enforced per-user query scope is not a defect.
- **Approval drift**: an approved described action runs with changed arguments, a different resource, principal or later model turn. Confirm approval binds the normalized tool name, the whole argument object, requester, target, amount, expiry and batch membership, and that retries and resumed sessions cannot authorize a mutated or duplicate side effect.
- **Schema and dispatcher disagreement**: the schema accepts aliases, extra fields, duplicate keys, coercions, free-form nested objects or out-of-range values that the dispatcher or handler reads differently. Compare validation, canonicalization, generated bindings and handler defaults, and validate again where a value becomes a resource selector or security option.
- **Unbounded delegated loops**: a bounded request queues repeated spend, send, mutation or external work with no per-request budget, per-action authorization, cancellation or idempotency. Confirm effect on shared cost, quotas, other users or durable state through code-level accounting and a locally bounded loop, never by exhausting a service.

## MCP and sub-agent classes

- **Trust inheritance**: a delegated task receives the whole session, credentials, memory or capabilities instead of the least authority it needs. Check the principal and tenant carried into each call, capability narrowing, credential audience, and whether results coming back are treated as untrusted.
- **Server and tool identity confusion**: calls or results routed by server names, tool names, request IDs, resource URIs or model-picked aliases an attacker can influence, instead of the authenticated connection and outstanding request. Check whether two servers can claim one tool or resource identity, whether reconnecting changes the binding, and whether one server's response can satisfy another's pending call.
- **Metadata as policy**: tool descriptions, resource metadata, prompts, completion hints or schemas from an MCP peer trusted as authorization. They can steer the model but never grant capability; find the deterministic allowlist, server identity check and handler authorization that stay authoritative when metadata conflicts.

## Output and disclosure classes

- **Output reaching an executing sink**: model output goes to HTML, Markdown, a template, a URL or a command without the sink's encoding and policy. For browser rendering check auto-loaded resources and sanitization in the client-side domain; renderer behavior outside the repository is `needs_validation`.
- **Sensitive context extraction**: the assembled context holds credentials, another user's data, private source or policy values that grant access, and user-influenced output exposes them. Read prompt assembly and data-fetch code; revealing generic instructions or behavior that crosses no data boundary is not a finding.

## Universal moves

- Draw four maps first: each execution identity, each capability, every writable context or memory source and each output destination; then connect the principal at the start to the authority at the end.
- Start at side-effecting tools and work backward through dispatcher, schema, confirmation, model context, retrieval and ingestion; start at durable memory reads and trace every writer.
- Compare direct, queued, retry, resume, batch and delegated paths for one action; the strongest gate must apply after arguments are final and before every side effect.

## Validation rules

1. Name the crossed boundary and observable result: attacker, affected principal or shared resource, execution identity, target, and the unauthorized or unrequested action or disclosure.
2. Confused-deputy claims prove the tool lacks requester-and-resource authorization and that the attacker cannot do the same thing normally; action-binding claims instead prove attacker content caused an action under the affected principal's authority that the principal did not intentionally request or approve, and generic authorization does not establish that intent.
3. Memory or retrieval claims cite both the attacker-controlled write and the later cross-principal read or privileged decision; a shared record with no reachable consumer is not enough.
4. Action binding compares the intentional request or normalized approved object with the one the handler uses, and confirms a locally observable unrequested action, mutation, duplicate or authority change without running anything harmful; schema disagreement compares the normalized validated object with the handler's.
5. MCP identity claims verify the authenticated connection, request correlation, tool namespace and effective credential; external server identity or deployment routing makes it `needs_validation`.
6. `confirmed` needs a full source trace and a meaningful result; `needs_validation` names the unresolved boundary fact and the bounded local or owner-run check.
