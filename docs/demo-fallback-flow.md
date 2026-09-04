# PayPilot AI — Demo Fallback & Contingency Plan

## Contingency Guidelines
> **GOLDEN RULE**: Never fake a live recovery. If a live payment or API connection experiences network delays during a judge presentation, fall back seamlessly to previously verified records while explicitly stating: *"This is a previously verified Razorpay Test Mode recovery."*

---

## Contingency Matrix

| Issue Scenario | Cause | Presenter Reaction & Action | Presenter Exact Statement |
| :--- | :--- | :--- | :--- |
| **Razorpay Payment Delay** | Test Mode payment link takes $>10\text{s}$ to trigger webhook | Open existing recovered case `#rec_...` in Case Explorer | *"While this test payment finishes processing, let's look at a previously verified Razorpay Test Mode recovery case."* |
| **Late Webhook Arrival** | Webhook delivery queue delayed | Show `CREATED` state & active Razorpay Payment Link ID (`plink_...`) | *"The payment link was successfully created via Razorpay API. We can view the active `plink_` ID and raw webhook audit log."* |
| **Gemini API Key Missing / Unreachable** | External AI rate limit or network outage | System automatically invokes `FallbackAIService` | *"Our isolated Fallback AI Service evaluates failure heuristic rules deterministically with 0.85 confidence."* |
| **Browser Hard Refresh** | Presenter accidentally refreshes tab | Page reloads static chunks (`chunks/...js`) and fetches dynamic metrics | *"The Next.js production frontend instantly reconnects to our FastAPI backend, fetching live state."* |
| **Tunnel / Domain Disconnect** | Cloudflare Quick Tunnel expires | Switch to local `http://localhost:8000` backend URL | *"We are running on local FastAPI backend port 8000 with complete Razorpay Test Mode support."* |
