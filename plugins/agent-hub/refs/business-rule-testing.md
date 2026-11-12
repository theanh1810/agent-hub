# Business-rule testing
<Owner: refs/roles/planner/test-cases.md § Business rules>
<Read when: brainstorm lists `change_design.business_rules[]` at change-design, planner or implement writes the cases of a task a rule names, or test chooses its exploratory probes and reports one it cannot judge>

---

Every business rule of a touched screen, API or flow gets one case where it holds and one where it is broken; an unrecorded rule is asked, never guessed (a form once saved a start date after the expiry date uncaught). The one statement; brainstorm, planner and test point here and copy none of it.

## Rule categories

| Category | What it constrains | Example |
|---|---|---|
| cross-field | one field against another | start date ≤ expiry date · min ≤ max |
| state | which transition is allowed from which state | a cancelled order cannot be shipped |
| permission | which role may do it | only the owner edits the pass |
| quota / limit | a count or amount cap, per period or in total | at most 3 passes per member per month |
| step order | a step that needs an earlier one | pay before confirm |

The input kinds — empty, absent, boundary, wrong shape, too large — belong to `rules/code-style/_discipline.md` § 2; a rule above adds to them, never replaces them.

## Where a rule comes from

A rule is listed only from: a UC acceptance criterion or the change's spec delta; the user's own words with their date; a `Q-` id of the analysis record's `user_decisions_verbatim[]`. A rule recorded nowhere (one the code seems to enforce, or one "every app has") is a Clarify question, one decision (`CLAUDE.md` §0.2), answered into `user_decisions_verbatim[]` first. When the spec is silent, the report says "spec missing" and asks the user, never judging by what a user would reasonably expect.

## The record

Brainstorm writes the rules at change-design, at `change_design` level beside `wave_order_evidence`, never as a top-level task key (`agent-hub check plan` rejects it):

```yaml
business_rules:
  - id: RULE-1
    text: start_date <= expiry_date on a pass
    surface: the "borrowed item pass" form and the endpoint that saves it
    source: "user, verbatim"
    task_ids: [W1-T2]
```

`business_rules: []` carries a one-line `business_rules_reason` when the change touches no product rule (a ruleset change, a refactor with no behaviour change).

## The case pair

For each rule, in each task its `task_ids` names: at least one case with `polarity: valid` and one with `polarity: violating`, each carrying `rule_ref: RULE-n`. These are case keys, not kinds: `kind` stays in the enum of `refs/roles/planner/test-cases.md § Kinds` (valid is `happy`, or `edge` at the boundary; violating is `error`).

- **Valid** — input the rule allows, accepted as the source says. A cross-field rule is tested at equality when its source allows equality; a source silent on equality is one more question.
- **Violating** — input the rule forbids. Expected: the stated rejection, the message or error code the source fixes, and nothing written. A rejection message no source fixes is end-user copy, so it is asked too.

## API-direct trigger

When the task changes a server route or handler (its `touches` holds `api`, or its `files[]` holds a route or handler), the violating set adds one case that calls the endpoint directly, bypassing the form: layer `integration` or `contract`, `api_endpoints`, `expected_status` 4xx, `expected_error_code`, and a check that nothing was written — a form check alone does not hold the rule, the server must. A UI-only task gets the screen-level pair only.

## Violation probes

Test's exploratory part (`refs/roles/test/explore.md`) aims probes at the rules of the touched surface, recorded or not:

- reversed dates — end before start, expiry before start;
- zero, a negative, or one past a cap;
- one over a quota, or the same action repeated past its limit;
- a step skipped, repeated or taken out of order;
- the action under a role that should not have it.

A probe against a recorded rule has its oracle and is red or green as usual; a probe against no recorded rule is § Suspected-defect report.

## Suspected-defect report

A probe the system accepted where no recorded rule says whether it should is exploratory status `suspected`, labelled **Suspected defect, needs confirmation**. Test files it for the user to settle and never concludes it is a bug.

- Not red: not written to `errors.yaml`, outside the error-loop cap.
- Listed under `## Suspected defect, needs confirmation` in `explore-r{round}.md`: what was entered, what happened, the rule it would break if that rule holds.
- The run returns `needs_user_input` with one `user_questions[]` entry per suspected case, each one decision — options `Is a defect, must block` · `Allowed` — naming the input and result in plain words.
- Re-spawned with the answers, test re-runs nothing else: `Is a defect` turns the case red with the user's dated words as oracle, `Allowed` green; both are written into `explore-r{round}.md`, and an `Is a defect` answer is a rule brainstorm lists next time.

## Example

"borrowed item pass", RULE-1 `start_date <= expiry_date`, source the user's words:

| Case | Polarity | Steps | Expected |
|---|---|---|---|
| screen | valid | start today, expiry +30 days, save | saved |
| screen | violating | start after expiry, save | rejected with the message the source fixes; nothing saved |
| API-direct, only when the task changes the handler | violating | call the save endpoint with start > expiry | 4xx with its error code; nothing written |

With RULE-1 recorded nowhere, the same reversed-date input is a violation probe: accepted → `suspected`, asked, never red.
