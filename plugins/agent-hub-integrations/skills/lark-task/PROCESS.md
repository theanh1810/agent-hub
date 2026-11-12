# Task process on Lark

Applies to every `[PRJ] <name>` project created with the `lark-task` skill of Claude.

## 1. Six columns, in order

| # | Column | Meaning |
|---|---|---|
| 1 | Backlog | Work recorded, not yet scheduled |
| 2 | To do | Work that will be done, not started |
| 3 | In progress | Being worked on |
| 4 | Testing | Being tested |
| 5 | Deploy | Being deployed |
| 6 | Done | Finished |

## 2. The column is the truth, the `Status` field follows it

- The column holding a task is the task's real state.
- The `Status` field on a task always carries that column's name, for filtering and quick scanning in the list.
- If the two disagree: trust the column, then fix `Status` to match.
- To change `Status`: ask Claude to move the column; Claude never edits `Status` alone.

## 3. Creating a task

- Ask Claude, for example: "create a lark task for project DEMO: ...".
- A new task goes to `To do` unless you name another column; `Status` is set to that column's name. A task created straight in `Done` is also ticked complete.
- Every task follows one template: summary `[KEY-n] <Verb> <object>`; a description with 4 headings `Context`,
  `Work to do`, `Done when`, `Source link`; 1 assignee; `Priority`, `Labels`,
  `Estimate` (hours); the six progress fields of section 5.
- The start date and due date you give at creation are copied into `Planned start` and `Planned end`;
  afterwards these two fields stay unchanged, even if the start or due date moves.
- Created straight in `In progress`, `Testing`, `Deploy` or `Done`: Claude asks for the actual start date, and
  also the actual end date for `Done`; answering "today" is fine.
- A task created in Lark directly, not through Claude: fill `Planned start` and `Planned end` yourself.

## 4. Moving a column

**Ask Claude**, for example: "move DEMO-1 to Testing". Claude works in order and skips any step that already holds:

1. read the task: which column, which `Status`, whether it is ticked complete;
2. move the task to the new column;
3. set `Status` to the new column's name and record the actual dates per section 5;
4. new column is `Done`: tick complete; new column is not `Done`: untick if ticked;
5. read the task back to check.

If a step fails: Claude reports which column the task is in and its `Status`; asking for the move again brings it into line.

**Dragging a card by hand in Lark**: Lark changes only the column. After dragging, open the task and pick `Status` with
the new column's name; dragging into or out of `Done` also ticks or unticks complete. Dragged into `In progress`,
`Testing`, `Deploy` or `Done` while `Actual start` is empty: fill in the actual start date. Dragged into `Done`:
fill in `Actual end`; dragged out of `Done`: clear `Actual end`.

## 5. Tracking progress

| Field | Type | Format | Who fills it |
|---|---|---|---|
| `Progress` | number | %, 0 decimals | you, or Claude when you ask |
| `Planned start` | date | dd/mm/yyyy | Claude at creation, copied from the start date you gave; unchanged afterwards |
| `Planned end` | date | dd/mm/yyyy | Claude at creation, copied from the due date you gave; unchanged afterwards |
| `Actual start` | date | dd/mm/yyyy | Claude when the task first moves into `In progress`, `Testing`, `Deploy` or `Done`; moving back to `Backlog` or `To do` keeps it |
| `Actual end` | date | dd/mm/yyyy | Claude when the task moves into `Done`; cleared when it moves out of `Done` |
| `Progress update` | text | 'dd/mm/yyyy: <note>' | you, or Claude when you ask |

- `Progress update` keeps only the latest note: each update replaces the old note. If you ask Claude without
  giving a date, Claude writes today's date.
- To judge progress: compare `Planned end` with `Actual end`, or with today if the task is not finished.

## 6. Viewing the board

Open the `[PRJ] <name>` tasklist in Lark, choose Board view, group by section. Do this once per
project; the Lark API cannot do this step.
