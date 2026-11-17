# merge (dev-team MR lifecycle — devops opens the MR, reviewer reviews, devops posts the notes and merges)

Mode routing: `refs/lanes.md` names one reviewer mode per lane; `agents/reviewer.md` § Modes fixes one per spawn. Read that section and no other.

Roles, as on a dev team:

- **implement** = author: creates the branch, commits locally. **devops** pushes and opens the MR at the plan's end. implement never reviews its own MR or merges.
- **reviewer** = reviewer: pulls the branch, scans the diff and returns the verdict, findings and summary text; it writes nothing to GitLab.
- **devops** = merge actor: posts the reviewer's notes, records the approval and merges on pass.
- **Author identity** = the user's GitLab account (`gitlab.user` in project `AGENTS.md` or `~/.claude/gitlab-user.txt`); every commit, MR and note is authored as that user via MCP, never another.

### Where `merge` sits in the run

`reviewer mode=merge` does not run inside a run: the code review and `test` run once, side by side (`refs/lanes.md`), and a finding goes brainstorm `mode=error-batch`, then implement (`refs/gates.md § Gate procedures`). After the user approves at the final gate devops pushes the branch and opens the MR at the plan's end (`skills/devops-deploy/references/integration.md`; with no plan, only when the user asks), `draft: true` while any check is red, converted to ready before handover; the user merges by hand. This mode runs only when the user asks on an MR already opened: `pass` is followed by one devops wave that posts the notes and merges; `needs_changes` and `blocking` leave it open and reroute to implement inside `fix_list[]` scope.

### Phase A — devops opens the MR (author role)

In a plan: branch and local commit once per wave; push and MR by devops at the plan's end, after the user's approval. With no plan: only when the user asks, through devops.

1. **Branch**: in a plan `feat/<plan_id>`, made once before its first task (`refs/gates.md § Gate procedures`); otherwise `git checkout -b <type>/<plan_id>-<slug>`, types `feat | fix | refactor | hotfix | chore | docs`, slug kebab ≤40 chars.
2. **Commit** (Conventional Commits): one per wave in a plan (R-COMMIT-WAVE; a fix after merge review is its own commit, Phase B step 8), else one logical unit. Subject ≤72 chars; body explains WHY; reference `plan_id`, the wave and each `task_id`.
   ```
   <type>(<scope>): <imperative subject>

   <body — why this change, not what>

   Plan: <plan_id>
   Wave: <wave_id> — <task_id>, <task_id>, …
   Refs: <issue id if any>
   ```
3. **Push**: `git push -u origin <branch>`.
4. **Open the MR** via `mcp__mcp_gitlab__save_merge_request` (in a plan only at the first wave commit; later ones update it):
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
     - [ ] the task's box ticked in `tasks.md` and its handoff written (`refs/closeout.md § Recording What a Change Did`)
     ```
   - **author**: the GitLab user from config, never a generic bot unless the project sets one. **target_branch**: project default (`main` / `develop`). **source_branch**: step 1. **labels**: `<type>`, `plan:<plan_id>`, priority if hotfix, `needs-review`. **assignees**: empty; **reviewers**: project rotation or specified. **draft**: `true` if tests are not yet green.
5. **Return** `mr_iid`, `mr_url`, `source_branch`, `target_branch`, `commits[]` to main thread, which routes to reviewer (`mode=merge`), in a plan once, after its last wave commit.

### Phase B — reviewer pulls and reviews

1. **Fetch**: `mcp__mcp_gitlab__get_merge_request`, asking for its diffs and changed files.
2. **Pull locally** (clone present): `git fetch origin <source_branch> && git checkout <source_branch>`. Read code in context, not only the diff.
3. **Sanity checks first** (cheap, fail fast): title is Conventional Commits with clear intent · description has all 6 sections, non-empty · checked boxes spot-verified (run the repo lint and test commands on the branch) · the MR merge status read from `get_merge_request` shows no conflicts · CI pipeline green · no `node_modules`, build artifacts, `.env` or unrelated files.
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
   - **Plan compliance**: matches the task's text and `Files:` line in `tasks.md`.
### Phase C — devops posts and merges

The reviewer's handback (verdict, `findings[]`, summary text) goes to one devops wave, which posts the notes, and on `pass` only approves and merges. Reviewer writes nothing to GitLab.

6. **Return inline notes** as `findings[]` (one per `file:line`, text `<severity> <category>: <problem>. <fix>.`); devops posts them with `mcp__mcp_gitlab__save_note`, the `file:line` in the note text (e.g. `blocking correctness: missing await → race condition. Add await before db.save().`). Author is the configured user. A reply to an inline review comment goes in that comment's own thread, never as a new comment at the top of the MR.
7. **Summary note**: reviewer returns this text; devops posts it with `mcp__mcp_gitlab__save_note`:
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
   - **`pass`**: devops runs the final guard (CI green via `list_pipelines` and `get_pipeline`, merge status from `get_merge_request` shows no conflicts and approvals satisfied), then approves through `save_merge_request_review`, after which `accept_merge_request` merges with `squash: true` (default, configurable), `should_remove_source_branch: true`, and `merge_commit_message`:
     ```
     Merge !<iid> <title>

     <description summary, 3-5 lines>

     Reviewed-by: <gitlab user>
     Plan: <plan_id>
     ```
   - **`needs_changes`**: leave the MR open, the notes and the summary note above posted by devops with `save_note`, route to `implement` with `fix_list[]`. Do NOT merge. In a plan, implement commits that fix as one small commit of its own on the plan branch, its message naming the review finding ids it resolves; a commit resolving a merge conflict is allowed the same way.
   - **`blocking`**: as `needs_changes`, marked `blocking`; reroute to `brainstorm` if the root cause is unclear (architectural concern), else to `implement`.
9. **After merge** (devops, after the merge): verify the target branch updated (`mcp__mcp_gitlab__list_commits`); the source branch is deleted (MR setting); trigger devops if `target=main` AND auto-deploy is configured (project `AGENTS.md`).

### Severity

`agents/reviewer.md` § Severity is the only severity table. For `merge`: a `warning` permits `needs_changes`, never `pass`; no waiver merges a `warning` (fix it, or it was never a finding).

### Forbidden

`agents/reviewer.md` § Forbidden already covers own-work review, editing the branch, merging on `needs_changes` or `blocking`, preference severity. MR mechanics it lacks:

- Force merge with conflicts unresolved; merge without CI green (override only on a documented hotfix with user approval).
- Skipping description sections; a generic title ("update", "fix bug", "wip", "test").
- A bot or anonymous identity when the project specifies a GitLab user.

### Config

`gitlab.user` (project `AGENTS.md` or `~/.claude/gitlab-user.txt`): GitLab username + token reference for MCP; missing blocks reviewer and implement with `needs_user_input`. `merge.strategy`: `squash` (default) | `merge_commit` | `rebase`. `merge.delete_source_branch`: default `true`. `merge.require_approvals`: default 1 (the reviewer's).
