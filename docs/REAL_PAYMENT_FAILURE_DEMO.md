# Real Razorpay Payment Failure & Recovery Demo Guide

## 1. Overview & Setup
This guide explains how to demonstrate a complete, verified revenue recovery lifecycle in **Razorpay Test Mode** for **PayPilot AI**.

---

## 2. Step-by-Step Setup Instructions

### Step 1: Start PayPilot Backend
```bash
cd backend
.\venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Step 2: Start Next.js Production Frontend
```bash
cd frontend
npm run start
```
Frontend URL: `http://localhost:3000`

### Step 3: Expose Local Webhook Endpoint (Optional for Live Webhook Delivery)
If testing live webhooks from Razorpay Dashboard:
```bash
ngrok http 8000
```
Copy the generated HTTPS URL (e.g., `https://xxxx.ngrok-free.app`).

### Step 4: Configure Razorpay Webhook
1. Log into [Razorpay Dashboard (Test Mode)](https://dashboard.razorpay.com/).
2. Navigate to **Settings** $\rightarrow$ **Webhooks** $\rightarrow$ **Add New Webhook**.
3. Set Webhook URL: `https://xxxx.ngrok-free.app/api/v1/webhooks/razorpay` (or local simulation endpoint).
4. Secret: Set matching secret configured in `RAZORPAY_WEBHOOK_SECRET`.
5. Active Events: Select `payment.failed`, `payment_link.paid`, `payment.captured`.

---

## 3. Triggering a Real Payment Failure in Test Mode

1. Initiate a test payment transaction via standard Razorpay Checkout modal or API.
2. In Razorpay Test Mode modal:
   - For Card: Use test card numbers designed to fail (or select "Failure" in Test Mode modal).
   - For Netbanking: Select any test bank and choose "Fail" on the simulated bank page.
   - For UPI: Enter test failure VPA `failure@razorpay`.
3. Razorpay emits `payment.failed` webhook payload containing:
   - `id`: Payment ID (`pay_...`)
   - `error_code`: Error code (e.g. `BAD_REQUEST_ERROR`)
   - `error_description`: Failure description
   - `error_source`: Failure origin (`bank`, `gateway`, `customer`)
   - `error_step`: Failure step (`payment_authorization`)
   - `error_reason`: Exact reason key (e.g. `payment_verification_failed`)

---

## 4. PayPilot Ingestion & Verification Sequence

```text
Razorpay payment.failed Ingested
        │
        ├── Extract & persist error_code, error_source, error_step, error_reason
        ├── Classify failure category (AUTHENTICATION_FAILURE, BANK_FAILURE, etc.)
        ├── Run Gemini AI Diagnosis (receives authoritative Razorpay facts)
        ├── Evaluate Policy Safety Gate (Confidence >= 0.70, Retries <= 3, Cooldown >= 1h)
        └── Create Razorpay Payment Link (plink_... / https://rzp.io/...)
        │
Customer completes Payment Link payment
        │
        ├── Ingest payment_link.paid webhook (HMAC SHA256 verified)
        ├── Transition RecoveryCase status to RECOVERED
        └── Update recovered_amount idempotently
```
