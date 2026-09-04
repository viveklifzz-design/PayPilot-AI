# Real Payment Failure Recovery Demo Specification & Walkthrough

## 1. Objective
Demonstrate a complete, judge-auditable end-to-end payment failure recovery flow in **Razorpay Test Mode**:

```text
REAL/TEST RAZORPAY PAYMENT
        ↓
PAYMENT FAILED
        ↓
ACTUAL RAZORPAY FAILURE FACTS
        ↓
DETERMINISTIC FAILURE CLASSIFICATION
        ↓
HUMAN-READABLE FAILURE EXPLANATION
        ↓
AI DIAGNOSIS
        ↓
POLICY SAFETY GATE
        ↓
RAZORPAY RECOVERY PAYMENT LINK
        ↓
CUSTOMER PAYS
        ↓
payment_link.paid WEBHOOK
        ↓
RECOVERY VERIFIED
        ↓
₹ RECOVERED
        ↓
AUDIT TRAIL
```

---

## 2. Authoritative Payment Facts vs AI Recommendations

| Component | Nature | Source / Location | Display Label |
| :--- | :--- | :--- | :--- |
| **Error Code / Source / Step / Reason** | Authoritative Fact | Razorpay Webhook Payload (`payment.failed`) | `AUTHORITATIVE RAZORPAY FACT` |
| **Failure Category** | Deterministic Classification | `app/services/revenue_risk/failure_classifier.py` | `DETERMINISTIC PAYPILOT CLASSIFICATION` |
| **Human Explanation** | Safe Explanation Layer | `app/services/revenue_risk/failure_explanation.py` | `EXPLANATION` |
| **AI Diagnosis & Action** | Structured Recommendation | `app/services/ai/gemini_service.py` | `AI RECOMMENDATION` |
| **Policy Approval** | Hard Safety Rule Gate | `app/services/policy/engine.py` | `POLICY GATE DECISION` |

---

## 3. Webhook Handling & Idempotency Safeguards
- **HMAC Verification**: HMAC SHA256 signature calculated over raw request body using `RAZORPAY_WEBHOOK_SECRET`. Invalid signatures return `HTTP 401`.
- **Idempotency Protection**: `payment_link.paid` webhook checks if `RecoveryCase` is already marked `RECOVERED`. Duplicate events return `200 OK` without incrementing `recovered_amount` twice.
