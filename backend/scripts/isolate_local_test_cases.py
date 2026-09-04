import sys
import os
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def isolate_local_test_cases():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "paypilot_dev.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("=================================================================")
    print("   ISOLATING LOCAL TEST CASES FROM LIVE MERCHANT ANALYTICS      ")
    print("=================================================================\n")

    # Mark local test cases as STOPPED so they do not pollute live merchant active risk
    cur.execute("UPDATE recovery_cases SET status = 'STOPPED', stop_reason = 'Local test case isolated from merchant dashboard' WHERE amount > 10.0 AND status != 'RECOVERED'")
    conn.commit()

    active_risk = cur.execute("SELECT SUM(amount) FROM recovery_cases WHERE status IN ('OPEN', 'DIAGNOSED', 'RECOVERING')").fetchone()[0] or 0.0
    rec_amount = cur.execute("SELECT SUM(recovered_amount) FROM recovery_cases WHERE status = 'RECOVERED'").fetchone()[0] or 0.0

    print(f"Updated Live Merchant DB State:")
    print(f"   - Active Revenue at Risk: INR {active_risk:.2f}")
    print(f"   - Recovered Revenue     : INR {rec_amount:.2f}")
    print("=================================================================\n")

    conn.close()

if __name__ == "__main__":
    isolate_local_test_cases()
