# PayPilot AI — Recovery Action Execution Engine Specification

**Track 03 — AI Revenue Recovery | Razorpay AI Buildathon**

---

## 1. Overview & Execution Isolation

The **Recovery Action Execution Engine** is the sole component in PayPilot AI authorized to execute recovery interventions.

```
       Payment Failure Webhook ──> Revenue Risk Engine ──> RecoveryCase (OPEN)
                                                                │
                                                                ▼
                                                       AI Diagnosis Service
                                                                │
                                                                ▼
                                                    Policy Safety Gate Check
                                                                │
                                                  ┌─────────────┴─────────────┐
                                               Allowed                     Blocked
                                                  │                           │
                                                  ▼                           ▼
                                      Recovery Action Executor         Status: STOPPED /
                                    (Razorpay Test Payment Links /     ESCALATED
                                     Reminders / Retries)
```

> **SAFETY PRINCIPLE**: AI recommendations can NEVER trigger recovery execution without passing the Policy Safety Gate (`allowed == True`).

---

## 2. Action Types & Execution Implementations

| Action Type | Real / Abstraction | Implementation Mechanism |
| :--- | :--- | :--- |
| **`RECOVERY_LINK`** | **REAL Razorpay Test API** | Creates Razorpay Payment Link (`client.payment_link.create`) & captures `short_url`. |
| **`RETRY`** | **Safe Retry Abstraction** | Orchestrates payment retry attempt without duplicate order creation. |
| **`REMINDER`** | **Internal Notification Log** | Generates customer reminder payload & audit event. |
| **`ESCALATE`** | **Human Review Workflow** | Transitions case to `ESCALATED` and logs high-priority alert. |
| **`STOP`** | **Safe Automation Halt** | Transitions case to `STOPPED` and logs explicit stop reason. |

---

## 3. Recovery Case & Action State Machine

### Case Lifecycle (`RecoveryCase.status`)
```
OPEN ──> DIAGNOSED ──> RECOVERY_PENDING ──> RECOVERING ──> RECOVERED
  │                         │                     │
  ├───> ESCALATED <─────────┼─────────────────────┤
  │                         │                     │
  └───> STOPPED <───────────┴─────────────────────┘
```

### Action Lifecycle (`RecoveryAction.status`)
- `INITIATED`: Action payload built and sent to executor.
- `SUCCESS`: Payment link created / Payment received.
- `FAILED`: Provider error or network failure.
- `EXPIRED`: Payment link expired.
- `BLOCKED`: Rejected by Policy Safety Gate.

---

## 4. Payment Link Webhook Lifecycle (`payment_link.paid`)

When a customer pays using the generated test recovery link:
1. Razorpay dispatches `payment_link.paid` webhook.
2. Webhook pipeline verifies HMAC SHA256 signature and checks event idempotency (`X-Razorpay-Event-Id`).
3. Pipeline matches `razorpay_payment_link_id` in `recovery_actions`.
4. `RecoveryAction.status` updated to `SUCCESS`.
5. `RecoveryCase.status` updated to `RECOVERED`, and `recovered_amount` set to paid amount.
6. Audit event `RECOVERY_PAYMENT_RECEIVED` recorded.
7. Future recovery executions for this case are strictly BLOCKED.
