---
description: Use after a session to look back and propose improvements to the environment (not the code), so the next session gets it right more easily.
argument-hint: [session or plan to review]
---

# /retro

Look back at one session and propose environment improvements. Read-only: edits no code, applies nothing; candidates are listed by severity for the user to pick.

## Steps

1. Read the session (transcript, plan, errors) and the repo's existing checks (commit hooks, CI lint, types, tests) first, so nothing already built but unwired or broken is rebuilt.
2. For each task ask: could the environment make the next attempt easier to get right? A tightly constrained API, a lint rule enforcing it, a data source (progress logs, a test DB, a browser): the "pit of success".
3. Group candidates:
   - **Navigation**: pointers that help an agent find the right file
   - **Automatic checks**: deterministic checks instead of written rules
   - **Code-style rules**
   - **Global guidance too long**
   - **Tool cost**
   - **Dead sentences**: instructions the model already follows
   - **Information access**
4. A repo with no guardrail at all (no commit hook, no CI running lint, types and tests) is itself a finding, not a neutral default.
5. Present candidates by severity, each with session evidence. Propose only; do nothing outside the scope the user picks.

## Forbidden

- Proposing a rule where a deterministic check would do.
