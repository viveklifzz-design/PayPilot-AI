import urllib.request
import json
import sqlite3
import os

def audit_all():
    print("=================================================================")
    print("     PAYPILOT AI -- FINAL INTEGRATION REGRESSION AUDIT           ")
    print("=================================================================\n")

    # 1. Primary Frontend Routes Check
    routes = [
        "http://localhost:3000/",
        "http://localhost:3000/cases",
        "http://localhost:3000/safety",
        "http://localhost:3000/benchmark"
    ]
    print("--- 1. FRONTEND PRIMARY ROUTES HTTP CHECK ---")
    for r in routes:
        try:
            code = urllib.request.urlopen(r).getcode()
            print(f" {r:35} -> HTTP {code} ({'PASS' if code == 200 else 'FAIL'})")
        except Exception as e:
            print(f" {r:35} -> ERROR: {e}")

    # 2. Unified Risk API vs DB Calculations Check
    print("\n--- 2. UNIFIED RISK API vs DIRECT DB CALCULATIONS ---")
    summary = json.loads(urllib.request.urlopen("http://127.0.0.1:8000/api/v1/revenue-risk/summary").read().decode())
    opps = json.loads(urllib.request.urlopen("http://127.0.0.1:8000/api/v1/revenue-risk/opportunities").read().decode())

    conn = sqlite3.connect("paypilot_dev.db")
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
    db_mnd = sum(r[1] for r in active_rows if r[0] == 'MANDATE_RETRY')
    db_total = db_pf + db_cd + db_sub + db_b2b + db_mnd

    rec_row = cur.execute("SELECT sum(recovered_amount) FROM recovery_cases WHERE status = 'RECOVERED'").fetchone()
    db_recovered = rec_row[0] or 0.0
    conn.close()

    print(f" API Total Risk       : INR {summary['total_revenue_at_risk']:,.2f} | DB Total Risk : INR {db_total:,.2f}")
    print(f" API Payment Fail Risk: INR {summary['payment_failure_risk']:,.2f} | DB Fail Risk  : INR {db_pf:,.2f}")
    print(f" API Dropoff Risk     : INR {summary['checkout_dropoff_risk']:,.2f} | DB Drop Risk  : INR {db_cd:,.2f}")
    print(f" API Subscription Risk: INR {summary['subscription_risk']:,.2f} | DB Sub Risk   : INR {db_sub:,.2f}")
    print(f" API Recovered Revenue: INR {summary['total_recovered_revenue']:,.2f} | DB Recovered  : INR {db_recovered:,.2f}")

    match = (
        summary['total_revenue_at_risk'] == db_total and
        summary['payment_failure_risk'] == db_pf and
        summary['checkout_dropoff_risk'] == db_cd and
        summary['subscription_risk'] == db_sub and
        summary['total_recovered_revenue'] == db_recovered
    )
    print(f" Financial Consistency Verdict: {'PASS (100% MATCH)' if match else 'FAIL'}")

    # 3. Secret & Hardcoded URL Scan
    print("\n--- 3. SECRET EXPOSURE & HARDCODED CREDENTIAL SCAN ---")
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    PATTERNS = ["RAZORPAY_KEY_SECRET=", "RAZORPAY_WEBHOOK_SECRET=", "GEMINI_API_KEY="]
    unredacted = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        if any(x in root for x in ["venv", "node_modules", ".git", ".next", "brain"]):
            continue
        for file in files:
            if file.endswith((".py", ".ts", ".tsx")):
                path = os.path.join(root, file)
                rel = os.path.relpath(path, PROJECT_ROOT)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_idx, line in enumerate(f, 1):
                            for p in PATTERNS:
                                if p in line and not line.strip().endswith("=") and "your_" not in line and ".example" not in file:
                                    unredacted.append(f"{rel}:L{line_idx}: {p}")
                except Exception:
                    pass

    if unredacted:
        for u in unredacted:
            print(" [FAIL]", u)
    else:
        print(" [PASS] Zero unredacted secrets found in committed source code files.")

if __name__ == "__main__":
    audit_all()
