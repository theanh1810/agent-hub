# Spec layer (SDD)

<Owner: agents/test.md § Spec layer (SDD)>
<Read when: `spec_required: true`. With it false, skip this file.>

---

- **Tests bind to the AC, not the implementation.** An assertion on an internal call, private field or mock invocation passes while production breaks.
- **Naming.** A test covering a business AC carries both ids: `describe("UC-042 / AC-2: payment succeeds")`. That name is how AC Coverage is measured; an unnamed test is "not measurable", not coverage.
- **Coverage write-back.** Return `ac_coverage[]` (UC-XXX/AC-N, test name, PASS, evidence; `SDD.md § 3.1` step 2). Closeout step 4 fills `### Test mapping` from it and brainstorm fills the UC's test-mapping table, the primary source for AC Coverage; the grep over test names is only the cross-check. Return only rows a case measured, each with its evidence; never invent a UC mirror. An empty `ac_coverage[]` leaves every AC "not measurable".
- **Test never runs closeout.** Four of its five steps write files test may not touch; `closeout` is a separate spawn after test.
- **`characterization` mode.** Before a refactor, capture current behaviour from real (anonymised) input and output; it proves no change, not correctness. Red after a refactor means behaviour changed: stop and report. Editing it until it passes hides a regression (reviewer files `spec_drift`).
