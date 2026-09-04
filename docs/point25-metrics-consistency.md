# Metric Citation & Benchmark Consistency Audit Report

## 1. Overview
This audit classifies every metric citation across the PayPilot AI repository to distinguish historical frozen baselines from the current official multi-source unified benchmark.

---

## 2. Metric Classification Matrix

| Metric Value | Benchmark Category | Description & Context | File Locations |
| :--- | :--- | :--- | :--- |
| **Precision 83.69%**<br>**Recall 86.13%**<br>**Recovery Rate 59.27%** | **Historical Single-Source Baseline** | Evaluation metrics from Point #15–21 baseline freeze computed over payment failure cases only. | `docs/FINAL_BASELINE.md`, `docs/final-metrics.md`, `docs/point21-final-freeze-report.md`, `docs/evaluation-methodology.md`, `README.md` |
| **Precision 77.76%**<br>**Recall 84.98%**<br>**Recovery Rate 56.50%** | **Current Official Unified Benchmark** | Point #25 multi-source benchmark metrics computed over 1,000 synthetic cases sampled across `PAYMENT_FAILURE`, `CHECKOUT_DROPOFF`, and `SUBSCRIPTION_FAILURE`. | `docs/point25-unified-revenue-recovery-report.md`, `docs/point25-evidence-verification-report.md` |

---

## 3. Discrepancy Explanation & Canonical Guidance
- **Why Metrics Differ**: The pre-Point #23 benchmark evaluated payment failures only. The Point #25 benchmark evaluates a unified 3-source dataset including lower-intent checkout abandonments and recurring subscription failures.
- **Canonical Source of Truth**: `docs/point25-unified-revenue-recovery-report.md` is the official current multi-source benchmark for Track 03 evaluation.
