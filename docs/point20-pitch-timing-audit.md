# PayPilot AI — 5-Minute Pitch Timing Audit

## 1. Presentation Timing Breakdown

| Segment | Target Time | Estimated Time | Key Presenter Objective | Evidence Shown |
| :--- | :---: | :---: | :--- | :--- |
| **1. Problem** | 0:00–0:30 (30s) | 30s | Explain revenue at risk from failed payments & danger of naive retries | Industry failure metrics |
| **2. Solution** | 0:30–1:00 (30s) | 30s | Introduce PayPilot AI & the 7-stage autonomous recovery loop | Architecture diagram |
| **3. Live Demo** | 1:00–3:00 (120s) | 115s | Demonstrate real Razorpay Test Mode transaction, AI diagnosis, Policy Gate, & webhook trace | `http://localhost:3000` & `CaseDetailDrawer` |
| **4. AI + Safety** | 3:00–4:00 (60s) | 55s | Explain AI advisory boundary vs. Policy Gate rules ($\ge 0.70$ conf, $\le 3$ retries, $\le \text{₹50k}$) | Policy Safety Gate card |
| **5. Evaluation** | 4:00–4:30 (30s) | 30s | Present 1,000 synthetic case benchmark metrics (Precision 83.69%, Recall 86.13%, Unsafe Actions = 0) | `/benchmark` page |
| **6. Closing** | 4:30–5:00 (30s) | 25s | Summarize autonomous loop, 96/96 backend tests passed, and impact | Final slide & QR code |

**TOTAL ESTIMATED TIME**: **4 Minutes 45 Seconds (285s)** — *Fits within the 5-minute presentation limit.*
