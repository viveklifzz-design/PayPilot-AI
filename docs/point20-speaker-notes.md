# PayPilot AI — Screen-by-Screen Speaker Notes

## Screen 1: Dashboard Overview (`/`)
- **SHOW**: Executive dashboard grid, connection badges (`Razorpay Test Mode — Connected`), **Revenue at Risk**, and **Recovered Revenue** cards.
- **SAY**: "PayPilot AI continuously monitors payment health and tracks total revenue at risk versus revenue recovered."
- **WHY IT MATTERS**: Establishes live integration with Razorpay Test Mode and clear financial tracking.
- **EXPECTED RESULT**: Badges display green `Connected` status; KPI metrics load dynamically.
- **FALLBACK**: If loading takes time, point out the live status badge showing active backend connection.

---

## Screen 2: Recent Razorpay Transactions (`/`)
- **SHOW**: Live transaction stream with IST timestamp column (`24 Aug 2026, 05:20:44 PM IST`).
- **SAY**: "Here is our live transaction stream. Notice that all timestamps are rendered in unambiguous Indian Standard Time."
- **WHY IT MATTERS**: Demonstrates real-time payment ingestion and local timezone compliance.
- **EXPECTED RESULT**: Displays ₹10 test payments with `captured` or `failed` status.
- **FALLBACK**: If stream is empty, point out the refresh button which re-queries the backend API.

---

## Screen 3: Recovery Cases Explorer (`/cases`)
- **SHOW**: Recovery Cases table with risk level badges (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and filter toolbar.
- **SAY**: "In the Recovery Cases Explorer, PayPilot AI categorizes every payment failure by risk severity and priority."
- **WHY IT MATTERS**: Shows structured case management and risk prioritization.
- **EXPECTED RESULT**: Renders active cases list; clicking a row opens the Case Detail Drawer.
- **FALLBACK**: Use filter buttons to highlight specific risk levels.

---

## Screen 4: Case Detail Trace Drawer (Drawer Component)
- **SHOW**: AI Diagnosis card (`gemini-3.6-flash`), **`POLICY APPROVED`** card, Razorpay Payment Link ID (`plink_...`), and 7-Stage Chronological Timeline.
- **SAY**: "Inside the Case Trace Drawer, Gemini AI diagnoses the root cause. Crucially, the Policy Safety Gate independently verifies all safety rules before calling Razorpay APIs. Upon payment, signed webhooks confirm recovery and append to our 7-stage audit timeline."
- **WHY IT MATTERS**: Proves deterministic safety gate primacy, real Razorpay execution, and full decision explainability.
- **EXPECTED RESULT**: Renders 7 chronological stages (`DETECT` $\rightarrow$ `RECOVER`) with IST timestamps.
- **FALLBACK**: If inspecting a stopped case, point out the policy block card explaining why retries were halted.

---

## Screen 5: Synthetic Evaluation Benchmark (`/benchmark`)
- **SHOW**: Batch evaluation metrics (Precision 83.69%, Recall 86.13%, Unsafe Actions 0) and the label `"Synthetic Evaluation — No Real Money"`.
- **SAY**: "On our 1,000 synthetic case benchmark (Seed 42), PayPilot AI achieved **83.69% Precision**, **86.13% Recall**, and **0 Unsafe Actions**. Note that synthetic benchmark evaluation is strictly separated from live Razorpay Test Mode data."
- **WHY IT MATTERS**: Demonstrates quantitative system accuracy at scale with 100% data source transparency.
- **EXPECTED RESULT**: Displays metric summary cards and synthetic case table.
- **FALLBACK**: Point out the CSV export button allowing judges to download the complete synthetic run dataset.
