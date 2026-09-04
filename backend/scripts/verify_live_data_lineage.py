import sys
import os
import sqlite3
import json
import urllib.request
import requests
import dotenv

def verify_live_data_lineage():
    print("=================================================================")
    print("   PAYPILOT AI -- LIVE PROVIDER DATA LINEAGE AUDIT               ")
    print("=================================================================\n")

    # 1. PROVIDER AUDIT
    dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    payment_id = "pay_TTa6BvTMgDHtc8"

    print(f"1. RAZORPAY TEST MODE PROVIDER AUDIT:")
    url = f"https://api.razorpay.com/v1/payments/{payment_id}"
    res = requests.get(url, auth=(key_id, key_secret))
    if res.status_code != 200:
        print(f"   [FAIL] Razorpay API returned HTTP {res.status_code}")
        return False

    rzp_p = res.json()
    rzp_amount = rzp_p["amount"] / 100.0
    print(f"   [PASS] Live Razorpay API Payment  : {rzp_p['id']}")
    print(f"          - Provider Amount (INR)     : INR {rzp_amount:.2f}")
    print(f"          - Provider Status           : {rzp_p['status']}")
    print(f"          - Provider Order ID         : {rzp_p['order_id']}")
    print(f"          - Provider Customer Email   : {rzp_p['email']}")

    # 2. DATABASE AUDIT
    print(f"\n2. LOCAL DATABASE AUDIT:")
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "paypilot_dev.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    db_txn = cur.execute(
        "SELECT id, customer_id, razorpay_payment_id, amount, status, payment_method FROM transactions WHERE razorpay_payment_id = ?",
        (payment_id,)
    ).fetchone()

    if not db_txn:
        print(f"   [FAIL] Transaction '{payment_id}' not found in local database.")
        conn.close()
        return False

    db_id, db_cust_id, db_pay_id, db_amount, db_status, db_method = db_txn
    print(f"   [PASS] Local Database Transaction : ID #{db_id[:8]}")
    print(f"          - DB Payment ID             : {db_pay_id}")
    print(f"          - DB Amount                 : INR {db_amount:.2f}")
    print(f"          - DB Status                 : {db_status}")

    # Verify amount match
    if db_amount != rzp_amount:
        print(f"   [FAIL] Provider amount (INR {rzp_amount}) != DB amount (INR {db_amount})")
        conn.close()
        return False
    print(f"   [PASS] Provider vs DB Amount Match: EXACT MATCH (INR {db_amount:.2f})")

    # 3. BACKEND API AUDIT
    print(f"\n3. BACKEND REST API AUDIT:")
    api_url = "http://127.0.0.1:8000/api/v1/transactions"
    try:
        api_txns = json.loads(urllib.request.urlopen(api_url).read().decode())
        target_api = next((t for t in api_txns if t.get("razorpay_payment_id") == payment_id), None)
        if not target_api:
            print(f"   [FAIL] Transaction '{payment_id}' missing in API GET /api/v1/transactions output.")
            conn.close()
            return False

        print(f"   [PASS] API Endpoint GET /api/v1/transactions returned payment '{payment_id}'")
        print(f"          - API Amount                : INR {target_api['amount']:.2f}")
        print(f"          - API Status                : {target_api['status']}")
    except Exception as e:
        print(f"   [FAIL] REST API call failed: {e}")
        conn.close()
        return False

    # 4. CUSTOMER PORTAL AUDIT & OWNERSHIP SECURITY
    print(f"\n4. CUSTOMER PORTAL & SECURITY AUDIT:")
    login_url = "http://127.0.0.1:8000/api/v1/customer/login"

    # Authorized Login (Customer A: void@razorpay.com)
    req_a = urllib.request.Request(
        login_url,
        data=json.dumps({"email": rzp_p["email"]}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    res_a = json.loads(urllib.request.urlopen(req_a).read().decode())
    cust_a_id = res_a["customer_id"]
    print(f"   [PASS] Authorized Customer Login (Customer A: {rzp_p['email']}) -> Customer ID: {cust_a_id[:8]}")

    # Lookup Customer A transaction
    lookup_url = f"http://127.0.0.1:8000/api/v1/customer/transactions/{payment_id}"
    req_lookup = urllib.request.Request(lookup_url, headers={"x-customer-id": cust_a_id})
    res_lookup = json.loads(urllib.request.urlopen(req_lookup).read().decode())
    print(f"   [PASS] Customer Portal Transaction Lookup for '{payment_id}' : HTTP 200 OK")
    print(f"          - Customer View Amount       : INR {res_lookup['amount']:.2f}")
    print(f"          - Customer View Status       : {res_lookup['status']}")

    # Unauthorized Lookup (Customer B accessing Customer A transaction -> HTTP 403 Forbidden)
    req_b = urllib.request.Request(
        login_url,
        data=json.dumps({"email": "unauthorized_hacker@example.com"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    res_b = json.loads(urllib.request.urlopen(req_b).read().decode())
    cust_b_id = res_b["customer_id"]

    req_hack = urllib.request.Request(lookup_url, headers={"x-customer-id": cust_b_id})
    try:
        urllib.request.urlopen(req_hack)
        print(f"   [FAIL] Unauthorized access was ALLOWED! Security breach!")
        conn.close()
        return False
    except urllib.error.HTTPError as err:
        if err.code == 403:
            print(f"   [PASS] Unauthorized Lookup (Customer B -> Customer A Transaction) -> HTTP 403 Forbidden (SECURITY INTACT)")
        else:
            print(f"   [FAIL] Unexpected HTTP status: {err.code}")
            conn.close()
            return False

    conn.close()

    print("\n=================================================================")
    print("   LIVE DATA LINEAGE AUDIT VERDICT: 100% PASS (PROVIDER VERIFIED)")
    print("=================================================================\n")
    return True

if __name__ == "__main__":
    verify_live_data_lineage()
