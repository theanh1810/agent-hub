# Findings taxonomy — the criteria
<Owner: agents/reviewer.md § Findings taxonomy>
<Read when: Workflow step 3, filing or dismissing a finding in any category>

---

Checked on **every** pass, whatever the mode, except the style categories `mode=independent` skips (`skills/review-checklist/references/independent.md`). The **fourteen** `##` anchors below are the cross-mode categories; the `category` enum in `agents/reviewer.md` § Output holds **twenty-six** values (`python3 tools/check.py ruleset` (agent-hub repo only), check `reviewer_categories_anchored`, counts both from this file). Each anchor carries name, severity and trigger on one line, then criteria, signals and exclusions.

The other **twelve** are raised by a `review-checklist` section or a section of this file, which titles them in prose, not snake_case, so use the table below rather than grepping the enum. A value with no anchor is not a category; a finding fitting none of the twenty-six needs a rule before a label. "Raised from" is not "checked in one mode only": `code_comments` and `commit_message` are read on every pass but `independent`, and only `commit_message` narrows itself, to `mode=merge`. A category is mode-scoped only where its anchor names a mode section of `review-checklist`; § Universal checklist is every mode, so `spec_debt_missing` anchors there and is checked on every pass.

| Enum value | Raised from |
|---|---|
| `security` · `design` · `prd_compliance` | `review-checklist` § security · § design (UI) · § task (compliance) |
| `correctness` · `dead_code` · `reuse_miss` · `perf` · `resource_leak` · `readability` | `review-checklist` § merge → Phase B step 4, bullets **Correctness** · **Dead/orphan code** · **Reuse miss** · **Perf** · **Resource** · **Readability** |
| `code_comments` | this file, § Comment policy |
| `commit_message` | `refs/roles/reviewer/merge-policy.md § Commit policy`, read on `mode=merge` |
| `spec_debt_missing` | `review-checklist` § Universal checklist, bullet **Spec debt** |

The severity in each heading is that section's; `agents/reviewer.md § Severity` maps it to a verdict.

## `handoff_incomplete` — blocking — the upstream agent's output lacks one of the six sections `rules/core.md § Handoff contract` names, or its fenced `json` block

Read the names in `rules/core.md § Handoff contract`. Blocks the wave-close; main re-spawns the agent with the missing parts named. Scout returns the raw object from line 2, with no fenced block. Skip for a gate status such as `needs_user_input`.

## `pattern_violation` — blocking — implement edited ≥10 lines of real logic and cited no `pattern_reference`, or one that does not exist, or one that is unrelated

≥10 lines of real logic (not a typo, rename or comment) and no `pattern_reference: <file:line>`, or a path that does not exist, or an unrelated one (different domain, layer, no matching symbol). Verify the citation by reading it. Skip only on a greenfield repo, where implement writes `pattern_reference: greenfield`.

## `style_source` — 🟠 major, 🔴 blocking when the repo has a style file — the diff contradicts a **measured** line in `{sub_repo}/docs/CODE-STYLE.md`, rank 1 of `rules/code-style/README.md` § Precedence

The diff contradicts a measured line (module system, export shape, error type, test location, casing); measured lines are counts, so contradicting one is drift. Quote the line, its count and the diff line that breaks it.

That file is rank 1 of `rules/code-style/README.md` § Precedence (the cited `pattern_reference` neighbour is rank 4); the ladder is not copied here. The higher rank wins where sources disagree (`_discipline.md` rank 2 or `<language>.md` rank 3 over the neighbour settles a repo with no rank 1). The disagreement is itself a 🟡 finding: name both ranks and which you believe is stale, and why.

No `{sub_repo}/docs/CODE-STYLE.md`: 🟡 `minor`, once per run, suggesting `/codestyle`; never blocking.

## `discipline` — 🟠 major — a breach of `rules/code-style/_discipline.md`, rank 2: file budget · case coverage · length · scope · comments, one finding per breach, each naming its section

The discipline outranks the neighbour: a neighbour dense with comments does not license this diff to be (the carve-out of `refs/roles/implement/craft.md` § Priorities rule 2). One finding per breach, naming the section:

- **§1 file budget**: a new file with no accepted reason · a `utils` / `helpers` / `constants` file for one symbol · a one-call wrapper · an `index` re-exporting one module · more files created than changed, unexplained.
- **§2 case coverage**: an input case neither covered nor declared impossible · an "impossible" with no reason · a boundary the spec names with no test · a retry-or-concurrency claim without evidence.
- **§3 length**: an abstraction with one implementation · a parameter or hook with one caller · configuration for a value that never varied · a second implementation of something the codebase has (cite the original `file:line`).
- **§4 scope**: a changed line tracing to neither the request nor something it broke · formatting or renaming outside the touched functions · a file outside `binding_scope` (that one is 🔴).
- **§5 comments**: a comment matching none of the categories of `_discipline.md` §5 · a needed category missing · a handoff that does not list every comment with `file:line` and category. Filed as `code_comments` under § Comment policy; the list lives only in §5.

The handoff must answer the five questions of `_discipline.md` § The check before the commit; missing answers are `handoff_incomplete`.

## `code_standards` — 🟠 major, 🔴 blocking on implement's Forbidden list — `refs/roles/implement/craft.md` § Priorities and § Craft, and `agents/implement.md` § Forbidden, tested by **"where did the task ask for this line?"**

Read the task's `what`, `purpose` and `files[].why` first; unanswerable is a finding. Blocking when the diff contains anything from implement's Forbidden list:

| Signal | How to find it |
|---|---|
| An abstraction with one caller (interface, strategy, hook, factory) | grep the symbol in the diff, count call sites |
| A config knob, env var or feature flag the task never mentions | compare with `what` + `purpose` |
| A branch no call site reaches | read `files[]`, trace callers |
| A business number or string with no named constant and no source | grep literals in the diff |
| Dead code, commented-out blocks, `_unused` parameters | read the diff |
| `TODO` with no owner and ticket | grep `TODO` |
| A cast dodging the compiler: `as any`, `# type: ignore`, `unwrap()` with no invariant | grep |
| Empty `catch {}`, or `return null` with no explanation | grep |
| A new dependency in `package.json` / `Cargo.toml` / `go.mod` / `requirements.txt` | read those files' diff |
| Reformatting of untouched lines | `git diff -w` much smaller than `git diff` |

Major: complexity >12, nesting >3, more than 4 parameters, a boolean parameter that switches behaviour · a function over 80 lines (a flag to check the job count, not a cap) · naming diverging from the neighbouring file · a helper duplicating one that exists · an assertion loosened to pass · a name no longer describing the code.

## `plan_fidelity` — 🔴 blocking — a file in the diff that is not in `task.files[]`, a commit holding more than one task's work, a task's work split over several commits, or a `review_checkpoint.focus[]` the diff cannot answer

1. **Out of scope**: a file in the diff not in `task.files[]` and not declared in the handoff as rename fan-out or a compile fix. Name the path.
2. **Batched tasks**: a commit holding more than one task's work, or a task's work split over several commits (aside from its acceptance commit, a fix after merge review (`skills/review-checklist/references/merge.md` Phase B step 8), a fix-round commit (`agents/implement.md` Close step) and an acceptance restore commit (`refs/closeout.md` step 2)); or a task snapshot (`refs/roles/implement/close-task.md § Freeze for review`) containing another task's work.
3. **`review_checkpoint.focus[]` not checkable from the diff**: the task or the checkpoint is wrong.

## `spec_drift` — 🔴 critical, blocking — the code implements a business rule no AC covers, or contradicts one that exists. Propose both routes and **choose neither**: it is a business decision, so it goes to the user

One finding per rule, naming `file:line`, the suspected rule and the UC that should have held it. Propose both routes, both to the user: (a) brainstorm adds the AC and the code stands, or (b) implement changes the code to match the existing AC.

Softeners: `hotfix` does not block (check `specs/_debt.md` carries the line; file `spec_debt_missing` 🟠 if not). A class-A bug needs only its regression test bound to the existing AC. A rule already in the UC's `## Open questions` awaiting the user drops to 🟡 with "waiting on user".

## `spec_required_misclassified` — 🟠 major — the third net of `rules/SDD.md` §11, run even when `spec_required: false`. Do **not** block; the user decides whether it is a real new business rule or outside SDD scope

Four strong signals: a new field, column or business enum value · a new route, endpoint, event or topic · a migration or contract file in the diff · a hardcoded business constant with no source noted. Outside SDD scope it merges; a real new business rule goes back to brainstorm for an AC first; the user decides which.

## `spec_readability` — 🟡 minor, only when the diff touches `specs/` — spec prose against `rules/SDD.md` §4: Given/When/Then wording that does not follow the spec language, an AC with no id, an unmeasurable sentence, no `## History`. Never blocking

Violations of `rules/SDD.md` §4: no quick-info table · a technical term with no glossary entry · Given/When/Then wording that does not follow the spec language · class or function names outside `## Technical notes` · an AC with no id · an unmeasurable sentence ("handle it fast", "better UX") · no `## History`. A brownfield spec may be ugly.

## `result_write_back` — 🟠 major — `refs/closeout.md § Recording What a Change Did`: `status: done` with `result: null`, a `result` with no `changes[]` on a task that touched code, a `changes[]` entry with an empty `cost`, or a status disagreeing between the task record and `plan.<lang>.md`, or a finished task missing a `result.ac_check` entry for one of its acceptance criteria, or holding `met: true` with no `evidence`

A task ticked in `tasks.md` whose `Done when:` no command in the handoff shows met · a meaningful change whose handoff has no before/after or an empty cost. Per `refs/closeout.md § What every meaningful change answers` a result with commits and file names but no before/after is a receipt; an empty cost means the trade-off was never considered.

An `ac_check` entry whose `met: true` the diff contradicts (the cited line does not hold the change, or a `tc_id` has no exit-0 row in `result.commands[]`), and an entry with `met: false`, are filed under `prd_compliance` naming the AC id at 🟠 or above: only 🟡 passes the final gate (`agents/reviewer.md` § Severity).

## `closeout_incomplete` — 🟠 major, one case 🔴 — `refs/closeout.md § The five steps, in this order`: the run produced a diff and the handoff has no `closeout:` block, or a field in it is missing or `false`. `plan_written_back: false` **with `status: done`** is the 🔴, and the push hook is not evidence for the other four steps

| Field | What a bad value means |
|---|---|
| `reindex` | The GitNexus graph still describes pre-diff code; every later `impact` is answered confidently from a stale graph |
| `diff_matches_plan: false` | Files changed that no task named: scope creep or an unrecorded decision. Read the listed paths first |
| `plan_written_back: false` **with `status: done`** | **🔴 blocking.** The plan claims work it holds no record of; the one case that blocks alone (see `result_write_back`) |
| `spec_synced` empty while `spec_required: true` | The UC still describes old behaviour; overlaps `spec_drift`, report the closer fit, not both |
| `memory` | `[]` with a stated reason is fine. `[]` with no reason, or more than three entries, is the finding |
| `cleanup` | Covered by `artifact_litter`: report it there; do not double-report |

No push hook exists (step 1 is the only reindex): a handoff citing a hook for any closeout step is the finding.

## `artifact_litter` — 🟠 major — the last net for `refs/artifact-layout.md`, four signals, read against `refs/artifact-layout.md § Where writing is allowed` rather than judged from memory. Also that `.cm-tmp/` and any `~/.claude-backups/{plan_id}/{task_id}` were cleaned

1. A new file outside the `refs/artifact-layout.md § Where writing is allowed` table (read the table).
2. An image, log or dump under `docs/changes/**`, at a **sub-repo root**, or at `{workspace_root}` outside the folders that table lists. Two different places: the first is inside the code, the second one level above.
3. A filename containing `$`, `{`, `}`, or shaped like `test-N` / `screenshot-N`.
4. A **new** `plan_id`, or the `{slug}` of `docs/brainstorm/` or `docs/changes/adhoc/`, with no repo prefix (`refs/artifact-layout.md § Where the workspace root is`, *Paths stay flat*). Existing `plan_id`s are never renamed: flagging one is a false positive.

Also check `.cm-tmp/` and `~/.claude-backups/{plan_id}/{task_id}` (`refs/artifact-layout.md § Ephemeral output`) were cleaned and the handoff has its `cleanup:` line. In a plan's closeout or merge review, a `.cm-tmp/{task_id}` (or `.cm-tmp/{plan_id}`) of the closing plan still present and not named as kept is this finding (the *Closeout sweep* of `refs/artifact-layout.md` § The cleanup gate missed it); the folder this review writes, and any folder of a run with no plan (main thread sweeps it: `refs/artifact-layout.md § The cleanup gate`), are not.

## `redundant_read` — minor — more than two `Read` calls on one file in a session with no `Edit` between them. Warn only, log the waste; auditor tracks the trend

## `jargon_in_option` — minor, major when it touches data or contracts — an `AskUserQuestion` `label` or `description` using a technical term with no plain-language gloss. Propose the replacement wording

Terms such as `debounce`, `idempotent`, `optimistic locking`, `event sourcing`, `SSR/CSR/SSG`, `race condition`, `denormalization`, an algorithm or pattern name. Major when the option touches the data model, an API contract or permission logic (a wrong choice there means data loss or a security hole).

## Design smells (not nits)

Filed under the closest category (`code_standards`, `readability`, `reuse_miss`), each with a named remedy that removes moving pieces:

- A new condition grafted onto an unrelated flow; a condition repeated over one shape signals a missing model or dispatcher.
- A refactor that only moves complexity: count the concepts the reader must hold; unchanged means not cleaner.
- A feature's own logic leaking into a shared module; a near-copy of a standard helper; a vague type boundary (`any`, a cast, a silent fallback hiding an unclear invariant).
- Remedies by name: replace an `if` chain with a dispatcher · merge duplicate branches · split orchestration from business logic · delete a forwarding-only wrapper.

Prefer the remedy that removes moving pieces over one that spreads the same complexity around.
- A change that both refactors and adds behaviour is two changes: say so and ask to split.

## Eight dimensions — the deep review mapped onto the categories above, not a second checklist

Each dimension is looked at once. Column 2 names the category or checklist line already covering each bullet; a bullet nothing covers is the one new line in its row, filed under the closest category. Severity stays 🔴🟠🟡 (`refs/review-trail.md § Severity tags, learning mode, and the dashboard`). A dimension examined with nothing to report is an absence claim listing what was checked; one that does not apply is `N/A: <reason>`, never omitted (on a ruleset, docs or config-only change D and E are `N/A`).

| Dimension and its bullets | Already covered by | Applies when |
|---|---|---|
| A Requirements & Correctness: missing requirements and acceptance criteria · incorrect business rules · inconsistent state transitions · null, undefined, empty, invalid and boundary inputs · unhandled exceptions and partial failures | `prd_compliance` (checklist § task) · `spec_drift` · `correctness` (`skills/review-checklist/references/merge.md` Phase B step 4) · the universal rows of `skills/review-checklist/SKILL.md`: edge cases and error paths, catch-and-swallow | always |
| B Runtime & Algorithms: execution and control flow · async/await and Promise behavior · mutability, reference sharing and side effects · recursion or loop termination · time and space complexity · hidden state and ordering | `correctness` (merge.md step 4: async race, missing await, off-by-one) · `perf` (a number and its source) · new line: a shared reference mutated by its callee, a side effect the signature hides, state relied on and not enforced, or a recursion or loop with no stated end is `correctness`, naming the line | always; async/await and Promise on JavaScript and TypeScript only, elsewhere the language's own primitive |
| C Architecture: DDD boundaries and aggregate invariants · dependency direction and module boundaries · SOLID and unnecessary coupling · contract compatibility and breaking changes · overengineering | contracts: the universal `api_impact` / `route_map` row and merge.md step 4 **Contract** · overengineering: `code_standards` and `discipline` §3 · new line: a crossed domain boundary or invariant, a dependency pointing the wrong way, or coupling the task did not ask for is `code_standards`, naming the two modules | always |
| D Database & Data Integrity: transaction correctness · isolation, concurrent writes and locking · lost updates, deadlocks, inconsistent reads · N+1, indexing, pagination · migrations and rollback compatibility · multi-tenant isolation | `perf` (merge.md step 4 Perf) · merge.md step 5 **Migration** · tenant isolation: `security` · new line: a transaction not covering its writes, an isolation or locking assumption, a lost update, a deadlock or inconsistent read is `correctness`, naming the two racing statements | the change touches a schema, query or migration |
| E Concurrency & Distributed Systems: races · duplicate requests and events · idempotency · retries, timeouts, circuit breakers · message ordering, redelivery, acknowledgment · partial failure · cache invalidation and stampedes | `correctness` (async race) · the universal row on edge cases, error paths and idempotency · `perf` (merge.md step 4, cache checks) · new line: an unbounded retry or timeout, a missing circuit breaker, an ordering, redelivery or acknowledgment assumption, or a stampede gap is `correctness`, naming the failing interleaving | the change touches a queue, retry, cache or cross-process call |
| F Security: authentication and authorization · object-level access control · injection · sensitive data exposure · input validation and output encoding · secrets, dependencies, unsafe defaults · privilege escalation and tenant boundaries | `security` for all seven (`skills/review-checklist/references/security.md`, merge.md step 5, the universal Security row); a dependency added or bumped is checked in `security` mode against Context7 advisories; no new line | always, at the depth security.md sets |
| G Performance & Reliability: blocking operations · CPU and memory · leaks and cleanup · connection pool exhaustion · excessive I/O · bottlenecks under concurrency · observability and recovery | `perf` · `resource_leak` · merge.md step 5 **Telemetry** · new line: recovery after a failure (restart, resume, retry) is named in the change, or a missing one is `correctness` | always |
| H Testability & Production: unit, integration, contract and E2E coverage · missing negative and boundary tests · failure injection and load tests · deployment and backward compatibility · logging, metrics, tracing, alerting · safe rollback | merge.md step 5 **Tests** and the universal test-quality row · `discipline` §2 · merge.md step 5 **Migration** and the plan's rollback strategy · **Telemetry** · new line: failure injection and load tests are expected where the change adds a retry, queue or pool; absence is `discipline` §2 | always |

## Comment policy — `code_comments`, 🟠 major

Enforces `rules/code-style/_discipline.md` §5 (the only statement of permitted categories and forbidden shapes). Judge against the comment block implement's handoff must carry, in both directions.

- **Missing where required** (a §5 category the diff needed): `blocking` for a business rule with no `UC-XXX / AC-N`; `warning` for the rest.
- **Present where forbidden** (matching no §5 category, a stale comment on removed code, a docstring added to fill a quota): `warning`, 🟠 major, not `suggestion` (a `pass` may carry any number of those).
- A missing docstring on an exported symbol is not a defect on its own (quota rule removed 2026-08-31).
- Skip for `target_area: docs`, generated code and test fixtures.
