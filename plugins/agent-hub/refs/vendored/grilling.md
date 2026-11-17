# Grilling
<Owner: refs/roles/brainstorm/intake.md>
<Read when: brainstorm, on complex work or with several decisions open (the clarify gate)>

<!-- owned:begin id=mp-grilling-head -->
## What this ruleset overrides
- "Ask the whole frontier in one round" becomes a round limited to one branch (one issue) and five questions; a question downstream of an unanswered one is held back, and each return carries `decisions_left`.
- "Dispatch a sub-agent" for facts becomes a scout through `recommend_scan[]`; a fact the repo can answer is never asked.
- The session is done when no open decision changes what gets built; the rest is a ruling in the ledger. The clarify method in `refs/roles/brainstorm/intake.md` wins over this text.
- Install, fetch, update or clone steps: not followed.
- Sub-agent or browser steps: not followed.
- Files outside the artifact layout: not written.
- Searches: scout via `recommend_scan[]`.
- Memory store: claude-mem.
- Edits to `CLAUDE.md`, agents or skills: never made.
- Skill tool calls: read the vendored file of that name instead.

Upstream text (mattpocock/skills, MIT, id mp-grilling; Copyright (c) 2026 Matt Pocock):
<!-- owned:end id=mp-grilling-head -->
<!-- vendored:begin id=mp-grilling src=mattpocock/skills@5863806dd4e15c63174bee4e7515a4256792ecfa:skills/productivity/grilling/SKILL.md#L6-L30 licence=MIT -->
Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Format a round like so:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Word each question so "yes" accepts your recommended answer.

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent with a fresh context window to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.
<!-- vendored:end id=mp-grilling -->
