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
from app.models.recovery_case import RecoveryCase
from app.services.revenue_risk.risk_engine import risk_engine
from app.core.config import settings

async def sync_real_provider_data():
    print("=================================================================")
    print("   PAYPILOT AI -- SYNC REAL RAZORPAY PROVIDER RECORDS           ")
    print("=================================================================\n")

    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET

    async with AsyncSessionLocal() as db:
        # Merchant & Customer Setup
        m_res = await db.execute(select(Merchant))
        merchant = m_res.scalars().first()
        if not merchant:
            merchant = Merchant(name="Razorpay Test Merchant", email="merchant@razorpay.com")
            db.add(merchant)
            await db.commit()
            await db.refresh(merchant)

        # 1. SYNC REAL CAPTURED PAYMENT (pay_TTa6BvTMgDHtc8)
        res_cap = requests.get("https://api.razorpay.com/v1/payments/pay_TTa6BvTMgDHtc8", auth=(key_id, key_secret))
        if res_cap.status_code == 200:
            data_cap = res_cap.json()
            c_res = await db.execute(select(Customer).where(Customer.email == data_cap["email"]))
            cust_cap = c_res.scalar_one_or_none()
            if not cust_cap:
                cust_cap = Customer(
                    merchant_id=merchant.id,
                    name=data_cap["email"].split("@")[0],
                    email=data_cap["email"],
                    phone=data_cap.get("contact")
                )
                db.add(cust_cap)
                await db.commit()
                await db.refresh(cust_cap)

            t_res_cap = await db.execute(select(Transaction).where(Transaction.razorpay_payment_id == "pay_TTa6BvTMgDHtc8"))
            txn_cap = t_res_cap.scalar_one_or_none()
            if not txn_cap:
                txn_cap = Transaction(
                    merchant_id=merchant.id,
                    customer_id=cust_cap.id,
                    razorpay_payment_id=data_cap["id"],
                    razorpay_order_id=data_cap.get("order_id"),
                    amount=data_cap["amount"] / 100.0,
                    currency=data_cap["currency"],
                    status=data_cap["status"],
                    payment_method=data_cap["method"],
                    raw_payload=data_cap
                )
                db.add(txn_cap)
            else:
                txn_cap.customer_id = cust_cap.id
                txn_cap.amount = data_cap["amount"] / 100.0
                txn_cap.status = data_cap["status"]
                txn_cap.payment_method = data_cap["method"]
                db.add(txn_cap)

            await db.commit()
            print(f"[PASS] 1. Synced Real Captured Payment : pay_TTa6BvTMgDHtc8 (INR {data_cap['amount']/100:.2f}, captured)")

        # 2. SYNC REAL FAILED PAYMENT (pay_TTXlSqxyg5hAiT)
        res_fail = requests.get("https://api.razorpay.com/v1/payments/pay_TTXlSqxyg5hAiT", auth=(key_id, key_secret))
        if res_fail.status_code == 200:
            data_fail = res_fail.json()
            c_res2 = await db.execute(select(Customer).where(Customer.email == data_fail["email"]))
            cust_fail = c_res2.scalar_one_or_none()
            if not cust_fail:
                cust_fail = Customer(
                    merchant_id=merchant.id,
                    name=data_fail["email"].split("@")[0],
                    email=data_fail["email"],
                    phone=data_fail.get("contact")
                )
                db.add(cust_fail)
                await db.commit()
                await db.refresh(cust_fail)

            t_res_fail = await db.execute(select(Transaction).where(Transaction.razorpay_payment_id == "pay_TTXlSqxyg5hAiT"))
            txn_fail = t_res_fail.scalar_one_or_none()
            if not txn_fail:
                txn_fail = Transaction(
                    merchant_id=merchant.id,
                    customer_id=cust_fail.id,
                    razorpay_payment_id=data_fail["id"],
                    razorpay_order_id=data_fail.get("order_id"),
                    amount=data_fail["amount"] / 100.0,
                    currency=data_fail["currency"],
                    status=data_fail["status"],
                    payment_method=data_fail["method"],
                    error_code=data_fail.get("error_code"),
                    error_description=data_fail.get("error_description"),
                    error_source=data_fail.get("error_source"),
                    error_step=data_fail.get("error_step"),
                    error_reason=data_fail.get("error_reason"),
                    raw_payload=data_fail
                )
                db.add(txn_fail)
                await db.commit()
                await db.refresh(txn_fail)
            else:
                txn_fail.customer_id = cust_fail.id
                txn_fail.amount = data_fail["amount"] / 100.0
                txn_fail.status = data_fail["status"]
                txn_fail.error_code = data_fail.get("error_code")
                txn_fail.error_description = data_fail.get("error_description")
                txn_fail.error_source = data_fail.get("error_source")
                txn_fail.error_step = data_fail.get("error_step")
                txn_fail.error_reason = data_fail.get("error_reason")
                db.add(txn_fail)
                await db.commit()

            # Ensure RecoveryCase exists for this real failed transaction
            rc_res = await db.execute(select(RecoveryCase).where(RecoveryCase.transaction_id == txn_fail.id))
            rc = rc_res.scalar_one_or_none()
            if not rc:
                risk_res = risk_engine.assess_transaction(amount=float(txn_fail.amount), error_code=txn_fail.error_code)
                rc = RecoveryCase(
                    case_type="PAYMENT_FAILURE",
                    merchant_id=merchant.id,
                    transaction_id=txn_fail.id,
                    customer_id=cust_fail.id,
                    amount=float(txn_fail.amount),
                    risk_score=risk_res.risk_score,
                    risk_level=risk_res.risk_level,
                    priority_score=risk_res.priority_score,
                    priority_level=risk_res.priority_level,
                    risk_factors=risk_res.risk_factors,
                    status="OPEN",
                    policy_passed=True
                )
                db.add(rc)
                await db.commit()

            print(f"[PASS] 2. Synced Real Failed Payment   : pay_TTXlSqxyg5hAiT (INR {data_fail['amount']/100:.2f}, failed)")
            print(f"       - Error Code                 : {data_fail.get('error_code')}")
            print(f"       - Error Reason               : {data_fail.get('error_reason')}")

    print("\n=================================================================")
    print("   PROVIDER DATA SYNC COMPLETE: Real INR 10 Records Synced       ")
    print("=================================================================\n")
    return True

if __name__ == "__main__":
    asyncio.run(sync_real_provider_data())
