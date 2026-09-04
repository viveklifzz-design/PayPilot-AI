# POINT #25 — READ-ONLY PRE-AUDIT REPORT

## 1. Overview & Purpose
This audit analyzes the PayPilot AI codebase prior to implementing **Point #25: Unified Revenue Recovery Intelligence**.

PayPilot AI currently supports three distinct revenue-risk sources:
1. `PAYMENT_FAILURE` — Ingested via Razorpay `payment.failed` webhooks or transaction failures.
2. `CHECKOUT_DROPOFF` — Detected when a `CheckoutSession` remains unpaid after the 30-minute inactivity window.
3. `SUBSCRIPTION_FAILURE` — Initiated when a recurring `Subscription` auto-debit attempt fails.

---

## 2. Comprehensive Findings Matrix

| Audit Topic | Current Implementation | Files Involved | Identified Gaps / Weaknesses to Fix |
| :--- | :--- | :--- | :--- |
| **A. Revenue at Risk Calculation** | Computed per `RecoveryCase` via `amount`. In `analytics.py`, total is `SUM(amount)`. | `backend/app/api/v1/endpoints/analytics.py`, `backend/app/models/recovery_case.py` | No unified deduplication service across overlapping entities (e.g. converted checkout with payment failure). |
| **B. Recovered Amount Calculation** | Computed per `RecoveryCase` via `recovered_amount` upon `RECOVERED` status transition. | `backend/app/api/v1/endpoints/webhooks.py`, `backend/app/api/v1/endpoints/analytics.py` | Need to verify active risk status excludes converted or safely stopped cases. |
| **C. PAYMENT_FAILURE Creation** | Created on `payment.failed` webhook via `_trigger_risk_assessment_and_case_creation()`. | `backend/app/api/v1/endpoints/webhooks.py` | Handled properly, but needs explicit exposure in unified risk model. |
| **D. CHECKOUT_DROPOFF Creation** | Created by `dropoff_detector.py` when `CheckoutSession` age $> 30\text{m}$. | `backend/app/services/revenue_risk/dropoff_detector.py` | Idempotent per session ID, but session conversion must cleanly remove active risk. |
| **E. SUBSCRIPTION_FAILURE Creation** | Created by `subscription_recovery.py` when recurring auto-debit transaction fails. | `backend/app/services/revenue_risk/subscription_recovery.py` | Idempotent per attempt ID, but attempt conversion must transition state to `RECOVERED`. |
| **F. Entity Linking** | `RecoveryCase` links `transaction_id`, `checkout_session_id`, `subscription_id`, `subscription_attempt_id`, `customer_id`. | `backend/app/models/recovery_case.py` | Foreign keys exist, but missing a single unified API endpoint returning normalized risk items sorted by priority. |
| **G. Duplicate Prevention** | Pre-creation queries check existing `RecoveryCase` by foreign key (`transaction_id`, `checkout_session_id`, `subscription_attempt_id`). | `webhooks.py`, `dropoff_detector.py`, `subscription_recovery.py` | Works at DB level, but explicit deduplication rules must be documented in `docs/revenue-risk-deduplication.md`. |
| **H. Dashboard Aggregation** | `analytics.py` sums amounts by `case_type`. | `backend/app/api/v1/endpoints/analytics.py`, `frontend/src/app/page.tsx` | Needs unified risk cards, priority breakdown, and explicit source breakdown visuals. |
| **I. Audit Events** | Appended to `audit_logs` table. IST timestamps formatted in UI. | `backend/app/models/audit_log.py`, `frontend/src/lib/api.ts` | Complete stage trace (DETECT $\rightarrow$ CLASSIFY $\rightarrow$ PRIORITIZE $\rightarrow$ DIAGNOSE $\rightarrow$ DECIDE $\rightarrow$ POLICY $\rightarrow$ EXECUTE $\rightarrow$ VERIFY $\rightarrow$ RECOVER) supported. |
| **J. Synthetic Evaluation Dataset** | Synthetic cases generated in `dataset.py` (1,000 cases). | `backend/app/services/evaluation/dataset.py`, `evaluator.py` | Dataset lacks explicit `case_type` distribution (`PAYMENT_FAILURE`, `CHECKOUT_DROPOFF`, `SUBSCRIPTION_FAILURE`). |

---

## 3. Plan for Implementation

1. **Phase 1 — Canonical Revenue Risk Model (`backend/app/services/revenue_risk/unified_risk.py`)**:
   - Create normalized `UnifiedRiskItem` schema & service aggregating all 3 case types into a single interface.
2. **Phase 2 — Deduplication (`docs/revenue-risk-deduplication.md`)**:
   - Document deterministic deduplication precedence (`transaction_id` $\rightarrow$ `checkout_session_id` $\rightarrow$ `subscription_attempt_id` $\rightarrow$ `provider_reference`).
3. **Phase 3 — Unified Risk Status (`docs/unified-risk-state-model.md`)**:
   - Map existing `RecoveryCase` states to `AT_RISK`, `RECOVERING`, `RECOVERED`, `STOPPED`, `ESCALATED`, `EXPIRED`.
4. **Phase 4 — Priority Engine (`backend/app/services/revenue_risk/priority_engine.py`)**:
   - Implement deterministic `PriorityEngine` (0–100 score + priority factors).
5. **Phase 5 & 6 — Unified Endpoints & AI Boundaries**:
   - Add `GET /api/v1/revenue-risk/summary` and `GET /api/v1/revenue-risk/opportunities`.
6. **Phase 7 to 10 — UI, Dashboard & Customer History**:
   - Update Dashboard cards, case drawer detail, customer history view, and audit trail.
7. **Phase 11 — Evaluation Extension**:
   - Update `dataset.py` and `evaluator.py` to sample across all 3 case types (1,000 cases, seed 42) and compute unified recovery rate.
8. **Phase 12 to 17 — Testing, Build, Regression & Final Report**:
   - Run 100% pytest, npm build, benchmark run, public demo verification, and write final report.
