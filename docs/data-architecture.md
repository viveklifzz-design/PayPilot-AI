# PayPilot AI — Data Architecture & Entity Relationship Specification

## 1. Entity Relationship Model Overview

```text
┌──────────────┐       1:N       ┌──────────────┐       1:N       ┌──────────────┐
│   Merchant   │────────────────►│   Customer   │────────────────►│ Transaction  │
└──────────────┘                 └──────────────┘                 └──────────────┘
                                                                         │
                                                                         │ 1:1
                                                                         ▼
┌──────────────┐       1:N       ┌──────────────┐       1:N       ┌──────────────┐
│  AuditLog    │◄────────────────│ RecoveryCase │────────────────►│ AIDiagnosis  │
└──────────────┘                 └──────────────┘                 └──────────────┘
                                         │
                                         │ 1:N
                                         ▼
                                 ┌──────────────┐
                                 │RecoveryAction│
                                 └──────────────┘
```

---

## 2. Core Entities & Schema Specifications

### 2.1 `Merchant`
- **Purpose**: Represents the registered merchant entity using PayPilot AI.
- **Key Fields**: `id`, `name`, `email`, `created_at`.
- **Relationships**: Has many `Customer` and `Transaction` records.

### 2.2 `Customer`
- **Purpose**: Stores customer payment profiles and historical performance.
- **Key Fields**: `id`, `merchant_id`, `name`, `email`, `total_successful_payments`, `total_failed_payments`.
- **Relationships**: Belongs to `Merchant`; has many `Transaction` and `RecoveryCase` records.

### 2.3 `Transaction`
- **Purpose**: Records raw payment attempts ingested via Razorpay API or Webhooks.
- **Key Fields**: `id`, `merchant_id`, `customer_id`, `razorpay_payment_id`, `razorpay_order_id`, `amount`, `currency`, `status` (`created`, `authorized`, `captured`, `failed`), `error_code`, `payment_method`.
- **Relationships**: Has one `RecoveryCase` when status is `failed`.

### 2.4 `RecoveryCase`
- **Purpose**: Core domain entity tracking recovery lifecycle.
- **Key Fields**: `id`, `merchant_id`, `transaction_id`, `amount`, `risk_score`, `risk_level` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), `priority_level` (`P1` to `P4`), `status` (`OPEN`, `DIAGNOSED`, `ACTION_PENDING`, `RECOVERING`, `RECOVERED`, `FAILED`, `ESCALATED`, `STOPPED`), `ai_recommended_action`, `ai_confidence`, `policy_passed`, `actual_action_taken`, `retry_count`, `recovered_amount`.
- **Relationships**: Belongs to `Transaction`; has many `AIDiagnosis`, `RecoveryAction`, and `AuditLog` records.

### 2.5 `AIDiagnosis`
- **Purpose**: Stores structured AI Payment Failure Diagnosis records.
- **Key Fields**: `id`, `case_id`, `provider`, `model`, `risk_level`, `recoverability_score`, `failure_category`, `root_cause`, `recommended_action`, `confidence`, `reason`, `explanation`.

### 2.6 `RecoveryAction`
- **Purpose**: Tracks recovery execution attempts (e.g. Razorpay Payment Link creation).
- **Key Fields**: `id`, `case_id`, `action_type`, `status` (`PENDING`, `EXECUTING`, `CREATED`, `SUCCEEDED`, `COMPLETED`, `FAILED`), `razorpay_payment_link_id`, `short_url`, `executed_at`.

### 2.7 `WebhookEvent`
- **Purpose**: Stores raw webhook payloads for auditability and idempotency check.
- **Key Fields**: `id`, `razorpay_event_id`, `event_type`, `payload`, `processed` (boolean).

### 2.8 `AuditLog`
- **Purpose**: Immutable structured audit trail for system actions.
- **Key Fields**: `id`, `case_id`, `actor` (`SYSTEM`, `AI_AGENT`, `POLICY_ENGINE`, `RAZORPAY_WEBHOOK`, `HUMAN_OPERATOR`), `event_type`, `description`, `metadata_json`, `created_at`.

### 2.9 `EvaluationRun` (Synthetic Benchmark Entity)
- **Purpose**: Stores batch benchmark evaluation results.
- **Key Fields**: `id`, `dataset_size`, `seed`, `precision`, `recall`, `f1_score`, `unsafe_actions`, `run_summary_json`.

---

## 3. Data Isolation Notice
> **Real vs. Synthetic Data**: `Transaction` and `RecoveryCase` store live Razorpay Test Mode transactions. Synthetic evaluation data generated during `/benchmark` runs is isolated in memory / `EvaluationRun` tables and NEVER alters live merchant transaction totals.
