# PayPilot AI — Build & Implementation Plan

**Track 03 — AI Revenue Recovery | Razorpay AI Buildathon**

---

## Phased Development Roadmap

This plan follows a strict, verification-driven development flow. Each phase must be built, tested, and verified before advancing to the next.

---

### Phase 0: Specification, Architecture & Project Scaffold (COMPLETED)
- [x] Create `docs/MASTER_SPEC.md`
- [x] Create `docs/ARCHITECTURE.md`
- [x] Create `docs/BUILD_PLAN.md`
- [x] Propose DB Schema, API endpoints, AI Tool list, and Razorpay integration points.
- [x] Initialize repository structure (`backend/` FastAPI).

---

### Phase 1: Foundation (Backend FastAPI + Database setup) (COMPLETED)
- [x] Setup Python environment, `requirements.txt`, FastAPI server.
- [x] Setup PostgreSQL-compatible SQLAlchemy models (`Merchant`, `Customer`, `Transaction`, `RecoveryCase`, `RecoveryAction`, `AuditLog`, `WebhookEvent`, `EvaluationRun`, `AIDiagnosis`).
- [x] Setup database migrations (Alembic).
- [x] Health check endpoints (`/health`, `/health/db`, `/api/v1/health`, `/api/v1/health/db`).

---

### Phase 2: Razorpay Test Mode & Webhook Core (COMPLETED)
- [x] Implement `RazorpayClientService` wrapping official `razorpay` SDK in Test Mode.
- [x] Implement `POST /api/v1/webhooks/razorpay` with HMAC SHA256 signature verification.
- [x] Implement idempotency checking via `webhook_events` table.
- [x] CLI webhook simulator utility (`scripts/simulate_webhook.py`).

---

### Phase 3: Revenue At Risk Engine & Policy Gate (COMPLETED)
- [x] Implement `RevenueRiskEngine` (`backend/app/services/revenue_risk/`).
- [x] Implement `PolicyEngine` safety gate (`backend/app/services/policy/`).
- [x] Case listing, details, and policy check endpoints (`/api/v1/cases`).

---

### Phase 4: AI Diagnosis & Recovery Decision Service (COMPLETED)
- [x] Implement `BaseAIService`, `GeminiAIService`, `DeterministicAIFallbackService`.
- [x] Enforce Pydantic structured JSON schema `AIDiagnosisOutput`.
- [x] Dedicated `AIDiagnosis` ORM model and audit logs.
- [x] `POST /api/v1/cases/{case_id}/diagnose` endpoint.

---

### Phase 5: Recovery Action Execution Engine (COMPLETED)
- [x] Implement `RecoveryActionExecutorService` (`backend/app/services/recovery/`).
- [x] Real Razorpay Test Payment Link creation (`RECOVERY_LINK`).
- [x] Payment Link paid webhook recovery lifecycle (`payment_link.paid`).
- [x] Execution endpoint `POST /api/v1/cases/{case_id}/execute` & demo endpoint.

---

### Phase 6: Buildathon Gap-Closure — Batch Evaluation & Measured Recovery (COMPLETED)
- [x] `docs/PHASE6_GAP_ANALYSIS.md` & `docs/BATCH_EVALUATION.md`.
- [x] Extended `EvaluationRun` table and migration `005_extend_evaluation_runs_table.py`.
- [x] Seed-reproducible `BatchEvaluatorService` (`seed=42`) across 100 cases.
- [x] Evaluation endpoints (`POST /evaluation/run`, `GET /evaluation/runs/{id}`, `GET /evaluation/runs/{id}/cases`, `GET /evaluation/runs/{id}/audit`).
- [x] Analytics endpoints (`GET /analytics/metrics`, `GET /analytics/funnel`, `GET /analytics/recent-activity`).
- [x] Comprehensive Pytest test suite (`test_evaluation.py`, `test_analytics.py`).

---

### Phase 7: Merchant Dashboard UI (Next Steps)
- [ ] Build responsive Next.js dashboard UI (Metric Cards, Recovery Funnel, Case Explorer Table, Case Detail Drawer, Batch Evaluation Benchmark Report).
