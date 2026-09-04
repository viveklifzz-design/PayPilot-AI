# PayPilot AI — Primary Live Demonstration Flow

## Single Primary Demonstration Walkthrough

```text
FAILED PAYMENT ──► RECOVERY CASE ──► AI DIAGNOSIS ──► POLICY GATE ──► RECOVERY LINK
                                                                           │
RECOVERED ◄── AUDIT TRAIL ◄── WEBHOOK ◄── PAYMENT ◄── RAZORPAY TEST MODE ◄─┘
```

---

## Stage-by-Stage Script & Evidence Specifications

| Stage # | Stage Name | UI Location | Expected Status / Evidence | Presenter Exact Sentence |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **Failed Payment** | Overview (`/`) | Transaction `pay_...` (`status: failed`, Amount: ₹10) | "PayPilot AI automatically detects a failed payment attempt ingested via Razorpay." |
| **2** | **Recovery Case** | Cases (`/cases`) | Case `#rec_...` (`status: OPEN`, Risk: `MEDIUM`) | "The Revenue Risk Engine assesses transaction risk and initializes a tracked Recovery Case." |
| **3** | **AI Diagnosis** | Case Detail Drawer | `gemini-3.6-flash` output (Category, Root Cause) | "Gemini AI diagnoses the failure root cause as gateway timeout with 88% confidence." |
| **4** | **AI Decision** | Case Detail Drawer | `ai_recommended_action: RECOVERY_LINK` | "The AI recommends dispatching an automated Razorpay Payment Link." |
| **5** | **Policy Gate** | Case Detail Drawer | Card **`POLICY APPROVED`** | "The Policy Safety Gate independently evaluates the recommendation against 5 safety rules." |
| **6** | **Recovery Link** | Case Detail Drawer | `plink_...` & `https://rzp.io/...` | "Upon policy approval, PayPilot AI calls Razorpay's API to generate a real Payment Link." |
| **7** | **Razorpay Test Mode** | Razorpay Gateway | Test payment interface | "The customer opens the Razorpay Payment Link and completes the ₹10 test payment." |
| **8** | **Payment Webhook** | Backend Logs | `payment_link.paid` event (HMAC verified) | "Razorpay dispatches a signed webhook event which our backend verifies via HMAC SHA256." |
| **9** | **Recovered State** | Case Detail Drawer | Case Status **`RECOVERED`** | "PayPilot AI confirms payment receipt, updates case status to RECOVERED, and adds ₹10 to revenue." |
| **10** | **Audit Trail** | Case Detail Drawer | 7-Stage Chronological Timeline | "The entire decision sequence is recorded in an immutable 7-stage audit timeline with IST timestamps." |
