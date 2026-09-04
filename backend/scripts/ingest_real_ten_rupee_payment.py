import sys
import os
import asyncio
import requests
import dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base import *
from app.db.session import AsyncSessionLocal
from sqlalchemy import select
from app.models.merchant import Merchant
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.core.config import settings

async def sync_real_ten_rupee_payment_from_razorpay():
    print("=================================================================")
    print("   FETCHING REAL RAZORPAY TEST MODE INR 10 PAYMENT FROM PROVIDER  ")
    print("=================================================================\n")

    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET
    payment_id = "pay_TTa6BvTMgDHtc8"
    url = f"https://api.razorpay.com/v1/payments/{payment_id}"

    res = requests.get(url, auth=(key_id, key_secret))
    if res.status_code != 200:
        print(f"[FAIL] Failed to fetch payment '{payment_id}' from Razorpay API: HTTP {res.status_code}")
        print(res.text)
        return False

    provider_data = res.json()
    print(f"[PASS] 1. Live Razorpay API Response : HTTP 200 OK")
    print(f"       - Payment ID                 : {provider_data['id']}")
    print(f"       - Amount (paise)             : {provider_data['amount']} (INR {provider_data['amount'] / 100:.2f})")
    print(f"       - Status                     : {provider_data['status']}")
    print(f"       - Order ID                   : {provider_data['order_id']}")
    print(f"       - Method                     : {provider_data['method']} ({provider_data.get('bank')})")
    print(f"       - Email                      : {provider_data['email']}")

    async with AsyncSessionLocal() as db:
        m_res = await db.execute(select(Merchant))
        merchant = m_res.scalars().first()
        if not merchant:
            merchant = Merchant(name="Razorpay Merchant", email="merchant@razorpay.com")
            db.add(merchant)
            await db.commit()
            await db.refresh(merchant)

        # Find or create customer matching email/contact from Razorpay
        c_res = await db.execute(select(Customer).where(Customer.email == provider_data["email"]))
        customer = c_res.scalar_one_or_none()
        if not customer:
            customer = Customer(
                merchant_id=merchant.id,
                name=provider_data["email"].split("@")[0],
                email=provider_data["email"],
                phone=provider_data["contact"]
            )
            db.add(customer)
            await db.commit()
            await db.refresh(customer)

        # Sync or update transaction record with Provider Data
        t_res = await db.execute(select(Transaction).where(Transaction.razorpay_payment_id == payment_id))
        txn = t_res.scalar_one_or_none()

        if not txn:
            txn = Transaction(
                merchant_id=merchant.id,
                customer_id=customer.id,
                razorpay_payment_id=provider_data["id"],
                razorpay_order_id=provider_data["order_id"],
                amount=provider_data["amount"] / 100.0,
                currency=provider_data["currency"],
                status=provider_data["status"],
                payment_method=provider_data["method"],
                raw_payload=provider_data
            )
            db.add(txn)
        else:
            txn.customer_id = customer.id
            txn.amount = provider_data["amount"] / 100.0
            txn.status = provider_data["status"]
            txn.payment_method = provider_data["method"]
            txn.raw_payload = provider_data
            db.add(txn)

        await db.commit()
        await db.refresh(txn)

        print(f"[PASS] 2. Synced with Local Database : Transaction ID #{txn.id[:8]}")
        print(f"       - DB Amount                  : INR {txn.amount:.2f}")
        print(f"       - DB Status                  : {txn.status}")
        print(f"       - DB Customer ID             : {customer.id}")

    print("\n=================================================================")
    print("   RAZORPAY PROVIDER-VERIFIED INR 10 PAYMENT SYNC COMPLETE        ")
    print("=================================================================\n")
    return True

if __name__ == "__main__":
    asyncio.run(sync_real_ten_rupee_payment_from_razorpay())
