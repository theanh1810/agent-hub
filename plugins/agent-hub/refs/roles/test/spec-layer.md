# Spec layer (SDD)

<Owner: agents/test.md § Spec layer (SDD)>
<Read when: `spec_required: true`. With it false, skip this file.>

---

- **Tests bind to the scenario, not the implementation.** An assertion on an internal call, private field or mock invocation passes while production breaks.
- **Naming.** A test covering a scenario carries the scenario name in its test name (a converted UC's old id survives inside that title, `rules/SDD.md § 2`). That name is how coverage is measured (`rules/SDD.md § 8.2`); an unnamed test is "not measurable", not coverage.
- **Coverage write-back.** Return `ac_coverage[]`, one row per scenario `{scenario, test, covered}`; brainstorm reads it before archive (`rules/SDD.md § 3.1`). Return only rows a case measured, its evidence in `commands[]`. An empty `ac_coverage[]` leaves every scenario "not measurable".
- **Test never runs closeout.** Four of its five steps write files test may not touch; `closeout` is a separate spawn after test.
- **`characterization` mode.** Before a refactor, capture current behaviour from real (anonymised) input and output; it proves no change, not correctness. Red after a refactor means behaviour changed: stop and report. Editing it until it passes hides a regression (reviewer files `spec_drift`).
