import sqlite3

conn = sqlite3.connect('backend/paypilot_dev.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT * FROM recovery_cases WHERE status='RECOVERED'")
cases = cursor.fetchall()

print(f"Total Cases with status='RECOVERED': {len(cases)}\n")

for c in cases:
    c_id = c['id']
    amt = c['amount']
    rec_amt = c['recovered_amount']
    c_type = c['case_type']
    
    # check actions
    cursor.execute("SELECT * FROM recovery_actions WHERE case_id=?", (c_id,))
    actions = [dict(a) for a in cursor.fetchall()]
    
    # check matching captured transaction in DB
    cursor.execute("SELECT * FROM transactions WHERE status='captured'")
    all_captured = cursor.fetchall()
    matched_captured = []
    for t in all_captured:
        t_dict = dict(t)
        # Check if transaction matches case ID, amount, or payload
        if t_dict['amount'] == rec_amt or (c['transaction_id'] and t_dict['id'] == c['transaction_id']):
            matched_captured.append(t_dict)

    print(f"Case {c_id}: Type={c_type}, Amt={amt}, RecAmt={rec_amt}")
    print(f"  Actions: {actions}")
    print(f"  Possible Captured Txns in DB: {matched_captured}\n")
