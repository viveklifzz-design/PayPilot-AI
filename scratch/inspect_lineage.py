import sys
import os
import sqlite3
import json

sys.path.insert(0, 'backend')

db_path = 'backend/paypilot_dev.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=================== ALL RECOVERY CASES ===================")
cursor.execute("SELECT id, case_type, amount, recovered_amount, status, transaction_id, mandate_id FROM recovery_cases")
for row in cursor.fetchall():
    print(dict(row))

print("\n=================== ALL CAPTURED TRANSACTIONS ===================")
cursor.execute("SELECT id, merchant_id, customer_id, razorpay_payment_id, razorpay_order_id, amount, status FROM transactions WHERE status='captured'")
for row in cursor.fetchall():
    print(dict(row))

print("\n=================== ALL RECOVERY ACTIONS ===================")
cursor.execute("SELECT id, case_id, action_type, status, razorpay_payment_link_id, short_url, payload FROM recovery_actions")
for row in cursor.fetchall():
    print(dict(row))

print("\n=================== AUDIT LOGS FOR RECOVERY ===================")
cursor.execute("SELECT id, case_id, actor, event_type, description, metadata_json, created_at FROM audit_logs WHERE event_type LIKE '%RECOVER%' OR description LIKE '%reconcil%' OR description LIKE '%captured%' OR description LIKE '%success%'")
for row in cursor.fetchall():
    print(dict(row))
