# Browser order for the test role

<Owner: agents/test.md § Tools>
<Read when: any browser case, before choosing the driver for it.>

---

1. Driver for a browser case: qa-pilot first; Playwright when qa-pilot is not OK for that case; chrome-devtools only for a case tagged `perf`.
2. qa-pilot is not OK when:
   - its server is not loaded or the key is missing;
   - the same step fails twice;
   - its verdict comes without a screenshot or a step log;
   - the page shows protected data (production, real customer data, secrets);
   - the case needs evidence its tools do not produce.
   - qa-pilot sends page content and screenshots to a vision-model API, so it runs only on local, dev and staging pages with seed data; other pages go to Playwright. The user may widen this per project.
3. A red from qa-pilot is rerun with Playwright before it is filed: red twice, filed with both outputs; green on Playwright, pass, noted "qa-pilot red not reproduced".
4. Evidence is the same whatever the driver: screenshot, console errors, network failures, a11y. Playwright collects what the driver cannot.
5. `perf`: trace, Core Web Vitals, throttling, CPU profile through chrome-devtools on a local or staging page; numbers and the trace path go into the report; thresholds from `refs/thresholds.md`.
6. Never run `npx qa-pilot init` or any installer; never `browser_run_code_unsafe`.
7. One driver per case at a time; sessions are closed at the end. The report names `driver` and `fallback_reason` per case.
