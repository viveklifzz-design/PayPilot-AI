# PayPilot AI — Primary Live Demo Rehearsal Specification

## 1. 13-Step Demonstration Walkthrough

1. **Dashboard Overview**: Open `http://localhost:3000`. Confirm `Razorpay Test Mode — Connected` & `Backend — Connected` badges.
2. **Financial KPIs**: Inspect **Revenue at Risk** (failed payment total) and **Recovered Revenue**.
3. **Recent Transactions**: Scroll down to live transaction stream. Locate real ₹10 payment attempt (`pay_...`).
4. **Timezone Audit**: Verify IST timestamp format (`24 Aug 2026, 05:20:44 PM IST`).
5. **Cases Explorer**: Navigate to `/cases`. Click case `#rec_...` to open `CaseDetailDrawer`.
6. **Failure Context**: Inspect failed transaction details (Amount: ₹10, Method: UPI, Status: `OPEN`).
7. **AI Diagnosis**: View Gemini AI (`gemini-3.6-flash`) root cause analysis (*Gateway timeout*) and confidence score ($88\%$).
8. **AI Recommendation**: View proposed recovery action (`RECOVERY_LINK`).
9. **Policy Safety Gate**: Inspect **`POLICY APPROVED`** card verifying confidence ($\ge 0.70$), retries ($\le 3$), cooldown ($\ge 1\text{h}$), and amount cap ($\le \text{₹50k}$).
10. **Razorpay Payment Link Execution**: Inspect Razorpay payment link ID (`plink_...`) and short URL (`https://rzp.io/...`).
11. **Test Payment Execution**: Complete ₹10 test payment on Razorpay Test Gateway interface.
12. **Webhook & Case Recovery**: Ingest `payment_link.paid` webhook. Observe status transition to **`RECOVERED`** and confirmed recovered amount.
13. **7-Stage Audit Timeline**: Inspect full chronological decision timeline (`DETECT` $\rightarrow$ `DIAGNOSE` $\rightarrow$ `DECIDE` $\rightarrow$ `POLICY` $\rightarrow$ `EXECUTE` $\rightarrow$ `VERIFY` $\rightarrow$ `RECOVER`).
