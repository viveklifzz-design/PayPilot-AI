# PayPilot AI — Fallback Demo Rehearsal & Contingency Plan

## 1. Golden Safety Rule
> **NEVER FAKE RECOVERY**: If live payment or webhook ingestion experiences latency during a presentation, fall back to previously verified records while explicitly stating: *"This is a previously verified Razorpay Test Mode recovery."*

---

## 2. Contingency Rehearsal Matrix

| Contingency Scenario | System Fallback Behavior | Presenter Reaction |
| :--- | :--- | :--- |
| **Razorpay API Latency** | Payment Link creation takes $>10\text{s}$ | Switch to existing verified case `#rec_...` with active Payment Link ID (`plink_...`) |
| **Delayed Webhook Event** | `payment_link.paid` webhook queue delayed | Show `CREATED` action state & raw webhook audit log entry |
| **Gemini AI Unavailability** | External LLM API rate limit or outage | `FallbackAIService` populates heuristic diagnosis (Confidence: 0.85) |
| **Frontend Tab Reload** | Presenter reloads browser tab | Page reloads static chunks (`chunks/...js`) and reconnects to backend |
| **Tunnel Expiration** | Cloudflare Quick Tunnel expires | Present on local backend URL `http://localhost:8000` |
