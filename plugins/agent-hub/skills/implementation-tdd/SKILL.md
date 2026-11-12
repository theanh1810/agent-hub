---
name: implementation-tdd
description: Use when writing or modifying production code, applying an analysed bug fix, or refactoring (implement, fix, refactor, TDD, write tests for). Gives production code covered by tests that were red for the expected reason.
user-invocable: false
allowed-tools:
  - Read
  - Grep
  - Glob
  - mcp__gitnexus__api_impact
  - Bash(tools/check ruleset (package repo only))
model: inherit
---

# Implementation (TDD)

The procedure for each implement mode; rules and gates are in `agents/implement.md`. Test craft (names, mocks, fakes, layers): `skills/implementation-tdd/references/testing.md`, before the first test. Diagnosis is `brainstorm`'s.

## When to use

Any implement code change: feature, refactor, mobile screen, analysed bug fix. Not root-causing, review or E2E.

## Feature (TDD cycle)

> "NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST"

1. **Find how this repo tests**: its wrapper (`./gradlew`, `make test`) over a global tool, the command for one test, the CI command that blocks merge; never default to `npm test`.
2. **Red**: write the failing test from `acceptance_criteria`, in the layer of the case it serves (`refs/roles/planner/test-cases.md`); an integration case hits the real store (a task database from `task-db.sh`, `refs/local-postgres.md`), never a mock. One test per cycle.
   - State which production change would turn it red, and whether that is a bug or a decision.
   - Confirm it fails for the right reason (feature absent), not a typo or environment error; green at once means it checks existing behaviour: fix the test.
3. **Green**: the minimal code that passes. `mcp__gitnexus__api_impact` BEFORE saving shared code.
4. **Refactor**: structure only; behaviour unchanged, no test touched.
5. **Verify**: iterate on the narrow tests of the part changed; at the spawn's end lint, type check and the whole suite. A red test you did not cause is still named. A docs-only task runs its cases and `tools/check ruleset (package repo only)`.
6. **Self-critique**: `any` / TBD / leftover logs / hardcoded values; security boundaries validated; every `test_cases[]` entry green (gate 6).
7. **Closeout**: § Closeout.

Code written before its test is deleted, not kept "as reference".

### Rationalization → Reality

| Rationalization | Reality |
|---|---|
| "Too simple to test" | Simple code breaks; the test costs seconds |
| "I'll test after" | A test that passes at once proves nothing about the code |
| "I already tried it by hand" | A manual run leaves no record and cannot be rerun |

**Red flags**: tests batched before code · an assertion on a mock's presence · an expected value computed by the code under test · the whole world mocked (`references/testing.md`) · "all pass" with no count.

## Refactor

1. **Detect**: dead code, complexity hotspots, duplicates, weak names. Chesterton's Fence: understand WHY before deleting; unsure: leave it, file it in `extra.findings[]`.
2. **Apply (safe order)**: unused imports, dead code, renames, flatten nesting, extract patterns, reduce complexity, consolidate duplicates.
3. **Preserve behaviour**: same outputs, errors, side effects and order; old tests stay green unedited; verify after every change, revert at once on failure.
4. **Stop**: an unavoidable contract break is `needs_revision`, `reason: scope_extension_needed`; a usage you cannot confirm is left as is, never deleted on a guess.

Do not simplify code you do not understand, code about to be rewritten, or where the simpler version is measurably slower on a hot path. Refactoring plus new behaviour is two changes: split it. Over-simplification traps: inlining a helper that gave a concept a name makes the call site harder to read; merging two simple unrelated functions into one complex one is not simpler; an abstraction may exist for extensibility or testability, so check before removing it; fewer lines is not the goal, easier comprehension is.

## Mobile

React Native + Expo, Flutter; UI floors (HIG / Material, safe areas, touch targets, platform splits): `skills/design-ui/SKILL.md` § Floors, in review order. Tokens never in `AsyncStorage`: `expo-secure-store` / Keychain / Keystore. Jest + RNTL; snapshots only for stable layouts, few, every change read. TDD cycle as in `feature`.

## Bug fix (an analysed bug)

> Write → Run (pass) → Revert fix → Run (MUST FAIL) → Restore → Run (pass)

1. Write the regression test from brainstorm's failing reproduction (the task's first case). Run it on the unfixed code: it must fail for the reason the root cause states; record it as `red_before_fix`. Green on old code does not reproduce the bug: `needs_revision`, `reason: root_cause_unconfirmed`.
2. Forcing red by editing code or data: compare against the original with python3 difflib, not bare `diff`, to prove the edit landed (RTK.md:54). No correct seam (the test would hit the same failure pattern as the call site)? Record exactly that.
3. Apply the fix; the same test passes.
4. A bug from bad data: also validate at every layer the data passes (entry point, business logic, environment guard, audit trail).
5. **Debug logs** (proposed by brainstorm, added by implement) carry a unique tag (`[DEBUG-a4f2]`) so one grep removes them.
   Temporary logging is added only by an instrumentation task that brainstorm designed; that task's last step removes every added log line, and its diff holds no logging when it closes.
6. **Close** only when the unminimised repro no longer goes red, the regression test passes (or the missing seam is recorded), tagged logs and scratch samples are gone. Put the confirmed hypothesis in the commit message.

## Receiving review findings

The order and scope of a fix round are in `refs/roles/implement/sources.md` § Fix round. On top of it, per finding:
- Verify the finding against the code before touching anything; a finding the code disproves is reported with the evidence and not applied.
- State what the fix changes in plain words; skip thanks and agreement phrases.
- For a finding that asks for new code, grep the tree for a real use first; no use means report it as unused and add nothing.

## Build-check-fix and the Three-Fail Rule

- A check of your own that goes red is fixed in place and run again; this inner loop is not counted in the error-loop cap (`refs/roles/orchestrator/error-loop.md`).
- **Restore point**: the baseline recorded at the start (`agents/implement.md` Workflow step 5). A failed fix returns to it; never stack fixes on a failed attempt, never rewrite history. A step's output differing from its `expect` is `refs/roles/implement/sources.md` § The plan is the contract.
- After 3 failed fix attempts STOP and diagnose nothing: `needs_revision`, `reason: root_cause_unconfirmed`, each attempt and the first failing output quoted verbatim (`refs/roles/brainstorm/modes.md` roots causes).

## Closeout

Gate 9 of `agents/implement.md`; exit evidence: gate 6 and Workflow steps 5-6. Procedure `refs/roles/implement/close-task.md` § Closeout (steps 1-3 on every run with a diff; `detect_changes` alone is not closeout). mem0: search first, `update_memory` a near duplicate, at most three durable validated entries; `mem0: []` with a stated reason is correct.

## Gotchas

- `tempfile.mkstemp` plus `os.replace` leaves mode 0600: chmod the file back to its original mode (recorded 2026-10-01).
- Checking record pins by splitting lines and stripping indent reported a false 0 off: check byte-exact on a copy after each task (recorded 2026-10-01).
- A lock path that is an empty regular file never yields `os.mkdir`'s lock: report it rather than wait (recorded 2026-11-05).
- A removed or added frontmatter line shifts every record pin below it, and pin_resolves checks records too: fix the pins your own edit shifted (recorded 2026-10-06).
