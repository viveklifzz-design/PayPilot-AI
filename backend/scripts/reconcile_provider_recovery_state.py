import sys
import os
import asyncio
import sqlite3
import requests
import dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings

def reconcile_provider_recovery_state():
    print("=================================================================")
    print("   PAYPILOT AI -- RECONCILE PROVIDER RECOVERY STATE              ")
    print("=================================================================\n")

    dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET

    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "paypilot_dev.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Fetch all cases marked RECOVERED
    recovered_cases = cur.execute(
        "SELECT id, case_type, amount, status, recovered_amount, transaction_id FROM recovery_cases WHERE status = 'RECOVERED'"
    ).fetchall()

    print(f"Found {len(recovered_cases)} recovery cases marked RECOVERED in database:")

    reconciled_count = 0
    for case in recovered_cases:
        case_id, c_type, amount, c_status, rec_amount, txn_id = case
        
        # Check associated recovery action payment links
        actions = cur.execute(
            "SELECT id, action_type, status, razorpay_payment_link_id FROM recovery_actions WHERE case_id = ?",
            (case_id,)
        ).fetchall()

        is_provider_paid = False
        plink_id = None
        for act in actions:
            act_id, act_type, act_status, link_id = act
            if link_id:
                plink_id = link_id
                url = f"https://api.razorpay.com/v1/payment_links/{link_id}"
                res = requests.get(url, auth=(key_id, key_secret))
                if res.status_code == 200:
                    pl_data = res.json()
                    if pl_data.get("amount_paid", 0) > 0 and len(pl_data.get("payments", [])) > 0:
                        is_provider_paid = True
                        break

        if not is_provider_paid:
            print(f" - Case #{case_id[:8]} (Amount: INR {amount:.2f}): Uncollected on Razorpay API (Link: {plink_id or 'None'}) -> Reconciling status to DIAGNOSED, recovered_amount = 0.0")
            cur.execute(
                "UPDATE recovery_cases SET status = 'DIAGNOSED', recovered_amount = 0.0 WHERE id = ?",
                (case_id,)
            )
            reconciled_count += 1
        else:
            print(f" - Case #{case_id[:8]} (Amount: INR {amount:.2f}): PROVIDER VERIFIED PAID (Link: {plink_id})")

    conn.commit()
    conn.close()

    print(f"\n=================================================================")
    print(f"   RECONCILIATION COMPLETE: Reconciled {reconciled_count} local uncollected cases.")
    print("=================================================================\n")
    return True

if __name__ == "__main__":
    reconcile_provider_recovery_state()
