# UX rules, flow rows: motion, forms and feedback, charts
<Owner: skills/design-ui/references/ux-rules-core.md>
<Read when: a brief or a UI review concerns motion, a form, feedback or a chart>

Same source and exclusions as `ux-rules-core.md`; navigation rows sit in the catalog's Navigation block. Exit duration as a share of enter, and stagger per item: group `ux_motion` (`refs/thresholds.md`), never copied here.

## Motion

- Choose shared motion tokens by distance, complexity, platform and user context, and test that feedback stays responsive; no one duration range is universal.
- Match loading feedback to the expected wait: no flashing indicator for near-instant work, no unexplained long wait.
- Animate one or two key elements per view; arriving elements decelerate, leaving ones accelerate, and only constant-rate progress or rotation is linear.
- A state change (hover, active, expanded, collapsed, modal) animates rather than snaps; replacing content inside one container uses a crossfade.
- A screen transition keeps spatial continuity (shared element or directional slide), and direction expresses hierarchy: entering from below goes deeper, exiting upward goes back. A modal or sheet animates from its trigger.
- Parallax is sparing, respects reduced motion and never disorients.
- A press on a tappable card or button gives a subtle scale that restores on release; a drag, swipe or pinch tracks the finger in real time.
- All motion shares one rhythm from the same tokens. A fading element either completes its fade or stays visible; it does not linger nearly transparent.
- Rapid state changes cancel and replace the previous micro-interaction safely and set the final state explicitly; correctness never depends on an animation-end event.

## Forms and feedback

- Mark required fields; show a loading state and then a success or error state on submit; confirm a completed action briefly (checkmark, toast, colour flash).
- Toasts dismiss themselves after a few seconds; a destructive action asks for confirmation; a disabled element is visibly reduced, changes the cursor and carries the semantic attribute.
- An error says its cause and how to fix it and includes a recovery path (retry, edit, help link); a request timeout gives clear feedback with a retry.
- Error and success colours meet the text-contrast floor.
- Group related fields (fieldset and legend, or visual grouping); a multi-step flow shows a step indicator or progress bar and allows going back.
- Mobile inputs are tall enough for the touch target; destructive actions use the semantic danger colour and sit apart from the primary action.

## Charts and data

- Match chart type to the data: trend as line, comparison as bar, proportion as pie or donut; avoid pie or donut beyond five categories and switch to bars.
- Supplement colour with patterns, textures or shapes so series differ without colour; avoid red and green as the only pair.
- Offer a table alternative and a text summary or `aria-label` stating the key insight, since a chart alone is not readable by a screen reader; interactive points, bars and slices are keyboard-navigable and their tooltips reachable without hover.
- Show the legend near the chart, not below a scroll fold; make it clickable to toggle series; label values directly on a small dataset.
- Tooltips or data labels show exact values on hover (web) or tap (mobile); interactive chart elements have a touch area that meets the touch floor or expands on touch.
- Label axes with units and a readable scale, with ticks that are not cramped and auto-skip on small screens; time series state the granularity (day, week, month) and allow switching; use locale-aware number, date and currency formats.
- On a small screen a chart reflows or simplifies (horizontal bars instead of vertical, fewer ticks); limit density per chart and split into several charts instead of overloading one.
- Data against its background meets 3:1 and data text labels 4.5:1; grid lines are low contrast so they do not compete with the data.
- Loading shows a skeleton or shimmer, never an empty axis frame; no data shows a meaningful empty state with guidance; a failed load shows an error with a retry, never a broken chart.
- Entrance animation respects reduced motion and the data is readable at once; a very large dataset (thousands of points) is aggregated or sampled with drill-down, and drill-down keeps a back path and hierarchy trail.
- A data table supports sorting with `aria-sort` for the current state; data-heavy products offer CSV or image export; emphasise the trend over decoration, with no heavy gradients or shadows that obscure the data.
