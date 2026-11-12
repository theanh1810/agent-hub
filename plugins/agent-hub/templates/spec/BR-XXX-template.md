# BR-XXX: {Business requirement name}

> Prose in this file is written in the reply language (core §1); headings, field labels and ids stay in English.
> This layer answers **why do this work**. Short, measurable, no technical solution yet.
> One BR usually produces a few use cases.

---

## Quick info

| Field | Content |
|---|---|
| **Id** | BR-XXX |
| **Status** | draft / approved / in progress / done |
| **Owner** | {who can decide the scope and the level of success} |
| **Stakeholders** | {who is affected if this is done wrong: operations, customer care, accounting...} |
| **Timeline** | {quarter / month / hard deadline if any} |
| **Last updated** | YYYY-MM-DD |

---

## Glossary

| Term | Meaning in this document |
|---|---|
| {order close rate} | {the number of successfully paid orders divided by the number of times a customer started paying} |
| ... | ... |

---

## Background

{Why this requirement appeared: business situation, customer feedback, legal rule, an incident that happened.}

{Write 3-6 sentences. A newcomer reads this section to understand why the system has this part.}

## Goal

{One clear sentence with a number. Avoid "optimise", "improve", "enhance the experience" unless there is a way to measure it.}

> Good example: Raise the successful-order rate of new customers from 62% to 80% in the third quarter.
> Bad example: Improve the payment experience.

## How it is measured

| Metric | From → to | Measured where | Baseline period |
|---|---|---|---|
| {metric name} | {62% → 80%} | {which dashboard, filtered by what} | {which month} |

## In scope

- {Item 1}
- {Item 2}

## Deliberately NOT done

> This section often saves a project from scope creep. Be explicit, including things everyone assumes are included.

- {Work that will be done in another BR — name that BR}
- {Work decided not to be done in this phase}

## Related use cases

- UC-XXX: {name}
- UC-YYY: {name}

## Constraints

- **Technical:** {e.g. must run on the current system, no database change}
- **Legal / regulatory:** {e.g. comply with the personal data rules}
- **Time:** {hard deadline if any, and the consequence of being late}

## Open questions

- [ ] {A question the business side has not answered}

## History

- v1 (YYYY-MM-DD, {who}): first version
- v2 (YYYY-MM-DD, {who}): {what changed, why}
