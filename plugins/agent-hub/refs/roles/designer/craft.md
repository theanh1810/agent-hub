# Design craft — ideas, copy, anti-default rules, page frame
<Owner: agents/designer.md § References>
<Read when: Workflow steps 3 and 5 for any new screen or page; the pre-handoff list before step 7 on a mobile or native app. Token, a11y, touch and motion floors are `skills/design-ui/SKILL.md`, not here.>

---

A brief states decisions a stranger could build from. Each rule is a decision the brief must record or a default it must not fall into.

## Idea and content

- Write the idea as one sentence: "[a thing of this subject] becomes [a layout device]" ("'Clean and modern' is not an idea."). Rival test: put the nearest competitor's name in; if it still holds, the idea belongs to the industry.
- List 8-12 things only this client has (names, addresses, constraints, materials, rituals) before drawing; they are the source of ideas.
- Write the page as claims with evidence, one line per section; a section without a claim is deleted.
- The first screen answers the viewer's first question in large type; every section a viewer looks for has its own heading and a place in navigation.
- Each page has one thing a viewer can do or that differs each visit, from real content, usable by finger on a phone, with a no-script fallback.
- Write each section in full (a whole menu, every room, what a price includes); a thin section is why a clean page loses to a full one.
- Never invent proof (customers, quotes, reviews, press, figures); sample content is listed in the handoff for confirmation.

## Copy

- Designer drafts the UI copy (a plain-text copy deck before building; headlines ≤2 lines at every width); the user approves it: AC-fixed copy is `ac_fixed` and verbatim, the rest is `draft` and goes out as `needs_user_input`.
- A button says what happens ("Save changes", not "Submit"); one action keeps one name through the flow; an error says what is wrong and how to fix it, without apologising; an empty screen invites action.

## Screens with no design source

This section applies only when no design source exists (`refs/roles/designer/sources.md`); with a source, fidelity wins.

- Fix these layout tells in your own draft before returning: more than one section per screen, no word budget per screen, captions under images, credits longer than one line.
- Report these copy tells with a proposed rewrite for each, marked `draft` and awaiting the user's approval, never applied on your own: overused em dashes and exclamation marks, default-cast names, headings built from two fragments or a number pair, virtue words, response-time promises.

## Page frame

- Equal outer margins; a section whose text fills the left half has an image, column or list in the right; no blank run taller than half a screen; the gap between sections exceeds every gap inside one.
- Name each section's layout in one word (split, list, full-bleed, grid…); the same word twice in a row or three times on a page shows a template.
- Removing decoration must not leave a hole filled by other decoration: use larger type, enough content, an on-subject photo or a flat colour block.

## Against the default look

Machine-made interfaces converge (cream + serif + terracotta; black + one neon; newspaper layout with hairlines; identical SaaS cards with grey shadow): "they are defaults rather than choices, and they appear regardless of subject". Each choice needs a reason from this brief.

- Avoid the tells: gradient text, glass blur in many places, glowing buttons, three identical icon feature cards, emoji as icons, small uppercase labels on every heading, a "New/Beta" badge on top, one highlighted word in a headline. Use the project's real palette, never default purple or indigo. Each tell found in a screenshot is reported by `test` as a finding (§ Visual critique); the designer's brief avoids them and never bans a tell by name.
- "Visual structure is information.": borders, numbering, rules and labels appear only when they encode real content; 01/02/03 only for a true sequence.
- One type family, or two clearly different; a clear scale; ≥3 times from body to headline; ≤5 sizes; no paragraph wider than ~75 characters.
- "Spend your boldness in one place.": one memorable move, the rest quiet; the boldness dial says how loud.
- Real photos replace grey boxes and fake dashboards; each image does one job. One consistent SVG icon set (same stroke, same radius).
- Two passes: sketch a short plan (4-6 named colours, type roles, layout ideas in words, principles), "review that plan against the brief before building", fix whatever matches a default and record the change.

## Redesigning an existing page

Capture and measure the current page first; keep its stack, content and what works; never change the framework; order by large effect, small risk.

## Visual critique — criteria only, run by test

Screenshot critique and scoring belong to `test` (user decision, 2026-10-26); designer takes no screenshots, the brief carries the criteria:

- "Judge only the pictures. If a problem is visible in a screenshot, it is real, whatever the code says." Widths 1440 / 768 / 390, production build included.
- Look 1 second, then 5; squint for 2-3 large blocks; cover the logo and ask whether it belongs to a rival; count left-edge positions (2-3 is good); accent colour in few places; nothing overlaps a headline or button at any scroll position; no horizontal scrolling row on a phone.
- Stranger test: from the first screen alone, a newcomer can say what this is, who it is for and what to do next; a title that makes sense only after scrolling fails. Space and frame: the gap between sections is clearly larger than any gap inside one; no hole beside a short column or under a removed decoration; left and right margins match; no section keeps its text in one half and leaves the other empty; no stretch of nothing taller than half a screen. Colour: name which colour holds most of the surface, which supports and where the accent sits. Sameness: give each section's layout one word (split, list, grid, statement, full-bleed); the same word twice in a row, or three times on a page, is the template showing. Phone: its own crop and line breaks, not the desktop page squeezed. Fullness: each desktop screen reads as composed, not a narrow column of small text with dead ground either side; a page that could pass for an unfinished wireframe is underbuilt. Substance: every section the brief asked for gives its information completely at a readable size, and the primary action is a real button on the first screen.
- AI tells are reported as findings with where each appears and never banned or auto-replaced. Beyond the avoid list above: a soft grey shadow under every card; a near-black ground with one neon accent and a glow; a bento grid of rounded tiles as the feature section; a floating blurred pill navigation; a decorative status dot ("live", "available"); the same fade-and-rise on every block, hover lift on every card, bounce easing, meaningless infinite loops; monospace micro-labels; thin hairline rules and 1px outlined boxes everywhere; design-tool chrome as ornament (crosshairs, crop marks, dashed guides); agency meta strings (local time, coordinates, version stamps, middle-dot strings); a headline that is a full sentence over three or four lines; the stock section order hero, logos, features, testimonial, pricing, call to action; everything centred; one medium border radius on every element; invented social proof (logos, quotes, star rows, "10,000+ teams"); genre copy (unlock, seamless, supercharge, "not just X, it's Y", three-part headlines, "Get started" as the only label); a "→" appended to link text; lorem ipsum; uniform padding everywhere; uniform stock card grids.

## Pre-handoff (mobile and native)

Before returning: icons, touch feedback, contrast in light and dark, safe areas, accessibility; try 375 px and landscape, the largest system font size, reduced motion; decorative icons beside text are `aria-hidden`.

| Rationalization | Reality |
|---|---|
| "Clean and modern is the idea" | It is every competitor's idea; apply the rival test. |
| "A few sample testimonials make it feel real" | Invented proof is forbidden; list sample content for confirmation. |
| "The AC doesn't fix this label, so I'll just ship mine" | Draft it, mark `draft`, return it for approval. |
