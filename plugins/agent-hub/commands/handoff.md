---
description: "Use when the current work must continue in a fresh session or be delegated to a new agent: write a handoff note that points to existing records instead of copying them."
argument-hint: [what the next session should do]
---

# /handoff

Write a handoff for the next session.

## Steps

1. Save it to the OS temp directory, never into the workspace.
2. Point by path to content that already lives in a spec, plan, ADR, commit or diff; do not copy it.
3. Redact secrets.
4. Add a "suggested skills" section for the next session.
5. Delegating in the background: give the new agent a descriptive name and pass the note by file, never inline in the command, so the shell never runs special characters.
