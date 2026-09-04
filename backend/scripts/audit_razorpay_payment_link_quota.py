import os
import sys
import requests
import dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.config import settings

def audit_razorpay_quota():
    print("=================================================================")
    print("   PAYPILOT AI -- RAZORPAY PAYMENT LINK QUOTA AUDIT              ")
    print("=================================================================\n")

    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET

    res = requests.get("https://api.razorpay.com/v1/payment_links?count=100", auth=(key_id, key_secret))
    if res.status_code != 200:
        print(f"[FAIL] Could not query Razorpay API: HTTP {res.status_code}")
        return False

    plinks = res.json().get("payment_links", [])
    total_count = len(plinks)

    categories = {
        "PAID": [],
        "PARTIALLY_PAID": [],
        "CREATED": [],
        "CANCELLED": [],
        "EXPIRED": []
    }

    for l in plinks:
        status = l.get("status", "").upper()
        if status in categories:
            categories[status].append(l)
        else:
            categories.setdefault(status, []).append(l)

    print(f"Total Payment Links on Razorpay API: {total_count} / 30 (Test Mode Quota Limit)\n")

    for cat_name, items in categories.items():
        print(f"=== {cat_name} ({len(items)}) ===")
        for item in items:
            p_ids = [p.get("payment_id") for p in item.get("payments", [])]
            print(f" - ID: {item['id']} | Amount: INR {item['amount']/100:.2f} | Paid: INR {item['amount_paid']/100:.2f} | Status: {item['status']} | Payments: {p_ids or 'None'}")
        print()

    quota_exhausted = total_count >= 30
    print("=================================================================")
    print(f"   QUOTA STATUS: {'EXHAUSTED (30/30 limit reached)' if quota_exhausted else 'AVAILABLE'}")
    print("=================================================================\n")
    return not quota_exhausted

if __name__ == "__main__":
    audit_razorpay_quota()
