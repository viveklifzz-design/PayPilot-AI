# PayPilot AI — 5-Minute Judge Quickstart & Walkthrough

## 1. Quick Setup (Fresh Machine)

### Step 1: Environment Setup
```bash
# Clone repository
git clone https://github.com/your-username/paypilot-ai.git
cd paypilot-ai
cp .env.example .env
```

### Step 2: Start Backend (Terminal 1)
```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1    # Windows PowerShell
# source venv/bin/activate    # Linux/macOS
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
*Verify Backend*: `http://localhost:8000/api/v1/health`

### Step 3: Start Frontend (Terminal 2)
```bash
cd frontend
npm ci
npm run build
npm run start
```
*Open Dashboard*: `http://localhost:3000`

---

## 2. 15-Step Judge Walkthrough

1. **Dashboard Home** (`http://localhost:3000`): View the clean executive interface.
2. **Razorpay Status**: Verify **`Razorpay Test Mode — Connected`** badge in top navbar.
3. **Backend Status**: Verify **`Backend — Connected`** badge.
4. **Revenue Metrics**: Inspect **Revenue at Risk** (failed payment value) and **Recovered Revenue**.
5. **Recent Transactions**: Scroll to the live transaction stream.
6. **Real Payment Event**: Locate a ₹10 test transaction (`pay_...`).
7. **IST Timestamps**: Note unambiguous IST timestamp formatting (`DD Mon YYYY, hh:mm:ss AM/PM IST`).
8. **Recovery Case Trace Drawer**: Click any case to open the `CaseDetailDrawer`.
9. **AI Diagnosis**: View root cause analysis, failure category, and confidence score ($88\%$).
10. **AI Recommendation**: View proposed action (`RECOVERY_LINK`).
11. **Policy Safety Gate**: View **`POLICY APPROVED`** card enforcing confidence thresholds, retry limits, cooldowns, and amount limits.
12. **Razorpay Execution**: Inspect real Razorpay Payment Link ID (`plink_...`) and payment URL (`https://rzp.io/...`).
13. **Webhook Trace**: Confirm `payment_link.paid` webhook event ingestion.
14. **Audit Timeline**: Review the 7-Stage Chronological Decision Timeline (`DETECT` $\rightarrow$ `DIAGNOSE` $\rightarrow$ `DECIDE` $\rightarrow$ `POLICY` $\rightarrow$ `EXECUTE` $\rightarrow$ `VERIFY` $\rightarrow$ `RECOVER`).
15. **Benchmark Page** (`/benchmark`): Review the 1,000 synthetic case batch evaluation (Precision **83.69%**, Recall **86.13%**, **Unsafe Actions = 0**).

---

## 3. Demo Talking Points

- **Problem**: Failed payments cost merchants 15%-30% of revenue, but generic automated retries annoy customers and risk compliance violations.
- **Autonomous Loop**: PayPilot AI automatically detects, diagnoses, gates, executes, and verifies revenue recovery end-to-end.
- **AI Role**: Gemini AI diagnoses failure root cause and proposes recovery actions.
- **Deterministic Safety**: The Policy Engine has total authority. No money action is executed unless all 5 policy safety rules pass.
- **Razorpay Integration**: Real Razorpay Test Mode integration using HMAC SHA256 webhooks and Payment Links API.
- **Data Isolation**: Live Razorpay test transactions are strictly separated from synthetic benchmark evaluation data.
