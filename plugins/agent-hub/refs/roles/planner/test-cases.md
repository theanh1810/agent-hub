# Test case derivation

<Owner: agents/planner.md § Test cases>
<Read when: brainstorm `mode=change-design` sizing a test plan, and planner Workflow step 4 writing the cases from it, for any task whose `target_area` is not `docs`. A docs-only plan is exempt and never reads this file.>

---

## Writing a case

Planner maps rows to cases; it does not choose test levels (pyramid, group mix, coverage analysis are `test`'s) and adds no kind or layer the test plan does not name.

- A good test checks external behaviour only; the case names a similar test already in the codebase to follow.
- Extra-input lines (inputs or errors the spec implies but no task tests, written by brainstorm under "Also check" in `test_plan`) become one case each in the task that owns the code, most harmful first: "its silence on an input is not permission for that input to break the program".

## Types

Binds only plans whose `plan.yaml` lacks `test_schema: layers`; others use § Layers. Every case carries one `type`, from this list only:

`unit` · `integration` · `api` · `e2e` · `visual` · `a11y` · `script`

- `unit` — one function or module, run with the repo's own framework from its manifest (jest/vitest in `package.json`, pytest in `pyproject.toml`, `cargo test`); the exact command goes in `verification`. No unit framework means a new dependency: ask the user (`CLAUDE.md` §0.2), never pick.
- `integration` — two modules together, not through the route.
- `api` — a call to an HTTP route, handler or IPC command, asserting status or Ok/Err and body.
- `e2e` — a flow in a browser or on a device (replaces `browser`).
- `visual` — a snapshot compare. `a11y` — an accessibility check.
- `script` — a check command run from `verification` (grep, python3, check-ruleset) for work no test framework covers.

`manual-trace` is not a type: implement runs every case.

## Layers

Binds a plan whose `plan.yaml` carries `test_schema: layers`; a plan without it keeps § Types and is not migrated. Every case carries one `layer`, from this list only, and still a `kind` (§ Kinds), orthogonal to the layer:

`unit` · `integration` · `contract` · `e2e` · `security` · `local_validation`

- `unit` — a function, service or business rule alone.
- `integration` — an API with its real database and surrounding parts: connect the real data source, never a mocked one.
- `contract` — frontend and backend agree on request and response shape, checked against the OpenAPI document.
- `e2e` — a real user flow in a browser or on a device; visual and a11y are checks inside the case (`checks: [visual, a11y]`), not layers.
- `security` — abnormal input and vulnerabilities: a ZAP scan plus custom cases.
- `local_validation` — proof on the locally running system: read-only SQL, a metric, a log line or a command's exit code.

Legacy types map to layers for reading older plans: `unit`→`unit`; `integration`→`integration`; `api`→`integration` with its data store, `contract` when checking shape; `e2e`→`e2e`; `visual`, `a11y`→ checks inside an `e2e` case; `script`→`unit` when it runs the repo's test framework, else `local_validation` (a repo with no framework, such as `~/.claude`, is `local_validation`). There is no layer for speed or load: a measured threshold the plan states is a `local_validation` metric.

## Kinds

Every case carries `kind: happy|edge|error|fallback|timeout|retry|security|partial_failure|concurrency`, each drawing on `rules/code-style/_discipline.md` §2: `edge` is its input list (empty, absent, boundary, wrong shape, too large); `error` the error path and the message a person reads; `retry` runs twice (idempotent or not); `partial_failure` fails halfway (what is left, who cleans it); `concurrency` runs concurrently with itself; `timeout` a slow dependency; `fallback` a dependency down or absent and the degraded path; `security` an unauthorized caller or another tenant's data, plus §2's error leaking internals.

The nine bind a plan first written after claude-test-kinds-and-done-checks closed; an earlier plan keeps `happy|edge|error`. The rows of § Kinds by task type bind a plan first written after claude-openspec-pilot closed; an earlier plan keeps every kind or its waiver.

Every non-exempt task has ≥1 case of each kind its rows in § Kinds by task type name, or one `case_kind_waivers[]` entry `{kind, reason, evidence}` per missing named kind; `evidence` is a `file:line` showing why the kind cannot occur, and a waiver without one fails `agents/planner.md § Quality gates`. A kind no row names needs no waiver. `case_kind_waivers[]` sits beside `test_cases[]`, never inside, because implement runs every entry of `test_cases[]` (`agents/implement.md § Hard gates`, gate 6).

## Layers by what the task touches

Binds a plan whose `plan.yaml` carries `test_schema: layers`; a plan without it keeps § Legacy rows. A task declares the touch rows that apply in `touches: [logic|api|shape|screen|input|state]` and carries one `layer_waivers[]` entry `{layer, reason, evidence}` per required layer it cannot have; `evidence` is a `file:line`, as in `case_kind_waivers[]`.

| Task type | Cases it must carry |
|---|---|
| any implementation task | every `acceptance_criteria` entry → ≥1 case via `covers_acceptance`, written `{task_id}/AC-n` or the `UC-XXX/AC-N` the criterion names after `→`, traceable both ways (`agent-hub check plan` ac_trace) |
| a business-rule AC, `spec_required` true or false | ≥1 case whose `covers_acceptance` names it. With `spec_required: true` the AC is one in `covers_uc` and the test name carries UC-ID and AC-ID. A business AC with no test fails `agents/planner.md § Quality gates` |
| `logic` — a function, service or business rule | ≥1 `unit` |
| `api` — an API route or handler and its data store | ≥1 `integration` on the real store; the data source is never mocked |
| `shape` — a request or response shape between two parts, or a route another part calls | ≥1 `contract` on the producer and on each consumer |
| `screen` — a screen or a user flow | ≥1 `e2e` carrying `checks: [visual, a11y]`, plus § Screen states |
| `input` — user input reaching the server, an auth, role or tenant boundary, or a defence (rate limit, block rule) | ≥1 `security` |
| `state` — persistent state written, a defence, a job, or a change with no test framework | ≥1 `local_validation` |
| any non-exempt task | ≥1 case of each kind its § Kinds by task type rows name, or a waiver per missing kind. Null, empty and limit are `edge`, as is an empty result that is still valid; unauthorized access, another tenant's data and an error leaking internals are `security` |

### Legacy rows, plans without `test_schema: layers`

The first, business-rule and last rows above apply to every plan. These four stay for a plan keeping § Types:

| Task type | Cases it must carry |
|---|---|
| UI | ≥1 `e2e`, ≥1 `visual`, ≥1 `a11y` |
| API or contract | ≥1 `integration` on the producer and on each consumer |
| touches code logic | ≥1 `unit` |
| touches an API | ≥1 `api`, whose `api_endpoints` lists every endpoint the task touches |

## Toolset per layer

Binds a `test_schema: layers` plan. The tool of each layer is fixed; a repo's existing runner does not override it.

| Layer | Tool |
|---|---|
| `unit` | Jest or Vitest, whichever the repo has (neither: the install task asks once, by the ask-once table of `code-style/README.md` § Test layout); another language: its standard runner (pytest, go test, JUnit, ...) |
| `integration` | Supertest on a JS/TS server; another language: the runner's own HTTP client. The database is a task database from `task-db.sh` (`refs/local-postgres.md`), the isolated test database of `refs/roles/test/two-pass.md` § Step 1, so the case never reads the development database |
| `contract` | an OpenAPI validator against the repo's OpenAPI document (none: the install task generates or asks for it); same for every language |
| `e2e` | Playwright; same for every language |
| `security` | OWASP ZAP baseline scan plus custom cases in the unit or integration runner; same for every language |
| `local_validation` | no tool: read-only SQL, a metric, a log line or a command |

**Install first.** A plan whose repo lacks a tool of a layer some task needs carries a first task in its first wave, `install test toolset`, before any task whose cases need it; the plan gate approves that dependency, so implement does not ask again.

**Docker.** The shared Postgres (`refs/local-postgres.md`) and ZAP need Docker. Absent, the plan carries a `user_actions` entry (install Docker) before the first wave, and until done the layers needing it are `not_run`, which blocks GREEN (`refs/roles/test/two-pass.md` § Not run).

## Lessons that bind every plan

Each row reads "when the task ..., the plan carries ...":

| # | Lesson | When the task | The plan carries |
|---|---|---|---|
| 1 | wiring | adds a parameter or a call | an `integration` or `e2e` case through the real caller proving the value arrives, not only a `unit` case on the callee |
| 2 | mocks | has an `integration` case | no mock of the data source; a `unit` case that mocks it does not count toward `integration` |
| 3 | fired-count | adds or changes a defence | a `local_validation` case with a read-only SQL count of how often the defence fired, expected > 0 after the triggering case |
| 4 | column limit | writes user input to a database column | an `edge` case at the column's maximum length and one past it, under the database's strict mode |
| 5 | fail-open | reads an auxiliary signal (a hint, a fingerprint) that can be malformed | a case whose expected outcome is the rule brainstorm asked the user, from the record's `confirmed_values`, never assumed; no confirmed rule: `blocked_needs_spec` |
| 6 | sibling parity | has sibling paths in the analysis's `affected_surfaces` | on every sibling path the same case as its twin, or a stated reason it does not apply |
| 7 | defence trio | adds a defence | cases for a known false positive, a threshold changed at runtime without a deploy, the kill switch (threshold 0 disables the gate), and a system error inside the defence; each expected outcome from a user-confirmed acceptance criterion, else `blocked_needs_spec` |

## Fields on a case

On an `integration` or `contract` case calling a route, `api_endpoints` is required; `expected_status` on an HTTP route only; `expected_error_code` when the route returns 4xx/5xx or the IPC command returns `Err`. On other layers they stay optional, as does `affected_test_cases` on the task (they let the test agent check response content and name the cases a fix reached); populate when known. A `contract` case also carries `contract_ref`, the OpenAPI path and operation it checks. A plan without `test_schema: layers` keeps these on its `api` cases.

An `e2e` or component case on a screen task carries `states: [state]` and `themes: [light|dark]`, the states and themes it checks (§ Screen states). `state_waivers[]` sits beside `test_cases[]`, never inside, for the same reason as `case_kind_waivers[]`.

A step of a browser case whose correct outcome shows nothing on the page, in the network or in the URL starts with `[no-effect] `; the test agent then skips the effect rule and the disabled and covered part of the actionability gate for that step (a non-unique target still fails: `skills/testing-e2e/references/browser.md` step 4). Planner writes the prefix only where the expected result says nothing changes.

## Exemptions

| Exempt | Condition |
|---|---|
| `target_area: docs` | unconditional |
| `target_area: infra` | config-only with no behaviour surface; still needs a `verification` step |
| a pure refactor | `preserve_api: true`, and the task records `inherits_tests_from: [task_id]` |
| the `closeout` task | `test_cases: []`, as the CLOSEOUT note of `templates/plan/task-template.yaml` shows |

An exempt task needs neither kinds nor waivers.

## Kinds by task type

Test cases scale with the size and kind of the task: a fix unrelated to the UI, for example, needs no UI test. A task takes the union of the rows its change matches, and may add any other kind with its reason.

| The change | Kinds it needs |
|---|---|
| a check, script or config with no runtime surface | `happy`, `error` (passes on the change, fails on a cut copy) |
| code logic | `happy`, `edge`, `error` |
| calls a dependency (database, network, file, queue, service) | adds `timeout`, `fallback`, `partial_failure` |
| writes state a caller may repeat (handler, job, migration) | adds `retry` |
| state shared with parallel callers | adds `concurrency` |
| input crossing a trust boundary (auth, another tenant's data, user input) | adds `security` |
| a route or handler whose surface carries a business rule | the API-direct violating case of § Business rules |

Layers follow § Layers by what the task touches the same way: a task reaching no screen carries no `e2e` case.

## Screen states

Binds a plan whose `validation_strategy` carries `state_case_standard: 1`; an earlier plan keeps § Layers by what the task touches alone.

A task with `touches: [screen]` declares `screen_states: {states: [...], themes: [...]}`:

- `states` always hold `loading`, `empty`, `error` (with retry), `fallback` (the data source fails), `success` and `disabled`, plus `selected`, `hover` and `focus` where the element has them.
- `themes` is `[light]`, or `[light, dark]` when the app has dark mode.
- Each state has ≥1 `e2e` or component case whose `states[]` names it, in every theme the case's `themes[]` lists; or one `state_waivers[]` entry `{state, reason, evidence}`, `evidence` a `file:line`, as in `case_kind_waivers[]`.

## Lean cases

Binds a plan whose `validation_strategy` carries `state_case_standard: 1`.

- No two cases check the same (`covers_acceptance`, `layer`, state).
- A screen's states are 1-2 table-shaped cases, one row per state (`refs/roles/test/levels.md`, table-driven cases).
- A behaviour a lower layer can check gets no `e2e` case.
- One case may cover several ACs and states, listed in `covers_acceptance` and `states`.
- `agent-hub check plan` WARNs on a duplicate (`chk_duplicate_cases`) and never blocks.

## Business rules

A case proving a `change_design.business_rules[]` entry carries `rule_ref: RULE-n` and `polarity: valid|violating`; `kind` stays in § Kinds. For each rule, in each task its `task_ids` names, write ≥1 `valid` and ≥1 `violating` case, and on a task that changes a route or handler the API-direct violating case. Pair, trigger and worked example: `refs/business-rule-testing.md § The case pair` and `§ API-direct trigger`; not copied here.
