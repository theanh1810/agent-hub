---
description: "Use when the current work must continue in a fresh session or be delegated to a new agent: write a handoff note that points to existing records instead of copying them."
argument-hint: [what the next session should do]
---

# /handoff
<Owner: the user, by `/handoff`>
<Read when: the user types `/handoff`>

Write a handoff for the next session.

## Steps

1. Save it to the OS temp directory (`$TMPDIR`, else `/tmp`), never into the workspace; report the absolute path.
2. Point by path to content that already lives in a spec, change folder, decision record, commit or diff; do not copy it.
3. Redact secrets (keys, passwords, tokens, personal data).
4. Add a "suggested skills" section for the next session.
5. Delegating in the background: give the new agent a descriptive name and pass the note by file, never inline in the command, so the shell never runs special characters.
6. Start the final reply with a short `## ` section stating the next step: `hooks/clear_handoff.py` carries the first `## ` section of the last reply across `/clear`, and reads no other record.

<!-- owned:begin id=mp-handoff-head -->
## What this ruleset overrides
- The note stays in the OS temp directory as above; the upstream sentence about the temporary directory is the same rule, and the steps above win on any difference.
- "Skills" in the suggested-skills section means this plugin's skills and the vendored texts under `refs/vendored/`.
- Install, fetch, update or clone steps: not followed.
- Browser steps: not followed; a background delegation is step 5, run by main thread.
- Files: only the note of step 1.
- Searches: none; the note points to existing records.
- Memory store: claude-mem.
- Edits to `CLAUDE.md`, agents or skills: never made.
- Skill tool calls: read the vendored file of that name instead.

Upstream text (mattpocock/skills, MIT, id mp-handoff; Copyright (c) 2026 Matt Pocock):
<!-- owned:end id=mp-handoff-head -->
<!-- vendored:begin id=mp-handoff src=mattpocock/skills@5863806dd4e15c63174bee4e7515a4256792ecfa:skills/productivity/handoff/SKILL.md#L8-L16 licence=MIT -->
Write a handoff document summarising the current conversation so a fresh agent can continue the work. Save to the temporary directory of the user's OS (`$TMPDIR`, else `/tmp`; `%TEMP%` on Windows) - not the current workspace.

Include a "suggested skills" section in the document, naming which skills the next agent should call the Skill tool for.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.
<!-- vendored:end id=mp-handoff -->
