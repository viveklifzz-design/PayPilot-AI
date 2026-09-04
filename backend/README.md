# PayPilot AI — Backend Service

**Track 03 — AI Revenue Recovery | Razorpay AI Buildathon**

Autonomous revenue recovery agent backend built with FastAPI, Async SQLAlchemy, Razorpay Test API Integration, and HMAC Webhook Pipeline.

---

## 1. Prerequisites & System Requirements

- **Python**: 3.10+ (Tested on Python 3.12)
- **Database**: PostgreSQL (or SQLite for local dev/testing)
- **Package Manager**: `pip`

---

## 2. Virtual Environment Setup

From the `backend/` directory:

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Activate on macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 3. Environment Variables Setup

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Configurable variables in `.env`:
- `PROJECT_NAME`: Application title (`PayPilot AI`)
- `ENVIRONMENT`: Environment mode (`development` / `production`)
- `DATABASE_URL`: Database connection string (`sqlite+aiosqlite:///./paypilot_dev.db` or `postgresql://postgres:postgres@localhost:5432/paypilot_db`)
- `RAZORPAY_KEY_ID`: Razorpay Test Mode Key ID (`rzp_test_...`)
- `RAZORPAY_KEY_SECRET`: Razorpay Test Mode Key Secret
- `RAZORPAY_WEBHOOK_SECRET`: Secret used for webhook HMAC signature verification
- `GEMINI_API_KEY`: Google Gemini API Key

---

## 4. Database Setup & Migration Commands

Database tables can be initialized automatically on server boot, or manually via Alembic migrations:

```bash
# Run online database migrations to head
alembic upgrade head

# Create a new migration revision
alembic revision --autogenerate -m "Describe migration"
```

---

## 5. Phase 2 API Endpoints

- **`GET /health`**: Application service status check.
- **`GET /health/db`**: Live database connectivity verification.
- **`POST /api/v1/payments/orders`**: Create a Razorpay Test Mode Order & persist `Transaction`.
- **`POST /api/v1/webhooks/razorpay`**: HMAC SHA256 signature-verified webhook receiver with idempotency checking.
- **`GET /api/v1/transactions`**: List transactions with optional status filter.
- **`GET /api/v1/transactions/{id}`**: Get detailed transaction by ID.

---

## 6. Local Webhook Simulation Utility

To simulate sending valid Razorpay webhooks with real HMAC SHA256 signatures locally:

```bash
python scripts/simulate_webhook.py
```

---

## 7. Running the Backend Application

Launch the FastAPI development server with auto-reload:

```bash
uvicorn app.main:app --reload --port 8000
```

Interactive API documentation:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 8. Running Test Suite

Run unit and integration tests using `pytest`:

```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v
```
