# Choosing the test level, and judging coverage

<Owner: agents/test.md § Workflow step 1>
<Read when: choosing the level or shape of an exploratory case or of a `missing_test_cases[]` proposal, mapping ACs to cases, or checking a diff against its requirements.>

---

User decision 48: test chooses the levels of what it adds (part b, `missing_test_cases[]`); plan cases keep the plan's layer.

## Which level

- Lowest level that catches the behaviour: pure logic → unit; crossing a boundary (API, database, file system) → integration; only critical flows → E2E. No E2E for what a unit test covers.
- The pyramid is a suggested ratio: mostly small tests (milliseconds, one process, no I/O), fewer medium (seconds, localhost), very few large (minutes, external services).
- Test only this code's behaviour, never a third-party library. Each test builds and cleans its own state (passes alone, fails together = isolation bug).
- Watch each test go red for the right reason before trusting it: a test that can never go red is as useless as one that is always red.

## What a test asserts

- A script runs with controlled input, then asserts output, side effect or exit code; a doc that instructs an agent is tested by the agent's behaviour; prose for readers needs no test. Asserting that a file contains an exact line proves only that the source is the source.
- Prefer table-driven cases with hand-written literal expectations: each row independent, expectation never derived from the code under test.
- Bind to the AC, never to implementation: no assertion on internal calls or mocks.
- A function or component covers five groups: happy path; empty input (string, array, null); boundary (smallest, largest, one, many, 0, negative, over max); error path and bad input (wrong type, network drop, timeout); concurrency, wrong order, missing precondition.

## Coverage mapping

- Every AC has at least one case, traceable both ways; an AC with no case is reported missing. Each endpoint the code changed has one case observing it and one checking its UI link; each error code in the contract has a case triggering it.
- Suggested additions are ranked: critical (data loss, security) · high (core business logic) · medium (edges and errors) · low (utility, formatting).

## Matching requirements to the diff

- Name three failure kinds: missing (skipped, or claimed but not done), extra (a feature nobody asked for), misread (right feature, wrong way, or the wrong problem solved).
- A task listing several files, one change each: match each file to its hunk. A named file the diff does not touch is missing even if the rest is clean.
- A requirement living in unchanged code, or spread across tasks, that cases cannot check from the diff goes in a separate "not checkable from the diff" list with the reason; never guess.
- Before saying "meets the requirements" go line by line: re-read plan → checklist → verify each → report gaps. A green suite does not replace it.
