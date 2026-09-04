# PayPilot AI — Master Product Specification

**Track 03 — AI Revenue Recovery | Razorpay AI Buildathon**  
**Product Tagline:** Autonomous Revenue Recovery Agent

---

## 1. Product Overview

PayPilot AI is an autonomous, policy-guarded revenue recovery agent designed to detect, diagnose, intervene, and verify failed or at-risk payment transactions in real time. It converts passive payment failures into active recovery opportunities without risking customer relationship damage or introducing unauthorized financial operations.

### 1.1 Key Value Proposition
- **Real-Time Detection:** Automatically captures payment failures via Razorpay Webhooks.
- **AI-Driven Diagnosis:** Uses structured Gemini LLM reasoning to determine root cause and recoverability.
- **Deterministic Policy Safety Gate:** Enforces hard business constraints (retry limits, cooldowns, max amounts, high-value escalation) that cannot be bypassed by the AI.
- **Bounded Autonomous Recovery:** Executes Razorpay Test API operations (Payment Links, Reminders, Retries) safely.
- **Empirical Revenue Measurement:** Tracks exact recovered revenue with full audit trail logging and reproducible synthetic evaluation.

---

## 2. Buildathon Requirements Mapping

| Requirement | Implementation Strategy | Status |
| :--- | :--- | :--- |
| **Revenue-at-Risk Detection** | Webhook listener & deterministic risk scoring engine | Phase 3 |
| **AI Diagnosis & Decision** | Gemini API structured JSON output (`pydantic` validated) | Phase 4 |
| **Policy/Safety Gate** | Deterministic rule engine blocking unauthorized LLM actions | Phase 3 |
| **Bounded Actions** | Razorpay Payment Links, Payment Reminders, Retry logic | Phase 5 |
| **Outcome Verification** | Webhook verification & Razorpay Order/Payment status API polling | Phase 6 |
| **Audit Trail** | Immutable PostgreSQL log table tracking every decision step | Phase 7 |
| **Batch Evaluation** | Synthetic dataset generator + precision/recall/recovery analytics | Phase 8 |
| **Razorpay Integration** | Official Razorpay Python SDK (`razorpay`), Test Mode credentials | Phase 2 |
| **Merchant Dashboard** | Next.js 14 (App Router) + Tailwind CSS + Lucide icons + Charts | Phase 9 |

---

## 3. Core Product Flow

```
Payment Failure Event / At-Risk Trigger (Razorpay Webhook)
                      ↓
           Signature & Idempotency Gate
                      ↓
       Deterministic Revenue Risk Scoring (Priority, Amount, History)
                      ↓
          AI Agent Diagnosis & Recommended Action (Gemini LLM)
                      ↓
       Deterministic Policy Gate (Rule Check: Max Retry, Cooldown, Limit)
          ├── PASS ──> Bounded Action Execution (Razorpay Payment Link / Reminder)
          └── FAIL ──> Safe Stop / Human Escalation
                      ↓
          Outcome Verification (Razorpay Webhook / Polling)
                      ↓
   Measurement of Recovered Revenue + Immutable Audit Trail Update
                      ↓
            Merchant Dashboard Metric & Timeline Sync
```

---

## 4. Database Schema (PostgreSQL)

```sql
-- 1. Merchants Table
CREATE TABLE merchants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    razorpay_key_id VARCHAR(255),
    razorpay_key_secret_hash VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Customers Table
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID REFERENCES merchants(id),
    razorpay_customer_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    total_successful_payments INT DEFAULT 0,
    total_failed_payments INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Transactions Table (Observed & Simulated)
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID REFERENCES merchants(id),
    customer_id UUID REFERENCES customers(id),
    razorpay_payment_id VARCHAR(255) UNIQUE,
    razorpay_order_id VARCHAR(255),
    amount DECIMAL(12, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'INR',
    status VARCHAR(50) NOT NULL, -- e.g., created, authorized, captured, failed
    error_code VARCHAR(100),
    error_description TEXT,
    payment_method VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Recovery Cases Table
CREATE TABLE recovery_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID REFERENCES merchants(id),
    transaction_id UUID REFERENCES transactions(id),
    customer_id UUID REFERENCES customers(id),
    amount DECIMAL(12, 2) NOT NULL,
    risk_score DECIMAL(5, 2) NOT NULL, -- 0.00 to 100.00
    risk_level VARCHAR(20) NOT NULL, -- LOW, MEDIUM, HIGH, CRITICAL
    status VARCHAR(50) NOT NULL, -- OPEN, DIAGNOSED, ACTION_PENDING, IN_PROGRESS, RECOVERED, FAILED, ESCALATED, STOPPED
    ai_root_cause VARCHAR(100),
    ai_recommended_action VARCHAR(50),
    ai_confidence DECIMAL(5, 2),
    ai_reasoning TEXT,
    policy_passed BOOLEAN DEFAULT FALSE,
    policy_failure_reason TEXT,
    actual_action_taken VARCHAR(50),
    retry_count INT DEFAULT 0,
    recovered_amount DECIMAL(12, 2) DEFAULT 0.00,
    stop_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Recovery Actions Table (Execution Records)
CREATE TABLE recovery_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES recovery_cases(id),
    action_type VARCHAR(50) NOT NULL, -- RETRY, RECOVERY_LINK, REMINDER, ESCALATE, STOP
    status VARCHAR(50) NOT NULL, -- INITIATED, SUCCESS, FAILED, EXPIRED
    razorpay_payment_link_id VARCHAR(255),
    short_url TEXT,
    payload JSONB,
    response JSONB,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Audit Logs Table (Immutable Event Log)
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES recovery_cases(id),
    actor VARCHAR(50) NOT NULL, -- SYSTEM, AI_AGENT, POLICY_ENGINE, HUMAN_OPERATOR, RAZORPAY_WEBHOOK
    event_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Webhook Events Table (Idempotency & Auditing)
CREATE TABLE webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Evaluation Runs Table (Synthetic Benchmarking)
CREATE TABLE evaluation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_name VARCHAR(255) NOT NULL,
    total_cases INT NOT NULL,
    revenue_at_risk DECIMAL(12, 2) NOT NULL,
    recoverable_revenue DECIMAL(12, 2) NOT NULL,
    total_recovered DECIMAL(12, 2) NOT NULL,
    recovery_rate DECIMAL(5, 2) NOT NULL,
    precision_rate DECIMAL(5, 2) NOT NULL,
    false_intervention_rate DECIMAL(5, 2) NOT NULL,
    escalation_rate DECIMAL(5, 2) NOT NULL,
    safe_stop_rate DECIMAL(5, 2) NOT NULL,
    metrics JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. API Endpoint Architecture

### 5.1 Webhooks API
- `POST /api/v1/webhooks/razorpay`: Verifies HMAC SHA256 signature, logs idempotency event, triggers async recovery pipeline.

### 5.2 Recovery Cases API
- `GET /api/v1/cases`: Paginated list of recovery cases with filtering (`status`, `risk_level`, `search`).
- `GET /api/v1/cases/{case_id}`: Detailed case overview including transaction details, AI reasoning, policy status, and execution history.
- `GET /api/v1/cases/{case_id}/audit-trail`: Chronological audit log events for a specific recovery case.
- `POST /api/v1/cases/{case_id}/escalate`: Manual merchant override to force escalation.
- `POST /api/v1/cases/{case_id}/retry`: Manual merchant override to retry recovery.

### 5.3 Dashboard & Analytics API
- `GET /api/v1/analytics/metrics`: Aggregated financial metrics (Revenue at Risk, Recovered Revenue, Recovery Rate, Active Recoveries, Safe Stops).
- `GET /api/v1/analytics/funnel`: Recovery pipeline conversion funnel metrics.
- `GET /api/v1/analytics/recent-activity`: Real-time stream of latest recovery actions and outcomes.

### 5.4 AI & Policy Testing API
- `POST /api/v1/recovery/diagnose-simulated`: Trigger AI diagnosis and policy evaluation on synthetic or test input.

### 5.5 Synthetic Evaluation API
- `POST /api/v1/evaluation/run`: Triggers synthetic dataset generation and calculates precision, recall, recovery rate, and total recovered metrics.
- `GET /api/v1/evaluation/runs`: List of past evaluation runs.
- `GET /api/v1/evaluation/runs/{run_id}`: Detailed evaluation run report.

---

## 6. AI Agent Design & Schema Validation

The AI agent interacts exclusively through strict Pydantic schemas.

### Structured Output Schema (`AIDiagnosisOutput`)

```python
from pydantic import BaseModel, Field
from typing import Literal

class AIDiagnosisOutput(BaseModel):
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    recoverability_score: float = Field(..., ge=0.0, le=1.0)
    root_cause: Literal[
        "temporary_bank_outage",
        "insufficient_funds",
        "authentication_failed",
        "expired_card",
        "network_timeout",
        "suspected_fraud",
        "unknown"
    ]
    recommended_action: Literal[
        "RETRY",
        "RECOVERY_LINK",
        "REMINDER",
        "ESCALATE",
        "STOP"
    ]
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str = Field(..., description="Concise, merchant-facing explanation of decision logic")
    escalation_required: bool
```

---

## 7. Policy Engine Specification

The Policy Engine sits between AI outputs and action execution. It validates whether an AI recommendation complies with merchant safety guidelines.

| Rule Name | Rule Condition | Outcome if Violate |
| :--- | :--- | :--- |
| **Max Retry Limit** | `retry_count >= 3` | Force `STOP` or `ESCALATE` |
| **Minimum Cooldown** | `time_since_last_action < 2 hours` | Reject action, schedule delayed execution |
| **Max Auto Recovery Amount** | `amount > ₹50,000` | Force `ESCALATE` to human operator |
| **Min AI Confidence** | `ai_confidence < 0.70` | Force `ESCALATE` or `STOP` |
| **Already Recovered Check** | `status == 'RECOVERED'` | Force `STOP` immediately |
| **Fraud Suspect Guard** | `root_cause == 'suspected_fraud'` | Force `STOP` + `ESCALATE` |

---

## 8. Definition of Done (Phase 0 -> Final)
1. Complete document specs (`MASTER_SPEC.md`, `ARCHITECTURE.md`, `BUILD_PLAN.md`).
2. Clean backend & frontend project initialization.
3. Razorpay Test Mode integration with signature-verified webhook pipeline.
4. End-to-end execution of a real/simulated payment failure through AI diagnosis, policy check, Razorpay Payment Link execution, and outcome verification.
5. Merchant dashboard displaying real database-driven metrics.
6. Batch evaluation generator proving recovery performance metrics.
