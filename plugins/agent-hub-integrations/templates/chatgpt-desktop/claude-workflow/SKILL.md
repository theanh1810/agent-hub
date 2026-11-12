---
name: claude-workflow
description: Run the user's complete Claude engineering workflow in local Codex Work using native role profiles, migrated skills, canonical plans, review, tests and closeout. Use for engineering investigation or changes and workflow audits; exclude general conversation and unrelated document work.
---

# Native engineering fleet for Codex Work

This is the entry skill for the native conversion installed in `~/.codex/claude-workflow/`.
Read `~/.codex/claude-compat/runtime.md` first. It defines the actual host mappings, source
precedence, model/effort inheritance, skill bootstrap, gates and runtime limitations.
Then read only the source rule and role references relevant to this request.

Use the configured native role profiles under `~/.codex/agents/`: orchestrator, brainstorm,
scout, designer, planner, implement, reviewer, test, devops and auditor, plus effort variants.
Main dispatches workers in dependency order using the exposed host API; workers return a follow-up request and do not
nested-spawn. System/developer restrictions and the user's current scope always take
precedence. If delegation is prohibited or unavailable, disclose sequential phases and
leave a mandatory independent-review gate pending rather than inventing a reviewer.

## Start

1. Resolve the actual product workspace and repository roots. Neither `.claude` nor the
   converted rule library is the implicit product root.
2. Classify from `~/.codex/claude-compat/refs/workflow-routing.md` and the single routing table
   `~/.codex/claude-compat/refs/roles/orchestrator/workflows.md`.
3. Use the matching native profile and explicitly load its named bootstrap skills if missing.
   Keep the inherited OpenAI model and the configured profile effort; never pass Claude
   model labels or claim an unenforced turn cap.
4. Carry existing user choices and authorization through design, plan, execution and closeout.
   Perform the concrete authorized work; preserve unresolved product and host approval gates.

## Canonical state

Specs/current approved deltas own behavior. Brainstorm owns scope and `change_design`.
Planner details it without inventing ACs. Execution YAML owns task status/results;
Vietnamese mirror is derived. Reuse the existing plan resolver,
validators, templates and lock protocol through the converted
library's support links. User amendments update design/plan before code changes.

Review precedes tests. Independent reviewers get frozen code and an isolated brief.
Record actual checks and evidence, never tool availability as a test PASS. Preserve
error batching, the two-cycle correction cap and honest accepted-partial reporting.
Closeout verifies scope/diff, results, spec synchronization, available durable memory and
cleanup of this task's exact temporary paths.

## Entry commands

- Spec operations: `source-command-spec`; init/check helpers are supporting references.
- Audit: `source-command-audit`.
- Code style: `source-command-codestyle`.
- Explicit full multi-agent pipeline: `orchestrate`.

These are native skill entries, invoked with the host's skill selector. Hooks require the
normal Codex trust review; do not bypass it. No skill authorizes a deployment, publication,
message or additional tool access. Reply in Vietnamese and report actual outcomes and limits.
