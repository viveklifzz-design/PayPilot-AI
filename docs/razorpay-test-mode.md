# PayPilot AI — Razorpay Test Mode Integration Setup Guide

## 1. Test Mode Notice
> **TEST MODE ONLY — NO REAL MONEY**: PayPilot AI integrates exclusively with Razorpay Test Mode for development, testing, and evaluation. No real money transactions are performed.

---

## 2. Obtaining Razorpay Test Credentials

1. Log in to your [Razorpay Dashboard](https://dashboard.razorpay.com/).
2. Switch the top toggle from **Live Mode** to **Test Mode**.
3. Navigate to **Settings** $\rightarrow$ **API Keys** $\rightarrow$ Click **Generate Test Key**.
4. Copy your credentials:
   - **Key ID**: `rzp_test_YOUR_KEY_ID`
   - **Key Secret**: `YOUR_RAZORPAY_KEY_SECRET`
5. Save these values to your local `.env` file:
   ```env
   RAZORPAY_KEY_ID=rzp_test_YOUR_KEY_ID
   RAZORPAY_KEY_SECRET=YOUR_RAZORPAY_KEY_SECRET
   ```

---

## 3. Configuring Webhooks for Automated Recovery

1. In the Razorpay Dashboard (Test Mode), navigate to **Settings** $\rightarrow$ **Webhooks**.
2. Click **Add New Webhook**.
3. Enter Webhook Details:
   - **Webhook URL**:
     - Local Dev: `http://localhost:8000/api/v1/webhooks/razorpay`
     - Public Demo (Cloudflare Tunnel): `https://<subdomain>.trycloudflare.com/api/v1/webhooks/razorpay`
   - **Secret**: Enter your secret string (e.g. `YOUR_WEBHOOK_SECRET`)
4. Select Active Events:
   - `payment.failed` (Triggers Risk Engine & case creation)
   - `payment.authorized` (Updates transaction state)
   - `payment.captured` (Confirms payment capture)
   - `payment_link.paid` (Executes automated case recovery completion)
5. Save the secret to `.env`:
   ```env
   RAZORPAY_WEBHOOK_SECRET=YOUR_WEBHOOK_SECRET
   ```

---

## 4. End-to-End Webhook & Recovery Verification

1. Start backend and frontend servers:
   ```bash
   # Terminal 1 - Backend
   cd backend
   .\venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

   # Terminal 2 - Frontend
   cd frontend
   npm run start
   ```
2. Verify Razorpay Connection status in top navbar header badge (**`Razorpay Test Mode — Connected`**).
3. Trigger a test payment or webhook simulation.
4. Verify HMAC signature check in backend logs (`verification_result=PASS`).
5. Observe transaction appearing in **Recent Razorpay Transactions** and case creation in **Recovery Cases**.
