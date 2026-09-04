# Phase C — Manual Browser Demo & Acceptance Audit Report
**PayPilot AI — Razorpay AI Buildathon Track 03: AI Revenue Recovery**

---

## 1. Executive Summary & Audit Findings

Following the Critical Phase C Acceptance Audit, PayPilot AI has been rigorously audited across all 9 revenue recovery scenarios. Data lineage, provider verification, database state machine transitions, and financial metric calculations have been audited against source code, SQLite database records (`backend/paypilot_dev.db`), and Razorpay API server responses.

### Critical Acceptance Audit Results
- **Backend Test Suite**: **323 / 323 passed** in `pytest` (0 failures, 0 regressions, including new audit integrity tests).
- **Frontend Production Build**: **18 / 18 static routes compiled clean** (`npm run build` completed with zero errors).
- **Metric Integrity**: Mismatched ₹2,500 test record (`a802b0cb-06a3-4ba2-b0d5-e1ab37422741`) reclassified as **`INVALID_UNRECONCILED`** and excluded from live merchant recovered revenue metrics. Live recovered revenue dynamically reflects exact provider-captured payments (**INR 80.00**).
- **Mandate Retry Sequencer (Scenario 6)**: Reclassified as **`DATABASE DERIVED / SIMULATION`** because auto-debit retries simulate mandate state transitions without live NACH bank provider callbacks.

---

## 2. Complete Data Lineage & Classification Matrix

| Scenario # | Scenario Name | Primary Frontend Route | Backend Endpoint(s) | Database Source | Provider API Involved? | Provider ID | Provider-Confirmed Result? | Strict Classification |
|---|---|---|---|---|---|---|---|---|
| **Scenario 1** | Payment Failure & Auto-Recovery | `/recover/{caseId}` | `POST /api/v1/recovery/simulate-payment-failure`<br>`POST /api/v1/checkout/create-link`<br>`POST /api/v1/checkout/verify` | `recovery_cases`<br>`transactions`<br>`recovery_actions` | Yes | `pay_TU3EQsT63DFVuX`<br>`order_TU2xgzptEfg7rP` | **Yes** (Status `captured` for ₹10.00 recovery payment) | **PROVIDER VERIFIED** (for captured payments; link creation alone is **DATABASE DERIVED**) |
| **Scenario 2** | Checkout Abandonment Nudge | `/revenue-risk` | `GET /api/v1/revenue-risk/overview`<br>`POST /api/v1/recovery/trigger-action` | `recovery_cases`<br>`invoices` | No | N/A | No | **DATABASE DERIVED** |
| **Scenario 3** | Subscription Grace & Dunning | `/subscriptions` | `GET /api/v1/subscriptions`<br>`POST /api/v1/subscriptions/{id}/retry` | `subscriptions`<br>`recovery_cases` | No | N/A | No | **DATABASE DERIVED** |
| **Scenario 4** | B2B Receivable & Link Dispatch | `/receivables` | `GET /api/v1/receivables`<br>`POST /api/v1/receivables/{id}/send-link` | `invoices`<br>`promises_to_pay` | No | N/A | No | **DATABASE DERIVED** |
| **Scenario 5** | Promise-to-Pay Commitment | `/cases` | `GET /api/v1/recovery-cases`<br>`POST /api/v1/recovery-cases/{id}/promise-to-pay` | `promises_to_pay`<br>`recovery_cases` | No | N/A | No | **DATABASE DERIVED** |
| **Scenario 6** | Mandate Retry Sequencer | `/mandates` | `GET /api/v1/mandates`<br>`POST /api/v1/mandates/simulate-retry` | `mandates`<br>`mandate_retry_attempts` | No | `order_TXvOOkIWyc0l00` (Internal Order Ref) | No (State transition simulated internally) | **DATABASE DERIVED / SIMULATION** |
| **Scenario 7** | Human Agent Escalation | `/cases` | `GET /api/v1/recovery-cases`<br>`POST /api/v1/recovery-cases/{id}/escalate` | `recovery_cases`<br>`notifications` | No | N/A | No | **DATABASE DERIVED** |
| **Scenario 8** | Safety & Circuit Breakers | `/safety` | `GET /api/v1/safety/circuit-breakers`<br>`POST /api/v1/safety/override` | `circuit_breakers`<br>`audit_logs` | No | N/A | No | **DATABASE DERIVED** |
| **Scenario 9** | Audit Trail & Notifications | `/audit` | `GET /api/v1/audit/logs`<br>`GET /api/v1/notifications` | `audit_logs`<br>`notifications` | No | N/A | No | **DATABASE DERIVED** |

---

## 3. Detailed Audit Evidence for Scenario 1 Payment Recovery

### Lineage Trace
1. **Original Failed Payment**: Razorpay Payment `pay_TTXlSqxyg5hAiT` (Order `order_TTKk5jdEkFdEIY`, status `failed`, amount ₹10.00).
2. **PayPilot Recovery Case**: Case `d669dce3-b855-4348-b457-f0ef7c34b6b1` (Amount ₹10.00, Status `OPEN`).
3. **Recovery Decision & Action**: Policy Gate approved `RAZORPAY_STANDARD_CHECKOUT`. Created Razorpay Checkout Order `order_TU2xgzptEfg7rP`.
4. **Customer Checkout & Verification**: Customer completed checkout in Razorpay Test Mode.
5. **Provider Confirmation**: Razorpay API returned HTTP 200 for payment `pay_TU3EQsT63DFVuX` (Order `order_TU2xgzptEfg7rP`, status `captured`, amount ₹10.00).
6. **PayPilot State Transition**: `RecoveryCase.status` updated to **`RECOVERED`**, `recovered_amount = 10.0`.
7. **Audit Log Event**: `RECOVERY_CHECKOUT_VERIFIED` logged with metadata `{"payment_id": "pay_TU3EQsT63DFVuX", "order_id": "order_TU2xgzptEfg7rP", "amount": 10.0, "provider_status": "captured"}`.

---

## 4. Unreconciled Data Handling (Issue 2)

- Historical Case `a802b0cb-06a3-4ba2-b0d5-e1ab37422741` (Amount ₹2,500):
  - Previously had `status = 'RECOVERED'` without a matching provider-captured payment transaction.
  - Reclassified in database to **`INVALID_UNRECONCILED`** and `recovered_amount = 0.0`.
  - Excluded from executive dashboard recovery metrics.

---

## 5. Verification Commands

```powershell
# 1. Pytest Test Suite
cd backend
.\venv\Scripts\python -m pytest -v
# Result: 323 passed in pytest

# 2. Frontend Production Build
cd frontend
npm run build
# Result: Compiled successfully (18/18 static pages generated)
```

---

## 6. Conclusion & Status

Phase C Acceptance Audit is **COMPLETE AND VERIFIED**. PayPilot AI provides truthful, auditable data lineage for all 9 scenarios under Track 03 Razorpay AI Buildathon criteria.
