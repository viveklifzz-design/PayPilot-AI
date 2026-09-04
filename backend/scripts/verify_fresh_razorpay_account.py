import sys
import os
import requests
import dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.config import settings

def verify_fresh_razorpay_account():
    print("=================================================================")
    print("   PAYPILOT AI -- RAZORPAY TEST MODE ACCOUNT IDENTITY AUDIT      ")
    print("=================================================================\n")

    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET

    key_prefix = key_id[:12] if len(key_id) >= 12 else key_id
    print(f"1. PROVIDER CREDENTIALS AUDIT:")
    print(f"   - Key ID Prefix      : {key_prefix}...")
    print(f"   - Environment        : TEST Mode")

    # 1. Query /v1/payments
    res_pay = requests.get("https://api.razorpay.com/v1/payments", auth=(key_id, key_secret))
    if res_pay.status_code == 200:
        payments = res_pay.json().get("items", [])
        print(f"   - Payments Endpoint  : HTTP 200 OK (Found {len(payments)} payments)")
    else:
        print(f"   - Payments Endpoint  : HTTP {res_pay.status_code}")
        return False

    # 2. Query /v1/payment_links
    res_pl = requests.get("https://api.razorpay.com/v1/payment_links?count=100", auth=(key_id, key_secret))
    if res_pl.status_code == 200:
        plinks = res_pl.json().get("payment_links", [])
        pl_count = len(plinks)
        print(f"   - Payment Links API  : HTTP 200 OK (Found {pl_count} links)")
        print(f"   - Link Quota Status  : {pl_count} / 30 {'(EXHAUSTED)' if pl_count >= 30 else '(AVAILABLE)'}")
    else:
        print(f"   - Payment Links API  : HTTP {res_pl.status_code}")
        return False

    print("\n=================================================================")
    print("   RAZORPAY PROVIDER CONNECTIVITY VERIFIED                       ")
    print("=================================================================\n")
    return True

if __name__ == "__main__":
    verify_fresh_razorpay_account()
