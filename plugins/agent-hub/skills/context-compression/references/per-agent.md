# Context Compression — filter, compress, and what each agent keeps

# Step 1 — Filter (drop before compress)

Each block is walked once: drop, keep verbatim, compress prose, or handle raw output.

## Drop list (HARD — remove entirely)

- **Pleasantries and acknowledgments** ("Sure!", "Got it", "Let me", "I'll proceed"): confirmations with no new information.
- **Self-narration without progress** ("This looks correct", "As expected"): keep only a finding the next agent needs.
- **Failed tool explorations** (empty grep, wrong path, empty MCP query): keep ONLY the negative fact ("no callers found for X").
- **Repeated reads**: keep the most recent copy.
- **Stale plans**: superseded versions, unchosen candidates, drafts replaced by the final.
- **Verbose tool catalogs** already used: keep names, drop descriptions.
- **Echoed user input.**
- **Hedge runs** ("I think", "perhaps", "let me check again"): replace with assertion or fact.
- **Intermediate failed attempts**: keep the final working version plus one line "tried X, Y; both failed because Z".
- **Tracebacks beyond the root frame**: keep first 5 frames and bottom 2, drop the middle.
- **Build noise**: duplicate dependency lines, progress bars, ANSI codes (context-mode handles most; strip the rest).
- **Empty section headers.**
- **History irrelevant to the current wave.**

## Keep list (HARD — never drop, never compress to ambiguity)

- `file:line` citations; identifiers (symbols, route paths, env keys without values, service names).
- Acceptance criteria, validation commands, expected outputs.
- First root-cause error verbatim (frame and message).
- Contracts: API signature, schema field, socket event name.
- Approval gates, blockers, open questions; security findings with severity rationale.
- `plan_id`, `task_id`, `mr_iid`, `commit_sha`; `binding_scope`; `errors.yaml` entries verbatim.
- User decisions: candidate pick, plan approval, override flags.

## Decision per block (1-pass scan)

```
for each block in context:
  if block in Drop list → remove
  elif block in Keep list → keep verbatim, NEVER compress
  elif block is prose narration → mark for Caveman lite/full per fill level
  elif block is raw tool output → mark for context-mode / sandbox-to-file
  elif block is duplicate of newer block → remove older
  else → keep, evaluate next pass
```

## Filter budget per agent

| Agent | Expected drop ratio |
|---|---|
| brainstorm | 20-30% — narration drops, findings stay |
| scout | 30-40% — only patterns + file:line survive |
| implement | 30-50% — drop "thinking aloud", keep diff + test result |
| reviewer | 10-20% — findings are signal; drop only filler |
| test | 30-50% — drop snapshot prose, keep evidence path + first error |
| devops | 20-30% — drop log lines after the first match, keep cmd + path |

A long block that filtering drops by <10% is unusual: check it is not junk kept out of caution.

# Step 2 — Compress what remains

## Decision matrix

| Context | Action |
|---|---|
| Long `brainstorm` / `test` log narration | context-mode on raw output; Caveman `lite` on prose summary |
| Memory file pre-save (`~/.claude/memory/**/*.md`) | `caveman-compress <file>` (writes `*.original.md` backup) |
| Bloated MCP catalog descriptions | `caveman-shrink` (catalog only, never requests/responses) |
| Context >50% / >70% / >85% window | § Auto compression below |
| Final user response | NEVER compress — Vietnamese, normal prose, full final-response contract |

## Auto compression (HARD — every agent self-monitors)

At the start of every tool turn: filter (Step 1), check context fill, pick a mode.

| Fill | Action |
|---|---|
| <50% | filter only; no Caveman/context-mode |
| 50-70% | filter + Caveman `lite` on internal narration + compress (run bare) `git log/status`, build/test/lint logs, kubectl/docker logs |
| 70-85% | filter aggressive (+10 pts drop ratio) + Caveman `full` on prose + sandbox all raw outputs to `{workspace_root}/.cm-tmp/{task_id}/<job>.out` (`refs/artifact-layout.md § Ephemeral output`) and cite the path; never inline >30 lines; drop the prior agent's full handoff, keep its summary line + path |
| >85% | Emergency closeout: filter to the bare keep-list; tick the task's box in `tasks.md` and write the handoff summary (`refs/closeout.md § Recording What a Change Did`); `{plan_dir}/` holds no file beyond the plan files (`refs/artifact-layout.md § Where writing is allowed`); raw output stays in `.cm-tmp/{task_id}/`; save to project memory (context-memory §Project memory); return a short status and recommend a fresh session. `test` instead returns `in_progress` with `progress.yaml` and `remaining_test_case_ids[]` (`refs/roles/test/resume.md`) and writes no plan |

Fill is each agent's own reading of its window; nothing upstream reports it, so "context was fine" with no filter pass is a guess. Not optional past 70%.

## context-mode quick rules

- Verify install: `context-mode doctor`.
- `grep`, `rg`, `cat`, `find`, `ls` are excluded from the hook **on purpose**: summarising a file under inspection changes conclusions, not just token count. Never route a file read or search through context-mode. `head` / `tail` are still rewritten: use `sed -n 'A,Bp'`. Measurements: `refs/toolset.md § context-mode local patch`.
- `git diff` fails two ways under the hook and only one looks like a failure; confirm the whole diff is in front of you before gating it (`refs/toolset.md § context-mode local patch`).
- Run commands bare (`git status`, `git log`, tests, `lint`, `tsc`, builds, `docker logs`, `kubectl logs`, `curl`): context-mode compresses large Bash and MCP output in the main thread by its PostToolUse hook; subagents pass through (R19). context-mode has no wrapper subcommand (cli.mjs ALL_COMMANDS: setup, doctor, upgrade, server, mcp, hook, help).
- Use `tee` or the raw output path only if compressed output hides needed details.
- NEVER hide the first root-cause error.

## Caveman variants

Definitions: the `caveman` plugin skill § Intensity. This skill decides only where each is allowed: `lite` on handoff prose, `full` on prose at high fill, `ultra` only on non-critical prose, `wenyan` never in a safety-critical section, none on the final user response.

## What each agent must never trim

Each `agents/<agent>.md` carries that role's never-trim list beside its pointer to this skill (§ Artifact layout for every agent); that list is the authority and this skill keeps no copy.

## Memory hygiene

- Save prose with every identifier kept, and never save Caveman-compressed prose that omits identifiers.
- `caveman-compress` is for natural-language memory files only, never code, config, secrets, raw logs. What may never be stored: `skills/context-memory/references/format.md` § Never store.
- After compression, verify the `.original.md` backup exists before deleting upstream.
