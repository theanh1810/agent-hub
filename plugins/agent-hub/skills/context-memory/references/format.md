# Context Memory — which store, and the mem0 format

## Which store a fact belongs in

Route by lifetime, not by how interesting the fact feels. Writing into the wrong store is how mem0 reached 1370 mostly dead entries by 2026-08-30 (gate statuses, one-off UI observations, paths into retired plan folders).

| The fact is | It goes in | Lifetime |
|---|---|---|
| what happened in this task: diff, commits, files, validation | `result` block of that task in its task record only (`refs/plan-files.md`); the mirror carries `status` and the `Result` block rebuilt from it (`refs/closeout.md § The result in the mirror`) | dies with the plan |
| test evidence: screenshots, console dumps, network captures | `{plan_dir}/evidence/{task_id}/` | dies with the plan |
| operational or conventional truth about one workspace | the project memory file (`skills/context-memory/SKILL.md` § Discovery order) | as long as the workspace |
| true in another project a month from now, plan deleted | mem0 | durable, cross-project |

Test for the last two: would this help in a different repo? Yes: mem0. Only here: the project memory file. Cannot finish "this is still true after the plan is archived": it is a plan `result`. Cross-project reference material lives in `~/.claude/memory/global/`, indexed in `global/INDEX.md`; session notes stay in the scratchpad.

## Never store, in either store (HARD)

- secrets, tokens, API keys, passwords
- raw logs, transient stack traces, full source files
- vague Caveman-compressed prose missing identifiers
- one-off task noise, incomplete guesses

The Zero-Mem answer "decisions only, keep the wording" means decisions are stored in the user's own words, and no raw log or transient trace ever is; the four types below are unchanged.

## mem0

### Read (bootstrap)

`mcp__mcp_mem0__search_memories(query=<repo + task keywords>)` first; `list_entities` only when scope is unclear; pull only what is relevant.

### Shape: one memory, one durable fact

Text: at most 2 sentences, self-contained for a reader with no plan, branch or session. Every `add_memory` call passes `infer: false`, so mem0 stores the text as written. Metadata, all required:

| Key | Value |
|---|---|
| `project` | a name from the existing project list, or `fleet` for a fleet-wide lesson, so one search finds it from any workspace |
| `type` | exactly one of the four below |
| `subject` | English lowercase kebab-case stable identifier used for dedup: symbol, module or topic; good `gitnexus-reindex-flags`, bad `how to reindex gitnexus` |
| `plan_id` | optional, traceability only; the memory must not depend on it |
| `user_quote` | required on an entry that records a user decision: the user's words verbatim, Vietnamese kept |
| `original_text` | on a translated entry: the text before translation |

| `type` | Holds |
|---|---|
| `architecture_decision` | a decision, its reason, what it rules out |
| `reusable_workflow` | a way of doing something that will be done again |
| `validated_root_cause` | a cause proven by reproduction, plus the rule that prevents it |
| `recurring_pitfall` | a counted lesson: a trap hit again or a user correction seen again; `candidate` at counts 1-2, `pattern` at 3 (`skills/context-memory/references/dedup.md` § Lesson counter) |

A `recurring_pitfall` also carries counter metadata; an entry without `count` is read as count 2.

| Key | Value |
|---|---|
| `count` | sightings counted so far |
| `seen` | `[{date, ref}]`, one item per sighting; a `ref` already in it is never counted again |
| `scope` | `project` or `fleet` |
| `reader` | `main`, or the role that reads the pattern |
| `stage` | `candidate`, `awaiting_approval` (a fleet draft) or `pattern` |
| `draft`, `declined`, `promoted_to` | optional: `{target, line}` of a fleet draft; the date the user declined it; the path a pattern was written to |

In `~/.claude` a lesson read by a role is `fleet` scope. `validated_finding` and `validated_test_finding` are retired: a task outcome belongs in the plan `result`.

### Never put in mem0

- a path under `docs/changes/**`
- a gate status or run date (`RED`, "on 2026-08-02")
- a one-off UI observation ("showed 63 rows")
- an error id local to one plan (`E11`)
- anything in the never-store list above

### Trust

mem0 is not a source of truth: cross-check with the graph and a file read. Never call `mcp__mcp_mem0__delete_*` without an explicit user request. A wrong memory is updated or removed, not acted on.
