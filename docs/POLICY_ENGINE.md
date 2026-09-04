# PayPilot AI — Policy Engine & Safety Gate Specification

**Track 03 — AI Revenue Recovery | Razorpay AI Buildathon**

---

## 1. Overview & Policy Gate Philosophy

The **Policy Engine** is a non-bypassable, deterministic safety layer positioned between AI/Automated recommendations and actual financial/communication action execution.

```
       Proposed Recovery Action (e.g. RETRY, RECOVERY_LINK, ESCALATE)
                                   │
                                   ▼
              ┌─────────────────────────────────────────┐
              │           POLICY SAFETY GATE            │
              │  - Check 1: Already Recovered?          │
              │  - Check 2: Max Retries Exceeded?       │
              │  - Check 3: Cooldown Enforced?          │
              │  - Check 4: Exceeds Max Auto Amount?    │
              │  - Check 5: Minimum AI Confidence Met?  │
              │  - Check 6: Fraud / Security Guard?     │
              │  - Check 7: Valid Action Type?          │
              └────────────────────┬────────────────────┘
                                   │
                     ┌─────────────┴─────────────┐
                  Passed                      Violated
                     │                           │
                     ▼                           ▼
            Action Execution Approved      Action Overridden to STOP / ESCALATE
            Log Audit Event                Log Audit Event with Violations
```

> **CORE PRINCIPLE**: An LLM or automated script can NEVER execute a financial action that violates Policy Engine rules.

---

## 2. Configurable Policy Rules

| Rule Identifier | Parameter Name | Default Config Value | Description |
| :--- | :--- | :--- | :--- |
| `RULE_ALREADY_RECOVERED` | N/A | Hardcoded True | Prevents re-executing recovery on payments already `captured` or `RECOVERED`. |
| `RULE_MAX_RETRIES` | `MAX_RETRY_LIMIT` | `3` attempts | Blocks execution if `retry_count >= MAX_RETRY_LIMIT`. |
| `RULE_COOLDOWN_PERIOD` | `COOLDOWN_HOURS` | `2.0` hours | Enforces minimum wait time between consecutive automated recovery interventions. |
| `RULE_HIGH_VALUE_LIMIT` | `MAX_AUTO_RECOVERY_AMOUNT` | `₹50,000.00` | Rejects automated retry/link for high-value cases, forcing `ESCALATE` to human operator. |
| `RULE_MIN_CONFIDENCE` | `MIN_AI_CONFIDENCE` | `0.70` | Rejects AI recommendations where `ai_confidence < MIN_AI_CONFIDENCE`. |
| `RULE_FRAUD_GUARD` | N/A | Hardcoded True | Immediately blocks and escalates any case with `suspected_fraud` or security failure codes. |
| `RULE_VALID_ACTION` | N/A | Enum check | Ensures action is one of `RETRY`, `RECOVERY_LINK`, `REMINDER`, `ESCALATE`, `STOP`. |

---

## 3. Decision Output Schema

The Policy Engine returns a strictly validated Pydantic model (`PolicyCheckResult`):

```json
{
  "allowed": false,
  "action": "RECOVERY_LINK",
  "effective_action": "ESCALATE",
  "reason": "Action rejected due to policy violations: ['MAX_RETRIES_EXCEEDED', 'AMOUNT_EXCEEDS_AUTO_LIMIT']",
  "violations": ["MAX_RETRIES_EXCEEDED", "AMOUNT_EXCEEDS_AUTO_LIMIT"],
  "requires_escalation": true,
  "stop_automation": true,
  "evaluated_at": "2026-08-23T13:45:00Z"
}
```

---

## 4. Audit Logging & Compliance

Every policy evaluation automatically generates an immutable `AuditLog` entry:
- `actor`: `POLICY_ENGINE`
- `event_type`: `POLICY_EVALUATED_APPROVED` or `POLICY_EVALUATED_BLOCKED`
- `metadata_json`: Includes rules evaluated, list of violations, proposed action, and effective action.
