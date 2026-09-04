# PayPilot AI Architecture Specification
**Razorpay AI Buildathon Track 03: AI Revenue Recovery**

---

## 1. System Overview & Data Flow

```text
┌─────────────────────────────────────────────────────────┐
│              Frontend (Next.js 14.2.15)                 │
│   Tailwind CSS / Lucide Icons / React Query Client      │
└────────────────────────────┬────────────────────────────┘
                             │ HTTP / JSON (Port 3000)
                             ▼
┌─────────────────────────────────────────────────────────┐
│               FastAPI Backend (Port 8000)               │
│                   App Router & Endpoints                │
└─────┬──────────────────────┬──────────────────────┬─────┘
      │                      │                      │
      ▼                      ▼                      ▼
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│  AI Engine  │      │ Policy Gate  │      │ Stopping Rules  │
│ (Gemini API │      │ (Rules &     │      │ Engine          │
│ / Fallback) │      │ Constraints) │      │ (Max 3 Retries) │
└─────────────┘      └──────────────┘      └─────────────────┘
      │                      │                      │
      └──────────────────────┼──────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│             Provider Reconciliation Engine              │
│       HMAC-SHA256 Signature Verification & Checks        │
└────────────────────────────┬────────────────────────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
┌───────────────────────┐         ┌───────────────────────┐
│ Razorpay Test Mode    │         │ SQLite Database       │
│ Payment Links & Orders│         │ (`paypilot_dev.db`)   │
└───────────────────────┘         └───────────────────────┘
```

---

## 2. Component Breakdown

### A. AI Decision Layer (`backend/app/services/recovery/ai_decision_service.py`)
- Analyzes transaction failure facts (`error_code`, `error_description`, `amount`).
- Calls Google Gemini API (`gemini-3.6-flash`).
- Falls back to deterministic failure intelligence engine if API is unreachable.

### B. Policy Gate (`backend/app/services/recovery/policy_gate.py`)
- Enforces strict financial rules before executing recovery actions.
- Rejects recovery if case is already `RECOVERED`, risk is invalid, or failure code is non-retryable.

### C. Provider Reconciliation (`backend/app/services/recovery/reconciliation_service.py`)
- Queries Razorpay API to verify payment status (`captured`) and order ID match.
- Verifies HMAC-SHA256 signatures on checkout callbacks.
- Updates database state to `RECOVERED` only upon provider confirmation.

### D. Mandate Retry Sequencer (`backend/app/services/revenue_risk/mandate_service.py`)
- Bounded retry scheduler for recurring auto-debit retries.
- Enforces exponential cooldown periods ($24h \times \text{attempt count}$) and max 3 retries.
- Operates in simulation mode without live bank callbacks.

### E. Audit & Event Registry (`backend/app/models/audit_log.py`)
- Immutable log recording of all AI decisions, Policy Gate evaluations, webhook payloads, and state transitions.

---

## 3. Security & Compliance Architecture
- **No Secret Storage in Code**: All API keys read exclusively from environment variables.
- **HMAC Verification**: All Razorpay webhooks and checkout callbacks verified via HMAC-SHA256 signature algorithms.
- **No Sensitive Card Data**: Payment checkout delegated entirely to Razorpay Standard Checkout in Test Mode.
