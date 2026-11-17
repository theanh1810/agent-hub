# UI bug fix

A bug fix on user-visible surface is done only when the `test` agent confirms it in a real browser or on a device. A type-check, a lint pass or "the diff looks right" is not evidence.

## Applies to

Any fix that modifies a component (React, Vue, Svelte, RN, Flutter), stylesheet, theme token or CSS variable, route, page or screen layout, modal, dialog, drawer or overlay, form input, validation display or error toast, or a mobile screen, nav stack or safe-area padding. In doubt, it counts.

## Flow

The order is the `bug` row of `refs/lanes.md`, the routing source of truth. Reviewer skips only on the exemptions of `refs/lanes.md` § Reviewer exemptions; "no security or contract surface touched" is not one.

## What `test` produces

- **Browser**: a screenshot before and after (`mcp__plugin_playwright_playwright__browser_take_screenshot`); the accessibility tree (`browser_snapshot`), the primary inspection; a console scan with zero new errors (`browser_console_messages`); a network scan with no new 4xx or 5xx (`browser_network_requests`); an a11y score not below the pre-fix score (`npx lighthouse <url> --only-categories=accessibility --output=json --quiet --output-path={workspace_root}/.cm-tmp/{task_id}/lighthouse-a11y.json`, read `categories.accessibility.score`); several viewport widths when layout changed, from the closed list in `agents/test.md` § Evidence storage.
- **Mobile**: a simulator screenshot before and after; a Detox or Maestro flow covering the broken interaction; a reset between flows; device logs (`adb logcat`, Xcode crash logs); HIG / Material adherence, safe areas, touch targets at least 44pt iOS / 48dp Android.
- A visual comparison against the baseline at the threshold and direction in `agents/test.md` § Evidence storage.
- A pass/fail summary mapped to the bug's reproduction steps, with evidence under the field names of `agents/test.md` § Output.

Every artefact is ephemeral under `{workspace_root}/.cm-tmp/{task_id}/` (tree: `agents/test.md` § Evidence storage). A UI hotfix still runs a smoke `test` (snapshot and console): fewer flows, never skipping the agent.

## Closeout

- A recurring UI flake that cost a real error loop: claude-mem, `type: recurring_pitfall`, error text verbatim (`skills/context-memory/SKILL.md`).
- A stable visual baseline: a file at `docs/reviews/baselines/{repo}-{route_slug}/{viewport}.png`, promoted only after a green run (`agents/test.md` § Evidence storage).
- Workspace-local truth the run established: the project memory file, never a path written into claude-mem.

## Red flags

| Thought | Reality |
|---|---|
| "Lint and unit tests pass, so it is fixed" | Only `test` evidence closes a UI bug. |
| "The change is obvious, skip test" | Obvious changes are where regressions hide. |
| "implement already checked it" | An implement-side claim never replaces `test` evidence. |
| "Compress the log" | Never hide the first console or network error. |
