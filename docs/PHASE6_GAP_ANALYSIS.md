# Phase 6 — Buildathon Gap Analysis: Batch Evaluation & Measured Revenue Recovery

**Track 03 — AI Revenue Recovery | Razorpay AI Buildathon**

---

## 1. Executive Summary

Phases 1 through 5 successfully built a complete, single-transaction payment failure diagnosis and recovery pipeline:
`payment.failed` $\rightarrow$ `Revenue Risk Engine` $\rightarrow$ `RecoveryCase` $\rightarrow$ `AI Diagnosis` $\rightarrow$ `Policy Safety Gate` $\rightarrow$ `Recovery Action` $\rightarrow$ `Razorpay Test Mode Payment Link` $\rightarrow$ `payment_link.paid` $\rightarrow$ `Recovery Case RECOVERED` $\rightarrow$ `Audit Trail`.

However, for a Buildathon judge to evaluate system efficacy at scale, PayPilot AI must demonstrate **measured money recovered across a batch of transactions** (e.g. 100 failed payments) with clear metrics:
- Total revenue at risk
- Recovered revenue & recovery rate
- Policy allowed vs blocked counts
- Escalated vs stopped counts
- Remaining revenue at risk

---

## 2. Existing Component Audit (Phases 1–5)

| Component | Status | Existing Capabilities | Reuse in Phase 6 |
| :--- | :--- | :--- | :--- |
| **Database & ORM** | ✅ Complete | PostgreSQL / SQLite models (`Merchant`, `Customer`, `Transaction`, `RecoveryCase`, `RecoveryAction`, `AIDiagnosis`, `AuditLog`, `EvaluationRun`). | Reused directly. Extend `EvaluationRun` table to store complete batch metrics. |
| **Razorpay Core** | ✅ Complete | HMAC SHA256 verification, idempotency checking, order creation, payment link creation, webhook ingestion. | Real Razorpay Test Mode remains isolated from simulation. |
| **Risk Engine** | ✅ Complete | Deterministic scoring (`0-100`), recoverability, risk levels (`LOW`/`MEDIUM`/`HIGH`/`CRITICAL`), priority levels, risk factors. | Reused directly for every batch case. |
| **AI Diagnosis** | ✅ Complete | `BaseAIService`, `GeminiAIService`, `DeterministicAIFallbackService`, `AIDiagnosisOutput` schema. | Reused directly for every batch case. |
| **Policy Engine** | ✅ Complete | Hard safety rules (`MAX_RETRY_LIMIT`, `COOLDOWN_HOURS`, `MAX_AUTO_RECOVERY_AMOUNT`, `MIN_AI_CONFIDENCE`, `SUSPECTED_FRAUD_GUARD`). | Reused directly. Evaluates EVERY action in the batch. |
| **Recovery Engine** | ✅ Complete | Executors for `RECOVERY_LINK`, `RETRY`, `REMINDER`, `ESCALATE`, `STOP`. Idempotency protection. | Reused for real mode; simulated mode wraps executor. |

---

## 3. What Phase 6 Adds

1. **Batch Evaluation Engine (`backend/app/services/evaluation/`)**:
   - Synthesizes/generates $N$ (e.g. 100) realistic, heterogeneous payment failure scenarios using a deterministic seed (`seed=42`).
   - Runs EVERY case through the EXACT SAME pipeline (`Risk Engine` $\rightarrow$ `AI Diagnosis` $\rightarrow$ `Policy Gate`).
   - Applies a seed-reproducible recovery outcome simulator for evaluation mode without calling external Razorpay payment APIs.
   - Computes 15+ quantitative financial & operational metrics.
2. **Evaluation API Endpoints (`backend/app/api/v1/endpoints/evaluation.py`)**:
   - `POST /api/v1/evaluation/run`: Triggers a batch evaluation run (`{"batch_size": 100, "seed": 42, "mode": "simulation"}`).
   - `GET /api/v1/evaluation/runs/{run_id}`: Returns summary metrics for an evaluation run.
   - `GET /api/v1/evaluation/runs/{run_id}/cases`: Returns case-by-case breakdown.
   - `GET /api/v1/evaluation/runs/{run_id}/audit`: Returns the decision and policy audit trail for the batch run.
3. **Dashboard-Ready Analytics API (`backend/app/api/v1/endpoints/analytics.py`)**:
   - `GET /api/v1/analytics/metrics`: High-level merchant metrics (revenue at risk, recovered revenue, recovery rate, attempts, blocks).
   - `GET /api/v1/analytics/funnel`: Conversion funnel (`Failed` $\rightarrow$ `Diagnosed` $\rightarrow$ `Approved` $\rightarrow$ `Attempted` $\rightarrow$ `Recovered`).
   - `GET /api/v1/analytics/recent-activity`: Real-time audit & recovery activity stream.
4. **Documentation & Safety Tests**:
   - `docs/BATCH_EVALUATION.md` documenting batch methodology, seed reproducibility, and financial metrics.
   - Comprehensive safety unit tests in `backend/tests/test_evaluation.py` and `backend/tests/test_analytics.py`.

---

## 4. What Phase 6 Explicitly Will NOT Add

- ❌ NO mobile app or frontend React app (only clean backend JSON APIs ready for frontend integration).
- ❌ NO SMS, WhatsApp, or email external provider integrations (reminders remain logged abstractions).
- ❌ NO arbitrary LLM tool execution or unconstrained free-text decision making.
- ❌ NO modification or breaking of existing Phases 1–5 code and tests.
- ❌ NO uncontrolled real Razorpay Payment Links generated during simulation runs.
