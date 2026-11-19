# Sources — read in this order
<Owner: agents/reviewer.md § Workflow>
<Read when: Workflow step 2, before the diff is opened>

---

| Order | Source | Why |
|---|---|---|
| 1 | **Spec first**: the live UC or the change's spec delta in `covers_uc` (`refs/plan-lane.md`) | opening code first is how a reviewer comments on naming and misses the business rule. Ask: is the flow clear · is each AC checkable · is an obvious exception missing |
| 2 | The task entry in the change's `tasks.md` (`refs/plan-lane.md`) | `Files:` · `Covers:` · `Done when:` · `Test:` |
| 3 | `{plan_dir}/design/{slug}/DESIGN.md` for FE work | the pattern, states and copy the diff was meant to implement |
| 4 | **The tests, before the code** | do they show intent · check behaviour, not implementation detail · carry descriptive names · would they catch a regression (`refs/roles/reviewer/finding-bar.md`, the experiment) |
| 5 | The diff | `mcp__mcp_gitlab__get_merge_request` (with its diffs), or for a task review the snapshot implement froze (`refs/roles/implement/close-task.md` § Freeze for review), `snapshot: {base, tip}`: `git diff <base> <tip> -- <files[].path>` and `git show <tip>:<path>`, or with no git the `tip` clone against `base` (pre-edit backup, or for a fix the last `tip`) with Python `difflib`; never the working tree (the next task is editing it). **Verify the diff is complete first** (below) |
| 6 | `mcp__gitnexus__impact` for a changed shared/exported symbol; `api_impact` for a route or handler file; both when applicable | who else breaks; the author may not have checked |
| 7 | `errors.yaml` | whether a prior blocking verdict has gone stale |
| 8 | claude-mem | findings already settled on this repo, so they are not re-litigated |
| 9 | Context7 (`mcp__plugin_context7_context7__query-docs`) | `security` mode: known advisories for a dependency the diff adds or bumps |

The `mcp__mcp_gitlab__` chain `merge` mode adds: `refs/roles/reviewer/merge-policy.md`.

**Read one task, not the whole plan** (`refs/plan-lane.md`). For each scenario the task's `Covers:` names, find the test that carries it and open its evidence line in the diff.

A review packet row marked `NO BASE`, a backup flagged `OLDER THAN APPROVAL`, or a case printed `not run` is a 🟠 finding.

## Verify the diff is complete before judging it

The context-mode hook rewrites `git diff` and fails silently on the broad, pathspec-less call `merge` mode depends on (empty output, exit 0, real diff not empty); read `refs/toolset.md § context-mode local patch` before gating any diff. Confirm you saw all of it by comparing a byte count taken outside the hook:

```bash
node -e 'console.log(require("child_process").execFileSync("git",["diff","<A>..<B>"],{encoding:"utf8"}).length)'
```

or read the file directly with `sed -n '1,200p' <file>`, which the hook leaves alone. A `pass` on a diff never fully read looks identical to a clean review.
