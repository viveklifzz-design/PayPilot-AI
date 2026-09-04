import sqlite3
import json
import os
import sys

sys.path.insert(0, 'backend')

conn = sqlite3.connect('backend/paypilot_dev.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== STEP 5: FINANCIAL INTEGRITY AUDIT ===")
cursor.execute("SELECT id, case_type, amount, recovered_amount, status FROM recovery_cases WHERE status='RECOVERED'")
recovered_cases = cursor.fetchall()
print(f"Total RECOVERED Cases: {len(recovered_cases)}")
total_rec_sum = sum(c['recovered_amount'] for c in recovered_cases)
print(f"Total Recovered Revenue Sum in DB: INR {total_rec_sum:.2f}")

for c in recovered_cases:
    print(f"  Case {c['id']}: Type={c['case_type']}, Amt={c['amount']}, RecAmt={c['recovered_amount']}")

print("\n=== STEP 6: DASHBOARD TRUTHFULNESS ===")
cursor.execute("SELECT id, status, recovered_amount FROM recovery_cases WHERE status='INVALID_UNRECONCILED'")
unreconciled = cursor.fetchall()
print(f"Unreconciled Cases isolated: {len(unreconciled)}")
for u in unreconciled:
    print(f"  Unreconciled Case {u['id']}: Status={u['status']}, RecAmt={u['recovered_amount']}")

print("\n=== STEP 9: POLICY & STOPPING RULES VERIFICATION ===")
cursor.execute("SELECT id, case_type, status, policy_failure_reason FROM recovery_cases WHERE status IN ('ESCALATED', 'STOPPED')")
stopped = cursor.fetchall()
print(f"Escalated/Stopped Cases: {len(stopped)}")
for s in stopped:
    print(f"  Stopped Case {s['id']}: Status={s['status']}, Reason={s['policy_failure_reason']}")

print("\n=== STEP 10: AUDIT TRAIL INTEGRITY ===")
cursor.execute("SELECT count(*) as cnt FROM audit_logs")
log_cnt = cursor.fetchone()['cnt']
print(f"Total Audit Log Events in DB: {log_cnt}")

print("\n=== STEP 11: NOTIFICATION INTEGRITY ===")
cursor.execute("SELECT count(*) as cnt FROM notifications")
notif_cnt = cursor.fetchone()['cnt']
print(f"Total Notifications in DB: {notif_cnt}")

print("\n=== STEP 7 & 8: SECRET ISOLATION AUDIT ===")
# Ensure no hardcoded secret keys in frontend source files
frontend_dir = 'frontend/src'
secret_leaks = []
terms_to_check = ['rzp_live_', 'sk_live_', 'AIzaSy']
for root, dirs, files in os.walk(frontend_dir):
    for f in files:
        if f.endswith(('.ts', '.tsx', '.json', '.js')):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                content = fp.read()
                for term in terms_to_check:
                    if term in content:
                        secret_leaks.append((path, term))

if secret_leaks:
    print("[FAIL] Secret leaks found in frontend:", secret_leaks)
else:
    print("[OK] Zero hardcoded API secrets found in frontend source files!")
