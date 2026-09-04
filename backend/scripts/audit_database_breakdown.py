import sys
import os
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def audit_database_breakdown():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "paypilot_dev.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("=================================================================")
    print("   PAYPILOT AI -- MASTER DATABASE CONTAMINATION & LINEAGE AUDIT  ")
    print("=================================================================\n")

    # 1. Audit Transactions Table
    print("--- 1. TRANSACTIONS TABLE BREAKDOWN ---")
    txns = cur.execute("SELECT id, razorpay_payment_id, razorpay_order_id, amount, status FROM transactions").fetchall()
    print(f"Total Transactions in DB: {len(txns)}\n")

    real_provider_txns = []
    local_test_txns = []
    synthetic_txns = []

    for t in txns:
        t_id, rzp_pay_id, rzp_order_id, amount, status = t
        is_real = (rzp_pay_id in ["pay_TTXlSqxyg5hAiT", "pay_TTa6BvTMgDHtc8", "pay_TU3EQsT63DFVuX"]) or (rzp_order_id in ["order_TU2xgzptEfg7rP", "order_TTa635I4vZt4cV"])
        
        classification = "REAL RAZORPAY TEST MODE" if is_real else ("SYNTHETIC EVALUATION" if amount > 5000 else "LOCAL TEST DATA")
        
        if is_real:
            real_provider_txns.append(t)
        elif classification == "SYNTHETIC EVALUATION":
            synthetic_txns.append(t)
        else:
            local_test_txns.append(t)

        print(f"Txn ID: {t_id[:16]}... | RzpPayID: {rzp_pay_id or 'N/A':<20} | Amount: INR {amount:10.2f} | Status: {status:<10} | Class: {classification}")

    # 2. Audit Recovery Cases Table
    print("\n--- 2. RECOVERY CASES TABLE BREAKDOWN ---")
    cases = cur.execute("SELECT id, transaction_id, amount, status, recovered_amount, case_type FROM recovery_cases").fetchall()
    print(f"Total Recovery Cases in DB: {len(cases)}\n")

    for c in cases:
        c_id, t_id, amount, status, rec_amt, c_type = c
        c_type_str = c_type or "PAYMENT_FAILURE"
        is_real_case = (amount == 10.0 and (status in ["RECOVERED", "RECOVERING", "OPEN", "DIAGNOSED"]))
        classification = "REAL RAZORPAY TEST MODE" if is_real_case else ("SYNTHETIC EVALUATION" if amount > 5000 else "LOCAL TEST CASE")

        print(f"Case ID: {c_id[:16]}... | TxnID: {t_id[:16] if t_id else 'N/A':<16} | Type: {c_type_str:<18} | Amount: INR {amount:10.2f} | Status: {status:<12} | Recovered: INR {rec_amt:8.2f} | Class: {classification}")

    print("\n-----------------------------------------------------------------")
    print(f"SUMMARY OF CLASSIFICATIONS:")
    print(f"Real Provider Transactions: {len(real_provider_txns)}")
    print(f"Local Test Transactions    : {len(local_test_txns)}")
    print(f"Synthetic Transactions     : {len(synthetic_txns)}")
    print("=================================================================\n")

    conn.close()

if __name__ == "__main__":
    audit_database_breakdown()
