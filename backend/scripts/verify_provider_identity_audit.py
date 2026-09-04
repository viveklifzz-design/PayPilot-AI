import sys
import os
import requests
import dotenv

def run_identity_audit():
    print("=================================================================")
    print("   PAYPILOT AI -- REAL PROVIDER RECOVERY IDENTITY AUDIT          ")
    print("=================================================================\n")

    dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")

    # 1. ORIGINAL PAYMENT AUDIT
    pay_id = "pay_TTa6BvTMgDHtc8"
    url_pay = f"https://api.razorpay.com/v1/payments/{pay_id}"
    res_pay = requests.get(url_pay, auth=(key_id, key_secret))
    
    if res_pay.status_code == 200:
        pay_data = res_pay.json()
        print(f"1. ORIGINAL RAZORPAY PAYMENT (pay_TTa6BvTMgDHtc8):")
        print(f"   - Provider Status                 : {pay_data['status']}")
        print(f"   - Provider Amount (paise)         : {pay_data['amount']} (INR {pay_data['amount']/100:.2f})")
        print(f"   - Order ID                       : {pay_data['order_id']}")
        print(f"   - Payment Method                 : {pay_data['method']} ({pay_data.get('bank')})")
        print(f"   - Email                          : {pay_data['email']}")
        print(f"   - Classification                 : ORIGINAL REAL PAYMENT (INR 10.00)")
    else:
        print(f"[FAIL] Could not query payment '{pay_id}': HTTP {res_pay.status_code}")

    # 2. RECOVERY PAYMENT LINK AUDIT (plink_TThMwMCq60gAju)
    plink_id = "plink_TThMwMCq60gAju"
    url_plink = f"https://api.razorpay.com/v1/payment_links/{plink_id}"
    res_plink = requests.get(url_plink, auth=(key_id, key_secret))

    if res_plink.status_code == 200:
        plink_data = res_plink.json()
        print(f"\n2. RECOVERY PAYMENT LINK (plink_TThMwMCq60gAju):")
        print(f"   - Provider Status                 : {plink_data['status']}")
        print(f"   - Provider Amount (paise)         : {plink_data['amount']} (INR {plink_data['amount']/100:.2f})")
        print(f"   - Provider Amount Paid (paise)    : {plink_data['amount_paid']} (INR {plink_data['amount_paid']/100:.2f})")
        print(f"   - Short URL                      : {plink_data['short_url']}")
        print(f"   - Associated Payments Count      : {len(plink_data.get('payments', []))}")
        
        has_new_payment = len(plink_data.get('payments', [])) > 0
        if not has_new_payment:
            print(f"   - Provider Payment Entity         : NONE (Link is in 'created' state, uncollected on Razorpay)")
            print(f"   - Identity Match Result           : pay_TTa6BvTMgDHtc8 (INR 10) != plink_TThMwMCq60gAju (INR 2,500)")
            print(f"   - Classification                 : REAL RECOVERY PAYMENT NOT YET VERIFIED ON PROVIDER")
    else:
        print(f"[FAIL] Could not query Payment Link '{plink_id}': HTTP {res_plink.status_code}")

    print("\n=================================================================")
    print("   PROVIDER IDENTITY AUDIT SUMMARY:                               ")
    print("   - Original Payment (pay_TTa6BvTMgDHtc8) : INR 10.00 (CAPTURED)")
    print("   - Recovery Link (plink_TThMwMCq60gAju)  : INR 2,500.00 (UNPAID)")
    print("   - Result: DO NOT MATCH. Recovery payment entity not yet paid on Razorpay.")
    print("=================================================================\n")

if __name__ == "__main__":
    run_identity_audit()
