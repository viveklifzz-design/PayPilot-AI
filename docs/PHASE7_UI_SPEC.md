# PayPilot AI — Phase 7 Merchant Dashboard UI Specification

**Track 03 — AI Revenue Recovery | Razorpay AI Buildathon**

---

## 1. Overview & UI Design Principles

The **PayPilot AI Merchant Dashboard** is a clean, data-driven, judge-facing SaaS interface built using **Next.js (App Router), TypeScript, and Tailwind CSS**. 

It provides real-time visibility into the revenue recovery pipeline, proving to merchants and Buildathon judges that PayPilot AI:
1. **Detects** revenue at risk across failed payment transactions.
2. **Diagnoses** payment failure root causes via structured AI outputs.
3. **Validates** all AI recommendations through a non-bypassable deterministic Policy Safety Gate.
4. **Executes** bounded recovery actions via Razorpay Test Mode APIs.
5. **Verifies** outcomes and measures actual recovered revenue across single cases and 100-case batches.

### Design Principles:
- **Trustworthy & Data-Driven**: Professional fintech styling (navy, slate, emerald, amber, rose color palette).
- **5-Second Clarity**: High-impact metric cards, visual conversion funnels, and clear status badges.
- **Strict Disambiguation**: Clearly distinguishes **REAL Razorpay Test Mode** vs **Simulation / Evaluation Mode**.
- **Responsive**: Fully responsive layout for desktop, tablet, and mobile browsers.

---

## 2. Navigation & Screen Architecture

```
                    PayPilot AI Top Navigation & Integration Bar
       [Razorpay Status Badge | Mode Switcher | API Health Indicator]
                                     │
    ┌────────────────┬───────────────┼───────────────┬────────────────┐
    ▼                ▼               ▼               ▼                ▼
Screen 1:        Screen 2:       Case Detail     Screen 3:        Screen 4:
Overview         Recovery Cases  Drawer          Policy Safety    Batch Benchmark
- Metrics        - Filterable    - Timeline      - Safety Rules   - 100-Case Eval
- Funnel           Table         - AI Reasoning  - AI vs Policy   - Seed Runner
- Activity Feed  - Tiers & Badges- Audit Events    Overrides      - History
```

---

## 3. Screen Specifications

### Screen 1: Overview & Metrics Dashboard
- **Header Summary Cards**:
  - `Revenue At Risk` (₹ Amount)
  - `Recovered Revenue` (₹ Amount)
  - `Recovery Rate` (%)
  - `Failed Payments` (Count)
  - `Recovered Cases` (Count)
  - `Recovery Attempts` (Count)
  - `Policy Blocks` (Count)
  - `Escalated Cases` (Count)
- **Recovery Funnel**: Visual stage conversion bar (`Failed Payments` $\rightarrow$ `AI Diagnosed` $\rightarrow$ `Policy Approved` $\rightarrow$ `Recovery Attempted` $\rightarrow$ `Revenue Recovered`).
- **Recent Activity Stream**: Real-time event log fetched from `/api/v1/analytics/recent-activity`.

### Screen 2: Recovery Cases Explorer & Detail Drawer
- **Filter Bar**: `All`, `Critical`, `High`, `Medium`, `Low`, `Recovered`, `Blocked`, `Escalated`.
- **Cases Table**: Columns for Case ID, Amount (₹), Risk Level, Risk Score, Failure Category, AI Recommendation, AI Confidence %, Policy Decision, Recovery Status, Recovered Amount, Created Time.
- **Interactive Case Detail Drawer**:
  - **Visual Timeline**: `Payment Failed` $\rightarrow$ `Risk Analysis` $\rightarrow$ `AI Diagnosis` $\rightarrow$ `Policy Gate` $\rightarrow$ `Recovery Action` $\rightarrow$ `Webhook Verification` $\rightarrow$ `Final Outcome`.
  - **Context Tabs**: Payment Details, Risk Factors, AI Explanation, Policy Rules Evaluated, Policy Violations, Execution Details, Raw Audit Trail.

### Screen 3: Safety & Policy Gate View
- **Policy Rules Grid**: Displays active policy thresholds (`MAX_RETRY_LIMIT = 3`, `COOLDOWN_HOURS = 2h`, `MAX_AUTO_RECOVERY_AMOUNT = ₹50,000`, `MIN_AI_CONFIDENCE = 70%`, `SUSPECTED_FRAUD_GUARD`, `ALREADY_RECOVERED_GUARD`).
- **AI Recommendation $\neq$ Final Action Visualizer**: Demonstrates real cases where AI recommended an action (e.g., `RETRY` with 99% confidence), but the Policy Gate blocked it and forced safe escalation (`ESCALATE` / `STOP`).

### Screen 4: Batch Benchmark & Simulation Runner
- **Batch Metric Summary**: Batch Size, Revenue At Risk, Recovered Revenue, Recovery Rate %, Recovery Success Rate %, Policy Approval %, Policy Block %, Escalated %, Remaining Risk.
- **Simulation Control Panel**: Inputs for `Batch Size` (default 100), `Seed` (default 42), and `Run Evaluation` button.
- **Mode Badge**: Prominently displays `SIMULATION / EVALUATION MODE`.
- **Run History**: Table of past evaluation runs with direct inspection support.

---

## 4. API Endpoints Mapping

| Frontend Component | Backend API Route | Data Returned |
| :--- | :--- | :--- |
| Overview Metrics Cards | `GET /api/v1/analytics/metrics` | Financial metrics & counters |
| Overview Funnel | `GET /api/v1/analytics/funnel` | Conversion funnel stage counts |
| Overview Recent Activity | `GET /api/v1/analytics/recent-activity` | Activity stream audit logs |
| Cases Table | `GET /api/v1/cases` | Filtered list of recovery cases |
| Case Detail Drawer | `GET /api/v1/cases/{id}` | Detailed case info & risk factors |
| Case Audit Trail | `GET /api/v1/cases/{id}/audit-trail` | Case audit logs |
| Batch Benchmark Run | `POST /api/v1/evaluation/run` | Triggers 100-case evaluation run |
| Batch Run Details | `GET /api/v1/evaluation/runs/{id}` | Batch run metrics summary |
| Batch Cases Breakdown | `GET /api/v1/evaluation/runs/{id}/cases` | Case-level evaluation results |
| Batch Audit Trail | `GET /api/v1/evaluation/runs/{id}/audit` | Policy decision audit trail |
| Execute Case Action | `POST /api/v1/cases/{id}/execute` | Executes recovery action |
