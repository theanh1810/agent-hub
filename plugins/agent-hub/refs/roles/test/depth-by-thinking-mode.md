# Depth by `thinking_mode`

<Owner: agents/test.md § Depth by `thinking_mode`>
<Read when: Workflow step 2, resolving depth.>

---

## Breadth and depth

Cover what the case names, then the shapes around it: **boundaries** (empty, one, many, the plan's maximum, one past it) · **bad input** (wrong type or format, over-long, whitespace only, unicode, emoji, SQL-ish, script-ish: the app must refuse cleanly; not a security audit) · **wrong order** (submit twice fast, click while loading, navigate away mid-request and back) · **absent preconditions** (not logged in, session expired, no permission, feature off, network dropped). An unreasonable case is worth running: it may be rejected, never corrupt state or crash. Every case records which stage failed.

## The table

Auto-derive when `thinking_mode` is null. A user cue ("test thoroughly", "test in depth", "just run it quickly", or the same words in the reply language) wins. Say which mode ran: green at `quick` and at `extended` are different claims.

| | `quick` | `standard` (default) | `extended` |
|---|---|---|---|
| **When** | smoke, re-run of a fix, hotfix verification, one screen | most tasks: feature ≤3 screens, bug with known repro | new flow ≥4 screens · money, auth, permissions, legal weight · cross-platform parity · release candidate |
| **Stages** | 1 UI · 5 request · 6 backend · 8 binding | all 8 | all 8 |
| **3 FE feel** | skip | loading and error state appear at all | measure: transition, focus, no flash or jump |
| **4 FE perf** | skip | only when the task touches a rendering path | always, with Web Vitals |
| **7 Data** | skip unless plan supplies a read-back | read back when plan supplies a query or endpoint | read back, and check the double-write a retry would cause |
| **Boundaries** | only what the case names | empty · one · many · stated maximum | plus one past the maximum and the order-of-magnitude case |
| **Bad input** | skip | wrong type, wrong format, empty | plus over-long, whitespace-only, unicode, emoji, SQL-ish, script-ish |
| **Wrong order** | skip | double submit | plus click-while-loading, navigate-away mid-request, back-and-return |
| **Absent preconditions** | skip | not logged in | plus expired session, no permission, feature off, network dropped |
| **Unreasonable cases** | skip | skip | run them |
| **Visual regression** | skip | changed screens only | every screen in the flow, at every viewport the design brief names from the `agents/test.md` § Evidence storage list |

## Three rules override the table

1. A case's own layer always runs its stage: an `e2e` visual or a11y check, a `security` case, a `script` case run even in `quick`.
2. A stage that already failed is always re-run; a fix is not verified by a shallower pass than the one that caught the bug.
3. Never downgrade below the plan. Depth narrows each case, never drops a derived one; skipping a listed case is `needs_revision`.

Record the original mode and the reason for every rise; depth only rises, never falls ("it's a one-line change" does not argue it down).

## The patterns that force `extended`

`changed_files[]`, or routes a case's `api_endpoints` name, matching **any** pattern sets `thinking_mode: extended` (same mechanism as `rules/SDD.md` §11.1).

| Group | Patterns |
|---|---|
| Money | `**/payment*/**` · `**/billing/**` · `**/invoice*/**` · `**/checkout/**` · `**/refund*/**` · `**/subscription*/**` · `**/pricing/**` · `**/wallet/**` · `**/transaction*/**` · `**/ledger/**` · `**/payout*/**` |
| Identity and access | `**/auth*/**` · `**/login/**` · `**/session*/**` · `**/token*/**` · `**/oauth/**` · `**/sso/**` · `**/password*/**` · `**/2fa/**` · `**/otp/**` |
| Permission | `**/permission*/**` · `**/role*/**` · `**/policy/**` · `**/policies/**` · `**/guard*/**` · `**/middleware/auth*` · `**/acl/**` · `**/rbac/**` |
| Legal and personal data | `**/kyc/**` · `**/consent/**` · `**/gdpr/**` · `**/audit-log*/**` · `**/contract*/**` · `**/tax/**` · `**/compliance/**` · `**/pii/**` |
| Data integrity | `**/migration*/**` · `**/*.sql` · `**/schema.prisma` · `**/backup*/**` · `**/restore*/**` · `**/seed*/**` |
| Release surface | `**/webhook*/**` · `**/*.proto` · `openapi*.yaml` · `swagger*.json` · `**/contracts/**` |

Business meaning beats the folder name: a `core/` module computing an invoice total is money code. Record the pattern that would have matched in `depth_escalation_reason`.
