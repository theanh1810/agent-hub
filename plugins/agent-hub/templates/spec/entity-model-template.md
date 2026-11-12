# Conceptual model — {Business group name}

> Prose in this file is written in the reply language (core §1); headings, field labels and ids stay in English.
>
> It answers the question: **which "nouns" is the system talking about?**
>
> This is NOT a database diagram. No data types, no indexes, no foreign keys.
> Record only: names, meaning, the possible states, relations to other nouns.
>
> Why it matters: when the spec uses the right business names, the AI generates classes, functions and tests
> closer to how the team talks every day. Give the AI `tbl_dh_v2` with columns `ma_kh, tt` and it must guess; give it `Order has many OrderItem,
> belongs to one Customer` and it has a hook to hold on to.

---

## Quick info

| Field | Content |
|---|---|
| **Business group** | {e.g. Ordering (Checkout)} |
| **Status** | draft / approved / dug from old code, unconfirmed |
| **Last updated** | YYYY-MM-DD |

## Glossary

| Term | Meaning in this document |
|---|---|
| {Order} | {One time a customer places an order} |
| ... | ... |

> **Warning on one word with several meanings**: if the same word carries two meanings in two places
> (`Order` in Ordering = a purchase order, `Order` in Delivery = a delivery order), split it into two
> separate business groups, one file each. Cramming both into one concept creates a giant class
> that people and AI both misread easily.

---

## {Order}

- **Represents:** {one time a customer places an order}
- **Possible states:** {`draft` → `awaiting_payment` → `paid` → `cancelled` → `manual_review` (needs a person to check by hand)}
- **Relations:**
  - Has many: {OrderItem}
  - Has one: {Payment — only after payment}
  - Belongs to: {Customer}
- **Own rules:** {e.g. an order in status `paid` must not have its amount edited}

## {OrderItem}

- **Represents:** {one line in the order}
- **Belongs to:** {Order}
- **References:** {Product}

## {Payment}

- **Represents:** {one payment transaction}
- **Belongs to:** {Order}
- **Method:** {`qr_code` scan a code / `credit_card` card / `wallet` e-wallet}
- **Possible states:** {`pending` → `success` → `failed` → `refunded`}

---

## Concepts with unclear meaning (for legacy systems)

> Use when digging the model out of an existing database. Record it as it is, mark what needs asking an operator.
> Do not guess and write it down as fact — a wrong spec is more dangerous than a missing one.

| Current name | Guessed meaning | Who to ask | Status |
|---|---|---|---|
| `flag_v2` | {surcharge-policy flag for old contracts signed before 2022-07} | {operations lead} | awaiting confirmation |
| `flag_v3` | {the new surcharge policy} | | confirmed 2026-08-01 |

Rename proposal after confirmation: `flag_v2` + `flag_v3` → `contract_policy_version`.

## History

- v1 (YYYY-MM-DD, {who}): first version
- v2 (YYYY-MM-DD, {who}): {what changed, why}
