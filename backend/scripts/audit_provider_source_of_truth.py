import sys
import os
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings

def audit_provider_source_of_truth():
    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET

    print("=================================================================")
    print("   PAYPILOT AI -- DIRECT RAZORPAY API SOURCE OF TRUTH AUDIT      ")
    print("=================================================================\n")

    auth = (key_id, key_secret)

    # 1. Fetch Original Failed Payment pay_TTXlSqxyg5hAiT
    print("1. QUERYING ORIGINAL FAILED PAYMENT (pay_TTXlSqxyg5hAiT)...")
    res1 = requests.get("https://api.razorpay.com/v1/payments/pay_TTXlSqxyg5hAiT", auth=auth)
    if res1.status_code == 200:
        p1 = res1.json()
        print(f"   - Payment ID       : {p1.get('id')}")
        print(f"   - Amount           : INR {p1.get('amount') / 100:.2f} ({p1.get('amount')} paise)")
        print(f"   - Currency         : {p1.get('currency')}")
        print(f"   - Status           : {p1.get('status')}")
        print(f"   - Captured         : {p1.get('captured')}")
        print(f"   - Method           : {p1.get('method')}")
        print(f"   - Provider Order ID: {p1.get('order_id')}")
        print(f"   - Error Code       : {p1.get('error_code')}")
        print(f"   - Error Reason     : {p1.get('error_reason')}")
        print(f"   - Created At       : {p1.get('created_at')}")
        print(f"   - Notes            : {p1.get('notes')}")
    else:
        print(f"   [ERROR] Failed to fetch pay_TTXlSqxyg5hAiT: {res1.status_code} {res1.text}")

    print("\n-----------------------------------------------------------------\n")

    # 2. Fetch Real Recovery Order order_TU2xgzptEfg7rP
    print("2. QUERYING REAL RECOVERY ORDER (order_TU2xgzptEfg7rP)...")
    res2 = requests.get("https://api.razorpay.com/v1/orders/order_TU2xgzptEfg7rP", auth=auth)
    if res2.status_code == 200:
        o2 = res2.json()
        print(f"   - Order ID         : {o2.get('id')}")
        print(f"   - Order Amount     : INR {o2.get('amount') / 100:.2f} ({o2.get('amount')} paise)")
        print(f"   - Amount Paid      : INR {o2.get('amount_paid') / 100:.2f} ({o2.get('amount_paid')} paise)")
        print(f"   - Amount Due       : INR {o2.get('amount_due') / 100:.2f} ({o2.get('amount_due')} paise)")
        print(f"   - Currency         : {o2.get('currency')}")
        print(f"   - Status           : {o2.get('status')}")
        print(f"   - Created At       : {o2.get('created_at')}")
        print(f"   - Notes            : {o2.get('notes')}")
    else:
        print(f"   [ERROR] Failed to fetch order_TU2xgzptEfg7rP: {res2.status_code} {res2.text}")

    print("\n-----------------------------------------------------------------\n")

    # 3. Fetch Real Recovery Payment pay_TU3EQsT63DFVuX
    print("3. QUERYING REAL RECOVERY PAYMENT (pay_TU3EQsT63DFVuX)...")
    res3 = requests.get("https://api.razorpay.com/v1/payments/pay_TU3EQsT63DFVuX", auth=auth)
    if res3.status_code == 200:
        p3 = res3.json()
        print(f"   - Payment ID       : {p3.get('id')}")
        print(f"   - Amount           : INR {p3.get('amount') / 100:.2f} ({p3.get('amount')} paise)")
        print(f"   - Currency         : {p3.get('currency')}")
        print(f"   - Status           : {p3.get('status')}")
        print(f"   - Captured         : {p3.get('captured')}")
        print(f"   - Method           : {p3.get('method')}")
        print(f"   - Provider Order ID: {p3.get('order_id')}")
        print(f"   - Created At       : {p3.get('created_at')}")
        print(f"   - Notes            : {p3.get('notes')}")
    else:
        print(f"   [ERROR] Failed to fetch pay_TU3EQsT63DFVuX: {res3.status_code} {res3.text}")

    print("\n=================================================================")
    print("   PROVIDER SOURCE OF TRUTH AUDIT COMPLETE                       ")
    print("=================================================================\n")

if __name__ == "__main__":
    audit_provider_source_of_truth()
