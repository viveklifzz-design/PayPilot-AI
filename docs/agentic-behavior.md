# PayPilot AI — Bounded Autonomous Agentic Workflow

## 1. Definition & Agentic Loop
PayPilot AI operates as a **bounded autonomous agent**. It does not perform unrestricted financial actions; instead, it executes an autonomous perceive-diagnose-decide-gate-act-verify loop bounded by deterministic policy safety constraints.

---

## 2. The 8-Stage Agentic Loop

```text
 1. OBSERVE   ──────► Ingests payment.failed webhook event from Razorpay
       │
 2. GATHER    ──────► Queries customer track record & transaction history
       │
 3. DIAGNOSE  ──────► Invokes Gemini AI to determine failure root cause
       │
 4. DECIDE    ──────► Proposes optimal recovery intervention (e.g. RECOVERY_LINK)
       │
 5. GATE      ──────► Passes proposal through 5 Policy Safety Gate rules
       │
 6. ACT       ──────► Invokes Razorpay API tool (create_payment_link)
       │
 7. VERIFY    ──────► Ingests signed payment_link.paid webhook verification
       │
 8. TERMINATE ──────► Updates state to RECOVERED, STOPPED, or ESCALATED
```

---

## 3. Tool Usage & Action Capabilities
The agent utilizes specialized internal tool services:
- `RazorpayClient.create_payment_link()`: Creates payment links.
- `PolicyEngine.evaluate_action()`: Validates safety rules.
- `RiskEngine.assess_risk()`: Scores failure severity.
- `AuditLogService.log_event()`: Records immutable decision traces.
