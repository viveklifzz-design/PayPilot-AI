import sqlite3
import uuid
import datetime

conn = sqlite3.connect('backend/paypilot_dev.db')
cursor = conn.cursor()

# Update case a802b0cb-06a3-4ba2-b0d5-e1ab37422741
cursor.execute("""
    UPDATE recovery_cases 
    SET status = 'INVALID_UNRECONCILED', recovered_amount = 0.0 
    WHERE id = 'a802b0cb-06a3-4ba2-b0d5-e1ab37422741'
""")

# Insert audit log
log_id = str(uuid.uuid4())
now_str = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
meta = '{"case_id": "a802b0cb-06a3-4ba2-b0d5-e1ab37422741", "previous_status": "RECOVERED", "new_status": "INVALID_UNRECONCILED", "reason": "AMOUNT_MISMATCH_NO_PROVIDER_PAYMENT"}'

cursor.execute("""
    INSERT INTO audit_logs (id, case_id, actor, event_type, description, metadata_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", (
    log_id,
    'a802b0cb-06a3-4ba2-b0d5-e1ab37422741',
    'DATA_LINEAGE_AUDITOR',
    'DATA_LINEAGE_RECLASSIFIED',
    'Case marked INVALID_UNRECONCILED: Case amount INR 2,500 has no matching provider-captured payment. Excluded from recovered revenue metrics.',
    meta,
    now_str
))

conn.commit()
print("Successfully updated case a802b0cb-06a3-4ba2-b0d5-e1ab37422741 to INVALID_UNRECONCILED.")
