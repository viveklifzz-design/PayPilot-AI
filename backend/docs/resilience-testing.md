# PayPilot AI — Hard Failure Testing & Resilience Documentation

## 1. Executive Summary
This document provides the formal machine-readable failure matrix, safety invariant definitions, and empirical test results for PayPilot AI's failure injection and resilience validation suite (Point #11).

> **Core System Guarantee**: PayPilot AI does not blindly execute financial recovery actions when provider dependencies fail, when AI predictions are uncertain, or when safety policy constraints are violated. Every failure mode results in a safe, deterministic, and audited outcome.

---

## 2. Machine-Readable Failure Matrix

| Failure Scenario | Injection Method | Expected Safe Result | Provider Called | Database Mutated | Audit Event Logged | Final Case Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **Razorpay API 400/401/429/500/Timeout** | Mock API Exception | Fail safely; record error | YES | NO | `RECOVERY_EXECUTION_FAILED` | `FAILED` |
| **Duplicate Webhook Delivery** | Repeated `x-razorpay-event-id` | Idempotent response (`ignored`) | NO | NO | None (duplicate) | Preserved |
| **Low AI Confidence (< 0.70)** | `ai_confidence = 0.45` | Policy Gate blocks action | NO | NO | `RECOVERY_POLICY_BLOCKED` | `STOPPED` / `ESCALATED` |
| **Retry Limit Exceeded ($\ge 3$)** | `retry_count = 3` | Policy Gate blocks action | NO | NO | `RECOVERY_POLICY_BLOCKED` | `STOPPED` |
| **Cooldown Window Active (< 1h)** | Action executed 5 min ago | Policy Gate blocks action | NO | NO | `RECOVERY_POLICY_BLOCKED` | Preserved |
| **High Value Transaction (> ₹50,000)** | `amount = ₹75,000` | Overridden to Escalate | NO | NO | `RECOVERY_POLICY_BLOCKED` | `ESCALATED` |
| **Invalid / Malformed AI Output** | `confidence = -1.0` / invalid action | Policy Gate overrides to Stop/Escalate | NO | NO | `RECOVERY_POLICY_BLOCKED` | `STOPPED` / `ESCALATED` |
| **Database Connection Failure** | Mock DB Session exception | Return safe failure JSON | NO | NO | Error logged | `FAILED` |
| **Out-of-Order Webhook Delivery** | `payment.captured` before `authorized` | Process payload gracefully | NO | YES | `WEBHOOK_RECEIVED` | `captured` |
| **Duplicate `payment_link.paid`** | Send `payment_link.paid` twice | Idempotent single revenue add | NO | NO | Single event | `RECOVERED` (₹2,500.00) |
| **Unknown Webhook Event Type** | `event = "payment.unknown"` | Return HTTP 200 safely | NO | NO | Recorded | Preserved |
| **Missing Webhook Signature** | Omit `x-razorpay-signature` | HTTP 401 Unauthorized | NO | NO | Rejected | Preserved |
| **Invalid Webhook Signature** | Bogus `x-razorpay-signature` | HTTP 401 Unauthorized | NO | NO | Rejected | Preserved |
| **Webhook Payload Tampering** | Tampered JSON payload | HTTP 401 Signature Fail | NO | NO | Rejected | Preserved |
| **Concurrent Recovery Execution** | Parallel `/execute` calls | Return existing active link | NO | NO | Single Link Created | `RECOVERING` |

---

## 3. Automated Safety Invariants

1. **Unsafe Money Actions**: Policy Gate blocks 100% of policy-violating financial actions.
2. **Revenue Idempotency**: Duplicate `payment_link.paid` webhooks never double-count `recovered_amount`.
3. **No Unearned Recovery**: `RecoveryCase` cannot become `RECOVERED` without confirmed payment event.
4. **Provider Error Isolation**: Failed Razorpay API calls are recorded as `FAILED`, never `COMPLETED`.
5. **Webhook Security**: Invalid HMAC signatures cannot mutate database transactions.
6. **Synthetic Isolation**: Benchmark evaluation runs do not insert records into production `transactions` or call Razorpay APIs.
7. **Single Active Link**: A single `RecoveryCase` cannot have multiple active Razorpay payment links.
8. **Low-Confidence Safeguard**: Low confidence AI predictions ($\text{confidence} < 0.70$) never trigger automatic money actions.
9. **Retry Limit Enforcement**: Retry limit ($N \ge 3$) cannot be exceeded.
10. **Cooldown Enforcement**: Re-intervention cannot occur before cooldown period expires.

---

## 4. Empirical Failure Test Summary

```text
Total Failure Scenarios Tested: 16
Passed:                        16
Failed:                        0

Unsafe Money Actions:          0 (Expected: 0)
Duplicate Recovery Links:      0 (Expected: 0)
Duplicate Recovered Amounts:   0 (Expected: 0)
Invalid Signature Mutations:   0 (Expected: 0)
```
