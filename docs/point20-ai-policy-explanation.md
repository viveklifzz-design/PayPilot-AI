# PayPilot AI — AI Advisory vs. Deterministic Policy Boundary

## 1. Architectural Mandate
> **Core Principle**: AI recommends, but Policy Controls. Google Gemini AI (`gemini-3.6-flash`) has ZERO direct authority to move money or call payment gateways.

---

## 2. 4-Layer System Boundary

```text
 ┌──────────────────────────────────────────────────────────┐
 │ Layer 1: AI Diagnostic Advisory (gemini-3.6-flash)      │
 │ - Parses failure error codes & customer payment history   │
 │ - Generates category, root cause, & confidence score     │
 │ - Proposes candidate action (e.g. RECOVERY_LINK)         │
 └────────────────────────────┬─────────────────────────────┘
                              │ Candidate Proposal
                              ▼
 ┌──────────────────────────────────────────────────────────┐
 │ Layer 2: Deterministic Policy Safety Gate                │
 │ - Independent, non-bypassable Python rule checks        │
 │ - Enforces confidence (>= 0.70), retries (<= 3),        │
 │   cooldown (>= 1h), amount cap (<= ₹50,000)               │
 │ - Outputs ALLOWED or BLOCKED                             │
 └────────────────────────────┬─────────────────────────────┘
                              │ Approved Action ONLY
                              ▼
 ┌──────────────────────────────────────────────────────────┐
 │ Layer 3: Controlled Execution Layer                      │
 │ - Invokes Razorpay Payment Links API                     │
 │ - Generates plink_... & short URLs                       │
 └────────────────────────────┬─────────────────────────────┘
                              │ Execution Event
                              ▼
 ┌──────────────────────────────────────────────────────────┐
 │ Layer 4: Audit & Verification Layer                      │
 │ - Ingests HMAC-signed webhooks                           │
 │ - Emits 7-stage chronological timeline with IST stamps   │
 └──────────────────────────────────────────────────────────┘
```
