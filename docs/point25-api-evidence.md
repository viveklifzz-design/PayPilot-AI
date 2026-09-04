# POINT #25 — UNIFIED API EVIDENCE VERIFICATION REPORT

## 1. Executive Summary
Independent verification of the unified endpoints `GET /api/v1/revenue-risk/summary` and `GET /api/v1/revenue-risk/opportunities` was conducted on `http://127.0.0.1:8000`.

Status: **PASS (GREEN)**

---

## 2. Actual API Response Snippets

### Endpoint: `GET /api/v1/revenue-risk/summary`
```json
{
  "total_revenue_at_risk": 21500.0,
  "payment_failure_risk": 21500.0,
  "checkout_dropoff_risk": 0.0,
  "subscription_risk": 0.0,
  "recoverable_revenue": 15050.0,
  "total_recovered_revenue": 2500.0,
  "unified_recovery_rate": 10.42,
  "total_cases_count": 8,
  "active_opportunities_count": 7,
  "high_priority_count": 0,
  "cases_by_source": {
    "PAYMENT_FAILURE": 8,
    "CHECKOUT_DROPOFF": 0,
    "SUBSCRIPTION_FAILURE": 0
  },
  "cases_by_unified_status": {
    "AT_RISK": 2,
    "RECOVERING": 5,
    "RECOVERED": 1,
    "STOPPED": 0,
    "ESCALATED": 0,
    "EXPIRED": 0
  }
}
```

### Endpoint: `GET /api/v1/revenue-risk/opportunities`
```json
{
  "summary": { ... },
  "opportunities": [
    {
      "case_id": "b52e274f-cef3-4d8c-bf70-484645ddf961",
      "case_type": "PAYMENT_FAILURE",
      "amount": 4500.0,
      "risk_amount": 4500.0,
      "recoverability_score": 0.7,
      "priority_score": 24.6,
      "priority_level": "LOW",
      "priority_factors": [
        "Standard transaction value (₹4,500.00)",
        "Moderate recovery probability (70%)"
      ],
      "failure_category": "NETWORK_OR_TECHNICAL_FAILURE",
      "status": "OPEN",
      "unified_status": "AT_RISK",
      "source": "RAZORPAY_WEBHOOK"
    },
    ...
  ]
}
```

---

## 3. Mandatory Compliance Checklist

| Check | Verdict | Evidence / Reasoning |
| :--- | :---: | :--- |
| **Mathematical Consistency** | **PASS** | `total_revenue_at_risk` (21500) = `pf_risk` (21500) + `cd_risk` (0) + `sub_risk` (0) |
| **Recoverable vs Total Risk** | **PASS** | `recoverable_revenue` (15050.0) $\le$ `total_revenue_at_risk` (21500.0) |
| **Active Risk Excludes Recovered** | **PASS** | Active risk (21500.0) excludes the 1 `RECOVERED` case (2500.0) |
| **Deterministic Priority Sorting** | **PASS** | Opportunities sorted by `priority_score` descending (24.6 $\rightarrow$ 23.8 $\rightarrow$ 18.8 $\rightarrow$ 18.8 $\rightarrow$ 18.0 $\rightarrow$ 18.0 $\rightarrow$ 17.2) |
| **No Duplicate Case IDs** | **PASS** | 7 active opportunity items have 7 distinct UUIDs |
| **No Negative Amounts** | **PASS** | All currency values $\ge 0.0$ |
