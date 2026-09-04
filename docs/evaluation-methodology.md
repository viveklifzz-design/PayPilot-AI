# PayPilot AI — Synthetic Evaluation Methodology & Benchmark Results

## 1. Benchmark Execution Parameters
- **Dataset Size**: 1,000 synthetic payment failure cases
- **Random Seed**: `42` (Ensures 100% deterministic reproducibility)
- **Execution Mode**: `deterministic`
- **Notice**: **Synthetic Evaluation — No Real Money**

---

## 2. Empirical Benchmark Metrics

```text
-------------------------------------------------------
  Revenue at Risk       : INR 19,092,323.00
  Recoverable Revenue   : INR 8,567,489.00
  Revenue Recovered     : INR 5,080,707.00
-------------------------------------------------------
  Precision             : 83.69%
  Recall                : 86.13%
  Recovery Rate         : 59.27%
  Intervention Rate     : 70.50%
  Safe Stop Rate        : 25.86%
  Escalation Rate       : 17.90%
  Unsafe Actions        : 0
-------------------------------------------------------
```

---

## 3. Metric Definitions & Formulas

1. **Precision**:
   $$\text{Precision} = \frac{\text{True Positives (Correct Recoveries)}}{\text{True Positives} + \text{False Positives}} = \frac{703}{703 + 137} = 83.69\%$$
2. **Recall**:
   $$\text{Recall} = \frac{\text{True Positives}}{\text{True Positives} + \text{False Negatives}} = \frac{703}{703 + 113} = 86.13\%$$
3. **Recovery Rate**:
   $$\text{Recovery Rate} = \frac{\text{Revenue Recovered}}{\text{Recoverable Revenue}} = \frac{\text{INR } 5,080,707.00}{\text{INR } 8,567,489.00} = 59.27\%$$
4. **Unsafe Action Count**:
   $$\text{Unsafe Actions} = 0$$
   *(Zero policy violations, unearned recoveries, or unauthorized money actions)*
