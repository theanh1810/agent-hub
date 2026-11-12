---
name: lark-task
description: Use when the user wants a task, project, subtask or column move created or changed in Lark (larksuite.com) under their own identity. Gives the Lark task, project or column change made under the user's own identity. Triggers on "lark task", "create lark task", "create lark project", "move lark column", "lark tasklist".
user-invocable: true
allowed-tools:
  - Read
  - Grep
  - Glob
  - mcp__lark-mcp__task_v2_task_get
  - mcp__lark-mcp__task_v2_taskSubtask_list
  - mcp__lark-mcp__task_v2_tasklist_list
  - mcp__lark-mcp__task_v2_tasklist_get
  - mcp__lark-mcp__task_v2_tasklist_tasks
  - mcp__lark-mcp__task_v2_section_list
  - mcp__lark-mcp__task_v2_section_tasks
  - mcp__lark-mcp__task_v2_customField_list
  - mcp__lark-contact__contact_v3_user_batchGetId
model: inherit
---

# Lark Task

Creates and manages Lark Tasks as the logged-in user (`user_access_token`) through the `lark-mcp` server, never as the shared app. Project = tasklist, kanban columns = status, every task from one full template. One read-only lookup, email to open_id, runs as the app (`tenant_access_token`) on a second server, `lark-contact`, because lark-mcp drops that tool in user token mode; every write stays on `lark-mcp`. One-time setup is `setup.md`, read only when the tools are missing (then only that request stops).

## When to use

The user asks for a Lark task, project, subtask, column move or task update. Descriptions follow the agent-brief shape of `templates/agent-brief/AGENT-BRIEF-template.md` inside the four fixed headings of section 3.

## 1. Preconditions

1. The session must expose lark-mcp tools, registered in snake_case by default (`--tool-name-case`/`-c`): map `task.v2.task.create` to the tool whose name ends in `task_v2_task_create`. Check the exact tool each step is about to call. `contact_v3_user_batchGetId` is called only on `lark-contact`, never on `lark-mcp` (it lists it in `-t` but drops it in user token mode). Missing: read `setup.md`, tell the user which tool and request needs it, stop that request. The granted tool lists are the two `-t` values of `setup.md` step 5.
2. Read `registry.json` (this folder) first. Ids only; shape and keys: section 6.
3. Never write an app id, app secret or token into any file.
4. Registry gaps = stop and ask, never guess:
   - `template_tasklist_guid`, `me.open_id` or any `fields.*.guid` is null: tell the user Init is needed and run Init (section 5) first; Init resumes from the registry and never creates a second template tasklist or field.
   - Unknown project KEY, or a project entry whose `tasklist_guid` is null (the placeholder shape): ask whether to create a new project; never map to the nearest key.
   - Priority or label name not in `options`: stop and ask. Create a new option only when the user explicitly asks: `customFieldOption.create` on that field guid, then record the guid.
   - Section name not in `projects.<KEY>.sections`: ask.
5. Auth or token error from lark-mcp: stop and tell the user to re-run the login command in `setup.md` Troubleshooting. Wait for the user's confirmation before any retry of a create, patch or add; on resume reuse the same `client_token`. Describe the error class only, no invented codes. An error from `lark-contact` (app token, so the user login does not fix it): stop the request that needed the lookup, describe the error class only, point to the `lark-contact` lines of `setup.md` Troubleshooting; never retry the lookup through lark-mcp.

## 2. Conventions

- Project = tasklist named `[PRJ] <name>`; registry key = the project key, e.g. `DEMO`.
- Task summary = `[KEY-n] <Verb> <object>`; `n` = `projects.<KEY>.next_n`.
- Kanban sections, in order: `Backlog`, `To do`, `In progress`, `Testing`, `Deploy`, `Done`.
- The section is the task's state; the `Status` field mirrors it with the option of the same name. A card dragged in the Lark UI changes only the section (nothing listens to the drag), so whoever dragged it sets `Status` and the completed tick by hand.
- Team process doc: `PROCESS.md` in this folder is the source; the user pastes it into Lark Docs and re-pastes after each change. A change to section 2, section 3 or Move column updates `PROCESS.md` in the same edit and tells the user to re-paste.
- Board view cannot be created by API: the user switches the tasklist to Board view grouped by section once, in the Lark UI.

## 3. Task template (every field)

| Field | Value |
|---|---|
| summary | `[KEY-n] <Verb> <object>` |
| description (max 3000 chars) | exactly these four headings: `## Context` / `## Work to do` / `## Done when` / `## Source link` |
| members | 1 `assignee` + any number of `follower` (`id` = open_id `ou_...`, max 50 per request) |
| start, due | `{timestamp: "<ms string>", is_all_day}`; both with the same `is_all_day`; start <= due; an all-day date (`is_all_day: true`) is sent as 12:00 machine-local time on that date |
| custom_fields | `Priority` single_select -> `single_select_value` = option_guid; `Labels` multi_select -> `multi_select_value` = [option_guid]; `Estimate` number -> `number_value` string, hours, one decimal, e.g. `"2.5"`; `Status` single_select -> `single_select_value` = option_guid of the option named as the task's section |
| tasklists | `[{tasklist_guid, section_guid}]` - custom field values are accepted only when the task is created with this and the field is attached to that tasklist |
| origin | `{platform_i18n_name, href:{url,title}}` for the source link; settable at create only, immutable after |
| client_token | `"lark-task-" + uuid`, 10-100 chars; generated once per intended task before the first `task.create` and reused on every retry |
| subtasks | `task.v2.taskSubtask.list` on the parent first, then `task.v2.taskSubtask.create` for the missing ones, after the parent exists; summary + assignee only (due only if the user states it); no `[KEY-n]` numbering, no section or tasklist placement |

Option names (exact):

- `Priority`: `P0 Urgent`, `P1 High`, `P2 Medium`, `P3 Low`
- `Labels`: `Frontend`, `Backend`, `Bug`, `Feature`, `Docs`, `Infra`
- `Estimate`: number, `decimal_count` 1, unit hours
- `Status`: `Backlog`, `To do`, `In progress`, `Testing`, `Deploy`, `Done` (the section names of section 2, same order)

## 4. Ask, never guess (HARD)

Ask before calling `task.create` when the user did not state the **assignee**, the **due date**, the **priority**, or the **project KEY** (when not named). Creating a project: ask project name and KEY. One decision per question.

- Assignee defaults to `me.open_id` only when the user says "assign to me" or equivalent. Any other assignee or follower: ask for the email, resolve it to an open_id with `contact_v3_user_batchGetId` on `lark-contact` (`data.emails: [<email>]`, `params.user_id_type: "open_id"`). No open_id returned: stop that request and tell the user which email returned none.
- Start is optional, empty unless stated; if both are set, start <= due with the same `is_all_day`.
- Labels and estimate are optional: empty when not stated.
- Date to ms conversion uses the machine's local timezone. An all-day date uses 12:00 local time, so its calendar date is the same in every timezone from UTC-11 to UTC+12. After `task.get`, read the returned `start`/`due` date: with `is_all_day: true` take the UTC calendar date of the timestamp (Lark returns 00:00 UTC of the date), otherwise convert to a local date. If it differs from the date the user stated, report both dates and do not patch on your own.

## 5. Procedures

**Init (once, resumable)** and **New project**: read `references/init-registry.md` and follow it step by step; it is the only statement of both procedures.

**Create task.**

1. Ask for missing items (section 4).
2. `customField.list` on the project, `customField.add` only the missing template fields (section 3), so a field added to the template after the project was created reaches it.
3. Generate `client_token` once for this request (section 3).
4. Number check: first take the lock with `mkdir registry.lock` beside `registry.json` (this folder). The directory already exists: another run holds it or a crash left it, so stop and ask the user before deleting it; never delete it on your own. Then `n` = `next_n`. Run `tasklist.tasks` on the project, all pages. While a task whose summary starts with `[KEY-n] ` exists: if the rest of its summary equals the `<Verb> <object>` about to be created, an earlier run already created this request and did not finish - `task.get` it, report that task to the user and continue at step 7 with it, creating no second task; otherwise set `n` = `n + 1` and check again.
5. Build the template (section 3) with summary `[KEY-n] <Verb> <object>`, the target section (default `To do`), and `Status` = the option named as that section.
6. `task.create`. On a timeout or network error retry with the same `client_token`; an auth error follows section 1 item 5.
7. Target section `Done` and `completed_at` is `"0"`: `task.patch`, `update_fields: ["completed_at"]`, `task.completed_at` = the current time in ms as a string (as Move column step 3). Otherwise: no call.
8. `task.get` read-back, for every task whatever its section: check every field that was set, including the section, `Status`, the completed state and the all-day date check of section 4.
9. Subtasks: first `task.v2.taskSubtask.list` on the parent; run `taskSubtask.create` only for requested subtasks whose summary is not already listed. Each carries summary + assignee, + due only if the user states it; no `[KEY-n]`, no section.
10. Write `next_n` = `n + 1` to the registry, only after steps 6-9 succeeded: until then a rerun's step 4 finds this task by its `[KEY-n] ` and resumes it. Then remove the lock (`rmdir registry.lock`). Any stop after this run took the lock also removes it before reporting; a stop because the lock already existed leaves it.

A step from 7 on that fails: stop, `task.get`, remove `registry.lock`, and report `KEY-n`, which steps ran, and the task's section, `Status` and completed state. A retry reruns Create task for the same request: step 4 finds the task and resumes at step 7, creating no second task; an auth error follows section 1 item 5.

**Move column.** Each step is decided by the target section and the task's current state, never by the section it leaves, so a rerun ends in the same state and a hand-dragged card is put right. In this order, each step only after the previous one succeeded:

0. Resolve and read. The user named `KEY-n`: `tasklist.tasks` on the project, all pages, and take the one task whose summary starts with `[KEY-n] `; none or more than one: stop and ask. `customField.list` on the project, `customField.add` only the missing template fields (section 3). `task.get`: the current section is the `section_guid` of its `tasklists` entry for this project, named through `projects.<KEY>.sections`; a guid not there: stop and ask.
1. Current section is not the target: `task.v2.task.addTasklist` with the same `tasklist_guid` and the target `section_guid`. Never `task.patch` for this: it cannot change members, reminders or tasklists. Already in the target: no call.
2. `Status` is not the option named as the target: `task.patch`, `update_fields: ["custom_fields"]`, `task.custom_fields: [{guid: fields.status.guid, single_select_value: fields.status.options[<target section name>]}]`. Already that option: no call.
3. Target `Done` and `completed_at` is `"0"`: `task.patch`, `update_fields: ["completed_at"]`, `task.completed_at` = the current time in ms as a string. Target not `Done` and `completed_at` is not `"0"`: the same call with `task.completed_at` = `"0"`. Otherwise: no call.
4. `task.get` read-back: section, `Status` and the completed state.

A step that fails: stop, `task.get`, and report which steps ran plus the task's current section, `Status` and completed state. A retry reruns Move column from step 0, which skips what already holds; an auth error follows section 1 item 5. Never undo the earlier steps.

**Update task.** `task.patch` for summary, description, start, due and custom_fields other than `Status`, with `update_fields` = exactly the changed fields and their new values in `task`. A field named in `update_fields` but missing from `task` is cleared: never name a field without setting it. For `custom_fields` only the passed values change. `Status` and the completed tick follow the section and are never patched here: a request to change `Status` is Move column to the section of that name; a request to tick or untick that names no section is asked, never guessed. Ask-never-guess (section 4) applies. Add a member with `task.v2.task.addMembers`; there is no remove-member tool, so the user removes members in the Lark UI. `origin` is fixed at create. Reminders are out of scope.

**Look-up.** `tasklist.tasks`, `section.tasks`, `task.get`.

## 6. Registry rules

Write after every create. Ids only. Never add keys outside the shape and the field-to-key map in `references/init-registry.md`; read it before any registry write other than `next_n`.

## Gotchas

- A moved task was once read back in its old column: re-read the task and compare its column before reporting a move done (recorded 2026-10-21).

## Red flags

| Thought | Reality |
|---|---|
| "The assignee is probably this person" | No open_id from the email lookup means stop and say which email returned none. |
| "The write failed, retry it" | After an auth error, no retry until the user confirms; resume with the same `client_token`. |
| "Undo the earlier steps" | A failed step stops and reports; earlier steps are never undone. |
| "Put the token in the registry" | The registry holds ids only; never a secret or token. |
