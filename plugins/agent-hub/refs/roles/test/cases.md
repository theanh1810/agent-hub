# Test case derivation

<Owner: agents/test.md § Test cases>
<Read when: test derives the cases of a task that is not exempt (§ Exemptions).>

---

## Writing a case

Test derives every case from the task, never from the chat; it adds no kind or layer the rows below do not name.

- Sources, per task of `tasks.md` (`refs/plan-lane.md § tasks.md shape`): each scenario its `Covers:` names (WHEN/THEN from the spec delta under `specs/`, else the live spec), its `Done when:`, and its `Test:` layers. No plan: the acceptance and `flows:` of brainstorm's record (`record_ref`).
- At least one case per covered scenario and one for `Done when:`, at each layer the rows below require. Case id `TC-<task id>-<n>` (`TC-1.2-3`). A case carries `covers`: the scenario names verbatim, or `done-when`.
- The test name in code carries the scenario name; a converted UC's old id survives only inside that title (`rules/SDD.md § 2`).
- A good test checks external behaviour only; the case names a similar test already in the codebase to follow.
- Extra-input lines (inputs or errors the spec implies but no task tests, written by brainstorm under "Also check") become one case each in the task that owns the code, most harmful first: "its silence on an input is not permission for that input to break the program".
- A layer the rows require that the task's `Test:` does not name is a plan gap: a `missing_test_cases[]` entry `{scenario, why_needed}`, never a case of test's own.
- A kind, layer or state the rows require that cannot occur gets one waiver line `{task, kind|layer|state, reason, evidence}` in the `## Round {n} · explore` section of `{plan_dir}/review.md` (no plan: the adhoc record); `evidence` is a `file:line` showing why; a waiver without one is not accepted.
- The derived cases go into `progress.yaml` before the first one runs (`refs/roles/test/resume.md`).

## Layers

Every case carries one `layer`, from the list `Test:` takes (`refs/plan-lane.md § tasks.md shape`), and a `kind` (§ Kinds), orthogonal to the layer:

`unit` · `integration` · `contract` · `e2e` · `security` · `script`

- `unit` — a function, service or business rule alone.
- `integration` — an API with its real database and surrounding parts: connect the real data source, never a mocked one.
- `contract` — frontend and backend agree on request and response shape, checked against the OpenAPI document.
- `e2e` — a real user flow in a browser or on a device; visual and a11y are checks inside the case (`checks: [visual, a11y]`), not layers.
- `security` — abnormal input and vulnerabilities: a ZAP scan plus custom cases.
- `script` — proof by command on the locally running system or the tree: read-only SQL, a metric, a log line or a command's exit code. A repo with no test framework (such as `~/.claude`) uses it.

`api`, `visual`, `a11y` and `local_validation` are not layers: an API call is `integration` (`contract` when checking shape), visual and a11y are checks inside an `e2e` case, a local proof is `script`. There is no layer for speed or load: a measured threshold the design states is a `script` metric.

## Kinds

Every case carries `kind: happy|edge|error|fallback|timeout|retry|security|partial_failure|concurrency`, each drawing on `rules/code-style/_discipline.md` §2: `edge` is its input list (empty, absent, boundary, wrong shape, too large); `error` the error path and the message a person reads; `retry` runs twice (idempotent or not); `partial_failure` fails halfway (what is left, who cleans it); `concurrency` runs concurrently with itself; `timeout` a slow dependency; `fallback` a dependency down or absent and the degraded path; `security` an unauthorized caller or another tenant's data, plus §2's error leaking internals.

Every non-exempt task has ≥1 case of each kind its rows in § Kinds by task type name, or a waiver per missing named kind (§ Writing a case). A kind no row names needs no waiver.

## Layers by what the task touches

Test reads which rows apply from the task's `Files:` and covered scenarios; the layers they require should be the task's `Test:` layers (one missing: § Writing a case).

| Task type | Cases it must carry |
|---|---|
| any implementation task | every covered scenario and the `Done when:` → ≥1 case whose `covers` names it |
| a business-rule scenario, `spec_required` true or false | ≥1 case whose `covers` names it, its test name carrying the scenario name. A business rule with no test is a gap |
| `logic` — a function, service or business rule | ≥1 `unit` |
| `api` — an API route or handler and its data store | ≥1 `integration` on the real store; the data source is never mocked |
| `shape` — a request or response shape between two parts, or a route another part calls | ≥1 `contract` on the producer and on each consumer |
| `screen` — a screen or a user flow | ≥1 `e2e` carrying `checks: [visual, a11y]`, plus § Screen states |
| `input` — user input reaching the server, an auth, role or tenant boundary, or a defence (rate limit, block rule) | ≥1 `security` |
| `state` — persistent state written, a defence, a job, or a change with no test framework | ≥1 `script` |
| any non-exempt task | ≥1 case of each kind its § Kinds by task type rows name, or a waiver per missing kind. Null, empty and limit are `edge`, as is an empty result that is still valid; unauthorized access, another tenant's data and an error leaking internals are `security` |

## Toolset per layer

The tool of each layer is fixed; a repo's existing runner does not override it.

| Layer | Tool |
|---|---|
| `unit` | Jest or Vitest, whichever the repo has (neither: the install task asks once, by the ask-once table of `code-style/README.md` § Test layout); another language: its standard runner (pytest, go test, JUnit, ...) |
| `integration` | Supertest on a JS/TS server; another language: the runner's own HTTP client. The database is a task database from `task-db.sh` (`agent-hub-local-services: refs/local-postgres.md`), the isolated test database of `refs/roles/test/two-pass.md` § Step 1, so the case never reads the development database |
| `contract` | an OpenAPI validator against the repo's OpenAPI document (none: the install task generates or asks for it); same for every language |
| `e2e` | Playwright; same for every language |
| `security` | OWASP ZAP baseline scan plus custom cases in the unit or integration runner; same for every language |
| `script` | no tool: read-only SQL, a metric, a log line or a command |

**Install first.** When the repo lacks the tool of a layer some task needs, brainstorm puts a task `install test toolset` in the plan's first wave; the plan gate approves that dependency, so implement does not ask again. Missing at test time: `missing_test_cases[]`.

**Docker.** The shared Postgres (`agent-hub-local-services: refs/local-postgres.md`) and ZAP need Docker. Absent, the layers needing it are `not_run`, which blocks GREEN (`refs/roles/test/two-pass.md` § Not run).

## Lessons that bind every plan

Each row reads "when the task ..., its cases include ...":

| # | Lesson | When the task | Its cases include |
|---|---|---|---|
| 1 | wiring | adds a parameter or a call | an `integration` or `e2e` case through the real caller proving the value arrives, not only a `unit` case on the callee |
| 2 | mocks | has an `integration` case | no mock of the data source; a `unit` case that mocks it does not count toward `integration` |
| 3 | fired-count | adds or changes a defence | a `script` case with a read-only SQL count of how often the defence fired, expected > 0 after the triggering case |
| 4 | column limit | writes user input to a database column | an `edge` case at the column's maximum length and one past it, under the database's strict mode |
| 5 | fail-open | reads an auxiliary signal (a hint, a fingerprint) that can be malformed | a case whose expected outcome is the rule a scenario or the user's recorded answer states, never assumed; none: `blocked_needs_spec` |
| 6 | sibling parity | has sibling paths in brainstorm's `affected_surfaces[]` (`refs/roles/test/explore.md`) | on every sibling path the same case as its twin, or a stated reason it does not apply |
| 7 | defence trio | adds a defence | cases for a known false positive, a threshold changed at runtime without a deploy, the kill switch (threshold 0 disables the gate), and a system error inside the defence; each expected outcome from a scenario or the user's recorded answer, else `blocked_needs_spec` |

## Fields on a case

On an `integration` or `contract` case calling a route, `api_endpoints` is required; `expected_status` on an HTTP route only; `expected_error_code` when the route returns 4xx/5xx or the IPC command returns `Err`. On other layers they stay optional; populate when known. A `contract` case also carries `contract_ref`, the OpenAPI path and operation it checks.

An `e2e` or component case on a screen task carries `states: [state]` and `themes: [light|dark]`, the states and themes it checks (§ Screen states).

A step of a browser case whose correct outcome shows nothing on the page, in the network or in the URL starts with `[no-effect] `; the test agent then skips the effect rule and the disabled and covered part of the actionability gate for that step (a non-unique target still fails: `skills/testing-e2e/references/browser.md` step 4). The test role writes the prefix only where the expected result says nothing changes.

## Minimum validation by class

| Type | Validation |
|---|---|
| simple | syntax or type check where relevant |
| bug | reproduce it, or explain the repro, plus a targeted regression test |
| hotfix | smoke test plus a rollback path |
| feature | the layers it touches, mapped to the covered scenarios |
| complex | per-wave plus a final integration pass |
| infra | config test, dry run, service status and logs |

UI work: `test` captures a visual snapshot, console errors, network failures and a11y on a real browser or device; spec-only validation is not acceptable.

## Exemptions

| Exempt | Condition |
|---|---|
| a docs-only task | `Covers: none` and every `Files:` path is documentation; unconditional |
| a config-only task with no behaviour surface | still one `script` case: the check its `Done when:` names |
| a pure refactor | `Done when:` states behaviour unchanged; its cases are the existing tests of its `Files:`, re-run in step 1 (`two-pass.md`) |

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

A task whose `Files:` reach a screen gets its states and themes from the design brief's `state_matrix`, else from the screen as built:

- `states` always hold `loading`, `empty`, `error` (with retry), `fallback` (the data source fails), `success` and `disabled`, plus `selected`, `hover` and `focus` where the element has them.
- `themes` is `[light]`, or `[light, dark]` when the app has dark mode.
- Each state has ≥1 `e2e` or component case whose `states[]` names it, in every theme the case's `themes[]` lists, or a waiver (§ Writing a case).

## Lean cases

- No two cases check the same (`covers`, `layer`, state).
- A screen's states are 1-2 table-shaped cases, one row per state (`refs/roles/test/levels.md`, table-driven cases).
- A behaviour a lower layer can check gets no `e2e` case.
- One case may cover several scenarios and states, listed in `covers` and `states`.

## Business rules

A case proving a `business_rules[]` entry of brainstorm's design carries `rule_ref: RULE-n` and `polarity: valid|violating`; `kind` stays in § Kinds. For each rule, in each task its `task_ids` names, write ≥1 `valid` and ≥1 `violating` case, and on a task that changes a route or handler the API-direct violating case. Pair, trigger and worked example: `refs/business-rule-testing.md § The case pair` and `§ API-direct trigger`; not copied here.

Test pyramid, size model and anti-patterns for designing cases inside the layer `Test:` fixed: `refs/vendored/test-design.md`.
