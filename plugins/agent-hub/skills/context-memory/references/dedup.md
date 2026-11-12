# Context Memory — dedup and timing (mem0 write, HARD)

## Dedup before write (HARD)

```
search_memories(query = project + subject)
  hit on same {project, type, subject} -> update_memory (never a second add)
  no hit                               -> add_memory
```

Three memories about one AntD `Descriptions` span bug is the failure this rule stops.

Search by `subject` before every write: with `infer: false` mem0's own extraction-based dedup is off, so this search is the only dedup.

Updating an entry whose text is Vietnamese: rewrite it in English with `update_memory` and move the old text to `original_text`, or to `user_quote` when it is the user's words.

## Lesson counter (for `recurring_pitfall`)

A lesson, a trap hit again or a user correction, is counted, not self-judged. Metadata: `skills/context-memory/references/format.md`.

1. `search_memories(query = project + subject)`; a fleet lesson uses project `fleet`.
2. Found (a hit whose `project`, `type` and `subject` all equal the sighting's; any other hit counts as not found): read the entry's metadata from the hit (`get_memory` by id when absent). When the sighting's `ref` is not in `seen[]`, `update_memory` with the whole metadata object as read: append `{date, ref}` to `seen[]`, `count` + 1, every other key resent unchanged. When it is already there, make no call, so overlapping windows and re-runs never count one sighting twice. `update_memory` replaces the metadata, and a key left out is deleted (AF-1).
3. Not found: `add_memory(text, metadata, infer=false)` with the full metadata (`project`, `type`, `subject`, `scope`, `reader`, `count` 1, `seen` `[{date, ref}]`, `stage: candidate`). `infer=false` stores the text as written; the default lets mem0 rewrite it and split one lesson into two, which splits its count. It counts toward the cap of three adds per run (`refs/closeout.md` § What goes into mem0 at closeout, and what does not); over the cap the lesson is not counted and the closeout block says so.
4. An entry without `count` is read as count 2.
5. `ref` names the sighting, not the detector, so closeout and the auditor give one sighting one `ref`. A user correction is `transcript:<session_id>#<message uuid>` (`<session_id>` is the transcript file stem, `$CLAUDE_CODE_SESSION_ID` in the session that holds it; the uuid is the first user message stating the correction); a closeout that cannot resolve both leaves it uncounted, for the auditor. `<plan_id>/<task_id>` is only for a trap hit again that is not a user correction.
6. `count` 3 or more with `stage: candidate`: promotion per `refs/closeout.md` § What goes into mem0 at closeout, and what does not. Only an interactive closeout promotes; the auditor never does.
7. mem0 down or erroring: the lesson is not counted and the closeout block's `mem0` reads `mem0 unavailable, lesson <subject> not counted`.

## Timing

Write at closeout, only after validation passed. A guess, hypothesis or unproven fix is not written: mem0 cannot mark a fact provisional, so it would read as settled truth next session.
