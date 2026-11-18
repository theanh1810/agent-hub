# Flow drawing
<Owner: agents/brainstorm.md>
<Read when: brainstorm in `mode=plan-write`; implement at the closeout of an L3 or L2 run; main thread showing a plan gate, a final gate or a final reply>

---

A change the user reads gets one simple drawing of how its flow changes, made with the user skill `diagram-design`. The drawing never blocks a gate, and the approval stamp does not cover it.

## When

- L3: brainstorm draws in `mode=plan-write`, after `plan.vi.md` and before `agent-hub check plan`, and redraws when a task or a `Files:` list changes. Skipped when every task has `Covers: none`. At the end, the implement spawn that runs the closeout checks it before closeout step 5 (§ End check).
- L2: implement draws once from its own diff, before closeout step 5, when three or more changed paths are neither tests (a `test`, `tests` or `__tests__` segment, or a name holding `.test.`, `.spec.` or `_test.`, or starting `test_`) nor `*.md`.
- No drawing in L0, L1, L-cfg, L-inv or L-ops. A user who asks for one gets it in any run with a diff; a user who refuses gets `skipped: user said no drawing`.

## What

One picture: the flow after the change. Steps it adds or alters carry `accent`, the first two in flow order; any further ones carry a muted `mới` or `đổi` tag. A removed step stays in place, dashed, muted, labelled `bỏ`. Flowchart by default; Sequence only when the change is about who calls whom. Caps: Flowchart at most 7 nodes, 9 arrows, 2 decisions; Sequence at most 4 participants, 9 messages. One node is one module, service, screen or actor step, its internals collapsed; no fields, tables, status sets or component maps. A longer flow is cut to the changed part, with a `…` node at each cut end. When no step's behaviour changes (pure schema, pure styling), draw nothing and write `không có luồng thay đổi — <reason>`.

Each node's `<g>` carries `data-files="<path>,…"`: the non-test, non-doc files that implement that step. Labels are in the reply language; module, symbol, endpoint and status names stay as in code. A visible last line under the drawing reads `Vẽ theo kế hoạch ngày <date>` (L3) or `Vẽ theo code ngày <date>` (L2).

## Style

Check `~/.claude/skills/diagram-design/SKILL.md` exists; when it does not, write `skipped: skill not installed` and go on. Read it by path, plus `assets/template.html` and the one type reference. Pick the skin by the skill's own lookup in `references/profiles.md`, read-only: a valid project `.diagram-design` marker, else the working copy's profile header, else the only non-`default` profile in `~/.diagram-design/profiles/`. No such profile: the shipped default skin, and the line `Chưa có hồ sơ thương hiệu cho bản vẽ — dùng kiểu mặc định`. Never run onboarding or the `save`, `update`, `load`, `switch` or `reset` verbs; never write the marker, `~/.diagram-design/`, or anything in the skill folder; never pause at the skill's confirm step. Fonts follow the profile's `Font source`: `web` keeps the profile's `fonts.googleapis.com/css2` link, `system` and the default skin delete the template's font link. No PNG or SVG export unless the user asked.

## Checks

From the skill folder: `python3 -B -I scripts/verify_geometry.py <file>` and `python3 -B -I scripts/self_check.py <file>`, adding `--offline` when the font link was deleted. Running them is not a test of source. Every `data-files` path is in the plan's `Files:` (L3) or the run's changed paths (L2), and every non-test, non-doc `Files:` path sits on some node. Record the counts and exit codes as `diagram_check`. Only these two scripts exist; a reference naming another check script is not run and not claimed. One fix attempt; still failing, keep the file and add `chưa qua kiểm tra: <script>`.

## End check

L3 only, in the closeout of the `mode=simplify` spawn and of each fix-round spawn. Redraw when closeout step 2 recorded `diff_matches_plan: false`, or when an accented node's `data-files` names no changed path; the last line becomes `Cập nhật theo code ngày <date>`. Otherwise change only the last line, to `Đối chiếu với code ngày <date>: khớp`, and re-run the checks. One file, rewritten in place, never copied. A reordered call inside planned files is not caught: say so in `diagram_check`.

## Where it shows

Paths: `refs/plan-lane.md § Where the files live` (L3) and `refs/artifact-layout.md § Where writing is allowed` (L2). `plan.vi.md` holds one `Bản vẽ:` line above the first task block; the closeout block holds `diagram`: the path with `confirmed` or `updated`, `no flow change`, or `skipped: <reason>`; the final reply gives the absolute path (`refs/final-response.md`).
