# Razorpay Test Mode Payment Failure Testing Guide

> **IMPORTANT NOTICE**: This document describes testing payment failure events using **Razorpay Test Mode**. No real money is moved or charged.

---

## 1. Supported Test Mode Failure Methods in Razorpay

When interacting with the Razorpay Checkout modal or Payment Link in **Test Mode** (`rzp_test_...`), Razorpay supports official failure scenarios:

### Method A: UPI Failure Scenario
- **VPA / UPI ID**: `failure@razorpay`
- **Behavior**: Entering `failure@razorpay` on the Razorpay UPI checkout screen immediately generates a real `payment.failed` event with:
  - `error_code`: `BAD_REQUEST_ERROR`
  - `error_source`: `bank`
  - `error_step`: `payment_authorization`
  - `error_reason`: `payment_verification_failed`

### Method B: Card Failure Scenarios (Standard Test Cards)
- **Test Card Number**: `4111 1111 1111 1111` (Visa Test Card)
- **Modal Action**: In Test Mode popup, select **Failure** option when prompted to simulate bank decline or OTP failure.
- **Behavior**: Generates `payment.failed` event with authentication / bank failure flags.

---

## 2. End-to-End Test Procedure

1. **Start Backend Server**:
   ```bash
   cd backend
   .\venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

2. **Start Frontend Server**:
   ```bash
   cd frontend
   npm run start
   ```

3. **Verify Razorpay Test Mode Health**:
   Open `http://localhost:8000/api/v1/health/razorpay` and verify `"test_mode": true`.

4. **Trigger Payment Failure in Razorpay Checkout**:
   - Open a Razorpay Payment Link or Test Checkout.
   - Enter test email/phone.
   - Choose UPI method $\rightarrow$ Enter VPA `failure@razorpay`.
   - Click Pay.

5. **Verify `payment.failed` Webhook Ingestion**:
   - Razorpay dispatches signed `payment.failed` webhook.
   - PayPilot receives payload, verifies HMAC SHA256 signature, extracts `error_code`, `error_description`, `error_source`, `error_step`, `error_reason`, and creates a `RecoveryCase`.

6. **View Payment Failure Intelligence in PayPilot Dashboard**:
   - Open `http://localhost:3000/cases`.
   - Click on the newly created Recovery Case to open `CaseDetailDrawer`.
   - Inspect the **RAZORPAY PAYMENT FACTS** card to view the exact failure attributes from Razorpay.

---

## 3. Local Inspection Utility (Test Fixture Only)

To inspect any persisted payment failure transaction and its facts via CLI:
```bash
cd backend
.\venv\Scripts\python scripts/inspect_payment_failure.py
```
