# Dispatch — briefing workers, waiting, reading what returns
<Owner: agents/orchestrator.md § Workflow>
<Read when: writing a spawn's `brief`, running workers in parallel, or main thread waiting on workers and reading their returns>

---

## The brief

- **Self-contained.** A worker gets no session history and no pasted summary of earlier tasks: "you construct exactly what they need." (One spawn once ran to 42k characters, 99% pasted history.)
- **Five things, no more:** where the task sits in the whole (one line); the brief file path ("read this first"); interfaces and decisions from earlier tasks the brief lacks; how open ambiguities were settled; the report file path.
- **Task content:** scope, goal, constraints, expected output, interfaces touched, the relevant slice of spec.
- **Exact values live only in the brief file** (numbers, fixed strings, signatures, test cases); the spawn text never copies them.
- Compressing a decision (`skills/context-compression/SKILL.md` first) never trims `plan_id`, `task_id`, `analysis_ref`, dependencies, changed files, validation status, blockers, approvals, acceptance criteria or `next_spawns[]` fields.
- Pass the brainstorm machine record path to workers, never to an independent review (it stays blind to the plan).

## Waiting on workers (main thread)

- "Never poll a wait interface with short timeouts, and never sit in one silent, open-ended wait either."
- Do internal work while waiting; when idle wait in 5-10 minute segments, one status line between, list live agents, shut down one that finished without reporting.

## When workers return

- Parallel returns: read each summary, check conflicts between them, run the whole suite, spot-check patterns (workers can be wrong the same way).
- "Done with concerns": read the concerns first.
- `in_progress` is resumed with its `remaining_task_ids[]`, not restarted.
