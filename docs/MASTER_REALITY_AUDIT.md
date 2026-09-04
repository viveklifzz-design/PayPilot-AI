# PAYPILOT AI — MASTER REALITY AUDIT & DATA LINEAGE REPORT (PUSH #1)

## 1. Requirement-by-Requirement Audit

This document presents the complete, read-only empirical audit of **PayPilot AI** for **Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery**.

Data Classification & Status Standard:
- **`GREEN`**: Independently proven against live Razorpay Test Mode API and database.
- **`YELLOW`**: Implemented in code/DB but not yet provider-backed on Razorpay API.
- **`RED`**: Incorrect, broken, or contaminated metric/flow requiring remediation.
- **`BLUE`**: Synthetic evaluation benchmark only (Seed 42, 1,000 cases under `/benchmark`).

| Track 03 Core Requirement | Technical Implementation | Provider Proof | Status |
| :--- | :--- | :---: | :---: |
| **1. Detect Revenue at Risk** | `unified_risk.py`, `risk_engine.py` | Live DB & Provider Facts | **GREEN** |
| **2. Razorpay Failure Facts** | `failure_classifier.py`, `failure_explanation.py` | `pay_TTXlSqxyg5hAiT` Facts | **GREEN** |
| **3. Determine Right Intervention** | `ai_service.py` (Gemini 3.6 Flash) | Local Service Execution | **YELLOW** |
| **4. Execute Bounded Recovery** | `executor.py`, `razorpay_recovery.py` | Payment Link API (`plink_...`) | **GREEN** |
| **5. Policy Safety Gate** | `policy_engine.py` | Deterministic Rules ($\le \text{₹50k}$, Retries $\le 3$) | **GREEN** |
| **6. Real Payment Link Creation** | `razorpay_service.py` | 25 Links on Razorpay API | **GREEN** |
| **7. Real Payment Completion** | Razorpay Test Mode Checkout | `plink_TTa5w0TzG0OYDn` Paid (₹10) | **GREEN** |
| **8. Real Recovery Verification** | `payment_link.paid` Webhook | Uncollected for ₹2.5k Links | **YELLOW** |
| **9. Customer Portal & Security** | `customer_portal.py` | Login (HTTP 200), Ownership (HTTP 403) | **GREEN** |
| **10. Synthetic Evaluation Benchmark** | `run_evaluation.py`, `evaluation.py` | 1,000 cases (Seed 42) under `/benchmark` | **BLUE** |

---

## 2. Razorpay Provider Inventory (Live API Audit)

Direct query against `https://api.razorpay.com/v1/` using `RAZORPAY_KEY_ID` (`rzp_test_YOUR_KEY_ID`):

### Payments Inventory (`GET /v1/payments`): Total 9 Payments Found
1. `pay_TTbILwSgrvZntp`: ₹10.00, Status: `captured`, Method: `netbanking`, Email: `void@razorpay.com`
2. `pay_TTb2wi7mgN7NNX`: ₹10.00, Status: `captured`, Method: `netbanking`, Email: `void@razorpay.com`
3. `pay_TTa6BvTMgDHtc8`: ₹10.00, Status: `captured`, Method: `netbanking`, Email: `void@razorpay.com` (Linked to `plink_TTa5w0TzG0OYDn`)
4. `pay_TTZC16Z4gneHTm`: ₹10.00, Status: `captured`, Method: `netbanking`, Email: `void@razorpay.com`
5. `pay_TTYAV8yxNAGyu8`: ₹10.00, Status: `captured`, Method: `netbanking`, Email: `void@razorpay.com`
6. `pay_TTXoqAarF6GBDz`: ₹10.00, Status: `captured`, Method: `netbanking`, Email: `waghmarevivek15@gmail.com`
7. `pay_TTXlSqxyg5hAiT`: ₹10.00, Status: **`failed`**, Method: `card`, Error: `BAD_REQUEST_ERROR` (`international_transaction_not_allowed`), Email: `waghmarevivek15@gmail.com`
8. `pay_TTLBa88AgQaFGj`: ₹10.00, Status: `created`, Method: `card`, Email: `void@razorpay.com`
9. `pay_TTKnrN0rEjSKVY`: ₹10.00, Status: **`failed`**, Method: `wallet`, Error: `BAD_REQUEST_ERROR` (`payment_cancelled`), Email: `waghmarevivek15@gmail.com`

### Payment Links Inventory (`GET /v1/payment_links`): Total 25 Payment Links Found
- **Paid Links (6)**: `plink_TTbI6Yt3KtYPia` (₹10), `plink_TTb2fwGfrMX4xO` (₹10), `plink_TTa5w0TzG0OYDn` (₹10), `plink_TTZBl1bVEvQvVy` (₹10), `plink_TTYAA63FvjXN7O` (₹10), `plink_TTKj2u39IX6j8g` (₹10).
- **Unpaid Links (19)**: All ₹2,500 links (`plink_TThMwMCq60gAju`, `plink_TThMD3H8GqdMz6`, `plink_TTh8tpsM68mx6P`, etc.) have `amount_paid = 0`, `status = created`, `payments = []`.

---

## 3. Database Inventory & Configuration

- **Active Database URL**: `sqlite+aiosqlite:///./paypilot_dev.db` (File: `backend/paypilot_dev.db`)
- **Tables Registered**: `merchants`, `customers`, `transactions`, `recovery_cases`, `recovery_actions`, `audit_logs`, `webhook_events`, `checkout_sessions`, `subscriptions`, `invoices`, `mandates`, `evaluation_runs`.

---

## 4. Provider $\leftrightarrow$ Database Reconciliation

| Record Type | Reference ID | Amount | Provider Status | Local DB Status | Reconciliation Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Real Payment** | `pay_TTa6BvTMgDHtc8` | ₹10.00 | `captured` | `captured` | **GREEN (MATCH)** |
| **Real Failed Txn** | `pay_TTXlSqxyg5hAiT` | ₹10.00 | `failed` | Not yet in DB | **RED (MISSING IN DB)** |
| **Real Payment Link** | `plink_TTa5w0TzG0OYDn` | ₹10.00 | `paid` | Not yet linked | **YELLOW (LINK UNSEEDED)** |
| **Recovery Link** | `plink_TThMwMCq60gAju` | ₹2,500.00 | `created` (Paid: 0) | `RECOVERED` (Local) | **RED (MISMATCH)** |

---

## 5. Dashboard Data Lineage Audit

- **API Endpoint**: `GET /api/v1/analytics/metrics`
- **Contamination Bug**:
  - `analytics.py` (lines 57-70): If `total_cases == 0`, metrics fall back to `EvaluationRun` (synthetic benchmark data).
  - SQLite `RecoveryCase` table contains 4 local test cases marked `RECOVERED` of ₹2,500 each, producing ₹10,000.00 dashboard recovered revenue despite 0 payments collected for those links on Razorpay API.
- **Classification**: **RED (REQUIRES CONTAMINATION CLEANUP)**

---

## 6. Payment Failure Verification

- Live Razorpay API contains actual failed payment `pay_TTXlSqxyg5hAiT` (Error Code: `BAD_REQUEST_ERROR`, Error Reason: `international_transaction_not_allowed`).
- Status: **GREEN (PROVIDER FAILED TRANSACTION AVAILABLE)**

---

## 7. Recovery Verification

- Payment links are created successfully via Razorpay API (`plink_...`).
- However, ₹2,500 links (`plink_TThMwMCq60gAju`, `plink_TTh8tpsM68mx6P`) have `amount_paid = 0` on Razorpay.
- Status: **YELLOW (REAL RECOVERY PAYMENT NOT YET VERIFIED ON PROVIDER)**

---

## 8. Customer Portal Verification

- Route `/customer` exists and loads cleanly.
- `POST /api/v1/customer/login` and `GET /api/v1/customer/transactions/{id}` return HTTP 200.
- Ownership protection (`HTTP 403 Forbidden` for unauthorized customer) is active.
- Status: **GREEN**

---

## 9. Simulation Isolation Audit

- B2B Receivables, Mandate Retry, Subscription Recovery, Hinglish Communication display badge **`LOCAL TEST SIMULATION`**.
- Status: **GREEN**

---

## 10. Synthetic Evaluation Isolation Audit

- 1,000 synthetic test cases (Seed 42) rendered under `/benchmark` with explicit badge **`SYNTHETIC EVALUATION — NO REAL MONEY`**.
- Contamination fallback in `analytics.py` must be disabled.
- Status: **YELLOW (ISOLATED IN UI, BACKEND FALLBACK NEEDS REMOVAL)**

---

## 11. Duplicate Audit

- No duplicate transaction IDs found in SQLite database.
- Webhook idempotency logic active in `webhooks.py`.
- Status: **GREEN**

---

## 12. Security Audit

- HMAC SHA256 Webhook Verification active on `/api/v1/webhooks/razorpay`.
- Customer Ownership protection active on `/api/v1/customer/transactions/{id}` (returns HTTP 403 Forbidden).
- Zero API keys or secrets committed in frontend or documentation.
- Status: **GREEN**

---

## 13. UI Route Reality Audit

| Route | HTTP Status | API Endpoint | Data Classification | Status |
| :--- | :---: | :--- | :--- | :---: |
| **`/`** | HTTP 200 | `GET /api/v1/analytics/metrics` | Live Merchant Stream | **RED (Contaminated fallback)** |
| **`/transactions`** | HTTP 200 | `GET /api/v1/transactions` | Real Razorpay Test Mode | **GREEN** |
| **`/cases`** | HTTP 200 | `GET /api/v1/cases` | Live Recovery Stream | **GREEN** |
| **`/revenue-risk`** | HTTP 200 | `GET /api/v1/revenue-risk/summary` | Canonical Risk Engine | **GREEN** |
| **`/receivables`** | HTTP 200 | `GET /api/v1/receivables` | Local Test Simulation | **GREEN** |
| **`/subscriptions`** | HTTP 200 | `GET /api/v1/cases?type=SUBSCRIPTION_FAILURE` | Local Test Simulation | **GREEN** |
| **`/mandates`** | HTTP 200 | `GET /api/v1/mandates` | Local Test Simulation | **GREEN** |
| **`/communications`** | HTTP 200 | `POST /api/v1/communication/generate` | Local Test Simulation | **GREEN** |
| **`/customers`** | HTTP 200 | Customer Directory View | Customer Directory | **GREEN** |
| **`/customer`** | HTTP 200 | `POST /api/v1/customer/login` | Customer Portal | **GREEN** |
| **`/audit`** | HTTP 200 | `GET /api/v1/audit` | Audit Stream | **GREEN** |
| **`/safety`** | HTTP 200 | `GET /api/v1/cases` | Policy Engine | **GREEN** |
| **`/benchmark`** | HTTP 200 | `GET /api/v1/evaluation/summary` | Synthetic Evaluation | **BLUE** |

---

## 14. RED / GREEN Status Table

```text
=================================================================
             PAYPILOT AI MASTER REALITY AUDIT MATRIX             
=================================================================
1. Razorpay Provider Credentials      : GREEN (rzp_test_YOUR_KEY_ID)
2. Razorpay Provider Payments API     : GREEN (9 payments found)
3. Real Failed Provider Payment       : GREEN (pay_TTXlSqxyg5hAiT)
4. Customer Portal & Security         : GREEN (HTTP 200 & HTTP 403)
5. Local Feature Simulations          : GREEN (Explicitly labelled)
6. Synthetic Benchmark Isolation      : BLUE  (Isolated under /benchmark)
7. Dashboard Synthetic Fallback       : RED   (analytics.py fallback)
8. Recovery Amount Provider Sync      : RED   (Local test ₹2.5k cases)
9. Real Provider Payment Completion   : YELLOW(plink_TThMwMCq60gAju unpaid)
=================================================================
```

---

## 15. Exact Blockers & Required Fixes

1. **Dashboard Fallback Cleanup**: Remove synthetic `EvaluationRun` fallback lines 57-70 in `backend/app/api/v1/endpoints/analytics.py`.
2. **Failed Payment Ingestion**: Ingest real provider failed payment `pay_TTXlSqxyg5hAiT` into SQLite database.
3. **Database Cleanup**: Reset local test ₹2,500 recovery cases so merchant dashboard reflects exact provider data.

---

## 16. Summary Findings Report

### A. What is Actually Working
- Direct Razorpay API integration with live Test Mode credentials.
- All 13 Next.js merchant and customer routes returning HTTP 200.
- Customer Portal authentication and ownership security protection (`HTTP 403 Forbidden`).
- B2B Receivables, Mandate Retry, Subscription, and Hinglish Communication simulations cleanly labelled as `LOCAL TEST SIMULATION`.
- Synthetic Evaluation Benchmark isolated under `/benchmark` with 1,000 cases (Seed 42).

### B. What is Only Local/Test
- Historical test recovery cases of ₹2,500 created during local testing whose payment links are uncollected on Razorpay.

### C. What is Synthetic
- The 1,000-case evaluation benchmark dataset under `/benchmark`.

### D. What is Wrong
- `analytics.py` lines 57-70 falling back to synthetic benchmark metrics when live cases are 0.
- SQLite `paypilot_dev.db` contains uncollected test ₹2,500 cases inflating merchant dashboard recovered metrics.

### E. Exact Next Implementation Steps (For Next Push)
1. Remove synthetic evaluation fallback in `analytics.py`.
2. Sync real provider failed payment `pay_TTXlSqxyg5hAiT` and paid payment `pay_TTa6BvTMgDHtc8` into SQLite.
3. Reset uncollected test recovery cases in SQLite.
4. Execute `pytest`, `npm run build`, and `verify_live_data_lineage.py`.
