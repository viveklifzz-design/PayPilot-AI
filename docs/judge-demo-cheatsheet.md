# PayPilot AI — Judge Demo Quick Reference Cheatsheet

## One-Page Presentation Cheat Sheet

| Screen / View | What to Show | What to Say | Expected Result |
| :--- | :--- | :--- | :--- |
| **Navbar Header** | Connection Badges | "Notice live connectivity: `Razorpay Test Mode — Connected` and `Backend — Connected`." | Badges render green; proves active backend & Razorpay Test API link. |
| **Overview (`/`)** | KPI Cards | "PayPilot AI tracks **Revenue at Risk** (failed attempts) vs. **Recovered Revenue**." | Displays ₹19.09M risk / ₹5.08M recovered metrics from dynamic API. |
| **Recent Transactions** | Stream & IST | "Here is a real ₹10 payment attempt (`pay_...`). Timestamps use IST: `24 Aug 2026, 05:20:44 PM IST`." | Shows live transaction stream with IST timezone formatting. |
| **Recovery Cases (`/cases`)** | Case Registry | "Let's open Case `#rec_...` to trace its AI diagnosis and safety evaluation." | Lists cases with risk level badges (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`). |
| **Case Detail Drawer** | AI Diagnosis | "Gemini AI diagnosed root cause: *Gateway timeout*, 88% confidence, recommending `RECOVERY_LINK`." | Drawer opens showing root cause, confidence %, and recommended action. |
| **Case Detail Drawer** | Policy Gate Card | "The Policy Gate verified confidence $\ge 0.70$, retries $\le 3$, cooldown active, and amount $\le \text{₹50k}$." | Displays **`POLICY APPROVED`** card; proves AI is bounded by safety rules. |
| **Case Detail Drawer** | Execution & Link | "PayPilot AI called Razorpay Payment Links API, generating link `plink_...` with live short URL `https://rzp.io/...`." | Renders real Razorpay Payment Link reference ID & payment URL. |
| **Case Detail Drawer** | Webhook & Status | "Razorpay sent a `payment_link.paid` webhook. HMAC signature passed, updating status to `RECOVERED`." | Shows status badge **`RECOVERED`** and confirmed recovered amount. |
| **Case Detail Drawer** | 7-Stage Audit | "Trace the full decision timeline from `DETECT` to `RECOVER` with complete explainability." | Displays 7-stage chronological timeline with IST timestamps. |
| **Benchmark (`/benchmark`)** | 1,000 Cases | "Our 1,000 synthetic case benchmark (Seed 42) achieved **83.69% Precision**, **86.13% Recall**, and **0 Unsafe Actions**." | Shows benchmark summary prominently labeled `"Synthetic Evaluation — No Real Money"`. |
| **Safety (`/safety`)** | Policy Rules | "AI recommends, but Policy controls. If retries $\ge 3$, Policy Gate instantly overrides AI to `STOP`." | Displays 6 active policy rule cards and block/override demonstrations. |
