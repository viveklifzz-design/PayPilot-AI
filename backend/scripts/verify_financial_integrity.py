import urllib.request
import json
import sqlite3
import os

def run_financial_integrity_check():
    print("=================================================================")
    print("   PAYPILOT AI -- FINANCIAL INTEGRITY & DEDUPLICATION AUDIT      ")
    print("=================================================================\n")

    url = "http://127.0.0.1:8000/api/v1/revenue-risk/summary"
    try:
        api_summary = json.loads(urllib.request.urlopen(url).read().decode())
    except Exception as e:
        print(f"[FAIL] Could not query API summary at {url}: {e}")
        return False

    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "paypilot_dev.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    active_rows = cur.execute("""
        SELECT case_type, amount 
        FROM recovery_cases 
        WHERE status IN ('OPEN', 'DIAGNOSED', 'ACTION_PENDING', 'IN_PROGRESS', 'RECOVERING')
    """).fetchall()

    db_pf = sum(r[1] for r in active_rows if r[0] == 'PAYMENT_FAILURE')
    db_cd = sum(r[1] for r in active_rows if r[0] == 'CHECKOUT_DROPOFF')
    db_sub = sum(r[1] for r in active_rows if r[0] == 'SUBSCRIPTION_FAILURE')
    db_b2b = sum(r[1] for r in active_rows if r[0] == 'B2B_RECEIVABLE')
    db_mand = sum(r[1] for r in active_rows if r[0] == 'MANDATE_RETRY')
    db_total_risk = db_pf + db_cd + db_sub + db_b2b + db_mand

    rec_row = cur.execute("SELECT sum(recovered_amount) FROM recovery_cases WHERE status = 'RECOVERED'").fetchone()
    db_recovered = rec_row[0] or 0.0
    conn.close()

    api_total_risk = api_summary["total_revenue_at_risk"]
    api_recovered = api_summary["total_recovered_revenue"]

    risk_discrepancy = abs(api_total_risk - db_total_risk)
    rec_discrepancy = abs(api_recovered - db_recovered)

    print(f" Direct DB Active Revenue at Risk : INR {db_total_risk:,.2f}")
    print(f" API Summary Total Revenue Risk  : INR {api_total_risk:,.2f}")
    print(f" Discrepancy                     : INR {risk_discrepancy:,.2f}")
    print("-----------------------------------------------------------------")
    print(f" Direct DB Recovered Revenue      : INR {db_recovered:,.2f}")
    print(f" API Summary Recovered Revenue    : INR {api_recovered:,.2f}")
    print(f" Discrepancy                     : INR {rec_discrepancy:,.2f}")
    print("-----------------------------------------------------------------")

    passed = (risk_discrepancy == 0.0 and rec_discrepancy == 0.0)
    if passed:
        print("[PASS] Financial Integrity Verified: ZERO DISCREPANCY (INR 0.00)")
    else:
        print("[FAIL] Financial Discrepancy Detected!")

    print("\n=================================================================")
    print(f"   FINANCIAL INTEGRITY AUDIT VERDICT: {'PASS' if passed else 'FAIL'}")
    print("=================================================================\n")
    return passed

if __name__ == "__main__":
    run_financial_integrity_check()
