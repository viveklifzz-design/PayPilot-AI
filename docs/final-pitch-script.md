# PayPilot AI — 5-Minute Master Pitch Script

## Timed Presentation Script for Razorpay AI Buildathon 2026

---

### 0:00–0:30 | PROBLEM: Failed Payments & Revenue at Risk

**Presenter Speaking**:
"Every year, online businesses lose billions to failed payment transactions — from gateway timeouts and expired UPI handles to insufficient balance errors.

The standard response? Generic, brute-force retries. Merchants blindly resend payment links, annoying customers, exhausting retry limits, and risking compliance violations.

Merchants need an intelligent system that can automatically diagnose *why* a payment failed, determine whether it's safe to recover, and execute the exact right intervention through Razorpay."

---

### 0:30–1:00 | SOLUTION: PayPilot AI Autonomous Recovery Agent

**Presenter Speaking**:
"Introducing **PayPilot AI** — an autonomous revenue recovery agent powered by Google Gemini and Razorpay Test Mode.

PayPilot AI operates a continuous 7-stage recovery loop:
**Detect** failed payments $\rightarrow$ **Diagnose** failure root cause with Gemini AI $\rightarrow$ **Decide** optimal recovery action $\rightarrow$ Filter through a deterministic **Policy Safety Gate** $\rightarrow$ **Execute** Razorpay Payment Links $\rightarrow$ Ingest **Webhook** verification $\rightarrow$ Confirm **Recovered** revenue $\rightarrow$ Emit an immutable **Audit Trail**."

---

### 1:00–3:00 | LIVE DEMO: Real Razorpay Test Mode Recovery Flow

**Presenter Speaking**:
*(Navigates to `http://localhost:3000`)*
"Let's look at the live system.

1. **Dashboard Overview**: Here on the executive dashboard, you see our active connection badges: `Razorpay Test Mode — Connected` and `Backend — Connected`.
2. **Financial KPIs**: PayPilot AI tracks **Revenue at Risk** (failed payment attempts) and **Recovered Revenue** brought back into merchant accounts.
3. **Recent Transactions**: Scroll down to our live transaction stream. Here is a real ₹10 payment attempt (`pay_...`). Notice the unambiguous Indian Standard Time formatting: `24 Aug 2026, 05:20:44 PM IST`.
4. **Recovery Cases Explorer** *(Navigates to `/cases`)*: Let's inspect a real recovery case (`#rec_...`).
5. **AI Failure Diagnosis**: Gemini AI (`gemini-3.6-flash`) diagnosed the root cause: *Bank gateway timeout during peak hour processing*, assigning an 88% confidence score and recommending a `RECOVERY_LINK`.
6. **Policy Safety Gate**: Notice the **`POLICY APPROVED`** compliance card. The Policy Engine independently verified that confidence exceeds 70%, retries are under 3, cooldown is active, and amount is within our ₹50,000 cap.
7. **Razorpay Execution**: PayPilot AI dispatched a call to the Razorpay Payment Links API, generating payment link `plink_...` with live short URL `https://rzp.io/...`.
8. **Webhook Verification**: Upon customer payment, Razorpay dispatched a `payment_link.paid` webhook. PayPilot AI verified the HMAC SHA256 signature, confirmed idempotency, updated the case to **`RECOVERED`**, and added ₹10 to Recovered Revenue.
9. **7-Stage Audit Timeline**: Click inspect to trace the full chronological decision timeline from `DETECT` to `RECOVER` with complete explainability."

---

### 3:00–3:45 | AI + SAFETY: Deterministic Policy Primacy

**Presenter Speaking**:
"A critical architectural principle of PayPilot AI: **AI recommends, but Policy Controls.**

Gemini AI is strictly advisory. The LLM cannot directly execute money movements or call Razorpay APIs.

Our Policy Safety Gate enforces 5 non-bypassable rules in code:
- **Minimum AI Confidence**: $\ge 0.70$
- **Maximum Retry Limit**: $\le 3$ attempts
- **Cooldown Window**: $\ge 1$ hour
- **Auto-Recovery Amount Cap**: $\le \text{₹50,000}$ (Higher amounts automatically escalate to human merchants)
- **Suspected Fraud Guard**: Hard stop on security flags

If AI recommends a retry with 99% confidence, but 3 retries have already occurred, the Policy Gate **INSTANTLY OVERRIDES AND BLOCKS** the execution. Zero unsafe actions occur."

---

### 3:45–4:20 | EVALUATION: 1,000-Case Benchmark

**Presenter Speaking**:
*(Navigates to `/benchmark`)*
"To evaluate system performance at scale, we built a batch evaluation engine tested against a 1,000 synthetic case benchmark (Seed 42).

> *Note*: Synthetic Evaluation data is strictly isolated from real Razorpay transactions as labeled: **'Synthetic Evaluation — No Real Money'**.

Our deterministic evaluation results:
- **Precision**: **83.69%** (Accurate identification of recoverable failures)
- **Recall**: **86.13%** (High coverage of recoverable revenue)
- **Recovery Rate**: **59.27%**
- **Unsafe Actions**: **0** (Zero compliance violations across all 1,000 cases)
- **Revenue Recovered**: ₹5.08M recovered out of ₹8.57M recoverable revenue."

---

### 4:20–4:45 | RELIABILITY & RESILIENCE

**Presenter Speaking**:
"PayPilot AI is built for enterprise resilience:
- **HMAC SHA256 Webhook Security**: Every webhook is verified over raw bytes. Mismatched signatures return HTTP 401.
- **Idempotency Protection**: `x-razorpay-event-id` checks prevent duplicate event processing.
- **AI Fallback Engine**: If Gemini API key is unconfigured or rate limited, system falls back to heuristic rules without failing.
- **Test Suite Verification**: **96/96 backend tests passed** and **16 resilience scenarios passed**."

---

### 4:45–5:00 | CLOSING

**Presenter Speaking**:
"PayPilot AI doesn't just predict failed payments.

It detects revenue at risk, diagnoses the failure, chooses a bounded recovery action, executes it through Razorpay Test Mode, verifies the outcome, knows when to stop, and records the entire decision trail.

Thank you."
