# PayPilot AI — Audit Trail & AI Decision Explainability Documentation

## 1. Executive Summary & Core Principle
PayPilot AI maintains a structured, immutable audit log trail for every payment recovery case across its complete lifecycle. 

> **Explainability Principle**: PayPilot AI exposes structured decision factors, chronological stage timelines, and policy safety checks—not private internal model chain-of-thought.

---

## 2. End-to-End Decision Lifecycle Stages
Every recovery case is traced across 7 chronological stages:

1. **`DETECT`** (`CASE_CREATED`): Payment failure captured via webhook or transaction stream.
2. **`DIAGNOSE`** (`AI_DIAGNOSIS_COMPLETED`): AI identifies root cause, failure category, and confidence score.
3. **`DECIDE`** (`AI_DECISION_MADE`): AI recommends an optimal recovery action (e.g. `RECOVERY_LINK`, `RETRY`, `REMINDER`).
4. **`POLICY`** (`RECOVERY_POLICY_CHECKED` / `RECOVERY_POLICY_BLOCKED`): Policy Safety Gate validates confidence, retry limits, cooldown windows, and transaction amount limits.
5. **`EXECUTE`** (`RECOVERY_EXECUTION_STARTED` / `RECOVERY_PAYMENT_LINK_CREATED` / `RECOVERY_EXECUTION_FAILED`): Policy-approved action executed against Razorpay Test Mode API.
6. **`VERIFY`** (`RECOVERY_PAYMENT_RECEIVED`): Razorpay `payment_link.paid` or `payment.captured` webhook signature verified.
7. **`RECOVER`** (`CASE_RECOVERED` / `CASE_STOPPED` / `CASE_ESCALATED`): Final case status transition and revenue yield recording.

---

## 3. Dedicated Trace & Audit APIs

### 3.1 7-Stage Chronological Timeline API
`GET /api/v1/cases/{case_id}/timeline`
Returns stage items sorted strictly chronologically with IST-formatted timestamps, titles, descriptions, and metadata.

### 3.2 Decision Summary & Explainability API
`GET /api/v1/cases/{case_id}/decision-summary`
Returns judge-friendly decision summary payload containing the structured `explainability_checklist`:
- **Customer Payment History Check**: Evaluates past success/failure track record.
- **Failure Classification Check**: Analyzes error code and failure category.
- **Retry Limit Compliance Check**: Validates retry count boundary ($\le 3$).
- **Amount Limit Check**: Validates transaction value threshold ($\le \text{₹50,000}$).
- **Policy Gate Result**: Confirms Policy Safety Gate approval.

### 3.3 Audit Trail API
`GET /api/v1/audit?case_id={case_id}&event_type={event_type}&limit=50`
Returns raw structured audit events with mandatory secret redaction.

---

## 4. Security & Secret Redaction Policy
All audit metadata is automatically sanitized before API serialization. Sensitive keys (`RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, `authorization`, `password`, `token`, `secret`) are replaced with `[REDACTED_SECRET]`.

---

## 5. Case Trace Examples

### 5.1 Recovered Case Example
- **Case ID**: `85cd25d1-b6b8-4d1b-8b9d-45e1637322c1`
- **Amount**: ₹2,500.00
- **AI Recommendation**: `RECOVERY_LINK` (Confidence: 88%)
- **Policy Gate**: `APPROVED`
- **Execution**: Payment Link `plink_TTcOi7WbGtRkjF` created via Razorpay API (`https://rzp.io/rzp/QNWlnFwc`)
- **Verification**: `payment_link.paid` webhook signature verified
- **Result**: State $\rightarrow$ `RECOVERED` | Recovered Amount: ₹2,500.00

### 5.2 Policy-Blocked Case Example
- **Case ID**: `905bfd6a-f783-4b55-8c0e-d76508b1b8b1`
- **Amount**: ₹75,000.00
- **AI Recommendation**: `RECOVERY_LINK` (Confidence: 91%)
- **Policy Gate**: `BLOCKED` (Violation: Amount exceeds maximum automatic limit ₹50,000)
- **Effective Action**: `ESCALATE`
- **Result**: State $\rightarrow$ `ESCALATED` | Recovered Amount: ₹0.00

### 5.3 Provider Failure Case Example
- **Case ID**: `f10a0222-5712-4fe5-99df-22b0bf7d2ee6`
- **Amount**: ₹2,500.00
- **AI Recommendation**: `RECOVERY_LINK`
- **Policy Gate**: `APPROVED`
- **Execution**: Razorpay API returned HTTP 500
- **Audit Log**: `RECOVERY_EXECUTION_FAILED`
- **Result**: State $\rightarrow$ `FAILED` | Recovered Amount: ₹0.00
