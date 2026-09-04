# PayPilot AI — Complete API Inventory Specification

## 1. Executive Summary
This document provides an inventory of all active REST API endpoints implemented in the PayPilot AI FastAPI backend (`/api/v1`).

---

## 2. API Endpoint Matrix

| Method | Path | Category | Purpose | Security / Auth | Side Effects |
| :---: | :--- | :--- | :--- | :---: | :--- |
| `GET` | `/api/v1/health` | Health | Service status check | None (Public) | None |
| `GET` | `/api/v1/health/db` | Health | Database connectivity check | None (Public) | None |
| `GET` | `/api/v1/health/razorpay` | Health | Safe Razorpay config check | None (Public) | None |
| `GET` | `/api/v1/transactions` | Payments | List transactions stream | None (Public) | None |
| `GET` | `/api/v1/transactions/{id}` | Payments | Fetch single transaction | None (Public) | None |
| `GET` | `/api/v1/cases` | Recovery Cases | List recovery cases | None (Public) | None |
| `GET` | `/api/v1/cases/{case_id}` | Recovery Cases | Fetch recovery case detail | None (Public) | None |
| `POST` | `/api/v1/cases/{case_id}/diagnose` | AI Diagnosis | Run AI Failure Diagnosis | None (Public) | Creates `AIDiagnosis`, logs audit |
| `POST` | `/api/v1/cases/{case_id}/policy-check` | Policy Engine | Evaluate action vs Policy | None (Public) | Evaluates safety gate, logs audit |
| `POST` | `/api/v1/cases/{case_id}/execute` | Recovery Execution | Execute recovery link | None (Public) | Calls Razorpay API, creates `RecoveryAction` |
| `GET` | `/api/v1/cases/{case_id}/timeline` | Audit Trace | Fetch 7-stage decision timeline | None (Public) | None |
| `GET` | `/api/v1/cases/{case_id}/decision-summary` | Audit Trace | Fetch decision explainability | None (Public) | None |
| `GET` | `/api/v1/audit` | Audit Trail | Query structured audit logs | Secret Redacted | None |
| `GET` | `/api/v1/analytics/metrics` | Analytics | Fetch KPI revenue metrics | None (Public) | None |
| `GET` | `/api/v1/analytics/funnel` | Analytics | Fetch 5-stage conversion funnel | None (Public) | None |
| `GET` | `/api/v1/analytics/recent-activity` | Analytics | Fetch real-time audit activity | None (Public) | None |
| `POST` | `/api/v1/evaluation/run` | Benchmark | Run synthetic batch evaluation | None (Public) | Generates synthetic dataset |
| `GET` | `/api/v1/evaluation/summary` | Benchmark | Fetch latest benchmark summary | None (Public) | None |
| `GET` | `/api/v1/evaluation/runs/{id}` | Benchmark | Fetch evaluation run detail | None (Public) | None |
| `GET` | `/api/v1/evaluation/runs/{id}/cases` | Benchmark | Fetch synthetic case list | None (Public) | None |
| `GET` | `/api/v1/evaluation/runs/{id}/export/csv` | Benchmark | Export synthetic run to CSV | None (Public) | Returns CSV file download |
| `POST` | `/api/v1/webhooks/razorpay` | Webhooks | Razorpay HMAC webhook ingestion | HMAC Signature | Mutates case & transaction state |
