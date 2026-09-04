# PayPilot AI — Gemini AI Integration & Safety Architecture

## 1. AI Engine Overview
PayPilot AI uses Google Gemini (`gemini-3.6-flash`) for real-time payment failure diagnosis and recovery recommendation.

- **Environment Variable**: `GEMINI_API_KEY`
- **Default Model**: `gemini-3.6-flash`
- **Role**: Analyzes failure error codes, payment methods, customer track record, and risk factors to output structured JSON recommendations.

---

## 2. Configuration Setup
Add your Gemini API Key to `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.6-flash
```

---

## 3. Resilient Fallback Architecture
If `GEMINI_API_KEY` is unconfigured, invalid, or hits rate limits:
1. PayPilot AI seamlessly transitions to an isolated `FallbackAIService`.
2. The fallback service evaluates transaction context against deterministic domain heuristic rules.
3. Returns structured diagnosis output with confidence score `0.85`.
4. **Result**: The application remains 100% operational without failing or throwing 500 errors.

---

## 4. Policy Safety Gate Primacy
> **Core Safety Architecture**: Gemini AI is an advisory diagnostic engine. The LLM does NOT directly execute unrestricted financial actions.

### Governance Control Flow:
```text
  Transaction Context
          │
          ▼
┌──────────────────┐
│ Gemini AI Engine │ (Diagnoses failure & proposes action e.g. RECOVERY_LINK)
└──────────────────┘
          │
          ▼
┌──────────────────┐
│  Policy Safety   │ (Evaluates Confidence >= 0.70, Retries <= 3, Cooldown >= 1h, Amount <= ₹50k)
│       Gate       │
└──────────────────┘
          │
      ┌───┴───┐
      ▼       ▼
  [ALLOWED] [BLOCKED]
      │       │
      ▼       ▼
  Execute   Stop / Escalate
```
