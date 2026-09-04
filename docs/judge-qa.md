# PayPilot AI — Comprehensive Judge Q&A Guide

## 24 Judge Questions & Implementation-Backed Answers

### 1. Why does this need AI?
**Answer**: Standard payment gateways return cryptic, low-level error codes (e.g. `GATEWAY_ERROR`, `BAD_REQUEST_HEADER`). Gemini AI analyzes these error codes alongside customer payment history, payment method, and transaction context to interpret the true failure root cause and assess recoverability score.

### 2. Why not simple rules?
**Answer**: Simple rules work well for hard boundaries (e.g., maximum retry caps, amount limits), but struggle to parse complex, contextual failure scenarios across diverse payment methods (UPI vs. credit card) and customer track records. PayPilot AI uses AI for contextual diagnosis and deterministic rules for safety boundaries.

### 3. Can the AI directly move money?
**Answer**: **No.** Gemini AI is strictly advisory. It generates a diagnostic recommendation. It has zero API keys for Razorpay, zero database write permissions to financial balances, and zero direct execution capability.

### 4. How do you prevent unsafe actions?
**Answer**: All AI recommendations are intercepted by an independent, deterministic Policy Safety Gate. The Policy Gate enforces 5 hard rules: Minimum AI Confidence ($\ge 0.70$), Maximum Retry Limit ($\le 3$), Mandatory Cooldown ($\ge 1\text{h}$), Maximum Auto-Recovery Amount ($\le \text{₹50k}$), and Fraud Guards. If any rule is violated, the action is blocked instantly.

### 5. What happens when AI is wrong?
**Answer**: If AI overestimates recoverability on an unrecoverable failure, the Policy Gate restricts retries to $\le 3$ and cooldown to $\ge 1\text{h}$. If the customer fails to pay via the Payment Link, the case transitions safely to `STOPPED` or `EXPIRED` without financial loss or customer harassment.

### 6. What happens when Razorpay API fails?
**Answer**: The `RecoveryExecutorService` catches gateway API exceptions, records the action as `FAILED`, sets the case status to `FAILED`, and logs a `RECOVERY_EXECUTION_FAILED` audit event. Case state remains uncorrupted.

### 7. What happens with duplicate webhooks?
**Answer**: PayPilot AI checks `x-razorpay-event-id` against the `webhook_events` database table. If a duplicate event ID is ingested, the system logs `status: ignored` and returns HTTP 200 without re-executing recovery actions or double-counting revenue.

### 8. How do you measure recovery?
**Answer**: Recovery is measured when a signed `payment_link.paid` or `payment.captured` webhook is received for a tracked `RecoveryCase`, changing case status to `RECOVERED` and updating `recovered_amount`.

### 9. Is ₹5.08M actually recovered from Razorpay?
**Answer**: **No.** ₹5.08M is the result of our **1,000 synthetic case batch evaluation benchmark** run against a deterministic dataset (Seed 42). Real Razorpay Test Mode transactions are ₹10 test payments clearly separated on the live dashboard.

### 10. What is synthetic vs real data?
**Answer**: Real Razorpay Test Mode data represents live ₹10 test payments ingested from Razorpay API/webhooks. Synthetic evaluation data represents a 1,000-case dataset used exclusively on `/benchmark` to measure algorithm accuracy.

### 11. How did you calculate Precision?
**Answer**:
$$\text{Precision} = \frac{\text{True Positives}}{\text{True Positives} + \text{False Positives}} = \frac{703}{703 + 137} = 83.69\%$$

### 12. How did you calculate Recall?
**Answer**:
$$\text{Recall} = \frac{\text{True Positives}}{\text{True Positives} + \text{False Negatives}} = \frac{703}{703 + 113} = 86.13\%$$

### 13. Why Seed 42?
**Answer**: Seed 42 is used as a standard random seed to ensure 100% deterministic reproducibility across independent benchmark evaluation runs.

### 14. How does the system know when to stop?
**Answer**: The system stops recovery interventions when: (a) Case reaches status `RECOVERED`, (b) Retry attempts reach 3 (`MAX_RETRIES_EXCEEDED`), (c) Case is flagged for suspected fraud, or (d) Amount exceeds ₹50,000 requiring human merchant escalation.

### 15. How is the webhook secured?
**Answer**: Webhooks verify the `x-razorpay-signature` header using HMAC SHA256 over raw request payload bytes using `RAZORPAY_WEBHOOK_SECRET`. Invalid signatures return HTTP 401.

### 16. What happens with high-value payments?
**Answer**: Any payment failure exceeding ₹50,000 is automatically overridden by the Policy Gate from `RECOVERY_LINK` to `ESCALATE`, changing case status to `ESCALATED` for human merchant review.

### 17. What happens with repeated failures?
**Answer**: Retries are capped at 3 attempts max with mandatory 1-hour cooldowns. Once 3 retries are exhausted, the case is permanently set to `STOPPED`.

### 18. What happens if confidence is low?
**Answer**: If AI confidence is $< 0.70$, the Policy Gate blocks the action (`LOW_CONFIDENCE`), setting case status to `STOPPED` or `ESCALATED`.

### 19. Can this scale to production?
**Answer**: Yes. The backend is built with asynchronous FastAPI, SQLAlchemy, and aiosqlite/asyncpg, supporting high-concurrency PostgreSQL and worker task queues.

### 20. What are the current limitations?
**Answer**: Integrated exclusively with Razorpay Test Mode (no real bank money moved), synthetic benchmark is seed-based, and third-party public hosting is deployment-ready but not kept live to avoid cloud costs.

### 21. Why Razorpay?
**Answer**: Razorpay provides comprehensive Payment Links APIs and robust webhook events (`payment.failed`, `payment_link.paid`), making it the ideal partner gateway for autonomous payment recovery.

### 22. What makes this agentic?
**Answer**: PayPilot AI exhibits an autonomous perceive-diagnose-decide-gate-act-verify loop. It perceives gateway webhooks, diagnoses root causes, decides actions, validates policy boundaries, invokes Razorpay API tools, and verifies outcomes.

### 23. What tools can the agent use?
**Answer**: The agent uses the Razorpay Payment Links API (`create_payment_link`), Risk Scoring Engine (`assess_risk`), Policy Engine (`evaluate_action`), and Audit Service (`log_event`).

### 24. What is the human-in-the-loop boundary?
**Answer**: High-value cases ($> \text{₹50k}$), low AI confidence ($< 0.70$), or suspected fraud cases automatically route to human merchants via case escalation.
