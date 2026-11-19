# Context Memory — dedup and timing (claude-mem write, HARD)

## Dedup before write

```
mcp__plugin_claude-mem_mcp-search__search(query = project + subject)
  hit on same {project, type, subject} -> no save, the entry stands
  changed fact on that hit             -> mcp__plugin_claude-mem_mcp-search__save_memory, text begins "supersedes #<old id>: <reason>"
  no hit                               -> mcp__plugin_claude-mem_mcp-search__save_memory
```

Three memories about one AntD `Descriptions` span bug is the failure this rule stops.

Search by `subject` before every write: claude-mem has no dedup of its own and no update tool, so this search is the only dedup.

A Vietnamese entry is never edited in place: a new English save begins `supersedes #<old id>: <reason>` and keeps the user's words in quotes; new entries are written in English.

## Lesson counter (for `recurring_pitfall`)

A lesson, a trap hit again or a user correction, is counted, not self-judged. Metadata: `skills/context-memory/references/format.md`.

1. `agent-hub lesson sight --project <project> --type <type> --subject <subject> --ref <ref> --date <date>` (a fleet lesson uses project `fleet`); the ledger `memory/global/lessons.yaml` holds the count.
2. The JSON it prints says `counted`: `false` when the sighting's `ref` is already in `seen`, so overlapping windows and re-runs never count one sighting twice; `true` appends `{date, ref}` and adds 1.
3. `new: true` (first sighting): save the lesson text once with `mcp__plugin_claude-mem_mcp-search__save_memory` (project and subject as in the ledger), counted toward the cap of three saves per run (`refs/closeout.md` § What goes into claude-mem at closeout, and what does not); over the cap the ledger still counts and the closeout block says the text was not saved.
4. An entry without `count` is read as count 2.
5. `ref` names the sighting, not the detector, so closeout and the auditor give one sighting one `ref`. A user correction is `transcript:<session_id>#<message uuid>` (`<session_id>` is the transcript file stem, `$CLAUDE_CODE_SESSION_ID` in the session that holds it; the uuid is the first user message stating the correction); a closeout that cannot resolve both leaves it uncounted, for the auditor. `<plan_id>/<task_id>` is only for a trap hit again that is not a user correction.
6. `count` 3 or more with `stage: candidate`: promotion per `refs/closeout.md` § What goes into claude-mem at closeout, and what does not. Only an interactive closeout promotes; the auditor never does.
7. claude-mem down or erroring: the ledger still counts the sighting; the text is not saved and the closeout block's `memory` reads `claude-mem unavailable, lesson <subject> text not saved`.

## Timing

Write at closeout, only after validation passed. A guess, hypothesis or unproven fix is not written: claude-mem cannot mark a fact provisional, so it would read as settled truth next session.
