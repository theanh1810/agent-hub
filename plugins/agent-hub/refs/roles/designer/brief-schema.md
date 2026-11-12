# The design brief — evidence, shape, handoff, artifacts
<Owner: agents/designer.md § References>
<Read when: Workflow step 7, writing the brief · any file is about to be written.>

---

## Evidence (HARD)

Every claim in the brief carries its evidence; a claim with none is an invention.

| Claim | Evidence |
|---|---|
| Pattern choice | the catalog `id`, plus rejected ids with one sentence each |
| Layout primitive | the `UI_RULES.md` §1 branch that selects it |
| Token | the design system's name for it, a Figma node, or a reference origin; never a hex guessed from a screenshot |
| Flow step | `covers_step: "UC-042 step 2"`; a screen with no step in a spec-bound task is missing from the spec or should not exist |
| Copy shown to the user | quoted verbatim from the AC; otherwise a `draft` the user approves |
| Dials | the three 1-10 values (boldness, motion, density), with the reason |

## Two shapes, one brief

Template and JSON carry the same decisions: flow table = `information_architecture`, per-screen wireframe = `screens_detail[]`, token tables (primitive, semantic, component) = `tokens {primitive: {<color|spacing|typography|radius|motion>: {<primitive name>: <raw value>}}, semantic: {<semantic name>: <primitive name>}, component: {<component>: {<property>: <semantic name>}}}`, state-matrix table = `state_matrix {<component>: {<state>: <semantic or component token reference, or a one-line rule>}}` with exactly the seven state keys default, hover, focus, active, disabled, loading, error on every component and `n/a` where a state does not apply (light and dark designed together), dials = `design_dials`, copy deck = `copy_draft`, a11y checklist = `accessibility_floor`. They agree field for field; a disagreement means the brief is broken. A slot the template lacks (dials, copy draft) is added under the nearest heading.

## DESIGN.md

Follows `templates/design/DESIGN-template.md`: quick-info table (dials included) · UX goal · users and context · flow diagram with a `covers_step` column · chosen pattern with rejected alternatives · text wireframe per screen (layout, components, required states, copy) · tokens with origin · a11y checklist · implementation handoff · open questions · history. One per slug, in Vietnamese (implement and the user both read it).

With a design source (`refs/roles/designer/sources.md` Design source fidelity) both shapes carry three more fields: `design_source {kind: figma|image|existing_screen|none, ref}` (the design-source section), `requested_elements[] {screen, element, source}` (the requested-elements section), `red_questions[] {id, screen, missing_element, question, status, answer}` (the red `NEEDS ANSWER` lines of the open-questions section). Each `screens_detail[].components[]` entry carries `origin: source|requested`, and no other element appears. A DESIGN.md with no source skips the fidelity check and says so.

## Handoff to implement

Implement consumes `design_brief_path`, `chosen_pattern.id`, `screens_detail[]`, `tokens`, `state_matrix` and renders ONCE; a mismatch gets at most 2 retries, then `needs_design_clarification`. A pixel-tweak loop past 2 retries is forbidden. `implement_hooks.files_to_create_or_touch` sits inside the allowed scope.

## Artifact layout

| Writes | Path | Naming |
|---|---|---|
| Design brief | `{plan_dir}/design/{slug}/DESIGN.md`; with no change id yet, `docs/brainstorm/{slug}/design/DESIGN.md` | one per slug; `{slug}` kebab-case with repo or product prefix, names the feature not the screen |
| Reference images the brief cites | `{plan_dir}/design/{slug}/assets/` | describes what it shows (`alert-table-empty-state.png`, never `ref-1.png`) |

No separate UX sketch file; flow analysis lives in the brief. Scratch: `{workspace_root}/.cm-tmp/{task_id}/`, deleted before done. Nothing at a sub-repo root, nothing at `{workspace_root}` outside the registered folders, nothing under `docs/changes/**`; naming and content: `CLAUDE.md` §19.4.
