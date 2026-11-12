---
paths:
  - "**/*.jsx"
  - "**/*.tsx"
---
# React (web) — and Next.js

Mechanics only. Comments: `_discipline.md` §5. Naming, function shape, structure: `agents/implement.md`. Which UI file owns what: `UI_RULES.md § Scope`. `javascript.md` or `typescript.md` applies underneath, by extension. The repo's `docs/CODE-STYLE.md` overrides.

---

## Files and components

- **One component per file, named after it in `PascalCase`** (`DeviceCard.jsx`, not `deviceCard.jsx` or `device-card.jsx`); 201 PascalCase and 4 camelCase components is a convention plus drift.
- Hooks live in `hooks/`, named `useThing.js`; a hook file exports that hook.
- A sub-component used by exactly one parent stays in the parent's file until a second parent needs it (`_discipline.md` §1).
- Follow the repo on `export default` vs named; where both exist in quantity, match the neighbouring directory.

## Rendering rules that cause real bugs

- **Never call a hook conditionally, in a loop or after an early return**; breaking it corrupts hook state.
- **A list key is a stable id from the data**: an array index silently reuses the wrong DOM node on reorder.
- **Do not derive state computable during render**: `useState` plus `useEffect` mirroring a prop is a race; compute inline.
- `useEffect` synchronises with something outside React (a subscription, timer, DOM, network), not a prop change.
- **Every effect that subscribes returns a cleanup**, or a listener, interval or observer leaks across remounts.
- Dependency arrays are complete; a deliberately trimmed one says why in a comment.
- `useMemo` / `useCallback` need a reason (a measured cost, or a dependency identity a child relies on).

## Data and state

- Server data belongs to what the repo uses (react-query, SWR, a context); never introduce a second mechanism beside it.
- Context is for what is genuinely global (auth, theme, a realtime connection); frequently-changing values in context re-render every consumer.
- A new state library is a new dependency and needs the approval gate (`CLAUDE.md` §15).

## Async in components

- Every fetch renders all three states: loading, error, empty. "Empty" is not "loading"; merging them breaks `_discipline.md` §2.
- Abort in-flight requests on unmount, or guard the state write.
- Never `async` directly on a `useEffect` callback; define an inner async function and call it.

## Styling

Follow `UI_RULES.md`. With Tailwind, compose utilities in the class list; no ad-hoc CSS file for one component unless the repo does that; no inline colour or spacing literals — use the token scale.

## Accessibility — the non-negotiable minimum

A clickable thing is a `<button>`, a navigation an `<a>` (a `<div onClick>` is unreachable by keyboard). Every input has a label, every image `alt` (`UI_RULES.md` §13; a finding, not a nit).

## Next.js

- Know which side a file runs on: in the app router a component is a server component until `'use client'` (a decision to justify, at the top).
- A secret read in a client component is published; only `NEXT_PUBLIC_*` is safe there.
- Fetch data in the server component or route handler, not in a client `useEffect` that could have been server-rendered.

## Tests

- Query the way a user does — role, label, text; a CSS-class query breaks on a restyle.
- Assert what renders, not how state got there.
- A UI change is not verified by a unit test alone: `CLAUDE.md` §9 requires `test` on a real browser with a screenshot, console errors and network failures.
