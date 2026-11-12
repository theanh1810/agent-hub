# Spec debt

> Copy this file to `docs/specs/_debt.md` in the product's workspace folder when first needed.
>
> This is where business rules that went into code but that **nobody has confirmed** are recorded.
> Most come from midnight hotfixes: someone had to decide at once to put out a fire, and
> without a record, three months later nobody can explain why that code exists.
>
> `auditor` scans this file on every run. Overdue by 3 days → red flag.

---

## Owed

- [ ] {YYYY-MM-DD} · {hotfix | error-batch | spec-gap} · {short incident name}
      - Patched at: `{file path:line}`
      - Rule just applied: {a description a non-coder can read and understand}
      - Has anyone CONFIRMED this rule: **no** — need to ask {person name}
      - UC to update: {UC-XXX, or "no UC exists for this flow yet"}
      - Due: {YYYY-MM-DD}

## Filled-in example

- [x] 2026-08-07 · hotfix · An order was processed twice when the network dropped midway
      - Patched at: `src/use-cases/checkout/webhook-handler.ts:88`
      - Rule just applied: ignore a callback from the payment gateway if that transaction id was already processed
      - Has anyone CONFIRMED this rule: **yes** — Owner A confirmed 2026-08-08
      - UC to update: UC-042 → AC-4 added, bump v2
      - Due: 2026-08-08 · **paid**

---

## Rules

- Record at the moment of the patch, not at the end of the day. The memory of "why we chose this way back then" fades very fast.
- The most important line is **"Has anyone confirmed this rule"**. Unconfirmed means
  the system is running on one person's decision made at 3 a.m.
- Paying the debt = ask the business owner → write it into the UC → tick the checkbox, keep the line for history.
- Never delete a ticked line. That history answers "where did this rule come from".
