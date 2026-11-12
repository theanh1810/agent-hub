# Planning and execution rationalizations

Read when a planning or plan-execution step tempts a shortcut. Each row is an excuse and what is true.

| Rationalization | Reality |
|---|---|
| "The key I need isn't in the template; I'll add one" | An unread key discards content. |
| "A count in `files` is shorter" | `files` is `{path, change, why}` entries. |
| "Closeout can wait for a later plan" | A diff-making plan carries exactly one closeout task. |
| "Layer by layer is simpler to schedule" | Vertical slices are the default; layering needs a `wave_rationale`. |
| "I'll figure it out as I go" | That's how you end up with a tangled mess and rework. 10 minutes of planning saves hours. |
| "The tasks are obvious" | Write them down anyway. Explicit tasks surface hidden dependencies and forgotten edge cases. |
| "Planning is overhead" | Planning is the task. Implementation without a plan is just typing. |
| "I can hold it all in my head" | Context windows are finite. Written plans survive session boundaries and compaction. |
| "The old plan is stale, I'll just replace it" | Unchecked tasks may be mid-build in another session. Overwriting them destroys work state that exists nowhere else. Stop and ask. |
| "I remember what Task N says" | You remember a summary. The brief has the exact values. Read it. |
| "I'll run the full suite at the end instead of per step" | Per-step runs are how you learn which step broke it. The end-of-task run is the contract, not a substitute. |
| "I read my own diff carefully; the final reviewer is redundant" | Same author, same blind spots. The reviewer is the only fresh context this run buys. |
| "Tests should pass, the change was trivial" | "Should" is not evidence. The contract requires the command and its output. |
| "The fix is obvious, no need for a failing test first" | The failing test is the only proof the finding was real and is now gone. Without it you have a diff and a hope. |

Source tags by file line of the rows above: rows 11-15 (addy planning-and-task-breakdown SKILL.md:225-229); rows 16-20 (obra executing-plans SKILL.md:310-320).
