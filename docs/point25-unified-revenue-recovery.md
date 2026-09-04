# Unified Revenue Recovery Intelligence Specification

## 1. Overview & Architecture
PayPilot AI unifies three primary revenue-risk sources for **Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery**:
1. `PAYMENT_FAILURE` — Direct transaction auto-debit / payment attempts that fail.
2. `CHECKOUT_DROPOFF` — Abandoned checkout sessions exceeding 30-minute inactivity window.
3. `SUBSCRIPTION_FAILURE` — Recurring subscription billing auto-debit failures.

---

## 2. Canonical Data Flow & Risk Layer

```text
  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
  │ PAYMENT_FAILURE │  │ CHECKOUT_DROPOFF │  │ SUBSCRIPTION_FAILURE │
  └────────┬────────┘  └────────┬─────────┘  └──────────┬───────────┘
           │                    │                       │
           └────────────────────┼───────────────────────┘
                                │
                                ▼
               Unified Revenue Risk Intelligence Layer
              (app/services/revenue_risk/unified_risk.py)
                                │
               ┌────────────────┴────────────────┐
               │  Deterministic Priority Engine  │ (0-100 score + factors)
               │ (app/services/revenue_risk/...) │
               └────────────────┬────────────────┘
                                │
       ┌────────────────────────┴────────────────────────┐
       ▼                                                 ▼
GET /api/v1/revenue-risk/summary         GET /api/v1/revenue-risk/opportunities
 (Deduplicated financial summary)        (Prioritized active opportunities)
```

---

## 3. Deterministic Priority Engine
Priority is calculated deterministically (0–100 score) based on:
- **Amount Exposure** (up to 40 pts)
- **Recoverability Score** (up to 30 pts)
- **Customer History** (up to 20 pts)
- **Urgency Bonus** (+10 pts for subscription churn risk, +5 pts for active drop-off)
- **Retry Penalty** (-5 pts per retry attempt)

The LLM is **never** permitted to assign arbitrary financial priority scores.

---

## 4. Deduplication & Money Safety Rules
- **Precedence Hierarchy**: `transaction_id` $\rightarrow$ `checkout_session_id` $\rightarrow$ `subscription_attempt_id` $\rightarrow$ `provider_reference`.
- **Active Risk Boundaries**: Converted checkouts and recovered payments immediately exit active revenue-at-risk. No double-counting is permitted.
- **Strict Policy Safety Gate**: AI recommendations cannot bypass policy constraints ($\ge 0.70$ confidence, $\le 3$ retries, 1-hour cooldown).
