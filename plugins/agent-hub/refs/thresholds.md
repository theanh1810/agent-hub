# Thresholds: master file, project copy, approval by group
<Owner: CLAUDE.md §9>
<Read when: a check, review or plan reads a vendor number (a size, time, rate or count), or a plan lists the threshold groups the user approves>

- The master is `templates/thresholds/thresholds.yaml`; a project's copy is `{workspace_root}/docs/thresholds.yaml`. An agent that needs a number reads the project copy.
- A group with `approved` set in the project copy is a gate: a number over it fails the check. Any other number (no project copy, or the group unapproved) is the master value, reported as an advisory finding and never failing a check (Q-D28-3-a).
- Ask moment: once per project, when `docs/thresholds.yaml` is absent; where it exists the question is skipped.
- Planner lists in `plan.<lang>.md` the unapproved groups the plan's checks read; the user approves per group at the plan gate (Q-D28-2-b).
- `closeout` copies the master into `docs/thresholds.yaml` when absent and stamps `approved: {by: <the user's words verbatim>, at: <date>}` on each approved group, with any value the user changed.
- Rollout and observability numbers are suggestions until approved; a number in `skills/testing-e2e/references/checks.md` stays there and is not repeated in the master.
