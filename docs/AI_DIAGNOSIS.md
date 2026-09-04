# PayPilot AI — AI Diagnosis Service & Prompt Engineering

**Track 03 — AI Revenue Recovery | Razorpay AI Buildathon**

---

## 1. Overview & Architectural Isolation

The **AI Diagnosis Service** provides structured, advisory reasoning for failed payment transactions. It analyzes transaction metadata, error codes, customer payment history, and risk scores to determine the root cause of payment failure and recommend a bounded recovery intervention.

```
       RecoveryCase Context (Transaction, Customer History, Risk Score)
                                   │
                                   ▼
                       AI Provider Abstraction
                     (BaseAIService Interface)
                                   │
             ┌─────────────────────┴─────────────────────┐
             ▼                                           ▼
      GeminiAIService                            Fallback Service
 (google-genai / gemini-2.5-flash)           (Deterministic Rules)
             │                                           │
             └─────────────────────┬─────────────────────┘
                                   │
                                   ▼
                           AIDiagnosisOutput
                  (Pydantic Schema Validation)
                                   │
                                   ▼
                       Policy Engine Safety Gate
               (Enforces MAX_RETRIES, COOLDOWN, LIMITS)
```

> **SAFETY MANDATE**: The AI output is STRICTLY ADVISORY. An AI recommendation can NEVER execute a financial or customer action directly without explicit Policy Safety Gate validation.

---

## 2. Pydantic Structured Output Schema (`AIDiagnosisOutput`)

All AI responses are forced into strict Pydantic JSON schemas:

```python
class AIDiagnosisOutput(BaseModel):
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    recoverability_score: float = Field(..., ge=0.0, le=1.0)
    failure_category: Literal[
        "NETWORK",
        "AUTHENTICATION",
        "INSUFFICIENT_FUNDS",
        "LIMIT_EXCEEDED",
        "USER_CANCELLED",
        "PAYMENT_METHOD",
        "BANK_DECLINED",
        "FRAUD_OR_SECURITY",
        "UNKNOWN"
    ]
    root_cause: str = Field(..., description="Short title of the failure root cause")
    recommended_action: Literal[
        "RETRY",
        "RECOVERY_LINK",
        "REMINDER",
        "ESCALATE",
        "STOP"
    ]
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str = Field(..., description="Merchant-facing explanation of decision logic")
    explanation: str = Field(..., description="Technical summary for audit trail")
    escalation_required: bool
```

---

## 3. Provider Abstraction & Fallback Resiliency

1. **Abstract Interface (`BaseAIService`)**: Decouples API handlers from specific LLM vendors.
2. **Gemini SDK (`google-genai`)**: Uses `client.models.generate_content(...)` with `gemini-2.5-flash`.
3. **Deterministic Fallback (`DeterministicAIFallbackService`)**: If `GEMINI_API_KEY` is missing, or if Gemini encounters API errors, timeouts, or malformed JSON, PayPilot AI instantly engages the rule-based fallback service:
   - `recommended_action = "ESCALATE"`
   - `confidence = 0.0`
   - `reason = "AI diagnosis fallback active due to API unavailability."`

This guarantees 100% backend uptime and prevents pipeline crashes during LLM outages.

---

## 4. System Prompt Specification (Version: `v1.0.0`)

```text
System Prompt:
You are PayPilot AI, an expert payment recovery assistant for Razorpay merchants.
Your task is to analyze the payment failure context and produce a structured JSON response.

Input Context Provided:
- Transaction Amount, Currency, Payment Method
- Provider Error Code and Description
- Customer Payment History (Successful payments count, Failed payments count)
- Revenue Risk Assessment (Risk Level, Priority, Risk Factors)

Rules:
1. Map the provider error code to the most accurate failure_category.
2. Select exactly one recommended_action from: RETRY, RECOVERY_LINK, REMINDER, ESCALATE, STOP.
3. If risk level is CRITICAL or fraud is suspected, set recommended_action to ESCALATE or STOP.
4. Assign a confidence score between 0.0 and 1.0 based on evidence strength.
5. Provide a concise, professional, merchant-facing reason.
```

---

## 5. Security & Privacy Controls

- **Zero Secret Exposure**: API keys (`GEMINI_API_KEY`) are kept strictly server-side in `.env`.
- **Sanitized Prompts**: Customer credit card numbers, CVVs, tokens, and authorization headers are NEVER included in AI prompt payloads.
- **Immutable Audit Logging**: Every diagnosis request logs `AI_DIAGNOSIS_STARTED`, `AI_DIAGNOSIS_COMPLETED`, or `AI_DIAGNOSIS_FAILED` in `audit_logs`.
