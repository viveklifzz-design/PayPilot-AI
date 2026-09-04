# PayPilot AI — Pitch Claim to Evidence Matrix

## Overview
This matrix maps every presentation pitch claim directly to its UI evidence, underlying backend source code, and empirical test suite verification.

---

## Pitch Claim to Code & Test Mapping

| Presentation Claim | UI Evidence | Code Implementation | Empirical Test Evidence |
| :--- | :--- | :--- | :--- |
| **"Real Razorpay Integration"** | Payment Link ID (`plink_...`) & short URL (`https://rzp.io/...`) | `app/services/razorpay/service.py` | Pytest `test_razorpay.py` & `test_recovery_execution.py` |
| **"HMAC Webhook Security"** | Webhook verification badge & audit log entry | `app/api/v1/endpoints/webhooks.py` (`signature.py`) | Pytest `test_webhooks.py` (Mismatched signature returns HTTP 401) |
| **"AI Failure Diagnosis"** | AI Diagnosis card (`gemini-3.6-flash`, Root Cause, Confidence) | `app/services/ai/gemini_service.py` | Pytest `test_ai_service.py` (Structured JSON output & Fallback engine) |
| **"Policy Safety Primacy"** | **`POLICY APPROVED`** card & Blocked override cards | `app/services/policy/policy_engine.py` | Pytest `test_policy_engine.py` & `test_resilience.py` (**0 Unsafe Actions**) |
| **"Real Recovery Execution"** | Case status **`RECOVERED`** & confirmed revenue | `app/services/recovery/executor.py` | Pytest `test_recovery_execution.py` (`payment_link.paid` flow) |
| **"Full Audit Trail"** | 7-Stage Chronological Timeline with IST timestamps | `app/api/v1/endpoints/cases.py` & `audit.py` | Pytest `test_audit_trail.py` (`GET /cases/{id}/timeline`) |
| **"Evaluation Benchmark"** | `/benchmark` page (1,000 cases, Seed 42, Precision **83.69%**, Recall **86.13%**) | `app/services/evaluation/evaluator.py` | CLI `scripts/run_evaluation.py` & Pytest `test_evaluation.py` |
| **"Resilience & Safety"** | Health badges & error redaction (`[REDACTED_SECRET]`) | `app/core/exceptions.py` & `audit.py` | Pytest `test_resilience.py` (16 resilience scenarios passed) |
