# PAYPILOT AI — FINAL UI, DATA LINEAGE & REALITY AUDIT REPORT

## 1. Executive Summary & Page Lineage Audit

This report presents an empirical audit of all merchant-facing and customer-facing routes in **PayPilot AI** for **Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery**.

Data Classification Standard:
- **REAL RAZORPAY TEST MODE**: Live Razorpay API provider evidence (`rzp_test_...`, `plink_...`, HMAC SHA256 Webhooks).
- **LOCAL TEST SIMULATION**: Validated locally through SQLite database state transitions and service classes.
- **SYNTHETIC EVALUATION — NO REAL MONEY**: 1,000 synthetic benchmark test cases (Seed 42), strictly isolated under `/benchmark`.

---

## 2. Comprehensive Merchant & Customer Route Audit Table

| Page Route | Purpose | HTTP Status | Dynamic Data Lineage | Hardcoded Revenue? | Data Classification Badge | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`/`** | Overview Dashboard | **HTTP 200** | `GET /api/v1/analytics/metrics` | **NO** | LIVE MERCHANT STREAM | **REAL PROVIDER VERIFIED** |
| **`/transactions`** | Live Transactions Registry | **HTTP 200** | `GET /api/v1/transactions` | **NO** | `REAL RAZORPAY TEST MODE` | **REAL PROVIDER VERIFIED** |
| **`/cases`** | Recovery Cases Console | **HTTP 200** | `GET /api/v1/cases` | **NO** | LIVE RECOVERY STREAM | **REAL PROVIDER VERIFIED** |
| **`/revenue-risk`** | Unified Risk Intelligence | **HTTP 200** | `GET /api/v1/revenue-risk/summary` | **NO** | CANONICAL RISK ENGINE | **REAL VERIFIED** |
| **`/receivables`** | B2B Receivables Chaser | **HTTP 200** | `GET /api/v1/receivables` | **NO** | `LOCAL TEST SIMULATION` | **LOCAL TEST VERIFIED** |
| **`/subscriptions`** | Failed Subscription Recovery | **HTTP 200** | `GET /api/v1/cases?type=SUBSCRIPTION_FAILURE` | **NO** | `LOCAL TEST SIMULATION` | **LOCAL TEST VERIFIED** |
| **`/mandates`** | Mandate Retry Sequencer | **HTTP 200** | `GET /api/v1/mandates` | **NO** | `LOCAL TEST SIMULATION` | **LOCAL TEST VERIFIED** |
| **`/communications`** | Hinglish Communication Layer | **HTTP 200** | `POST /api/v1/communication/generate` | **NO** | `LOCAL TEST SIMULATION` | **LOCAL TEST VERIFIED** |
| **`/customers`** | Customers Directory | **HTTP 200** | Customer Directory View | **NO** | PORTAL DIRECTORY | **REAL VERIFIED** |
| **`/customer`** | Customer Recovery Portal | **HTTP 200** | `POST /api/v1/customer/login` / `transactions/{id}` | **NO** | CUSTOMER PORTAL | **REAL VERIFIED** |
| **`/audit`** | Real-Time Audit Trail Logs | **HTTP 200** | `GET /api/v1/audit` | **NO** | AUDIT STREAM | **REAL VERIFIED** |
| **`/safety`** | Policy & Safety Console | **HTTP 200** | `GET /api/v1/cases` (Policy Status) | **NO** | POLICY ENGINE | **REAL VERIFIED** |
| **`/benchmark`** | Synthetic Batch Benchmark | **HTTP 200** | `GET /api/v1/evaluation/summary` | **NO** | `SYNTHETIC EVALUATION — NO REAL MONEY` | **SYNTHETIC ONLY** |

---

## 3. Data Lineage Verification Findings

1. **Zero Hardcoded Merchant Revenue**:
   - The main merchant dashboard (`/`) loads metrics dynamically from `http://127.0.0.1:8000/api/v1/analytics/metrics`.
   - Zero hardcoded rupee amounts exist in frontend rendering code.

2. **Synthetic Benchmark Isolation**:
   - The synthetic evaluation benchmark (Seed 42, 1,000 cases) is 100% isolated under `/benchmark`.
   - Explicitly displays the warning badge: `"SYNTHETIC EVALUATION — NO REAL MONEY"`.

3. **Drill-down & Fact Integrity**:
   - Every transaction displays authoritative Razorpay facts (`error_code`, `error_source`, `error_step`, `error_reason`, `error_description`).
   - Every recovery case connects to a 7-stage chronological audit timeline with IST timestamps.

---

## 4. Final Verdict

### **PAYPILOT AI UI & ROUTE AUDIT: 100% PASS (13 / 13 ROUTES HTTP 200 OK)**
