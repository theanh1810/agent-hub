# Sources — read in this order
<Owner: agents/reviewer.md § Workflow>
<Read when: Workflow step 2, before the diff is opened>

---

| Order | Source | Why |
|---|---|---|
| 1 | **Spec first**: the live UC or the change's spec delta in `covers_uc` (`refs/change-files.md`) | opening code first is how a reviewer comments on naming and misses the business rule. Ask: is the flow clear · is each AC checkable · is an obvious exception missing |
| 2 | The task record (`refs/plan-files.md § Reading one task`) | `what` · `purpose` · `solution` · `files[].why` · `acceptance_criteria` · `review_checkpoint` |
| 3 | `{plan_dir}/design/{slug}/DESIGN.md` for FE work | the pattern, states and copy the diff was meant to implement |
| 4 | **The tests, before the code** | do they show intent · check behaviour, not implementation detail · carry descriptive names · would they catch a regression (`refs/roles/reviewer/finding-bar.md`, the experiment) |
| 5 | The diff | `mcp__mcp_gitlab__get_merge_request_diffs`, or for a task review the snapshot implement froze (`refs/roles/implement/close-task.md` § Freeze for review), `snapshot: {base, tip}`: `git diff <base> <tip> -- <files[].path>` and `git show <tip>:<path>`, or with no git the `tip` clone against `base` (pre-edit backup, or for a fix the last `tip`) with Python `difflib`; never the working tree (the next task is editing it). **Verify the diff is complete first** (below) |
| 6 | `mcp__gitnexus__impact` for a changed shared/exported symbol; `api_impact` for a route or handler file; both when applicable | who else breaks; the author may not have checked |
| 7 | `errors.yaml` | whether a prior blocking verdict has gone stale |
| 8 | mem0 | findings already settled on this repo, so they are not re-litigated |
| 9 | Context7 (`mcp__plugin_context7_context7__query-docs`) | `security` mode: known advisories for a dependency the diff adds or bumps |

The `mcp__mcp_gitlab__` chain `merge` mode adds: `refs/roles/reviewer/merge-policy.md`.

**Read one task, not the whole plan** (`refs/plan-files.md § Reading one task`); the `result` judged under `result_write_back` is in that record. Per `result.ac_check` entry open each `evidence` line in the diff (at `scope: plan`, the review packet) and match each `tc_id` to a `result.commands[]` exit; an acceptance criterion with no entry is `result_write_back`.

A review packet row marked `NO BASE`, a backup flagged `OLDER THAN APPROVAL`, or a case printed `not run` is a 🟠 finding unless that task's `result` explains it.

## Verify the diff is complete before judging it (HARD)

The RTK hook rewrites `git diff` and fails silently on the broad, pathspec-less call `merge` mode depends on (empty output, exit 0, real diff not empty); read `RTK.md` § `git diff` before gating any diff. Confirm you saw all of it by comparing a byte count taken outside the hook:

```bash
node -e 'console.log(require("child_process").execFileSync("git",["diff","<A>..<B>"],{encoding:"utf8"}).length)'
```

or read the file directly with `sed -n '1,200p' <file>`, which the hook leaves alone. A `pass` on a diff never fully read looks identical to a clean review.
