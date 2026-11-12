---
slug: "<repo>-<what-was-done>"          # starts with the repo name (refs/artifact-layout.md § Where writing is allowed)
date: "YYYY-MM-DD"
run:
  started_at: "YYYY-MM-DDTHH:MM:SSZ"   # ISO 8601 UTC, seconds; taken from .cm-tmp/{task_id}/run-started-at
  finished_at: "YYYY-MM-DDTHH:MM:SSZ"
files_changed: ["<path/to/file>"]
commits: []   # SHAs of this change, when it was committed; empty -> the map shows no_commit
# data_impact: the 13 declared keys of refs/closeout.md § Data impact, all present, a list of entries or "none: <reason>".
# Free text is written in the user's language, the one exception to the English yaml; keys, none:, enum values, paths, symbols and
# commands stay verbatim. Replace every placeholder: one left as written shows on the change map as a reason nobody wrote.
data_impact:
  purpose: "none: <one-line reason>"
  flow: "none: <one-line reason>"
  ui: "none: <one-line reason>"
  endpoints: "none: <one-line reason>"
  db_schema: "none: <one-line reason>"
  data_reads: "none: <one-line reason>"
  data_writes: "none: <one-line reason>"
  business_rules: "none: <one-line reason>"
  access: "none: <one-line reason>"
  events_jobs: "none: <one-line reason>"
  config: "none: <one-line reason>"
  code_changes: "none: <one-line reason>"
  risk_rollback: "none: <one-line reason>"
---

# <slug>

## What changed
<file and function or line>

## Old code
<short excerpt>

## New code
<excerpt>

## What the change does
<how the new mechanism differs from the old one, not a retelling of the diff>

## Impact
<what the user sees differently; what else it touches; whether it needs a migration, a restart or a new login>

## Benefit and cost
<the concrete benefit and the price paid; the cost is never left empty>
