# SDD — Spec-Driven Development

The spec sits between people and code: **people agree on intent; AI generates code, tests and docs around it.** When something is wrong, fix the spec first, the code second.

Source: *Spec Driven Development* (Nguyễn Thế Huy) plus a Scrum coaching template set. <!-- scrub-allow: source credit, Q23 -->

**Language.** This file is English; the prose under `specs/` is in the reply language (`core.md` §1), because the user reads it (§4), while its section headings are the English ones of `templates/spec/`. **Paths.** Every `docs/…` path and a bare `specs/…`: `refs/artifact-layout.md` § Where the workspace root is.

---

## 1. When to use it

**On** when any holds: the system lives longer than six months · more than one person touches the codebase · business rules are non-trivial (money, contracts, legal, access control) · AI writes most of the code · this is the product's core.

**Off (HARD — forcing it manufactures work)**: a throwaway prototype · a technical spike · a one-off script · a typo, rename or copy edit · a production hotfix while it burns (spec afterwards).

| Class | Spec required? |
|---|---|
| `simple` | no |
| `problem-solving` | no |
| `bug` (local) | no |
| `bug` (shared symbol / contract / route / schema) | **yes** |
| `hotfix` | not at fix time |
| `feature` | **yes** |
| `medium` / `complex` / `refactor` | **yes** |
| `infra` / `docs` | no |

**This column is the coarse on/off switch, never the artifact owed — §10 is the per-class authority (HARD)** and alone says which artifact each class owes, when and who writes it. A `refactor` reads **yes** here and owes **no spec change** there; `complex` owes an ADR this table never mentions.

Time-box a first-round UC to **1-2 hours**; longer means it is being over-written.

### 1.1 Spec Layer — who does what

Duty table and blocking gates here; per-class rule §10, procedure §10-§11. Orchestrator sets `spec_required` from the class on every spawn (`agents/orchestrator.md` § Spec layer routing); an agent reads the flag from its brief, then §10 for what it obliges.

| Agent | Obligation |
|---|---|
| `orchestrator` | sets `spec_required` per class and leaves reading and writing spec to `brainstorm` instead; never reads or writes spec |
| `brainstorm` | owns behavior specs; change files per `refs/change-files.md`; a user's business answer goes into the authoritative UC or capability requirement; every bug is classified A or B |
| `designer` | the UC main flow **is** the primary flow; displayed copy matches the AC word for word |
| `planner` | `covers_uc` and `covers_acceptance` on every task, pointing at real ids; the final wave carries the `closeout` task, whose step 4 is the spec sync (`CLAUDE.md` §21) |
| `implement` | a rule the spec does not state → **STOP** `blocked_needs_spec`; naming follows the Entity Model; a hotfix logs `specs/_debt.md` |
| `reviewer` | reads spec **before** code; `spec_drift` 🔴 blocking; the closing question: *"which spec does this rule come from?"* |
| `test` | test names carry the UC and AC ids; tests bind to the AC's behaviour, not the implementation |
| `devops` | infrastructure uses an ADR, linked to the UC or BR it affects |
| `auditor` | the four SDD metrics plus overdue `specs/_debt.md` lines |

**Blocking gates (HARD)**: a UC with no acceptance criteria → no code · a class-B bug with no user answer → no code · `spec_drift` → no merge · a plan closing without its `closeout` step 4 → not Done. **A hotfix is never blocked**: patch, log the debt, repay within 24 hours.

**The initial `spec_required` is a guess.** Three nets re-evaluate it (§11): brainstorm after its dependency trace · implement on the real diff · reviewer scanning four signals even when it is `false`. **Raise only, never lower.** Deterministic triggers: §11.1.

**Measurement.** `specs/README.md` opens with an adoption block; missing → the auditor prints `N/A`, never `0%`. AC Coverage has **three** states: has a test · missing a test · not yet measurable.

---

## 2. Four layers

| Layer | Answers | File | Owner |
|---|---|---|---|
| **BR** | why are we doing this? | `specs/business-requirements/BR-XXX-*.md` | user / PO |
| **UC** | who does what with the system? | `specs/use-cases/<context>/UC-XXX-*.md` | user + brainstorm |
| **Entity Model** | what nouns is the system talking about? | `specs/entities/<context>.md` | brainstorm + implement |
| **AC** | how do we know it is done correctly? | inside the UC file | user approves, tests bind to them |

The Entity Model is **not an ERD**: no indexes, datatypes or foreign keys, only names, meanings, states, relationships, so the AI uses the business vocabulary instead of inventing one (`tbl_dh_v2` → `Order`).

---

## 3. Folder layout (in the project workspace, never in `~/.claude`)

```
{workspace_root}/                   # CODE_ROOT + one segment, one product — CLAUDE.md §19.0
├── docs/specs/                     # the whole spec layer of the product (D12)
│   ├── business-requirements/BR-001-*.md
│   ├── use-cases/<bounded-context>/UC-042-*.md
│   ├── use-cases/_legacy/          # excavated from old code, unconfirmed
│   ├── entities/<bounded-context>.md
│   ├── diagrams/
│   └── README.md                   # index + per-UC status + adoption block
├── docs/changes/{plan_id}/         # a change, one folder: proposal.md, design.md, design.yaml, specs/<context>/spec.md, plan files (refs/plan-files.md), errors.yaml, logs/, reviews/
├── docs/changes/archive/{YYYY-MM-DD}-{plan_id}/  # closed changes, merged by §3.1; older archives keep {plan_id}
├── docs/brainstorm/                # work with no change id yet (refs/artifact-layout.md §19.1)
├── docs/adr/                       # technical decisions, linked to UC/BR  # scrub-allow: product path
└── <sub_repo>/src/  <sub_repo>/tests/   # the code; no sub-repo holds specs/
```

Change files per change: `refs/change-files.md`. **In a code workspace the plan is the spec (HARD)**. `specs/use-cases/` stays the system **as it runs**; `docs/changes/{plan_id}/` is this change, and closing it merges its delta into the UCs and archives it (§3.1).

Every task record carries `covers_uc`, and every `covers_acceptance` is a **real AC id in a real UC file** or in the change's delta. After implement and review, update the UC (§3.1) and bump its `## History` before closing the plan, or the baseline drifts from the code.

A task needing SDD in a workspace with no `docs/specs/`: §10.3.

### 3.1 Closing a change (HARD)

A plan in `docs/changes/{plan_id}/` merges at closeout step 4 (`refs/closeout.md`). A folder holding `specs/` (the Requirement/Scenario deltas of `refs/change-files.md`) closes by the steps below; one holding `deltas/` closes by §3.1.1. Brainstorm writes behavior specs, in order:

1. **Requirement, flow and exception delta into the UC.** For each `docs/changes/{plan_id}/specs/<context>/spec.md`: `## ADDED Requirements` joins the UC's `## Acceptance criteria` under the AC id it reserved · `## MODIFIED Requirements` replaces the block with that id whole · `## REMOVED Requirements` keeps the id, marked **retired**, never deleted · `## RENAMED Requirements` changes the name beside an id that stays. Its `#### Scenario:` blocks become the AC's Given-When-Then. A delta with no live UC is a new UC, copied whole. A reserved AC id, an `E-n` or an inserted step number (`n.1`) another change already took is a stop, `needs_user_input`, never a renumber. `## Flow Changes` and `## Exception Changes` merge the same way into `## Main flow` / `## Alternate flows` / `## Decided exceptions`. Step numbers are dot-separated and compare segment by segment, a number sorting before every number that extends it (`2` < `2.0.1` < `2.1` < `2.1.1` < `2.2` < `3`); a step inserted after `p` takes the next sibling of `p` when free and sorting before the next step `q`, else `p.1`, then `p.0.1`; before step 1, `p` is `0`; no existing number or variant key (`2a`, `4a`) changes. A replaced block is written from the delta's full text, never patched. What lands in the UC is prose in the reply language (`core.md` §1) under the English fields `Given:` / `When:` / `Then:`, keeping its AC id; the English delta stays in the archive and the `## History` line of step 3 cites it.
2. **`### Test mapping`**: one row per AC the change touched: `Priority` from the delta, `Matching test` and `Status` from test's `ac_coverage[]`; an AC a `test_cases[].covers_acceptance` names but `ac_coverage[]` does not stays `not written yet`.
3. **`## History`** gains one line: date, `plan_id` and the archived delta's path, the AC ids, flow steps and exception ids added, changed and dropped, each rename as `old → new`.
4. **`docs/specs/README.md`**: update the index row of each touched UC.
5. **Archive.** The folder moves whole to `docs/changes/archive/{YYYY-MM-DD}-{plan_id}/` (the date the archive runs); nothing in the archive is edited again.

Reviewer's `spec_trace` takes `uc_ids` and `ac_covered` from the task records and checks each AC id against the live UC **or the delta**; until step 1 runs, a new id exists only in the delta.

### 3.1.1 Legacy UC-delta change

A folder holding `deltas/` closes by steps 2-4 of §3.1 and the numbering rules above, with this step 1:

1. For each file under `docs/changes/{plan_id}/deltas/<context>/`: `## Added ACs` joins the UC's `## Acceptance criteria` under the reserved id · `## Changed ACs` replaces the block with the same id · `## Removed ACs` keeps the id, marked **retired**. No live UC → a new UC, copied whole. A taken AC id, `E-n` or inserted step is a stop, never a renumber. `## Added/Changed flows` and `## Added/Changed exceptions` add, replace whole or mark **retired** the step, variant or `E-n`; `## Renamed` changes the name beside an id that stays. The heading's instruction after " — " is dropped; **Why changed** and **Previously** stay in the archived delta that `## History` points to.
5. **Archive** to `docs/changes/archive/{plan_id}/`; nothing in it is edited again.

---

## 4. Spec prose style (HARD)

A spec is read by **three audiences at once**: the user deciding the rules, the developer or AI writing code, the tester writing tests.

Required: **the reply language** (`core.md` §1) for descriptions, flows and reasoning, English kept for entity names, fields, statuses, endpoints, filenames · a **quick-info table** at the top · a **glossary** covering every technical or internal term (naming a term without glossing it is a violation) · **Given-When-Then** in the UC: `Given:` / `When:` / `Then:` / `And:`, the fields English and their prose in the reply language (a spec delta is English Requirement/Scenario, `refs/change-files.md`; the live UC follows this section) · a **numbered main flow**, one action per step, from the user's point of view ("The customer taps…"), never the code's · **every AC has an id** the tests bind to · **open questions as checkboxes** `- [ ]`.

Forbidden: logic code, class or function names in Flow and AC (they belong in `## Technical notes` at the end) · unglossed jargon (idempotent, race condition, hydration, N+1, binding, side-effect; gloss each term instead) · unmeasurable sentences ("handles it quickly", "better UX"; state the measurable result instead) · confusing an exception with a bug: "an expired QR shows a message" is an exception and belongs to the spec; "the app crashes when the QR expires" is a bug.

Templates: `templates/spec/`.

---

## 5. Six principles as constraints

| Principle | Constraint |
|---|---|
| **Requirements-Driven** | A new concept in code (field, status, flow, permission, policy) exists in the spec **before or at the same time**. `implement` hitting a rule the spec does not state **STOPS** |
| **AI-Assisted** | AI does the shaped work (CRUD, mapping, boilerplate, adapters, tests from existing ACs); people decide refund policy, limits, access rights, trade-offs, anything with money or legal weight. The closing review question, *"which spec does this rule come from?"*, unanswerable means no merge |
| **Iterative** | A first-round spec needs the main flow and 2-3 clear ACs. Every file has `## History`. A wrong AC is marked deprecated, never deleted |
| **Test-Protected** | Every AC has ≥1 test named with both ids: `describe("UC-042/AC-2: payment succeeds")` (readers still accept the spaced form of old labels). Tests check **the spec's behaviour**, not implementation detail |
| **Stakeholder-Centric** | Brainstorm's clarify and approval gates are that step, and **the answer is written into the UC file**, never left in the session |
| **Traceable** | Code → spec → test → requirement. Commits read `<type>(UC-XXX): …`. Mirrored folders: `specs/use-cases/checkout/UC-042-*.md` ↔ `src/use-cases/checkout/place-order-qr/` ↔ `tests/{unit,integration,e2e}/use-cases/checkout/place-order-qr/` (`code-style/README.md` § Test layout) |

---

## 6. Ready / Done

**Ready** — enough to start coding: a UC id and its BR link · actor, trigger, main flow · ≥1 AC in `Given / When / Then` form · every term in the glossary · the user confirmed it or answered every clarify question · no open question blocking the main flow. **Missing ACs means no code starts (HARD).**

**Done** — after implement: every AC has ≥1 test named with both ids · the tests pass · any rule discovered while coding is written back into the UC · `## History` bumped · the commit carries the UC id · `Status` reads `implemented`.

---

## 7. Brownfield

Two mistakes (HARD): ❌ a **big-bang rewrite before there is a baseline** (an old system has hidden features customers depend on). ❌ **generating a spec from code and treating it as truth**: it says what the code **does**, never whether it is **right**.

Steps (HARD order): 1 brainstorm builds the Entity Model from the DB schema (an opaque column gets `TODO: verify`) · 2 brainstorm writes Use Cases from controllers, production logs, the UI flow · 3 **verify with the people who operate it**, the user decides; unconfirmed UCs are tagged `legacy-unverified` in `specs/use-cases/_legacy/` · 4 test + implement write **characterization tests** from real anonymised production I/O before refactoring (they prove a refactor did not change behaviour, not that the code is right) · 5 implement refactors behind the spec and those tests; one PR never mixes a large refactor with a rule change.

Invest by module temperature, never spec 100% of a codebase: `git log --since=6.months.ago --name-only | sort | uniq -c | sort -rn | sed -n '1,20p'`. **Hot** (changes every sprint) → full spec + characterization + AC tests. **Warm** → a stub, filled when work approaches. **Cold** → leave it. **A brownfield spec is allowed to be ugly** (`TODO: verify`, old terms beside new): a **real** spec comes before a **pretty** one. Stop when a new developer works independently in a module within a week, hot modules exceed 70% coverage, and "can we do X?" is answered in an hour.

---

## 8. Metrics

| Metric | Measures | Target |
|---|---|---|
| **Spec Coverage** | active use cases with a usable spec (BR link + ACs) | greenfield ~100% of MVP · hot brownfield ~70%/quarter · all-legacy: report the coverage that exists, do not force a target |
| **AC Coverage** | ACs with ≥1 matching test | matters more than code coverage |
| **Regen Success Rate** | AI regenerations whose tests pass without heavy manual fixing | low = unclear spec **or** wrong tests |
| **Trace Ratio** | commits carrying a valid UC id | without it every incident starts with grep and guesswork |

Avoid: spec line count (rewards length) · UCs closed per week (rewards artificial splitting) · raw code coverage. `auditor` measures all four per window.

### 8.1 The adoption block (HARD)

A repo that has not renamed its tests reports AC Coverage 0%, which **does not mean there are no tests**: nothing has been measured. `specs/README.md` opens with:

```yaml
---
sdd_adopted: 2026-08-10              # written by /spec init
naming_convention_from: 2026-08-10   # from here, tests must carry UC-ID + AC-ID
scope: partial | full
modules_in_scope:                    # required when partial
  - src/use-cases/checkout
---
```

- **No block** → every metric is `N/A` with "the repo has not declared an adoption mark" instead of `0%`; printing `0%` is forbidden.
- **Trace Ratio** counts only commits with `ts >= sdd_adopted`.
- **AC Coverage** counts only ACs of a UC marked `implemented` and created or updated after adoption; a draft UC is out.
- **`scope: partial`** → every metric counts only inside `modules_in_scope[]`.
- **Spec Coverage** — the denominator is *active use cases in scope*, not the file count under `specs/`; `_legacy/` counts separately.

### 8.2 Three sources for AC Coverage (HARD)

Read in this order. Tests are declared at planning time (`tasks[].test_cases[].covers_acceptance` as `UC-XXX/AC-N`), so the plan is read **before** the test directory; measuring by test name is the **last** source.

| Priority | Source | Why |
|---|---|---|
| 1 | the `### Test mapping` table in the UC file, filled by brainstorm from test's `ac_coverage[]` | data an agent recorded, not an inference |
| 2 | `plan.yaml` and `tasks/*/*.yaml` of every plan, open or archived (`refs/plan-files.md § Where a plan lives`) → `test_cases[].covers_acceptance` | this AC was planned to be covered |
| 3 | a `UC-XXX/AC-N` label in a test file | a labelled test exists, but nobody wrote it back into the UC |

Measuring: `commands/spec.md` § check. `docs/specs/` and `docs/changes/` resolve from the **workspace root** (`CLAUDE.md` §19.0), never cwd; test directories are **discovered** in every sub-repo before grepping, never hardcoded.

Three states: **has a test** (both agree) · **missing a test** (both empty, UC shipped: the real gap) · **not yet measurable** (table empty but tests exist for that module, unlabelled). The third counts in **neither** numerator nor denominator. Above 30% "not yet measurable", the fix is a labelling pass over test names, not more tests.

### 8.2b Who sets scope, and how narrow scoping is caught

`scope` and `modules_in_scope[]` are **chosen by the user from a list Claude produces** (`/spec init` reads `git log --since=6.months.ago`, builds options with commit counts); the user never types a path. A narrow scope makes metrics look good while real coverage stays low, so: (1) every hot module *not* selected is listed under "Not yet specified" with its commit count; (2) a task touching a module outside scope **must ask**: brainstorm neither adds it silently nor skips the spec silently, asks once per module and records the choice; (3) the auditor compares declared scope with reality and reports a heavily-changed module outside it. Narrowing is allowed; the reason goes into "Not yet specified".

### 8.3 Reading the metrics

AC Coverage 0% is not "no tests" (check the adoption block, `tests/`, the "not yet measurable" count). Trace Ratio low is not "lazy" (check pre-adoption commits and `spec_required: false` tasks). Regen Success low is not "the AI is bad" (unclear spec or wrong tests; auditor names which, with a `plan_id`). Spec Coverage 100% is not "everything covered" (check the denominator and that "Not yet specified" is current).

---

## 10. Playbook per task type (HARD)

§1 is the coarse threshold; this is the concrete behaviour. An agent looks up its own row and does not extrapolate. **Before** = finished before touching code · **During** = alongside · **After** = once the code runs.

| Task type | Artifact | When | Who | Blocks merge? |
|---|---|---|---|---|
| `simple` (typo, local rename, comment) | — | — | — | no |
| `simple` **changing user-visible behaviour** | one line into an existing AC | During | implement | no |
| `problem-solving` | — | — | — | no |
| `bug` type A — **spec right, code wrong** | no spec change; a regression test on the existing AC | During | test | no |
| `bug` type B — **spec missing the rule** | a new AC, history bumped | **Before** | brainstorm → user approves | **yes** |
| `bug` touching a shared symbol / contract / route / schema | as type B, plus verifying the Entity Model | **Before** | brainstorm | **yes** |
| `hotfix` | record the debt; do **not** block the fix | **After**, ≤24h | implement logs, brainstorm repays | no |
| `feature` ≤2 files | short UC: summary, main flow, ≥2 ACs | **Before** | brainstorm | **yes** |
| `feature` ≥3 files or cross-module | full UC + Entity Model + BR link | **Before** | brainstorm + user | **yes** |
| `medium` | full UC | **Before** | brainstorm | **yes** |
| `complex` / architecture | UC + Entity Model + ADR | **Before** | brainstorm + planner | **yes** |
| `refactor` | **no spec change** (behaviour unchanged); characterization tests first | Before | test + implement | **yes** (tests pass) |
| `refactor` that must change behaviour | two PRs: pure refactor, then the rule change with its spec | Before | planner | **yes** |
| `infra` / CI/CD | an ADR, not a UC | During | devops | no |
| `docs` | — | — | — | no |
| `error-batch` | — unless the root cause is a spec gap → open a debt entry | After | brainstorm | no |
| UI-only (layout changed, rules unchanged) | update the main-flow step if the user sees it differently | During | designer → implement | no |
| An API / event / schema contract change | the UC of **every** consumer is reviewed | **Before** | brainstorm | **yes** |

### 10.1 Bug type A or B (brainstorm decides in Phase 4)

One question: **does the spec already say what this behaviour should be?** When the spec is silent, the answer is "spec missing", asked of the user, not judged by what a user would reasonably expect.

| Answer | Type | Action |
|---|---|---|
| Yes, clearly, and the code differs | **A** | fix the code, add a regression test on the existing AC, leave the spec alone |
| Yes, but ambiguously (two readings both defensible) | **B** | ask which is right → rewrite the AC → then fix |
| No, the spec never covers this | **B** | ask → add the AC → then fix |
| There is no UC for this flow | **B** | write a short UC for this exact situation, not the whole flow |

**Ask the user and write the answer into the spec before fixing a type-B bug; fixing it without a user answer is forbidden**: it is the "AI picked a plausible-sounding number" failure this method exists to prevent. An exception the user expects but the spec never described is type B.

### 10.2 Hotfix — spec debt

Production is burning: **fix first, spec after**; blocking a hotfix to write a spec is using the method wrong, so ship the patch and record the debt rather than drop it:

1. `implement` patches, then adds a line to `specs/_debt.md`:

```markdown
- [ ] 2026-08-07 · hotfix · An order was processed twice when the network dropped midway
      - Patched at: `src/use-cases/checkout/webhook-handler.ts:88`
      - Rule just applied: ignore a callback from the payment gateway if that transaction id was already processed
      - Has anyone CONFIRMED this rule: **no** — need to ask {person name}
      - UC to update: UC-042
      - Due: 2026-08-08
```

2. Within 24h `brainstorm` reopens it, asks the user to confirm the rule, writes it into the UC, ticks the box.
3. `auditor` reports red on anything overdue by more than 3 days.

The line that matters most is **"has anyone confirmed this rule?"**: a hotfix creates rules a developer decided alone at 3am, exactly the ones nobody can later explain.

### 10.3 A workspace with no `docs/specs/` yet

The trigger is the user's, never an agent's: a task needing SDD here stops with `needs_user_input` proposing `/spec init`. `commands/spec.md` § init asks which modules come first; `refs/roles/brainstorm/modes.md` § reverse-engineer, spec-init, spec-scope, spec-debt: `spec-init` writes into `specs/` only after that answer. Init is small (building the whole spec set is the big-bang trap): four directories and `specs/README.md` as the index, and **no UC**: `/spec new` or `/spec reverse` writes the first UC for the part being touched, and a legacy repo runs §7 for **that module only**. The index is invalid without its adoption block (§8.1); `scope` and `modules_in_scope[]` come from the user's answer (§8.2b), and the `Not yet specified:` line names the modules known to have none, or the index lies about coverage.

---

## 11. Against misclassification (HARD)

`spec_required` is derived from the class before anyone knows what the code touches; a small-looking bug that turns out to touch a contract is ordinary. **Do not trust the initial classification.** Re-evaluate at three points, each with more evidence than the last: task start (guess from class) → brainstorm Phase 4 (knows the impact) → implement before commit (knows the real diff) → reviewer on the diff (last net).

### 11.1 Deterministic triggers, by path and pattern

No judgement. A diff touching **any** of these forces `spec_required = true`, whatever the class:

| Group | Patterns |
|---|---|
| Migration / schema | `**/migrations/**` · `**/schema.prisma` · `*.sql` · `**/models/**` with a column added or removed |
| External contract | `**/*.proto` · `openapi*.yaml` · `swagger*.json` · `**/contracts/**` |
| Routing | `**/routes/**` · `**/router/**` · any endpoint declaration, a path added, removed or changed |
| Business state | a value added to an enum with business meaning — status, type, tier, role |
| Permission | `**/policies/**` · `**/permissions/**` · `**/guards/**` · `**/middleware/auth*` |
| Events | a new event, topic or queue name, or a changed payload |
| Business constants | a number with business meaning: a limit, an expiry, a rate, a threshold, a retry count |
| Money and legal | any module containing `payment`, `refund`, `invoice`, `billing`, `tax`, `contract`, `kyc`, `consent` |

A **floor, not a ceiling**: matching nothing here does not mean no spec is needed.

### 11.2 The three nets

**Net 1 — brainstorm, after the dependency trace.** Raise `spec_required` to true when the impact set touches a shared or exported symbol, a contract, a route, a schema or a socket, or matches §11.1; record `spec_required_escalated_from` plus a one-sentence reason so the auditor can measure how often the initial class is wrong. **Raise only, never lower**: a `feature` that turns out "actually simple" keeps `true`, since lowering is a back door around the gate.

**Net 2 — implement, before committing.** With `spec_required: false` but a diff matching §11.1 or adding a business rule, return `blocked_needs_spec` with `spec_required_escalation: true`, the pattern matched and the `file:line`. Exceptions: a `hotfix` never blocks (it logs the debt); a purely mechanical change (rename, format, move) records `spec_scope_note` and proceeds.

**Net 3 — reviewer, the last net.** Even at `spec_required: false`, scan for four strong signals: a new field, column or business enum value · a new route, endpoint or event · a migration or contract file in the diff · a hardcoded business constant with no source. One or more hits → finding `spec_required_misclassified`, 🟠 major. **It does not block by itself**: the user decides whether it is outside SDD scope or a real rule needing an AC; reviewer does not choose, since this is a business decision.

### 11.3 Measuring misclassification

`auditor` counts per window: `spec_required_escalated` (net-1 escalations / total tasks) — above 30% the class criteria need review · `spec_required_misclassified` (net-3 findings / tasks at `false`) — above 10% nets one and two are leaking · **both at zero for several days while large tasks shipped** → suspect the nets are not running, not perfect classification.
