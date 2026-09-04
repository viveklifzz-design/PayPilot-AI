# PAYPILOT AI — FINAL JUDGE DEMO REHEARSAL SCRIPT

## 1. Executive Summary & Demo Overview

This document provides the exact **SHOW**, **SAY**, and **WHY IT MATTERS** rehearsal walkthrough for presenting **PayPilot AI** to the judges for **Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery**.

- **Target Presentation Time**: 5 to 7 Minutes
- **Core Narrative**: PayPilot AI is an autonomous AI Revenue Recovery Command Center that turns payment failures, abandoned checkouts, failed subscriptions, overdue B2B receivables, and recurring mandates into recovered revenue—bounded by deterministic policy gates and verified by real Razorpay Test Mode webhooks.

---

## 2. Minute-by-Minute Rehearsal Script

### MINUTE 0:00 - 1:00 | ACT 1: OVERVIEW DASHBOARD & LIVE REVENUE METRICS

#### **SHOW**
- Open merchant Overview at `http://localhost:3000/`.
- Highlight top metric cards: **Total Revenue at Risk**, **Recovered Revenue**, **Policy Gate Blocks**, and **Remaining Risk**.
- Highlight the **Recovery Conversion Funnel** showing pipeline progression from failure detection to verified recovery.
- Point out the **Live Merchant Stream** badge and IST timestamp refresh bar.

#### **SAY**
> "Namaste judges! Welcome to PayPilot AI — the Autonomous Revenue Recovery Command Center purpose-built for Razorpay merchants.
> In high-volume digital commerce, payment failures, abandoned checkouts, and failed subscriptions create massive revenue leakage. PayPilot AI solves this by transforming lost revenue into recovered money.
> Notice our merchant dashboard: every financial number here is calculated dynamically from live database transactions. Zero numbers are hardcoded, and live merchant metrics are strictly isolated from synthetic benchmarks."

#### **WHY IT MATTERS**
- Establishes immediate trust and demonstrates real-time financial data lineage without fake or hardcoded numbers.

---

### MINUTE 1:00 - 3:00 | ACT 2: REAL RAZORPAY PAYMENT FAILURE RECOVERY (PRIMARY DEMO)

#### **SHOW**
- Navigate to `/transactions` and select the failed transaction (`#821dd426`).
- Display authoritative Razorpay failure facts:
  - Error Code: `BAD_REQUEST_PAYMENT_TIMED_OUT`
  - Error Source: `bank`
  - Error Step: `payment_authorization`
  - Error Reason: `payment_verification_failed`
- Show human-readable explanation: *"Payment failed due to an issuer bank authorization failure or server downtime."*
- Click to open the associated Recovery Case.
- Walk through the 7-stage lifecycle: **DETECT $\rightarrow$ DIAGNOSE $\rightarrow$ DECIDE $\rightarrow$ POLICY $\rightarrow$ EXECUTE $\rightarrow$ VERIFY $\rightarrow$ RECOVER**.
- Show Gemini 3.6 Flash AI Diagnosis (*"Temporary bank network timeout during OTP verification"*, Recommended Action: `RECOVERY_LINK`, Confidence: 92%).
- Show Policy Safety Gate status: **APPROVED** ($\text{Confidence} \ge 0.70$, $\text{Amount} \le \text{₹50,000}$, $\text{Retries} \le 3$).
- Show Razorpay Test Mode Payment Link reference `plink_TTh8tpsM68mx6P` and click the short link `https://rzp.io/rzp/vsKQMYz`.
- Show `payment_link.paid` HMAC SHA256 Webhook ingestion, transition to status **RECOVERED**, and verified recovered amount **₹2,500.00**.
- Show 7-stage Audit Trail timeline.
- Return to `/revenue-risk` and demonstrate that recovered revenue has exited active risk.

#### **SAY**
> "Here is our primary flow operating in real Razorpay Test Mode. When a payment fails, PayPilot extracts authoritative Razorpay error facts.
> Our failure classifier categorizes it as an AUTHENTICATION_FAILURE and provides a safe human explanation.
> Next, Gemini AI diagnoses the root cause and recommends a RECOVERY_LINK strategy with 92% confidence.
> But AI does NOT move money directly. Our deterministic Policy Gate verifies safety limits: confidence must be at least 70%, retries capped at 3, and auto-recovery capped at ₹50,000.
> Upon approval, PayPilot calls Razorpay's API to generate a real Test Mode Payment Link `plink_TTh8tpsM68mx6P`. When the customer pays, PayPilot ingests the `payment_link.paid` webhook, validates the HMAC signature, updates the case to RECOVERED, and records ₹2,500.00 in recovered revenue."

#### **WHY IT MATTERS**
- Proves end-to-end provider integration with genuine Razorpay credentials, real payment links, HMAC security, and money safety policy enforcement.

---

### MINUTE 3:00 - 4:30 | ACT 3: MULTI-SOURCE RECOVERY SHOWCASE

#### **SHOW**
- Navigate through `/receivables` (B2B Receivables Chaser), `/subscriptions` (Failed Subscriptions), `/mandates` (Mandate Retry Sequencer), `/communications` (Hinglish Communication Layer).
- Point out the badge on each screen: **LOCAL TEST SIMULATION**.
- On `/receivables`, show invoice `INV-2026-B2B-88` (overdue by 7 days) and registered Promise-to-Pay date. Highlight the max 3 reminders stopping rule.
- On `/mandates`, show mandate `MND-VERIFY-1787594822` (Attempt 3/3 cap reached $\rightarrow$ **CANCELLED & ESCALATED** with 24h cooldown).
- On `/communications`, demonstrate generating localized Hinglish SMS text (*"Namaste Rahul, aapka ₹2,500 ka payment complete nahi ho paya..."*) and voice script assistance. Show disclaimer: *"Voice assistance only — Money movement strictly requires Policy Gate approval."*

#### **SAY**
> "Beyond payment failures, PayPilot AI handles multi-source revenue leakage.
> In B2B Receivables, we track overdue invoices, enforce a strict stopping rule of max 3 reminders, register customer Promise-to-Pay dates, and automatically escalate missed promises.
> In Mandate Retry Sequencer, we enforce bounded retry scheduling with 24-hour cooldowns and automatic escalation when 3 retries are exceeded.
> In our Communication Center, we generate localized Hinglish, Hindi, and English recovery notifications and voice scripts — while maintaining our safety invariant: voice communication CANNOT execute money movement directly."

#### **WHY IT MATTERS**
- Demonstrates comprehensive Track 03 capabilities across all 5 revenue risk sources while maintaining honest data classification.

---

### MINUTE 4:30 - 5:30 | ACT 4: CUSTOMER PORTAL & STRICT OWNERSHIP SECURITY

#### **SHOW**
- Navigate to `/customer`.
- Sign in as `customer@merchant.com` (`customer_id: cust_a`).
- Enter Transaction ID `821dd426-343c-4660-88d3-f59545d3fbd5` and click Lookup.
- Show customer view: Status `failed`, Amount `₹2,500.00`, official failure explanation, and `Complete Payment` button linking to Razorpay Payment Link.
- **SECURITY DEMONSTRATION**: Sign in as Customer B (`cust_b`) and attempt to look up Customer A's transaction ID `821dd426`.
- Show clean UI error banner: **`HTTP 403 Forbidden — Access Denied: You do not have permission to view another customer's transaction.`**

#### **SAY**
> "Now let me show you the Customer Recovery Portal at `/customer`. Customers can log in, enter their transaction ID, review the official failure reason, and complete their payment via Razorpay.
> Most importantly, customer privacy and security are strictly enforced. Watch what happens when Customer B tries to guess Customer A's transaction ID: PayPilot intercepts the request and returns HTTP 403 Forbidden with zero data leakage."

#### **WHY IT MATTERS**
- Proves enterprise-grade customer authentication and ownership security protection.

---

### MINUTE 5:30 - 6:30 | ACT 5: SYNTHETIC EVALUATION BENCHMARK & CLOSING

#### **SHOW**
- Navigate to `/benchmark`.
- Point out the prominent warning badge: **`SYNTHETIC EVALUATION — NO REAL MONEY`**.
- Show 1,000-case reproducible benchmark results (Seed 42):
  - Revenue at Risk: ₹17,950,799.00
  - Recovered Revenue: ₹3,710,722.00
  - Precision: **77.76%** | Recall: **84.98%** | Recovery Rate: **56.5%**
  - **Unsafe Actions: 0**
- Show audit trail at `/audit`.

#### **SAY**
> "Finally, under `/benchmark`, we evaluate PayPilot AI's intelligence across a 1,000-case synthetic dataset.
> In deterministic mode with seed 42, PayPilot achieves 77.76% precision, 84.98% recall, and a 56.5% recovery rate — with ZERO policy safety violations.
> Notice our clear data classification: synthetic evaluation numbers stay under `/benchmark` and are never mixed with live merchant revenue.
> In summary, PayPilot AI is a complete, hardened, evidence-backed AI Revenue Recovery solution ready for production. Thank you!"

#### **WHY IT MATTERS**
- Concludes the demo with quantitative benchmark evidence, zero policy violations, and absolute financial data integrity.
