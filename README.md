# PayPilot AI
**Autonomous AI Revenue Recovery Agent for Razorpay AI Buildathon (Track 03: AI Revenue Recovery)**

[![Pytest Suite](https://img.shields.io/badge/Pytest-323%20Passed-emerald.svg)](backend/tests)
[![Next.js Build](https://img.shields.io/badge/Next.js-14.2.15-blue.svg)](frontend)
[![Track 03 Alignment](https://img.shields.io/badge/Razorpay%20Buildathon-Track%2003-indigo.svg)](#3-razorpay-track-03-alignment)

---

## 1. Problem
Online merchants lose **15%–30% of legitimate revenue** due to transaction drop-offs, payment gateway failures, expired recurring mandates, checkout abandonment, and overdue B2B invoices. Standard payment gateways inform merchants that a transaction failed, but do not provide an autonomous agentic system to diagnose the root cause, enforce financial policy controls, or execute intelligent recovery outreach without human intervention.

---

## 2. Solution
**PayPilot AI** is an autonomous AI agentic system designed for Razorpay merchants. It integrates directly with Razorpay Test Mode APIs to analyze transaction failure facts, evaluate strict policy constraints (Policy Gate), schedule bounded retries, generate secure Razorpay Payment Links, and manage end-to-end recovery workflows across B2C payments, subscriptions, and B2B receivables.

---

## 3. Razorpay Track 03 Alignment
Built specifically for **Razorpay AI Buildathon Track 03: AI Revenue Recovery**, PayPilot AI implements:
- Direct integration with **Razorpay Standard Checkout** and **Razorpay Payment Links API**.
- Server-side **HMAC-SHA256 signature verification** on all checkout payment callbacks (`/api/v1/checkout/verify`).
- Direct mapping of Razorpay failure codes (`BAD_REQUEST_ERROR`, `NACH_HEADER_INVALID`, `INSUFFICIENT_FUNDS`).

---

## 4. Key Recovery Scenarios

PayPilot AI covers **9 primary revenue recovery scenarios**:

| Scenario # | Scenario Name | Primary Route | Key Endpoints | Classification |
|---|---|---|---|---|
| **Scenario 1** | Payment Failure & Auto-Recovery | `/recover/{caseId}` | `POST /api/v1/checkout/create-link`<br>`POST /api/v1/checkout/verify` | **PROVIDER VERIFIED** (for captured payments) |
| **Scenario 2** | Checkout Abandonment Nudge | `/revenue-risk` | `GET /api/v1/revenue-risk/overview`<br>`POST /api/v1/recovery/trigger-action` | **DATABASE DERIVED** |
| **Scenario 3** | Subscription Grace & Dunning | `/subscriptions` | `GET /api/v1/subscriptions`<br>`POST /api/v1/subscriptions/{id}/retry` | **DATABASE DERIVED** |
| **Scenario 4** | B2B Receivable & Link Dispatch | `/receivables` | `GET /api/v1/receivables`<br>`POST /api/v1/receivables/{id}/send-link` | **DATABASE DERIVED** |
| **Scenario 5** | Promise-to-Pay Commitment | `/cases` | `GET /api/v1/recovery-cases`<br>`POST /api/v1/recovery-cases/{id}/promise-to-pay` | **DATABASE DERIVED** |
| **Scenario 6** | Mandate Retry Sequencer | `/mandates` | `GET /api/v1/mandates`<br>`POST /api/v1/mandates/simulate-retry` | **DATABASE DERIVED / SIMULATION** |
| **Scenario 7** | Human Agent Escalation | `/cases` | `GET /api/v1/recovery-cases`<br>`POST /api/v1/recovery-cases/{id}/escalate` | **DATABASE DERIVED** |
| **Scenario 8** | Safety & Circuit Breakers | `/safety` | `GET /api/v1/safety/circuit-breakers`<br>`POST /api/v1/safety/override` | **DATABASE DERIVED** |
| **Scenario 9** | Audit Trail & Notifications | `/audit` | `GET /api/v1/audit/logs`<br>`GET /api/v1/notifications` | **DATABASE DERIVED** |

---

## 5. Architecture

```text
Frontend (Next.js 14)
   │
   ▼
Next.js API Proxy (`/api/v1/*`)
   │
   ▼
FastAPI Backend (Port 8000)
   ├── Policy Gate (Safety & Rules)
   ├── Stopping Rules Engine
   ├── Risk & Priority Engine
   ├── Provider Reconciliation Engine
   └── AI Decision Engine (Google Gemini API / Fallback)
   │
   ├── Database: SQLite (`paypilot_dev.db`)
   ├── Provider: Razorpay Test Mode API
   └── Events: Audit Logs & Notifications
```

---

## 6. AI / LLM Usage
PayPilot AI uses **Google Gemini API** (`gemini-3.6-flash`) for failure diagnosis, Hinglish/English intent classification, and recovery plan generation. If Gemini API is unreachable or rate-limited, PayPilot automatically reverts to a **100% deterministic rule-based fallback engine** without interrupting checkout or leaking errors to the user.

---

## 7. Deterministic Safety Controls
AI recommendations never execute without passing deterministic financial guardrails:
- **Policy Gate**: Rejects retry if case is already `RECOVERED`, risk level is invalid, or failure code is non-retryable (`ACCOUNT_CLOSED`, `MANDATE_REVOKED`).
- **Stopping Rules Engine**: Halts outreach if max retry count (3) is reached or customer requests escalation.
- **Circuit Breakers**: Halts automated messages if error spikes exceed 5%.

---

## 8. Razorpay Integration
- **Test Mode Checkout**: Generates real Razorpay Test Mode Orders (`order_...`) and Payment Links (`plink_...`).
- **Signature Verification**: Validates `razorpay_signature` using HMAC-SHA256 with `RAZORPAY_KEY_SECRET`.
- **Reconciliation**: Queries Razorpay API to confirm payment status is `captured` before updating database case state to `RECOVERED`.

---

## 9–15. Detailed Workflow Specs

### 9. Payment Recovery Flow
1. Failed transaction received via webhook or API.
2. AI diagnoses error; Policy Gate evaluates safety constraints.
3. Razorpay Order generated; customer presented with `/recover/{caseId}` page.
4. Customer completes checkout; PayPilot verifies HMAC signature server-side and updates case to `RECOVERED`.

### 10. Checkout Abandonment
Detects dropped sessions, computes abandonment risk, and triggers automated WhatsApp/SMS recovery links.

### 11. Subscription Recovery
Tracks dunning grace periods for recurring plans before cancellation.

### 12. B2B Receivables
Manages high-value corporate invoices with automated link distribution.

### 13. Promise-to-Pay
Captures customer payment commitments and pauses automated escalation until the promised date.

### 14. Mandate Retry Sequencer
Executes bounded retry windows for recurring auto-debit failures in simulation mode.

### 15. Human Escalation
Transfers cases with low confidence or explicit merchant escalation requests to human operator review.

---

## 16. Notifications
Real-time merchant notification registry recording recovery alerts, mandate warnings, and payment receipts.

---

## 17. Audit Trail
Immutable event logging recording every AI decision, Policy Gate evaluation, webhook delivery, and reconciliation.

---

## 18. Data Lineage Classification
PayPilot AI enforces explicit labeling across four distinct data lineage tiers:
1. **PROVIDER VERIFIED**: Confirmed against Razorpay API server (`pay_...` with status `captured`). Used for live dashboard metrics.
2. **DATABASE DERIVED**: Internal state machine transitions.
3. **DATABASE DERIVED / SIMULATION**: Simulated mandate retries without live bank NACH callbacks.
4. **SYNTHETIC / DEMO FIXTURE**: Offline benchmark evaluation datasets (`/benchmark`).
5. **INVALID / UNRECONCILED**: Isolated test records excluded from financial metrics.

---

## 19. Failure & Fallback Handling
Includes rate limit handling, database retry mechanisms, circuit breaker overrides, and graceful UI error states.

---

## 20. Voice Assistant Status
**Voice Assistant is FROZEN / BYPASSED**. It is preserved in the repository to prevent regressions, but is not required for Track 03 revenue recovery judging.

---

## 21. Tech Stack
- **Frontend**: Next.js 14.2.15 (React 18, Tailwind CSS, Lucide Icons)
- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0 (AsyncIO), Pytest
- **Database**: SQLite (`paypilot_dev.db`)
- **Payment Gateway**: Razorpay Test Mode API SDK
- **AI / LLM**: Google Gemini API (`google-genai` SDK)

---

## 22. Local Setup

### Prerequisites
- Python 3.12+
- Node.js 18+

### 1. Clone & Setup Environment
```bash
git clone https://github.com/YourUsername/PayPilot-AI.git
cd PayPilot-AI

# Create backend env file
cp .env.example backend/.env

# Create frontend env file
cp frontend/.env.example frontend/.env.local
```

### 2. Start Backend
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Start Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 23. Environment Variables

| Variable | Description | Required? |
|---|---|---|
| `RAZORPAY_KEY_ID` | Razorpay Test Mode Key ID | Yes |
| `RAZORPAY_KEY_SECRET` | Razorpay Test Mode Key Secret | Yes |
| `RAZORPAY_WEBHOOK_SECRET` | Razorpay Webhook HMAC Secret | Optional |
| `GEMINI_API_KEY` | Google Gemini API Key | Yes |
| `DATABASE_URL` | SQLAlchemy Connection String | Default: `sqlite+aiosqlite:///./paypilot_dev.db` |
| `NEXT_PUBLIC_API_BASE_URL` | Backend URL for Next.js Proxy | Default: `http://localhost:8000` |

---

## 24. Testing

### Run Backend Pytest Suite (323 Tests)
```bash
cd backend
.\venv\Scripts\python -m pytest -v
```

---

## 25. Production Build

### Build Frontend
```bash
cd frontend
npm run build
```

---

## 26. Demo Instructions
See [`docs/DEMO_GUIDE.md`](docs/DEMO_GUIDE.md) for a 3-minute step-by-step judge walkthrough.

---

## 27. Deployment Instructions
Deploy backend via FastAPI / Uvicorn container and frontend via Vercel or Next.js static export.

---

## 28. Known Limitations
- Voice Assistant route is frozen/bypassed.
- Mandate retry executes in deterministic simulation mode (no live bank NACH callbacks).

---

## 29. What Broke During Development
See [`docs/WHAT_BROKE_AT_2AM.md`](docs/WHAT_BROKE_AT_2AM.md) for real incidents, diagnoses, and resolutions.

---

## 30. Future Scope
- Live Razorpay NACH mandate webhook integration.
- Automated WhatsApp Cloud API interactive message templates.

---

## 31. AI Disclosure
AI recommendations in PayPilot AI are generated using Google Gemini API (`gemini-3.6-flash`) and governed by deterministic policy guardrails.

---

## 32. Safety & Compliance Notes
PayPilot AI never stores card numbers, CVVs, or bank passwords. All payments use Razorpay Standard Checkout in Test Mode.
