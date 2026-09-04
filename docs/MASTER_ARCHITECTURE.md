# PayPilot AI — Master System Architecture Specification

## 1. End-to-End System Flow Architecture

```text
┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
│  Razorpay Test Mode    │      │    FastAPI Backend     │      │   Next.js 14 Frontend  │
│  Payment Gateway       │──────│      Port 8000         │──────│       Port 3000        │
└────────────────────────┘      └────────────────────────┘      └────────────────────────┘
            │                               │                               │
            │ (HMAC Webhooks)               │ (Async SQLite DB)             │ (12s Polling)
            ▼                               ▼                               ▼
┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
│   Webhook Ingestion    │      │  Policy Safety Gate    │      │  Audit Trail Timeline  │
│  (Signature Verified)  │─────►│   (0 Unsafe Actions)   │─────►│   (7-Stage Trace)      │
└────────────────────────┘      └────────────────────────┘      └────────────────────────┘
```

The PayPilot AI architecture completes an autonomous revenue recovery loop:

`Razorpay Test Mode` $\rightarrow$ `Webhook Ingestion` $\rightarrow$ `Revenue Detection` $\rightarrow$ `Recovery Case` $\rightarrow$ `AI Diagnosis` $\rightarrow$ `AI Decision` $\rightarrow$ `Policy Safety Gate` $\rightarrow$ `Recovery Executor` $\rightarrow$ `Razorpay Payment Link` $\rightarrow$ `Payment Result Webhook` $\rightarrow$ `Verification` $\rightarrow$ `Recovered / Escalated / Stopped` $\rightarrow$ `Audit Trail` $\rightarrow$ `Dashboard`

---

## 2. Component Specifications

### 2.1 Webhook Ingestion Engine
- **Responsibility**: Ingests HTTP POST events from Razorpay, validates HMAC SHA256 signatures, prevents duplicate processing via `x-razorpay-event-id`, and records `WebhookEvent` database records.
- **Input**: Raw HTTP request body bytes and `x-razorpay-signature` header.
- **Output**: Verified webhook payload dispatching to Revenue Risk Engine.
- **Database Interaction**: Inserts into `webhook_events` table; queries event idempotency.
- **Failure Behavior**: Missing or invalid signatures immediately reject with HTTP 401 Unauthorized.
- **Security**: Verifies raw bytes before JSON decoding to prevent key-reordering discrepancies.

### 2.2 Revenue Risk Engine
- **Responsibility**: Scores failed payment attempts ($0.0 - 100.0$), assigns risk level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), priority level (`P1` to `P4`), and initializes `RecoveryCase`.
- **Input**: `Transaction` metadata, customer payment history, and gateway error code.
- **Output**: Evaluated risk score, priority level, and instantiated `RecoveryCase`.
- **Database Interaction**: Inserts `recovery_cases` record; updates `transactions` table.
- **Failure Behavior**: Defaults to `MEDIUM` risk and `P2` priority if customer history is incomplete.
- **Security**: Sanitizes payment error descriptions before processing.

### 2.3 AI Failure Diagnosis Service
- **Responsibility**: Invokes Google Gemini AI (`gemini-3.6-flash`) to diagnose failure root cause and recommend an optimal recovery action (`RECOVERY_LINK`, `RETRY`, `REMINDER`).
- **Input**: Transaction context dictionary (failed amount, currency, payment method, error code, customer history).
- **Output**: Structured `AIDiagnosis` record (category, root cause, confidence, recommended action, reasoning).
- **Database Interaction**: Inserts `ai_diagnoses` record; updates `recovery_cases` fields.
- **Failure Behavior**: Seamlessly transitions to `FallbackAIService` (rule-based heuristic analysis with confidence 0.85) if Gemini API key is missing or rate limited.
- **Security**: Generates recommendations ONLY as advisory inputs; AI is not directly authorized to move money.

### 2.4 Deterministic Policy Safety Gate
- **Responsibility**: Independently evaluates AI recommendations against 5 strict safety rules before execution.
- **Input**: Proposed action, AI confidence score, retry count, cooldown window, transaction amount, and gateway error code.
- **Output**: `PolicyCheckResult` (`allowed: bool`, `effective_action: str`, `violations: List[str]`, `reason: str`).
- **Database Interaction**: Inserts `audit_logs` entry (`RECOVERY_POLICY_CHECKED` or `RECOVERY_POLICY_BLOCKED`).
- **Failure Behavior**: Rejects unapproved actions and overrides recommendation to `STOP` or `ESCALATE`.
- **Security**: Authoritative gatekeeper; 0 unsafe actions executed.

### 2.5 Recovery Executor Service
- **Responsibility**: Calls Razorpay Payment Links API (`POST /v1/payment_links`) to generate recovery URLs for policy-approved cases.
- **Input**: Approved action (`RECOVERY_LINK`), case ID, amount, and customer details.
- **Output**: Razorpay payment link ID (`plink_...`), short URL (`https://rzp.io/...`), and `RecoveryAction` record.
- **Database Interaction**: Inserts `recovery_actions` record (`status: CREATED`); updates case status to `RECOVERING`.
- **Failure Behavior**: Sets action status to `FAILED`, case status to `FAILED`, and logs `RECOVERY_EXECUTION_FAILED` without corrupting case state.
- **Security**: Masked API headers; zero key secret exposure in API responses.

### 2.6 Verification & Audit Engine
- **Responsibility**: Ingests `payment_link.paid` webhook, confirms signature, updates case status to `RECOVERED`, records recovered revenue, and emits 7-stage chronological audit timeline.
- **Input**: Razorpay webhook event payload.
- **Output**: Updated `RecoveryCase` (`status: RECOVERED`, `recovered_amount: ₹X.XX`).
- **Database Interaction**: Updates `recovery_cases` and `recovery_actions`; inserts `audit_logs` record.
- **Failure Behavior**: Prevents duplicate revenue addition via idempotency checks.
- **Security**: Enforces strict audit log secret redaction (`[REDACTED_SECRET]`).
