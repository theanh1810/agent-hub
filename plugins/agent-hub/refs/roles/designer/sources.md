# Sources — read these before designing
<Owner: agents/designer.md § References>
<Read when: Workflow step 1, every run. Thinking mode governs steps 2-4. Spec hook when `spec_required: true`. Reference design systems only with no house style. Design source fidelity whenever a Figma, image or existing screen exists.>

---

## When spawned

Only main thread, only after brainstorm sets `needs_design: true`; designer reads only and calls no agent.

- **Spawn for:** a new FE feature (web, RN, Flutter, desktop) · a change to layout, flow, composition or visible behaviour · a design-system migration · web–mobile parity.
- **Skip for:** backend, API, infra, CI, DB migration · a logic bug with no visual change · copy-only edit (≤2 strings, no layout shift) · CLI, scripts, docs · a hotfix where the design shipped and only behaviour broke.

## Thinking mode

| Mode | When | Behaviour | Clarify loops |
|---|---|---|---|
| `quick` | 1 screen, pattern established | reuse the pattern, 1 candidate, no catalog survey; still writes `DESIGN.md` | 0 |
| `standard` | feature ≤3 screens | 1 chosen pattern + 1 rejected, full `DESIGN.md` | ≤1 |
| `extended` | new flow ≥4 screens, design-system migration, cross-platform parity | 2-3 candidates with reject reasons, full `DESIGN.md` with the flow in prose | ≤2 |

The user cue `design carefully`, `deep ux` or `redesign everything` forces `extended`.

## Sources, in order

| # | Source | Why |
|---|---|---|
| 1 | brainstorm machine record and `design.md` (`refs/plan-lane.md`) | the problem as framed, `binding_scope` |
| 2 | live UC and the change's spec delta in `uc_ids[]` | the agreed flow; read before drawing any flow |
| 3 | `specs/entities/<context>.md` | screens and components take names from the Entity Model |
| 4 | the repo's theme, tokens, component library | read-only; match house style, never a parallel scale |
| 5 | `rules/UI_RULES.md` | §1 layout primitive, §6 z-index ladder, §12 mobile rules |
| 6 | Figma (`figma.com/` URL) | `mcp__mcp_figma__get_design_context` |
| 7 | reference `DESIGN.md` of other products, only with no house style | § Reference design systems |
| 8 | an old plan path in the brief or a task file that no longer exists → `agent-hub locate --resolve PATH` | the new path from `docs/changes/MIGRATION-MAP.tsv`; the old folder is never recreated |

The pattern catalog: `refs/roles/designer/catalog.md`.

## Paths

Every `docs/…` path resolves from `{workspace_root}` (`refs/artifact-layout.md § Where the workspace root is`); `specs/` is `{workspace_root}/docs/specs/`. A `{slug}` carries the repo or product as prefix; folders stay flat. The design library alone is global: `~/.claude/docs/design-library/{lib}/`, shared and referenced in place, never copied per repo.

## Reference design systems

For a project with no design system and no look named by the user. "Use references as evidence, not as templates."

| Source | Reach it with | Holds |
|---|---|---|
| awesome-design-md | fetched by `devops` after approval (`https://github.com/voltagent/awesome-design-md` or `https://getdesign.md/{brand}/design-md`); designer reads the returned path | curated `DESIGN.md` of known products |

Any network fetch of an asset, font, icon set or design library goes through `devops` with the user's approval; the designer returns `needs_devops` with the exact command and reads the path devops returns (D21-b).

It follows the Stitch shape: theme · palette and roles · typography · components · layout · depth · do/don't · responsive · agent guide.

Rules:

1. **House style wins.** Existing tokens, theme or library are the standard; read a reference only with nothing to match or when the user names one.
2. **Reference, never paste.** Take the reasoning (why this scale, contrast, elevation), not another brand's palette, type or names.
3. **Cite it.** A reference token records its origin in the token table's origin column (`awesome-design-md:figma`); no origin is an invention.
4. **Ask before adopting** a whole system: `needs_user_input` with candidates as options.
5. **Learn from 2-3 reference screens:** record the decisions (hierarchy, density, navigation, controls, responsive, states), rebuild with this product's components and tokens.
6. **Store the chosen system as one Master plus per-screen overrides**; put a screen's change in its override and ask permission before touching the Master, never overwrite it unasked.

| Rationalization | Reality |
|---|---|
| "This brand's palette looks right, paste it" | Reasoning only; the palette belongs to that brand. |
| "The repo has tokens, but the reference is nicer" | House style wins; adopting a system is the user's call. |

## Spec hook (HARD when `spec_required: true`)

Rules in `rules/SDD.md`. With `uc_ids[]`, read the UC before drawing anything; never invent a flow that exists.

- The UC main flow **is** the primary flow; each screen carries `covers_step: "UC-042 step N"`. A screen covering no step means the spec is missing or the screen is surplus.
- UC alternate flows and decided exceptions **are** the edge flows. An exception with no screen or state is a gap: add it, or say why it is dropped.
- Acceptance criteria name the observable states (error message, countdown, pending); AC-fixed copy is copied word for word.
- A UC missing a step or contradicting itself → `needs_user_input`; never patched with a screen.
- Names come from the Entity Model.

`spec_required: false` → skip.

## Design source fidelity

When the user asks the agent to read a Figma or image design, the agent follows all of it and adds nothing without asking and being allowed; the question names the screen that lacks the element and asks whether to add it. The one statement of the rule; every reader follows it and keeps no copy.

**Trigger.** A screen has a source: a Figma node, a design image or screenshot, or, with neither, the screen as it now is. A screen with no design keeps the catalog and `UI_RULES.md` process.

**Readers.** designer, brainstorm, implement, test, any agent asked to read a design.

**Rule.** Follow the source in full: screens, layout, element set, order, states, copy. Add nothing, drop nothing.

**Allowed additions.** Only an element the request or an AC names, recorded in `requested_elements[]` with its source (`AC-n`, or the user's words with date), styled from the existing screen's fields, buttons, spacing and text.

**Everything else is a red question**, one decision each:

- worded `Screen <screen name> has no <element>; add it?`, options `Add` · `Do not add`;
- written in the open-questions section of DESIGN.md as `- [ ] <span style="color:#d32f2f">**NEEDS ANSWER**</span> Screen … has no …; add it? (blocks the whole screen …)` (the bold label stays readable where HTML is not rendered);
- one open red question blocks the whole screen; several go out as several one-decision entries of one `user_questions[]`;
- the answer is written into DESIGN.md: `Add` moves the element to `requested_elements[]` with source `user YYYY-MM-DD`; `Do not add` ticks the line with the answer.

| Reader | On an element the source lacks |
|---|---|
| designer | `needs_user_input`, one entry per open red question |
| brainstorm | asks a Clarify question naming screen and element; writes no AC, requirement or task for it |
| implement | does not build it; `needs_design_clarification` naming screen and element; starts no UI task while a red question is open |
| test | runs the check below |

**Test's check.** On a UI task whose DESIGN.md names a `design_source` of kind `figma`, `image` or `existing_screen`, test compares each built screen with `screens_detail[].components[]` (each `origin: source|requested`) plus `requested_elements[]`: Figma re-read with `get_design_context`; an image or the existing screen's baseline kept beside the new screenshot. An element on screen in neither list is a `fidelity_findings[]` entry `verdict: extra`; a source element missing is `verdict: missing`. Any finding makes the gate `RED`, `failure_type: fixable`; the oracle is DESIGN.md's `design_source` and `requested_elements[]`. A DESIGN.md without `design_source` (pre-rule) skips the check and the report says so.

| Rationalization | Reality |
|---|---|
| "The screen obviously needs a back button" | Not in the source → red question. |
| "It is only a small empty-state line" | Small additions are additions; ask. |
