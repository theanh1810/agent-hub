---
name: design-ui
description: Use when changing UI components, themes, tokens or styles on web or React Native/Flutter, or when a design brief or UI diff is checked against token, accessibility and touch-target floors. Gives the token, accessibility and touch-target verdict for a UI change. Triggers on "UI change", "component", "theme", "tokens", "spacing", "colors", "design review".
user-invocable: false
allowed-tools:
  - Read
  - Grep
  - Glob
  - mcp__plugin_playwright_playwright__browser_snapshot
  - mcp__plugin_playwright_playwright__browser_take_screenshot
  - mcp__plugin_playwright_playwright__browser_console_messages
  - mcp__plugin_playwright_playwright__browser_network_requests
model: inherit
---

# Design UI

The floors a brief must meet and a diff must keep. Decisions (pattern, library, flow) are `designer`'s and arrive settled in `{plan_dir}/design/{slug}/DESIGN.md`.

## When to use

| Agent | Arrives | Uses it for |
|---|---|---|
| `designer` | eager, via its frontmatter | the token, a11y and mobile floors its brief satisfies |
| `implement` | on demand, frontend task | executing the brief: tokens, spacing, touch targets, validation |
| `reviewer` | on demand, design mode | checking the diff against the same floors |

Not for choosing a pattern, library or flow (§ Decisions made elsewhere).

## Reuse before create

1. Design library (`~/.claude/docs/design-library/`, § Design library).
2. Existing design system, Tailwind config, theme tokens.
3. Existing component props and variants.
4. CSS utilities (Tailwind, shadcn, NativeWind).
5. CSS variables and design tokens.
6. Inline style only for runtime-computed values.

## Key rules

- Never duplicate a component that exists in the library or project; never invent a size outside the existing scale.
- Reference a token for colour, spacing and shadow; never hardcode them: "Define semantic color tokens (primary, secondary, error, surface, on-surface) not raw hex in components". Tokens come from the brief or repo theme.
- One scale per shared thing (spacing 4/8, type sizes, z-index, elevation); no stray or odd values.
- Three token tiers: primitive → semantic → component; each component has a state matrix over the seven states (default, hover, focus, active, disabled, loading, error), light and dark designed together.
- Press state never shifts layout; press, focus, disabled keep contrast in light and dark; measure overlays on the real background.
- Layout primitives and React mechanics follow the file `UI_RULES.md` assigns each.

## Floors, in review order

Earlier categories outrank later ones: "Follow priority 1→10 to decide which category to focus on first".

1. **Accessibility.** WCAG AA: contrast, focus visible, labels, keyboard, reduced motion. WCAG 2.2: a sticky bar or overlay never hides the focused control; drag-and-drop has a one-pointer or keyboard alternative; login allows pasting a password. Never colour alone (add an icon or text); icon-only controls have a readable label; decorative icons beside text are `aria-hidden`.
2. **Touch.** Targets ≥44pt iOS / 48dp Android, with the hit area extended past the visual bounds when needed; ≥8px between targets; web minimum 24x24 CSS px.
3. **Performance.** Images WebP/AVIF with `srcset` and declared size; `font-display`; third-party scripts async and pruned; lists of 50+ virtualised.
4. **Style and layout.** Mobile-first with systematic breakpoints, no horizontal scroll, `dvh` not `100vh`, body text ≥16px on mobile.
5. **Type and colour.** Lines 35-60 characters on mobile, 60-75 on desktop; line-height 1.5-1.75; tabular figures for tables, prices, clocks. Dark mode is designed with light: desaturated tints, never inverted colours, contrast checked per mode.
6. **Motion.** Carries meaning, each kind with its own duration, animating only transform and opacity, respecting reduced motion; interruptible, never blocking input; exit ≈60-70% of entry; forward and back consistent. Untriggered motion stays sparing (one good entrance beats fade-slide on everything); motion answering a user action is always fine.
7. **Text handling.** A long label wraps before it truncates; truncation shows an ellipsis and the full text is reachable; long strings (URLs, IDs) use `overflow-wrap`, never `break-all` for prose; an auto-rotating carousel has a pause control and stops on focus or reduced motion.
8. **Form, navigation, chart rules** are in `refs/roles/designer/catalog.md` Pattern rules. Further UX rows: `skills/design-ui/references/ux-rules-core.md` and `ux-rules-flow.md`.

Mobile: React Native StyleSheet patterns, provider-level theme, HIG / Material, safe areas, platform splits via `Platform.OS`. Responsive widths: `agents/test.md` § Evidence storage (not re-listed here).

## Design library

Vetted patterns from public systems (Apple HIG, Material 3, shadcn, Radix, Ant, Tailwind UI); consult before inventing UI. Global at `~/.claude/docs/design-library/{lib}/`, one copy for every product (`CLAUDE.md` §19.1), never per repo.

A design-library fetch is not run by the designer: the designer returns `needs_devops` with the exact command (`npx getdesign@latest add apple`, also material, shadcn, tailwind), run from `~/.claude/docs/design-library`; devops runs it after the user approves; the designer reads the fetched files from the path devops returns.

`getdesign` unavailable → put the design doc, token JSON or Figma export into `{lib}/` with a `MANIFEST.md`:

```markdown
# {lib} design library
- tokens: colors / spacing / typography / radii / shadows / motion
- components: button / input / dialog / sheet / table / nav / ...
- patterns: form layout / empty state / error state / loading / settings page
- guidelines: when to use / when to avoid / accessibility notes
```

Look up the `MANIFEST.md` before drawing any UI.

## Decisions made elsewhere

| Decision | Home |
|---|---|
| Pattern (nav, density, disclosure, feedback, shell) | `refs/roles/designer/catalog.md` |
| Component library, platform / density / interaction fit | `refs/roles/designer/catalog.md`, against the library `MANIFEST.md` |
| Screen flow, entry and exit, failure paths, mental load | `agents/designer.md` |
| Reference `DESIGN.md` when the repo has no house style | `refs/roles/designer/sources.md` |

All four reach `implement` settled. Render the brief once; re-deriving a decision it fixes is forbidden, and a brief contradicting the requirement is `needs_design_clarification`, not resolved locally. No UX sketch file: the flow lives in the brief.

## Validation

- Web: `mcp__plugin_playwright_playwright__browser_take_screenshot`, `browser_snapshot` (a11y tree), `browser_console_messages`, `browser_network_requests`; isolated headless.
- Mobile: simulator screenshot, plus Detox / Maestro when scoped.
- Visual regression threshold and direction: `agents/test.md` § Evidence storage.
- Token audit: grep the diff for hardcoded `#`, `px`, `rgb(`, `box-shadow:` not from a token.
- Every UI-touching task goes to `test` (`testing-e2e`, `references/ui-bug.md`); screenshot critique and scoring are test's.

## Red flags

| Rationalization | Reality |
|---|---|
| "One hex here is faster than a token" | Hardcoded values drift; use the token or add it to the theme. |
| "Same component, slightly different, I'll write a new one" | Extend the existing variant. |
| "I'll skip reduced-motion, it's a small animation" | Floors 1 and 6 apply to every animation. |
| "The design brief picked a worse pattern; I'll swap it" | Escalate with `needs_design_clarification`. |
