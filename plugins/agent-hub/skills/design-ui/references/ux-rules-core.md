# UX rules, core rows: accessibility, touch, performance, layout, type
<Owner: skills/design-ui/SKILL.md § Floors>
<Read when: a design brief or a UI review needs a row the floors of SKILL.md lack; each row below is absent from the floors and from `refs/roles/designer/catalog.md` Pattern rules>

Source: the ui-ux-pro-max quick-reference rule set, residual rows only. Rows that would make an agent choose a visual style, a colour scheme, a typeface or wording are not here: those come from the brief. Type and motion numbers live in groups `ux_type` and `ux_motion` (`refs/thresholds.md`), never copied here.

## Accessibility

- Meaningful images carry a text alternative; tab order matches visual order and every control works from the keyboard; the system's own shortcuts are kept and a drag has a keyboard alternative.
- Support the system text-size setting; the layout does not truncate as text grows.
- Reading order is logical for a screen reader, and a control's hint says what it will do.
- A modal and every step of a multi-step flow offers a cancel or back path.
- The focus indicator is judged by area and by contrast against its surroundings, not only by being visible; at the enhanced level the whole focused component stays visible.
- A repeated help mechanism keeps its relative position across a page set; information already given in a process is reused, not asked again.
- A changed count or status is announced as one complete phrase without moving focus, through one appropriate live region.

## Touch and interaction

- A primary interaction works by click or tap, never by hover alone; clickable web elements show the pointer cursor; `touch-action: manipulation` removes the tap delay.
- Prefer vertical scroll on main content and avoid horizontal swipe there; use the platform's standard gestures and do not redefine them.
- A press shows visual feedback (ripple or state layer); haptics confirm important actions and are used sparingly.
- A tap never needs pixel precision on a small icon or a thin edge; keep primary targets clear of the notch, the gesture bar and screen edges.
- A drag starts only after a movement threshold, so a slip does not drag.

## Performance

- Prioritise above-the-fold styles; split code by route or feature and load non-hero components on demand; preload only the critical fonts.
- Batch layout reads before writes; keep per-frame work within the frame budget and heavy work off the main thread.
- Debounce or throttle high-frequency events (scroll, resize, input).
- Show offline state with a basic fallback; offer a lighter mode (smaller images, fewer animations) on a slow network.

## Layout and responsive

- The viewport meta sets `width=device-width, initial-scale=1` and never disables zoom.
- Component spacing is comfortable for touch: not cramped enough to cause a mis-tap.
- Desktop content has one consistent maximum width.
- A fixed bar reserves padding so content beneath is not covered; avoid a nested scroll region inside the main scroll.
- The layout stays readable and operable in landscape; on mobile the core content comes first and secondary content folds or hides.
- Hierarchy comes from size, spacing and contrast, never from colour alone.
- Pick a badge, status tag, filter chip or removable value by its meaning; essential labels stay available and an unavoidable truncation is disclosed to pointer and keyboard users. A chip collection wraps before its labels shrink, and a `+n` summary is an operable disclosure, not hidden values.
- Each screen has one primary action; secondary actions are visibly subordinate. Prefer the platform's native controls over custom ones unless a requirement calls for custom.

## Type and colour

- Use the platform type system (Dynamic Type styles on iOS, type roles on Material) and let weight reinforce hierarchy.
- Text is darker than its ground in light mode; respect the platform default letter-spacing and avoid tight tracking on body text.
- Whitespace groups related items and separates sections on purpose.
- A short heading may use balanced wrapping as a progressive heuristic; natural wrapping stays readable and no blanket non-breaking spaces glue final words.
