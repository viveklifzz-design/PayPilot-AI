# POINT #26 — READ-ONLY PRE-AUDIT REPORT

## 1. Overview & Purpose
This pre-audit evaluates the current state of PayPilot AI's real payment failure recovery lifecycle prior to implementing **Point #26: Real Payment Failure → Recovery → Verified Recovery Demo**.

---

## 2. Audit Findings Matrix

| Lifecycle Stage | Current Status | Implementation & Source File | Gaps to Address in Point #26 |
| :--- | :---: | :--- | :--- |
| **1. Webhook Ingestion** | **VERIFIED** | Ingests `payment.failed` and extracts all 5 error attributes (`error_code`, `description`, `source`, `step`, `reason`) in `backend/app/api/v1/endpoints/webhooks.py` | Need safe handling when fields are missing or unknown without inventing reasons. |
| **2. Deterministic Classification** | **VERIFIED** | `classify_razorpay_failure()` in `backend/app/services/revenue_risk/failure_classifier.py` | Add a human-readable explanation layer in `backend/app/services/revenue_risk/failure_explanation.py`. |
| **3. AI Diagnosis** | **VERIFIED** | Structured output (`root_cause`, `recommended_action`, `confidence`, `reasoning`) in `backend/app/services/ai/gemini_service.py` | AI receives authoritative Razorpay facts and does not invent original failure reason. |
| **4. Policy Safety Gate** | **VERIFIED** | Rules enforced in `backend/app/services/policy/engine.py` (Confidence $\ge 0.70$, Retries $\le 3$, Cooldown $\ge 1\text{h}$, Amount $\le \text{₹50k}$) | Blocked actions halt Razorpay API calls and display explicit policy violation reason. |
| **5. Razorpay Recovery Link** | **VERIFIED** | Creates genuine Test Mode Payment Link (`plink_...` / `https://rzp.io/...`) in `backend/app/services/recovery/executor.py` | Display provider reference and short payment URL cleanly in UI. |
| **6. Customer Payment Webhook** | **VERIFIED** | Ingests `payment_link.paid` / `payment.captured` with HMAC SHA256 verification in `webhooks.py` | Ensure idempotency prevents doubling `recovered_amount`. |
| **7. UI & Case Detail Drawer** | **VERIFIED** | `CaseDetailDrawer.tsx` displays Authoritative Payment Facts, Failure Classification, Timeline, and Verification card | Explicitly label missing reasons as "Razorpay did not provide a failure reason." |
| **8. One-Command Verification** | **MISSING** | Needs CLI verification runner | Create `backend/scripts/verify_recovery_demo.py` checking end-to-end evidence. |

---

## 3. Real vs Synthetic Boundaries

| Component | Status | Description |
| :--- | :---: | :--- |
| **Razorpay Payment Links API** | **REAL TEST MODE** | Genuine API calls to `https://api.razorpay.com/v1/payment_links` using `rzp_test_...` credentials. |
| **Webhook HMAC Verification** | **REAL TEST MODE** | HMAC SHA256 signature verification via `RAZORPAY_WEBHOOK_SECRET`. |
| **Evaluation Benchmark** | **SYNTHETIC** | 1,000 synthetic test cases generated via seed 42, explicitly labeled "No Real Money". |

---

## 4. Next Steps & Plan for Point #26

1. **Phase 1**: Create `docs/REAL_PAYMENT_FAILURE_DEMO.md` explaining exact Test Mode setup and failure triggers.
2. **Phase 4**: Create `backend/app/services/revenue_risk/failure_explanation.py` and unit tests.
3. **Phase 10 & 11**: Create `backend/scripts/reset_demo_recovery.py` for clean demo reset.
4. **Phase 12**: Create `backend/scripts/verify_recovery_demo.py` for one-command lifecycle verification.
5. **Phase 13 to 17**: Execute tests, frontend build, benchmark run, public demo suite, and generate final documentation.
