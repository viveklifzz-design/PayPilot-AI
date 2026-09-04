import requests

BASE_URL = "http://localhost:3000"

def verify_visual_data_qa():
    print("=================================================================")
    print("   PAYPILOT AI -- BROWSER DATA & VISUAL QA DETAILED AUDIT        ")
    print("=================================================================\n")

    # 1. OVERVIEW DATA CHECK
    print("1. OVERVIEW PAGE (/) DATA QA:")
    res_overview = requests.get(f"{BASE_URL}/")
    print(f"   - HTTP Status: {res_overview.status_code}")
    print(f"   - Single Header: {'<header' in res_overview.text and res_overview.text.count('<header') == 1}")
    print(f"   - Single Sidebar: {'<aside' in res_overview.text and res_overview.text.count('<aside') == 1}")

    # 2. TRANSACTIONS DATA CHECK
    print("\n2. TRANSACTIONS PAGE (/transactions) DATA QA:")
    res_txns = requests.get("http://127.0.0.1:8000/api/v1/transactions").json()
    txn_ids = [t.get("razorpay_payment_id") for t in res_txns]
    print(f"   - Live Transactions Returned: {len(res_txns)}")
    print(f"   - Razorpay Payment IDs: {txn_ids}")
    has_real_fail = "pay_TTXlSqxyg5hAiT" in txn_ids
    has_real_recovery = "pay_TU3EQsT63DFVuX" in txn_ids
    has_synthetic_test = any(tid and "pay_test_fail_" in tid for tid in txn_ids)
    print(f"   - Real Failure (pay_TTXlSqxyg5hAiT) Present   : {has_real_fail}")
    print(f"   - Real Recovery (pay_TU3EQsT63DFVuX) Present : {has_real_recovery}")
    print(f"   - Synthetic Test (pay_test_fail_) Excluded    : {not has_synthetic_test}")

    # 3. RECOVERY CASES DATA CHECK
    print("\n3. RECOVERY CASES PAGE (/cases) DATA QA:")
    res_cases = requests.get("http://127.0.0.1:8000/api/v1/cases").json()
    case_ids = [c.get("id") for c in res_cases]
    amounts = [c.get("amount") for c in res_cases]
    statuses = [c.get("status") for c in res_cases]
    print(f"   - Live Recovery Cases Returned: {len(res_cases)}")
    print(f"   - Case IDs: {case_ids}")
    print(f"   - Amounts: {amounts}")
    print(f"   - Statuses: {statuses}")
    has_real_case = "d669dce3-b855-4348-b457-f0ef7c34b6b1" in case_ids
    has_synthetic_b2b = any(amt > 50000.0 for amt in amounts)
    print(f"   - Real Case (d669dce3-b855-4348-b457-f0ef7c34b6b1) Present : {has_real_case}")
    print(f"   - Synthetic B2B (> 50k) Excluded                          : {not has_synthetic_b2b}")

    # 4. REVENUE RISK SUMMARY CHECK
    print("\n4. REVENUE RISK PAGE (/revenue-risk) DATA QA:")
    res_risk = requests.get("http://127.0.0.1:8000/api/v1/revenue-risk/summary").json()
    print(f"   - Total Revenue at Risk     : INR {res_risk.get('total_revenue_at_risk'):.2f}")
    print(f"   - Total Recovered Revenue   : INR {res_risk.get('total_recovered_revenue'):.2f}")
    print(f"   - Unified Recovery Rate     : {res_risk.get('unified_recovery_rate')}%")

    # 5. BENCHMARK ISOLATION CHECK
    print("\n5. SYNTHETIC BENCHMARK PAGE (/benchmark) QA:")
    res_bench = requests.get(f"{BASE_URL}/benchmark")
    is_synthetic_labeled = "SYNTHETIC" in res_bench.text
    print(f"   - Clearly Labeled SYNTHETIC : {is_synthetic_labeled}")

    print("\n=================================================================")
    qa_pass = has_real_fail and has_real_recovery and not has_synthetic_test and has_real_case and not has_synthetic_b2b and is_synthetic_labeled
    if qa_pass:
        print("   FINAL BROWSER VISUAL & DATA QA VERDICT: PASS                  ")
    else:
        print("   FINAL BROWSER VISUAL & DATA QA VERDICT: FAIL                  ")
    print("=================================================================\n")

if __name__ == "__main__":
    verify_visual_data_qa()
