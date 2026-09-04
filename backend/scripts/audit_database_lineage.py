import sys
import os
import sqlite3

def audit_database_lineage():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "paypilot_dev.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("=================================================================")
    print("   PAYPILOT AI -- DATABASE LINEAGE & INTEGRITY AUDIT             ")
    print("=================================================================\n")

    # 1. Audit Original Failed Payment pay_TTXlSqxyg5hAiT
    print("1. DATABASE AUDIT FOR ORIGINAL FAILED PAYMENT (pay_TTXlSqxyg5hAiT)...")
    t1 = cur.execute("SELECT id, razorpay_payment_id, razorpay_order_id, amount, status, error_code, error_reason FROM transactions WHERE razorpay_payment_id = 'pay_TTXlSqxyg5hAiT'").fetchone()
    if t1:
        print(f"   - Transaction DB ID : {t1[0]}")
        print(f"   - Payment ID       : {t1[1]}")
        print(f"   - Order ID         : {t1[2]}")
        print(f"   - Amount           : INR {t1[3]:.2f}")
        print(f"   - Status           : {t1[4]}")
        print(f"   - Error Code       : {t1[5]}")
        print(f"   - Error Reason     : {t1[6]}")

        # Update order_id if it was improperly set to order_TU2xgzptEfg7rP
        if t1[2] != 'order_TTKk5jdEkFdEIY':
            print(f"   [FIX] Updating DB Transaction razorpay_order_id from '{t1[2]}' to actual provider order_id 'order_TTKk5jdEkFdEIY'")
            cur.execute("UPDATE transactions SET razorpay_order_id = 'order_TTKk5jdEkFdEIY' WHERE razorpay_payment_id = 'pay_TTXlSqxyg5hAiT'")
            conn.commit()
    else:
        print("   [WARN] pay_TTXlSqxyg5hAiT not found in transactions table.")

    print("\n-----------------------------------------------------------------\n")

    # 2. Audit Recovery Case for pay_TTXlSqxyg5hAiT
    print("2. DATABASE AUDIT FOR RECOVERY CASE...")
    c1 = cur.execute("SELECT id, transaction_id, amount, status, recovered_amount, actual_action_taken FROM recovery_cases WHERE transaction_id = ? OR amount = 10.0", (t1[0] if t1 else 'none',)).fetchall()
    for c in c1:
        print(f"   - RecoveryCase ID   : {c[0]}")
        print(f"   - Transaction ID    : {c[1]}")
        print(f"   - Case Amount       : INR {c[2]:.2f}")
        print(f"   - Case Status       : {c[3]}")
        print(f"   - Recovered Amount  : INR {c[4]:.2f}")
        print(f"   - Action Taken      : {c[5]}")

    print("\n-----------------------------------------------------------------\n")

    # 3. Audit Recovery Payment pay_TU3EQsT63DFVuX
    print("3. DATABASE AUDIT FOR RECOVERY PAYMENT (pay_TU3EQsT63DFVuX)...")
    t3 = cur.execute("SELECT id, razorpay_payment_id, razorpay_order_id, amount, status FROM transactions WHERE razorpay_payment_id = 'pay_TU3EQsT63DFVuX'").fetchone()
    if t3:
        print(f"   - Transaction DB ID : {t3[0]}")
        print(f"   - Payment ID       : {t3[1]}")
        print(f"   - Order ID         : {t3[2]}")
        print(f"   - Amount           : INR {t3[3]:.2f}")
        print(f"   - Status           : {t3[4]}")
    else:
        print("   [WARN] pay_TU3EQsT63DFVuX not found in transactions table.")

    print("\n=================================================================")
    print("   DATABASE LINEAGE AUDIT COMPLETE                              ")
    print("=================================================================\n")

    conn.close()

if __name__ == "__main__":
    audit_database_lineage()
