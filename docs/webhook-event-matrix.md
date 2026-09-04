# PayPilot AI — Webhook Event Ingestion Matrix

## 1. Webhook Processing Architecture
`POST /api/v1/webhooks/razorpay` receives raw event payloads from Razorpay, verifies HMAC SHA256 signatures, checks `x-razorpay-event-id` for idempotency, and mutates transaction/case state.

---

## 2. Event Handling Matrix

| Webhook Event | Handler Method | Database Mutation | Recovery Case Mutation | Audit Event Emitted | Idempotency Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`payment.failed`** | `_handle_payment_failed()` | Creates/updates `Transaction` (`status: failed`) | Triggers Risk Engine; creates `RecoveryCase` (`status: OPEN`) | `REVENUE_RISK_ASSESSED`, `CASE_CREATED` | Skips if `x-razorpay-event-id` duplicate |
| **`payment.authorized`** | `_handle_payment_authorized()` | Updates `Transaction` (`status: authorized`) | Maintains case state | `WEBHOOK_RECEIVED` | Skips if duplicate event ID |
| **`payment.captured`** | `_handle_payment_captured()` | Updates `Transaction` (`status: captured`) | Marks case `RECOVERED` if active case exists | `RECOVERY_PAYMENT_RECEIVED`, `CASE_RECOVERED` | Skips if duplicate event ID |
| **`payment_link.paid`** | `_handle_payment_link_paid()` | Updates `RecoveryAction` (`status: COMPLETED`) | Marks case `RECOVERED`; updates `recovered_amount` | `RECOVERY_PAYMENT_RECEIVED`, `CASE_RECOVERED` | Single revenue addition; duplicate payload ignored |
| **Unsupported / Unknown** | Default Handler | Inserts `WebhookEvent` record | None | `WEBHOOK_RECEIVED` (ignored) | Returns HTTP 200 (`status: ignored`) |

---

## 3. Webhook Security Controls
- **HMAC SHA256 Signature Match**: Computed using `RAZORPAY_WEBHOOK_SECRET` against raw request bytes. Missing or mismatched signatures return **HTTP 401 Unauthorized**.
- **Idempotency Safeguard**: Every processed `x-razorpay-event-id` is stored. Duplicate events return HTTP 200 (`status: ignored`) without mutating records.
