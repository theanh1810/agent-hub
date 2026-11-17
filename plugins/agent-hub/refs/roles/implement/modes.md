# Implement modes — refactor, mobile, bug fix
<Owner: agents/implement.md § Role>
<Read when: `mode=refactor`, `mode=mobile`, or a task applying an analysed bug fix>

---

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

1. Write the regression test from brainstorm's failing reproduction (the first case at the task's `Test:` layer). Run it on the unfixed code: it must fail for the reason the root cause states; record it as `red_before_fix`. Green on old code does not reproduce the bug: `needs_revision`, `reason: root_cause_unconfirmed`.
2. Forcing red by editing code or data: compare against the original with python3 difflib, not bare `diff`, to prove the edit landed. No correct seam (the test would hit the same failure pattern as the call site)? Record exactly that.
3. Apply the fix; the same test passes.
4. A bug from bad data: also validate at every layer the data passes (entry point, business logic, environment guard, audit trail).
5. **Debug logs** (proposed by brainstorm, added by implement) carry a unique tag (`[DEBUG-a4f2]`) so one grep removes them.
   Temporary logging is added only by an instrumentation task that brainstorm designed; that task's last step removes every added log line, and its diff holds no logging when it closes.
6. **Close** only when the unminimised repro no longer goes red, the regression test passes (or the missing seam is recorded), tagged logs and scratch samples are gone. Put the confirmed hypothesis in the commit message.
