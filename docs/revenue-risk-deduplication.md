# Unified Revenue Risk Deduplication Rules

## 1. Core Principle
Revenue at Risk in PayPilot AI must **NEVER** be double counted.

When a payment failure, checkout drop-off, or subscription failure occurs, the financial amount is linked to a single canonical identity. If a checkout session or subscription attempt transitions to `CONVERTED` or `RECOVERED`, it immediately leaves active revenue-at-risk.

---

## 2. Canonical Identity Precedence Order

PayPilot AI enforces deterministic canonical identity in the following hierarchy:

1. `transaction_id`: Top precedence for gateway payment failures.
2. `checkout_session_id`: Deterministic identity for abandoned checkouts.
3. `subscription_payment_attempt_id`: Deterministic identity for recurring subscription failures.
4. `provider_reference` / `razorpay_payment_link_id`: Provider payment reference identity.

---

## 3. Deduplication Scenarios & Rules

### Scenario A: Payment Failure on Abandoned Checkout Session
- **Rule**: If a customer abandons a checkout (`CheckoutSession`), and subsequently attempts payment which fails (`Transaction`), PayPilot AI links the resulting `RecoveryCase` via `transaction_id` and `checkout_session_id`.
- **Deduplication**: Only **one** `RecoveryCase` represents the risk exposure. Active risk amount = `₹X` (not `2 * ₹X`).

### Scenario B: Checkout Conversion / Payment Link Completion
- **Rule**: When a customer completes payment via a Razorpay Payment Link (`payment_link.paid`), `CheckoutSession.status` becomes `CONVERTED` and `RecoveryCase.status` becomes `RECOVERED`.
- **Deduplication**: Active risk calculation filters out `RECOVERED` and `CONVERTED` sessions (`status.in_(['AT_RISK', 'RECOVERING'])`), ensuring converted checkouts cease contributing to active revenue-at-risk.

### Scenario C: Subscription Recurring Payment Retry
- **Rule**: Each recurring payment attempt generates a unique `SubscriptionPaymentAttempt`. Pre-creation lookup verifies no duplicate `RecoveryCase` exists for `subscription_attempt_id`.
- **Deduplication**: Subsequent retries update attempt status rather than creating duplicate active cases.

---

## 4. Exclusion of Approximate Customer Merging
PayPilot AI does **NOT** use fuzzy/approximate customer matching to merge distinct money records. Money records are merged **only** when an explicit foreign key link (`transaction_id`, `checkout_session_id`, `subscription_attempt_id`) connects the entities.
