import sqlite3
import urllib.request
import json

def verify_db_deduplication():
    conn = sqlite3.connect("paypilot_dev.db")
    cursor = conn.cursor()

    # Query active cases directly from database
    cursor.execute("""
        SELECT case_type, amount, status 
        FROM recovery_cases 
        WHERE status IN ('OPEN', 'DIAGNOSED', 'ACTION_PENDING', 'IN_PROGRESS', 'RECOVERING')
    """)
    active_rows = cursor.fetchall()

    db_pf_risk = sum(r[1] for r in active_rows if r[0] == 'PAYMENT_FAILURE' or r[0] is None)
    db_cd_risk = sum(r[1] for r in active_rows if r[0] == 'CHECKOUT_DROPOFF')
    db_sub_risk = sum(r[1] for r in active_rows if r[0] == 'SUBSCRIPTION_FAILURE')
    db_total_risk = db_pf_risk + db_cd_risk + db_sub_risk

    # Query recovered cases directly from database
    cursor.execute("SELECT sum(recovered_amount) FROM recovery_cases WHERE status = 'RECOVERED'")
    db_recovered_revenue = cursor.fetchone()[0] or 0.0

    conn.close()

    # Fetch API summary
    api_summary = json.loads(urllib.request.urlopen("http://127.0.0.1:8000/api/v1/revenue-risk/summary").read().decode())

    print("--- INDEPENDENT DATABASE CALCULATION ---")
    print(f"DB Total Risk       : INR {db_total_risk:,.2f}")
    print(f"DB Payment Fail Risk: INR {db_pf_risk:,.2f}")
    print(f"DB Dropoff Risk     : INR {db_cd_risk:,.2f}")
    print(f"DB Subscription Risk: INR {db_sub_risk:,.2f}")
    print(f"DB Recovered Revenue: INR {db_recovered_revenue:,.2f}")

    print("\n--- UNIFIED API RESPONSE ---")
    print(f"API Total Risk      : INR {api_summary['total_revenue_at_risk']:,.2f}")
    print(f"API Payment Fail Risk: INR {api_summary['payment_failure_risk']:,.2f}")
    print(f"API Dropoff Risk    : INR {api_summary['checkout_dropoff_risk']:,.2f}")
    print(f"API Subscription Risk: INR {api_summary['subscription_risk']:,.2f}")
    print(f"API Recovered Revenue: INR {api_summary['total_recovered_revenue']:,.2f}")

    match = (
        db_total_risk == api_summary['total_revenue_at_risk'] and
        db_pf_risk == api_summary['payment_failure_risk'] and
        db_recovered_revenue == api_summary['total_recovered_revenue']
    )
    print(f"\nVERIFICATION RESULT: {'MATCH (PASS)' if match else 'DISCREPANCY (FAIL)'}")

if __name__ == "__main__":
    verify_db_deduplication()
