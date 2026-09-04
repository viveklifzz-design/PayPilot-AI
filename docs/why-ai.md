# PayPilot AI — Architectural Boundary: AI vs. Deterministic Rules

## Executive Architecture Summary
> **AI = Decision Intelligence | Policy Engine = Deterministic Safety Boundary | Executor = Controlled Action Layer**

---

## Architectural Responsibility Matrix

```text
 ┌──────────────────────────────────────────────────────────┐
 │  AI Diagnostic Engine (gemini-3.6-flash)                 │
 │  - Contextual error code interpretation                  │
 │  - Failure root cause classification                      │
 │  - Recoverability score & confidence estimation          │
 │  - Action recommendation (RECOVERY_LINK, RETRY, etc.)   │
 └────────────────────────────┬─────────────────────────────┘
                              │ Advisory Proposal
                              ▼
 ┌──────────────────────────────────────────────────────────┐
 │  Deterministic Policy Safety Gate                        │
 │  - Non-bypassable code safety rules                      │
 │  - Retry attempt limit cap (<= 3 retries)                │
 │  - Mandatory cooldown window enforcement (>= 1h)         │
 │  - Maximum auto-recovery amount cap (<= ₹50,000)         │
 │  - Suspected fraud hard block                            │
 └────────────────────────────┬─────────────────────────────┘
                              │ Approved Action ONLY
                              ▼
 ┌──────────────────────────────────────────────────────────┐
 │  Razorpay Recovery Executor Layer                        │
 │  - Calls Razorpay Payment Links API                      │
 │  - Generates plink_... & short URLs                      │
 │  - Ingests HMAC SHA256 webhooks                          │
 └──────────────────────────────────────────────────────────┘
```

---

## Detailed Division of Responsibilities

### Rules Handle (Policy Safety Gate):
- Hard safety boundaries ($\le 3$ retries, $\ge 1\text{h}$ cooldown)
- Financial caps ($\le \text{INR 50,000.00}$)
- Confidence thresholds ($\ge 0.70$)
- Hard stops on security and fraud flags
- Guaranteed 0 unsafe actions

### AI Handles (Gemini Diagnostic Service):
- Parsing unstructured/cryptic gateway error payloads
- Evaluating customer track record and historical payment behavior
- Assessing recoverability probability
- Providing natural language decision explanations for merchants
