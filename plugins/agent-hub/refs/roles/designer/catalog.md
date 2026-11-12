# DESIGN catalog
<Owner: agents/designer.md § References>
<Read when: Workflow step 4, selecting the pattern and the component library, and whenever a `chosen_pattern.id` is checked against the catalog.>

---

Source of truth for `chosen_pattern.id`. Pick one primary pattern; combine secondary ones inside screens. A pattern outside this catalog is an invention.

## A. Information density patterns

| id | Best for | Platform | Notes |
|---|---|---|---|
| `feed-list` | Linear content stream, infinite content | web, mobile | Virtualized list, pull-to-refresh on mobile |
| `card-grid` | Browsable items with images (gallery, products) | web, mobile | `grid auto-fit minmax` web · `flex-wrap` RN |
| `master-detail` | List + selected item viewer (mail, files) | web (desktop), tablet | Two-pane; collapses to push-nav on phone |
| `dashboard-tiles` | Multi-metric overview, quick scan | web | Grid template areas; hero KPI top-left |
| `wizard-stepper` | Linear multi-step task (onboarding, checkout) | all | Progress indicator, back/next, save draft |
| `kanban-board` | Status-grouped items, drag rearrange | web, tablet | Column flex-row, virtualized columns |
| `timeline` | Time-ordered events | web, mobile | Vertical, sticky date headers |
| `inbox-triage` | Action queue (approve/dismiss) | all | Swipe actions mobile, batch select web |

## B. Navigation patterns

| id | Best for | Platform | Notes |
|---|---|---|---|
| `top-tabs` | 2-5 sibling sections at top | web, mobile | Underline indicator, swipeable mobile |
| `bottom-tabs` | 3-5 primary sections, persistent | mobile | iOS/Android native tab bar |
| `side-nav` | Many sections, hierarchy, desktop-first | web | Collapsible, app shell grid area |
| `drawer` | Secondary nav hidden until needed | mobile, web | Hamburger trigger |
| `command-palette` | Power users, keyboard-first | web, desktop | `cmd+k`, fuzzy search |
| `breadcrumb` | Deep hierarchy navigation | web | Pair with side-nav |
| `stack-nav` | Push/pop screens (mobile native) | mobile | React Navigation stack |

## C. Input patterns

| id | Best for | Platform | Notes |
|---|---|---|---|
| `form-vertical` | Standard data entry | all | Label-above-input, inline validation |
| `form-inline-row` | Tight grids, table cells | web | Compact spacing |
| `wizard-form` | Long form split into steps | all | Use `wizard-stepper` shell |
| `search-as-you-type` | Live filter / autocomplete | all | Debounced, results below input |
| `chip-multiselect` | Tags / filters | all | Wrap flex, removable chips |
| `slider-range` | Numeric filter / volume | all | Touch-friendly hit area mobile |
| `date-picker` | Date / range | all | Native input on mobile, calendar popover web |

## D. Disclosure patterns

| id | Best for | Platform | Notes |
|---|---|---|---|
| `modal-dialog` | Blocking decision, focused task | all | `z-modal` ladder, esc/backdrop close |
| `drawer-side` | Detail without losing context | all | Right-side on desktop, bottom-sheet on mobile |
| `bottom-sheet` | Mobile-first reveal | mobile | Snap points, swipe-down dismiss |
| `popover` | Anchored mini surface | web | `position` rules §2 |
| `tooltip` | Microcopy on hover/focus | web | `aria-describedby` |
| `accordion` | Many collapsible sections | all | Single-open vs multi-open |
| `tabs-inline` | Switch view within page | all | Distinct from `top-tabs` (page-scoped) |

## E. Feedback patterns

| id | Best for | Platform | Notes |
|---|---|---|---|
| `toast-snackbar` | Transient confirmation | all | Auto-dismiss, action button optional |
| `inline-banner` | Persistent page-level message | all | Severity colors, dismissible |
| `skeleton-loader` | Predictable content shape loading | all | Shimmer, no spinner on layout |
| `progress-determinate` | Known % task | all | File upload, multi-step |
| `progress-indeterminate` | Unknown duration | all | Spinner or sliding bar |
| `empty-state` | No data yet | all | Illustration + CTA + explanation |
| `error-state` | Recoverable failure | all | Cause + retry action |

## F. App shell patterns

| id | Best for | Platform | Notes |
|---|---|---|---|
| `top-bar-content` | Simple apps | all | Header + scrollable body |
| `header-sidebar-main` | Productivity / SaaS | web | CSS grid `template-areas` |
| `tab-bar-stack` | Mobile native shell | mobile | Bottom tabs + per-tab stack |
| `split-view` | Tablet / desktop large | web, tablet | Resizable panes |
| `single-screen-app` | Focused tool (calculator, chat) | all | No nav chrome |

## Decision rubric

Six steps, in order. This picks a **pattern**; the library is separate (§ Component library rubric).

1. **Platform** → navigation (§B). Mobile: `bottom-tabs` / `stack-nav`. Web SaaS: `side-nav`. Hybrid: `drawer` + responsive `top-tabs`.
2. **Content shape** → density (§A). Time-ordered: `timeline`. Equal-rank items: `card-grid`. Sequential task: `wizard-stepper`.
3. **Action** → input (§C). Dense entry: `form-vertical`. Quick filter: `chip-multiselect` / `search-as-you-type`.
4. **Reveal cost** → disclosure (§D). Blocking decision: `modal-dialog`. Non-blocking detail: `drawer-side` / `bottom-sheet`. Microcopy: `tooltip`.
5. **Feedback** → §E. Every async action maps to one of progress, toast, banner, empty, error; a missing feedback state is a blocking finding. "Disable button during async operations; show spinner or progress."
6. **Shell last** → §F, hosting the navigation of step 1.

Record rejected patterns, one sentence each. Native or system controls first; custom only when the brand needs it.

## Pattern rules

What a chosen pattern must carry.

**Navigation**
- The back button is predictable; bottom bar ≤5 items; deep links work; system gestures stay available, never blocked.
- A route change moves focus to the main content; back restores scroll, filters and typed input; a "skip to content" link exists.
- Headings h1→h6 never skip a level; breadcrumb from 3 levels deep; screens ≥1024px prefer a side bar.
- iOS uses a bottom tab bar for top-level destinations; Android uses a top app bar with a navigation icon for primary structure.
- Navigation items carry both icon and text label; the current location is highlighted by colour, weight or an indicator.
- Primary navigation (tabs, bottom bar) and secondary navigation (drawer, settings) stay clearly separate; bottom navigation holds top-level screens only, never sub-navigation; never mix tab, side and bottom navigation at one hierarchy level.
- Navigation placement is the same on every page, and core navigation stays reachable from deep pages.
- Modals and sheets offer a clear dismiss (swipe down on mobile) and are not used for a primary navigation flow.
- Search is easy to reach, with recent or suggested queries; actions that overflow the space go into an overflow menu instead of being crammed.
- A nav badge is used sparingly for unread or pending and clears after the visit.
- The navigation stack is never silently reset and never jumps to home unexpectedly.
- Dangerous actions (delete account, log out) sit apart, visually and spatially, from normal navigation items; an unavailable destination explains why instead of silently disappearing.

**Gestures**
- No critical action is gesture-only: "Don't rely on gesture-only interactions; always provide visible controls for critical actions". A swipe action carries a visible hint.

**Forms**
- Labels always visible (a placeholder is not a label); error beside its field; help text; reveal optional parts progressively.
- A control explains itself by shape, label and position; needing instruction means redesign. Remaining limits (password rules, file types) sit beside the field via `aria-describedby`.
- After a failed submit, focus goes to an error summary linking each field (none → the first wrong field), with the error kept beside the field. Errors and toasts use an `aria-live` region; a toast never steals focus.
- Validate on blur, not per keystroke; correct input type and `autocomplete`; show/hide password; read-only differs from disabled; the submit button disables while sending; long forms autosave a draft; closing a sheet with unsaved changes confirms; a delete offers undo.

**Charts and data**
- Legend and tooltip; accessible colours; pair colour with a second cue to tell series apart, never colour alone.

**Async and empty**
- Touch feedback ≤100 ms; an action over 1 s uses a skeleton rather than a blocking spinner; reserve space for late content so the layout never jumps. "An empty screen is an invitation to act."

## Component library rubric

Chooses the library implementing the pattern; output is `implement_hooks.component_lib_preference`. Read the acceptance criteria and surface, then each candidate's `MANIFEST.md` under `~/.claude/docs/design-library/{lib}/`, and score:

1. **Platform** — iOS-first: Apple HIG. Android-first: Material. Cross-platform web: shadcn / Tailwind UI. React Native: NativeWind plus platform-conditional styling.
2. **Density** — consumer marketing: Tailwind UI / shadcn. Enterprise data-heavy: Ant / Mantine. Editorial: custom plus Tailwind.
3. **Interaction** — rich primitives (combobox, command-k, drag-and-drop): Radix / shadcn. Form-heavy: React Hook Form plus Zod patterns.
4. **Existing project tech** — never add a second UI library when one is wired; extend it. This overrides the other three (house-style rule, `refs/roles/designer/sources.md`).

Emit the library, one sentence why, 3-5 components to reuse. Strong on 1-3 but losing 4 loses.

| Rationalization | Reality |
|---|---|
| "This library is nicer than the one already wired" | Criterion 4 wins; extend what exists. |
| "The async action is fast, no feedback state" | Every async action has one; missing is a blocking finding. |
