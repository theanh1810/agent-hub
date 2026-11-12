---
description: "Run the auditor agent to check fleet effectiveness (default: last 24h). Reads docs/changes/, errors.yaml, mem0, and MR history when present."
---

# /audit — Daily fleet effectiveness audit

Invoke the `auditor` agent on the project at cwd. To audit every project from a shell or a schedule, run `agent-hub-audit`. Every `docs/…` path resolves from `{workspace_root}` (`CLAUDE.md` §19.0).

## Steps

1. Spawn `Agent(subagent_type="agent-hub-auditor:auditor")` with:

```json
{
  "time_window": { "from": "<now - 24h ISO8601>", "to": "<now ISO8601>" },
  "scope": "single_project",
  "project_slugs": ["<derived from cwd git remote OR cwd dirname>"],
  "compare_days": 7,
  "interactive": true
}
```

2. The auditor's sources are `${CLAUDE_PLUGIN_ROOT}/agents/auditor.md` § Sources. `interactive: true` lets it ask one question at a time; on `needs_user_input` main thread calls `AskUserQuestion` and re-spawns with the answers.
3. The auditor writes `docs/audits/{YYYY-MM-DD}.md` (in the user's reply language, from `${CLAUDE_PLUGIN_ROOT}/templates/audit/AUDIT-template.md`).
4. Main thread returns a 3-sentence summary, the report path, the top red flags and high-level recommendations.

## Args (optional)

Each arg changes one field; no arg keeps step 1's defaults.

| Arg | What it changes |
|---|---|
| `/audit` | default: last 24 h, `single_project`, model per frontmatter (`sonnet`) |
| `/audit 7d` | `time_window.from = now - 7 days`; same for `30d`, `48h` |
| `/audit all` | `scope = "all"`, drop `project_slugs` |
| `/audit since 2026-05-25` | `time_window.from = 2026-05-25T00:00:00` in the machine's timezone |
| `/audit deep` | `Agent(subagent_type="agent-hub-auditor:auditor", model="opus")`: the only arg that changes the model (default `sonnet`, `CLAUDE.md` §0) |

Combinable: `/audit 7d deep` is a 7-day window on opus.

## Output format

Final response, in the user's reply language:

```markdown
## Audit summary
{2-3 sentences: completion_rate, rework_rate, top red flag}

## Metrics
- completion_rate: {N}/{M} = {ratio}: completed / (completed + failed)
- rework_rate: {ratio}
- implement_to_reviewer_ratio: {N}/{M} = {ratio}: {🟢 ≥0.9 | 🟡 0.5–0.9 | 🔴 <0.5 | ⛔ =0 when implement tasks exist}
- closeout_complete: {N}/{M} = {ratio}: {🔴 <0.8 → `closeout_skipped`}; write `null` when no run produced a diff
- sdd_metrics: spec_coverage {…} · ac_coverage {…} · ac_unmeasurable {…} · trace_ratio {…} — print `N/A` without an adoption block, never `0%`

## Files changed
- docs/audits/{YYYY-MM-DD}.md

## Top red flags
- {flag 1: severity + evidence}
- {flag 2}
- {flag 3}

## Recommendations
- {action 1: file/agent target}
- {action 2}

## Risk
{1 sentence; escalate if the trend is bad}
```

## Constitutional

- READ-ONLY outside `docs/audits/{YYYY-MM-DD}.md`.
- Cite `plan_id` / `task_id` / `MR_iid` for every claim; severity by evidence, no vibes.
- Never name a developer; name only the agent and the pattern.
