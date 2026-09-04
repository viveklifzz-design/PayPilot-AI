# PayPilot AI — Razorpay Integration & Webhook Specification

**Track 03 — AI Revenue Recovery | Razorpay AI Buildathon**

This document describes the official Razorpay Test Mode integration, Order flow, Webhook pipeline, HMAC SHA256 signature verification, idempotency logic, and security protocols used in PayPilot AI.

---

## 1. Overview & Verified APIs

PayPilot AI integrates with Razorpay Test Mode via the official Python SDK (`razorpay`).

### Real vs. Simulated Capabilities

| Capability | Integration Status | Notes / API Endpoints |
| :--- | :--- | :--- |
| **Order Creation** | **REAL Test Mode API** | `POST /v1/orders` (`client.order.create`) |
| **Payment Link Creation** | **REAL Test Mode API** | `POST /v1/payment_links` (`client.payment_link.create`) |
| **Webhook Signature Verification** | **REAL Test Mode Security** | HMAC SHA256 with `x-razorpay-signature` |
| **Idempotency Verification** | **REAL Database Check** | Header `X-Razorpay-Event-Id` logged in `webhook_events` |
| **Payment Status Query** | **REAL Test Mode API** | `GET /v1/payments/{payment_id}` (`client.payment.fetch`) |
| **Simulated Payment Triggers** | **SIMULATED Helper** | Dev test script emitting valid HMAC-signed webhooks for rapid testing |

---

## 2. Environment Configuration

All Razorpay credentials are strictly managed via environment variables.

| Environment Variable | Description | Example / Format |
| :--- | :--- | :--- |
| `RAZORPAY_KEY_ID` | Razorpay Test Mode Key ID | `rzp_test_YOUR_KEY_IDXX` |
| `RAZORPAY_KEY_SECRET` | Razorpay Test Mode Secret | `YYYYYYYYYYYYYYYYYYYYYYYY` |
| `RAZORPAY_WEBHOOK_SECRET` | Webhook signing secret | `whsec_ZZZZZZZZZZZZZZZZ` |

> **SECURITY GUARD**: Secrets are NEVER exposed to the frontend, NEVER logged in application logs, and NEVER committed to Git (`.gitignore` enforced).

---

## 3. Order & Payment Flow Architecture

```
Client / Tester
     │
     │  1. POST /api/v1/payments/orders { amount: 1500, currency: "INR" }
     ▼
PayPilot Backend
     │
     │  2. Razorpay API Call: client.order.create(amount=150000, currency="INR")
     ▼
Razorpay Test Servers ──> Returns Order Object { id: "order_Kxyz123", status: "created" }
     │
     │  3. Persists Transaction { razorpay_order_id: "order_Kxyz123", status: "created" }
     ▼
Transaction Record in Database (Status: created)
```

---

## 4. Webhook Ingestion & Signature Verification Pipeline

```
Razorpay Webhook Dispatch
          │
          │  POST /api/v1/webhooks/razorpay
          │  Headers: x-razorpay-signature, x-razorpay-event-id
          ▼
┌─────────────────────────────────────────────────────────┐
│ 1. Read RAW Body Bytes (Before JSON parsing)            │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Compute HMAC-SHA256(raw_body_bytes, secret)          │
│    Compare with x-razorpay-signature (constant-time)   │
└───────────────────────────┬─────────────────────────────┘
                            │
               ┌────────────┴────────────┐
             Valid                     Invalid
               │                         │
               ▼                         ▼
┌─────────────────────────────┐   ┌─────────────────────────────┐
│ 3. Check Event Idempotency  │   │ Reject 401 Unauthorized     │
│    in webhook_events        │   │ Log Security Audit          │
└──────────────┬──────────────┘   └─────────────────────────────┘
               │
      ┌────────┴────────┐
    New               Duplicate
      │                 │
      ▼                 ▼
┌─────────────┐   ┌───────────────────────────────────────────┐
│ 4. Persist  │   │ Return 200 OK ("Webhook already processed")│
│ Event & Run │   └───────────────────────────────────────────┘
│ Pipeline    │
└─────────────┘
```

---

## 5. Signature Verification Implementation

Signature verification MUST be performed against the raw HTTP request body string before any JSON deserialization:

```python
import hmac
import hashlib

def verify_razorpay_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    if not signature or not secret:
        return False
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)
```

---

## 6. Supported Razorpay Webhook Events

| Event Name | Trigger Condition | System Action |
| :--- | :--- | :--- |
| `payment.authorized` | Payment authorized by issuing bank | Update transaction status to `authorized` |
| `payment.captured` | Payment successfully captured | Update transaction status to `captured` / `RECOVERED` |
| `payment.failed` | Payment declined or failed | Update transaction status to `failed`, extract failure `error_code` & `error_description`, create `RecoveryCase` |
| `payment_link.paid` | Recovery link paid by customer | Update transaction status to `captured`, mark `RecoveryCase` as `RECOVERED` |

---

## 7. Local Webhook Testing Strategy

During local development, Razorpay webhooks can be tested using either of two methods:

### Option A: Local Tunneling (ngrok / Cloudflare Tunnel)
1. Start local tunnel: `ngrok http 8000`
2. Copy HTTPS forwarding URL: `https://your-subdomain.ngrok-free.app`
3. Configure webhook in Razorpay Dashboard: `https://your-subdomain.ngrok-free.app/api/v1/webhooks/razorpay`

### Option B: Local Signature Simulation Utility
Use the PayPilot backend CLI webhook emitter script (`backend/scripts/simulate_webhook.py`) which crafts valid payloads and generates real HMAC SHA256 signatures against `RAZORPAY_WEBHOOK_SECRET` for testing `/api/v1/webhooks/razorpay`.
