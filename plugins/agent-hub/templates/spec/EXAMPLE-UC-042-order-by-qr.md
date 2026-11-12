# UC-042: Order by QR code

> A filled-in sample for comparing writing style. It is not a real spec of any project.

---

## Quick info

| Field | Content |
|---|---|
| **Id** | UC-042 |
| **Business group** | Ordering (Checkout) |
| **Serves requirement** | BR-007 — Raise the conversion rate of new customers |
| **Status** | implemented |
| **Owner** | Owner A (sales business owner) |
| **Priority** | Must have |
| **Last updated** | 2026-08-07 |

---

## Summary

**As a** customer,
**I want** to pay for an order by scanning a QR code,
**so that** I do not retype my card details on every purchase.

---

## Glossary

| Term | Meaning in this document |
|---|---|
| QR code | A square image holding the order and the amount; the customer scans it with a banking app to pay |
| QR session (QRSession) | One press of the create-code button. Each session lives 15 minutes and then expires. An order can have several sessions if the customer creates the code again |
| Payment gateway | The partner that moves money between the customer's bank and the company account |
| Callback (webhook) | An automatic message the payment gateway sends back to our system when the customer has paid. Like a courier ringing the bell to say "delivered" |
| Awaiting manual check (manual_review) | The order status when the system cannot decide by itself and staff must look |

---

## Actor

Customer — may be logged in or not.

## Trigger

The customer presses the "QR payment" button on the cart screen.

## Preconditions

- The cart holds at least 1 product and the total is greater than 0
- The customer has chosen QR as the payment method

---

## Main flow

1. The system creates a QR code holding the order id, the amount and the expiry time.
2. The system shows the QR code with a countdown of the time left.
3. The customer opens the banking app and scans the code.
4. The payment gateway sends a callback to the system when the customer has paid.
5. The system moves the order to the paid status, sends a confirmation email and an in-app notification.

## Alternate flows

- **2a. The customer is not logged in:** go to the quick login flow (UC-005), and return to step 2 when it is done.
- **4a. The callback arrives more than 30 seconds late:** the screen shows the "confirming" status instead of an error, and the customer does not pay again.

## Decided exceptions

- **E1. The QR code is older than 15 minutes:** show "The QR code has expired, please create a new one", with a button to create a new code.
- **E2. The amount the customer transferred does not match the order:** the system refunds automatically and logs the incident for staff to see.
- **E3. No callback after 30 minutes:** move the order to the awaiting manual check status, do not cancel it automatically.

## After completion

- The order is in the paid status
- The customer received a confirmation email
- A payment record is linked to the order

---

## Acceptance criteria

### AC-1: QR code created successfully

- **Given:** the customer has a cart above 0 and has chosen QR payment
- **When:** the customer presses "QR payment"
- **Then:** the system creates a QR session whose expiry time = press time + 15 minutes
- **And:** the screen returns the QR image with a countdown

### AC-2: Payment succeeds within the valid time

- **Given:** the QR session has 5 minutes left
- **When:** the payment gateway reports success, with the right order id and the right amount
- **Then:** the order moves to the paid status
- **And:** the confirmation email is sent within 10 seconds

### AC-3: Payment after the code has expired

- **Given:** the QR session is older than 15 minutes
- **When:** the payment gateway still reports success
- **Then:** the system starts a refund by itself
- **And:** the order stays in the awaiting payment status
- **And:** the incident is logged with a lookup id

### AC-4: Two callbacks arrive for the same order

- **Given:** the order is already paid because of the first callback
- **When:** the payment gateway sends the callback again for that order
- **Then:** the system ignores it and creates no extra payment record
- **And:** no second confirmation email is sent

### Test mapping

| AC id | Priority | Matching test | Status |
|---|---|---|---|
| AC-1 | High | `tests/integration/use-cases/checkout/place-order-qr/AC-1-create-qr.test.ts` | pass |
| AC-2 | Most important | `.../AC-2-payment-success.test.ts` | pass |
| AC-3 | Most important | `.../AC-3-qr-expired.test.ts` | pass |
| AC-4 | Most important | `.../AC-4-duplicate-webhook.test.ts` | pass |

---

## Related

- **Must be done first:** UC-005 (quick login)
- **Depends on this UC:** UC-043 (cancel order and refund)
- **External systems:** the payment gateway, the email sending service
- **Related technical decision:** the decision record on event-driven payment handling

## Open questions

- [ ] Is there a limit on how many times in a row a customer can create the QR code again?
- [x] Is expiry 15 minutes or 5 minutes? → Owner A confirmed 15 minutes, on 2026-07-20

## Technical notes

- The expiry rule lives in `src/use-cases/checkout/place-order-qr/expiry.ts`
- Callback de-duplication uses the gateway's transaction id, not the order id — because one order can have several QR sessions

## History

- v1 (2026-07-15, Owner A): first version, with the Main flow and E1
- v2 (2026-07-22, Owner B): added AC-4 after a trial user found an order processed twice when the network dropped midway
- v3 (2026-08-07, Owner A): clarified E3, the order is not cancelled automatically but moved to awaiting manual check
