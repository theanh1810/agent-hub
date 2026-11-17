# Validation levels

1. Focused unit or command, with the tool `refs/roles/test/cases.md` § Toolset per layer names for the layer.
2. Lint, typecheck, build.
3. API smoke (`curl` + token), L3 sanity.
4. Browser UI smoke with `mcp__plugin_playwright_playwright__*`, headless on an in-memory profile (`agents/test.md` § Tools): `browser_navigate`, `browser_snapshot` (scoped per step, full for the a11y pass), `browser_take_screenshot`, `browser_console_messages`, `browser_network_requests`, `browser_evaluate` (Web Vitals), `browser_resize`. Lighthouse: `npx lighthouse <url> --output=json --quiet`, parse the JSON. Evidence dumps take an absolute `filename` into `.cm-tmp/{task_id}/` (`refs/roles/test/browser-lifecycle.md` § Keeping output small).
5. Mobile flow (Detox, Maestro, or simulator).

# Self-critique

- Quality thresholds: a11y ≥90 as the Lighthouse accessibility score (`categories.accessibility.score` ≥ 0.9; the tree pass gives no score, so without Lighthouse write 'not measured'), zero console errors, zero unexpected network failures.
- Visual regression: similarity meets the threshold `agents/test.md` § Evidence storage states.
- Performance (browser): LCP ≤2.5 s, INP ≤200 ms, CLS ≤0.1. Label every number lab or field; write 'not measured' instead of an estimate; measure before and after under the same conditions (addy web-performance-auditor.md:41-51, performance-optimization SKILL.md:8-20,139-172; no ledger, no auto-revert). Needs-work and poor bands: group web_perf (`refs/thresholds.md`).
- Responsive: no overflow at any viewport in the § Evidence storage list.
- Mobile: launch <3 s, no crash, stable memory.
- Network symptom classes to report: CORS, a missing request, a timeout, payload size (addy browser-testing SKILL.md:140-182).
- Coverage: every covered scenario has at least one case across L1-L4, recorded in `ac_coverage[]`; a gap goes to `missing_test_cases[]`.

# Constitutional

- ALWAYS snapshot before an action and wait after navigation.
- ALWAYS audit a11y on a real browser or device, never from the spec.
- ALWAYS capture evidence on failure AND success (baselines).
- ALWAYS observe network during every flow (L3) and assert UI ↔ API binding (L4): it proves the response actually renders.
- Re-snapshot an element that is not found and fail it only if it is still missing; NEVER fail an element-not-found without re-snapshotting.
- Carry `flow_context` through every scenario of the flow; NEVER lose `flow_context` between scenarios.
