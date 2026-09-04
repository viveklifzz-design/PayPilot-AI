# PayPilot AI — Judge Demonstration Script & Walkthrough Checklist

## Overview
This step-by-step checklist guides a live judge or evaluator through the complete PayPilot AI demonstration for the Razorpay AI Buildathon.

---

## Live Walkthrough Checklist

- [ ] **Step 1: Open Dashboard**
  - Navigate to `http://localhost:3000` in the browser.
  - Confirm page renders with complete Tailwind CSS styling.

- [ ] **Step 2: Verify Razorpay Connection**
  - Highlight the top navigation header badge: **`Razorpay Test Mode — Connected`** (Green indicator).

- [ ] **Step 3: Verify Backend Connection**
  - Highlight the backend status badge: **`Backend — Connected`** (Port 8000 status).

- [ ] **Step 4: Review Revenue at Risk KPI**
  - Point to the **Revenue at Risk** KPI card (Total value of failed payment attempts).

- [ ] **Step 5: Review Recovered Revenue KPI**
  - Point to the **Recovered Revenue** KPI card and current Recovery Rate percentage.

- [ ] **Step 6: Inspect Recent Razorpay Transactions Table**
  - Scroll to **Recent Razorpay Transactions**.
  - Show live payment ingestion stream.

- [ ] **Step 7: Verify Real ₹10 Razorpay Test Transaction**
  - Locate the real ₹10 payment attempt (`pay_...`).
  - Confirm timestamp is formatted in IST (`DD Mon YYYY, hh:mm:ss AM/PM IST`).

- [ ] **Step 8: Open Recovery Case Trace Drawer**
  - Click on a Recovery Case to open the `CaseDetailDrawer`.

- [ ] **Step 9: Inspect AI Failure Diagnosis**
  - Point out AI Diagnosis section (Root Cause, Failure Category, Confidence %).

- [ ] **Step 10: Inspect AI Recommended Action**
  - Point out recommended action (`RECOVERY_LINK`).

- [ ] **Step 11: Inspect Policy Safety Gate Compliance**
  - Point out Policy Safety Gate card: **`POLICY APPROVED`**.
  - Highlight that Policy Engine strictly enforces confidence thresholds, retry limits ($\le 3$), cooldown windows, and amount limits ($\le \text{₹50,000}$).

- [ ] **Step 12: Inspect Razorpay Payment Link Creation**
  - Show Razorpay Payment Link reference (`plink_...`) and short URL (`https://rzp.io/rzp/...`) generated via live Razorpay API.

- [ ] **Step 13: Inspect Webhook Confirmation Trace**
  - Point out `payment_link.paid` webhook event ingestion.

- [ ] **Step 14: Verify Final Recovery State**
  - Confirm Case status transition to **`RECOVERED`** and recovered amount updated to ₹10.00.

- [ ] **Step 15: Inspect 7-Stage Chronological Audit Timeline**
  - Scroll through the 7-Stage Decision Timeline:
    1. `DETECT` $\rightarrow$ 2. `DIAGNOSE` $\rightarrow$ 3. `DECIDE` $\rightarrow$ 4. `POLICY` $\rightarrow$ 5. `EXECUTE` $\rightarrow$ 6. `VERIFY` $\rightarrow$ 7. `RECOVER`
  - Highlight IST timestamps and structured decision explainability checklist.

- [ ] **Step 16: Open Benchmark Evaluation Page**
  - Click **Synthetic Evaluation Benchmark** in navigation bar (`/benchmark`).

- [ ] **Step 17: Inspect 1,000 Synthetic Case Batch Evaluation**
  - Show batch evaluation run on 1,000 synthetic payment failure cases (Seed 42).
  - Explicitly point out label: `"Synthetic Evaluation — No Real Money"`.

- [ ] **Step 18: Review Benchmark Performance Metrics**
  - Show Precision (**83.69%**), Recall (**86.13%**), and F1 Score (**84.89%**).

- [ ] **Step 19: Verify Safety Metric**
  - Highlight **Unsafe Actions: 0** (Zero policy violations or unearned money actions executed).

- [ ] **Step 20: Explain Safe Stopping & Failure Handling**
  - Open Safety Policy page (`/safety`).
  - Explain how PayPilot handles gateway failures, low AI confidence, and policy blocks deterministically.
