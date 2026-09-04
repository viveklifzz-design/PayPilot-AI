# PayPilot AI — Master Verified Metrics Reference

## Important Separation Notice
> **CRITICAL RULE**: Real Razorpay Test Mode transaction evidence MUST NOT be mixed or confused with Synthetic Evaluation Benchmark data.

---

## SECTION 1: REAL RAZORPAY TEST MODE METRICS (VERIFIED LIVE)

- **Razorpay Integration Mode**: Test Mode (`rzp_test_...`)
- **Razorpay Gateway Connection Status**: `Connected`
- **Backend API Connectivity**: `Connected` (Port 8000)
- **Live Transaction Ingestion**: Verified (₹10 test transactions)
- **HMAC Signature Check**: `PASS` (HTTP 401 on invalid signature)
- **Payment Link Generation**: Verified (`plink_...` / `https://rzp.io/...`)
- **Webhook Recovery Confirmation**: Verified (`payment_link.paid` $\rightarrow$ `RECOVERED`)
- **Audit Stage Trace**: 7 chronological stages (`DETECT` to `RECOVER`)
- **IST Timezone Compliance**: 100% (`Asia/Kolkata`)

---

## SECTION 2: SYNTHETIC EVALUATION BENCHMARK METRICS (VERIFIED SEED 42)

- **Notice**: **Synthetic Evaluation — No Real Money**
- **Dataset Size**: 1,000 synthetic failure cases
- **Random Seed**: `42` (100% deterministic reproducibility)
- **Precision**: **83.69%**
- **Recall**: **86.13%**
- **Recovery Rate**: **59.27%**
- **Intervention Rate**: **70.50%**
- **Safe Stop Rate**: **25.86%**
- **Escalation Rate**: **17.90%**
- **Unsafe Action Count**: **0**
- **Revenue at Risk**: INR 19,092,323.00
- **Recoverable Revenue**: INR 8,567,489.00
- **Revenue Recovered**: INR 5,080,707.00

---

## SECTION 3: SYSTEM TEST SUITE METRICS

- **Backend Pytest Suite**: **96 / 96 PASSED** (0 failures, 0 warnings)
- **Resilience Scenarios**: **16 / 16 PASSED**
- **Public Demo E2E Suite**: **10 / 10 CHECKS PASSED**
- **Frontend Production Build**: **✓ Compiled successfully** (0 errors)
- **Secret Leaks**: **0 exposed**
