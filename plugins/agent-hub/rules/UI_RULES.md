# UI_RULES — Layout & Styling Code Rules

Rules for any agent writing UI: web (CSS/Tailwind) and React Native `StyleSheet`. Pick the primitive by the problem's shape, not by habit.

## Scope

UI rules split into three files, one tier each (the only statement of the split).

| Tier | File | Owns |
|---|---|---|
| 1 | `UI_RULES.md` — this file, §1-§14 | layout primitives: which primitive a layout takes (position, flex, grid, stack), and the rules for each |
| 2 | `rules/code-style/react.md` | React mechanics: components, hooks, rendering, state, Next.js |
| 3 | `skills/design-ui/SKILL.md` | tokens, accessibility, touch targets |

---

## 1. Layout primitive decision tree

```
need to lay out elements?
├── overlap / float / pin to corner / badge on icon / modal over content
│   → position (relative parent + absolute child) | RN: position: 'absolute' on child
├── single row OR single column of items, dynamic count, even spacing
│   → flex (row or column) | RN: flexDirection
├── 2D grid (table-like, masonry, gallery)
│   → CSS grid | RN: no grid → flex+wrap or react-native-super-grid
├── vertical stack with consistent gap (forms, lists, settings rows)
│   → flex column + gap | RN: flex column + marginBottom OR a Stack component
├── center one item in container
│   → flex + justify-center + items-center (1 child) | RN: justifyContent + alignItems
├── push items to opposite ends (nav, toolbar)
│   → flex + justify-between
├── responsive multi-column that collapses on mobile
│   → grid template-columns with auto-fit minmax | RN: flex+wrap with width %
├── floating element follows scroll
│   → position: sticky (web only) | RN: ScrollView + custom logic
└── full-bleed background + centered content column
    → container with max-width + mx-auto, background on parent
```

## 2. Position rules

`position: absolute` only for: an overlap (badge, tooltip, dropdown panel, modal, toast) · pinning to a parent's corner (close button, FAB) · a popover anchored to its trigger · a decorative overlay (skeleton shimmer, focus ring).

**HARD**:
- The parent of an absolute child MUST be `position: relative` (or fixed/sticky/absolute); set it explicitly on the intended parent, never assume the root.
- `z-index` only inside the stacking ladder of §6: pick the nearest ladder level, because a bare `z-index: 9999` is forbidden.
- `position: fixed` only for viewport-anchored UI (sticky header, FAB, modal backdrop); document why.
- Never use absolute to "fix" flex misalignment; fix the flex.

## 3. Flex rules

- Row (toolbar, button group, chip list) → `flex flex-row`; stack (form rows, list items, settings) → `flex flex-col`; even spacing → `gap-*`, never margin between children.
- Items push apart → `justify-between`; cluster → `justify-start` + `gap`. Cross-axis → `items-center` for most UI, `items-start` for text+icon where the icon should not grow.
- Child grows → `flex-1` (web) / `flex: 1` (RN); fixed → `shrink-0`. Wrap → `flex-wrap` + `gap`.
- Keep flex nesting to 3 levels and extract a component beyond that; do not nest flex more than 3 deep.

**RN specifics**: the default `flexDirection` is `column` (web: `row`), so set it explicitly · `gap` works in modern RN, fallback `marginEnd`/`marginBottom` on children · `flex: 1` on a parent and child needs the parent to have a height (avoid in scrollables).

## 4. Grid rules

Use CSS grid (web only) for a true 2D layout (dashboard cards, gallery, calendar), template areas (app shell: header / sidebar / main / footer), and auto-responsive columns `repeat(auto-fit, minmax(280px, 1fr))`.

**HARD**: use flex for a single row or column, never grid · `grid-template-areas` for an app shell beats nested flex · keep grids within 2 levels, never nest grids 3 levels · RN has no grid: `flex-wrap` + percentage widths, or a grid lib.

## 5. Stack / Spacing

- Vertical rhythm from the token scale (`gap-2 | gap-4 | gap-6 | gap-8`): pick the nearest token step, never `gap-[7px]`. Sections: `space-y-{token}` on the parent or `gap` on a flex column.
- Padding for component internals; margin only for inter-component spacing the parent controls via gap.
- Forbidden: margin-collapse hacks; negative margins to "pull up" (use grid/flex alignment).

## 6. z-index ladder (HARD)

Named tokens, not bare numbers, defined in the theme config / Tailwind extend.

| Layer | Token | Range | Examples |
|---|---|---|---|
| base | `z-base` | 0 | normal flow |
| raised | `z-raised` | 10 | cards on hover |
| dropdown | `z-dropdown` | 100 | menus, comboboxes |
| sticky | `z-sticky` | 200 | sticky headers/footers |
| overlay | `z-overlay` | 300 | drawers, side panels |
| modal | `z-modal` | 400 | dialogs |
| popover | `z-popover` | 500 | tooltips above modals |
| toast | `z-toast` | 600 | notifications |
| top | `z-top` | 9999 | reserved for last-resort full-screen |

## 7. Sizing & overflow

Width `100%` or grid/flex auto; pixel widths only for icons, avatars, fixed columns · avoid fixed pixel height on content containers (use `min-h-*` for a floor) · overflow explicit (`overflow-hidden | auto | scroll`), since the default leaks shadows and dropdowns · `aspect-video | aspect-square | aspect-[16/9]` over manual height math.

## 8. Text

Wrap by default; truncate only when needed (`truncate`, `line-clamp-{n}`), with a tooltip for important data · long German or Vietnamese words → `break-words` · `tabular-nums` for numbers in tables.

## 9. Forms

Each field a flex column: label → input → helper → error · inline pairs (first/last name) in a flex row · inline validation below the input with `aria-invalid` + `aria-describedby` · submit at the bottom-right (LTR), full-width on mobile. Further form and feedback rows: `skills/design-ui/references/ux-rules-flow.md`.

## 10. Tables

`<table>` only for true tabular data · sticky header (`position: sticky; top: 0` on `<thead>` cells + `z-sticky`) · truncate cells with a tooltip on overflow · below 768px switch to a card list.

## 11. Animation

Design-system motion tokens (duration, easing), never `transition: all 1s` · `transform` and `opacity` only, never `width/height/top/left` (layout thrash; use `transform: scale`) · respect `prefers-reduced-motion`. Exit duration as a share of enter, and stagger per item: group ux_motion (`refs/thresholds.md`); further rows: `skills/design-ui/references/ux-rules-flow.md`. Layout and type rows: `skills/design-ui/references/ux-rules-core.md`.

## 12. Mobile (RN) specifics

`SafeAreaView` (or `useSafeAreaInsets`) around every screen · touch targets ≥44pt iOS / 48dp Android via min `width`/`height`; on web at least 44x44 CSS px · `Pressable` over `TouchableOpacity` in new code · `ScrollView` for short content, `FlatList` for ≥20 items · `KeyboardAvoidingView` (`padding` iOS, `height` Android) around forms · `Platform.OS` splits only where behaviour genuinely differs.

## 13. Anti-patterns

`position: absolute` to align inside flex; nested grids 3+ levels; bare `z-index: 9999` · a margin chain (`mt-4 mb-4 mr-2 ml-2`) instead of `gap`; fixed `height: 600px` on a content container; inline color or spacing values · a `<div>` chain for what should be `<button>` / `<a>` / `<nav>` · RN `flex: 1` on a child of `ScrollView` content (collapses) · animating `width`/`height`; truncating important data without a tooltip.

## 14. Decision shortcut (when stuck)

Pick the simplest primitive for THIS layout: tied → flex (most portable between web and RN); any overlap → position; a genuine 2D grid → grid; start from flex and move to absolute only when something overlaps, never absolute by default.
