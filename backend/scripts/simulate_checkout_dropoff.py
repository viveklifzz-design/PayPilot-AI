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
from app.models.checkout_session import CheckoutSession
from app.models.base import utc_now
from app.services.revenue_risk.dropoff_detector import dropoff_detector
from datetime import timedelta

async def main():
    async with AsyncSessionLocal() as db:
        print("=======================================================")
        print("    PAYPILOT AI -- CHECKOUT DROP-OFF SIMULATOR CLI     ")
        print("=======================================================")

        # Find or create merchant
        m_res = await db.execute(select(Merchant))
        merchant = m_res.scalars().first()
        if not merchant:
            merchant = Merchant(name="Demo Merchant", email="demo@merchant.com")
            db.add(merchant)
            await db.commit()
            await db.refresh(merchant)

        # 1. Create simulated inactive checkout session (45 minutes ago)
        old_time = utc_now() - timedelta(minutes=45)
        session = CheckoutSession(
            merchant_id=merchant.id,
            amount=2999.0,
            currency="INR",
            status="CREATED",
            created_at=old_time,
            source="CHECKOUT_SIMULATOR"
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        print(f"Created simulated unpaid checkout session '{session.id}' for INR 2,999.00 (Age: 45m).")

        # 2. Run dropoff detector
        created_cases = await dropoff_detector.detect_and_process_dropoffs(db, window_minutes=30)
        
        if created_cases:
            case = created_cases[0]
            print("\n[SUCCESS] Checkout Drop-off Detected & Processed!")
            print(f"Checkout Session ID : {session.id}")
            print(f"Recovery Case ID    : {case.id}")
            print(f"Case Type           : {case.case_type}")
            print(f"Status              : {case.status}")
            print(f"Amount              : INR {float(case.amount):,.2f}")
            print(f"Risk Score          : {case.risk_score} ({case.risk_level})")
            print(f"Priority            : {case.priority_level}")
        else:
            print("No drop-off cases created.")

if __name__ == "__main__":
    asyncio.run(main())
