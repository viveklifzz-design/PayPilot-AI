# PayPilot AI — 8-Slide Pitch Deck Specification

## Slide 1: Title & Overview
- **Title**: PayPilot AI — Autonomous Revenue Recovery Agent
- **Subtitle**: Razorpay AI Buildathon 2026 Presentation
- **Bullets**:
  - Autonomous 7-stage payment recovery loop
  - Google Gemini AI diagnosis + Razorpay Test Mode integration
  - Deterministic Policy Safety Gate (0 Unsafe Actions)
- **Visual**: PayPilot AI logo & executive dashboard screenshot
- **Time**: 0:00–0:30

---

## Slide 2: The Problem — Revenue at Risk
- **Title**: Billion-Dollar Revenue Leakage in Online Payments
- **Bullets**:
  - Payment failures cost merchants 15%–30% of gross revenue
  - Cryptic error codes lead to unguided, brute-force retries
  - Naive automation risks customer harassment & compliance violations
- **Visual**: Diagram showing payment failure dropoff rates
- **Time**: 0:30–0:50

---

## Slide 3: The Solution — Autonomous Recovery Loop
- **Title**: Detect $\rightarrow$ Diagnose $\rightarrow$ Gate $\rightarrow$ Recover
- **Bullets**:
  - Real-time Razorpay webhook failure detection
  - Gemini AI failure root cause diagnosis
  - Deterministic Policy Safety Gate validation
  - Automated Razorpay Payment Link execution & verification
- **Visual**: 7-stage recovery pipeline diagram
- **Time**: 0:50–1:15

---

## Slide 4: Real Razorpay Test Mode Live Demo
- **Title**: Live System Demonstration
- **Bullets**:
  - Live ₹10 Razorpay Test Mode transaction stream
  - AI Diagnosis (88% confidence) & recommended action
  - Real Razorpay Payment Link creation (`plink_...` / `https://rzp.io/...`)
  - Signed webhook ingestion (`payment_link.paid`) & IST audit timeline
- **Visual**: Live demo of `http://localhost:3000` & Case Detail Drawer
- **Time**: 1:15–3:00

---

## Slide 5: AI + Safety — Policy Gate Primacy
- **Title**: AI Recommends, Policy Controls
- **Bullets**:
  - Gemini AI is advisory; 0 direct money movement authority
  - Policy Safety Gate enforces 5 non-bypassable rules
  - Retries capped at $\le 3$; Cooldown $\ge 1\text{h}$; Auto-recovery cap $\le \text{₹50k}$
  - Instant override & block on safety violations
- **Visual**: Policy Safety Gate compliance card & override visualization
- **Time**: 3:00–3:45

---

## Slide 6: Batch Evaluation Benchmark
- **Title**: Proven Accuracy Across 1,000 Synthetic Cases
- **Bullets**:
  - **Precision**: 83.69% | **Recall**: 86.13% | **Recovery Rate**: 59.27%
  - **Unsafe Actions**: **0** (Zero compliance or safety violations)
  - Explicitly labeled: *"Synthetic Evaluation — No Real Money"*
- **Visual**: `/benchmark` page metric cards & charts
- **Time**: 3:45–4:20

---

## Slide 7: Enterprise Security & Resilience
- **Title**: Built for Production Reliability
- **Bullets**:
  - HMAC SHA256 webhook signature verification
  - Event idempotency tracking (`x-razorpay-event-id`)
  - Isolated AI Fallback engine & secret redaction
  - 96/96 Pytest backend tests & 16 resilience scenarios passed
- **Visual**: Security matrix & test suite execution report
- **Time**: 4:20–4:45

---

## Slide 8: Summary & Impact
- **Title**: Transforming Payment Recovery for Merchants
- **Bullets**:
  - Recovers lost revenue without customer friction
  - Guarantees 100% policy safety compliance
  - Full end-to-end decision explainability & audit trail
- **Visual**: Final call-to-action & GitHub repository QR code
- **Time**: 4:45–5:00
