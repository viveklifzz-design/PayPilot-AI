import requests
import json
import hmac
import hashlib

BASE_URL = "http://127.0.0.1:8000"

print("1. Creating real Razorpay Test Mode Order...")
order_res = requests.post(f"{BASE_URL}/api/v1/test/create-checkout-order", json={"amount": 20.0, "currency": "INR"})
print("Order Response Status:", order_res.status_code)
order_data = order_res.json()
print("Order Data:", json.dumps(order_data, indent=2))

order_id = order_data["order_id"]
key_id = order_data["key_id"]
secret = "TTEgRlyU2d4G0oBqjJ4384aV" # RAZORPAY_KEY_SECRET

fake_payment_id = f"pay_test_verify_{order_id[-6:]}"
msg = f"{order_id}|{fake_payment_id}".encode("utf-8")
valid_sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

print("\n2. Testing invalid signature rejection...")
invalid_res = requests.post(f"{BASE_URL}/api/v1/checkout/verify", json={
    "razorpay_payment_id": fake_payment_id,
    "razorpay_order_id": order_id,
    "razorpay_signature": "invalid_sig_test",
    "recovery_case_id": None
})
print("Invalid Signature Response Status:", invalid_res.status_code)
print("Invalid Signature Detail:", invalid_res.json())
assert invalid_res.status_code == 400

print("\n3. Testing idempotency with real verified payment ID (pay_TU3EQsT63DFVuX)...")
idempotent_res = requests.post(f"{BASE_URL}/api/v1/checkout/verify", json={
    "razorpay_payment_id": "pay_TU3EQsT63DFVuX",
    "razorpay_order_id": "order_TU2xgzptEfg7rP",
    "razorpay_signature": "any_sig_for_already_recorded",
    "recovery_case_id": "d669dce3-b855-4348-b457-f0ef7c34b6b1"
})
print("Idempotent Verification Status:", idempotent_res.status_code)
print("Idempotent Response:", json.dumps(idempotent_res.json(), indent=2))
assert idempotent_res.status_code == 200
assert idempotent_res.json()["verified"] is True

print("\nVERIFICATION FLOW LOGIC PASS!")
