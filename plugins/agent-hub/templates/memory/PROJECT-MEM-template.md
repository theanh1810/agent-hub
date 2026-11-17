---
name: project-mem-<project_slug>
description: Cross-session durable memory for <project_name>. AI in a fresh session recalls server, deploy, decisions, recent work.
metadata:
  type: project
  project_slug: <slug>
  last_updated: <YYYY-MM-DD>
---

# <project_name> — Project Memory

## Stack
- {lang/runtime, frameworks, DB, infra}

## Project files index (where AI looks)
- Workspace root: <abs path>            # CODE_ROOT + one segment, `refs/artifact-layout.md § Where the workspace root is`
- Server info: `{workspace_root}/docs/devops/SERVER-INFO.md`
- Plan dir: `{workspace_root}/docs/changes/`
- Design library: `~/.claude/docs/design-library/{lib}/`   # global, shared across products, never per product
- AGENTS.md: `<path>`

## Operational
<!-- present state: update an entry in place when it drifts -->
- Deploy command (staging): `<cmd>` — owner: devops — last verified: <YYYY-MM-DD>
- Deploy command (prod): `<cmd>` — gate: requires_approval
- Rollback: `<cmd>`
- SSH access pattern: see SERVER-INFO §2
- Log fetch shortcuts: see SERVER-INFO §5
- Vault refs index: <where secrets live>

## Decisions
<!-- ledger: append only, every claim dated; a claim about code names commit and repo; a change adds a new dated line marking the old one superseded -->
- <YYYY-MM-DD> — {decision} — **Why:** {reason} — **How to apply:** {when/where} — code claim: <repo>@<commit>
- ...

## Conventions
- {pattern} — **Why:** ... — **How to apply:** ...

## Recent changes (last 10)
- <YYYY-MM-DD> · plan_id: <id> · {1-line outcome} — files: <count>

## Open / deferred
- {open question / known tech debt}
