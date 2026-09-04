import sqlite3
import json

conn = sqlite3.connect('backend/paypilot_dev.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT * FROM recovery_cases")
cases = cursor.fetchall()

print(f"Total Recovery Cases: {len(cases)}\n")

for c in cases:
    c_dict = dict(c)
    print(f"--- CASE ID: {c_dict['id']} ---")
    print(f"Type: {c_dict['case_type']} | Amount: {c_dict['amount']} | Recovered Amount: {c_dict['recovered_amount']} | Status: {c_dict['status']}")
    print(f"Transaction ID: {c_dict['transaction_id']} | Mandate ID: {c_dict['mandate_id']}")
    
    # Get transaction
    if c_dict['transaction_id']:
        cursor.execute("SELECT * FROM transactions WHERE id=?", (c_dict['transaction_id'],))
        txn = cursor.fetchone()
        if txn:
            print(f"  Transaction: {dict(txn)}")
        else:
            print(f"  Transaction: NOT FOUND for id {c_dict['transaction_id']}")
    
    # Get recovery action
    cursor.execute("SELECT * FROM recovery_actions WHERE case_id=?", (c_dict['id'],))
    actions = cursor.fetchall()
    for a in actions:
        print(f"  Action: {dict(a)}")

    # Get audit log
    cursor.execute("SELECT * FROM audit_logs WHERE case_id=? ORDER BY created_at ASC", (c_dict['id'],))
    logs = cursor.fetchall()
    for l in logs:
        print(f"  Audit: [{l['created_at']}] {l['actor']} -> {l['event_type']}: {l['description']}")
    print("\n")
