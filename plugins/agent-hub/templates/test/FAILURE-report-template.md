<!-- Template for agents/test.md § Output discipline — failures only.
     One file per failed test case, written to
     {workspace_root}/.cm-tmp/{task_id}/failure-docs/{test_case_id}.md — CLAUDE.md §19.0.
     Report what happened. Do not diagnose — that is brainstorm work. -->

# Failure: {test_case_id} — {scenario}

**Task:** {task_id} · **Plan:** {plan_id} · **Layer:** L{1|2|3|4} · **Type:** {test_case.type}
**Failed stage:** {1_ui|2_fe_behaviour|3_fe_feel|4_fe_perf|5_request|6_backend|7_data|8_binding} · **Steps completed:** {N} of {M}

## Steps to reproduce
1. {verbatim test_case.steps[0]}
2. {verbatim test_case.steps[1]}
...

## Expected
{verbatim test_case.expected}

## Actual
{1-3 sentences describing what happened. NO root-cause speculation. NO "I think it's because..."}

## Network capture
**Endpoint:** {METHOD URL}
**Status:** expected {N}, got {M}
**Request payload (first 20 + last 20 lines):**
```json
{redacted payload — strip Authorization, Cookie, secrets}
```
**Response body (first 20 + last 20 lines):**
```json
{actual response — strip secrets}
```
**Body diff vs contract:**
| Field | Expected | Actual | Kind |
|---|---|---|---|
| ... | ... | ... | missing\|wrong_type\|wrong_value\|extra\|wrong_status |

## Console errors (first error verbatim)
```
{first console.error + stack frame, NO compression}
```

## Network failures (non-expected 4xx/5xx)
- {METHOD URL} → {status} {first 200 chars of body}

## Visual evidence
Scratch files live in `{workspace_root}/.cm-tmp/{task_id}/`; the at most 3 artefacts this report cites are copied to `{plan_dir}/evidence/{task_id}/`.
- Pre-action: {workspace_root}/.cm-tmp/{task_id}/step-NN-pre-{viewport}.png
- Post-action: {workspace_root}/.cm-tmp/{task_id}/step-NN-post-{viewport}.png
- A11y snapshot: {workspace_root}/.cm-tmp/{task_id}/step-NN-pre-snapshot.txt
- Baseline compared against: docs/reviews/baselines/{repo}-{route_slug}/{viewport}.png · similarity {0.00} — threshold: agents/test.md § Evidence storage

## Suspected scope (hint for brainstorm, NOT root cause)
{≤1 sentence. Blank if not obvious. Tester does NOT diagnose. Example: "POST /api/orders returned 500 — likely backend route." NOT "the bug is in OrderService.create() because..."}
