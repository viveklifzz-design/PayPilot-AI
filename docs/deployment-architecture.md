# PayPilot AI — Deployment Architecture Specification

## 1. Overview & System Topology
PayPilot AI is architected as a decoupled, environment-driven web application comprising a Next.js 14 frontend and a FastAPI backend with asynchronous database persistence.

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                           Client Browser                                │
│                   (Navigates to Public Frontend)                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTPS (API requests & 12s polling)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               Public Frontend (Vercel / Next.js 14)                     │
│               Config: NEXT_PUBLIC_API_BASE_URL                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTPS (REST API calls)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               Public Backend (Render / Railway / FastAPI)               │
│               Config: PORT, DATABASE_URL, CORS_ORIGINS                  │
└─────────────────────────────────────────────────────────────────────────┘
                   │                │                 │
      ┌────────────┘                │                 └────────────┐
      ▼                             ▼                              ▼
┌───────────┐            ┌─────────────────────┐        ┌─────────────────────┐
│ Database  │            │ Razorpay Test API   │        │ Google Gemini AI    │
│ (SQLite / │            │ & Live Webhook      │        │ Diagnostic Service  │
│PostgreSQL)│            │ Ingestion Endpoint  │        │ (gemini-3.6-flash)  │
└───────────┘            └─────────────────────┘        └─────────────────────┘
```

---

## 2. Component Deployment Breakdown

### 2.1 Public Frontend (Next.js 14 / Vercel)
- **Framework**: Next.js 14 (App Router, TypeScript, Tailwind CSS)
- **Deployment Platform**: Vercel (or any Node.js 18+ container environment)
- **Environment Variables**:
  - `NEXT_PUBLIC_API_BASE_URL`: Full HTTPS origin of deployed backend (e.g. `https://paypilot-backend.onrender.com`).
- **Build Target**: Static site generation & SSR (`next build` $\rightarrow$ `next start`).

### 2.2 Public Backend (FastAPI / Render / Railway)
- **Framework**: FastAPI (ASGI with Uvicorn)
- **Deployment Platform**: Render, Railway, Fly.io, or AWS App Runner
- **Startup Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables**:
  - `PORT`: Automatically assigned HTTP port (e.g. `8000` / `$PORT`)
  - `ENVIRONMENT`: `production`
  - `CORS_ORIGINS`: Comma-separated public frontend origins (e.g. `https://paypilot-ai.vercel.app`)
  - `DATABASE_URL`: `sqlite+aiosqlite:///./paypilot_dev.db` or `postgresql+asyncpg://user:pass@host:5432/paypilot`
  - `RAZORPAY_KEY_ID`: Razorpay Test Key ID (`rzp_test_...`)
  - `RAZORPAY_KEY_SECRET`: Razorpay Test Key Secret
  - `RAZORPAY_WEBHOOK_SECRET`: Razorpay Webhook Secret
  - `GEMINI_API_KEY`: Google Gemini API Key

### 2.3 Database Persistence Layer
- **Engine**: SQLite (`aiosqlite`) for local/demo or PostgreSQL (`asyncpg`) for production.
- **Auto-Initialization**: SQLAlchemy `Base.metadata.create_all` initializes schema automatically on startup.
- **Data Isolation**: Production transaction tables are strictly separated from synthetic benchmark evaluation data.

---

## 3. HTTPS & Security Requirements
- **Enforced HTTPS**: Public backend must run behind an SSL/TLS terminating proxy to process HTTPS webhook notifications from Razorpay.
- **CORS Isolation**: FastAPI CORS middleware strictly limits allowed origins to `CORS_ORIGINS`. Wildcard `*` origins are rejected in production.
- **Zero Secret Exposure**: Frontend client bundles never contain `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, or `GEMINI_API_KEY`.
