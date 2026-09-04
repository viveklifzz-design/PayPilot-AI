import sys
import os
import asyncio

# Add backend dir to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.base import *  # Load all SQLAlchemy models
from app.db.session import AsyncSessionLocal
from app.models.merchant import Merchant
from app.models.transaction import Transaction
from app.services.revenue_risk.subscription_recovery import subscription_recovery_service

async def main():
    async with AsyncSessionLocal() as db:
        print("=======================================================")
        print("   PAYPILOT AI -- SUBSCRIPTION FAILURE SIMULATOR CLI   ")
        print("=======================================================")

        m_res = await db.execute(select(Merchant))
        merchant = m_res.scalars().first()
        if not merchant:
            merchant = Merchant(name="Demo Merchant", email="demo@merchant.com")
            db.add(merchant)
            await db.commit()
            await db.refresh(merchant)

        # 1. Create simulated recurring subscription
        sub = await subscription_recovery_service.create_subscription(
            db=db,
            merchant_id=merchant.id,
            plan_name="Growth SaaS Monthly",
            amount=4999.0,
            billing_interval="monthly"
        )
        print(f"Created Subscription '{sub.id}' for '{sub.plan_name}' (INR 4,999.00/mo).")

        # 2. Simulate failed recurring transaction
        txn = Transaction(
            merchant_id=merchant.id,
            amount=4999.0,
            currency="INR",
            status="failed",
            error_code="BAD_REQUEST_ERROR",
            error_description="Recurring auto-debit attempt failed due to card authorization expiry",
            error_source="bank",
            error_step="payment_authorization",
            error_reason="card_expired",
            payment_method="card"
        )
        db.add(txn)
        await db.commit()
        await db.refresh(txn)

        # 3. Handle failed recurring payment
        attempt, case = await subscription_recovery_service.handle_failed_subscription_payment(
            db=db,
            subscription_id=sub.id,
            txn=txn,
            attempt_number=1
        )

        print("\n[SUCCESS] Subscription Failure Handled!")
        print(f"Subscription ID      : {sub.id}")
        print(f"Attempt ID           : {attempt.id}")
        print(f"Recovery Case ID     : {case.id}")
        print(f"Case Type            : {case.case_type}")
        print(f"Status               : {case.status}")
        print(f"Amount               : INR {float(case.amount):,.2f}")
        print(f"Risk Score           : {case.risk_score} ({case.risk_level})")
        print(f"Priority             : {case.priority_level}")

if __name__ == "__main__":
    asyncio.run(main())
