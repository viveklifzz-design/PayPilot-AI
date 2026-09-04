# Unified Risk State Model Specification

## 1. Overview
PayPilot AI maps entity-level states across `PAYMENT_FAILURE`, `CHECKOUT_DROPOFF`, and `SUBSCRIPTION_FAILURE` into a **Unified Risk State Model** representing canonical risk lifecycle stages.

---

## 2. Canonical Unified Risk States

| Unified Risk Status | Description | Included `RecoveryCase` States | Included `CheckoutSession` / `Subscription` States |
| :--- | :--- | :--- | :--- |
| **`AT_RISK`** | Active revenue exposure requiring intervention | `OPEN`, `DIAGNOSED` | `DROPPED`, `PAYMENT_FAILED` |
| **`RECOVERING`** | Active recovery execution in progress | `ACTION_PENDING`, `IN_PROGRESS`, `RECOVERING` | `RECOVERING` |
| **`RECOVERED`** | Payment successfully collected | `RECOVERED` | `CONVERTED`, `RECOVERED` |
| **`STOPPED`** | Safely halted by Policy Safety Gate or merchant rules | `STOPPED` | `STOPPED`, `CANCELLED` |
| **`ESCALATED`** | Referred to human support / review team | `ESCALATED` | `ESCALATED`, `PAST_DUE` |
| **`EXPIRED`** | Recovery window lapsed without success | `FAILED`, `EXPIRED` | `EXPIRED` |

---

## 3. State Mapping Diagram

```text
               ┌──────────┐
               │ AT_RISK  │ (OPEN, DIAGNOSED)
               └────┬─────┘
                    │ (Policy Approved Recovery Execution)
                    ▼
              ┌────────────┐
              │ RECOVERING │ (ACTION_PENDING, RECOVERING)
              └─┬────────┬─┘
                │        │
   (payment.paid)        (Policy Stop / Retry Limit)
                │        │
                ▼        ▼
       ┌───────────┐  ┌─────────┐ / ┌───────────┐ / ┌─────────┐
       │ RECOVERED │  │ STOPPED │   │ ESCALATED │   │ EXPIRED │
       └───────────┘  └─────────┘   └───────────┘   └─────────┘
```

---

## 4. Preservation Guarantee
The Unified Risk State Model operates as a read-side classification layer and does **NOT** mutate underlying database enum strings or break existing `RecoveryCase.status` values.
