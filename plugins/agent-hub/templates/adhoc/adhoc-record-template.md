---
slug: "<repo>-<what-was-done>"          # starts with the repo name (refs/artifact-layout.md § Where writing is allowed)
date: "YYYY-MM-DD"
run:
  started_at: "YYYY-MM-DDTHH:MM:SSZ"   # ISO 8601 UTC, seconds; taken from .cm-tmp/{task_id}/run-started-at
  finished_at: "YYYY-MM-DDTHH:MM:SSZ"
files_changed: ["<path/to/file>"]
commits: []   # SHAs of this change, when it was committed
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

## Data and screens affected
None

## Impact
<what the user sees differently; what else it touches; whether it needs a migration, a restart or a new login>

## Benefit and cost
<the concrete benefit and the price paid; the cost is never left empty>
