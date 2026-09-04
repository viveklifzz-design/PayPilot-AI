# PAYPILOT AI — FINAL USER JOURNEY AUDIT REPORT

## 1. Executive Summary & Journey Audit Matrix

This report documents the end-to-end verification of all 7 core user journeys in **PayPilot AI** for **Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery**.

Every journey is tracked across 9 technical verification criteria:
`CODE → API → DATABASE → UI → RUNTIME → TEST → DATA CLASSIFICATION → AUDIT → IDEMPOTENCY`

---

## 2. User Journey Verification Table

| Journey | Business Flow | Code File | API Endpoint | DB Model | Data Classification | Idempotency | Final Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| **JOURNEY A** | Razorpay Payment Failure $\rightarrow$ Error Facts $\rightarrow$ AI Diagnosis $\rightarrow$ Policy Gate $\rightarrow$ Recovery Link $\rightarrow$ Webhook $\rightarrow$ `RECOVERED` | `app/api/v1/endpoints/webhooks.py` | `POST /api/v1/webhooks/razorpay` | `Transaction`, `RecoveryCase` | **REAL PROVIDER VERIFIED** | **YES** | **REAL VERIFIED** |
| **JOURNEY B** | Checkout Drop-off $\rightarrow$ Detection ($30\text{m}+$) $\rightarrow$ Recovery Link $\rightarrow$ Conversion $\rightarrow$ Active Risk Removal | `app/services/revenue_risk/dropoff_detector.py` | `GET /api/v1/revenue-risk/summary` | `CheckoutSession`, `RecoveryCase` | **LOCAL TEST VERIFIED** | **YES** | **LOCAL TEST VERIFIED** |
| **JOURNEY C** | Subscription Failure $\rightarrow$ Attempt Failure $\rightarrow$ Policy Limits $\rightarrow$ Recovery Link $\rightarrow$ Active Subscription | `app/services/revenue_risk/subscription_recovery.py` | `GET /api/v1/revenue-risk/summary` | `Subscription`, `RecoveryCase` | **LOCAL TEST VERIFIED** | **YES** | **LOCAL TEST VERIFIED** |
| **JOURNEY D** | B2B Receivable $\rightarrow$ Overdue $\rightarrow$ Reminders ($\le 3$) $\rightarrow$ Promise-to-Pay $\rightarrow$ Fulfilled/Missed Escalation | `app/services/revenue_risk/receivables_service.py` | `GET /api/v1/receivables` | `Invoice`, `RecoveryCase` | **LOCAL TEST VERIFIED** | **YES** | **LOCAL TEST VERIFIED** |
| **JOURNEY E** | Mandate Retry Sequencer $\rightarrow$ Failed Attempt $\rightarrow$ Retries 1–3 $\rightarrow$ 24h Cooldown $\rightarrow$ Max Retry Escalation | `app/services/revenue_risk/mandate_service.py` | `GET /api/v1/mandates` | `Mandate`, `RecoveryCase` | **LOCAL TEST VERIFIED** | **YES** | **LOCAL TEST VERIFIED** |
| **JOURNEY F** | Customer Portal $\rightarrow$ Login $\rightarrow$ Transaction Lookup $\rightarrow$ Error Facts $\rightarrow$ Recovery Action $\rightarrow$ Ownership Protection | `app/api/v1/endpoints/customer_portal.py` | `GET /api/v1/customer/transactions/{id}` | `Customer`, `Transaction` | **REAL PROVIDER VERIFIED** | **YES** | **REAL VERIFIED** |
| **JOURNEY G** | Communication Layer $\rightarrow$ Hinglish / Hindi / English Messages $\rightarrow$ Voice Scripts $\rightarrow$ No Money Movement Invariant | `app/services/recovery/communication_service.py` | `POST /api/v1/communication/generate` | N/A | **LOCAL TEST VERIFIED** | **YES** | **LOCAL TEST VERIFIED** |

---

## 3. Journey-by-Journey Evidence Logs

### JOURNEY A: Real Razorpay Payment Failure Recovery
- **Original Failure**: Transaction `BAD_REQUEST_PAYMENT_TIMED_OUT` (Reason: `payment_verification_failed`)
- **Razorpay Link**: `plink_TThMwMCq60gAju` (`https://rzp.io/rzp/5MH8i3p`)
- **Webhook Ingestion**: `payment_link.paid` HMAC SHA256 Verified
- **Recovered Amount**: ₹2,500.00 updated cleanly
- **Audit Log**: 2 chronological events logged

### JOURNEY B: Checkout Drop-Off Recovery
- **Session Tracking**: `CheckoutSession` created, status `DROPPED` after 45m inactivity
- **Conversion Path**: Payment Link paid transitions session to `CONVERTED` and case to `RECOVERED`

### JOURNEY C: Failed Subscription Recovery
- **Subscription Attempt**: Attempt #1 failed (`decline_by_bank`)
- **Policy Enforcement**: Cooldown (1h), Amount cap ($\le \text{₹50k}$), Retries ($\le 3$)
- **Status Transition**: Payment attempt `SUCCEEDED`, subscription `ACTIVE`

### JOURNEY D: B2B Receivables Chaser & Promise-to-Pay
- **Overdue Detection**: Invoice `INV-VERIFY-1787594805` (10 days overdue) $\rightarrow$ `B2B_RECEIVABLE` case formed
- **Promise Registration**: Promise date registered $\rightarrow$ `PROMISE_TO_PAY` status
- **Missed Promise**: Simulated missed promise date $\rightarrow$ Auto-escalated to `ESCALATED`

### JOURNEY E: Mandate Retry Sequencer
- **Attempt Sequencing**: Attempt 1 (`RETRYING`, 24h cooldown) $\rightarrow$ Attempt 2 (`RETRYING`) $\rightarrow$ Attempt 3 (Cap reached $\rightarrow$ `CANCELLED` & `ESCALATED`)

### JOURNEY F: Customer Portal & Security
- **Customer Login**: `/api/v1/customer/login` returns `auth_token`
- **Ownership Security**: Customer A accessing Customer B's transaction ID returns **`HTTP 403 Forbidden`**

### JOURNEY G: Hinglish Communication Layer
- **Localized Messages**: Generates localized Hinglish SMS text and voice call scripts ("Namaste Rahul...")
- **Safety Invariant**: Communication service is strictly bounded; money movement via voice is prohibited.

---

## 4. Final Classification Summary

```text
REAL PROVIDER VERIFIED : Journey A (Real Razorpay Test Mode), Journey F (Customer Ownership Security)
LOCAL TEST VERIFIED    : Journey B (Checkout Drop-off), Journey C (Subscription), Journey D (Receivables), Journey E (Mandate), Journey G (Communication)
SYNTHETIC ONLY         : Synthetic Evaluation Benchmark (Seed 42, 1,000 cases under /benchmark)
MISSING / BLOCKED      : None (0 blockers)
```
