# Domain Modeling
<Owner: agents/brainstorm.md § References>
<Read when: brainstorm, when a term is new or conflicts with the glossary, when writing spec deltas, at spec-convert>

<!-- owned:begin id=mp-domain-modeling-head -->
## What this ruleset overrides
- Glossary file: write `openspec/glossary.md` when the project has `openspec/`, else `docs/glossary.md`. The format is in `refs/vendored/glossary-format.md`. Only brainstorm writes it, and it writes each settled term before returning.
- Decisions go to the `## Decisions` part of the change's `design.md`, not to `docs/adr/`. ADR-FORMAT.md is not vendored; the three-part test for recording a decision stays in force.
- A project with `openspec/` gets no `GLOSSARY.md`, no `GLOSSARY-MAP.md` and no new file under `docs/adr/`; an existing `docs/adr/` stays readable as history. A workspace without OpenSpec (the `.claude` folder, the agent-hub repo) keeps `docs/adr/` with `templates/adr`.
- The file-structure diagram and every `GLOSSARY.md` name below read as the glossary file above; the lazy-create rule applies to it.
- Install, fetch, update or clone steps: not followed.
- Sub-agent or browser steps: not followed.
- Files outside the artifact layout: not written.
- Searches: scout via `recommend_scan[]`.
- Memory store: claude-mem.
- Edits to `CLAUDE.md`, agents or skills: never made.
- Skill tool calls: read the vendored file of that name instead.

Upstream text (mattpocock/skills, MIT, id mp-domain-modeling; Copyright (c) 2026 Matt Pocock):
<!-- owned:end id=mp-domain-modeling-head -->
<!-- vendored:begin id=mp-domain-modeling src=mattpocock/skills@5863806dd4e15c63174bee4e7515a4256792ecfa:skills/engineering/domain-modeling/SKILL.md#L6-L74 licence=MIT -->
# Domain Modeling

Actively build and sharpen the project's domain model as you design. This is the *active* discipline: challenging terms, inventing edge-case scenarios, and writing the glossary and decisions down the moment they crystallise. (Merely *reading* `GLOSSARY.md` for vocabulary is not this skill: that's a one-line habit any skill can do. This skill is for when you're changing the model, not just consuming it.)

## File structure

Most repos have a single context:

```
/
├── GLOSSARY.md
├── docs/
│   └── adr/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
└── src/
```

If a `GLOSSARY-MAP.md` exists at the root, the repo has multiple contexts. The map points to where each one lives:

```
/
├── GLOSSARY-MAP.md
├── docs/
│   └── adr/                          ← system-wide decisions
├── src/
│   ├── ordering/
│   │   ├── GLOSSARY.md
│   │   └── docs/adr/                 ← context-specific decisions
│   └── billing/
│       ├── GLOSSARY.md
│       └── docs/adr/
```

Create files lazily: only when you have something to write. If no `GLOSSARY.md` exists, create one when the first term is resolved. If no `docs/adr/` exists, create it when the first ADR is needed.

## During the session

### Challenge against the glossary

When the user uses a term that conflicts with the existing language in `GLOSSARY.md`, call it out immediately. "Your glossary defines 'cancellation' as X, but you seem to mean Y. Which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'account': do you mean the Customer or the User? Those are different things."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: "Your code cancels entire Orders, but you just said partial cancellation is possible. Which is right?"

### Update GLOSSARY.md inline

When a term is resolved, update `GLOSSARY.md` right there. Don't batch these up: capture them as they happen. Use the format in [GLOSSARY-FORMAT.md](./GLOSSARY-FORMAT.md).

`GLOSSARY.md` should be totally devoid of implementation details. Do not treat `GLOSSARY.md` as a spec, a scratch pad, or a repository for implementation decisions. It is a glossary and nothing else.

### Offer ADRs sparingly

Only offer to create an ADR when all three are true:

1. **Hard to reverse**: the cost of changing your mind later is meaningful
2. **Surprising without context**: a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off**: there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR. Use the format in [ADR-FORMAT.md](./ADR-FORMAT.md).
<!-- vendored:end id=mp-domain-modeling -->
