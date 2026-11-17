# Research
<Owner: refs/roles/brainstorm/research.md>
<Read when: brainstorm, Phases 3-4>

<!-- owned:begin id=mp-research-head -->
## What this ruleset overrides
- No background agent: the investigation runs as scouts through `recommend_scan[]`; the primary-sources rule and the cite-every-claim rule stay in force.
- No findings file in the repo: findings return in the scout's JSON evidence and brainstorm's handoff; step 3 (save where the repo keeps notes) is not followed.
- Install, fetch, update or clone steps: not followed.
- Sub-agent or browser steps: not followed.
- Files outside the artifact layout: not written.
- Searches: scout via `recommend_scan[]`.
- Memory store: claude-mem.
- Edits to `CLAUDE.md`, agents or skills: never made.
- Skill tool calls: read the vendored file of that name instead.

Upstream text (mattpocock/skills, MIT, id mp-research; Copyright (c) 2026 Matt Pocock):
<!-- owned:end id=mp-research-head -->
<!-- vendored:begin id=mp-research src=mattpocock/skills@5863806dd4e15c63174bee4e7515a4256792ecfa:skills/engineering/research/SKILL.md#L6-L12 licence=MIT -->
Spin up a **background agent** to do the research, so you keep working while it reads. Start it with a fresh context window.

Its job:

1. Investigate the question against **primary sources** (official docs, source code, specs, first-party APIs), not a secondary write-up of them. Follow every claim back to the source that owns it.
2. Write the findings to a single Markdown file, citing each claim's source.
3. Save it where the repo already keeps such notes; match the existing convention, and if there is none, put it somewhere sensible and say where.
<!-- vendored:end id=mp-research -->
