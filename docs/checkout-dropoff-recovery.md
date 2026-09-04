# Checkout Drop-off Recovery Specification

## 1. Overview & Definition
Checkout drop-off recovery is a core capability of PayPilot AI for **Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery**.

A **Checkout Drop-off** occurs when a customer initiates a payment opportunity (e.g. razorpay order, payment link, or checkout session) but does NOT complete payment within the configured inactivity window (`CHECKOUT_DROPOFF_WINDOW_MINUTES`, default: 30 minutes).

Unlike **Payment Failures** (which trigger explicit `payment.failed` gateway errors), Checkout Drop-offs represent passive abandonments. PayPilot AI detects these abandoned opportunities deterministically, creates a `CHECKOUT_DROPOFF` Recovery Case, passes structured context to Gemini AI, evaluates the Policy Safety Gate, executes Razorpay Payment Link recovery, and converts the case upon receiving a verified `payment_link.paid` webhook.

---

## 2. Architecture & Workflow

```text
Checkout Initiated (CheckoutSession: CREATED)
        │
        │ Inactivity window (30 mins) elapses without payment
        ▼
Checkout Drop-off Detector (CheckoutDropoffDetector)
        │
        ├── Transition CheckoutSession status to DROPPED
        └── Idempotently create RecoveryCase (case_type: CHECKOUT_DROPOFF)
        │
        ▼
Gemini AI Diagnosis Service
        │
        ├── Evaluates checkout context, customer history & abandonment age
        └── Outputs recommended recovery action (e.g., RECOVERY_LINK)
        │
        ▼
Policy Safety Gate (PolicyEngine)
        │
        └── Validates confidence >= 0.70, retries <= 3, cooldown >= 1h, amount <= ₹50k
        │
      ┌─┴─┐
      ▼   ▼
  [ALLOW] [BLOCK]
      │
      ▼
Razorpay Payment Links API (Test Mode)
      │
      ├── Generates plink_... & short URL (https://rzp.io/...)
      └── Creates RecoveryAction (status: CREATED)
      │
      │ (payment_link.paid Webhook Ingested)
      ▼
Verification & Conversion Engine
      │
      ├── Verifies HMAC SHA256 signature
      ├── Transitions CheckoutSession status to CONVERTED
      ├── Transitions RecoveryCase status to RECOVERED
      └── Updates recovered_amount idempotently
```

---

## 3. Data Model (`CheckoutSession` & `RecoveryCase`)

### `checkout_sessions` Table:
- `id`: UUID (Primary Key)
- `merchant_id`: Merchant Foreign Key
- `customer_id`: Customer Foreign Key (nullable)
- `razorpay_order_id`: Razorpay Order ID (nullable)
- `amount`: Transaction value
- `status`: `CREATED` $\rightarrow$ `ACTIVE` $\rightarrow$ `DROPPED` $\rightarrow$ `RECOVERING` $\rightarrow$ `CONVERTED`
- `created_at`, `dropoff_detected_at`, `converted_at`

### `recovery_cases` Table Updates:
- `case_type`: `PAYMENT_FAILURE` vs `CHECKOUT_DROPOFF`
- `checkout_session_id`: CheckoutSession Foreign Key (nullable)

---

## 4. Idempotency & Money Safety
- **Detection Idempotency**: Running `CheckoutDropoffDetector` multiple times over the same inactive checkout session will not create duplicate `RecoveryCase` instances.
- **Conversion Idempotency**: Receiving duplicate `payment_link.paid` webhooks will not double `recovered_amount` or trigger duplicate audit logs.
- **Policy Primacy**: No Razorpay money action occurs without Policy Safety Gate approval (`policy_passed = True`).

---

## 5. CLI Testing & Verification

Run the CLI drop-off simulator to create an abandoned checkout and verify detection:
```bash
cd backend
.\venv\Scripts\python scripts/simulate_checkout_dropoff.py
```
