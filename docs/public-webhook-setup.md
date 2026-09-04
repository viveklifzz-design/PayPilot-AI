# PayPilot AI — Public Razorpay Webhook & Cloudflare Tunnel Setup Guide

## 1. Webhook Security Architecture Overview
PayPilot AI ingests live payment events from Razorpay using HMAC SHA256 signature verification.

- **Local Endpoint**: `http://localhost:8000/api/v1/webhooks/razorpay`
- **Public Tunnel Endpoint**: `https://<generated-subdomain>.trycloudflare.com/api/v1/webhooks/razorpay`
- **Supported Events**:
  - `payment.failed` (Triggers Risk Engine assessment and RecoveryCase creation)
  - `payment.authorized` (Updates transaction authorization state)
  - `payment.captured` (Confirms transaction payment capture)
  - `payment_link.paid` (Executes automated recovery completion and updates case state to `RECOVERED`)

---

## 2. Setting Up Cloudflare Quick Tunnel
To expose the local FastAPI backend running on port 8000 to the public internet for Razorpay webhooks:

1. **Install Cloudflared CLI** (if not already installed):
   ```bash
   winget install Cloudflare.cloudflared
   ```
2. **Launch Quick Tunnel**:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```
3. **Capture Public HTTPS URL**:
   Look for the generated line in the terminal output:
   ```text
   +-----------------------------------------------------------------------------------+
   | Your quick Tunnel has been created! Visit it at:                                  |
   | https://random-name-subdomain.trycloudflare.com                                    |
   +-----------------------------------------------------------------------------------+
   ```

---

## 3. Configuring Razorpay Dashboard Webhook
1. Log in to the [Razorpay Dashboard](https://dashboard.razorpay.com/) in **Test Mode**.
2. Navigate to **Settings** $\rightarrow$ **Webhooks** $\rightarrow$ Click **Add New Webhook**.
3. Fill in the configuration details:
   - **Webhook URL**: `https://random-name-subdomain.trycloudflare.com/api/v1/webhooks/razorpay`
   - **Secret**: Enter the exact secret string defined in your local `.env` (`RAZORPAY_WEBHOOK_SECRET`)
   - **Alert Email**: Enter your developer alert email
4. Select the required **Active Events**:
   - `payment.failed`
   - `payment.authorized`
   - `payment.captured`
   - `payment_link.paid`
5. Click **Create Webhook**.

---

## 4. Security & Idempotency Guarantees
- **HMAC Verification**: PayPilot AI computes `hmac.new(secret, body, hashlib.sha256).hexdigest()` and verifies it against the `x-razorpay-signature` header before processing.
- **Header Case-Insensitivity**: Signature header is checked case-insensitively (`x-razorpay-signature` or `X-Razorpay-Signature`).
- **Event Idempotency**: Every webhook request evaluates `x-razorpay-event-id`. Duplicate event IDs return HTTP 200 (`status: ignored`) without mutating database records.
- **Tunnel Lifecycle Note**: Cloudflare Quick Tunnels generate a new URL when restarted. If you restart `cloudflared`, update the Webhook URL in the Razorpay Dashboard.
