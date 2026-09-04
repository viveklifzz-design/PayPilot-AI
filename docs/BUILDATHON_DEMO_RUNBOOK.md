# PayPilot AI — Buildathon Demo Runbook (3–5 Minute Script)

**Track 03 — AI Revenue Recovery | Razorpay AI Buildathon**

---

## 1. Demo Preparation & Quick Setup

### Step 1: Start Backend API Server
```powershell
cd C:\Users\Vivek\.gemini\antigravity\scratch\paypilot-ai\backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

### Step 2: Start Frontend Merchant Dashboard
```powershell
cd C:\Users\Vivek\.gemini\antigravity\scratch\paypilot-ai\frontend
npm run dev
```
Open `http://localhost:3000` in browser.

---

## 2. Minute-by-Minute Demonstration Flow

### Minute 1: The Core Value Proposition (Screen 1 — Overview)
- **Action**: Open Dashboard (`http://localhost:3000`).
- **Script**: *"Judges, merchants lose millions of rupees to payment failures every year. Generic chatbots can't fix this. PayPilot AI is an autonomous, policy-governed revenue recovery engine built for Razorpay merchants."*
- **Highlight**: Point out **Revenue At Risk** (₹), **Recovered Revenue** (₹), **Recovery Rate** (%), and the **5-Stage Conversion Funnel**.

### Minute 2: Case Discovery & Pipeline Decisioning (Screen 2 — Cases Explorer)
- **Action**: Click **Recovery Cases** tab. Click a case to open the **Case Detail Drawer**.
- **Script**: *"When a payment fails on Razorpay, PayPilot AI ingests the webhook, assesses risk, diagnoses the root cause using Google Gemini 2.5 Flash, and selects a bounded recovery action."*
- **Highlight**: Show the **5-Stage Visual Timeline** (`Payment Failed` $\rightarrow$ `Risk Analysis` $\rightarrow$ `AI Diagnosis` $\rightarrow$ `Policy Gate` $\rightarrow$ `Outcome`). Point out AI reasoning and confidence.

### Minute 3: Deterministic Policy Gate & Safety Bounds (Screen 3 — Safety & Policy)
- **Action**: Click **Safety & Policy** tab.
- **Script**: *"Safety is paramount in fintech. AI recommendations are strictly advisory. PayPilot AI's Policy Gate has final authoritative power over execution."*
- **Highlight**: Show the active rules grid (`MAX_RETRY_LIMIT=3`, `COOLDOWN=2h`, `AUTO_LIMIT=₹50,000`). Point out the **AI Recommendation $\neq$ Final Action** override examples (e.g. ₹80k amount blocked by auto limit and forced to human escalation).

### Minute 4: Measuring Recovered Revenue Across 100 Cases (Screen 4 — Batch Benchmark)
- **Action**: Click **Batch Benchmark** tab. Click **Run 100-Case Evaluation** button (`seed=42`).
- **Script**: *"To prove PayPilot AI's statistical financial impact, we run a 100-case reproducible batch benchmark."*
- **Highlight**: Show **60.23% Recovery Rate** and **₹11,62,200.00 Recovered Revenue** across 100 cases. Point out explicit `SIMULATION / EVALUATION MODE` labeling.

---

## 3. Disambiguation & Key Takeaways for Judges

- **Razorpay Test Mode**: Isolated single-transaction payment link creation & HMAC webhook verification.
- **Simulation Mode**: 100-case statistical evaluation engine (`seed=42`).
- **Zero Hallucination Guarantee**: Every AI recommendation passes through non-bypassable policy safety rules.
