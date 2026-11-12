---
name: devops-deploy
description: Use when configuring infrastructure or CI/CD, deploying to staging or production, releasing a mobile build, fetching server logs, or managing rollback. Gives a deploy, release, log fetch or rollback that is idempotent and reversible. Triggers on "deploy", "release", "rollback", "CI/CD", "TestFlight", "Play Console", "EAS", "Fastlane".
user-invocable: false
allowed-tools:
  - Read
  - Grep
  - Glob
model: inherit
---

# DevOps Deploy

Procedure for the `devops` agent: idempotent, gated, observable.

## When to use

- A plan's devops wave, a staging or production deploy, a container or CI/CD change, a mobile release.
- A `log_fetch_request` from brainstorm, or an `infra_escalation_request` from test (`refs/roles/devops/server-touching.md`).
- End-of-plan branch integration.

## When not to use

- Application source or business logic (implement), testing (test), reviewing (reviewer).
- A step the plan does not name: that is a plan change, returned as `needs_revision`.

## Load

- `skills/devops-deploy/references/release.md` before a deploy, a CI/CD change or a rollback plan.
- `skills/devops-deploy/references/observability.md` for monitoring, alerting, logging or a `SERVER-INFO.md` alert entry.
- `skills/devops-deploy/references/integration.md` at the end of a plan (merge, PR, worktrees).
- `skills/devops-deploy/references/runbook.md` for a step only a person can do.
- `skills/devops-deploy/references/mobile.md` for an iOS or Android release.

## Workflow

1. **Bootstrap** (`agent-bootstrap`): mem0 outage patterns and `mcp__gitnexus__detect_changes` to compare the deploy scope with the git diff.
2. **Read SERVER-INFO.md** (`{workspace_root}/docs/devops/SERVER-INFO.md`, `CLAUDE.md` §19.0) every run, MANDATORY. Missing → block, propose the template copy from `${CLAUDE_PLUGIN_ROOT}/templates/SERVER-INFO.md`, return `needs_user_input` asking for hostnames, SSH, CI, log paths, monitoring and vault refs.
3. **Preflight**: read `AGENTS.md`; verify the environment (docker, kubectl, permissions, resources); check the six groups of `skills/devops-deploy/references/release.md`; cite SERVER-INFO §N for every command.
4. **Approval gate**: return `needs_approval`; **main thread** surfaces it (`CLAUDE.md` §2.1A), never orchestrator, and devops never pauses to ask by itself. Gates: `requires_approval` or `devops_security_sensitive`; `production` with `requires_approval`; mobile `track='external'` or `'production'`.
5. **Execute**: idempotent commands, atomic operations, following `task_definition.verification`.
6. **Verify**: health checks, resource allocation, pipeline status; after a release, the first-hour checks in `skills/devops-deploy/references/release.md`.
7. **Self-critique**: everything healthy, no orphans, usage within limits, idempotency and rollback verified.
8. **Cleanup**: remove orphaned resources (container, volume, DNS, temp user), close connections.
9. **Closeout**: update SERVER-INFO.md on drift (new host, changed CI step, refined rollback). Route the outcome by lifetime (`skills/context-memory/SKILL.md`): a lesson true in **any** repo → **mem0** (`type: reusable_workflow`, a trap hit twice → `recurring_pitfall`, after dedup by `{project, type, subject}`); a workspace fact (deploy command, host, rollback path, verification date) → the project memory file, `## Operational`. Neither takes a secret, token or raw log (`CLAUDE.md` §10).

## Log fetch (brainstorm debug requests)

On a `log_fetch_request`:
1. Read SERVER-INFO §5 (Logs) and pick the command for `source_hint`.
2. Run over SSH, kubectl or the log-UI API (RTK wrap for verbose output).
3. Save the raw output verbatim, uncompressed, to `{plan_dir}/logs/{task_id}-{YYYYMMDD-HHMMSS}.log` (root per `CLAUDE.md` §19.0, naming §19.4).
4. Redact secrets, tokens and personal data in the inline excerpt; quote only allowed fields.
5. Return `log_fetch_result`: command, path, first 50 matched lines.

Forbidden: paraphrasing lines, dropping timestamps, inlining more than 200 lines, skipping redaction. A production fetch needs brainstorm's `purpose`; record it as step 9 does; the log body goes to neither store.

## Key rules

- A `production` deploy has a rollback command already tested on staging; cert rotation, DB migration and new infrastructure need `requires_approval: true`; SSH access goes through the vault, never a plain file in the repo.
- **Docker**: specific tags (`node:22-alpine`), never `:latest` in production; multi-stage, non-root user, `HEALTHCHECK`, resource limits, `.dockerignore` excluding `node_modules`, `.git`, `tests`. Reuse images and containers (`refs/roles/devops/server-touching.md § Docker images and containers`).
- **Kubernetes**: `livenessProbe`, `readinessProbe`, `startupProbe` with sensible `initialDelay`.
- **Health and config**: a health endpoint returns `{ status: "ok" }` (or with dependencies, uptime, version); Twelve-Factor, env vars validated against a schema at startup (Zod), fail fast.
- Graceful shutdown on SIGTERM, separate environments, no hardcoded credentials.
- Strategies, flags, rollout thresholds, rollback commands: `skills/devops-deploy/references/release.md`.
- CI never holds production secrets; a repository ships an `.env.example` and no real value. Migration: `skills/devops-deploy/references/migration.md`; monitoring: `skills/devops-deploy/references/observability.md`; go/no-go: `skills/devops-deploy/references/ship-checklist.md`.

## Red flags and rationalizations

| Rationalization | Reality |
|---|---|
| "This migration or restart is obviously needed, I'll just do it" | A step the plan does not name is a plan change |
| "rsync exited 0, so it deployed" | Exit 0 is not evidence; show the host's SHA and proof the new build serves |
| "Rollback is written down, that is enough" | A rollback never run on this host is a plan, not a guarantee |
| "I remember this host's docroot" | Re-read SERVER-INFO.md every run; memory overwrote the wrong directory once |

## Verification

- [ ] SERVER-INFO sections cited per command; the deployed SHA read from the host with proof of serving.
- [ ] Rollback command stated, and whether it was ever run on this host.
- [ ] No orphan resources; no secret in any log, command or handoff (vault references only).
