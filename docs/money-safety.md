# PayPilot AI — Money Safety & Policy Controls Architecture

## 1. Safety Principles & Policy Rules
PayPilot AI enforces deterministic safety rules in code to guarantee zero unauthorized, accidental, or illegal financial actions.

---

## 2. Configured Policy Safety Gate Constraints

| Control Parameter | Configured Value | Enforcement Location | Action if Violated |
| :--- | :---: | :--- | :--- |
| **Minimum AI Confidence** | $\ge 0.70$ (70%) | `PolicyEngine.evaluate_action()` | Block proposed action; set status to `STOPPED`/`ESCALATED` |
| **Maximum Retry Limit** | $\le 3$ attempts | `PolicyEngine.evaluate_action()` | Block proposed action; set status to `STOPPED` |
| **Cooldown Window** | $\ge 60$ minutes (1 hour) | `PolicyEngine.evaluate_action()` | Block proposed action; maintain cooldown |
| **Maximum Auto-Recovery Amount** | $\le \text{INR 50,000.00}$ | `PolicyEngine.evaluate_action()` | Override action to `ESCALATE`; set status to `ESCALATED` |
| **Active Recovery Link Idempotency** | Max 1 active link per case | `RecoveryExecutorService` | Prevent duplicate execution; return existing payment link |
| **Webhook Signature Verification** | HMAC SHA256 match | `signature.py` (`verify_webhook_signature`) | Reject request immediately with HTTP 401 Unauthorized |
| **Event Idempotency Check** | Unique `x-razorpay-event-id` | `webhooks.py` (`razorpay_webhook`) | Ignore duplicate payload; return HTTP 200 (`status: ignored`) |
| **Audit Logging** | 100% structured logging | `AuditLog` service | Log immutable audit trail entry |

---

## 3. Policy Safety Gate Compliance Matrix

```text
Proposed Recovery Action (e.g. RECOVERY_LINK)
                      │
                      ▼
 ┌───────────────────────────────────────────┐
 │ 1. AI Confidence Check (>= 0.70)           │ ── (Fail) ──► Blocked (LOW_CONFIDENCE)
 └───────────────────────────────────────────┘
                      │ (Pass)
                      ▼
 ┌───────────────────────────────────────────┐
 │ 2. Retry Attempt Cap Check (<= 3 Retries) │ ── (Fail) ──► Blocked (MAX_RETRIES_EXCEEDED)
 └───────────────────────────────────────────┘
                      │ (Pass)
                      ▼
 ┌───────────────────────────────────────────┐
 │ 3. Active Cooldown Window Check (>= 60m)  │ ── (Fail) ──► Blocked (COOLDOWN_ACTIVE)
 └───────────────────────────────────────────┘
                      │ (Pass)
                      ▼
 ┌───────────────────────────────────────────┐
 │ 4. Maximum Amount Cap Check (<= ₹50,000)  │ ── (Fail) ──► Override to ESCALATE
 └───────────────────────────────────────────┘
                      │ (Pass)
                      ▼
                [POLICY APPROVED]
```
