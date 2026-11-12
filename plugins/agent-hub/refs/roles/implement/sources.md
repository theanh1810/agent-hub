# Sources
<Owner: agents/implement.md § References>
<Read when: Workflow step 1, before the task is read. The plan contract, the reading order, the spec layer, the fix round and where ephemeral files go all apply from intake on, so this file is read first.>

---

## Spec-driven and codebase-driven (HARD)

- **100% spec-driven.** The code implements all of the spec and nothing beyond it. A rule the spec does not state is `blocked_needs_spec`; a rule the spec states and the code contradicts is a defect even when it "works". Every business behaviour traces to a `UC-XXX / AC-N`.
- **100% codebase-driven.** Read how the codebase already solves the adjacent problem, then follow it: documentation, then neighbouring code, then patterns. A file in a house style nobody else uses costs every reader a dialect lesson.

## The plan is the contract (HARD)

The plan (`{plan_dir}/`, read per `refs/plan-files.md`) is the only source of truth for what is built. Not the chat, a ticket, a message that arrived mid-task, or your own better idea.

- **Exactly the task, nothing more, nothing less.** `what`, `files[]`, `solution`, `steps[]`, `acceptance_criteria` define the work. Less makes the plan lie about what shipped; more puts changes no reviewer expected and no test covers in the diff. "While you're in there, also…" is a plan change.
- **A change of mind does not change the plan.** The user says something different mid-task: do not act; return `needs_revision`, `reason: plan_change_required`, naming what they now want. Main records it as a pending change for the final gate, then implement continues the approved plan.
- **Cannot build it as written** (a file does not exist, a dependency makes the approach impossible): `needs_revision` with the evidence, same route. Never improvise.
- **Steps, as written.** `steps[]` is the binding order. The mode's procedure runs inside it and never reorders it; a TDD task carries its failing test as step 1.
  - A step's `before` that occurs other than exactly once in its file at that moment: `reason: step_anchor_mismatch`, with the step's `n`, the count found and the three lines around the anchor; never edit `before` to fit.
  - A step that contradicts an acceptance criterion or the `solution`: `reason: plan_internal_conflict`, naming both.
  - A step's output differs from its `expect`: the code is wrong (fix at its cause, never patch the symptom to match) or the plan is wrong (return it, never edit it).
- **Plan keys.** Read `non_goals`, `assumptions`, `confirmed_values`, `user_actions`, `contracts`, `rollback_strategy` from `plan.yaml` top level, never its `tasks`.

## Fix round

A fix-round spawn reads the round's `fix_list[]` from `errors.yaml` (`errors_path`, `round`; `refs/roles/brainstorm/error-batch.md`); each entry names the `files[]` it may touch and the `user_answer` that authorised anything outside its task. Findings reach implement only through it.

- **Any entry unclear: stop and ask about every unclear one before fixing any**, since entries may relate.
- **One entry at a time, a test per entry**: blockers first, then simple fixes, then complex; finish with a no-regression check.
- **In scope** (fix directly): every touched path is in the entry's `files[]` (its `user_answer` authorised any path outside the task, and any added case, copy, AC or expected-result change). Rerun that task's checks and `test_cases[]`, append finding id, files and fix snapshot to the named task's `result.deviations`, or, for an entry with `task_id: null`, to the closeout task's `result.changes[]` (`refs/closeout.md` § Who writes it), freeze for review (`refs/roles/implement/close-task.md` § Freeze for review). Anything the entry does not name: `needs_revision`, `reason: plan_change_required`.
- **"Make it standard" entry**: grep whether anything uses it. Unused: report a proposal to delete instead of polishing. "If we don't need this feature, don't add it."
- **Entry looks technically wrong or would break working behaviour**: do not fix blind. Check five things (right for this codebase; breaks running behaviour; why the current code is so; works on every platform/version; the reviewer had enough context). Cannot check: say "cannot verify without X"; return the evidence for brainstorm to decide.
- **Entry contradicts a decision the user already made**: stop and ask; do not fix to the reviewer's word.
- **Reply in actions**: "Fixed. [what changed, where]". No "you're absolutely right", no thanks. When you argued and were wrong, state the correction factually (what you checked, what came out) and move on, with no long apology.
- **Evidence**: the fix report names the test covering the fixed part, its command and output. Reviewers will not re-run tests for you; the report is the test evidence.

## Sources — read these before the first edit

| Order | Source | What it settles |
|---|---|---|
| 1 | The task record (`refs/plan-files.md § Reading one task`) | `what`, `purpose`, `files[]`, `solution`, `steps[]`, `interfaces`, `acceptance_criteria`, `test_cases[]`, `review_checkpoint`. Missing keys: `needs_revision`, never fill them in |
| 2 | `binding_scope` from the brainstorm handoff | files and symbols that may be touched, tools allowed |
| 3 | The live UC or the change's spec delta (`refs/change-files.md`) in `covers_uc`, plus `specs/entities/` | business rules, and the vocabulary to name things with |
| 4 | `design_brief_ref` → `{plan_dir}/design/{slug}/DESIGN.md` | FE work: pattern, screens, tokens. Build from them as given; never re-derive |
| 4a | an old plan path that does not exist (a migrated workspace) → `agent-hub locate --resolve PATH` | its new path through `docs/changes/MIGRATION-MAP.tsv`; never recreate the old folder |
| 5 | Project docs, `AGENTS.md` / `CLAUDE.md` of the repo | conventions the team wrote down |
| 5a | `{sub_repo}/docs/CODE-STYLE.md` when it exists | the measured house dialect. Absent: `rules/code-style/README.md` § Precedence decides the fallback |
| 5b | `rules/code-style/_discipline.md` always, plus `<language>.md` for each language in `binding_scope` and no other | file budget, case coverage, smallest diff, scope; language mechanics |
| 5c | `refs/code-standards.md` § Coding Principles, read before the first edit | think first, simplicity, surgical changes, goal-driven checks |
| 6 | Neighbouring code: the task's `pattern_refs` first, else `mcp__gitnexus__query` then 2-3 files that already do this | the pattern to copy (`refs/roles/implement/craft.md` § Priorities rule 2) |
| 7 | `mcp__gitnexus__impact` on every symbol about to change, `api_impact` on a route or handler file | who breaks if the signature moves |
| 8 | Context7 | only when a library's exact behaviour decides the code |

Reading order, not rank: where style sources disagree `rules/code-style/README.md` § Precedence decides (the only statement of that ladder); the repo's style file beats a neighbour, and their disagreement is a finding.

Not sources: broad repo scans outside `binding_scope`, web search, anything on a server (a `devops` spawn).

**Read cache.** Read a file once per spawn, again only after another task of the spawn edited it; never re-read to confirm an edit (edit tools fail loudly). Read tasks one at a time (`refs/plan-files.md § Reading one task`), never the whole plan.

## Running the checks

- **Checks by kind, once before the spawn's first edit and once after its last, never between.** A code task lints its changed files, type-checks, runs the tests related to them (`vitest related --run --passWithNoTests=false <files>`, or the runner's own mode; the full suite when that finds 0 tests); the spawn's end runs full lint, type check and suite (a fix-round spawn too). A docs-only task runs its `test_cases[]` and, in `~/.claude`, `tools/check ruleset (package repo only)`.
- Every command goes into `extra.test_results.commands` and `result.commands[]` with its real exit code read from the run, never inferred, and `tc_id` (TC-<task>-<n>, null if no case names it).
- A red check of your own is fixed in place and re-run (outside the error-loop cap; the Three-Fail Rule caps it).

## Design brief

With `design_brief_ref`, read the brief's `chosen_pattern.id`, `screens_detail[]`, `tokens` and `state_matrix` as the source of truth (their shape: `refs/roles/designer/brief-schema.md` § Two shapes, one brief). Render once; on mismatch at most **2 retries**, then `status: needs_design_clarification`; a pixel-tweak screenshot loop past 2 is forbidden. With a design source (`design_source.kind` not `none`) build only its elements and `requested_elements[]`; anything else is not built: return `needs_design_clarification` naming screen and element. Start no UI task while a red `NEEDS ANSWER` question is open (`refs/roles/designer/sources.md § Design source fidelity`). Read `rules/UI_RULES.md` on a frontend task.

## Spec layer (SDD)

Rules in `rules/SDD.md`. Implement never edits behaviour specs (brainstorm owns them); it reads the spec and logs debt on a hotfix.

- **Stop rule.** A business rule the spec does not cover (threshold, expiry, permission, state transition, rounding): `blocked_needs_spec` with `spec_question` (ONE decision, 2-4 options) and `blocked_at: file:line`. Main asks the user, brainstorm writes the AC, then the task re-runs; picking the value that "sounds reasonable" is the failure this prevents.
- **Escalation net (tier 2).** Before committing, check the diff against `rules/SDD.md` §11.1: migrations, `*.proto` / openapi, routes, business enums, policies and permissions, events, business constants, money and legal modules. A match with `spec_required: false`: `blocked_needs_spec` with `spec_required_escalation: true`, the pattern and `file:line`; do not commit. Exceptions: a hotfix never blocks (it logs `specs/_debt.md`); a purely mechanical change (rename, format, move) records `spec_scope_note` and proceeds.
- **Naming** follows the Entity Model. A code name that contradicts `specs/entities/`: report `spec_naming_conflict[]`, never coin a synonym.
- **Rules found while coding** go to `spec_delta[]` for brainstorm to write back at closeout step 4 (`refs/roles/implement/close-task.md` § Closeout). Leave the UC file to brainstorm; never edit a UC.

## Artifact layout

Files go only to paths in `CLAUDE.md` §19.1. Ephemeral output (logs, dumps, screenshots, scratch scripts) goes to `{workspace_root}/.cm-tmp/{task_id}/` and is deleted before the task is done.

Compressing a handoff or log: read `skills/context-compression/SKILL.md` first; never trim `file:line` citations, `pattern_reference`, the first root-cause error, test commands and numbers, `impact` / `api_impact` results, `result.changes[]` fields, blockers.
