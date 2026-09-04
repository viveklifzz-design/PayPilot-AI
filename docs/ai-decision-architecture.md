# PayPilot AI — AI Decision Architecture & Safety Control Flow

## 1. Executive Principle
> **AI Authorization Boundary**: Google Gemini AI (`gemini-3.6-flash`) acts exclusively as an advisory diagnostic service. The LLM is NEVER directly authorized to execute money recovery actions, initiate API calls to Razorpay, or mutate financial state.

---

## 2. Decision Pipeline Control Flow

```text
Sanitized Transaction & Customer Context
                  │
                  ▼
   ┌──────────────────────────────┐
   │ Google Gemini AI Service     │ (gemini-3.6-flash)
   │ Output: Failure Category,    │
   │ Root Cause, Confidence,      │
   │ Recommended Action           │
   └──────────────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────┐
   │ Deterministic Policy Safety  │ (Independent Safety Gate)
   │ Gate Evaluation              │
   └──────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
    [ALLOWED]           [BLOCKED]
        │                   │
        ▼                   ▼
Execute Recovery Link   Override to STOP/ESCALATE
```

---

## 3. Structured Decision Output
Gemini AI outputs a strictly formatted JSON object (`AIDiagnosisOutput`):

```json
{
  "risk_level": "MEDIUM",
  "recoverability_score": 0.85,
  "failure_category": "TEMPORARY_PAYMENT_FAILURE",
  "root_cause": "Bank gateway timeout during peak hour UPI processing",
  "recommended_action": "RECOVERY_LINK",
  "confidence": 0.88,
  "reason": "Customer has 7 previous successful payments and only 1 failure.",
  "explanation": "Temporary network timeout; payment link recommended."
}
```

---

## 4. Error & Safety Fallback Behavior

| Condition | Cause | System Reaction | Effective Outcome |
| :--- | :--- | :--- | :--- |
| **AI Key Missing** | `GEMINI_API_KEY` not configured | Fallback to `FallbackAIService` heuristic rule engine | Action evaluated safely (Confidence: 0.85) |
| **Malformed AI Output** | Invalid JSON response from LLM | Validation handler catches error; applies fallback schema | Recommendation validated against Policy Gate |
| **Low AI Confidence** | Confidence score $< 0.70$ | Policy Safety Gate catches rule violation (`LOW_CONFIDENCE`) | Action blocked; Case set to `STOPPED`/`ESCALATED` |
| **Policy Rule Violation** | Retry count $\ge 3$ or Cooldown $< 1\text{h}$ | Policy Safety Gate catches violation | Action blocked; Case set to `STOPPED` |
