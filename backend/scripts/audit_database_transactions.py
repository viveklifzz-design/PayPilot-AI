import os
import sqlite3

def audit_database_transactions():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "paypilot_dev.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("=================================================================")
    print("   ALL TRANSACTIONS IN PAYPILOT DATABASE                         ")
    print("=================================================================\n")

    txns = cur.execute("SELECT id, razorpay_payment_id, razorpay_order_id, amount, status, created_at FROM transactions ORDER BY created_at DESC").fetchall()
    for t in txns:
        print(f"ID: {t[0]} | PayID: {t[1]} | OrderID: {t[2]} | Amount: INR {t[3]:.2f} | Status: {t[4]}")

    print("\n=================================================================")
    print("   ALL RECOVERY CASES IN PAYPILOT DATABASE                       ")
    print("=================================================================\n")

    cases = cur.execute("SELECT id, case_type, transaction_id, amount, status, recovered_amount FROM recovery_cases ORDER BY created_at DESC").fetchall()
    for c in cases:
        print(f"CaseID: {c[0]} | Type: {c[1]} | TxnID: {c[2]} | Amount: INR {c[3]:.2f} | Status: {c[4]} | Recovered: INR {c[5]:.2f}")

    conn.close()

if __name__ == "__main__":
    audit_database_transactions()
