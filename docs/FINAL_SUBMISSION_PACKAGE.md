# PayPilot AI — Final Submission Package Summary

## 1. Hackathon Submission Overview

- **Project Name**: PayPilot AI
- **Track**: Track 03 — Revenue Recovery
- **Core Capability**: Bounded Autonomous Revenue Recovery Pipeline
- **Frontend Architecture**: Next.js 14 (App Router, TypeScript, Tailwind CSS)
- **Backend Architecture**: FastAPI (ASGI with Uvicorn, Python 3.10+)
- **Database Layer**: Async SQLAlchemy (`aiosqlite` / `asyncpg` compatible)
- **AI Failure Diagnosis**: Google Gemini AI (`gemini-3.6-flash`) with heuristic fallback
- **Payment Gateway**: Razorpay Test Mode (`rzp_test_...`)
- **Webhook Security**: HMAC SHA256 signature verification over raw request payload
- **Synthetic Benchmark**: 1,000 synthetic payment failure cases (Seed 42)
- **Public Deployment Status**: **NOT LIVE (ENVIRONMENT READY)**
- **Backend Pytest Suite**: **96 / 96 PASSED** in 8.41s
- **Frontend Production Build**: **✓ Compiled successfully** (0 errors)
- **Public Demo E2E Suite**: **10 / 10 CHECKS PASSED**
- **Documentation Index**: 24 technical architecture & judge evidence files

---

## 2. Key Differentiators & Highlights

1. **Deterministic Safety Boundary**: AI recommends, but Policy Gate controls. 0 unsafe actions executed.
2. **Real Razorpay Test Mode**: Ingests real ₹10 test payments and payment link callbacks.
3. **Full 7-Stage Auditability**: Emits complete chronological decision timeline with IST timestamps (`Asia/Kolkata`).
4. **Data Isolation**: Real Razorpay Test Mode transaction data is strictly separated from synthetic benchmark evaluation data.
