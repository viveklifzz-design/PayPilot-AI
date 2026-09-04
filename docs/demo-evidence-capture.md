# PayPilot AI — Visual Evidence Capture Plan

## 1. Overview
This plan specifies the 12 key visual assets (screenshots / recordings) to capture from the live running PayPilot AI application for submission packages and judge evaluation.

---

## 2. Capture Checklist Matrix

| Asset # | Target UI View | Captured Element | Purpose |
| :---: | :--- | :--- | :--- |
| **1** | Overview Dashboard | Entire `http://localhost:3000` header & KPI grid | Proves working Next.js dashboard UI |
| **2** | Razorpay Status Badge | **`Razorpay Test Mode — Connected`** badge | Proves live Razorpay Test Mode connection |
| **3** | Backend Status Badge | **`Backend — Connected`** badge | Proves live FastAPI backend connectivity |
| **4** | Financial KPI Cards | **Revenue at Risk** & **Recovered Revenue** cards | Displays revenue recovery metrics |
| **5** | Recent Transactions | Transaction table with IST timestamps (`DD Mon YYYY, hh:mm:ss AM/PM IST`) | Proves IST timezone formatting & live payment ingestion stream |
| **6** | Cases Explorer | `/cases` page with risk level filter buttons | Demonstrates case filtering capabilities |
| **7** | Case Detail Drawer | AI Diagnosis section (`gemini-3.6-flash`, Root Cause, Confidence %) | Demonstrates structured AI diagnosis output |
| **8** | Policy Gate Card | **`POLICY APPROVED`** compliance card | Proves Policy Engine safety gate authority |
| **9** | Razorpay Execution | Payment Link ID (`plink_...`) & short URL (`https://rzp.io/...`) | Proves real Razorpay Payment Links API integration |
| **10** | 7-Stage Audit Timeline | 7 chronological stages (`DETECT` $\rightarrow$ `RECOVER`) | Demonstrates end-to-end decision explainability |
| **11** | Benchmark Page | `/benchmark` page with 1,000 synthetic cases (Seed 42, **Unsafe Actions = 0**) | Proves deterministic batch evaluation capability |
| **12** | Data Notice | Label `"Synthetic Evaluation — No Real Money"` | Proves strict isolation of synthetic evaluation data |
