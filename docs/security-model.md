# PayPilot AI — Security Model & Controls Specification

## 1. Security Architecture Summary
PayPilot AI implements end-to-end security controls spanning credential isolation, HMAC webhook verification, secret redaction, CORS origins, and production error sanitization.

---

## 2. Key Security Controls Matrix

| Security Layer | Control Description | Verification Mechanism |
| :--- | :--- | :--- |
| **Credential Isolation** | API keys and secrets stored exclusively in local `.env` | Scanned repository git tracking; zero secrets committed |
| **Git Exclusion** | `.env`, `.env.*`, `venv/`, `node_modules/`, `*.db` in `.gitignore` | Verified git exclusion rules |
| **HMAC SHA256 Webhook Auth** | Computed signature compared with `x-razorpay-signature` | Mismatched signatures rejected with HTTP 401 |
| **Raw Request Body Verification** | Webhook HMAC computed over raw unparsed bytes | Prevents JSON key-reordering verification bypass |
| **Event Idempotency** | Database stores processed `x-razorpay-event-id` | Duplicate webhooks return HTTP 200 (`ignored`) without DB mutation |
| **Secret Redaction API** | `sanitize_metadata` strips sensitive keys | Replaces secrets with `[REDACTED_SECRET]` in audit endpoints |
| **Configurable CORS** | Environment-driven `CORS_ORIGINS` origins | FastAPI CORS middleware rejects unauthorized origins |
| **Production Exception Redaction** | Custom ASGI exception handlers | Production errors return clean JSON without stack traces or SQL |
| **Network Timeout Controller** | 10s `AbortController` in `fetchJson` | Prevents hanging client connections or request floods |
