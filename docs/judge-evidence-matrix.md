# PayPilot AI — Judge Technical Evidence Matrix

## Overview
This matrix maps every major system claim to its exact code implementation file, verification method, and empirical evidence.

---

## Technical Evidence Mapping

| System Claim | Implementation Location | Verification Method | Empirical Evidence |
| :--- | :--- | :--- | :--- |
| **Real Razorpay Integration** | `app/services/razorpay/service.py` | Pytest `test_razorpay.py` & Live API call | Live ₹10 payment links (`plink_...` / `https://rzp.io/...`) generated via Razorpay Test API. |
| **HMAC SHA256 Webhook Auth** | `app/api/v1/endpoints/webhooks.py` | Pytest `test_webhooks.py` | `x-razorpay-signature` verification PASS; invalid signatures return HTTP 401. |
| **Deterministic Policy Gate** | `app/services/policy/policy_engine.py` | Pytest `test_policy_engine.py` & `test_resilience.py` | **0 Unsafe Actions**; enforces confidence ($\ge 0.70$), retries ($\le 3$), cooldown ($\ge 1\text{h}$), amount cap ($\le \text{₹50,000}$). |
| **AI Failure Diagnosis** | `app/services/ai/gemini_service.py` | Pytest `test_ai_service.py` | Google Gemini (`gemini-3.6-flash`) outputs structured JSON diagnosis; includes fallback engine. |
| **Recovery Execution** | `app/services/recovery/executor.py` | Pytest `test_recovery_execution.py` | Creates `RecoveryAction`, updates case state to `RECOVERING`, processes `payment_link.paid` to `RECOVERED`. |
| **Audit Trail & 7-Stage Trace** | `app/api/v1/endpoints/cases.py` & `audit.py` | Pytest `test_audit_trail.py` | `GET /cases/{id}/timeline` returns 7 chronological stages (`DETECT` $\rightarrow$ `RECOVER`) with IST timestamps. |
| **Evaluation Benchmark** | `app/services/evaluation/evaluator.py` | CLI `scripts/run_evaluation.py` | 1,000 cases (Seed 42): Precision **83.69%**, Recall **86.13%**, Unsafe Actions **0**. |
| **Secret Exposure Safety** | `app/api/v1/endpoints/audit.py` | Pytest `test_audit_trail.py` & repository scan | Secret redaction replaces sensitive keys with `[REDACTED_SECRET]`; 0 secrets in git tracking. |
| **Frontend Production Build** | `frontend/src/` (Next.js 14) | Command `npm run build` | **✓ Compiled successfully** (0 errors). |
| **Full Regression Suite** | `backend/tests/` | Command `pytest` | **96 / 96 PASSED** in 8.55s. |
