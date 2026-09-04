# PayPilot AI — Public Deployment Webhook Guide

## 1. Public Endpoint & Security Specification
PayPilot AI ingests live payment failure and recovery events from Razorpay via a public HTTPS webhook endpoint.

- **Public Endpoint Format**: `https://YOUR-BACKEND-DOMAIN/api/v1/webhooks/razorpay`
- **Supported Events**:
  - `payment.failed` (Triggers Risk Engine assessment and RecoveryCase creation)
  - `payment.authorized` (Updates transaction authorization state)
  - `payment.captured` (Confirms transaction payment capture)
  - `payment_link.paid` (Executes automated case recovery completion and updates case state to `RECOVERED`)

---

## 2. Webhook Security & Ingestion Architecture

```text
Razorpay Gateway ──────► [POST /api/v1/webhooks/razorpay]
                                │
                                ▼
                   ┌──────────────────────────┐
                   │ Raw Request Body & Header│
                   │ Extraction (x-razorpay-  │
                   │        signature)        │
                   └──────────────────────────┘
                                │
                                ▼
                   ┌──────────────────────────┐
                   │ HMAC SHA256 Verification │
                   │  (Secret: WEBHOOK_SECRET)│
                   └──────────────────────────┘
                                │
                      ┌─────────┴─────────┐
                      ▼                   ▼
                  [PASS]               [FAIL]
                      │                   │
                      ▼                   ▼
           ┌─────────────────────┐   ┌─────────┐
           │ Idempotency Check   │   │ HTTP 401│
           │(x-razorpay-event-id)│   │  Reject │
           └─────────────────────┘   └─────────┘
```

---

## 3. Mandatory Security Controls
1. **HMAC SHA256 Signature Check**: Every request is verified using `hmac.new(secret, body, hashlib.sha256).hexdigest()`. Missing or invalid signatures return **HTTP 401 Unauthorized**.
2. **Raw Body Integrity**: Verification uses the unparsed bytes raw payload to prevent JSON re-serialization key-reordering discrepancies.
3. **Header Case-Insensitivity**: Signature header lookup supports `x-razorpay-signature`, `X-Razorpay-Signature`, or custom variations.
4. **Idempotency Prevention**: The database checks `x-razorpay-event-id`. Duplicate event deliveries return HTTP 200 (`status: ignored`) without mutating records or executing duplicate recovery actions.
5. **Unsupported Event Safety**: Unregistered event types return HTTP 200 (`status: ignored`) without throwing exceptions.

---

## 4. Razorpay Dashboard Webhook Configuration Steps

1. Log in to the [Razorpay Dashboard](https://dashboard.razorpay.com/) (Test or Live Mode).
2. Go to **Settings** $\rightarrow$ **Webhooks** $\rightarrow$ Click **Add New Webhook**.
3. Fill in the fields:
   - **Webhook URL**: `https://YOUR-BACKEND-DOMAIN/api/v1/webhooks/razorpay`
   - **Secret**: Enter the value of `RAZORPAY_WEBHOOK_SECRET` defined in your backend environment variables.
   - **Alert Email**: Enter your engineering contact email.
4. Select Active Events:
   - `payment.failed`
   - `payment.authorized`
   - `payment.captured`
   - `payment_link.paid`
5. Click **Save / Create Webhook**.
