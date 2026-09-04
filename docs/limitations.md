# PayPilot AI — System Limitations & Operational Scope

## Overview
This document honestly classifies real system boundaries and operational limitations discovered during engineering and evaluation.

---

## Technical Limitations Matrix

| Domain | Operational Limitation | Technical Context | Impact & Mitigation |
| :--- | :--- | :--- | :--- |
| **Razorpay Gateway** | Test Mode vs Real Money | Integrated exclusively with Razorpay Test Mode | Real test payments are ₹10 Test Mode transactions (no real bank money moved). |
| **Public Hosting** | Deployment Ready (Not Live) | Platform-compatible with Vercel & Render/Railway | Live third-party hosting not kept active to avoid ongoing cloud costs. |
| **Synthetic Dataset** | Benchmark vs Live Data | Benchmark uses 1,000 synthetic failure cases (Seed 42) | Benchmark metrics evaluate AI engine accuracy; clearly labeled `"Synthetic Evaluation — No Real Money"`. |
| **AI Provider** | External Network Dependency | Uses Google Gemini (`gemini-3.6-flash`) | If API key is missing or rate limited, system falls back to `FallbackAIService` heuristic rules. |
| **Public Webhooks** | Tunnel URL Lifecycle | Cloudflare Quick Tunnels generate dynamic domain URLs | Restarting `cloudflared` requires updating the Webhook URL in Razorpay Dashboard. |
| **Database Engine** | Default SQLite Development DB | SQLite used for local dev (`paypilot_dev.db`) | Fully compatible with PostgreSQL (`asyncpg`) for high-concurrency production deployments. |
