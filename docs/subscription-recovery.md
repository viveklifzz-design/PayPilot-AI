# Failed Subscription / Recurring Payment Recovery Specification

## 1. Overview & Architecture
Failed Subscription / Recurring Payment Recovery is a core capability of PayPilot AI for **Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery**.

In recurring billing (subscriptions, SaaS plans, memberships), automated auto-debit payments may fail due to card limit issues, card expiry, bank authorization timeouts, or insufficient funds. PayPilot AI models recurring billing relationships via the `Subscription` and `SubscriptionPaymentAttempt` domain entities, links failed transactions to recovery cases (`case_type: SUBSCRIPTION_FAILURE`), evaluates the Policy Safety Gate, executes bounded Razorpay Payment Link recovery, and updates subscription state upon receiving a verified payment webhook.

---

## 2. Subscription State Machine

```text
       ACTIVE
          │
          │ (Recurring payment attempt initiated)
          ▼
     PAYMENT_DUE
          │
          │ (Payment fails)
          ▼
   PAYMENT_FAILED
          │
          │ (Policy-approved recovery execution)
          ▼
     RECOVERING ───(payment_link.paid)───► RECOVERED / ACTIVE
          │
          ├───(Retry limit reached)──────► PAST_DUE
          └───(Policy stop / fraud)──────► CANCELLED
```

### Valid State Transitions:
1. `ACTIVE` $\rightarrow$ `PAYMENT_DUE` $\rightarrow$ `PAYMENT_FAILED`
2. `PAYMENT_FAILED` $\rightarrow$ `RECOVERING` (upon policy approval and Razorpay Payment Link creation)
3. `RECOVERING` $\rightarrow$ `RECOVERED` / `ACTIVE` (upon verified payment confirmation)
4. `RECOVERING` $\rightarrow$ `PAST_DUE` (when maximum retries $\ge 3$ reached without payment)
5. `RECOVERING` $\rightarrow$ `CANCELLED` (when policy safely stops or flags fraud)

---

## 3. Data Models (`Subscription` & `SubscriptionPaymentAttempt`)

### `subscriptions` Table:
- `id`: UUID (Primary Key)
- `merchant_id`: Merchant Foreign Key
- `customer_id`: Customer Foreign Key (nullable)
- `plan_name`: Name of recurring plan (e.g., "Pro SaaS Monthly")
- `amount`: Billing amount
- `billing_interval`: `monthly`, `quarterly`, `yearly`
- `status`: `ACTIVE`, `PAYMENT_DUE`, `PAYMENT_FAILED`, `RECOVERING`, `RECOVERED`, `PAST_DUE`, `CANCELLED`
- `next_payment_at`, `last_payment_at`

### `subscription_payment_attempts` Table:
- `id`: UUID (Primary Key)
- `subscription_id`: Subscription Foreign Key
- `transaction_id`: Transaction Foreign Key (nullable)
- `attempt_number`: Attempt count (1, 2, 3...)
- `amount`: Transaction value
- `status`: `PENDING`, `FAILED`, `SUCCEEDED`
- `failure_reason`: Error description text

---

## 4. Policy Gate Rules & Retry Boundaries
- **Maximum Retry Limit**: `MAX_SUBSCRIPTION_RETRIES = 3`. Attempt #4 is blocked by Policy Gate and set to `STOP` / `PAST_DUE`.
- **Mandatory Cooldown**: Minimum 1-hour cooldown enforced between retries.
- **High-Value Threshold**: Subscriptions $> \text{₹50,000.00}$ escalate to human review (`ESCALATE`).
- **AI Confidence Threshold**: AI diagnosis confidence must be $\ge 0.70$ for automated execution.

---

## 5. Environment & Provider Boundaries

> **HONEST SCOPE DECLARATION**:
> PayPilot AI implements the complete recurring subscription recovery decision engine, retry state machine, and Payment Link execution layer. Live Razorpay Subscription Manager APIs require provisioned merchant plan contracts; in this environment, recovery actions execute via **Razorpay Payment Links API in Test Mode** (`rzp_test_...`). No fake money is generated.
