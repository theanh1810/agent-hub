# Merge policy
<Owner: agents/reviewer.md § Modes>
<Read when: `mode: merge`>

---

**`merge` reads the MR and writes nothing to GitLab.** Reviewer pulls the branch, reviews and returns the verdict, `findings[]` and the summary note text; one `devops` wave then posts the notes with `mcp__mcp_gitlab__save_note` and, on `pass` only, records the approval with `save_merge_request_review` and merges with `accept_merge_request`, as the configured GitLab user. `needs_changes` or `blocking` leaves the MR open and reroutes to implement with `fix_list[]`.

- The merge identity is the configured `gitlab.user`, never anyone else's or a bot's.
- The chain: reviewer reads with `mcp__mcp_gitlab__get_merge_request` (its diffs included); devops posts notes with `save_note`, then on pass `save_merge_request_review` and `accept_merge_request`. The step-by-step is `skills/review-checklist/references/merge.md`.
- Never rewrite, amend or rebase a commit: file the finding; implement amends.

## Commit policy (mode=merge)

Against `refs/roles/implement/close-task.md` § Commit:

| Check | Severity |
|---|---|
| Author is not the configured git/GitLab user (Claude, a bot, the default identity); implement re-commits with an explicit `git -c user.name/email` | `blocking` |
| Subject not Conventional Commits, over 72 chars, not imperative; or "Fix bugs" / "Update code" / "Misc" / "Phase 1", or past tense | `warning` |
| `Refs:` missing when a plan exists (it names `plan_id`, the wave and task ids; a fix after merge review names its review finding ids instead, `skills/review-checklist/references/merge.md` Phase B step 8) | `warning` |
| Unrelated subsystems in one commit (fixed by splitting). A plan's wave commit is exempt (R-COMMIT-WAVE), and so is a fix or conflict-resolution commit after merge review (R-MERGE-FIX-COMMIT) | `warning` |
| The subject cannot stand alone in the history; the body does not say why, or admits nothing about the approach's weak points | `suggestion` |
| Body not a bullet list with a subsystem prefix per bullet naming exact identifiers (free-form paragraph, paraphrased reference) | `suggestion` |
| `Co-Authored-By: Claude` missing on AI-assisted commits | `suggestion` |
