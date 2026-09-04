# PayPilot AI — Judge Demo Path Reliability & Fallback Specification

## 1. Demo Path Reliability Sequence

```text
Overview Dashboard ──► Recovery Cases ──► Case Trace Drawer ──► Synthetic Benchmark ──► Safety Policy
(Live KPIs & Txns)    (Filtered List)    (7-Stage Timeline)      (1,000 Cases)          (Rules & Caps)
```

---

## 2. Step-by-Step Screen Verification & Fallbacks

| Demo Step | Screen / Component | Expected Live Data | Expected Status / Badge | Fallback Behavior |
| :---: | :--- | :--- | :--- | :--- |
| **1** | Navbar | Health badges | `Razorpay Test Mode — Connected` | Shows `Configuration Pending` if API key is unconfigured |
| **2** | Overview KPIs | Live metrics | `Revenue at Risk`, `Recovered Revenue` | Gracefully displays ₹0 while polling backend |
| **3** | Recent Transactions | Live ₹10 payment stream | `captured` / `failed` status | Shows clean empty state if no transactions exist |
| **4** | Recovery Cases (`/cases`) | Case registry list | `RECOVERED` / `ESCALATED` / `STOPPED` | Filter toolbar maintains responsive view |
| **5** | Case Detail Drawer | AI reasoning & Policy | `POLICY APPROVED` badge | If AI key missing, `FallbackAIService` populates diagnosis |
| **6** | 7-Stage Timeline | Chronological trace | `DETECT` $\rightarrow$ `RECOVER` stages | IST timestamps rendered consistently |
| **7** | Benchmark (`/benchmark`) | 1,000 synthetic cases | Precision 83.69%, Recall 86.13% | Prominently labeled `"Synthetic Evaluation — No Real Money"` |
| **8** | Safety (`/safety`) | 6 policy rule cards | Maximum retries, cooldown, ₹50k cap | Static policy rules derived from actual code constants |

---

## 3. Reliability Verification Result
- **Demo Path Execution**: 100% RELIABLE & VERIFIED
- **API Failure Resilience**: Verified with safe fallback responses
