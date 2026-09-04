# PayPilot AI — Batch Evaluation Engine & Measured Revenue Recovery

**Track 03 — AI Revenue Recovery | Razorpay AI Buildathon**

---

## 1. Executive Summary & Purpose

The **Batch Evaluation Engine** provides quantitative, judge-verifiable proof of PayPilot AI's performance across large volumes of failed payment transactions. 

While individual transactions test real-time webhooks and Razorpay API integration, the Batch Evaluation Engine demonstrates how PayPilot AI performs across a batch of transactions (e.g. 100 cases) to measure:
- Total Revenue at Risk
- Total Money Recovered & Recovery Rate (%)
- Policy Safety Gate Enforcement (Allowed vs Blocked)
- Human Escalations & Safe Automation Halts

```
                  Batch Request (batch_size=100, seed=42)
                                    │
                                    ▼
                Synthetic Heterogeneous Scenario Generator
                                    │
    ┌───────────────────────────────┴───────────────────────────────┐
    │  For each case (1 to 100):                                    │
    │  1. Revenue Risk Engine Assessment (score, level, priority)   │
    │  2. AI Failure Diagnosis (root cause, recommended action)     │
    │  3. Policy Safety Gate Validation (MAX_RETRIES, LIMITS)       │
    │  4. Seed-Reproducible Recovery Outcome Simulation            │
    └───────────────────────────────┬───────────────────────────────┘
                                    │
                                    ▼
                     Aggregated Evaluation Metrics
                     (Stored in evaluation_runs)
```

---

## 2. Simulation Mode vs Razorpay Test Mode

| Attribute | Batch Evaluation Mode (`simulation`) | Live Razorpay Test Mode (`razorpay_test`) |
| :--- | :--- | :--- |
| **Purpose** | Measure statistical financial recovery & policy safety across 100+ cases. | Real single-transaction Razorpay API payment link creation & webhook lifecycle. |
| **Provider API** | Internal deterministic simulator (Zero external API calls). | Real Razorpay Test API (`https://api.razorpay.com/v1`). |
| **Reproducibility** | **100% Deterministic** via seed (`seed=42`). | Live real-time network interactions. |
| **Labeling** | Explicitly tagged as `SIMULATION / EVALUATION MODE`. | Explicitly tagged as `RAZORPAY TEST MODE`. |

---

## 3. Financial & Operational Metrics Definitions

1. **Total Revenue at Risk**:
   $$\text{Total Failed Amount} = \sum_{i=1}^{N} \text{Amount}_i$$
2. **Total Money Recovered**:
   $$\text{Total Recovered} = \sum_{i \in \text{Recovered Cases}} \text{Amount}_i$$
3. **Recovery Rate (%)**:
   $$\text{Recovery Rate} = \left( \frac{\text{Total Recovered}}{\text{Total Revenue at Risk}} \right) \times 100$$
4. **Recovery Success Rate (%)**:
   $$\text{Recovery Success Rate} = \left( \frac{\text{Recovered Cases}}{\text{Recovery Attempt Cases}} \right) \times 100$$
5. **Precision Rate (%)**:
   $$\text{Precision Rate} = \left( \frac{\text{Policy Allowed Cases}}{\text{Total Cases}} \right) \times 100$$
6. **False Intervention Block Rate (%)**:
   $$\text{False Intervention Block Rate} = \left( \frac{\text{Policy Blocked Cases}}{\text{Total Cases}} \right) \times 100$$

> **Zero-Division Safeguard**: All division operations in Python handle zero denominators safely (`if total > 0 else 0.0`).

---

## 4. Example 100-Case Evaluation Output (`seed=42`)

```text
--------------------------------------------------
PAYPILOT AI — BATCH EVALUATION REPORT
Run Name: Batch Eval (Size: 100, Seed: 42)
Mode: SIMULATION / EVALUATION MODE
--------------------------------------------------
Total Failed Payments:        100
Total Revenue at Risk:        ₹19,29,700.00
Total Money Recovered:        ₹11,62,200.00
Remaining Revenue at Risk:    ₹7,67,500.00
--------------------------------------------------
Overall Recovery Rate:        60.23%
Recovery Success Rate:        83.87%
--------------------------------------------------
AI Diagnosed Count:           100
Policy Approved Count:        62
Policy Blocked Count:         38
Recovery Attempt Count:       62
Recovered Cases Count:        52
Failed Recovery Count:        10
Human Escalated Count:        26
Safe Stopped Count:           12
--------------------------------------------------
```

---

## 5. API Endpoints

- `POST /api/v1/evaluation/run`: Execute a batch evaluation run (`{"batch_size": 100, "seed": 42, "mode": "simulation"}`).
- `GET /api/v1/evaluation/runs/{run_id}`: Retrieve summary metrics for a run.
- `GET /api/v1/evaluation/runs/{run_id}/cases`: Retrieve individual case breakdown.
- `GET /api/v1/evaluation/runs/{run_id}/audit`: Retrieve decision and policy audit trail for the run.
- `GET /api/v1/analytics/metrics`: High-level aggregated merchant metrics.
- `GET /api/v1/analytics/funnel`: Conversion funnel breakdown.
- `GET /api/v1/analytics/recent-activity`: Real-time decision & activity stream.
