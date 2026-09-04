# PAYPILOT AI — FINAL LIVE DATA LINEAGE & PROVIDER AUDIT REPORT

## 1. Executive Summary & Audit Declaration

This report presents an empirical audit of the real Razorpay Test Mode transaction `pay_TTa6BvTMgDHtc8` and its end-to-end data lineage across:
`RAZORPAY PROVIDER API → LOCAL DATABASE → REST API → FRONTEND & CUSTOMER PORTAL`

### **AUDIT VERDICT: 100% PASS — PROVIDER VERIFIED**

---

## 2. Real Razorpay Test Mode Payment Lineage Audit

| Audit Layer | Object / Entity ID | Key Fields | Value / State | Lineage Status |
| :--- | :--- | :--- | :--- | :---: |
| **1. Live Razorpay API Server** | `pay_TTa6BvTMgDHtc8` | Amount (paise)<br>Status<br>Order ID<br>Method<br>Customer Email | 1000 ($\text{INR 10.00}$)<br>`captured`<br>`order_TTa635I4vZt4cV`<br>`netbanking` (`BARB_R`)<br>`void@razorpay.com` | **PROVIDER VERIFIED** |
| **2. Local SQLite Database** | Transaction `bda629a4` | `razorpay_payment_id`<br>Amount<br>Status<br>Customer ID | `pay_TTa6BvTMgDHtc8`<br>$\text{INR 10.00}$<br>`captured`<br>`5f4f2050-9cba-4ee6-bada-19d7433ffcf6` | **EXACT MATCH** |
| **3. Backend REST API** | `GET /api/v1/transactions` | `razorpay_payment_id`<br>Amount<br>Status | `pay_TTa6BvTMgDHtc8`<br>$\text{INR 10.00}$<br>`captured` | **EXACT MATCH** |
| **4. Customer Portal Login** | `POST /api/v1/customer/login` | Email<br>Customer ID | `void@razorpay.com`<br>`5f4f2050-9cba-4ee6-bada-19d7433ffcf6` | **HTTP 200 OK** |
| **5. Customer Transaction Lookup** | `GET /api/v1/customer/transactions/pay_TTa6BvTMgDHtc8` | Lookup Key<br>Amount<br>Status | `pay_TTa6BvTMgDHtc8`<br>$\text{INR 10.00}$<br>`captured` | **HTTP 200 OK** |
| **6. Ownership Security Check** | Customer B $\rightarrow$ Customer A Txn | Header `x-customer-id`<br>Response | `cust_b_unauthorized`<br>**HTTP 403 Forbidden** | **SECURITY INTACT** |

---

## 3. Audit Answers to Specific Directive Questions

1. **Was `ingest_real_ten_rupee_payment.py` auditing completed?**
   - YES. The initial draft contained static hardcoded dictionaries. It has been updated to query `https://api.razorpay.com/v1/payments/pay_TTa6BvTMgDHtc8` directly using live `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` credentials.

2. **Is `pay_TTa6BvTMgDHtc8` provider-verified?**
   - YES. `GET https://api.razorpay.com/v1/payments/pay_TTa6BvTMgDHtc8` returned **HTTP 200 OK** directly from Razorpay Test Mode servers.

3. **Does the Razorpay amount match the database amount?**
   - YES. Razorpay amount = 1000 paise ($\text{INR 10.00}$), DB amount = $\text{INR 10.00}$. Exact match (INR 0.00 discrepancy).

4. **Does the Customer Portal login work without HTTP 404?**
   - YES. `POST /api/v1/customer/login` and `GET /api/v1/customer/transactions/{id}` return **HTTP 200 OK**.

5. **Is Customer Ownership Security enforced?**
   - YES. Customer B attempting to query Customer A's transaction returns **HTTP 403 Forbidden** (`"Access Denied: You do not have permission to view another customer's transaction."`).

---

## 4. Final Classification Summary

```text
=================================================================
    PAYPILOT AI -- LIVE DATA LINEAGE AUDIT VERDICT               
=================================================================
REAL PROVIDER VERIFIED : pay_TTa6BvTMgDHtc8 (INR 10.00, captured, order_TTa635I4vZt4cV)
LOCAL TEST VERIFIED    : B2B Receivables, Mandates, Subscriptions
SYNTHETIC ONLY         : Benchmark Dataset (1,000 cases under /benchmark)
Customer Security      : HTTP 403 Forbidden ENFORCED
Final Lineage Status   : 100% VERIFIED & SUBMISSION READY
=================================================================
```
