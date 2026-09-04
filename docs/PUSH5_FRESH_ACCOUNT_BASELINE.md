# PAYPILOT AI — PUSH #5 FRESH ACCOUNT BASELINE & AUDIT REPORT

## 1. Executive Summary & Environment Baseline

This document records the baseline environment audit prior to executing **Push #5** for **PayPilot AI** on **Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery**.

### **ENVIRONMENT BACKUP VERIFICATION**:
- `.env` backed up to `.env.bak_push4`.
- `paypilot_dev.db` backed up to `paypilot_dev.db.bak_push4`.

---

## 2. Historical Razorpay Test Account Baseline

- **Key ID Prefix**: `rzp_test_TTDQ...`
- **Environment**: `TEST` Mode
- **Payment Link Quota Status**: `30 / 30` (Lifetime account limit reached on historical account)
- **Total Provider Payments Audited**: 9 payments
- **Real Failed Payment**: `pay_TTXlSqxyg5hAiT` ($\text{INR 10.00}$, `failed`, `BAD_REQUEST_ERROR`, `international_transaction_not_allowed`)
- **Real Captured Payment**: `pay_TTa6BvTMgDHtc8` ($\text{INR 10.00}$, `captured`, `order_TTa635I4vZt4cV`)

---

## 3. Data Boundary Rules

1. Live merchant dashboard calculates metrics strictly from provider-backed/verified database state.
2. Zero synthetic benchmark figures enter merchant Overview metrics.
3. Zero manual/fabricated `RECOVERED` states or fake payment IDs are introduced.
