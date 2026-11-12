# Test craft

Read before the first test of a task. One concept per heading; each rule carries its exception.

## What a test says

- Name = one behaviour, read as a spec. A name with "and" is two tests. One concept per test, arrange-act-assert.
- The expected value is a literal worked out by hand, never computed by the code under test.
- Test through the public interface, not internals. A refactor that keeps behaviour must not break a test; one that does means the test was coupled to the implementation.
- Test behaviour that depends on a constant or a message, not the constant or the wording.
- Repeated data in a test beats a shared fixture that is hard to read.

> DAMP Over DRY in Tests.

- Tests replace, never stack: once the interface of a deep module is tested, delete the old unit tests of the shallow modules it absorbed. A test must survive an internal refactor.
- Test your code at its boundary (the route you register, the query you emit, the payload you build), not framework machinery. A framework behaviour that surprised you gets exactly one characterization test stating the assumption.

> Your code, not the framework.

- Constructors, getters, constants and plain pass-through functions are worth a test only when they validate, normalize, default, derive, enforce or have a side effect; otherwise assert the first result a user sees.
- Before writing a test, name the production change that would make it red and say whether that is a bug or a decision.

## Mocks, fakes, data

Mock only at the system boundary (external API, time, randomness, slow things, side effects). Preference order: the real thing, an in-memory fake, a stub, a call-verifying mock last.

- Each external operation is its own function returning one shape, never one generic conditional `fetch`. Pass dependencies in; do not construct them inside. Never mock your own class.

> Each mock returns one specific shape

- Asserting that a mock exists is meaningless: it passes when the mock is present, fails when it is absent, and says nothing about the real component. Assert real behaviour; if the subject under test is the mock itself, drop the mock or the assertion.

> A mock assertion passes when the mock is present and fails when it is absent

- Before replacing a function with a mock, list the real function's side effects and keep real the ones the test depends on; mock only the slow or external layer beneath it.
- Fake data mirrors real data completely: every documented field, not only the ones the test reads. A mock missing a field passes the test and breaks the integration.

> Mirror real data completely.

- A fake or spy is specific: arguments, call count and order that belong to the contract are asserted. Each branch (success, error, corrupt data) has its own fixture so the wrong branch cannot satisfy the expectation.

> a fake that accepts anything verifies nothing

- Production classes carry production methods only: a cleanup used only by tests goes into a test utility, never a `destroy()` on the real class.

> Production classes carry production methods only.

## Mutation, warning signs, side channels

- Mental mutation: before finishing a test file, imagine one realistic change to the production code (wrong constant or argument, wrong branch, missing state change or side effect, empty or default return, missing validation for zero, empty, unauthorized or malformed input) and name the test that goes red. A mutation nothing catches means the behaviour is unprotected or the test is tautological. The real mutation run is `test`'s (`refs/roles/test/read-only.md`); implement only reasons about it.
- State, not interactions: assert what the function returned or left behind (tasks sorted newest first), not that it called `db.query` with `ORDER BY created_at DESC`; asserting call counts or order is allowed only where they are the contract (obra writing-good-tests.md:20-80, addy test-driven-development SKILL.md:144-300).
- Side channel: a test that proves a write by reading the table directly bypasses the interface a user takes; verify through the interface (`createUser`, then `getUser`), as the caller would (matt tdd tests.md:1-77).
- Warning signs, any one means rewrite the test (writing-good-tests.md:157-198):
  - setup and assertion share one object, so equality is guaranteed;
  - it can fail only through a crash or a missing selector;
  - it fails on every intentional change and never on accidental breakage;
  - expected values hide behind loops, builders or helpers;
  - it greps source text, or asserts a removed symbol stays removed;
  - it exists for coverage and checks no outcome or side effect;
  - an assertion checks a `*-mock` ID, or a method is called only from test files;
  - mock setup is more than half the test, or mocking is "just to be safe".
- Vacuous and snapshot rows (addy testing-patterns.md:229-231): a snapshot of everything is never reviewed, so assert specific values; shared mutable state pollutes tests, so set up and tear down per test; a permanent `test.skip` is dead code, remove or fix it; skipping a test to pass CI hides a bug.
- Rationalizations about the test itself:

| Rationalization | Reality |
|---|---|
| "Tests after achieve the same goal" | Tests after answer what the code does; tests first answer what it should do, and they are biased by the cases you already remembered. |
| "Deleting hours of code is wasteful" | The time is spent either way; code you cannot trust is the waste. |
| "I need to explore first" | Throw the exploration away, then write the test first. |
| "It's just a prototype" | Prototypes become production code. |
| "The code is self-explanatory" | A test is the specification of what it should do, not a description of what it does. |
| "Run it again to be extra sure" | A repeat with no edit in between adds nothing; run again after the next change. |

## Waiting

Flaky tests often guess at timing with a fixed delay (`sleep`, `setTimeout`): they pass on a fast machine and fail under load or in parallel. Wait for the condition the test can observe (an event, a state, a count, a file), not for a guessed duration.
- Poll with a short interval and an upper bound, and read the value inside the loop so the data is fresh; no bound loops forever.
- The failure message names the condition that never held and the time waited.
- A fixed timeout is right only when the code under test is itself time-based (a debounce, a tick interval): first wait for the triggering condition, then wait a duration derived from the known timing, with a comment saying why.

## Design signals

A test that is hard to write, needs everything mocked or has a huge setup signals tight coupling. Design for testability: take dependencies instead of making them, return results instead of effects, keep the surface small. Not knowing how to test it: write the interface you wish existed and its assertion first.
