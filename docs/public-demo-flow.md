# PayPilot AI — Public Judge Demonstration Flow (< 5 Minutes)

## Overview
This document outlines the concise 5-minute judge demonstration flow for evaluating PayPilot AI in a public demo environment.

---

## 5-Minute Live Demonstration Sequence

| Step # | UI Location | Action / Demonstration | Key Talking Point |
| :---: | :--- | :--- | :--- |
| **1** | Top Header | Observe **`Razorpay Test Mode — Connected`** badge | Proves live integration with Razorpay Test APIs & Webhooks. |
| **2** | Top Header | Observe **`Backend — Connected`** badge | Proves real-time FastAPI backend connectivity. |
| **3** | Overview Dashboard | Inspect **Revenue at Risk** KPI card | Highlights total value of failed payment attempts requiring recovery. |
| **4** | Overview Dashboard | Inspect **Recovered Revenue** KPI card | Highlights actual revenue brought back into merchant accounts. |
| **5** | Overview Dashboard | Scroll to **Recent Razorpay Transactions** | Displays real-time payment ingestion stream. |
| **6** | Overview Dashboard | Locate real ₹10 payment attempt (`pay_...`) | Proves real Razorpay Test Mode event processing. |
| **7** | Overview Dashboard | Observe IST timestamp format (`DD Mon YYYY, hh:mm:ss AM/PM IST`) | Unambiguous Indian Standard Time presentation. |
| **8** | Recovery Cases (`/cases`) | Click a case to open `CaseDetailDrawer` | Opens the complete end-to-end decision trace drawer. |
| **9** | Case Detail Drawer | Inspect **AI Diagnosis (gemini-3.6-flash)** | AI identifies root cause and confidence score ($88\%$). |
| **10** | Case Detail Drawer | Inspect **AI Recommended Action** | AI proposes optimal recovery intervention (`RECOVERY_LINK`). |
| **11** | Case Detail Drawer | Inspect **Policy Safety Gate** card | **`POLICY APPROVED`** — AI is bounded by 5 safety rules. |
| **12** | Case Detail Drawer | Inspect **Razorpay Execution** card | Displays real payment link reference (`plink_...`) & short URL. |
| **13** | Case Detail Drawer | Inspect **Webhook Confirmation** trace | Confirms `payment_link.paid` webhook ingestion. |
| **14** | Case Detail Drawer | Observe Case Status: **`RECOVERED`** | Confirms state transition and recovered amount. |
| **15** | Case Detail Drawer | Scroll 7-Stage Chronological Decision Timeline | Traces `DETECT` $\rightarrow$ `DIAGNOSE` $\rightarrow$ `DECIDE` $\rightarrow$ `POLICY` $\rightarrow$ `EXECUTE` $\rightarrow$ `VERIFY` $\rightarrow$ `RECOVER`. |
| **16** | Benchmark Page (`/benchmark`)| Navigate to **Synthetic Evaluation Benchmark** | Evaluates system performance across 1,000 synthetic cases (Seed 42). |
| **17** | Benchmark Page | Point out label: `"Synthetic Evaluation — No Real Money"` | Explicitly distinguishes real test payments from synthetic evaluation. |
| **18** | Benchmark Page | Inspect **Precision (83.69%)** & **Recall (86.13%)** | High accuracy in identifying recoverable vs. non-recoverable failures. |
| **19** | Benchmark Page | Inspect **Unsafe Actions: 0** | Zero compliance violations or unauthorized money actions executed. |
| **20** | Safety Page (`/safety`) | Review Safety Policy Engine rules | Explains automatic stopping, retry caps ($\le 3$), and cooldown windows. |
