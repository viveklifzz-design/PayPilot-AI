# PayPilot AI — Recovery State Machine Specification

## 1. `RecoveryCase` State Machine

```text
               ┌──────────┐
               │   OPEN   │ (Failed transaction detected)
               └────┬─────┘
                    │ AI Diagnosis
                    ▼
               ┌──────────┐
               │DIAGNOSED │ (Root cause identified)
               └────┬─────┘
                    │ Policy Safety Gate Evaluation
          ┌─────────┴─────────┐
          ▼                   ▼
    [APPROVED]            [BLOCKED]
          │                   │
          ▼                   ▼
   ┌──────────────┐    ┌──────────────┐
   │  RECOVERING  │    │  STOPPED /   │ (Safety rule violated)
   └──────┬───────┘    │  ESCALATED   │
          │            └──────────────┘
          │ payment_link.paid Webhook
          ▼
   ┌──────────────┐
   │  RECOVERED   │ (Revenue successfully recovered)
   └──────────────┘
```

### Valid `RecoveryCase` States:
- **`OPEN`**: Payment failure captured; case initialized.
- **`DIAGNOSED`**: AI diagnosis completed; failure category identified.
- **`RECOVERING`**: Policy-approved action executed; Razorpay Payment Link active.
- **`RECOVERED`**: Payment received via webhook; revenue confirmed.
- **`FAILED`**: Razorpay API call failed or execution error occurred.
- **`STOPPED`**: Blocked by Policy Engine safety rule (e.g. max retries exceeded).
- **`ESCALATED`**: Transaction amount exceeds auto-recovery cap ($\text{INR 50,000}$).

---

## 2. `RecoveryAction` State Machine

```text
 ┌─────────┐      ┌───────────┐      ┌─────────┐      ┌───────────┐
 │ PENDING │ ───► │ EXECUTING │ ───► │ CREATED │ ───► │ COMPLETED │
 └─────────┘      └─────┬─────┘      └─────────┘      └───────────┘
                        │
                        ▼ (API Error)
                  ┌───────────┐
                  │  FAILED   │
                  └───────────┘
```

### Valid `RecoveryAction` States:
- **`PENDING`**: Action created in DB prior to execution.
- **`EXECUTING`**: Dispatching API request to Razorpay Payment Links API.
- **`CREATED`**: Razorpay Payment Link created; URL & `plink_...` stored.
- **`COMPLETED`**: `payment_link.paid` webhook received and confirmed.
- **`FAILED`**: Gateway API error or network exception.
