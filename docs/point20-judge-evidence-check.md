# PayPilot AI — Judge Evidence Verification Matrix

## Core Claim Verification Mapping

| Core Presentation Claim | Target UI Evidence | Backend Implementation | Empirical Test Evidence |
| :--- | :--- | :--- | :--- |
| **"AI Diagnoses Payment Failures"** | AI Diagnosis card (`gemini-3.6-flash`, Root Cause, Confidence %) | `app/services/ai/gemini_service.py` | Pytest `test_ai_service.py` |
| **"AI Does Not Directly Control Money"** | Policy Safety Gate compliance card | `app/services/policy/policy_engine.py` | Pytest `test_policy_engine.py` |
| **"System Executes Bounded Recovery"** | Razorpay Payment Link ID (`plink_...`) & short URL | `app/services/recovery/executor.py` | Pytest `test_recovery_execution.py` |
| **"System Verifies Recovery"** | Signed `payment_link.paid` webhook & `RECOVERED` badge | `app/api/v1/endpoints/webhooks.py` | Pytest `test_webhooks.py` |
| **"Measured Benchmark Evaluation"** | `/benchmark` page (1,000 cases, Seed 42, Precision **83.69%**, Recall **86.13%**) | `app/services/evaluation/evaluator.py` | CLI `scripts/run_evaluation.py` |
| **"Unsafe Actions Prevented"** | **Unsafe Actions: 0** badge & policy override cards | `app/services/policy/policy_engine.py` | Pytest `test_resilience.py` (**16 resilience scenarios passed**) |
| **"Every Action Is Traceable"** | 7-Stage Chronological Decision Timeline with IST timestamps | `app/api/v1/endpoints/cases.py` & `audit.py` | Pytest `test_audit_trail.py` |
