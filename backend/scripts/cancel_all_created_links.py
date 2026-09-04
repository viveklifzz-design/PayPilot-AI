import os
import requests
import dotenv

dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
key_id = os.getenv("RAZORPAY_KEY_ID")
key_secret = os.getenv("RAZORPAY_KEY_SECRET")

res_pl = requests.get("https://api.razorpay.com/v1/payment_links?count=100", auth=(key_id, key_secret))
if res_pl.status_code == 200:
    plinks = res_pl.json().get("payment_links", [])
    print(f"Total Payment Links on Razorpay API: {len(plinks)}")
    cancelled = 0
    for l in plinks:
        if l.get("status") == "created":
            pid = l["id"]
            res = requests.post(f"https://api.razorpay.com/v1/payment_links/{pid}/cancel", auth=(key_id, key_secret))
            if res.status_code == 200:
                cancelled += 1
                print(f"Cancelled Payment Link: {pid} (Amount: INR {l['amount']/100:.2f})")
    print(f"Successfully cancelled total {cancelled} unpaid links.")
