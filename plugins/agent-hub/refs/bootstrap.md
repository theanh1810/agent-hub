# Bootstrap traps
<Owner: agents/implement.md § References, row "a worktree, or counting files in a shell">
<Read when: starting a task and unsure what to load, working in a worktree, or about to count or compare files in a shell>

---

The steps are in `rules/core.md § Start`. This file keeps the skip table, the worktree rule and the traps that cost real runs.

| Task | Skip |
|---|---|
| one-file edit | claude-mem, graph, library docs |
| docs-only | graph, library docs |
| hotfix | full claude-mem search (minimal recall only) |
| reviewer `mode=independent` | claude-mem, and the memory file's `## Decisions` and `## Recent changes` |
| explanation / Q&A | everything except the file the user pointed to |

**Read order.** The error or request, the relevant `AGENTS.md`, the targeted config, route, component or service, tests, docs; search by symbol, route or error first. A repo's `AGENTS.md` / `CLAUDE.md` holds its workspace rules; read it once when the harness did not load it.

**Isolated work in a worktree.** `node_modules` is cloned by the create hook; when the hook printed `node_modules not cloned`, run the repo's lockfile install (`npm ci`, `pnpm install --frozen-lockfile`, `yarn install --immutable`) and never copy `.next` or other build output in. Run the baseline tests first; a red baseline is reported and asked about. Never implement on `main` without the user's yes.

**Blast radius before saving any exported or shared symbol:** `skills/gitnexus-flow/SKILL.md` steps 4-5. A stale graph is refreshed by whoever hit it (`skills/gitnexus-flow/SKILL.md` § Stale index). Session notes stay in the scratchpad and die with the session.

## Gotchas

- Set `ANTHROPIC_BASE_URL` or `ANTHROPIC_API_KEY` only for the one session or command that needs it, never globally (breaks auth).

- Under the RTK hook `wc -l < file` prints 0 and `diff` can call differing files identical: count and compare with `python3 -I` (recorded 2026-09-07, 2026-09-21).
- The scratchpad is shared by parallel agents: prefix script names with the task id (recorded 2026-10-01).
- Never delete by glob in the scratchpad: delete only your own prefixed files by exact name (recorded 2026-10-05).

## Red flags

| Thought | Reality |
|---|---|
| "Load everything, to be safe" | Each extra source costs window and rarely reduces uncertainty |
| "I remember the rule" | A rule you are about to judge is re-read from disk |
| "impact ran, so the route is covered" | `impact` takes a symbol, `api_impact` a route; run the one that fits |
