# Stale verdict refresh
<Owner: agents/reviewer.md § Gates>
<Read when: `errors.yaml` has `meta.last_review_loop != meta.error_loop_count`>

---

A stale `needs_changes` or `blocking` review blocks work already fixed. On every spawn read the `meta:` block at the head of `errors.yaml`. When `meta.last_review_loop != meta.error_loop_count`, re-run the task-mode scope over the same diff and refresh the verdict.

- The stale review file is **replaced**, not appended; the old verdict moves to a `## Superseded (YYYY-MM-DD)` block at the end.
- Update `meta.last_review_loop` on success.
