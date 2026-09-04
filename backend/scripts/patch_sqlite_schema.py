import sqlite3

def patch():
    conn = sqlite3.connect("paypilot_dev.db")
    cursor = conn.cursor()
    
    # Patch recovery_cases
    cols = [row[1] for row in cursor.execute("PRAGMA table_info(recovery_cases)").fetchall()]
    if "case_type" not in cols:
        cursor.execute("ALTER TABLE recovery_cases ADD COLUMN case_type VARCHAR(50) DEFAULT 'PAYMENT_FAILURE'")
    if "checkout_session_id" not in cols:
        cursor.execute("ALTER TABLE recovery_cases ADD COLUMN checkout_session_id VARCHAR(36)")
    if "subscription_id" not in cols:
        cursor.execute("ALTER TABLE recovery_cases ADD COLUMN subscription_id VARCHAR(36)")
    if "subscription_attempt_id" not in cols:
        cursor.execute("ALTER TABLE recovery_cases ADD COLUMN subscription_attempt_id VARCHAR(36)")
        
    # Patch transactions
    t_cols = [row[1] for row in cursor.execute("PRAGMA table_info(transactions)").fetchall()]
    if "error_source" not in t_cols:
        cursor.execute("ALTER TABLE transactions ADD COLUMN error_source VARCHAR(100)")
    if "error_step" not in t_cols:
        cursor.execute("ALTER TABLE transactions ADD COLUMN error_step VARCHAR(100)")
    if "error_reason" not in t_cols:
        cursor.execute("ALTER TABLE transactions ADD COLUMN error_reason VARCHAR(100)")

    conn.commit()
    print("Updated recovery_cases cols:", [row[1] for row in cursor.execute("PRAGMA table_info(recovery_cases)").fetchall()])
    print("Updated transactions cols:", [row[1] for row in cursor.execute("PRAGMA table_info(transactions)").fetchall()])
    conn.close()

if __name__ == "__main__":
    patch()
