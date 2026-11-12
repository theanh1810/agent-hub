# {Feature name} — Design

> Prose in this file is written in the reply language (core §1); headings, field labels and ids stay in English.

| | |
|---|---|
| **Plan id** | {plan_id or slug} |
| **Platform** | {web · mobile-rn · mobile-flutter · desktop · cross} |
| **Related use cases** | {UC-XXX, UC-YYY — leave empty if the task needs no spec} |
| **Status** | {draft · approved · implemented} |
| **Updated** | {YYYY-MM-DD} |
| **Three dials 1-10** | boldness {1-10} · motion {1-10} · density {1-10} — {reason for the choice, 1 sentence} |

---

## UX goal

{2-3 sentences. What the user can do once this screen exists, where it sits in the journey, and why
they need it. Write from the user's point of view, not the code's.}

## Users and context

| | |
|---|---|
| **Who uses it** | {role — end customer · operations staff · system manager} |
| **When** | {frequency, circumstances — for example "every morning, on a phone, on a construction site"} |
| **Constraints** | {existing design system · brand colours · performance budget · a11y level} |
| **Main device** | {large screen · phone · handheld scanner} |

## Flow map

**Main flow**

```
S1 {Screen name} → S2 {Screen name} → S3 {Screen name}
```

| Screen | Name | Purpose | Entered from | Goes next to | UC steps covered |
|---|---|---|---|---|---|
| S1 | | | | | UC-XXX step 1 |
| S2 | | | | | UC-XXX step 2 |

**Exception flows**

| From screen | Situation | Handling screen / state | UC exception covered |
|---|---|---|---|
| S1 | network error | S1 state `error` + retry button | |
| S2 | no data yet | S2 state `empty` | |
| S2 | login session expired | back to the login screen | |

> Every exception recorded in the UC needs a row here. If an exception is left out, state the
> reason; never drop it silently.

## Chosen pattern

**Chosen: `{id in the DESIGN catalog}`**

{1-2 sentences: why this pattern fits the user goal, the platform and the constraints above.}

**Considered and rejected**

| Pattern | Why rejected |
|---|---|
| `{id}` | {1 sentence} |
| `{id}` | {1 sentence} |

**App shell:** `{id in group F}`

## Text wireframe per screen

### S1 — {Screen name}

**Layout:** `{flex-column · flex-row · grid · stack · position-overlay · tabs · drawer}` — per `UI_RULES.md` §1 branch {which branch}

```
┌─────────────────────────────┐
│ {AppBar: title, back button} │
├─────────────────────────────┤
│ {content area — described in words} │
│                             │
├─────────────────────────────┤
│ {bottom action bar}          │
└─────────────────────────────┘
```

| Component | Variant | Role |
|---|---|---|
| | | |

**Required states**

| State | What the user sees |
|---|---|
| `empty` | {illustration + explanatory sentence + action button} |
| `loading` | {skeleton in the exact shape of the content, no spinner that makes the layout jump} |
| `error` | {cause + how to retry} |
| `success` | |
| `offline` | {only when this screen works offline} |

**User-facing text**

| Where | Content | Source |
|---|---|---|
| | | {AC-n verbatim · `draft` awaiting the user's approval} |

> A sentence already written in the UC's Acceptance criteria is copied **verbatim**, never
> rewritten into another sentence. A sentence not yet in an AC is a **draft** (`copy_draft` in the JSON):
> designer writes it, the user approves it before implement uses it (decision 28).

**Touch targets (mobile only):** at least 44pt iOS / 48dp Android
**Breakpoints (web only):** {describe how the layout changes at each breakpoint}

---

### S2 — {Screen name}

{repeat the structure of S1}

## Tokens

**Primitive**

| Group | Values | Taken from |
|---|---|---|
| Colour | `blue-600`, `red-600`, `gray-500` | {name in the project's design system · Figma node · `awesome-design-md:{name}`} |
| Spacing | `4`, `8`, `16` | |
| Type | `24/600`, `14/400` | |
| Radius | `4`, `8`, `12` | |
| Motion | `120ms ease-out`, `220ms ease-in-out` | |

**Semantic** (name → primitive)

| Name | Primitive reference |
|---|---|
| `primary` | `blue-600` |

**Component** (property → semantic)

| Component | Property | Semantic reference |
|---|---|---|
| Button | `background` | `primary` |

**State matrix** (`state_matrix`, light and dark designed together)

| Component | default | hover | focus | active | disabled | loading | error |
|---|---|---|---|---|---|---|---|
| Button | | | | | | | |

> A project that already has a design system **reuses** it; do not build a parallel value scale.
> With Figma, take values from Figma; do not guess colour codes from a screenshot.

## Accessibility criteria (a11y)

**Target level:** WCAG {AA}

- [ ] Normal text contrast ≥ 4.5:1
- [ ] A visible focus outline when navigating by keyboard
- [ ] An icon-only button has a label for screen readers
- [ ] The main flow can be completed by keyboard alone
- [ ] Respects the operating system's reduced-motion setting
- [ ] {mobile} Touch targets ≥ 44pt / 48dp

## Handoff to development

| | |
|---|---|
| **Framework** | {react · next · rn · flutter · electron} |
| **Component library** | {shadcn · mui · antd · chakra · nativewind · none} |
| **Files to create or edit** | {list, must sit inside `binding_scope`} |

## Design source

- Type: {Figma · design image · an existing screen in the app · none}
- Link / path: {…}

## Requested extra elements

| Screen | Element | Source (AC / the user's words, dated) |
|---|---|---|
| {S1} | {…} | {AC-n · "…" YYYY-MM-DD} |

## Open questions

- [ ] {a question without an answer — say which part it blocks}
- [ ] <span style="color:#d32f2f">**NEEDS ANSWER**</span> Screen {screen name} has no {element} — add it? (blocks the whole screen {screen name})

## History

| Date | Change | Who |
|---|---|---|
| {YYYY-MM-DD} | First version | designer |
