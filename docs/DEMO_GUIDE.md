# PayPilot AI — Judge Demo Guide (3-Minute Walkthrough)
**Razorpay AI Buildathon Track 03: AI Revenue Recovery**

---

## Quick Start
1. Ensure backend (`http://localhost:8000`) and frontend (`http://localhost:3000`) are running.
2. Open `http://localhost:3000` in Google Chrome or Microsoft Edge.

---

## Step-by-Step Walkthrough

### 1. Executive Dashboard (`/`)
- **What to observe**: Live revenue metrics showing `Revenue at Risk`, `Recovered Revenue` (**INR 80.00**), and `Recovery Rate`.
- **Key point**: Zero synthetic data presented as live recovery.

### 2. Payment Failure Recovery Flow (`/cases` & `/recover/d669dce3-b855-4348-b457-f0ef7c34b6b1`)
- **What to observe**: View recovery case `d669dce3-b855-4348-b457-f0ef7c34b6b1`. Observe AI diagnosis (`WHAT HAPPENED?`, `WHY DID THIS HAPPEN?`), Policy Gate approval badge, and **Razorpay Standard Checkout** button.
- **Provider Evidence**: Verified captured Razorpay payment `pay_TU3EQsT63DFVuX` (INR 10.00).

### 3. Mandate Retry Sequencer (`/mandates`)
- **What to observe**: Mandate queue showing retry progress, failure reasons, Policy Gate decision badges, and **Attempt History Modal**.
- **Lineage Note**: Operating in simulation mode (`DATABASE DERIVED / SIMULATION`).

### 4. Subscription Grace & Dunning (`/subscriptions`)
- **What to observe**: Active subscriptions, dunning retry count, and grace period countdowns before cancellation.

### 5. B2B Receivables & Promise-to-Pay (`/receivables` & `/cases`)
- **What to observe**: Overdue corporate invoices and promise-to-pay commitment tracker.

### 6. Safety Controls & Circuit Breakers (`/safety`)
- **What to observe**: Autonomous rate limiters, circuit breakers, and manual override controls.

### 7. Immutable Audit Trail (`/audit`)
- **What to observe**: Complete chronological event log recording AI decisions, webhook payloads, and signature verification logs.
