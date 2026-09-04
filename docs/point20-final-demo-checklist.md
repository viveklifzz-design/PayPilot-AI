# PayPilot AI — Final Live Demo Setup Checklist

## Pre-Presentation Readiness Checklist

- [x] **Backend Running**: Uvicorn running on `http://127.0.0.1:8000`.
- [x] **Frontend Running**: Next.js production server running on `http://localhost:3000`.
- [x] **Razorpay Connection**: `Razorpay Test Mode — Connected` badge renders green.
- [x] **Backend Connection**: `Backend — Connected` badge renders green.
- [x] **Live Test Payment Evidence**: ₹10 test transaction (`pay_...`) available in stream.
- [x] **Recovered Case Evidence**: Recovered case (`#rec_...`) with Payment Link (`plink_...`) available.
- [x] **Webhook Audit Evidence**: Signed `payment_link.paid` event logged.
- [x] **7-Stage Audit Timeline**: Chronological trace with IST timestamps available in drawer.
- [x] **Synthetic Benchmark**: 1,000 cases (Seed 42) available on `/benchmark`.
- [x] **Zero Exposed Secrets**: No API keys or credentials visible on screen or in docs.
- [x] **Browser Viewport**: Browser zoom set to 100% at $1440 \times 900$ or $1366 \times 768$.
- [x] **Clean Tab Setup**: Single active tab open to `http://localhost:3000`.
- [x] **Primary Demo Rehearsed**: 13-step primary flow verified.
- [x] **Fallback Demo Rehearsed**: Contingency fallback rules verified.
- [x] **Pitch Timing Verified**: Timed presentation script completes in **4m 45s** ($\le 5$ minutes).
