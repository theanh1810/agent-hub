# Ship checklist — GO / NO-GO

Load before a production deploy, as the last gate after `release.md`. The checklist is read-only evidence gathering; the deploy itself and any rollback are devops steps that need the user's approval (`needs_approval`), and this file never authorises one. Bands, stage sizes and rollback timings are read from groups web_perf, rollout and observability of `templates/thresholds/thresholds.yaml` (`refs/thresholds.md`).

## Checklist
Mark each item pass, fail or not applicable with its evidence (a command output, a dashboard, a file path); an item without evidence is a fail.
- **Code**: tests (unit, integration, e2e), build without warnings, lint and type check pass; review approved; no unresolved TODO and no debug logging in production code; expected failure modes handled.
- **Security**: no secret in code or history; dependency audit clean of critical and high; input validated and authorisation checked on user-facing endpoints; security headers set; rate limit on authentication; CORS limited to named origins.
- **Performance**: Core Web Vitals within the Good band; no N+1 on critical paths; images, bundle and indexes within budget; caching for static assets and repeated queries (budgets from group web_perf).
- **Accessibility**: keyboard use, screen-reader structure, contrast, focus in modals, field-bound error messages, no axe-core or Lighthouse warnings (`skills/testing-e2e/references/a11y.md`).
- **Infrastructure**: production env vars set, migrations applied or ready with a tested down path (`migration.md`), DNS and SSL, CDN, logging and error reporting, health endpoint.
- **Observability**: the dashboards and alerts of `observability.md` exist and were test-fired.
- **Documentation**: README setup notes, API docs, ADRs for architectural decisions, changelog, user-facing docs.

## Decision
Write one decision, GO or NO-GO:
- **Blockers**: must be fixed before shipping, each with its source and `file:line`.
- **Recommended fixes**: should be fixed before shipping.
- **Acknowledged risks**: shipped anyway, each with its mitigation.
- **Rollback plan**: trigger conditions, exact procedure, recovery-time target (timings from group rollout).
- **Reports**: the reviewer, security and test reports the decision rests on.

Any blocker means NO-GO. GO with acknowledged risks is the user's decision, not devops's.

## After launch
In the first hour: health endpoint returns 200, no new error type on the error dashboard, no latency regression, the critical user flow works by hand, logs flow and are readable, and the rollback mechanism was confirmed (dry run where possible).
