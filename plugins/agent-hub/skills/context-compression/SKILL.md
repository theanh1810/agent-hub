---
name: context-compression
description: Use when an agent's handoff or memory file is verbose, the context window is filling up, tool output is bloated, or before deciding what may and may not be compressed. Gives the verdict on what may be shortened and what stays verbatim. Triggers on "compress context", "caveman", "rtk", "shrink output", "context pressure".
user-invocable: false
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(rtk --version)
  - Bash(rtk gain)
  - Bash(rtk git status *)
  - Bash(rtk git log *)
model: inherit
---

# Context Compression

Compression (Caveman, RTK) saves tokens. Keep every identifier the next agent needs and check a fact against the original, since compression is never a source of truth.

## When to use

Context pressure rises, or a handoff, memory file or tool output is verbose. Every passage entering the window must answer: does the agent need it, can it be assumed known, is it worth its tokens.

## Steps

1. **Filter, then compress**: drop what does not earn its tokens first; compressing junk yields small junk.
2. Run `skills/context-compression/references/per-agent.md`, read before the first tool turn: drop and keep lists, per-agent drop ratio, fill-level table, RTK rules, Caveman variants, memory hygiene.
3. Prefer a script to embedded code: a script costs its output, embedded code costs every load.
4. A sprawling document is split by layer: reference behind a pointer, branches in separate files.

## Hard rules (apply to all modes)

This section is the ruleset's only never-compress list. `CLAUDE.md` §7 and §22 point here and keep no copy.

NEVER compress:

- code blocks, inline code, config snippets
- secrets, tokens, credentials in any form
- raw logs that may hold stack traces with file:line
- security warnings, contract findings, severity rationale
- deploy commands, rollback steps, env var keys, approval gates
- the first root-cause error, verbatim, never dropped to fit a budget
- a `file:line` citation, a validation command, or its expected result
- `**/errors.yaml`, byte-exact, for brainstorm's error-batch pass

NEVER pair a compressor with the wrong input: RTK on prose, or Caveman over raw output already sandboxed to a file.

ALWAYS preserve file paths, line refs, symbols; API, socket and route names; request/response field names; acceptance criteria, validation commands and expected results; root-cause identifiers, blockers, `plan_id` / `task_id`.

Compression that introduces ambiguity in a required field: revert that field to normal prose.

## Red flags

| Thought | Reality |
|---|---|
| "Compress it all, it is only a log" | The first root-cause error and its file:line must survive verbatim. |
| "The summary is enough" | Compression is not a source of truth; keep identifiers. |
| "Caveman on the final answer saves tokens" | The final user reply is never compressed. |
