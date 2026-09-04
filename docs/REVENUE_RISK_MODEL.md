# PayPilot AI — Revenue-at-Risk Engine & Scoring Model

**Track 03 — AI Revenue Recovery | Razorpay AI Buildathon**

---

## 1. Terminology & Core Financial Definitions

PayPilot AI enforces clear distinction between different revenue states to avoid misleading financial claims:

| Term | Definition | Formula / Representation |
| :--- | :--- | :--- |
| **Gross Failed Amount** | Sum of all payment transaction amounts that resulted in `failed` status. | $\sum \text{failed\_amount}$ |
| **Revenue at Risk** | The financial exposure of a failed transaction, weighted by customer value and recoverability. | $\text{Transaction Amount} \times \text{Risk Multiplier}$ |
| **Estimated Recoverable Revenue** | Potential revenue expected to be recovered based on estimated recoverability score. | $\text{Amount} \times \text{Recoverability Score}$ |
| **Recovered Revenue** | Actual cash recovered from verified successful payments following intervention. | Realized database sum of paid recovery links / retries. |

---

## 2. Input Features Matrix

| Feature | Data Source | Type | Impact on Recoverability & Risk |
| :--- | :--- | :--- | :--- |
| `amount` | `Transaction.amount` | Float | Higher amount increases Priority and Financial Exposure. |
| `error_code` | `Transaction.error_code` | String | Bank outage / timeout = high recoverability; Expired card / Fraud = low recoverability. |
| `total_successful_payments` | `Customer.total_successful_payments` | Integer | Historical success indicates high customer intent & recoverability. |
| `total_failed_payments` | `Customer.total_failed_payments` | Integer | High past failure count indicates chronic payment issues / low intent. |
| `payment_method` | `Transaction.payment_method` | String | UPI / Netbanking has higher instant retry recoverability than Card 3DS timeouts. |
| `retry_count` | `RecoveryCase.retry_count` | Integer | More retries decrease recoverability and increase exhaustion risk. |

---

## 3. Risk Scoring & Recoverability Methodology

The Revenue Risk Engine produces two primary scores ($0.0$ to $100.0$ or $0.0$ to $1.0$):

### 3.1 Recoverability Score Calculation ($R \in [0.0, 1.0]$)

$$\text{Recoverability} = \text{BaseScore}(error\_code) + \text{CustomerHistoryBonus} - \text{RetryPenalty}$$

1. **Base Error Code Recoverability:**
   - Temporary bank/network outage (`BAD_REQUEST_PAYMENT_TIMED_OUT`, `GATEWAY_ERROR`): `0.85`
   - Authentication failure / user dropoff (`BAD_REQUEST_PAYMENT_CANCELLED`, `OTP_TIMEOUT`): `0.70`
   - Insufficient funds (`BAD_REQUEST_PAYMENT_DECLINED`): `0.50`
   - Permanent failure (`EXPIRED_CARD`, `INVALID_CARD_DETAILS`): `0.20`
   - Suspected Fraud / Blacklisted (`SUSPECTED_FRAUD`, `RISK_CHECK_FAILED`): `0.05`
   - Unknown failure code: `0.50`

2. **Customer History Adjustment:**
   - If `total_successful_payments >= 5`: `+0.15`
   - If `total_successful_payments >= 1`: `+0.08`
   - If `total_failed_payments > 3`: `-0.15`

3. **Retry Exhaustion Penalty:**
   - `retry_count == 1`: `-0.10`
   - `retry_count == 2`: `-0.25`
   - `retry_count >= 3`: `-0.50`

Bounded strictly between `0.00` and `1.00`.

### 3.2 Risk Score Calculation ($\text{RiskScore} \in [0.0, 100.0]$)

$$\text{RiskScore} = (1.0 - R) \times 70 + \text{AmountExposureScore} \times 30$$

where $\text{AmountExposureScore} = \min(1.0, \frac{\text{amount}}{100000.0})$.

---

## 4. Deterministic Risk Tiers

| Risk Level | Risk Score Range | Description & Operational Action |
| :--- | :--- | :--- |
| **LOW** | $0.00 - 24.99$ | High recoverability, low exposure. Ideal for automated retry/link. |
| **MEDIUM** | $25.00 - 49.99$ | Moderate recoverability. Normal recovery flow. |
| **HIGH** | $50.00 - 74.99$ | High risk of permanent churn. Requires tailored intervention. |
| **CRITICAL** | $75.00 - 100.00$ | Very low recoverability or high fraud exposure. Requires human escalation or safe stop. |

---

## 5. Priority Score & Priority Tiers

To prioritize merchant attention and recovery queues:

$$\text{PriorityScore} = (\text{AmountScore} \times 0.50) + (\text{RecoverabilityScore} \times 100 \times 0.30) + (\text{CustomerValueScore} \times 0.20)$$

| Priority Level | Priority Score | Action Queue Position |
| :--- | :--- | :--- |
| **CRITICAL** | $\ge 80.0$ | Instant automated intervention / Urgent alert |
| **HIGH** | $60.0 - 79.9$ | High priority processing |
| **MEDIUM** | $35.0 - 59.9$ | Standard processing |
| **LOW** | $< 35.0$ | Low priority processing |
