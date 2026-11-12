# merge (dev-team MR lifecycle — devops opens the MR, reviewer reviews and merges)

Mode routing: `refs/roles/orchestrator/workflows.md` § Workflows names one reviewer mode per class; `agents/reviewer.md` § Modes fixes one per spawn. Read that section and no other.

Roles, as on a dev team:

- **implement** = author: creates the branch, commits locally. **devops** pushes and opens the MR at the plan's end. Neither reviews its own MR or merges.
- **reviewer** = reviewer and merge actor: pulls the branch, scans the diff, posts inline notes, sets the verdict, merges on pass.
- **Author identity** = the user's GitLab account (`gitlab.user` in project `AGENTS.md` or `~/.claude/gitlab-user.txt`); every commit, MR and note is authored as that user via MCP, never another.

### Where `merge` sits in the run

`reviewer mode=merge` does not run inside a run: the code review and `test` run once, side by side (`refs/roles/orchestrator/workflows.md` § Workflows), and a finding goes brainstorm `mode=error-batch`, then implement (`CLAUDE.md` §2.1). After the user approves at the final gate devops pushes the branch and opens the MR at the plan's end (`skills/devops-deploy/references/integration.md`; with no plan, only when the user asks), `draft: true` while any check is red, converted to ready before handover; the user merges by hand. This mode runs only when the user asks on an MR already opened: `pass` merges; `needs_changes` and `blocking` leave it open and reroute to implement inside `fix_list[]` scope.

### Phase A — devops opens the MR (author role)

In a plan: branch and local commit once per wave; push and MR by devops at the plan's end, after the user's approval. With no plan: only when the user asks, through devops.

1. **Branch**: in a plan `feat/<plan_id>`, made once before its first task (`refs/roles/implement/close-task.md` § Wave commit); otherwise `rtk git checkout -b <type>/<plan_id>-<slug>`, types `feat | fix | refactor | hotfix | chore | docs`, slug kebab ≤40 chars.
2. **Commit** (Conventional Commits): one per wave in a plan (R-COMMIT-WAVE; a fix after merge review is its own commit, Phase B step 8), else one logical unit. Subject ≤72 chars; body explains WHY; reference `plan_id`, the wave and each `task_id`.
   ```
   <type>(<scope>): <imperative subject>

   <body — why this change, not what>

   Plan: <plan_id>
   Wave: <wave_id> — <task_id>, <task_id>, …
   Refs: <issue id if any>
   ```
3. **Push**: `rtk git push -u origin <branch>`.
4. **Open the MR** via `mcp__mcp_gitlab__create_merge_request` (in a plan only at the first wave commit; later ones update it):
   - **title** (HARD): `<type>(<scope>): <clear imperative summary>`, ≤72 chars, never vague ("update code", "fixes", "wip"): intent from the title alone.
   - **description** (HARD sections, in the project's documentation language):
     ```markdown
     ## Purpose
     {1-2 sentences — the problem and the solution}

     ## Changes
     - {file:line — what changed, and why}

     ## Links
     - Plan: `{plan_dir}/plan.<lang>.md`
     - Task: T<task_id>
     - Issue: #<id> (if any)

     ## Impact
     - API/contract: {yes/no — details}
     - DB migration: {yes/no — file path}
     - UI: {breakpoints/screens touched}
     - Rollback: {rollback steps if it fails}

     ## Test
     - Unit: {count pass/fail, command}
     - E2E: {flow run, evidence path}
     - Manual QA: {what the tester does, step by step}

     ## Pre-merge checklist
     - [ ] Lint pass
     - [ ] Typecheck pass
     - [ ] Unit test pass
     - [ ] E2E test pass (UI/API touching only)
     - [ ] `mcp__gitnexus__impact` reviewed for shared symbols; `api_impact` for routes/handler contracts
     - [ ] No secrets/PII in diff
     - [ ] `result` filled in the task record (`refs/plan-files.md`); `status` in both files — the mirror carries `status` and the `Result` block, which must match `result` (`refs/closeout.md § The result in the mirror`)
     ```
   - **author**: the GitLab user from config, never a generic bot unless the project sets one. **target_branch**: project default (`main` / `develop`). **source_branch**: step 1. **labels**: `<type>`, `plan:<plan_id>`, priority if hotfix, `needs-review`. **assignees**: empty; **reviewers**: project rotation or specified. **draft**: `true` if tests are not yet green.
5. **Return** `mr_iid`, `mr_url`, `source_branch`, `target_branch`, `commits[]` to orchestrator, which routes to reviewer (`mode=merge`), in a plan once, after its last wave commit.

### Phase B — reviewer pulls and reviews

1. **Fetch**: `mcp__mcp_gitlab__get_merge_request` + `get_merge_request_diffs` + `list_merge_request_changed_files`.
2. **Pull locally** (clone present): `rtk git fetch origin <source_branch> && rtk git checkout <source_branch>`. Read code in context, not only the diff.
3. **Sanity checks first** (cheap, fail fast): title is Conventional Commits with clear intent · description has all 6 sections, non-empty · checked boxes spot-verified (run `rtk lint`, `rtk test` on the branch) · `get_merge_request_conflicts` empty · CI pipeline green · no `node_modules`, build artifacts, `.env` or unrelated files.
4. **Diff scan, per hunk** (these bullet names are the `category` anchors):
   - **Correctness**: off-by-one, null/undefined deref, async race, missing await, wrong operator (`==` vs `===`, `<` vs `<=`), early return swallowing an error, swapped args, type coercion.
   - **Contract**: signature change against `mcp__gitnexus__api_impact`: every callsite updated? Backward compatibility kept or migration shipped?
   - **Dead/orphan code**: unused imports, unreachable branches, leftover `console.log`/`print`/`debugger`, commented-out blocks, TODO without owner+date, abandoned variables, dead exports.
   - **Duplication**: an identical block elsewhere; `mcp__gitnexus__query` before flagging.
   - **Reuse miss**: a new helper duplicating an existing util: cite the existing one.
   - **Perf**: O(n²) inside an O(n) loop, unindexed query, missing memo on a hot React tree, sync I/O on the request path, blocking `await` in a parallelizable map, N+1, unbounded list, missing pagination, full-table scan, cached data with no expiry (TTL), not invalidated by the write that changes its source, or with no size bound.
   - **Resource**: unclosed file or connection, missing `useEffect` cleanup, leaked subscription, missing `AbortController`, leaked file handle, DB connection not released.
   - **Readability**: a function over 50 lines doing 3+ things, a name that lies, a magic number without a const, a nested ternary over 2 deep, nesting over 3 levels.
   - **Smells**: the smell baseline with named remedies (matt code-review SKILL.md:43-56; addy code-review-and-quality SKILL.md:36-101). An unused-code claim needs a whole-tree check including tests, fixtures, config and string references (ponytail-audit SKILL.md:57-67). Per finding state what happens if it is skipped, and in the summary say whether the change is a one-way or two-way door with its blast radius (ponytail-review SKILL.md:69-91, matt pr SKILL.md:12-33,166-170).
5. **Cross-cut**:
   - **Tests**: every changed exported symbol touches at least one test? Tests assert behaviour, not implementation? A new branch is tested?
   - **Migration**: schema or contract change has a migration file, documented rollback, idempotent?
   - **Security**: secrets/PII in the diff (grep `key=`, `password=`, `token=`, `Bearer`, email, phone)? Authz on a new endpoint? Validation at the boundary? OWASP Top 10 surface?
   - **Telemetry**: the error path logs a structured error, not a stringified `e`; no PII logged.
   - **Plan compliance**: matches the task's `what` / `files[]` / `solution` in its task record.
6. **Post inline notes** via `mcp__mcp_gitlab__create_draft_note`, one per `file:line`, as `<severity> <category>: <problem>. <fix>.` (e.g. `blocking correctness: missing await → race condition. Add await before db.save().`), then publish in bulk via `bulk_publish_draft_notes`. Author is the configured user. A reply to an inline review comment goes in that comment's own thread, never as a new comment at the top of the MR.
7. **Summary note** via `mcp__mcp_gitlab__create_merge_request_note`:
   ```markdown
   ## Review summary

   **Verdict**: {pass | needs_changes | blocking}

   **Findings**: {N blocking}, {N warning}, {N suggestion}

   **Must fix before merge**:
   - {bullet per blocking finding, link to inline note}

   **Recommended**:
   - {bullet per warning}

   **Optional**:
   - {bullet per suggestion}

   **Diff stats**: {files} files, +{added} / -{removed} lines.
   ```
8. **Verdict and action**:
   - **`pass`**: final guard (CI green, no conflicts, approvals satisfied via `get_merge_request_approval_state`), then `approve_merge_request` and `merge_merge_request` with `squash: true` (default, configurable), `should_remove_source_branch: true`, and `merge_commit_message`:
     ```
     Merge !<iid> <title>

     <description summary, 3-5 lines>

     Reviewed-by: <gitlab user>
     Plan: <plan_id>
     ```
   - **`needs_changes`**: leave the MR open, `unapprove_merge_request` if previously approved, summary note above, route to `implement` with `fix_list[]`. Do NOT merge. In a plan, implement commits that fix as one small commit of its own on the plan branch, its message naming the review finding ids it resolves; a commit resolving a merge conflict is allowed the same way.
   - **`blocking`**: as `needs_changes`, marked `blocking`; reroute to `brainstorm` if the root cause is unclear (architectural concern), else to `implement`.
9. **After merge**: verify the target branch updated (`mcp__mcp_gitlab__list_commits`); the source branch is deleted (MR setting); set each task of the merged plan to `status: done` in the task record (`refs/plan-files.md`) and `plan.<lang>.md`, with the filled `result` block in the task record only (reviewer writes only `status` in the mirror; the `Result` block is the `wave_commit` spawn's, `refs/closeout.md § The result in the mirror`); trigger devops if `target=main` AND auto-deploy is configured (project `AGENTS.md`).

### Severity

`agents/reviewer.md` § Severity is the only severity table. For `merge`: a `warning` permits `needs_changes`, never `pass`; no waiver merges a `warning` (fix it, or it was never a finding).

### Forbidden

`agents/reviewer.md` § Forbidden already covers own-work review, editing the branch, merging on `needs_changes` or `blocking`, preference severity. MR mechanics it lacks:

- Force merge with conflicts unresolved; merge without CI green (override only on a documented hotfix with user approval).
- Skipping description sections; a generic title ("update", "fix bug", "wip", "test").
- A bot or anonymous identity when the project specifies a GitLab user.

### Config

`gitlab.user` (project `AGENTS.md` or `~/.claude/gitlab-user.txt`): GitLab username + token reference for MCP; missing blocks reviewer and implement with `needs_user_input`. `merge.strategy`: `squash` (default) | `merge_commit` | `rebase`. `merge.delete_source_branch`: default `true`. `merge.require_approvals`: default 1 (the reviewer's).
