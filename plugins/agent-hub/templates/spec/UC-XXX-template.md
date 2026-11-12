# UC-XXX: {Use case name in business language}

> Prose in this file is written in the reply language (core §1); headings, field labels and ids stay in English.
> Good name examples: "Order by QR code", "Request leave", "Apply a corporate discount".
> Bad names: "OrderService", "Handle payment API", "Fix checkout flow".

---

## Quick info

| Field | Content |
|---|---|
| **Id** | UC-XXX |
| **Business group** | {e.g. Ordering / Payment / Delivery / Time tracking} |
| **Serves requirement** | BR-YYY — {short name} |
| **Status** | draft / approved / implemented / retired |
| **Owner** | {who can decide the business rules of this UC} |
| **Priority** | Must have / Should have / Nice to have |
| **Last updated** | YYYY-MM-DD |

---

## Summary

**As a** {type of user},
**I want** {what to be able to do},
**so that** {what benefit is reached}.

> Example: As a customer, I want to pay by QR code, so that I do not retype my card details.

---

## Glossary

> Required. Every technical term or internal business word that appears in this file needs one line here.
> A reader who does not code must understand the rest of the file after reading this section.

| Term | Meaning in this document |
|---|---|
| {QRSession} | {One request by a customer to create a QR code. Expires after 15 minutes.} |
| {webhook} | {An automatic message the payment system sends back to us when the customer has paid.} |
| ... | ... |

---

## Actor

{Signed-in customer / Operations staff / Direct manager / External system / Scheduled job}

State it clearly, because each kind leads to different access and checks.

## Trigger

{The customer presses the "QR payment" button in the cart} — or {a webhook from a partner} / {a cron job at 00:00 every day} / {an internal event X}

## Preconditions

- {A condition that must hold before this flow can run}
- {e.g. The customer is signed in}
- {e.g. The cart has at least 1 product}

---

## Main flow

> Write from what the user sees, not from the code's point of view.
> One action per step. More than 8 steps: consider splitting into 2 UCs.

1. {The system shows ...}
2. {The user enters / presses ...}
3. {The system checks ... (details in the Acceptance criteria section)}
4. {The system saves ... and moves the status to ...}
5. {The system notifies ...}

## Alternate flows

> Variants that are still valid. Many bugs appear here, because the business owner thinks "that is obvious" while developers and AI do not.

- **2a. {Variant case}:** {what the system does differently}
- **4a. {Variant case}:** {what the system does differently}

## Decided exceptions

> Record only error cases that already have a decided handling. An undecided error stays in "Open questions".
> The difference: "The QR code expired, so show a message and let the user create a new one" = an exception. "The app crashes when the QR code expires" = a bug.

- **E1. {Situation name}:** {how the system handles it, what the user sees}
- **E2. {Situation name}:** {...}

## After completion

- {The system state after the main flow succeeds}
- {e.g. The order is in status `paid`, the customer receives a confirmation email}

---

## Acceptance criteria

> This is the most important section. Without it, coding must not start.
> Each criterion has its own id (AC-1, AC-2...) so tests can bind to it.

### AC-1: {Short name, readable as what is being checked}

- **Given:** {the starting state}
- **When:** {what the user or the system does}
- **Then:** {the expected, measurable result}
- **And:** {an additional result, if any}

### AC-2: {...}

- **Given:** ...
- **When:** ...
- **Then:** ...

> Writing tip: if you cannot think of a way to verify "Then" in one observable sentence, that AC is still vague.

### Test mapping

| AC id | Priority | Matching test | Status |
|---|---|---|---|
| AC-1 | Most important / High / Medium / Low | `{path of the test file}` | not written / pass / fail |
| AC-2 | | | |

Priority levels:

| Level | Meaning |
|---|---|
| **Most important** | A mistake loses money, corrupts data, or makes the feature unusable |
| **High** | A main feature is affected |
| **Medium** | A secondary feature or the experience |
| **Low** | Surface, cosmetic polish |

---

## Related

- **Must be done first:** {another UC}
- **Depends on this UC:** {another UC}
- **External systems:** {payment gateway, email service, LDAP...}
- **Related technical decision:** {link to an ADR if any}

## Open questions

> Written as checkboxes. A question that blocks the main flow means the UC is not ready for coding.

- [ ] {A question the business side has not answered}
- [ ] {...}

## Technical notes

> The only section allowed to name classes, functions, file paths and code.
> The sections above must be readable without knowing the code.

- {e.g. The expiry rule lives in `src/use-cases/checkout/place-order-qr/expiry.ts`}
- {e.g. Why this approach was chosen over the other}

## History

- v1 (YYYY-MM-DD, {who}): first version
- v2 (YYYY-MM-DD, {who}): added AC-4 for the duplicate-send case, found after a user trial
- v3 (YYYY-MM-DD, {who}): the old AC-2 marked **retired** because the policy changed from 5 minutes to 15 minutes
