#!/usr/bin/env python3
"""
Local Webhook Simulation Script for PayPilot AI
Generates valid Razorpay Webhook payloads with real HMAC-SHA256 signatures.
Explicitly loads backend/.env relative to this script's location.
"""
import sys
import os
import json
import hmac
import hashlib
from pathlib import Path
import httpx
from dotenv import load_dotenv

# Explicitly load backend/.env based on script location
BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BACKEND_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH, override=True)
else:
    # Fallback if executed from outside standard tree
    load_dotenv(override=True)

# Add backend to sys.path
sys.path.insert(0, str(BACKEND_DIR))

WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
TARGET_URL = os.getenv("TARGET_WEBHOOK_URL", "http://localhost:8000/api/v1/webhooks/razorpay")

def generate_failed_payment_payload(payment_id="pay_sim_999", order_id="order_sim_999", amount=150000):
    return {
        "entity": "event",
        "account_id": "acc_sim_123",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "entity": "payment",
                    "amount": amount,
                    "currency": "INR",
                    "status": "failed",
                    "order_id": order_id,
                    "method": "card",
                    "error_code": "BAD_REQUEST_PAYMENT_DECLINED",
                    "error_description": "Payment was declined by issuing bank",
                    "error_reason": "payment_declined",
                    "email": "customer@example.com",
                    "contact": "+919876543210"
                }
            }
        },
        "created_at": 1700000000
    }

def send_simulated_webhook(payload, secret=None, target_url=None, event_id=None):
    webhook_secret = secret or WEBHOOK_SECRET
    url = target_url or TARGET_URL
    
    raw_body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    signature = hmac.new(webhook_secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "x-razorpay-signature": signature,
    }
    if event_id:
        headers["x-razorpay-event-id"] = event_id

    secret_sha = hashlib.sha256(webhook_secret.encode('utf-8')).hexdigest()[:12] if webhook_secret else "NONE"
    body_sha = hashlib.sha256(raw_body).hexdigest()[:12]

    print("=== PayPilot AI Webhook Simulator ===")
    print(f"Env File Loaded: {ENV_PATH}")
    print(f"Secret SHA256 Fingerprint: {secret_sha} (Length: {len(webhook_secret)})")
    print(f"Body SHA256 Fingerprint: {body_sha}")
    print(f"Sending Webhook to: {url}")
    print(f"Event: {payload.get('event')}")
    print(f"Signature (first 8): {signature[:8]}...")

    try:
        response = httpx.post(url, content=raw_body, headers=headers, timeout=10.0)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return response
    except Exception as e:
        print(f"Error sending webhook: {e}")
        return None

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_URL
    payload = generate_failed_payment_payload()
    send_simulated_webhook(payload, target_url=target)
